"""
Manufacturing Order Views - List, Detail, CRUD Operations
عروض أوامر التصنيع - القائمة، التفاصيل، العمليات الأساسية
"""

from typing import Any, Dict, Optional
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import QuerySet, Q, Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.utils import timezone

from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem
from orders.models import Order
from core.mixins import PaginationFixMixin


class ManufacturingOrderListView(LoginRequiredMixin, PermissionRequiredMixin, PaginationFixMixin, ListView):
    """
    عرض قائمة أوامر التصنيع مع الفلترة والبحث
    """
    model = ManufacturingOrder
    template_name = "manufacturing/manufacturingorder_list.html"
    context_object_name = "manufacturing_orders"
    paginate_by = 25
    permission_required = "manufacturing.view_manufacturingorder"

    def get_queryset(self) -> QuerySet:
        """
        الحصول على قائمة أوامر التصنيع مع التحسينات
        """
        queryset = ManufacturingOrder.objects.select_related(
            'order',
            'order__customer',
            'created_by'
        ).prefetch_related(
            'items',
            'items__product'
        ).order_by('-created_at')

        # البحث
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(order__order_number__icontains=search) |
                Q(order__customer__name__icontains=search) |
                Q(contract_number__icontains=search)
            )

        # الفلترة حسب الحالة
        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)

        # الفلترة حسب التاريخ
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """إضافة بيانات إضافية للسياق"""
        context = super().get_context_data(**kwargs)
        
        # إحصائيات
        context['total_orders'] = ManufacturingOrder.objects.count()
        context['pending_orders'] = ManufacturingOrder.objects.filter(status='pending').count()
        context['in_progress_orders'] = ManufacturingOrder.objects.filter(status='in_progress').count()
        context['completed_orders'] = ManufacturingOrder.objects.filter(status='completed').count()
        
        # الفلاتر الحالية
        context['current_search'] = self.request.GET.get('search', '')
        context['current_status'] = self.request.GET.get('status', '')
        
        return context


class ManufacturingOrderDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    عرض تفاصيل أمر التصنيع
    """
    model = ManufacturingOrder
    template_name = "manufacturing/manufacturingorder_detail.html"
    context_object_name = "manufacturing_order"
    permission_required = "manufacturing.view_manufacturingorder"

    def get_queryset(self) -> QuerySet:
        """تحسين الاستعلام"""
        return ManufacturingOrder.objects.select_related(
            'order',
            'order__customer',
            'created_by'
        ).prefetch_related(
            'items',
            'items__product',
            'items__product__category'
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """إضافة بيانات إضافية"""
        context = super().get_context_data(**kwargs)
        
        # العناصر
        context['items'] = self.object.items.all()
        
        # الحالات المتاحة
        context['available_statuses'] = self._get_available_statuses()
        
        # السجل
        context['activity_log'] = self._get_activity_log()
        
        return context

    def _get_available_statuses(self) -> list:
        """الحصول على الحالات المتاحة للانتقال"""
        current_status = self.object.status
        
        status_flow = {
            'pending': ['in_progress', 'cancelled'],
            'in_progress': ['completed', 'on_hold', 'cancelled'],
            'on_hold': ['in_progress', 'cancelled'],
            'completed': [],
            'cancelled': []
        }
        
        return status_flow.get(current_status, [])

    def _get_activity_log(self) -> QuerySet:
        """الحصول على سجل النشاط"""
        # يمكن إضافة نموذج ActivityLog لاحقاً
        return []


class ManufacturingOrderCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    إنشاء أمر تصنيع جديد
    """
    model = ManufacturingOrder
    template_name = "manufacturing/manufacturingorder_form.html"
    fields = ['order', 'contract_number', 'expected_delivery_date', 'notes']
    permission_required = "manufacturing.add_manufacturingorder"
    success_url = reverse_lazy('manufacturing:order_list')

    def form_valid(self, form):
        """حفظ البيانات مع المستخدم الحالي"""
        form.instance.created_by = self.request.user
        form.instance.status = 'pending'
        messages.success(self.request, 'تم إنشاء أمر التصنيع بنجاح')
        return super().form_valid(form)


class ManufacturingOrderUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    تحديث أمر تصنيع
    """
    model = ManufacturingOrder
    template_name = "manufacturing/manufacturingorder_form.html"
    fields = ['contract_number', 'expected_delivery_date', 'notes', 'status']
    permission_required = "manufacturing.change_manufacturingorder"
    success_url = reverse_lazy('manufacturing:order_list')

    def form_valid(self, form):
        """حفظ التحديثات"""
        messages.success(self.request, 'تم تحديث أمر التصنيع بنجاح')
        return super().form_valid(form)


class ManufacturingOrderDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    حذف أمر تصنيع
    """
    model = ManufacturingOrder
    template_name = "manufacturing/manufacturingorder_confirm_delete.html"
    permission_required = "manufacturing.delete_manufacturingorder"
    success_url = reverse_lazy('manufacturing:order_list')

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """حذف مع رسالة نجاح"""
        messages.success(request, 'تم حذف أمر التصنيع بنجاح')
        return super().delete(request, *args, **kwargs)
