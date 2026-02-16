import logging
import uuid

from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class SoftDeleteManager(models.Manager):
    """
    Manager that filters out soft-deleted items by default.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        return super().get_queryset()

    def deleted(self):
        return super().get_queryset().filter(is_deleted=True)


class SoftDeleteMixin(models.Model):
    """
    Mixin to enable soft delete functionality.
    - Adds is_deleted and deleted_at fields.
    - Overrides delete() to perform soft delete and rename unique fields.
    - Adds restore() and hard_delete() methods.
    """

    is_deleted = models.BooleanField(default=False, verbose_name="محذوف", db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحذف")
    deleted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_deleted",
        verbose_name="حذف بواسطة",
    )

    # Use the soft delete manager by default
    objects = SoftDeleteManager()
    # Access all objects (including deleted) via all_objects
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(
        self, using=None, keep_parents=False, cascade=False, deleted_by_user=None
    ):
        """
        Soft delete the object.
        Renames unique fields to allow reuse of the identifier.
        Cascades to related objects if cascade=True.

        Args:
            deleted_by_user: User instance who performed the deletion (optional).
                             If not provided, auto-detects from CurrentUserMiddleware.
        """
        if self.is_deleted:
            return  # Already deleted

        # Auto-detect current user if not explicitly provided
        if deleted_by_user is None:
            try:
                from accounts.middleware.current_user import get_current_user
                current_user = get_current_user()
                if current_user and hasattr(current_user, 'pk') and current_user.pk:
                    deleted_by_user = current_user
            except Exception:
                pass

        with transaction.atomic():
            deletion_time = timezone.now()

            # Cascade delete to related objects FIRST (before deleting self)
            if cascade:
                # Collect all related objects for bulk update
                related_objects = self._get_related_objects()

                # Group by model type for bulk update
                from collections import defaultdict

                objects_by_model = defaultdict(list)

                for related_obj in related_objects:
                    if (
                        hasattr(related_obj, "is_deleted")
                        and not related_obj.is_deleted
                    ):
                        objects_by_model[type(related_obj)].append(related_obj)

                # Bulk update each model type (FAST - single query per model)
                for model_class, objects in objects_by_model.items():
                    if objects:
                        # Get PKs for bulk update
                        pks = [obj.pk for obj in objects]

                        # Bulk update is_deleted, deleted_at, and deleted_by
                        update_fields = {
                            "is_deleted": True,
                            "deleted_at": deletion_time,
                        }
                        if deleted_by_user and hasattr(model_class, "deleted_by"):
                            update_fields["deleted_by"] = deleted_by_user

                        model_class.all_objects.filter(pk__in=pks).update(
                            **update_fields
                        )

            # Now delete self (with unique field scrambling)
            self.is_deleted = True
            self.deleted_at = deletion_time
            if deleted_by_user:
                self.deleted_by = deleted_by_user

            # Handle unique constraints for parent object only
            self._scramble_unique_fields()

            self.save(using=using)

    def hard_delete(self, using=None, keep_parents=False):
        """
        Permanently delete the object from the database.
        """
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self, cascade=False):
        """
        Restore the soft-deleted object.
        Handles checking for conflicts with existing active objects.
        Cascades to related objects if cascade=True.
        """
        if not self.is_deleted:
            return

        with transaction.atomic():
            # Attempt to restore unique fields
            self._restore_unique_fields()

            self.is_deleted = False
            deleted_time = self.deleted_at
            self.deleted_at = None
            self.save()

            # Cascade restore to related objects that were deleted at the same time
            if cascade and deleted_time:
                for related_obj in self._get_related_objects():
                    if hasattr(related_obj, "restore") and hasattr(
                        related_obj, "is_deleted"
                    ):
                        if related_obj.is_deleted and related_obj.deleted_at:
                            # Restore if deleted within 1 second of parent (same cascade operation)
                            time_diff = abs(
                                (related_obj.deleted_at - deleted_time).total_seconds()
                            )
                            if (
                                time_diff < 10
                            ):  # 10 second tolerance for cascade operations
                                related_obj.restore(cascade=True)

    def _get_related_objects(self):
        """
        Get all related objects that should be cascade deleted/restored.
        Returns a list of related model instances.
        """
        related_objects = []

        # Iterate through all related fields
        for related in self._meta.related_objects:
            # Get the accessor name (e.g., 'manufacturing_orders')
            accessor_name = related.get_accessor_name()

            # Skip if accessor doesn't exist
            if not hasattr(self, accessor_name):
                continue

            try:
                # Get the related manager
                related_manager = getattr(self, accessor_name)

                # CRITICAL: Always use all_objects to get ALL related objects
                # including those that might be filtered by default manager
                if hasattr(related_manager.model, "all_objects"):
                    # Use all_objects manager to bypass any default filtering
                    related_queryset = related_manager.model.all_objects.filter(
                        **{related.field.name: self}
                    )
                else:
                    # Fallback to regular manager
                    related_queryset = related_manager.all()

                # Add to list
                for obj in related_queryset:
                    # Only cascade to objects with SoftDeleteMixin
                    if isinstance(obj, SoftDeleteMixin):
                        related_objects.append(obj)
            except Exception as e:
                # Log but don't fail if we can't access a relation
                logger.debug(
                    f"Could not access related objects via {accessor_name}: {e}"
                )
                continue

        return related_objects

    def _get_unique_fields(self):
        """
        Identify fields that have unique=True or are part of unique_together.
        Returns a list of field names.
        """
        unique_fields = []
        # Check single unique fields
        for field in self._meta.fields:
            if field.unique and not field.primary_key:
                unique_fields.append(field.name)

        # We handle unique_together by treating them individually for now,
        # scrambling one of them is usually enough to break the unique constraint of the tuple.
        # But for robustness, we can look at specific important fields like 'code', 'order_number'.
        return unique_fields

    def _scramble_unique_fields(self):
        """
        Appends a suffix to unique fields to free them up.
        """
        suffix = f"_DEL_{int(timezone.now().timestamp())}"
        unique_fields = self._get_unique_fields()

        for field_name in unique_fields:
            current_value = getattr(self, field_name)
            if not current_value:
                continue

            # Convert to string to append suffix
            new_value = f"{str(current_value)}{suffix}"

            # Truncate if necessary (though hopefully unique fields have room)
            max_length = self._meta.get_field(field_name).max_length
            if max_length and len(new_value) > max_length:
                # If too long, use a shorter random suffix
                short_suffix = f"_D{uuid.uuid4().hex[:4]}"
                new_value = (
                    f"{str(current_value)[:max_length-len(short_suffix)]}{short_suffix}"
                )

            setattr(self, field_name, new_value)

    def _restore_unique_fields(self):
        """
        Attempts to remove the _DEL_ suffix.
        If the original value is taken, assigns a new unique value.
        """
        unique_fields = self._get_unique_fields()

        for field_name in unique_fields:
            current_value = getattr(self, field_name)
            if not current_value or "_DEL_" not in str(current_value):
                continue

            # Extract original value (everything before the last _DEL_)
            original_value = str(current_value).split("_DEL_")[0]

            # Check if this original value is currently in use by an ACTIVE object
            ModelClass = self.__class__

            # Build query to check existence, excluding self
            query = Q(**{field_name: original_value}) & Q(is_deleted=False)
            if ModelClass.objects.filter(query).exists():
                # Conflict detected!
                new_value = self._resolve_conflict(field_name, original_value)
                setattr(self, field_name, new_value)
            else:
                # No conflict, restore original
                setattr(self, field_name, original_value)

    def _resolve_conflict(self, field_name, original_value):
        """
        Generate a new unique value when restoration finds a conflict.
        Example: CODE -> CODE_RESTORED_123
        """
        suffix = f"_RES_{uuid.uuid4().hex[:6]}"
        new_value = f"{original_value}{suffix}"

        # Check max length
        max_length = self._meta.get_field(field_name).max_length
        if max_length and len(new_value) > max_length:
            # Try to keep as much of original as possible
            allowed_len = max_length - len(suffix)
            new_value = f"{original_value[:allowed_len]}{suffix}"

        return new_value
