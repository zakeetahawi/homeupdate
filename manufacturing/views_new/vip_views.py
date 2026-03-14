"""
VIP Orders Views - Special handling for VIP customers
عروض طلبات VIP - معالجة خاصة لعملاء VIP
"""

from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import QuerySet, Q
from django.views.generic import ListView

from manufacturing.models import ManufacturingOrder
from core.mixins import PaginationFixMixin


class VIPOrdersListView(LoginRequiredMixin, PermissionRequiredMixin, PaginationFixMixin, ListView):
    """
    عرض طلبات VIP فقط
    """
    model = ManufacturingOrder
    template_name = "manufacturing/vip_orders_list.html"
    context_object_name = "vip_orders"
    paginate_by = 25
    permission_required = "manufacturing.view_manufacturingorder"
    allow_empty = True

    def get_queryset(self) -> QuerySet:
        """
        الحصول على طلبات VIP فقط
        """
        queryset = ManufacturingOrder.objects.select_related(
            'order',
            'order__customer'
        ).filter(
            Q(order__customer__is_vip=True) |
            Q(order__priority='high') |
            Q(order__is_urgent=True)
        ).order_by('-created_at')

        # البحث
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(order__order_number__icontains=search) |
                Q(order__customer__name__icontains=search)
            )

        # الفلترة حسب الحالة
        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """إضافة بيانات VIP"""
        context = super().get_context_data(**kwargs)
        
        # إحصائيات VIP
        vip_queryset = self.get_queryset()
        context['total_vip_orders'] = vip_queryset.count()
        context['pending_vip'] = vip_queryset.filter(status='pending').count()
        context['in_progress_vip'] = vip_queryset.filter(status='in_progress').count()
        context['urgent_orders'] = vip_queryset.filter(order__is_urgent=True).count()
        
        return context
