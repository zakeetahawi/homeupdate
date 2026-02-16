from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _


class SoftDeleteAdminMixin:
    """
    Mixin for ModelAdmin to handle Soft Deleted items.
    Adds:
    - 'is_deleted' list_filter.
    - Actions: Restore, Hard Delete.
    - Uses all_objects manager to show deleted items.
    """

    def get_queryset(self, request):
        # Use the manager that includes deleted items
        qs = self.model.all_objects.get_queryset()

        # If is_deleted filter is NOT present in GET params, show only active (non-deleted) items by default
        # This prevents deleted items from cluttering the main list view unless specifically requested
        if "is_deleted__exact" not in request.GET:
            qs = qs.filter(is_deleted=False)

        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def get_list_filter(self, request):
        # Add 'is_deleted' to existing list_filter
        existing = list(super().get_list_filter(request) or [])
        if "is_deleted" not in existing:
            existing.append("is_deleted")
        return tuple(existing)

    def get_list_display(self, request):
        # Add 'deleted_status' to list_display
        existing = list(super().get_list_display(request) or [])
        if "deleted_status" not in existing:
            existing.insert(0, "deleted_status")
        return tuple(existing)

    def get_readonly_fields(self, request, obj=None):
        """Make all fields read-only if the object is soft-deleted."""
        readonly = super().get_readonly_fields(request, obj) or ()
        if obj and getattr(obj, "is_deleted", False):
            # If object is deleted, make ALL fields read-only
            return readonly + tuple(f.name for f in self.model._meta.fields)
        return readonly

    def has_change_permission(self, request, obj=None):
        """Disable change permission for deleted items (makes them read-only view)."""
        if obj and getattr(obj, "is_deleted", False):
            return False
        return super().has_change_permission(request, obj)

    def has_view_permission(self, request, obj=None):
        """Allow viewing deleted items."""
        if obj and getattr(obj, "is_deleted", False):
            return True
        return super().has_view_permission(request, obj)

    def deleted_status(self, obj):
        """Visual indicator for deleted items"""
        if getattr(obj, "is_deleted", False):
            from django.utils.safestring import mark_safe

            return mark_safe(
                '<span style="background-color: #dc3545; color: white; padding: 3px 6px; border-radius: 4px; font-size: 11px;">محذوف</span>'
            )
        return ""

    deleted_status.short_description = "حالة"

    @admin.action(description=_("استعادة العناصر المحددة (Restore)"))
    def restore_selected(self, request, queryset):
        restored_count = 0

        for obj in queryset:
            if hasattr(obj, "restore"):
                obj.restore(cascade=False)  # Regular restore without cascade
                restored_count += 1

        self.message_user(
            request, _(f"تم استعادة {restored_count} عنصر بنجاح."), messages.SUCCESS
        )

    @admin.action(description=_("استعادة متسلسلة (Cascade Restore)"))
    def cascade_restore_selected(self, request, queryset):
        """
        Cascade restore selected items and all related objects.
        """
        restored_count = 0
        related_count = 0

        for obj in queryset:
            if hasattr(obj, "restore"):
                # Count related objects before restoring
                if hasattr(obj, "_get_related_objects"):
                    related_objs = obj._get_related_objects()
                    # Count only deleted related objects
                    related_count += sum(
                        1
                        for r in related_objs
                        if hasattr(r, "is_deleted") and r.is_deleted
                    )

                obj.restore(cascade=True)
                restored_count += 1

        self.message_user(
            request,
            _(
                f"تم استعادة {restored_count} عنصر و {related_count} عنصر مرتبط بشكل متسلسل."
            ),
            messages.SUCCESS,
        )

    @admin.action(description=_("حذف متسلسل (Cascade Delete)"))
    def cascade_delete_selected(self, request, queryset):
        """
        Cascade delete selected items and all related objects.
        WARNING: This will delete many related objects!
        """
        deleted_count = 0
        related_count = 0

        for obj in queryset:
            if hasattr(obj, "delete"):
                # Count related objects before deleting
                if hasattr(obj, "_get_related_objects"):
                    related_count += len(obj._get_related_objects())

                # Delete with cascade=True
                obj.delete(cascade=True)
                deleted_count += 1

        self.message_user(
            request,
            _(f"تم حذف {deleted_count} عنصر و {related_count} عنصر مرتبط بشكل متسلسل."),
            messages.WARNING,
        )

    @admin.action(description=_("حذف نهائي للعناصر المحددة (Hard Delete)"))
    def hard_delete_selected(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(
                request, _("عذراً، الحذف النهائي متاح للمدير العام فقط."), messages.ERROR
            )
            return

        deleted_count = 0
        for obj in queryset:
            try:
                from django.db import transaction as db_transaction
                with db_transaction.atomic():
                    self._hard_delete_cascade(obj)
                    deleted_count += 1
            except Exception as e:
                self.message_user(
                    request, _(f"خطأ في حذف {obj}: {e}"), messages.ERROR
                )

        self.message_user(
            request, _(f"تم حذف {deleted_count} عنصر بشكل نهائي."), messages.WARNING
        )

    @staticmethod
    def _hard_delete_cascade(obj):
        """
        حذف نهائي متسلسل: يحذف العنصر وكل العلاقات المرتبطة من قاعدة البيانات.
        يعطّل فحص FK مؤقتاً ثم يحذف كل شيء بأمان.
        """
        from django.db import connection

        # جمع كل الكائنات المرتبطة للحذف (من الأعمق للأعلى)
        to_delete = []
        SoftDeleteAdminMixin._collect_for_hard_delete(obj, to_delete, set())

        with connection.cursor() as cursor:
            # تعطيل فحص المفاتيح الأجنبية مؤقتاً
            if connection.vendor == 'mysql':
                cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
            elif connection.vendor == 'postgresql':
                cursor.execute('SET CONSTRAINTS ALL DEFERRED')

            try:
                # حذف من الأعمق للأعلى
                for del_obj in to_delete:
                    table = del_obj._meta.db_table
                    pk_col = del_obj._meta.pk.column
                    cursor.execute(
                        f'DELETE FROM {connection.ops.quote_name(table)} '
                        f'WHERE {connection.ops.quote_name(pk_col)} = %s',
                        [del_obj.pk]
                    )
            finally:
                # إعادة تفعيل فحص المفاتيح الأجنبية
                if connection.vendor == 'mysql':
                    cursor.execute('SET FOREIGN_KEY_CHECKS = 1')

    @staticmethod
    def _collect_for_hard_delete(obj, to_delete, visited):
        """
        جمع العنصر وكل العلاقات المرتبطة به بشكل متسلسل.
        يبني قائمة مرتبة من الأعمق (الأبناء) للأعلى (الأب).
        """
        obj_key = (type(obj).__name__, obj.pk)
        if obj_key in visited:
            return
        visited.add(obj_key)

        # أولاً: نجمع الأبناء (العلاقات المرتبطة)
        for related in obj._meta.related_objects:
            accessor = related.get_accessor_name()
            if not hasattr(obj, accessor):
                continue
            try:
                related_model = related.related_model
                manager = getattr(related_model, 'all_objects', related_model.objects)
                related_objs = list(manager.filter(**{related.field.name: obj}))
                for related_obj in related_objs:
                    SoftDeleteAdminMixin._collect_for_hard_delete(related_obj, to_delete, visited)
            except Exception:
                continue

        # ثانياً: نضيف العنصر نفسه (بعد أبنائه)
        to_delete.append(obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Add our custom actions
        if "restore_selected" not in actions:
            actions["restore_selected"] = (
                self.restore_selected.__func__,
                "restore_selected",
                _("استعادة العناصر المحددة (Restore)"),
            )
        if "cascade_restore_selected" not in actions:
            actions["cascade_restore_selected"] = (
                self.cascade_restore_selected.__func__,
                "cascade_restore_selected",
                _("استعادة متسلسلة (Cascade Restore)"),
            )
        if "cascade_delete_selected" not in actions:
            actions["cascade_delete_selected"] = (
                self.cascade_delete_selected.__func__,
                "cascade_delete_selected",
                _("حذف متسلسل (Cascade Delete)"),
            )
        if "hard_delete_selected" not in actions:
            actions["hard_delete_selected"] = (
                self.hard_delete_selected.__func__,
                "hard_delete_selected",
                _("حذف نهائي للعناصر المحددة (Hard Delete)"),
            )
        return actions
