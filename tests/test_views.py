from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Customer


@login_required
def test_inspections_view(request, customer_id):
    """صفحة اختبار لعرض معاينات العميل"""
    customer = get_object_or_404(Customer, pk=customer_id)

    # جلب المعاينات بنفس الطريقة المستخدمة في customer_detail
    inspections = customer.inspections.select_related(
        "customer", "branch", "created_by"
    ).order_by("-created_at")[:10]

    context = {
        "customer": customer,
        "inspections": inspections,
    }

    return render(request, "customers/test_inspections.html", context)
