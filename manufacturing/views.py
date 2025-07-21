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
from django.db import transaction

from .models import ManufacturingOrder, ManufacturingOrderItem
from orders.models import Order
from accounts.models import Notification, Department


class ManufacturingOrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_list.html'
    context_object_name = 'manufacturing_orders'
    # paginate_by = 25  # تم تعطيل Django pagination لاستخدام DataTables pagination
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
            # بحث شامل في كل الأعمدة المهمة
            queryset = queryset.filter(
                Q(order__id__icontains=search) |
                Q(order__order_number__icontains=search) |
                Q(contract_number__icontains=search) |
                Q(invoice_number__icontains=search) |
                Q(exit_permit_number__icontains=search) |
                Q(order__customer__name__icontains=search) |
                Q(order__customer__phone__icontains=search) |
                Q(order__salesperson__name__icontains=search) |
                Q(order__branch__name__icontains=search) |
                Q(notes__icontains=search) |
                Q(order_type__icontains=search) |
                Q(status__icontains=search) |
                Q(order_date__icontains=search) |
                Q(expected_delivery_date__icontains=search)
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
        
        # Add branches for filter dropdown
        from accounts.models import Branch
        context['branches'] = Branch.objects.all().order_by('name')
        
        # Add current date for date picker max date
        from datetime import date
        context['today'] = date.today().isoformat()
        
        # Add function to get available statuses for each order
        context['get_available_statuses'] = lambda current_status, order_type=None: self._get_available_statuses(self.request.user, current_status, order_type)
        
        return context
    
    def _get_available_statuses(self, user, current_status, order_type=None):
        """
        Get list of available statuses for the user based on current status and order type
        """
        if user.is_superuser:
            # Admin can see all statuses except current one, but follow the new logic
            all_statuses = [status for status in ManufacturingOrder.STATUS_CHOICES if status[0] != current_status]
            
            # Apply the new logic for admin users too
            if current_status == 'in_progress':
                if order_type == 'installation':
                    return [('ready_install', 'جاهز للتركيب')]
                elif order_type in ['custom', 'accessory']:
                    return [('completed', 'مكتمل')]
                else:
                    return []
            elif current_status == 'ready_install':
                return [('delivered', 'تم التسليم')]
            elif current_status == 'completed':
                return [('delivered', 'تم التسليم')]
            else:
                return all_statuses

        available_statuses = []

        if current_status == 'pending_approval':
            # Only approval users can change from pending_approval
            if user.has_perm('manufacturing.can_approve_orders'):
                available_statuses = [
                    ('pending', 'قيد الانتظار'),
                    ('rejected', 'مرفوض'),
                    ('cancelled', 'ملغي'),
                ]
            else:
                available_statuses = []

        elif current_status == 'pending':
            # Factory staff can see manufacturing progression
            if user.has_perm('manufacturing.change_manufacturingorder'):
                available_statuses = [
                    ('in_progress', 'قيد التصنيع'),
                    ('cancelled', 'ملغي'),
                ]
            else:
                available_statuses = []

        elif current_status == 'in_progress':
            if user.has_perm('manufacturing.change_manufacturingorder'):
                if order_type == 'installation':
                    # بعد قيد التنفيذ لطلبات التركيب: فقط جاهز للتركيب
                    available_statuses = [
                        ('ready_install', 'جاهز للتركيب'),
                    ]
                elif order_type in ['custom', 'accessory']:
                    # بعد قيد التنفيذ لطلبات التفصيل أو الاكسسوار: فقط مكتمل
                    available_statuses = [
                        ('completed', 'مكتمل'),
                    ]
                else:
                    available_statuses = []
            else:
                available_statuses = []

        elif current_status == 'ready_install':
            # بعد جاهز للتركيب: فقط تم التسليم
            if user.has_perm('manufacturing.change_manufacturingorder'):
                available_statuses = [('delivered', 'تم التسليم')]
            else:
                available_statuses = []

        elif current_status == 'completed':
            # بعد مكتمل: فقط تم التسليم
            if user.has_perm('manufacturing.change_manufacturingorder'):
                available_statuses = [('delivered', 'تم التسليم')]
            else:
                available_statuses = []

        elif current_status == 'delivered':
            # Delivered orders are final for non-admin users
            available_statuses = []

        elif current_status in ['rejected', 'cancelled']:
            # Rejected/cancelled orders are final for non-admin users
            available_statuses = []

        return available_statuses


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
    fields = ['order_type', 'status', 'contract_number', 'invoice_number', 
              'order_date', 'expected_delivery_date', 'exit_permit_number',
              'notes', 'contract_file', 'inspection_file']
    permission_required = 'manufacturing.change_manufacturingorder'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['order_date'].widget.attrs['type'] = 'date'
        form.fields['expected_delivery_date'].widget.attrs['type'] = 'date'
        # The 'order' field should not be editable after creation.
        # It's better to display it as readonly text.
        # We can remove it from fields list and handle it in the template.
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass the order instance to the context to display its info
        context['order'] = self.object.order
        return context

    def get_success_url(self):
        messages.success(self.request, 'تم تحديث أمر التصنيع بنجاح')
        return reverse('manufacturing:order_list')


class ManufacturingOrderDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_confirm_delete.html'
    success_url = reverse_lazy('manufacturing:order_list')
    permission_required = 'manufacturing.delete_manufacturingorder'
    
    def delete(self, request, *args, **kwargs):
        from django.db import transaction
        from orders.models import ManufacturingDeletionLog
        import json
        
        # الحصول على أمر التصنيع قبل الحذف
        manufacturing_order = self.get_object()
        order = manufacturing_order.order
        
        # حفظ بيانات أمر التصنيع قبل الحذف
        manufacturing_data = {
            'id': manufacturing_order.id,
            'status': manufacturing_order.status,
            'status_display': manufacturing_order.get_status_display(),
            'order_type': manufacturing_order.order_type,
            'contract_number': manufacturing_order.contract_number,
            'invoice_number': manufacturing_order.invoice_number,
            'order_date': manufacturing_order.order_date.isoformat() if manufacturing_order.order_date else None,
            'expected_delivery_date': manufacturing_order.expected_delivery_date.isoformat() if manufacturing_order.expected_delivery_date else None,
            'notes': manufacturing_order.notes,
            'created_at': manufacturing_order.created_at.isoformat() if manufacturing_order.created_at else None,
            'created_by': manufacturing_order.created_by.username if manufacturing_order.created_by else None,
        }
        
        with transaction.atomic():
            # إنشاء سجل الحذف
            ManufacturingDeletionLog.objects.create(
                order=order,
                manufacturing_order_id=manufacturing_order.id,
                deleted_by=request.user,
                reason=f'تم حذف أمر التصنيع بواسطة {request.user.get_full_name() or request.user.username}',
                manufacturing_order_data=manufacturing_data
            )
            
            # تحديث حالة الطلب
            order.order_status = 'manufacturing_deleted'
            order.tracking_status = 'processing'  # إعادة الطلب لحالة المعالجة
            order.save(update_fields=['order_status', 'tracking_status'])
            
            # حذف أمر التصنيع
            result = super().delete(request, *args, **kwargs)
            
            messages.success(
                request, 
                f'تم حذف أمر التصنيع #{manufacturing_order.id} بنجاح وتم تحديث حالة الطلب #{order.order_number} إلى "أمر تصنيع محذوف"'
            )
            
            return result


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
    # logger.info(f"[update_order_status] Starting update for order {pk}")  # معطل لتجنب الرسائل الكثيرة
    # logger.debug(f"[update_order_status] Request user: {request.user}")  # معطل لتجنب الرسائل الكثيرة
    # logger.debug(f"[update_order_status] POST data: {request.POST}")  # معطل لتجنب الرسائل الكثيرة
    
    try:
        # Check authentication
        if not request.user.is_authenticated:
            logger.warning("[update_order_status] Unauthenticated access attempt")
            return JsonResponse({
                'success': False, 
                'error': 'يجب تسجيل الدخول أولاً'
            }, status=401)
        
        # Get the order
        try:
            order = ManufacturingOrder.objects.get(pk=pk)
            logger.debug(f"[update_order_status] Found order: {order}")
        except ManufacturingOrder.DoesNotExist:
            # logger.error(f"[update_order_status] Order {pk} not found")  # معطل لتجنب الرسائل الكثيرة
            return JsonResponse({
                'success': False, 
                'error': 'لم يتم العثور على أمر التصنيع'
            }, status=404)
        
        # Check if order is in pending_approval status
        if order.status == 'pending_approval':
            return JsonResponse({
                'success': False,
                'error': 'لا يمكن تغيير حالة الطلب قبل الموافقة عليه. يرجى استخدام أزرار الموافقة أو الرفض.'
            }, status=403)
        
        # Check permission for manufacturing status changes
        if not request.user.has_perm('manufacturing.change_manufacturingorder'):
            logger.warning(f"[update_order_status] Permission denied for user {request.user}")
            return JsonResponse({
                'success': False, 
                'error': 'ليس لديك صلاحية لتحديث حالة الطلب'
            }, status=403)
        
        # Get and validate status
        new_status = request.POST.get('status')
        logger.debug(f"[update_order_status] Requested status: {new_status}")
        
        if not new_status:
            logger.warning("[update_order_status] No status provided")
            return JsonResponse({
                'success': False, 
                'error': 'لم يتم تحديد الحالة الجديدة'
            }, status=400)
        
        # التحقق من نوع الطلب الأصلي والحالة المطلوبة
        order_types = order.order.get_selected_types_list() if hasattr(order.order, 'get_selected_types_list') else []
        
        # التحقق من نوع الطلب والحالة المطلوبة
        if new_status == 'ready_install' and 'installation' not in order_types:
            return JsonResponse({
                'success': False,
                'error': 'لا يمكن تعيين حالة "جاهز للتركيب" إلا لأوامر التصنيع من نوع تركيب (installation) فقط.'
            }, status=400)
        
        # منع تعيين حالة "مكتمل" لطلبات التركيب
        if new_status == 'completed' and 'installation' in order_types:
            return JsonResponse({
                'success': False,
                'error': 'لا يمكن تعيين حالة "مكتمل" لطلبات التركيب. طلبات التركيب تصبح "جاهزة للتركيب" ثم "تم التسليم" فقط.'
            }, status=400)
        
        # منع تعيين حالة "جاهز للتركيب" لطلبات التفصيل والاكسسوار
        if new_status == 'ready_install' and ('tailoring' in order_types or 'accessory' in order_types):
            return JsonResponse({
                'success': False,
                'error': 'لا يمكن تعيين حالة "جاهز للتركيب" لطلبات التفصيل أو الاكسسوار. هذه الطلبات تصبح "مكتملة" فقط.'
            }, status=400)
        
        # منع الرفض والإلغاء بعد الحالات المكتملة
        if order.status in ['completed', 'ready_install'] and new_status in ['rejected', 'cancelled']:
            return JsonResponse({
                'success': False,
                'error': 'لا يمكن رفض أو إلغاء الطلب بعد أن يصبح مكتملاً أو جاهزاً للتركيب. يمكن فقط تسليمه.'
            }, status=400)
        
        # Prevent going back to pending_approval unless user is superuser
        if new_status == 'pending_approval' and not request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'لا يمكن العودة إلى حالة "قيد الموافقة" إلا من قبل مدير النظام'
            }, status=403)
        
        # Define status hierarchy to prevent going backwards (unless superuser)
        status_hierarchy = {
            'pending_approval': 0,
            'pending': 1,
            'in_progress': 2,
            'ready_install': 3,
            'completed': 4,
            'delivered': 5,
            'rejected': -1,
            'cancelled': -2
        }
        
        current_level = status_hierarchy.get(order.status, 0)
        new_level = status_hierarchy.get(new_status, 0)
        
        # Prevent going backwards unless user is superuser
        if new_level < current_level and not request.user.is_superuser and new_status not in ['rejected', 'cancelled']:
            return JsonResponse({
                'success': False,
                'error': 'لا يمكن العودة إلى حالة سابقة إلا من قبل مدير النظام'
            }, status=403)
            
        valid_statuses = dict(ManufacturingOrder.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            logger.warning(f"[update_order_status] Invalid status: {new_status}. Valid statuses: {list(valid_statuses)}")
            return JsonResponse({
                'success': False, 
                'error': f'حالة غير صالحة. الحالات المتاحة: {list(valid_statuses)}',
                'received_status': new_status,
                'valid_statuses': list(valid_statuses)
            }, status=400)
        
        # Handle delivery status - require delivery fields
        if new_status == 'delivered':
            delivery_permit_number = request.POST.get('delivery_permit_number', '').strip()
            delivery_recipient_name = request.POST.get('delivery_recipient_name', '').strip()
            
            if not delivery_permit_number:
                return JsonResponse({
                    'success': False,
                    'error': 'رقم إذن التسليم مطلوب عند تغيير الحالة إلى "تم التسليم"'
                }, status=400)
            
            if not delivery_recipient_name:
                return JsonResponse({
                    'success': False,
                    'error': 'اسم المستلم مطلوب عند تغيير الحالة إلى "تم التسليم"'
            }, status=400)
        
        # Update order status
        old_status = order.status
        # logger.info(f"[update_order_status] Updating order {pk} status from {old_status} to {new_status}")  # معطل لتجنب الرسائل الكثيرة
        
        order.status = new_status
        order.updated_at = timezone.now()
        
        # Handle delivery fields
        if new_status == 'delivered':
            order.delivery_permit_number = request.POST.get('delivery_permit_number', '').strip()
            order.delivery_recipient_name = request.POST.get('delivery_recipient_name', '').strip()
            order.delivery_date = timezone.now()
            # logger.debug(f"[update_order_status] Set delivery fields for order {pk}")  # معطل لتجنب الرسائل الكثيرة
        
        # Set completion date if status is completed or ready for installation
        if new_status in ['completed', 'ready_install', 'delivered'] and not order.completion_date:
            order.completion_date = timezone.now()
            # logger.debug(f"[update_order_status] Set completion date to {order.completion_date}")  # معطل لتجنب الرسائل الكثيرة
        
        # Save the order
        try:
            save_fields = ['status', 'updated_at', 'completion_date']
            if new_status == 'delivered':
                save_fields.extend(['delivery_permit_number', 'delivery_recipient_name', 'delivery_date'])
            order.save(update_fields=save_fields)
            # logger.info(f"[update_order_status] Successfully updated order {pk}")  # معطل لتجنب الرسائل الكثيرة
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
        # logger.info(f"[update_order_status] Success response: {response_data}")  # معطل لتجنب الرسائل الكثيرة
        
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
            order_date=order.order_date.date() if order.order_date else timezone.now().date(),
            expected_delivery_date=order.expected_delivery_date,
            created_by=request.user
        )
        
        # إرسال إشعار بإنشاء أمر التصنيع
        try:
            from accounts.models import Notification
            # إنشاء إشعار للإدارة
            Notification.objects.create(
                title=f'تم إنشاء أمر تصنيع جديد',
                message=f'تم إنشاء أمر تصنيع للعميل {order.customer.name} - الطلب #{order.order_number}',
                priority='medium',
                link=manufacturing_order.get_absolute_url()
            )
        except Exception as e:
            # لا نريد أن يفشل إنشاء الطلب بسبب الإشعار
            pass
        
        # Add order items to manufacturing order
        for item in order.items.all():
            ManufacturingOrderItem.objects.create(
                manufacturing_order=manufacturing_order,
                product_name=item.product.name if item.product else f'منتج #{item.id}',
                quantity=item.quantity or 1,
                specifications=getattr(item, 'specifications', None) or getattr(item, 'notes', None) or 'لا توجد مواصفات'
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
            order_date__range=(start_date, end_date)
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
        order_date__range=(start_date, end_date)
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


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import ManufacturingOrder
import json

@require_POST
def update_approval_status(request, pk):
    """
    API endpoint to approve or reject manufacturing orders
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Check authentication
        if not request.user.is_authenticated:
            logger.warning("Unauthenticated approval attempt")
            return JsonResponse({
                'success': False, 
                'error': 'يجب تسجيل الدخول أولاً'
            }, status=401)
        
        # Check approval permission - only users with specific permission can approve
        if not (request.user.has_perm('manufacturing.can_approve_orders') or request.user.is_superuser):
            logger.warning(f"Permission denied for user {request.user.username}")
            return JsonResponse({
                'success': False, 
                'error': 'ليس لديك صلاحية الموافقة على أوامر التصنيع'
            }, status=403)
        
        # Get the manufacturing order
        try:
            order = ManufacturingOrder.objects.select_related('order', 'order__created_by').get(pk=pk)
        except ManufacturingOrder.DoesNotExist:
            logger.error(f"Manufacturing order {pk} not found")
            return JsonResponse({
                'success': False, 
                'error': 'لم يتم العثور على الطلب.'
            }, status=404)
        
        # Parse request data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return JsonResponse({
                'success': False, 
                'error': 'بيانات غير صالحة'
            }, status=400)
        
        action = data.get('action')

        # Validate action
        if action not in ['approve', 'reject']:
            return JsonResponse({
                'success': False, 
                'error': 'إجراء غير صالح.'
            }, status=400)

        # Check if order is still pending approval (allow rejection from other statuses)
        if order.status != 'pending_approval' and action == 'approve':
            return JsonResponse({
                'success': False, 
                'error': f'لا يمكن الموافقة على الطلب. الحالة الحالية: {order.get_status_display()}. يمكن الموافقة فقط على الطلبات في حالة "قيد الموافقة".'
            }, status=400)
        
        # For rejection, check if order is in a state that allows rejection
        if action == 'reject':
            # يُسمح بالرفض فقط من حالات معينة
            allowed_rejection_statuses = ['pending_approval', 'pending']
            
            if order.status == 'rejected':
                return JsonResponse({
                    'success': False, 
                    'error': 'هذا الطلب مرفوض بالفعل.'
                }, status=400)
            
            if order.status not in allowed_rejection_statuses:
                return JsonResponse({
                    'success': False, 
                    'error': 'لا يمكن رفض الطلب بعد دخوله مرحلة التنفيذ. يُسمح بالرفض فقط قبل بدء التصنيع.'
                }, status=400)

        with transaction.atomic():
            if action == 'approve':
                order.status = 'pending'  # The manufacturing process itself is now 'pending'
                order.rejection_reason = None
                order.save()
                
                # Create a notification for the user who created the original order
                if order.order and order.order.created_by:
                    try:
                        from accounts.models import Notification
                        recipient = order.order.created_by
                        title = f'بدء تصنيع طلب {order.order.customer.name}'
                        message = f'تمت الموافقة على أمر التصنيع للعميل {order.order.customer.name} - الطلب #{order.order.order_number}\nدخل الطلب مرحلة التصنيع. رقم أمر التصنيع #{order.pk}.'
                    
                        Notification.objects.create(
                            recipient=recipient,
                            title=title,
                            message=message,
                            priority='high',
                            link=order.get_absolute_url()
                        )
                        logger.info(f"Approval notification sent to {recipient.username}")
                    except Exception as e:
                        logger.error(f"Failed to create approval notification: {e}")
                
                # Update order tracking status to in_progress
                if order.order:
                    order.order.tracking_status = 'in_progress'
                    order.order.save(update_fields=['tracking_status'])

                logger.info(f"Order {pk} approved by {request.user.username}")
                return JsonResponse({
                    'success': True, 
                    'message': 'تمت الموافقة على الطلب وبدء التصنيع.'
                })

            elif action == 'reject':
                reason = data.get('reason', '').strip()
                if not reason:
                    return JsonResponse({
                        'success': False, 
                        'error': 'سبب الرفض مطلوب.'
                    }, status=400)
                
                order.status = 'rejected'
                order.rejection_reason = reason
                order.save()

                # Revert original order status if it was set to 'factory'
                original_order = order.order
                if hasattr(original_order, 'tracking_status') and original_order.tracking_status == 'factory':
                    original_order.tracking_status = 'processing'  # Or 'pending'
                    original_order.save(update_fields=['tracking_status'])

                # Create a notification for the user who created the original order
                if order.order and order.order.created_by:
                    try:
                        from accounts.models import Notification
                        Notification.objects.create(
                            recipient=order.order.created_by,
                            title=f'طلب مرفوض - {order.order.customer.name}',
                            message=f'تم رفض أمر التصنيع للعميل {order.order.customer.name} - الطلب #{order.order.order_number}\n\nسبب الرفض: "{reason}"\n\nيرجى مراجعة الطلب وإجراء التعديلات المطلوبة.',
                            priority='high',
                            link=order.get_absolute_url()
                        )
                        logger.info(f"Rejection notification sent to {order.order.created_by.username}")
                    except Exception as e:
                        logger.error(f"Failed to create rejection notification: {e}")
                
                # Update order tracking status to rejected
                if order.order:
                    order.order.tracking_status = 'rejected'
                    order.order.save(update_fields=['tracking_status'])

                logger.info(f"Order {pk} rejected by {request.user.username}, reason: {reason}")
                return JsonResponse({
                    'success': True, 
                    'message': 'تم رفض الطلب وإرسال إشعار للمستخدم.'
                })

    except Exception as e:
        logger.error(f"Unexpected error in update_approval_status: {e}")
        return JsonResponse({
            'success': False, 
            'error': 'حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.'
        }, status=500)


@require_POST
def send_reply(request, pk):
    """
    Send reply to rejection notification
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'يجب تسجيل الدخول أولاً'}, status=401)
        
        order = ManufacturingOrder.objects.select_related('order', 'order__created_by').get(pk=pk)
        
        # Check if user is the order creator or has permission
        if not (order.order.created_by == request.user or request.user.is_superuser):
            return JsonResponse({
                'success': False, 
                'error': 'ليس لديك صلاحية للرد على هذا الطلب'
            }, status=403)
        
        reply_message = request.POST.get('reply_message', '').strip()
        if not reply_message:
            return JsonResponse({'success': False, 'error': 'نص الرد مطلوب'}, status=400)
        
        # إرسال إشعار للمدير أو المستخدمين المخولين بالموافقة
        from django.contrib.auth import get_user_model
        from django.db import models
        User = get_user_model()
        
        # العثور على المستخدمين المخولين بالموافقة
        approval_users = User.objects.filter(
            models.Q(is_superuser=True) | 
            models.Q(user_permissions__codename='can_approve_orders')
        ).distinct()
        
        # إرسال إشعار لكل مستخدم مخول
        for user in approval_users:
            try:
                from accounts.models import Notification
                Notification.objects.create(
                    recipient=user,
                    title=f'رد على رفض أمر التصنيع #{order.id}',
                    message=f'رد من {order.order.created_by.get_full_name() or order.order.created_by.username}:\n\n{reply_message}\n\nأمر التصنيع: #{order.id}\nسبب الرفض الأصلي: {order.rejection_reason}',
                    priority='medium',
                    link=order.get_absolute_url()
                )
                logger.info(f"Reply notification sent to {user.username}")
            except Exception as e:
                logger.error(f"Failed to create reply notification for {user.username}: {e}")
        
        return JsonResponse({
            'success': True, 
            'message': 'تم إرسال الرد بنجاح للإدارة'
        })

    except ManufacturingOrder.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'لم يتم العثور على أمر التصنيع'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in send_reply: {e}")
        return JsonResponse({'success': False, 'error': f'حدث خطأ غير متوقع: {str(e)}'}, status=500)
