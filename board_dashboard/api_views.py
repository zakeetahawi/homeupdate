from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from accounting.models import Transaction
from accounts.models import User
from cutting.models import CuttingOrderItem
from orders.models import Order, OrderItem
from user_activity.models import UserSession

from .mixins_api import DashboardFilterMixin
from .permissions import IsBoardMember


class BoardRevenueAPIView(APIView, DashboardFilterMixin):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsBoardMember]

    def get(self, request):
        # Base QuerySet: All orders except cancelled/rejected (Booking Value)
        base_qs = Order.objects.exclude(status__in=["cancelled", "rejected"])

        # Apply common filters
        base_qs = self.apply_filters(
            base_qs, branch_field="branch", salesperson_field="created_by"
        )

        # 1. Current Period Metrics
        start_date, end_date = self.get_date_range()
        current_qs = base_qs.filter(
            created_at__gte=start_date, created_at__lte=end_date
        )

        # Total Revenue (Booking Value)
        current_revenue = current_qs.aggregate(total=Sum("total_amount"))[
            "total"
        ] or Decimal("0.00")

        # Net Income (Cash Collected = Paid Amount)
        current_net_income = current_qs.aggregate(total=Sum("paid_amount"))[
            "total"
        ] or Decimal("0.00")

        # Total Debt (For consistency check in UI if needed, though UI uses Finance API for debt)
        current_debt = current_revenue - current_net_income

        # Total Credit (Overpayments from orders in this period)
        # Orders where paid > total
        credit_qs = current_qs.filter(paid_amount__gt=F("total_amount"))
        current_credit = credit_qs.aggregate(
            total=Sum(F("paid_amount") - F("total_amount"))
        )["total"] or Decimal("0.00")

        # 2. Previous Period (flexible based on compare_mode)
        compare_mode = request.GET.get("compare_mode", "period")  # 'period' or 'year'

        if compare_mode == "year":
            # Compare with same period last year
            try:
                # subtract 365 days (simple approximation, accurate enough for business dashboard)
                prev_end = end_date - timedelta(days=365)
                prev_start = start_date - timedelta(days=365)
            except:
                # fallback
                prev_end = start_date - timedelta(seconds=1)
                prev_start = prev_end - (end_date - start_date)
        else:
            # Default: Previous Period (Month-over-Month / Period-over-Period)
            duration = end_date - start_date
            prev_end = start_date - timedelta(seconds=1)
            prev_start = prev_end - duration

        prev_qs = base_qs.filter(created_at__gte=prev_start, created_at__lte=prev_end)
        prev_revenue = prev_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal(
            "0.00"
        )

        # 3. Growth Rate (Revenue)
        if prev_revenue > 0:
            growth_rate = ((current_revenue - prev_revenue) / prev_revenue) * 100
        else:
            growth_rate = 100 if current_revenue > 0 else 0

        # 4. Forecast (Simple Moving Average of last 3 months)
        forecast_qs = Order.objects.exclude(status__in=["cancelled", "rejected"])

        branch_id = request.GET.get("branch_id")
        if branch_id and branch_id != "all":
            forecast_qs = forecast_qs.filter(branch_id=branch_id)

        now = timezone.now()
        cur_month_start = now.replace(day=1, hour=0, minute=0, second=0)

        # Manual filtering for chart history (all time) - extending existing forecast_qs
        chart_qs = forecast_qs  # Start with branch filter applied above

        sp_id = request.GET.get("salesperson_id")
        if sp_id and sp_id != "all":
            chart_qs = chart_qs.filter(salesperson__user_id=sp_id)

        history_data = (
            chart_qs.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Sum("total_amount"))
            .order_by("month")
        )

        chart_labels = []
        chart_values = []

        for entry in history_data:
            if entry["month"]:
                chart_labels.append(entry["month"].strftime("%Y-%m"))
                chart_values.append(float(entry["total"]))

        # Simple forecast: Average of last 3 months
        if chart_values:
            vals = chart_values[-3:]
            forecast_val = sum(vals) / len(vals)
        else:
            forecast_val = 0

        forecast = forecast_val

        # Weights: 0.5, 0.3, 0.2
        # Old logic removed

        # 5. Branch Breakdown (Revenue by Branch)
        branch_breakdown = (
            current_qs.values("branch__name")
            .annotate(total=Sum("total_amount"))
            .order_by("-total")
        )

        return Response(
            {
                "current_revenue": float(current_revenue),  # Booking Value
                "net_income": float(current_net_income),  # Cash Collected
                "total_debt": float(current_debt),
                "total_credit": float(current_credit),  # Overpayments
                "previous_revenue": float(prev_revenue),
                "growth_rate": round(float(growth_rate), 2),
                "forecast_next_month": float(round(forecast, 2)),
                "chart_labels": chart_labels,
                "chart_values": chart_values,
                "branch_breakdown": list(branch_breakdown),
                "period_label": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            }
        )


class BoardInventoryAPIView(APIView, DashboardFilterMixin):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsBoardMember]

    def get(self, request):
        start_date, end_date = self.get_date_range()
        queryset = OrderItem.objects.all()
        queryset = self.apply_filters(
            queryset,
            date_field="order__created_at",
            branch_field="order__branch",
            salesperson_field="order__created_by",
        )

        # 1.1 Warehouse Filter (Specific to Inventory Panel)
        warehouse_ids = request.GET.getlist("warehouse_id")
        if warehouse_ids and "all" not in warehouse_ids:
            # Filter matches if:
            # (A) Order's Branch is linked to Warehouse OR
            # (B) Item is assigned to a Cutting Order at that Warehouse
            queryset = queryset.filter(
                Q(order__branch__warehouses__id__in=warehouse_ids)
                | Q(cutting_items__cutting_order__warehouse__id__in=warehouse_ids)
            ).distinct()

        # 1. Total Output (Meters)
        total_output = queryset.aggregate(total=Sum("quantity"))["total"] or 0

        # 2. Granular Tracking (By Branch) - Disabled for now as unused in UI and source of 500 errors
        warehouse_stats = []

        # 3. Product Demand (Top 10 Products by Cut Volume)
        product_demand = (
            queryset.filter(product__isnull=False)
            .values("product__name")
            .annotate(total=Sum("quantity"))
            .order_by("-total")[:10]
        )

        # 4. Cutting Point Breakdown (If applicable, mapped via warehouse or section)
        # Assuming warehouse represents the physical location/point

        # 5. Period Comparison
        compare_mode = request.GET.get("compare_mode", "period")
        if compare_mode == "year":
            prev_end = end_date - timedelta(days=365)
            prev_start = start_date - timedelta(days=365)
        else:
            duration = end_date - start_date
            prev_end = start_date - timedelta(days=1)
            prev_start = prev_end - duration

        prev_output = (
            OrderItem.objects.filter(
                order__created_at__gte=prev_start,
                order__created_at__lte=prev_end,
            ).aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        output_growth = 0
        if prev_output > 0:
            output_growth = ((total_output - prev_output) / prev_output) * 100

        return Response(
            {
                "total_output_meters": float(total_output),
                "prev_output_meters": float(prev_output),
                "output_growth": round(float(output_growth), 1),
                "warehouse_stats": list(warehouse_stats),
                "product_demand": list(product_demand),
            }
        )


class BoardStaffAPIView(APIView, DashboardFilterMixin):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsBoardMember]

    def get(self, request):
        start_date, end_date = self.get_date_range()

        # Base filter for Activity/Orders
        # 1. Order Creation Volume (exclude cancelled/rejected like Revenue API)
        orders_qs = Order.objects.exclude(
            status__in=["cancelled", "rejected"]
        ).filter(
            created_at__gte=start_date, created_at__lte=end_date
        )
        orders_qs = self.apply_filters(
            orders_qs, branch_field="branch", salesperson_field="created_by"
        )

        top_creators = (
            orders_qs.values("created_by__username")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        # 2. System Engagement
        # UserSession filtering is trickier with branch/salesperson filters if not directly linked
        # We'll filter by users who are active in the filtered set of orders if specific filters applied
        active_users_qs = UserSession.objects.filter(
            login_time__gte=start_date, last_activity__isnull=False
        )
        # If branch filter is applied, we might want to filter users by department/branch
        # For simplicity, we keep system engagement global unless strongly required contextually

        engagement = (
            active_users_qs.annotate(
                duration=ExpressionWrapper(
                    F("last_activity") - F("login_time"), output_field=DurationField()
                )
            )
            .values("user__username")
            .annotate(total_duration=Sum("duration"), session_count=Count("id"))
            .order_by("-total_duration")[:5]
        )

        formatted_engagement = []
        for item in engagement:
            total_seconds = (
                item["total_duration"].total_seconds() if item["total_duration"] else 0
            )
            formatted_engagement.append(
                {
                    "username": item["user__username"],
                    "hours": round(total_seconds / 3600, 1),
                    "sessions": item["session_count"],
                }
            )

        # 3. Top Performer (Weighted Score)
        # Score = (Revenue * 0.4) + (Volume * 0.3) + (Closures * 0.3)
        # This requires aggregation per user.
        # We fetch aggregate data and calculate in python for flexibility

        # Get metrics per user
        # 3. Top Performer (Ranking & Breakdown)
        # Check if we are filtering by a specific salesperson (User ID)
        salesperson_filter = request.GET.get("salesperson_id")

        if salesperson_filter and salesperson_filter != "all":
            # If filtering by specific user, we want to show THEIR aggregate performance
            # encompassing all orders (created by them OR assigned to them)
            # as returned by the inclusive filter in mixin.

            # Aggregate everything into one result
            agg_data = orders_qs.aggregate(
                revenue=Sum("total_amount"), volume=Count("id")
            )

            # Fetch the user details for display
            from accounts.models import User

            try:
                target_user = User.objects.get(id=salesperson_filter)
                username = target_user.username
                is_wholesale = target_user.is_wholesale
                is_retail = target_user.is_retail
            except User.DoesNotExist:
                username = "Unknown"
                is_wholesale = False
                is_retail = True

            # Construct a single metric item mimicking the values() structure
            user_metrics = [
                {
                    "created_by__username": username,
                    "created_by__is_wholesale": is_wholesale,
                    "created_by__is_retail": is_retail,
                    "revenue": agg_data["revenue"] or 0,
                    "volume": agg_data["volume"] or 0,
                }
            ]
        else:
            # Default behavior: Group by creator
            user_metrics = (
                orders_qs.values(
                    "created_by__username",
                    "created_by__is_wholesale",
                    "created_by__is_retail",
                )
                .annotate(revenue=Sum("total_amount"), volume=Count("id"))
                .order_by("-revenue")
            )

        # Order type mapping for selected_types JSON field
        ORDER_TYPE_NAMES = {
            "installation": "تركيب",
            "inspection": "معاينة",
            "tailoring": "تسليم",
            "products": "منتجات",
        }

        ranked_performers = []
        for item in user_metrics[:5]:  # Process top 5
            username = item["created_by__username"]
            if not username:  # Skip if no user
                continue
            revenue = float(item["revenue"] or 0)
            volume = item["volume"]
            is_wholesale = item.get("created_by__is_wholesale", False)

            # Build order type breakdown from selected_types (JSON field)
            user_orders = orders_qs.filter(created_by__username=username)
            type_counts = {}
            for order in user_orders.values_list("selected_types", "order_type"):
                sel_types = order[0]  # selected_types JSON
                old_type = order[1]   # legacy order_type
                if sel_types and isinstance(sel_types, list) and len(sel_types) > 0:
                    for st in sel_types:
                        label = ORDER_TYPE_NAMES.get(st, st)
                        type_counts[label] = type_counts.get(label, 0) + 1
                elif old_type:
                    # Fallback to old order_type field
                    label = "منتج" if old_type == "product" else "خدمة" if old_type == "service" else old_type
                    type_counts[label] = type_counts.get(label, 0) + 1
                else:
                    type_counts["غير محدد"] = type_counts.get("غير محدد", 0) + 1

            ranked_performers.append(
                {
                    "username": username,
                    "revenue": revenue,
                    "volume": volume,
                    "retail_breakdown": type_counts,
                    "score": revenue,
                }
            )

        # Global order type distribution (all orders in period)
        all_type_counts = {}
        for sel_types, old_type in orders_qs.values_list("selected_types", "order_type"):
            if sel_types and isinstance(sel_types, list) and len(sel_types) > 0:
                for st in sel_types:
                    label = ORDER_TYPE_NAMES.get(st, st)
                    all_type_counts[label] = all_type_counts.get(label, 0) + 1
            elif old_type:
                label = "منتج" if old_type == "product" else "خدمة" if old_type == "service" else old_type
                all_type_counts[label] = all_type_counts.get(label, 0) + 1
            else:
                all_type_counts["غير محدد"] = all_type_counts.get("غير محدد", 0) + 1

        top_user = ranked_performers[0] if ranked_performers else None

        # Total orders count
        total_orders_count = orders_qs.count()

        return Response(
            {
                "top_creators": list(top_creators),
                "engagement": formatted_engagement,
                "top_performer": top_user,
                "leaderboard": ranked_performers[:5],  # Return Top 5
                "order_type_distribution": all_type_counts,
                "total_orders_count": total_orders_count,
            }
        )


class BoardFinanceAPIView(APIView, DashboardFilterMixin):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsBoardMember]

    def get(self, request):
        # 1. Outstanding Debts - ALWAYS from start of current year (not filtered by date range)
        # This gives the true total outstanding debt picture
        year_start = timezone.make_aware(datetime(timezone.now().year, 1, 1))

        start_date, end_date = self.get_date_range()

        debt_qs = Order.objects.filter(
            paid_amount__lt=F("total_amount"),
            created_at__gte=year_start,
        ).exclude(status__in=["cancelled", "rejected"])

        debt_qs = self.apply_filters(
            debt_qs, branch_field="branch", salesperson_field="created_by"
        )

        outstanding = (
            debt_qs.aggregate(total_debt=Sum(F("total_amount") - F("paid_amount")))[
                "total_debt"
            ]
            or 0
        )

        # 2. Debt by User (Top 5)
        debt_by_user = (
            debt_qs.values("customer__name")
            .annotate(debt=Sum(F("total_amount") - F("paid_amount")))
            .order_by("-debt")[:5]
        )

        # 3. Payment Efficiency (Fast Payers)
        # Orders closed within 3 days and fully paid
        start_date, end_date = self.get_date_range()
        efficiency_qs = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            paid_amount__gte=F("total_amount"),
        )
        efficiency_qs = self.apply_filters(
            efficiency_qs, branch_field="branch", salesperson_field="created_by"
        )

        # Fast closure: updated_at (or completed_at if exists) <= created_at + 3 days
        # Since we don't have simplified duration field easily in DB without expression,
        # we check logic: updated_at <= created_at + 3 days
        fast_closures = efficiency_qs.filter(
            updated_at__lte=F("created_at") + timedelta(days=3)
        ).count()

        total_closed = efficiency_qs.count()
        efficiency_rate = (
            (fast_closures / total_closed * 100) if total_closed > 0 else 0
        )

        # Calculate remaining debtors (orders with outstanding debt)
        remaining_debtors_count = debt_qs.count()

        # Debt aging breakdown
        now = timezone.now()
        debt_0_30 = debt_qs.filter(created_at__gte=now - timedelta(days=30)).aggregate(
            total=Sum(F("total_amount") - F("paid_amount"))
        )["total"] or 0
        debt_31_60 = debt_qs.filter(
            created_at__lt=now - timedelta(days=30),
            created_at__gte=now - timedelta(days=60),
        ).aggregate(total=Sum(F("total_amount") - F("paid_amount")))["total"] or 0
        debt_61_90 = debt_qs.filter(
            created_at__lt=now - timedelta(days=60),
            created_at__gte=now - timedelta(days=90),
        ).aggregate(total=Sum(F("total_amount") - F("paid_amount")))["total"] or 0
        debt_over_90 = debt_qs.filter(
            created_at__lt=now - timedelta(days=90),
        ).aggregate(total=Sum(F("total_amount") - F("paid_amount")))["total"] or 0

        return Response(
            {
                "total_outstanding_debt": float(outstanding),
                "top_debtors": list(debt_by_user),
                "fast_closures_count": fast_closures,
                "efficiency_rate": round(efficiency_rate, 1),
                "remaining_debtors_count": remaining_debtors_count,
                "debt_aging": {
                    "0_30": float(debt_0_30),
                    "31_60": float(debt_31_60),
                    "61_90": float(debt_61_90),
                    "over_90": float(debt_over_90),
                },
            }
        )
