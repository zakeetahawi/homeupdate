from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone


class DashboardFilterMixin:
    """
    Mixin to apply common dashboard filters to QuerySets.
    Filters: date_range, branch, salesperson.
    """

    def apply_filters(
        self,
        queryset,
        date_field="created_at",
        branch_field="branch",
        salesperson_field="salesperson",
    ):
        request = self.request

        # 1. Date Range Filter
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        if date_from:
            try:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                queryset = queryset.filter(
                    **{f"{date_field}__gte": timezone.make_aware(dt_from)}
                )
            except (ValueError, TypeError):
                pass

        if date_to:
            try:
                dt_to = datetime.strptime(date_to, "%Y-%m-%d")
                # Make it end of day
                dt_to = dt_to.replace(hour=23, minute=59, second=59)
                queryset = queryset.filter(
                    **{f"{date_field}__lte": timezone.make_aware(dt_to)}
                )
            except (ValueError, TypeError):
                pass

        # 2. Branch Filter
        branch_id = request.GET.get("branch_id")
        if branch_id and branch_id != "all":
            # Handle empty branch_field (for models that don't support branch filtering)
            if branch_field:
                queryset = queryset.filter(**{f"{branch_field}_id": branch_id})

        # 3. Salesperson Filter (Inclusive: User OR Salesperson Profile)
        salesperson_id = request.GET.get("salesperson_id")
        if salesperson_id and salesperson_id != "all":
            if salesperson_field == "created_by":
                # Special handling for inclusive filtering on Order model
                # We want: (created_by = User) OR (salesperson__user = User)
                # The ID passed here is the User ID (from requested filter)
                # print(f"DEBUG: Inclusive filter applied for ID: {salesperson_id}")
                queryset = queryset.filter(
                    Q(created_by_id=salesperson_id)
                    | Q(salesperson__user_id=salesperson_id)
                )
                # print(f"DEBUG: Inclusive result count: {queryset.count()}")
            elif salesperson_field:
                # Fallback for other models or explicit field usage
                queryset = queryset.filter(
                    **{f"{salesperson_field}_id": salesperson_id}
                )

        return queryset

    def get_date_range(self):
        """Returns (start_date, end_date) based on request or defaults to current month."""
        now = timezone.now()
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        start = now.replace(day=1, hour=0, minute=0, second=0)
        end = now

        if not date_from and not date_to:
            # Default: All Time (From generous past date)
            start = timezone.make_aware(datetime(2020, 1, 1))
            end = now

        if date_from:
            try:
                start = timezone.make_aware(datetime.strptime(date_from, "%Y-%m-%d"))
            except Exception:
                pass

        if date_to:
            try:
                end = timezone.make_aware(
                    datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59)
                )
            except Exception:
                pass

        return start, end
