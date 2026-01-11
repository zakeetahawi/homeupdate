"""
Template tags for complaints integration with other modules
"""

from datetime import timedelta

from django import template
from django.db.models import Count, Q
from django.utils import timezone

from ..models import Complaint, ComplaintType

register = template.Library()


@register.inclusion_tag("complaints/widgets/customer_complaints_widget.html")
def customer_complaints_widget(customer, limit=5):
    """
    Display customer complaints widget for customer detail page
    """
    complaints = (
        Complaint.objects.filter(customer=customer)
        .select_related("complaint_type", "assigned_to")
        .order_by("-created_at")[:limit]
    )

    # Statistics for this customer
    stats = Complaint.objects.filter(customer=customer).aggregate(
        total=Count("id"),
        new=Count("id", filter=Q(status="new")),
        in_progress=Count("id", filter=Q(status="in_progress")),
        resolved=Count("id", filter=Q(status="resolved")),
        overdue=Count("id", filter=Q(status="overdue")),
    )

    return {
        "customer": customer,
        "complaints": complaints,
        "stats": stats,
        "has_complaints": complaints.exists(),
    }


@register.inclusion_tag("complaints/widgets/order_complaints_widget.html")
def order_complaints_widget(order, limit=3):
    """
    Display order-related complaints widget for order detail page
    """
    complaints = (
        Complaint.objects.filter(related_order=order)
        .select_related("complaint_type", "assigned_to", "customer")
        .order_by("-created_at")[:limit]
    )

    return {
        "order": order,
        "complaints": complaints,
        "has_complaints": complaints.exists(),
    }


@register.inclusion_tag("complaints/widgets/user_complaints_widget.html")
def user_complaints_widget(user, limit=5):
    """
    Display user's assigned complaints widget for dashboard
    """
    complaints = (
        Complaint.objects.filter(
            assigned_to=user, status__in=["new", "in_progress", "overdue"]
        )
        .select_related("customer", "complaint_type")
        .order_by("deadline")[:limit]
    )

    # Count overdue complaints
    overdue_count = complaints.filter(deadline__lt=timezone.now()).count()

    return {
        "user": user,
        "complaints": complaints,
        "overdue_count": overdue_count,
        "has_complaints": complaints.exists(),
    }


@register.inclusion_tag("complaints/widgets/department_complaints_widget.html")
def department_complaints_widget(department, limit=5):
    """
    Display department complaints widget for department dashboard
    """
    complaints = (
        Complaint.objects.filter(assigned_department=department)
        .select_related("customer", "complaint_type", "assigned_to")
        .order_by("-created_at")[:limit]
    )

    # Statistics for this department
    stats = Complaint.objects.filter(assigned_department=department).aggregate(
        total=Count("id"),
        new=Count("id", filter=Q(status="new")),
        in_progress=Count("id", filter=Q(status="in_progress")),
        resolved=Count("id", filter=Q(status="resolved")),
        overdue=Count("id", filter=Q(status="overdue")),
    )

    return {
        "department": department,
        "complaints": complaints,
        "stats": stats,
        "has_complaints": complaints.exists(),
    }


@register.simple_tag
def complaint_status_badge(status):
    """
    Generate HTML badge for complaint status
    """
    status_config = {
        "new": {"class": "bg-primary", "text": "جديدة", "icon": "fas fa-plus-circle"},
        "in_progress": {
            "class": "bg-warning",
            "text": "قيد الحل",
            "icon": "fas fa-cog",
        },
        "resolved": {
            "class": "bg-success",
            "text": "محلولة",
            "icon": "fas fa-check-circle",
        },
        "pending_evaluation": {
            "class": "bg-warning text-dark",
            "text": "بحاجة تقييم",
            "icon": "fas fa-star-half-alt",
        },
        "closed": {
            "class": "bg-secondary",
            "text": "مغلقة",
            "icon": "fas fa-times-circle",
        },
        "overdue": {
            "class": "bg-danger",
            "text": "متأخرة",
            "icon": "fas fa-exclamation-triangle",
        },
        "escalated": {"class": "bg-dark", "text": "مصعدة", "icon": "fas fa-arrow-up"},
    }

    config = status_config.get(status, status_config["new"])

    return f"""
    <span class="badge {config['class']} d-inline-flex align-items-center">
        <i class="{config['icon']} me-1"></i>
        {config['text']}
    </span>
    """


@register.simple_tag
def complaint_priority_badge(priority):
    """
    Generate HTML badge for complaint priority
    """
    priority_config = {
        "low": {"class": "bg-info", "text": "منخفضة", "icon": "fas fa-arrow-down"},
        "medium": {"class": "bg-warning", "text": "متوسطة", "icon": "fas fa-minus"},
        "high": {"class": "bg-danger", "text": "عالية", "icon": "fas fa-arrow-up"},
        "urgent": {"class": "bg-dark", "text": "عاجلة", "icon": "fas fa-exclamation"},
    }

    config = priority_config.get(priority, priority_config["medium"])

    return f"""
    <span class="badge {config['class']} d-inline-flex align-items-center">
        <i class="{config['icon']} me-1"></i>
        {config['text']}
    </span>
    """


@register.simple_tag
def get_complaint_stats_for_period(days=30):
    """
    Get complaint statistics for a specific period
    """
    start_date = timezone.now() - timedelta(days=days)

    stats = Complaint.objects.filter(created_at__gte=start_date).aggregate(
        total=Count("id"),
        new=Count("id", filter=Q(status="new")),
        resolved=Count("id", filter=Q(status="resolved")),
        overdue=Count("id", filter=Q(status="overdue")),
    )

    return stats


@register.filter
def time_until_deadline(complaint):
    """
    Calculate time remaining until deadline
    """
    if not complaint.deadline:
        return "غير محدد"

    now = timezone.now()
    if complaint.deadline < now:
        overdue = now - complaint.deadline
        if overdue.days > 0:
            return f"متأخر {overdue.days} يوم"
        else:
            hours = overdue.seconds // 3600
            return f"متأخر {hours} ساعة"
    else:
        remaining = complaint.deadline - now
        if remaining.days > 0:
            return f"{remaining.days} يوم متبقي"
        else:
            hours = remaining.seconds // 3600
            return f"{hours} ساعة متبقية"


@register.simple_tag
def quick_complaint_create_url(customer_id=None, order_id=None):
    """
    Generate URL for quick complaint creation with pre-filled data
    """
    from django.urls import reverse

    url = reverse("complaints:complaint_create")
    params = []

    if customer_id:
        params.append(f"customer_id={customer_id}")
    if order_id:
        params.append(f"order_id={order_id}")

    if params:
        url += "?" + "&".join(params)

    return url


@register.inclusion_tag("complaints/widgets/complaint_quick_stats.html")
def complaint_quick_stats():
    """
    Display quick complaint statistics for any dashboard
    """
    today = timezone.now().date()

    stats = {
        "total": Complaint.objects.count(),
        "today": Complaint.objects.filter(created_at__date=today).count(),
        "overdue": Complaint.objects.filter(
            deadline__lt=timezone.now(), status__in=["new", "in_progress"]
        ).count(),
        "urgent": Complaint.objects.filter(
            priority="urgent", status__in=["new", "in_progress"]
        ).count(),
    }

    return {"stats": stats}


@register.simple_tag
def complaint_type_color(complaint_type_name):
    """
    Get color for complaint type
    """
    colors = {
        "فني": "#007bff",
        "خدمة عملاء": "#28a745",
        "مالي": "#ffc107",
        "جودة": "#dc3545",
        "تسليم": "#6f42c1",
        "أخرى": "#6c757d",
    }

    return colors.get(complaint_type_name, "#6c757d")
