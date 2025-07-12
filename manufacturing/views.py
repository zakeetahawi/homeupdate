from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from django.template.loader import render_to_string
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import ManufacturingOrder, ManufacturingOrderItem
from accounts.models import UnifiedSystemSettings
from inventory.models import Product
from orders.models import Order
import json

class DashboardView(TemplateView):
    template_name = 'manufacturing/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # إحصائيات التصنيع
        context['orders_count'] = ManufacturingOrder.objects.count()
        context['pending_count'] = ManufacturingOrder.objects.filter(status='pending').count()
        context['in_progress_count'] = ManufacturingOrder.objects.filter(status='in_progress').count()
        context['completed_count'] = ManufacturingOrder.objects.filter(status='completed').count()
        context['delivered_count'] = ManufacturingOrder.objects.filter(status='delivered').count()
        context['recent_orders'] = ManufacturingOrder.objects.order_by('-created_at')[:10]
        return context

class ManufacturingOrderListView(LoginRequiredMixin, ListView):
    model = ManufacturingOrder
    template_name = 'manufacturing/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        queryset = ManufacturingOrder.objects.all().order_by('-created_at')
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(customer_name__icontains=search) |
                Q(status__icontains=search)
            )
        return queryset

class ManufacturingOrderDetailView(LoginRequiredMixin, DetailView):
    model = ManufacturingOrder
    template_name = 'manufacturing/order_detail.html'
    context_object_name = 'order'

class ManufacturingOrderCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = ManufacturingOrder
    template_name = 'manufacturing/order_form.html'
    fields = ['order_number', 'customer_name', 'description', 'expected_delivery_date', 'status']
    success_url = reverse_lazy('manufacturing:order_list')
    permission_required = 'manufacturing.add_manufacturingorder'

    def form_valid(self, form):
        messages.success(self.request, 'تم إنشاء طلب التصنيع بنجاح.')
        return super().form_valid(form)

class ManufacturingOrderUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = ManufacturingOrder
    template_name = 'manufacturing/order_form.html'
    fields = ['order_number', 'customer_name', 'description', 'expected_delivery_date', 'status']
    success_url = reverse_lazy('manufacturing:order_list')
    permission_required = 'manufacturing.change_manufacturingorder'

    def form_valid(self, form):
        messages.success(self.request, 'تم تحديث طلب التصنيع بنجاح.')
        return super().form_valid(form)

class ManufacturingOrderDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = ManufacturingOrder
    template_name = 'manufacturing/order_confirm_delete.html'
    success_url = reverse_lazy('manufacturing:order_list')
    permission_required = 'manufacturing.delete_manufacturingorder'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'تم حذف طلب التصنيع بنجاح.')
        return super().delete(request, *args, **kwargs)

# AJAX validation views
@csrf_exempt
def validate_manufacturing_order_ajax(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        order_number = data.get('order_number')
        
        if ManufacturingOrder.objects.filter(order_number=order_number).exists():
            return JsonResponse({'valid': False, 'message': 'رقم الطلب موجود مسبقاً'})
        
        return JsonResponse({'valid': True})

@csrf_exempt
def validate_manufacturing_item_ajax(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        if not Product.objects.filter(id=product_id).exists():
            return JsonResponse({'valid': False, 'message': 'المنتج غير موجود'})
        
        return JsonResponse({'valid': True})

@csrf_exempt
def get_product_info_ajax(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        return JsonResponse({
            'name': product.name,
            'price': str(product.price),
            'stock': product.stock
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'المنتج غير موجود'}, status=404)

@csrf_exempt
def get_order_info_ajax(request, order_id):
    try:
        order = ManufacturingOrder.objects.get(id=order_id)
        return JsonResponse({
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'status': order.status
        })
    except ManufacturingOrder.DoesNotExist:
        return JsonResponse({'error': 'الطلب غير موجود'}, status=404)
