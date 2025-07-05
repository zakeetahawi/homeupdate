from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count, Sum, F, Case, When, Value, IntegerField
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models.functions import TruncDay, TruncMonth, ExtractMonth, ExtractYear
import json

from .models import ManufacturingOrder, ManufacturingOrderItem
from orders.models import Order


class ManufacturingOrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_list.html'
    context_object_name = 'manufacturing_orders'
    paginate_by = 25
    permission_required = 'manufacturing.view_manufacturingorder'
    
    def get_queryset(self):
        # Optimize the query by selecting related fields that exist
        queryset = ManufacturingOrder.objects.select_related(
            'order',  # This is the only direct foreign key in the model
            'order__customer'  # Access customer through order
        ).order_by('-order_date')
        
        # Apply filters
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if status:
            queryset = queryset.filter(status=status)
            
        if search:
            # Search in relevant fields including order and customer fields
            queryset = queryset.filter(
                Q(order__id__icontains=search) |
                Q(contract_number__icontains=search) |
                Q(invoice_number__icontains=search) |
                Q(exit_permit_number__icontains=search) |
                Q(order__customer__name__icontains=search) |
                Q(order__customer__phone__icontains=search) |
                Q(notes__icontains=search)
            )
            
        if date_from:
            queryset = queryset.filter(order_date__gte=date_from)
            
        if date_to:
            # Add one day to include the entire end date
            import datetime
            end_date = datetime.datetime.strptime(date_to, '%Y-%m-%d') + datetime.timedelta(days=1)
            queryset = queryset.filter(order_date__lt=end_date)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Count, Q
        from django.contrib.auth import get_user_model
        
        # Get all manufacturing orders for statistics
        all_orders = self.get_queryset().model.objects.all()
        
        # Prepare status counts for the dashboard
        status_counts = all_orders.values('status').annotate(count=Count('status'))
        status_data = {item['status']: item['count'] for item in status_counts}
        
        # Add dashboard statistics
        context.update({
            'total_orders': all_orders.count(),
            'pending_orders': status_data.get('pending', 0),
            'in_progress_orders': status_data.get('in_progress', 0),
            'completed_orders': status_data.get('completed', 0),
            'delivered_orders': status_data.get('delivered', 0),
            'cancelled_orders': status_data.get('cancelled', 0),
            'ready_for_installation_orders': status_data.get('ready_for_installation', 0),
            'status_choices': dict(ManufacturingOrder.STATUS_CHOICES),
            'order_types': dict(ManufacturingOrder.ORDER_TYPE_CHOICES),
        })
        
        # Add filter values to context
        context.update({
            'status_filter': self.request.GET.get('status', ''),
            'search_query': self.request.GET.get('search', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'branch_filter': self.request.GET.get('branch', ''),
            'sales_person_filter': self.request.GET.get('sales_person', ''),
        })
        
        # Add current date for date picker max date
        from datetime import date
        context['today'] = date.today().isoformat()
        
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


import logging
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import ManufacturingOrder

# Configure logger
logger = logging.getLogger(__name__)

@require_http_methods(["POST"])
@csrf_exempt
def update_order_status(request, pk):
    """
    API endpoint to update the status of a manufacturing order.
    Expected POST data: {'status': 'new_status'}
    """
    logger.info(f"[update_order_status] Starting update for order {pk}")
    logger.debug(f"[update_order_status] Request user: {request.user}")
    logger.debug(f"[update_order_status] POST data: {request.POST}")
    
    try:
        # Check authentication
        if not request.user.is_authenticated:
            logger.warning("[update_order_status] Unauthenticated access attempt")
            return JsonResponse({
                'success': False, 
                'error': 'يجب تسجيل الدخول أولاً'
            }, status=401)
            
        # Check permission
        if not request.user.has_perm('manufacturing.change_manufacturingorder'):
            logger.warning(f"[update_order_status] Permission denied for user {request.user}")
            return JsonResponse({
                'success': False, 
                'error': 'ليس لديك صلاحية لتحديث حالة الطلب'
            }, status=403)
        
        # Get the order
        try:
            order = ManufacturingOrder.objects.get(pk=pk)
            logger.debug(f"[update_order_status] Found order: {order}")
        except ManufacturingOrder.DoesNotExist:
            logger.error(f"[update_order_status] Order {pk} not found")
            return JsonResponse({
                'success': False, 
                'error': 'لم يتم العثور على أمر التصنيع'
            }, status=404)
        
        # Get and validate status
        new_status = request.POST.get('status')
        logger.debug(f"[update_order_status] Requested status: {new_status}")
        
        if not new_status:
            logger.warning("[update_order_status] No status provided")
            return JsonResponse({
                'success': False, 
                'error': 'لم يتم تحديد الحالة الجديدة'
            }, status=400)
            
        valid_statuses = dict(ManufacturingOrder.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            logger.warning(f"[update_order_status] Invalid status: {new_status}. Valid statuses: {list(valid_statuses)}")
            return JsonResponse({
                'success': False, 
                'error': f'حالة غير صالحة. الحالات المتاحة: {list(valid_statuses)}',
                'received_status': new_status,
                'valid_statuses': list(valid_statuses)
            }, status=400)
        
        # Update order status
        old_status = order.status
        logger.info(f"[update_order_status] Updating order {pk} status from {old_status} to {new_status}")
        
        order.status = new_status
        order.updated_by = request.user
        order.updated_at = timezone.now()
        
        # Set completion date if status is completed or ready for installation
        if new_status in ['completed', 'ready_for_installation'] and not order.completion_date:
            order.completion_date = timezone.now()
            logger.debug(f"[update_order_status] Set completion date to {order.completion_date}")
        
        # Save the order
        try:
            order.save(update_fields=['status', 'updated_by', 'updated_at', 'completion_date'])
            logger.info(f"[update_order_status] Successfully updated order {pk}")
        except Exception as e:
            logger.error(f"[update_order_status] Error saving order {pk}: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'حدث خطأ أثناء حفظ التغييرات',
                'details': str(e),
                'exception_type': e.__class__.__name__
            }, status=500)
        
        # Log the status change in Django admin
        try:
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(order).pk,
                object_id=order.id,
                object_repr=str(order),
                action_flag=CHANGE,
                change_message=f'تم تغيير الحالة من {dict(ManufacturingOrder.STATUS_CHOICES).get(old_status, "")} إلى {dict(ManufacturingOrder.STATUS_CHOICES).get(new_status, "")}'
            )
            logger.debug(f"[update_order_status] Added admin log entry for order {pk}")
        except Exception as e:
            logger.error(f"[update_order_status] Error adding admin log entry: {str(e)}", exc_info=True)
            # Continue even if admin logging fails
        
        # Prepare success response
        response_data = {
            'success': True,
            'status': order.status,
            'status_display': order.get_status_display(),
            'updated_at': order.updated_at.strftime('%Y-%m-%d %H:%M'),
            'message': 'تم تحديث حالة الطلب بنجاح'
        }
        logger.info(f"[update_order_status] Success response: {response_data}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.critical(f"[update_order_status] Unexpected error: {str(e)}\n{error_trace}")
        
        return JsonResponse({
            'success': False, 
            'error': 'حدث خطأ غير متوقع',
            'exception_type': e.__class__.__name__,
            'details': str(e)
        }, status=500)


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


class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'manufacturing/dashboard.html'
    permission_required = 'manufacturing.view_manufacturingorder'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date range for the dashboard (last 30 days)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Get all manufacturing orders
        orders = ManufacturingOrder.objects.filter(
            order_date__date__range=(start_date, end_date)
        ).select_related('order', 'order__customer')
        
        # Calculate status counts
        status_counts = orders.values('status').annotate(
            count=Count('status')
        ).order_by('status')
        
        # Prepare status data for the chart
        status_data = {
            'labels': [],
            'data': [],
            'colors': [],
        }
        
        status_colors = {
            'pending': '#ffc107',     # Yellow
            'in_progress': '#0dcaf0', # Blue
            'completed': '#198754',   # Green
            'delivered': '#0d6efd',   # Primary blue
            'cancelled': '#dc3545',   # Red
        }
        
        for status in status_counts:
            status_display = dict(ManufacturingOrder.STATUS_CHOICES).get(status['status'], status['status'])
            status_data['labels'].append(status_display)
            status_data['data'].append(status['count'])
            status_data['colors'].append(status_colors.get(status['status'], '#6c757d'))
        
        # Get monthly order counts
        monthly_orders = orders.annotate(
            month=ExtractMonth('order_date'),
            year=ExtractYear('order_date')
        ).values('year', 'month').annotate(
            total=Count('id')
        ).order_by('year', 'month')
        
        # Prepare monthly data for the chart
        monthly_data = {
            'labels': [],
            'data': [],
        }
        
        # Get month names in Arabic
        month_names = [
            'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'
        ]
        
        for item in monthly_orders:
            month_name = f"{month_names[item['month']-1]} {item['year']}"
            monthly_data['labels'].append(month_name)
            monthly_data['data'].append(item['total'])
        
        # Get recent orders
        recent_orders = orders.order_by('-order_date')[:5]
        
        # Get orders by type
        orders_by_type = orders.values('order_type').annotate(
            count=Count('id'),
            total=Sum('order__total_amount')
        )
        
        context.update({
            'status_data': json.dumps(status_data),
            'monthly_data': json.dumps(monthly_data),
            'recent_orders': recent_orders,
            'orders_by_type': orders_by_type,
            'total_orders': orders.count(),
            'pending_orders': orders.filter(status='pending').count(),
            'in_progress_orders': orders.filter(status='in_progress').count(),
            'completed_orders': orders.filter(status='completed').count(),
            'delivered_orders': orders.filter(status='delivered').count(),
            'cancelled_orders': orders.filter(status='cancelled').count(),
            'total_revenue': sum(order.order.total_amount for order in orders if order.order and order.order.total_amount),
            'start_date': start_date,
            'end_date': end_date,
        })
        
        return context


def dashboard_data(request):
    """
    API endpoint to get dashboard data for AJAX requests
    """
    if not request.user.has_perm('manufacturing.view_manufacturingorder'):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get date range from request or use default (last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get all manufacturing orders
    orders = ManufacturingOrder.objects.filter(
        order_date__date__range=(start_date, end_date)
    ).select_related('order', 'order__customer')
    
    # Calculate status counts
    status_counts = orders.values('status').annotate(
        count=Count('status')
    ).order_by('status')
    
    # Prepare response data
    data = {
        'success': True,
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'in_progress_orders': orders.filter(status='in_progress').count(),
        'completed_orders': orders.filter(status='completed').count(),
        'delivered_orders': orders.filter(status='delivered').count(),
        'cancelled_orders': orders.filter(status='cancelled').count(),
        'status_data': {item['status']: item['count'] for item in status_counts},
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)
