from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator

from .models import ManufacturingOrder, ManufacturingOrderItem
from orders.models import Order


class ManufacturingOrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_list.html'
    context_object_name = 'manufacturing_orders'
    paginate_by = 20
    permission_required = 'manufacturing.view_manufacturingorder'
    
    def get_queryset(self):
        queryset = ManufacturingOrder.objects.select_related('order').order_by('-created_at')
        
        # Apply filters
        status = self.request.GET.get('status')
        order_type = self.request.GET.get('order_type')
        search = self.request.GET.get('search')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if status:
            queryset = queryset.filter(status=status)
            
        if order_type:
            queryset = queryset.filter(order_type=order_type)
            
        if search:
            queryset = queryset.filter(
                Q(order__id__icontains=search) |
                Q(contract_number__icontains=search) |
                Q(invoice_number__icontains=search) |
                Q(exit_permit_number__icontains=search)
            )
            
        if date_from:
            queryset = queryset.filter(order_date__gte=date_from)
            
        if date_to:
            queryset = queryset.filter(order_date__lte=date_to)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter values to context
        context['status_filter'] = self.request.GET.get('status', '')
        context['order_type_filter'] = self.request.GET.get('order_type', '')
        context['search_query'] = self.request.GET.get('search', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        return context


class ManufacturingOrderDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_detail.html'
    context_object_name = 'manufacturing_order'
    permission_required = 'manufacturing.view_manufacturingorder'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        return context


class ManufacturingOrderCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_form.html'
    fields = ['order', 'order_type', 'contract_number', 'invoice_number', 
              'order_date', 'expected_delivery_date', 'notes', 
              'contract_file', 'inspection_file']
    permission_required = 'manufacturing.add_manufacturingorder'
    
    def get_success_url(self):
        messages.success(self.request, 'تم إنشاء أمر التصنيع بنجاح')
        return reverse('manufacturing:order_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class ManufacturingOrderUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_form.html'
    fields = ['order', 'order_type', 'contract_number', 'invoice_number', 
              'order_date', 'expected_delivery_date', 'exit_permit_number',
              'notes', 'contract_file', 'inspection_file']
    permission_required = 'manufacturing.change_manufacturingorder'
    
    def get_success_url(self):
        messages.success(self.request, 'تم تحديث أمر التصنيع بنجاح')
        return reverse('manufacturing:order_list')


class ManufacturingOrderDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_confirm_delete.html'
    success_url = reverse_lazy('manufacturing:order_list')
    permission_required = 'manufacturing.delete_manufacturingorder'
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'تم حذف أمر التصنيع بنجاح')
        return super().delete(request, *args, **kwargs)


@require_http_methods(["POST"])
@csrf_exempt
def update_order_status(request, pk):
    if not request.user.has_perm('manufacturing.change_manufacturingorder'):
        return JsonResponse({'success': False, 'error': 'ليس لديك صلاحية لتحديث حالة الطلب'}, status=403)
    
    try:
        order = get_object_or_404(ManufacturingOrder, pk=pk)
        new_status = request.POST.get('status')
        
        if not new_status or new_status not in dict(ManufacturingOrder.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'حالة غير صالحة'}, status=400)
        
        order.status = new_status
        order.updated_at = timezone.now()
        order.save()
        
        # If status is changed to ready_for_installation, update the related installation if exists
        if new_status == 'ready_for_installation' and hasattr(order, 'installation'):
            installation = order.installation
            installation.status = 'ready'
            installation.ready_date = timezone.now()
            installation.save()
        
        return JsonResponse({
            'success': True,
            'status_display': order.get_status_display(),
            'updated_at': order.updated_at.strftime('%Y-%m-%d %H:%M')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def update_exit_permit(request, pk):
    if not request.user.has_perm('manufacturing.change_manufacturingorder'):
        return JsonResponse({'success': False, 'error': 'ليس لديك صلاحية لتحديث إذن الخروج'}, status=403)
    
    try:
        order = get_object_or_404(ManufacturingOrder, pk=pk)
        exit_permit_number = request.POST.get('exit_permit_number', '').strip()
        
        if not exit_permit_number:
            return JsonResponse({'success': False, 'error': 'يرجى إدخال رقم إذن الخروج'}, status=400)
        
        order.exit_permit_number = exit_permit_number
        order.updated_at = timezone.now()
        order.save()
        
        return JsonResponse({
            'success': True,
            'exit_permit_number': order.exit_permit_number,
            'updated_at': order.updated_at.strftime('%Y-%m-%d %H:%M')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def create_from_order(request, order_id):
    if not request.user.has_perm('manufacturing.add_manufacturingorder'):
        messages.error(request, 'ليس لديك صلاحية لإنشاء أمر تصنيع')
        return redirect('manufacturing:order_list')
    
    try:
        order = get_object_or_404(Order, pk=order_id)
        
        # Check if manufacturing order already exists for this order
        if ManufacturingOrder.objects.filter(order=order).exists():
            messages.warning(request, 'يوجد أمر تصنيع مسبقاً لهذا الطلب')
            return redirect('manufacturing:order_list')
        
        # Create manufacturing order
        manufacturing_order = ManufacturingOrder.objects.create(
            order=order,
            order_type='installation' if order.order_type == 'installation' else 'detail',
            contract_number=order.contract_number,
            order_date=order.order_date,
            expected_delivery_date=order.expected_delivery_date,
            created_by=request.user
        )
        
        # Add order items to manufacturing order
        for item in order.items.all():
            ManufacturingOrderItem.objects.create(
                manufacturing_order=manufacturing_order,
                product_name=item.product.name,
                quantity=item.quantity,
                specifications=item.specifications
            )
        
        messages.success(request, 'تم إنشاء أمر التصنيع بنجاح')
        return redirect('manufacturing:order_update', pk=manufacturing_order.pk)
        
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء إنشاء أمر التصنيع: {str(e)}')
        return redirect('orders:order_detail', pk=order_id)


def print_manufacturing_order(request, pk):
    """Generate a PDF for the manufacturing order"""
    manufacturing_order = get_object_or_404(ManufacturingOrder, pk=pk)
    
    # Get company name from settings
    from django.conf import settings
    company_name = getattr(settings, 'COMPANY_NAME', 'شركتنا')
    
    # Render the HTML template
    html_string = render_to_string('manufacturing/print/manufacturing_order.html', {
        'manufacturing_order': manufacturing_order,
        'items': manufacturing_order.items.all(),
        'now': timezone.now(),
        'company_name': company_name,
    })
    
    # Create PDF
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf = html.write_pdf()
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'filename=manufacturing_order_{manufacturing_order.id}.pdf'
    return response
