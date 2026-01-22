"""
Dashboard Views
عروض لوحة التحكم
"""

from django.db.models import Sum
from rest_framework.decorators import api_view
from rest_framework.response import Response

from customers.models import Customer
from orders.models import Order
from inventory.models import Product
from accounts.models import ActivityLog


@api_view(['GET'])
def dashboard_view(request):
    """
    عرض إحصائيات لوحة التحكم
    """
    try:
        # Calculate statistics
        stats = {
            "totalCustomers": Customer.objects.count(),
            "totalOrders": Order.objects.count(),
            "inventoryValue": Product.objects.aggregate(total=Sum("price", default=0))["total"],
            "pendingInstallations": 0,
        }

        # Get recent activities
        activities = (
            ActivityLog.objects.select_related("user")
            .order_by("-timestamp")[:10]
            .values("id", "type", "description", "timestamp")
        )

        return Response({"stats": stats, "activities": list(activities)})
    except Exception as e:
        return Response({"error": str(e)}, status=500)
