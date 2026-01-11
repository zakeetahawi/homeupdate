from datetime import timedelta

import numpy as np
from django.db.models import Avg, Count, F, Sum, Window
from django.db.models.functions import ExtractHour, TruncDay, TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from sklearn.linear_model import LinearRegression

from customers.models import Customer
from orders.models import Order, OrderItem

from .models import Report


def get_date_range_filter(date_range):
    """تحديد نطاق التاريخ للتحليل"""
    now = timezone.now()
    if date_range == "custom":
        # يمكن إضافة منطق مخصص هنا
        return now - timedelta(days=30)
    return now - timedelta(days=int(date_range))


def get_grouping_function(group_by):
    """تحديد دالة التجميع المناسبة"""
    grouping = {
        "day": TruncDay,
        "week": TruncWeek,
        "month": TruncMonth,
        "quarter": lambda field: TruncMonth(field, quarter=True),
    }
    return grouping.get(group_by, TruncMonth)


def calculate_predictions(historical_data, periods=3):
    """حساب التنبؤات باستخدام الانحدار الخطي"""
    if len(historical_data) < 2:
        return []

    X = np.array(range(len(historical_data))).reshape(-1, 1)
    y = np.array(historical_data)

    model = LinearRegression()
    model.fit(X, y)

    future_X = np.array(
        range(len(historical_data), len(historical_data) + periods)
    ).reshape(-1, 1)
    predictions = model.predict(future_X)

    return predictions.tolist()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_analytics_data(request):
    """جلب بيانات التحليلات حسب المعايير المحددة"""
    date_range = request.GET.get("dateRange", "30")
    group_by = request.GET.get("groupBy", "month")
    analysis_type = request.GET.get("analysisType", "trend")

    start_date = get_date_range_filter(date_range)
    group_func = get_grouping_function(group_by)

    # تحليل المبيعات
    orders = Order.objects.filter(created_at__gte=start_date)
    sales_data = (
        orders.annotate(period=group_func("created_at"))
        .values("period")
        .annotate(
            total_sales=Sum("total_amount"),
            order_count=Count("id"),
            avg_order_value=Avg("total_amount"),
        )
        .order_by("period")
    )

    historical_sales = [item["total_sales"] for item in sales_data]
    sales_predictions = calculate_predictions(historical_sales)

    # تحليل العملاء
    customer_data = Customer.objects.filter(
        customer_orders__created_at__gte=start_date
    ).annotate(
        total_orders=Count("customer_orders"),
        total_spent=Sum("customer_orders__total_amount"),
        avg_order_value=Avg("customer_orders__total_amount"),
        last_order_date=Max("customer_orders__created_at"),
    )

    # تحليل التدفق النقدي
    cash_flow = (
        orders.annotate(period=group_func("created_at"))
        .values("period")
        .annotate(
            inflow=Sum("total_amount"),
            outflow=Sum("costs"),
            net_flow=F("inflow") - F("outflow"),
        )
        .order_by("period")
    )

    return Response(
        {
            "sales_analysis": {
                "trends": list(sales_data),
                "predictions": [
                    {
                        "period": (timezone.now() + timedelta(days=30 * i)).strftime(
                            "%Y-%m"
                        ),
                        "value": val,
                    }
                    for i, val in enumerate(sales_predictions)
                ],
                "total_revenue": orders.aggregate(Sum("total_amount"))[
                    "total_amount__sum"
                ]
                or 0,
                "total_orders": orders.count(),
                "avg_order_value": orders.aggregate(Avg("total_amount"))[
                    "total_amount__avg"
                ]
                or 0,
            },
            "customer_insights": {
                "total_customers": customer_data.count(),
                "new_customers": customer_data.filter(
                    created_at__gte=start_date
                ).count(),
                "segments": analyze_customer_segments(customer_data),
                "top_customers": list(
                    customer_data.order_by("-total_spent")[:10].values(
                        "name", "total_orders", "total_spent", "avg_order_value"
                    )
                ),
            },
            "financial_health": {
                "cash_flow": list(cash_flow),
                "revenue_growth": calculate_growth(historical_sales),
                "next_quarter_forecast": (
                    sales_predictions[0] if sales_predictions else 0
                ),
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_kpi_details(request, kpi_type):
    """جلب تفاصيل مؤشر أداء محدد"""
    start_date = timezone.now() - timedelta(days=365)

    if kpi_type == "sales":
        data = (
            Order.objects.filter(created_at__gte=start_date)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total_sales=Sum("total_amount"), order_count=Count("id"))
            .order_by("month")
        )

        return Response(
            {
                "title": "تحليل نمو المبيعات",
                "data": list(data),
                "metrics": {
                    "total_growth": calculate_growth([d["total_sales"] for d in data]),
                    "avg_monthly_growth": calculate_average_growth(
                        [d["total_sales"] for d in data]
                    ),
                },
            }
        )

    elif kpi_type == "retention":
        monthly_retention = []
        for i in range(12):
            month_start = timezone.now() - timedelta(days=30 * (i + 1))
            month_end = timezone.now() - timedelta(days=30 * i)

            previous_customers = Customer.objects.filter(
                customer_orders__created_at__lt=month_start
            ).distinct()

            retained_customers = (
                previous_customers.filter(
                    customer_orders__created_at__range=[month_start, month_end]
                )
                .distinct()
                .count()
            )

            if previous_customers.count() > 0:
                retention_rate = (retained_customers / previous_customers.count()) * 100
            else:
                retention_rate = 0

            monthly_retention.append(
                {"month": month_start.strftime("%Y-%m"), "rate": retention_rate}
            )

        return Response(
            {
                "title": "تحليل معدل الاحتفاظ بالعملاء",
                "data": monthly_retention,
                "metrics": {
                    "current_rate": (
                        monthly_retention[0]["rate"] if monthly_retention else 0
                    ),
                    "avg_rate": (
                        sum(m["rate"] for m in monthly_retention)
                        / len(monthly_retention)
                        if monthly_retention
                        else 0
                    ),
                },
            }
        )

    elif kpi_type == "fulfillment":
        data = (
            Order.objects.filter(created_at__gte=start_date, status="completed")
            .annotate(
                month=TruncMonth("created_at"),
                fulfillment_time=(F("completion_date") - F("created_at")),
            )
            .values("month")
            .annotate(avg_time=Avg("fulfillment_time"), order_count=Count("id"))
            .order_by("month")
        )

        return Response(
            {
                "title": "تحليل وقت إتمام الطلبات",
                "data": list(data),
                "metrics": {
                    "current_avg_time": (
                        data.last()["avg_time"].total_seconds() / 3600 if data else 0
                    ),
                    "best_time": (
                        min(d["avg_time"].total_seconds() / 3600 for d in data)
                        if data
                        else 0
                    ),
                },
            }
        )

    elif kpi_type == "profit":
        data = (
            OrderItem.objects.filter(order__created_at__gte=start_date)
            .annotate(
                month=TruncMonth("order__created_at"), profit=F("price") - F("cost")
            )
            .values("month")
            .annotate(
                total_profit=Sum("profit"),
                total_revenue=Sum("price"),
                margin=ExpressionWrapper(
                    F("total_profit") * 100.0 / F("total_revenue"),
                    output_field=FloatField(),
                ),
            )
            .order_by("month")
        )

        return Response(
            {
                "title": "تحليل هامش الربح",
                "data": list(data),
                "metrics": {
                    "current_margin": data.last()["margin"] if data else 0,
                    "avg_margin": (
                        data.aggregate(Avg("margin"))["margin__avg"] if data else 0
                    ),
                },
            }
        )

    return Response({"error": "نوع مؤشر غير صالح"}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_latest_analytics(request):
    """جلب أحدث البيانات للتحديث المباشر"""
    last_hour = timezone.now() - timedelta(hours=1)

    recent_orders = Order.objects.filter(created_at__gte=last_hour)
    recent_customers = Customer.objects.filter(created_at__gte=last_hour)

    return Response(
        {
            "recent_activity": {
                "new_orders": recent_orders.count(),
                "new_customers": recent_customers.count(),
                "total_revenue": recent_orders.aggregate(Sum("total_amount"))[
                    "total_amount__sum"
                ]
                or 0,
            },
            "timestamp": timezone.now().isoformat(),
        }
    )


def analyze_customer_segments(customers):
    """تحليل وتقسيم العملاء إلى شرائح"""
    if not customers.exists():
        return {
            "segments": {"vip": [], "regular": [], "occasional": []},
            "summary": {"vip_count": 0, "regular_count": 0, "occasional_count": 0},
        }

    # حساب معايير التقسيم
    avg_spent = customers.aggregate(Avg("total_spent"))["total_spent__avg"] or 0
    avg_orders = customers.aggregate(Avg("total_orders"))["total_orders__avg"] or 0

    segments = {"vip": [], "regular": [], "occasional": []}

    for customer in customers:
        if (
            customer.total_spent > avg_spent * 2
            or customer.total_orders > avg_orders * 2
        ):
            segment = "vip"
        elif (
            customer.total_spent >= avg_spent * 0.5
            or customer.total_orders >= avg_orders * 0.5
        ):
            segment = "regular"
        else:
            segment = "occasional"

        segments[segment].append(
            {
                "id": customer.id,
                "name": customer.name,
                "total_spent": customer.total_spent,
                "total_orders": customer.total_orders,
                "avg_order_value": customer.avg_order_value,
            }
        )

    return {
        "segments": segments,
        "summary": {
            "vip_count": len(segments["vip"]),
            "regular_count": len(segments["regular"]),
            "occasional_count": len(segments["occasional"]),
        },
    }


def calculate_growth(values):
    """حساب نسبة النمو"""
    if len(values) < 2 or values[-2] == 0:
        return 0
    return ((values[-1] - values[-2]) / values[-2]) * 100


def calculate_average_growth(values):
    """حساب متوسط النمو"""
    if len(values) < 2:
        return 0

    growth_rates = []
    for i in range(1, len(values)):
        if values[i - 1] != 0:
            growth = ((values[i] - values[i - 1]) / values[i - 1]) * 100
            growth_rates.append(growth)

    return sum(growth_rates) / len(growth_rates) if growth_rates else 0
