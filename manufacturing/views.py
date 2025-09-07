from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.urls import reverse_lazy, reverse


# ...existing code...


from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count, Sum, F, Case, When, Value, IntegerField
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models.functions import TruncDay, TruncMonth, ExtractMonth, ExtractYear
import logging
import json
from django.db import transaction
from django.conf import settings




from .models import ManufacturingOrder, ManufacturingOrderItem, FabricReceipt, FabricReceiptItem
from orders.models import Order
from accounts.models import Department
from accounts.utils import apply_default_year_filter

logger = logging.getLogger(__name__)


class ManufacturingOrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_list.html'
    context_object_name = 'manufacturing_orders'
    paginate_by = 25  # تفعيل Django pagination
    permission_required = 'manufacturing.view_manufacturingorder'
    
    def get_paginate_by(self, queryset):
        try:
            page_size = int(self.request.GET.get('page_size', 25))
            if page_size > 100:
                page_size = 100
            elif page_size < 1:
                page_size = 25
            return page_size
        except Exception:
            return 25
    
    def get_queryset(self):
        # Optimize the query by selecting related fields that exist
        queryset = ManufacturingOrder.objects.select_related(
            'order',  # This is the only direct foreign key in the model
            'order__customer',  # Access customer through order
            'production_line'  # Production line information
        ).order_by('expected_delivery_date', 'order_date')

        # تطبيق إعدادات العرض للمستخدم الحالي
        queryset = self.apply_display_settings_filter(queryset)

        # Apply filters - دعم الفلاتر المتعددة
        # فلتر الحالات (اختيار متعدد)
        status_filters = self.request.GET.getlist('status')
        if status_filters:
            queryset = queryset.filter(status__in=status_filters)

        # فلتر الفروع (اختيار متعدد)
        branch_filters = self.request.GET.getlist('branch')
        if branch_filters:
            branch_query = Q()
            for branch_id in branch_filters:
                try:
                    branch_id = int(branch_id)
                    branch_query |= Q(order__branch_id=branch_id)
                except (ValueError, TypeError):
                    continue
            if branch_query:
                queryset = queryset.filter(branch_query)

        # فلتر أنواع الطلبات (اختيار متعدد)
        order_type_filters = self.request.GET.getlist('order_type')
        if order_type_filters:
            queryset = queryset.filter(order_type__in=order_type_filters)

        # فلتر خطوط الإنتاج (اختيار متعدد)
        production_line_filters = self.request.GET.getlist('production_line')
        if production_line_filters:
            line_query = Q()
            for line_id in production_line_filters:
                if line_id == '':  # غير محدد
                    line_query |= Q(production_line__isnull=True)
                else:
                    try:
                        line_id = int(line_id)
                        line_query |= Q(production_line_id=line_id)
                    except (ValueError, TypeError):
                        continue
            if line_query:
                queryset = queryset.filter(line_query)

        # فلتر الطلبات المتأخرة
        overdue_filter = self.request.GET.get('overdue')
        if overdue_filter == 'true':
            today = timezone.now().date()
            queryset = queryset.filter(
                expected_delivery_date__lt=today,
                status__in=['pending_approval', 'pending', 'in_progress']
            )

        # البحث النصي
        search = self.request.GET.get('search')

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

        # فلتر التواريخ
        date_from = self.request.GET.get('date_from')
        if date_from:
            try:
                queryset = queryset.filter(order_date__gte=date_from)
            except:
                pass

        date_to = self.request.GET.get('date_to')
        if date_to:
            try:
                import datetime
                end_date = datetime.datetime.strptime(date_to, '%Y-%m-%d') + datetime.timedelta(days=1)
                queryset = queryset.filter(order_date__lt=end_date)
            except:
                pass

        # تطبيق الترتيب
        sort_column = self.request.GET.get('sort')
        sort_direction = self.request.GET.get('direction', 'asc')

        if sort_column and sort_direction != 'none':
            sort_field = self.get_sort_field(sort_column)
            if sort_field:
                if sort_direction == 'desc':
                    sort_field = f'-{sort_field}'
                queryset = queryset.order_by(sort_field)
            else:
                queryset = queryset.order_by('expected_delivery_date', 'order_date')
        else:
            queryset = queryset.order_by('expected_delivery_date', 'order_date')

        return queryset

    def get_sort_field(self, sort_column):
        """تحديد حقل الترتيب المناسب"""
        sort_fields = {
            'id': 'id',
            'order_number': 'order__order_number',
            'order_type': 'order_type',
            'contract_number': 'contract_number',
            'production_line': 'production_line__name',
            'invoice_number': 'invoice_number',
            'customer': 'order__customer__name',
            'salesperson': 'order__salesperson__name',
            'branch': 'order__branch__name',
            'order_date': 'order_date',
            'expected_delivery_date': 'expected_delivery_date',
            'status': 'status',
        }
        return sort_fields.get(sort_column)

    def apply_display_settings_filter(self, queryset):
        """تطبيق فلترة بناءً على إعدادات العرض للمستخدم الحالي"""
        try:
            from .models import ManufacturingDisplaySettings

            # التحقق من وجود فلاتر يدوية في الطلب
            manual_filters = self.has_manual_filters()

            # إذا كان هناك فلاتر يدوية، لا نطبق إعدادات العرض التلقائية
            if manual_filters:
                return queryset

            # الحصول على إعدادات العرض للمستخدم الحالي
            display_settings = ManufacturingDisplaySettings.get_user_settings(self.request.user)

            if display_settings:
                # تطبيق فلترة الحالات
                if display_settings.allowed_statuses:
                    queryset = queryset.filter(status__in=display_settings.allowed_statuses)

                # تطبيق فلترة أنواع الطلبات
                if display_settings.allowed_order_types:
                    queryset = queryset.filter(order_type__in=display_settings.allowed_order_types)

            return queryset
        except Exception as e:
            # في حالة حدوث خطأ، إرجاع الـ queryset الأصلي
            logger.warning(f"خطأ في تطبيق إعدادات العرض: {e}")
            return queryset

    def has_manual_filters(self):
        """التحقق من وجود فلاتر يدوية في الطلب"""
        # قائمة بمعاملات الفلترة اليدوية
        filter_params = [
            'status',           # فلتر الحالة
            'order_type',       # فلتر نوع الطلب
            'search',           # البحث
            'date_from',        # تاريخ من
            'date_to',          # تاريخ إلى
            'customer',         # فلتر العميل
            'salesperson',      # فلتر البائع
            'branch',           # فلتر الفرع
            'production_line',  # فلتر خط الإنتاج
            'contract_number',  # رقم العقد
            'invoice_number',   # رقم الفاتورة
        ]

        # التحقق من وجود أي من هذه المعاملات في الطلب
        for param in filter_params:
            if self.request.GET.get(param):
                return True

        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Count, Q
        from django.contrib.auth import get_user_model
        from .models import ManufacturingDisplaySettings
        
        # Get manufacturing orders for statistics (مفلترة بالسنة الافتراضية)
        # استخدام نفس الفلتر المطبق على القائمة
        filtered_orders = ManufacturingOrder.objects.select_related('order', 'order__customer')

        # تطبيق فلتر السنة الافتراضية على الإحصائيات
        from accounts.utils import apply_default_year_filter
        filtered_orders = apply_default_year_filter(filtered_orders, self.request, 'order_date')

        # Add necessary data for the form
        context.update({
            'status_choices': dict(ManufacturingOrder.STATUS_CHOICES),
            'order_types': dict(ManufacturingOrder.ORDER_TYPE_CHOICES),
        })
        
        # Add filter values to context - دعم الفلاتر المتعددة
        context.update({
            'status_filters': self.request.GET.getlist('status'),
            'branch_filters': self.request.GET.getlist('branch'),
            'order_type_filters': self.request.GET.getlist('order_type'),
            'production_line_filters': self.request.GET.getlist('production_line'),
            'overdue_filter': self.request.GET.get('overdue', ''),
            'search_query': self.request.GET.get('search', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'page_size': self.request.GET.get('page_size', 25),
        })

        # Add filter options
        from accounts.models import Branch
        from .models import ProductionLine
        context.update({
            'branches': Branch.objects.filter(is_active=True).order_by('name'),
            'production_lines': ProductionLine.objects.filter(is_active=True).order_by('name'),
            'order_types': ManufacturingOrder.ORDER_TYPE_CHOICES,  # فقط أنواع التصنيع (بدون معاينات)
        })

        # Add available display settings for filter dropdown
        try:
            context['available_display_settings'] = ManufacturingDisplaySettings.objects.filter(
                is_active=True
            ).order_by('-priority', 'name')
        except Exception:
            context['available_display_settings'] = []

        # Add production lines for filter dropdown
        from .models import ProductionLine
        context['production_lines'] = ProductionLine.objects.filter(is_active=True).order_by('-priority', 'name')

        # Add order types for filter dropdown (إخفاء نوع "معاينات" من فلاتر المصنع)
        context['order_types'] = [
            ('installation', 'تركيب'),
            ('custom', 'تفصيل'),
            ('accessory', 'إكسسوار'),
            ('delivery', 'تسليم'),
        ]
        
        # Add current date for date picker max date
        from datetime import date
        context['today'] = date.today().isoformat()
        
        # Add function to get available statuses for each order
        context['get_available_statuses'] = lambda current_status, order_type=None: self._get_available_statuses(self.request.user, current_status, order_type)
        
        # Add page_size to context
        context['page_size'] = self.get_paginate_by(self.get_queryset())



        # معلومات حالة الفلترة
        has_manual_filters = self.has_manual_filters()
        active_display_settings = None

        if not has_manual_filters:
            # الحصول على إعدادات العرض النشطة
            active_display_settings = ManufacturingDisplaySettings.get_user_settings(self.request.user)

        context.update({
            'has_manual_filters': has_manual_filters,
            'active_display_settings': active_display_settings,
            'display_settings_applied': not has_manual_filters and active_display_settings is not None,
        })

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


class VIPOrdersListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """عرض طلبات VIP فقط"""
    model = ManufacturingOrder
    template_name = 'manufacturing/vip_orders_list.html'
    context_object_name = 'vip_orders'
    paginate_by = 25
    permission_required = 'manufacturing.view_manufacturingorder'

    def get_queryset(self):
        """الحصول على طلبات VIP فقط"""
        queryset = ManufacturingOrder.objects.select_related(
            'order', 'order__customer'
        ).filter(
            order__status='vip'  # فلترة طلبات VIP فقط
        ).order_by('-created_at', 'expected_delivery_date')

        # تطبيق فلترة السنة الافتراضية
        queryset = apply_default_year_filter(queryset, self.request, 'order_date')

        # تطبيق فلاتر البحث إذا وجدت
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(order__order_number__icontains=search_query) |
                Q(order__customer__name__icontains=search_query) |
                Q(contract_number__icontains=search_query) |
                Q(invoice_number__icontains=search_query)
            )

        # فلترة حسب الحالة
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # فلترة حسب نوع الطلب
        order_type_filter = self.request.GET.get('order_type')
        if order_type_filter:
            queryset = queryset.filter(order_type=order_type_filter)

        # فلترة حسب إعداد العرض المحدد يدوياً
        display_setting_filter = self.request.GET.get('display_setting')
        if display_setting_filter:
            try:
                from .models import ManufacturingDisplaySettings
                display_setting = ManufacturingDisplaySettings.objects.get(
                    id=display_setting_filter,
                    is_active=True
                )

                # تطبيق فلترة الحالات
                if display_setting.allowed_statuses:
                    queryset = queryset.filter(status__in=display_setting.allowed_statuses)

                # تطبيق فلترة أنواع الطلبات
                if display_setting.allowed_order_types:
                    queryset = queryset.filter(order_type__in=display_setting.allowed_order_types)

            except Exception as e:
                logger.warning(f"خطأ في تطبيق إعداد العرض: {e}")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إحصائيات طلبات VIP
        vip_orders = self.get_queryset()

        # إحصائيات حسب الحالة
        status_stats = {}
        for status_code, status_display in ManufacturingOrder.STATUS_CHOICES:
            count = vip_orders.filter(status=status_code).count()
            if count > 0:
                status_stats[status_code] = {
                    'count': count,
                    'display': status_display
                }

        # إحصائيات حسب النوع
        type_stats = {}
        for type_code, type_display in ManufacturingOrder.ORDER_TYPE_CHOICES:
            count = vip_orders.filter(order_type=type_code).count()
            if count > 0:
                type_stats[type_code] = {
                    'count': count,
                    'display': type_display
                }

        # الطلبات المتأخرة
        today = timezone.now().date()
        # الطلبات المتأخرة هي التي لم تصل إلى "جاهز للتركيب" أو "مكتملة" أو "تم التسليم"
        overdue_count = vip_orders.filter(
            expected_delivery_date__lt=today,
            status__in=['pending_approval', 'pending', 'in_progress']  # فقط هذه الحالات تعتبر متأخرة
        ).count()

        context.update({
            'total_vip_orders': vip_orders.count(),
            'status_stats': status_stats,
            'type_stats': type_stats,
            'overdue_count': overdue_count,
            'search_query': self.request.GET.get('search', ''),
            'current_status_filter': self.request.GET.get('status', ''),
            'current_type_filter': self.request.GET.get('order_type', ''),
            'status_choices': ManufacturingOrder.STATUS_CHOICES,
            'order_type_choices': ManufacturingOrder.ORDER_TYPE_CHOICES,
        })

        return context


class ManufacturingOrderDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = ManufacturingOrder
    template_name = 'manufacturing/manufacturingorder_detail.html'
    context_object_name = 'manufacturing_order'
    permission_required = 'manufacturing.view_manufacturingorder'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # الحصول على عناصر الطلب الأساسي مع بيانات التقطيع
        if self.object.order:
            order_items = self.object.order.items.all()

            # إنشاء قاموس لبيانات التقطيع والاستلام
            items_data = []

            for item in order_items:
                # البحث عن عنصر التقطيع المرتبط
                cutting_item = None
                cutting_orders = self.object.order.cutting_orders.all()

                for cutting_order in cutting_orders:
                    cutting_item = cutting_order.items.filter(order_item=item).first()
                    if cutting_item:
                        break

                # البحث عن بيانات الاستلام
                # أولاً: البحث في FabricReceiptItem
                fabric_receipt_item = FabricReceiptItem.objects.filter(
                    order_item=item,
                    fabric_receipt__manufacturing_order=self.object
                ).first()

                fabric_receipt = fabric_receipt_item.fabric_receipt if fabric_receipt_item else None

                # إذا لم نجد في FabricReceiptItem، نبحث مباشرة في FabricReceipt
                if not fabric_receipt:
                    fabric_receipt = self.object.fabric_receipts.first()  # أخذ أول استلام مرتبط بأمر التصنيع

                # إنشاء كائن بيانات العنصر
                item_data = {
                    'order_item': item,
                    'cutting_receiver_name': cutting_item.receiver_name if cutting_item else None,
                    'cutting_permit_number': cutting_item.permit_number if cutting_item else None,
                    'cutting_date': cutting_item.cutting_date if cutting_item else None,
                    'cutting_status': cutting_item.status if cutting_item else None,
                    'has_cutting_data': cutting_item is not None,
                    'warehouse_name': cutting_item.cutting_order.warehouse.name if cutting_item else None,
                    'fabric_received': fabric_receipt is not None,  # تغيير هنا: إذا وجد استلام فهو مستلم
                    'bag_number': fabric_receipt.bag_number if fabric_receipt else None,
                    'fabric_received_date': fabric_receipt.receipt_date if fabric_receipt else None,
                    'fabric_receiver_name': fabric_receipt.received_by_name if fabric_receipt else None,
                }
                items_data.append(item_data)

            context['items_data'] = items_data

            # حساب إجمالي الكمية من عناصر الطلب الأساسي
            total_quantity = sum(item.quantity for item in order_items)
            context['total_quantity'] = total_quantity
        else:
            context['order_items'] = []
            context['total_quantity'] = 0

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



class ChangeProductionLineView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """تبديل خط الإنتاج لأمر تصنيع"""
    permission_required = 'manufacturing.change_manufacturingorder'

    def post(self, request, pk):
        """تبديل خط الإنتاج"""
        try:
            # الحصول على أمر التصنيع
            manufacturing_order = get_object_or_404(ManufacturingOrder, pk=pk)

            # الحصول على البيانات من JSON أو POST
            if request.content_type == 'application/json':
                import json
                data = json.loads(request.body)
                new_production_line_id = data.get('production_line_id')
                reason = data.get('reason', '')
            else:
                new_production_line_id = request.POST.get('production_line_id')
                reason = request.POST.get('reason', '')

            if not new_production_line_id:
                return JsonResponse({
                    'success': False,
                    'message': 'يجب اختيار خط إنتاج'
                })

            # التحقق من وجود خط الإنتاج
            from .models import ProductionLine
            try:
                new_production_line = ProductionLine.objects.get(
                    id=new_production_line_id,
                    is_active=True
                )
            except ProductionLine.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'خط الإنتاج المحدد غير موجود أو غير نشط'
                })

            # حفظ خط الإنتاج القديم للسجل
            old_production_line = manufacturing_order.production_line
            old_line_name = old_production_line.name if old_production_line else 'غير محدد'

            # تحديث خط الإنتاج
            manufacturing_order.production_line = new_production_line
            manufacturing_order.save()

            # تسجيل العملية في السجل
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType

            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(ManufacturingOrder).pk,
                object_id=manufacturing_order.pk,
                object_repr=str(manufacturing_order),
                action_flag=CHANGE,
                change_message=f'تم تبديل خط الإنتاج من "{old_line_name}" إلى "{new_production_line.name}"'
            )

            return JsonResponse({
                'success': True,
                'message': f'تم تبديل خط الإنتاج بنجاح إلى "{new_production_line.name}"',
                'new_line_name': new_production_line.name,
                'old_line_name': old_line_name
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })


@require_http_methods(["GET"])
def get_production_lines_api(request):
    """API لجلب خطوط الإنتاج النشطة"""
    try:
        from .models import ProductionLine

        lines = ProductionLine.objects.filter(is_active=True).order_by('-priority', 'name')

        lines_data = []
        for line in lines:
            lines_data.append({
                'id': line.id,
                'name': line.name,
                'description': line.description or '',
                'capacity_per_day': line.capacity_per_day,
                'priority': line.priority
            })

        return JsonResponse(lines_data, safe=False)

    except Exception as e:
        return JsonResponse({
            'error': f'حدث خطأ: {str(e)}'
        }, status=500)


class ProductionLinePrintView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """طباعة طلبات خط إنتاج محدد مع فلاتر متقدمة وصفحات"""
    model = ManufacturingOrder
    template_name = 'manufacturing/production_line_print.html'
    context_object_name = 'orders'
    paginate_by = 100  # عرض 100 طلب في كل صفحة
    permission_required = 'manufacturing.view_manufacturingorder'

    def get_queryset(self):
        """الحصول على طلبات خط الإنتاج مع تطبيق الفلاتر"""
        from .models import ProductionLine
        from accounts.models import Branch
        from django.db.models import Q
        import datetime

        # الحصول على خط الإنتاج
        line_id = self.kwargs.get('line_id')
        self.production_line = get_object_or_404(ProductionLine, id=line_id, is_active=True)

        # الحصول على طلبات خط الإنتاج
        queryset = ManufacturingOrder.objects.select_related(
            'order', 'order__customer', 'order__branch', 'order__salesperson'
        ).filter(production_line=self.production_line)

        # تطبيق الترتيب
        sort_column = self.request.GET.get('sort')
        sort_direction = self.request.GET.get('direction', 'asc')

        if sort_column and sort_direction != 'none':
            # تحديد حقل الترتيب
            sort_field = self.get_sort_field(sort_column)
            if sort_field:
                if sort_direction == 'desc':
                    sort_field = f'-{sort_field}'
                queryset = queryset.order_by(sort_field)
            else:
                queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-created_at')

        # فلتر الحالات (اختيار متعدد)
        status_filters = self.request.GET.getlist('status')
        if status_filters:
            queryset = queryset.filter(status__in=status_filters)

        # فلتر الفروع (اختيار متعدد)
        branch_filters = self.request.GET.getlist('branch')
        if branch_filters:
            branch_query = Q()
            for branch_id in branch_filters:
                try:
                    branch_id = int(branch_id)
                    branch_query |= Q(order__branch_id=branch_id) | Q(order__customer__branch_id=branch_id)
                except (ValueError, TypeError):
                    continue
            if branch_query:
                queryset = queryset.filter(branch_query)

        # فلتر نوع الطلب (اختيار متعدد)
        order_type_filters = self.request.GET.getlist('order_type')
        if order_type_filters:
            queryset = queryset.filter(order_type__in=order_type_filters)

        # فلتر الطلبات المتأخرة
        overdue_filter = self.request.GET.get('overdue')
        if overdue_filter == 'true':
            today = timezone.now().date()
            queryset = queryset.filter(
                expected_delivery_date__lt=today,
                status__in=['pending_approval', 'pending', 'in_progress']
            )

        # فلتر التواريخ
        date_from = self.request.GET.get('date_from')
        if date_from:
            try:
                queryset = queryset.filter(order_date__gte=date_from)
            except:
                pass

        date_to = self.request.GET.get('date_to')
        if date_to:
            try:
                end_date = datetime.datetime.strptime(date_to, '%Y-%m-%d') + datetime.timedelta(days=1)
                queryset = queryset.filter(order_date__lt=end_date)
            except:
                pass

        return queryset

    def get_sort_field(self, sort_column):
        """تحديد حقل الترتيب المناسب"""
        sort_fields = {
            'id': 'id',
            'manufacturing_code': 'manufacturing_code',
            'contract_number': 'contract_number',
            'invoice_number': 'invoice_number',
            'customer': 'order__customer__name',
            'order_type': 'order_type',
            'status': 'status',
            'order_date': 'order_date',
            'expected_delivery_date': 'expected_delivery_date',
            'branch': 'order__branch__name',
            'salesperson': 'order__salesperson__name',
        }
        return sort_fields.get(sort_column)

    def get_context_data(self, **kwargs):
        """إضافة البيانات الإضافية للسياق"""
        context = super().get_context_data(**kwargs)
        from accounts.models import Branch

        # إحصائيات خط الإنتاج
        all_orders = self.get_queryset()
        total_orders = all_orders.count()
        active_orders = all_orders.filter(
            status__in=['pending_approval', 'pending', 'in_progress']
        ).count()
        completed_orders = all_orders.filter(
            status__in=['ready_install', 'completed', 'delivered']
        ).count()
        overdue_orders = all_orders.filter(
            expected_delivery_date__lt=timezone.now().date(),
            status__in=['pending_approval', 'pending', 'in_progress']  # فقط هذه الحالات تعتبر متأخرة
        ).count()

        # الفلاتر المطبقة
        applied_filters = {
            'status_filters': self.request.GET.getlist('status'),
            'branch_filters': self.request.GET.getlist('branch'),
            'order_type_filters': self.request.GET.getlist('order_type'),
            'overdue_filter': self.request.GET.get('overdue'),
            'date_from': self.request.GET.get('date_from'),
            'date_to': self.request.GET.get('date_to'),
        }

        # خيارات الفلاتر
        # الحصول على أنواع الطلبات المدعومة في هذا الخط
        supported_order_types = []
        if hasattr(self.production_line, 'supported_order_types') and self.production_line.supported_order_types:
            for order_type in self.production_line.supported_order_types:
                for choice_code, choice_name in ManufacturingOrder.ORDER_TYPE_CHOICES:
                    if choice_code == order_type:
                        supported_order_types.append((choice_code, choice_name))
        else:
            # إذا لم تكن محددة، عرض جميع الأنواع
            supported_order_types = ManufacturingOrder.ORDER_TYPE_CHOICES

        filter_options = {
            'status_choices': ManufacturingOrder.STATUS_CHOICES,
            'order_type_choices': supported_order_types,
            'branches': Branch.objects.filter(is_active=True).order_by('name'),
        }

        context.update({
            'production_line': self.production_line,
            'total_orders': total_orders,
            'active_orders': active_orders,
            'completed_orders': completed_orders,
            'overdue_orders': overdue_orders,
            'applied_filters': applied_filters,
            'filter_options': filter_options,
            'print_date': timezone.now(),
            'filtered_count': context['orders'].count() if context.get('orders') else 0,
        })

        return context


class ProductionLinePrintTemplateView(ProductionLinePrintView):
    """طباعة تقرير خط الإنتاج بقالب بسيط"""
    template_name = 'manufacturing/production_line_print_template.html'
    paginate_by = None  # إزالة pagination للطباعة

    def get_context_data(self, **kwargs):
        # الحصول على جميع الطلبات المفلترة بدون pagination
        queryset = self.get_queryset()

        context = {
            'orders': queryset,
            'production_line': self.production_line,
            'total_orders': queryset.count(),
            'now': timezone.now(),
        }

        # إضافة معلومات الفلاتر المطبقة للعرض
        applied_filters = {}

        # فلاتر الحالة
        status_filters = self.request.GET.getlist('status')
        if status_filters:
            applied_filters['status'] = status_filters

        # فلاتر الفروع
        branch_filters = self.request.GET.getlist('branch')
        if branch_filters:
            applied_filters['branch'] = branch_filters

        # فلاتر نوع الطلب
        order_type_filters = self.request.GET.getlist('order_type')
        if order_type_filters:
            applied_filters['order_type'] = order_type_filters

        # فلتر التواريخ
        date_from = self.request.GET.get('date_from')
        if date_from:
            applied_filters['date_from'] = date_from

        date_to = self.request.GET.get('date_to')
        if date_to:
            applied_filters['date_to'] = date_to

        # فلتر الطلبات المتأخرة
        overdue_filter = self.request.GET.get('overdue')
        if overdue_filter == 'true':
            applied_filters['overdue'] = True

        context['applied_filters'] = applied_filters
        context['has_filters'] = bool(applied_filters)

        return context


class ProductionLinePDFView(ProductionLinePrintTemplateView):
    """تحميل تقرير خط الإنتاج كملف PDF"""

    def setup(self, request, *args, **kwargs):
        """إعداد المتغيرات المطلوبة"""
        super().setup(request, *args, **kwargs)
        # تهيئة production_line من get_queryset
        self.get_queryset()

    def get(self, request, *args, **kwargs):
        try:
            from django.http import HttpResponse
            from weasyprint import HTML, CSS
            from django.template.loader import render_to_string
            import io

            # الحصول على البيانات
            context = self.get_context_data()

            # رندر HTML
            html_string = render_to_string(self.template_name, context, request=request)

            # تحويل إلى PDF
            html = HTML(string=html_string, base_url=request.build_absolute_uri())

            # CSS إضافي للطباعة
            css = CSS(string='''
                @page {
                    size: A4;
                    margin: 1.5cm;
                }
                body {
                    font-family: 'Arial', sans-serif;
                    -webkit-print-color-adjust: exact;
                    print-color-adjust: exact;
                }
            ''')

            # إنشاء PDF
            pdf_file = html.write_pdf(stylesheets=[css])

            # إنشاء الاستجابة
            response = HttpResponse(pdf_file, content_type='application/pdf')
            filename = f"production_line_{self.production_line.name}_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except ImportError:
            # إذا لم تكن weasyprint مثبتة، استخدم طريقة بديلة
            from django.http import JsonResponse
            return JsonResponse({
                'error': 'مكتبة PDF غير متوفرة. يرجى استخدام خيار الطباعة العادي.',
                'message': 'PDF library not available. Please use regular print option.'
            }, status=500)

        except Exception as e:
            from django.http import JsonResponse
            return JsonResponse({
                'error': f'خطأ في إنشاء PDF: {str(e)}',
                'message': 'Error generating PDF'
            }, status=500)

    def get(self, request, *args, **kwargs):
        """معالجة طلبات GET مع دعم تصدير PDF"""
        try:
            # تحديد نوع الاستجابة (HTML أو PDF)
            if request.GET.get('format') == 'pdf':
                return self.generate_pdf()

            return super().get(request, *args, **kwargs)

        except Exception as e:
            messages.error(request, f'حدث خطأ: {str(e)}')
            return redirect('manufacturing:dashboard')

    def generate_pdf(self):
        """إنتاج ملف PDF للطلبات المفلترة"""
        try:
            from django.template.loader import render_to_string
            from weasyprint import HTML

            # الحصول على جميع الطلبات المفلترة (بدون صفحات للـ PDF)
            all_filtered_orders = self.get_queryset()

            context = self.get_context_data()
            context.update({
                'orders': all_filtered_orders,  # جميع الطلبات المفلترة للـ PDF
                'is_pdf': True,
                'user': self.request.user,
            })

            html_string = render_to_string('manufacturing/production_line_print_pdf.html', context)
            html = HTML(string=html_string)
            pdf = html.write_pdf()

            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"production_line_{self.production_line.name}_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response

        except Exception as e:
            messages.error(self.request, f'خطأ في إنتاج PDF: {str(e)}')
            return redirect('manufacturing:dashboard')


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
        
        # إنشاء سجل تغيير الحالة
        try:
            from orders.models import OrderStatusLog
            # الحصول على الحالة السابقة للطلب الأساسي
            original_order_old_status = order.order.tracking_status if order.order else 'pending'
            
            OrderStatusLog.objects.create(
                order=order.order,
                old_status=original_order_old_status,
                new_status=new_status,
                changed_by=request.user,
                notes=f'تم تغيير حالة أمر التصنيع من {dict(ManufacturingOrder.STATUS_CHOICES).get(old_status, "")} إلى {dict(ManufacturingOrder.STATUS_CHOICES).get(new_status, "")}'
            )
            logger.debug(f"[update_order_status] Created status log for order {pk}")
        except Exception as e:
            logger.error(f"[update_order_status] Error creating status log: {str(e)}", exc_info=True)
            # Continue even if status logging fails
        
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
        
        # تم حذف نظام الإشعارات
        
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

        # Get all manufacturing orders (بدون فلترة افتراضية)
        orders = ManufacturingOrder.objects.all().select_related('order', 'order__customer')
        
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
            'completed_orders': orders.filter(status__in=['ready_install', 'completed']).count(),
            'delivered_orders': orders.filter(status='delivered').count(),
            'cancelled_orders': orders.filter(status='cancelled').count(),
            'total_revenue': sum(order.order.total_amount for order in orders if order.order and order.order.total_amount),
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
        'completed_orders': orders.filter(status__in=['ready_install', 'completed']).count(),
        'delivered_orders': orders.filter(status='delivered').count(),
        'cancelled_orders': orders.filter(status='cancelled').count(),
        'status_data': {item['status']: item['count'] for item in status_counts},
        'last_updated': timezone.now().isoformat(),
    }
    
    return JsonResponse(data)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ManufacturingOrder

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
                
                # تم حذف نظام الإشعارات
                
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

                # تم حذف نظام الإشعارات
                
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


def get_order_details(request, pk):
    """
    Get manufacturing order details including rejection reply
    """
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'يجب تسجيل الدخول أولاً'
            }, status=401)
        
        order = ManufacturingOrder.objects.select_related(
            'order', 'order__created_by'
        ).get(pk=pk)
        
        # Check permission
        if not (request.user.has_perm('manufacturing.view_manufacturingorder') or
                request.user.is_superuser):
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية لعرض تفاصيل هذا الطلب'
            }, status=403)
        
        # Prepare order data
        order_data = {
            'id': order.id,
            'status': order.status,
            'status_display': order.get_status_display(),
            'rejection_reason': order.rejection_reason,
            'rejection_reply': order.rejection_reply,
            'rejection_reply_date': order.rejection_reply_date.isoformat() if order.rejection_reply_date else None,
            'has_rejection_reply': order.has_rejection_reply,
        }
        
        return JsonResponse({
            'success': True,
            'order': order_data
        })
        
    except ManufacturingOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'لم يتم العثور على أمر التصنيع'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting order details: {e}")
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ غير متوقع'
        }, status=500)


@csrf_exempt
@require_POST
def send_reply(request, pk):
    """
    Send reply to rejection notification
    """
    from django.utils import timezone
    
    try:
        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'يجب تسجيل الدخول أولاً'
            }, status=401)
        
        order = ManufacturingOrder.objects.select_related(
            'order', 'order__created_by'
        ).get(pk=pk)
        
        # Debug logging
        logger.info(f"User {request.user.username} trying to reply to order {pk}")
        logger.info(f"Order created_by: {order.order.created_by if order.order else None}")
        logger.info(f"User is_superuser: {request.user.is_superuser}")
        logger.info(f"User is_staff: {request.user.is_staff}")
        
        # Check if user is the order creator, has permission, or is staff
        can_reply = (
            request.user.is_superuser or
            request.user.is_staff or
            (order.order and order.order.created_by == request.user) or
            request.user.has_perm('manufacturing.can_approve_orders') or
            request.user.has_perm('orders.change_order')
        )
        
        logger.info(f"Can reply: {can_reply}")
        
        if not can_reply:
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية للرد على هذا الطلب'
            }, status=403)
        
        # Parse JSON request data
        try:
            data = json.loads(request.body)
            reply_message = data.get('reply_message', '').strip()
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'بيانات غير صالحة'
            }, status=400)
        
        if not reply_message:
            return JsonResponse({
                'success': False,
                'error': 'نص الرد مطلوب'
            }, status=400)
        
        # Save reply to the order
        order.rejection_reply = reply_message
        order.rejection_reply_date = timezone.now()
        order.has_rejection_reply = True
        order.save(update_fields=[
            'rejection_reply',
            'rejection_reply_date',
            'has_rejection_reply'
        ])
        
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
                customer_name = (order.order.created_by.get_full_name() or
                                 order.order.created_by.username)
                message = (f'رد من {customer_name}:\n\n{reply_message}\n\n'
                           f'أمر التصنيع: #{order.id}\n'
                           f'سبب الرفض الأصلي: {order.rejection_reason}')
                
                Notification.objects.create(
                    recipient=user,
                    title=f'رد على رفض أمر التصنيع #{order.id}',
                    message=message,
                    priority='medium',
                    link=order.get_absolute_url()
                )
                logger.info(f"Reply notification sent to {user.username}")
            except Exception as e:
                logger.error(
                    f"Failed to create reply notification for "
                    f"{user.username}: {e}"
                )
        
        return JsonResponse({
            'success': True,
            'message': 'تم إرسال الرد بنجاح للإدارة'
        })

    except ManufacturingOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'لم يتم العثور على أمر التصنيع'
        }, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in send_reply: {e}")
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ غير متوقع: {str(e)}'
        }, status=500)


@require_POST
def re_approve_after_reply(request, pk):
    """
    Re-approve manufacturing order after reply to rejection
    """
    import logging
    from django.db import transaction
    logger = logging.getLogger(__name__)
    
    try:
        # Check authentication
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'يجب تسجيل الدخول أولاً'
            }, status=401)
        
        # Check approval permission
        if not (request.user.has_perm('manufacturing.can_approve_orders') or
                request.user.is_superuser):
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية الموافقة على أوامر التصنيع'
            }, status=403)
        
        order = ManufacturingOrder.objects.select_related(
            'order', 'order__created_by'
        ).get(pk=pk)
        
        # Check if order was rejected and has a reply
        if order.status != 'rejected' or not order.has_rejection_reply:
            return JsonResponse({
                'success': False,
                'error': 'يمكن الموافقة فقط على الطلبات المرفوضة التي تم الرد عليها'
            }, status=400)
        
        with transaction.atomic():
            # Reset rejection status and approve
            order.status = 'pending'
            order.save(update_fields=['status'])
            
            # Update order tracking status to in_progress
            if order.order:
                order.order.tracking_status = 'factory'
                order.order.save(update_fields=['tracking_status'])
            
            # Create notification for the order creator
            if order.order and order.order.created_by:
                try:
                    customer_name = order.order.customer.name
                    title = f'تمت الموافقة على طلبك بعد المراجعة - {customer_name}'
                    message = (f'تمت الموافقة على أمر التصنيع للعميل '
                               f'{customer_name} - '
                               f'الطلب #{order.order.order_number}\n'
                               f'دخل الطلب مرحلة التصنيع. '
                               f'رقم أمر التصنيع #{order.pk}.')
                    
                    Notification.objects.create(
                        recipient=order.order.created_by,
                        title=title,
                        message=message,
                        priority='high',
                        link=order.get_absolute_url()
                    )
                    logger.info(
                        f"Re-approval notification sent to "
                        f"{order.order.created_by.username}"
                    )
                except Exception as e:
                    logger.error(f"Failed to create re-approval notification: {e}")
            
            logger.info(f"Order {pk} re-approved by {request.user.username}")
            return JsonResponse({
                'success': True,
                'message': 'تمت الموافقة على الطلب وبدء التصنيع بعد المراجعة.'
            })
    
    except ManufacturingOrder.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'لم يتم العثور على أمر التصنيع'
        }, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in re_approve_after_reply: {e}")
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ غير متوقع: {str(e)}'
        }, status=500)


# Views للوصول بالكود بدلاً من ID
from django.contrib.auth.decorators import login_required

@login_required
def manufacturing_order_detail_by_code(request, manufacturing_code):
    """عرض تفاصيل أمر التصنيع باستخدام كود التصنيع"""
    # البحث بطريقة محسنة للأداء
    if '-M' in manufacturing_code:
        order_number = manufacturing_code.replace('-M', '')
        manufacturing_order = get_object_or_404(
            ManufacturingOrder.objects.select_related('order', 'order__customer'),
            order__order_number=order_number
        )
    else:
        # للأكواد القديمة
        manufacturing_id = manufacturing_code.replace('#', '').replace('-M', '')
        manufacturing_order = get_object_or_404(
            ManufacturingOrder.objects.select_related('order', 'order__customer'),
            id=manufacturing_id
        )
    
    return ManufacturingOrderDetailView.as_view()(request, pk=manufacturing_order.pk)

@login_required
def manufacturing_order_detail_redirect(request, pk):
    """إعادة توجيه من ID إلى كود التصنيع"""
    manufacturing_order = get_object_or_404(ManufacturingOrder, pk=pk)
    return redirect('manufacturing:order_detail_by_code', manufacturing_code=manufacturing_order.manufacturing_code)


class OverdueOrdersListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """عرض أوامر التصنيع المتأخرة"""
    model = ManufacturingOrder
    template_name = 'manufacturing/overdue_orders.html'
    context_object_name = 'overdue_orders'
    paginate_by = 25
    permission_required = 'manufacturing.view_manufacturingorder'

    def get_queryset(self):
        """الحصول على أوامر التصنيع المتأخرة فقط"""
        # الحصول على جميع أوامر التصنيع
        queryset = ManufacturingOrder.objects.select_related(
            'order', 'order__customer'
        ).all()

        # تطبيق فلتر السنة الافتراضية
        queryset = apply_default_year_filter(queryset, self.request, 'order_date')

        # تطبيق فلاتر إضافية
        search = self.request.GET.get('search')
        branch = self.request.GET.get('branch')
        order_types = self.request.GET.getlist('order_types')

        if search:
            queryset = queryset.filter(
                Q(order__id__icontains=search) |
                Q(order__order_number__icontains=search) |
                Q(contract_number__icontains=search) |
                Q(order__customer__name__icontains=search) |
                Q(order__customer__phone__icontains=search)
            )

        if branch:
            queryset = queryset.filter(order__branch__id=branch)

        if order_types:
            # فلترة حسب أنواع الطلبات المختارة
            type_filter = Q()
            for order_type in order_types:
                type_filter |= Q(order__selected_types__contains=[order_type])
            queryset = queryset.filter(type_filter)

        # فلترة الطلبات المتأخرة فقط
        # الطلبات المتأخرة هي التي لم تصل إلى "جاهز للتركيب" أو "مكتملة" أو "تم التسليم"
        today = timezone.now().date()
        overdue_queryset = queryset.filter(
            expected_delivery_date__lt=today,
            status__in=['pending_approval', 'pending', 'in_progress']  # فقط هذه الحالات تعتبر متأخرة
        ).order_by('expected_delivery_date')

        return overdue_queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إحصائيات الطلبات المتأخرة
        overdue_orders = self.get_queryset()

        # تجميع حسب الحالة
        status_counts = overdue_orders.values('status').annotate(
            count=Count('status')
        )
        status_data = {item['status']: item['count'] for item in status_counts}

        # حساب متوسط التأخير
        today = timezone.now().date()
        total_delay_days = 0
        count = 0
        for order in overdue_orders:
            if order.expected_delivery_date:
                delay_days = (today - order.expected_delivery_date).days
                total_delay_days += delay_days
                count += 1

        avg_delay_days = round(total_delay_days / count, 1) if count > 0 else 0

        # الحصول على السنة الافتراضية
        from accounts.models import DashboardYearSettings
        default_year = DashboardYearSettings.get_default_year()

        context.update({
            'total_overdue': overdue_orders.count(),
            # الطلبات الجاهزة للتركيب لا تعتبر متأخرة أبداً
            'ready_install_overdue': 0,
            'avg_delay_days': avg_delay_days,
            'default_year': default_year,
        })

        # Add branches for filter dropdown
        from accounts.models import Branch
        context['branches'] = Branch.objects.all().order_by('name')

        # Add order types for filter dropdown
        context['order_types'] = [
            ('inspection', 'معاينة'),
            ('installation', 'تركيب'),
            ('accessory', 'إكسسوار'),
            ('tailoring', 'تسليم'),
        ]

        # Add selected order types for form persistence
        context['selected_order_types'] = self.request.GET.getlist('order_types')

        return context


# نظام استلام الأقمشة في المصنع
class FabricReceiptView(LoginRequiredMixin, TemplateView):
    """صفحة استلام الأقمشة في المصنع"""
    template_name = 'manufacturing/fabric_receipt.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # الحصول على أوامر التصنيع التي لها عناصر جاهزة للاستلام
        manufacturing_orders = ManufacturingOrder.objects.filter(
            items__receiver_name__isnull=False,
            items__permit_number__isnull=False,
            items__fabric_received=False
        ).select_related(
            'order', 'order__customer'
        ).prefetch_related(
            'items'
        ).distinct().order_by('-order_date')

        # فلترة حسب البحث
        search = self.request.GET.get('search')
        if search:
            manufacturing_orders = manufacturing_orders.filter(
                Q(order__contract_number__icontains=search) |
                Q(order__customer__name__icontains=search) |
                Q(order__customer__phone__icontains=search)
            )

        context.update({
            'manufacturing_orders': manufacturing_orders,
            'search_query': search or '',
        })

        return context


@login_required
def receive_fabric_item(request, item_id):
    """استلام قماش عنصر واحد"""
    if request.method == 'POST':
        try:
            item = get_object_or_404(ManufacturingOrderItem, pk=item_id)

            data = json.loads(request.body)
            bag_number = data.get('bag_number', '').strip()
            notes = data.get('notes', '').strip()

            if not bag_number:
                return JsonResponse({
                    'success': False,
                    'message': 'رقم الشنطة مطلوب'
                })

            # تعيين العنصر كمستلم
            item.mark_fabric_received(
                bag_number=bag_number,
                user=request.user,
                notes=notes
            )

            return JsonResponse({
                'success': True,
                'message': 'تم استلام القماش بنجاح'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})


@login_required
def bulk_receive_fabric(request, order_id):
    """استلام جميع أقمشة الطلب بنفس رقم الشنطة"""
    if request.method == 'POST':
        try:
            manufacturing_order = get_object_or_404(ManufacturingOrder, pk=order_id)

            data = json.loads(request.body)
            bag_number = data.get('bag_number', '').strip()
            notes = data.get('notes', '').strip()

            if not bag_number:
                return JsonResponse({
                    'success': False,
                    'message': 'رقم الشنطة مطلوب'
                })

            # استلام جميع العناصر الجاهزة للاستلام
            items_to_receive = manufacturing_order.items.filter(
                receiver_name__isnull=False,
                permit_number__isnull=False,
                fabric_received=False
            )

            received_count = 0
            for item in items_to_receive:
                item.mark_fabric_received(
                    bag_number=bag_number,
                    user=request.user,
                    notes=notes
                )
                received_count += 1

            return JsonResponse({
                'success': True,
                'message': f'تم استلام {received_count} عنصر بنجاح'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})


@login_required
def fabric_receipt_status_api(request, order_id):
    """API للحصول على حالة استلام الأقمشة لأمر تصنيع"""
    try:
        manufacturing_order = get_object_or_404(ManufacturingOrder, pk=order_id)

        items_data = []
        for item in manufacturing_order.items.all():
            items_data.append({
                'id': item.id,
                'product_name': item.product_name,
                'quantity': str(item.quantity),
                'receiver_name': item.receiver_name,
                'permit_number': item.permit_number,
                'cutting_date': item.cutting_date.isoformat() if item.cutting_date else None,
                'delivery_date': item.delivery_date.isoformat() if item.delivery_date else None,
                'bag_number': item.bag_number,
                'fabric_received': item.fabric_received,
                'fabric_received_date': item.fabric_received_date.isoformat() if item.fabric_received_date else None,
                'fabric_status': item.get_fabric_status_display(),
                'fabric_status_color': item.get_fabric_status_color(),
                'has_cutting_data': item.has_cutting_data,
            })

        return JsonResponse({
            'success': True,
            'order': {
                'id': manufacturing_order.id,
                'customer_name': manufacturing_order.order.customer.name if manufacturing_order.order else '',
                'contract_number': manufacturing_order.order.contract_number if manufacturing_order.order else '',
                'total_items': manufacturing_order.total_items_count,
                'received_items': manufacturing_order.received_items_count,
                'pending_items': manufacturing_order.pending_items_count,
                'completion_percentage': manufacturing_order.items_completion_percentage,
                'is_all_received': manufacturing_order.is_all_items_received,
                'status_display': manufacturing_order.get_items_status_display(),
                'status_color': manufacturing_order.get_items_status_color(),
            },
            'items': items_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


class FabricReceiptView(LoginRequiredMixin, ListView):
    """صفحة استلام الأقمشة في المصنع - أوامر التقطيع للتصنيع"""
    template_name = 'manufacturing/fabric_receipt.html'
    context_object_name = 'cutting_orders'
    paginate_by = 20

    def get_queryset(self):
        """الحصول على أوامر التقطيع الجاهزة للاستلام للتصنيع وجميع الأنواع الأخرى"""
        from cutting.models import CuttingOrder
        from django.db.models import Q

        queryset = CuttingOrder.objects.select_related(
            'order', 'order__customer', 'warehouse'
        ).prefetch_related(
            'items'
        ).filter(
            # أوامر التقطيع المكتملة
            status='completed',
            # التي تحتوي على عناصر مكتملة وجاهزة للاستلام
            items__status='completed',
            items__receiver_name__isnull=False,
            items__permit_number__isnull=False
        ).filter(
            # تضمين جميع أنواع الطلبات: تصنيع، تركيب، تسليم، إكسسوار
            Q(order__selected_types__icontains='manufacturing') |
            Q(order__selected_types__icontains='installation') |
            Q(order__selected_types__icontains='tailoring') |
            Q(order__selected_types__icontains='accessory')
        ).exclude(
            # استبعاد الأوامر التي تم استلامها بالفعل
            items__fabric_received=True
        ).distinct().order_by('-created_at')

        # البحث
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(cutting_code__icontains=search) |
                Q(order__contract_number__icontains=search) |
                Q(order__customer__name__icontains=search) |
                Q(order__customer__phone__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إحصائيات
        total_available_orders = self.get_queryset().count()
        context['total_available_orders'] = total_available_orders

        # معلومات الصفحات
        paginator = context.get('paginator')
        if paginator:
            context['total_pages'] = paginator.num_pages
            context['current_page'] = context['page_obj'].number

        return context


@login_required
def receive_cutting_order_for_manufacturing(request, cutting_order_id):
    """استلام أمر تقطيع للتصنيع عبر AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'طريقة غير مدعومة'})

    try:
        from cutting.models import CuttingOrder
        cutting_order = get_object_or_404(CuttingOrder, pk=cutting_order_id)

        # التحقق من وجود عناصر جاهزة للاستلام
        ready_items = cutting_order.items.filter(
            status='completed',
            receiver_name__isnull=False,
            permit_number__isnull=False,
            fabric_received=False
        )

        if not ready_items.exists():
            return JsonResponse({
                'success': False,
                'message': 'لا توجد عناصر جاهزة للاستلام في هذا الأمر'
            })

        data = json.loads(request.body)
        bag_number = data.get('bag_number', '')
        received_by_name = data.get('received_by_name', '')
        notes = data.get('notes', '')

        if not received_by_name:
            return JsonResponse({
                'success': False,
                'message': 'يجب إدخال اسم المستلم'
            })

        # إنشاء استلام الأقمشة
        fabric_receipt = FabricReceipt.objects.create(
            order=cutting_order.order,
            cutting_order=cutting_order,
            receipt_type='cutting_order',
            permit_number=ready_items.first().permit_number,
            bag_number=bag_number,
            received_by_name=received_by_name,
            received_by=request.user,
            notes=notes
        )

        # إنشاء عناصر الاستلام وتحديث حالة العناصر
        items_count = 0
        for item in ready_items:
            FabricReceiptItem.objects.create(
                fabric_receipt=fabric_receipt,
                cutting_item=item,
                order_item=item.order_item,
                quantity_received=item.order_item.quantity + item.additional_quantity,
                item_notes=item.notes or ''
            )

            # تحديث حالة العنصر
            item.fabric_received = True
            item.save()
            items_count += 1

        return JsonResponse({
            'success': True,
            'message': f'تم استلام {items_count} عنصر بنجاح',
            'receipt_id': fabric_receipt.id
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@login_required
def get_cutting_order_data(request, cutting_order_id):
    """جلب بيانات أمر التقطيع للاستلام"""
    try:
        from cutting.models import CuttingOrder
        cutting_order = get_object_or_404(CuttingOrder, pk=cutting_order_id)

        # الحصول على العناصر المكتملة والجاهزة للاستلام
        completed_items = cutting_order.items.filter(
            status='completed',
            receiver_name__isnull=False,
            permit_number__isnull=False,
            fabric_received=False
        )

        if completed_items.exists():
            # جلب البيانات من أول عنصر (عادة تكون نفس البيانات لجميع العناصر في نفس الأمر)
            first_item = completed_items.first()

            return JsonResponse({
                'success': True,
                'permit_number': first_item.permit_number,
                'receiver_name': first_item.receiver_name,
                'cutting_code': cutting_order.cutting_code,
                'customer_name': cutting_order.order.customer.name,
                'items_count': completed_items.count()
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'لا توجد عناصر جاهزة للاستلام في هذا الأمر'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@require_http_methods(["POST"])
def receive_fabric_item(request, item_id):
    """استلام عنصر واحد من الأقمشة"""
    try:
        item = get_object_or_404(ManufacturingOrderItem, id=item_id)

        # التحقق من أن العنصر جاهز للاستلام
        if not item.receiver_name or not item.permit_number:
            return JsonResponse({
                'success': False,
                'message': 'العنصر غير جاهز للاستلام'
            })

        if item.fabric_received:
            return JsonResponse({
                'success': False,
                'message': 'تم استلام هذا العنصر مسبقاً'
            })

        # تحديث حالة الاستلام
        item.fabric_received = True
        item.fabric_received_date = timezone.now()
        item.fabric_received_by = request.user
        item.save()

        # إرسال إشعار
        try:
            from notifications.signals import create_notification
            create_notification(
                title='تم استلام أقمشة',
                message=f'تم استلام أقمشة {item.product_name} في المصنع',
                notification_type='fabric_received',
                related_object=item,
                created_by=request.user
            )
        except:
            pass

        return JsonResponse({
            'success': True,
            'message': 'تم استلام العنصر بنجاح'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@require_http_methods(["POST"])
def receive_all_fabric_items(request, order_id):
    """استلام جميع عناصر أمر التصنيع الجاهزة"""
    try:
        order = get_object_or_404(ManufacturingOrder, id=order_id)

        # الحصول على العناصر الجاهزة للاستلام
        ready_items = order.items.filter(
            receiver_name__isnull=False,
            permit_number__isnull=False,
            fabric_received=False
        )

        if not ready_items.exists():
            return JsonResponse({
                'success': False,
                'message': 'لا توجد عناصر جاهزة للاستلام'
            })

        # استلام جميع العناصر
        received_count = 0
        for item in ready_items:
            item.fabric_received = True
            item.fabric_received_date = timezone.now()
            item.fabric_received_by = request.user
            item.save()
            received_count += 1

        # إرسال إشعار
        try:
            from notifications.signals import create_notification
            create_notification(
                title='استلام أقمشة جماعي',
                message=f'تم استلام {received_count} عنصر من أمر التصنيع #{order.id}',
                notification_type='fabric_received',
                related_object=order,
                created_by=request.user
            )
        except:
            pass

        return JsonResponse({
            'success': True,
            'message': f'تم استلام {received_count} عنصر بنجاح',
            'received_count': received_count
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@require_http_methods(["GET"])
def recent_fabric_receipts(request):
    """الحصول على آخر عمليات استلام الأقمشة"""
    try:
        recent_items = ManufacturingOrderItem.objects.filter(
            fabric_received=True
        ).select_related(
            'fabric_received_by'
        ).order_by('-fabric_received_date')[:10]

        receipts = []
        for item in recent_items:
            receipts.append({
                'product_name': item.product_name,
                'receiver_name': item.receiver_name,
                'permit_number': item.permit_number,
                'received_date': item.fabric_received_date.strftime('%d/%m/%Y %H:%M') if item.fabric_received_date else '',
                'received_by': item.fabric_received_by.get_full_name() if item.fabric_received_by else 'غير محدد'
            })

        return JsonResponse({
            'success': True,
            'receipts': receipts
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@require_http_methods(["POST"])
@login_required
def receive_cutting_order(request, cutting_order_id):
    """استلام أمر تقطيع كامل في المصنع"""
    try:
        from cutting.models import CuttingOrder
        cutting_order = get_object_or_404(CuttingOrder, id=cutting_order_id)

        # التحقق من أن أمر التقطيع مكتمل
        if cutting_order.status != 'completed':
            return JsonResponse({
                'success': False,
                'message': 'أمر التقطيع غير مكتمل بعد'
            })

        # التحقق من أن الطلب ليس نوع "منتجات"
        if 'products' in cutting_order.order.get_selected_types_list():
            return JsonResponse({
                'success': False,
                'message': 'طلبات المنتجات لا تحتاج استلام في المصنع - تكتمل تلقائياً بعد التقطيع'
            })

        data = json.loads(request.body)
        bag_number = data.get('bag_number', '').strip()
        notes = data.get('notes', '').strip()

        if not bag_number:
            return JsonResponse({
                'success': False,
                'message': 'رقم الشنطة مطلوب'
            })

        # إنشاء سجل استلام الأقمشة
        fabric_receipt = FabricReceipt.objects.create(
            receipt_type='cutting_order',
            order=cutting_order.order,
            cutting_order=cutting_order,
            bag_number=bag_number,
            received_by=request.user,
            notes=notes
        )

        # البحث عن أمر تصنيع موجود أو إنشاء جديد
        manufacturing_order, created = ManufacturingOrder.objects.get_or_create(
            order=cutting_order.order,
            defaults={
                'order_date': timezone.now().date(),
                'expected_delivery_date': timezone.now().date() + timedelta(days=7),
                'notes': f'تم إنشاؤه من أمر التقطيع {cutting_order.cutting_code}. {notes}'.strip()
            }
        )

        # ربط استلام الأقمشة بأمر التصنيع
        fabric_receipt.manufacturing_order = manufacturing_order
        fabric_receipt.save()

        # إنشاء عناصر التصنيع وعناصر الاستلام
        created_items = 0
        for cutting_item in cutting_order.items.all():
            # إنشاء عنصر التصنيع
            manufacturing_item = ManufacturingOrderItem.objects.create(
                manufacturing_order=manufacturing_order,
                order_item=cutting_item.order_item,
                product_name=cutting_item.order_item.product.name if cutting_item.order_item.product else 'منتج غير محدد',
                quantity=cutting_item.order_item.quantity,
                bag_number=bag_number,
                fabric_received=True,
                fabric_received_date=timezone.now(),
                fabric_received_by=request.user,
                fabric_notes=f'مستلم من أمر التقطيع {cutting_order.cutting_code}'
            )

            # إنشاء عنصر الاستلام
            FabricReceiptItem.objects.create(
                fabric_receipt=fabric_receipt,
                order_item=cutting_item.order_item,
                cutting_item=cutting_item,
                product_name=cutting_item.order_item.product.name if cutting_item.order_item.product else 'منتج غير محدد',
                quantity_received=cutting_item.order_item.quantity,
                item_notes=f'مستلم من عنصر التقطيع'
            )

            created_items += 1

        # تحديث حالة أمر التقطيع لتجنب الاستلام المكرر
        cutting_order.notes = f'{cutting_order.notes}\nتم استلامه في المصنع - أمر تصنيع #{manufacturing_order.id}'.strip()
        cutting_order.save()

        # إرسال إشعار
        try:
            from notifications.signals import create_notification
            create_notification(
                title='استلام أمر تقطيع',
                message=f'تم استلام أمر التقطيع {cutting_order.cutting_code} في المصنع وإنشاء أمر تصنيع #{manufacturing_order.id}',
                notification_type='cutting_received',
                related_object=manufacturing_order,
                created_by=request.user
            )
        except:
            pass

        return JsonResponse({
            'success': True,
            'message': f'تم استلام أمر التقطيع بنجاح وإنشاء أمر تصنيع #{manufacturing_order.id} مع {created_items} عنصر'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


class FabricReceiptDetailView(LoginRequiredMixin, DetailView):
    """عرض تفاصيل استلام الأقمشة"""
    model = None  # سيتم تحديده في get_object
    template_name = 'manufacturing/fabric_receipt_detail.html'
    context_object_name = 'fabric_receipt'

    def get_object(self, queryset=None):
        receipt_id = self.kwargs.get('receipt_id')
        return get_object_or_404(FabricReceipt, id=receipt_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fabric_receipt = self.get_object()

        # إضافة العناصر
        context['receipt_items'] = fabric_receipt.items.all().select_related(
            'order_item', 'cutting_item'
        )

        # إضافة معلومات إضافية
        context['total_items'] = fabric_receipt.items.count()
        context['total_quantity'] = fabric_receipt.items.aggregate(
            total=models.Sum('quantity_received')
        )['total'] or 0

        return context


class FabricReceiptListView(LoginRequiredMixin, ListView):
    """عرض قائمة استلامات الأقمشة"""
    template_name = 'manufacturing/fabric_receipt_list.html'
    context_object_name = 'fabric_receipts'
    paginate_by = 20

    def get_queryset(self):
        return FabricReceipt.objects.select_related(
            'order', 'order__customer', 'order__customer__branch',
            'cutting_order', 'manufacturing_order', 'received_by'
        ).order_by('-receipt_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إحصائيات
        context['total_receipts'] = FabricReceipt.objects.count()
        context['today_receipts'] = FabricReceipt.objects.filter(
            receipt_date__date=timezone.now().date()
        ).count()
        this_week_count = FabricReceipt.objects.filter(
            receipt_date__gte=timezone.now().date() - timedelta(days=7)
        ).count()
        context['this_week_receipts'] = this_week_count
        context['daily_average'] = round(this_week_count / 7, 1) if this_week_count > 0 else 0

        return context


@require_http_methods(["POST"])
@login_required
def cleanup_products_manufacturing_orders(request):
    """حذف أوامر التصنيع الخاطئة لطلبات المنتجات"""
    try:
        # البحث عن أوامر التصنيع لطلبات المنتجات
        products_manufacturing_orders = ManufacturingOrder.objects.filter(
            order__selected_types__contains=['products']
        )

        deleted_count = products_manufacturing_orders.count()

        # حذف أوامر التصنيع
        products_manufacturing_orders.delete()

        return JsonResponse({
            'success': True,
            'message': f'تم حذف {deleted_count} أمر تصنيع خاطئ لطلبات المنتجات',
            'deleted_count': deleted_count
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@require_http_methods(["POST"])
@login_required
def fix_manufacturing_order_items(request):
    """إصلاح العناصر المفقودة في أوامر التصنيع"""
    try:
        # البحث عن أوامر التصنيع بدون عناصر
        orders_without_items = ManufacturingOrder.objects.filter(items__isnull=True).distinct()

        fixed_count = 0
        for manufacturing_order in orders_without_items:
            # البحث عن أمر التقطيع المرتبط
            cutting_orders = manufacturing_order.order.get_cutting_orders()

            if cutting_orders:
                cutting_order = cutting_orders.first()

                # إنشاء العناصر من أمر التقطيع
                for cutting_item in cutting_order.items.all():
                    ManufacturingOrderItem.objects.create(
                        manufacturing_order=manufacturing_order,
                        order_item=cutting_item.order_item,
                        product_name=cutting_item.order_item.product.name if cutting_item.order_item.product else 'منتج غير محدد',
                        quantity=cutting_item.order_item.quantity,
                        fabric_received=False,  # لم يتم الاستلام بعد
                        fabric_notes=f'تم إنشاؤه من أمر التقطيع {cutting_order.cutting_code}'
                    )

                fixed_count += 1

        return JsonResponse({
            'success': True,
            'message': f'تم إصلاح {fixed_count} أمر تصنيع',
            'fixed_count': fixed_count
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@require_http_methods(["POST"])
@login_required
def create_manufacturing_receipt(request):
    """إنشاء استلام أقمشة من المصنع"""
    try:
        manufacturing_order_id = request.POST.get('manufacturing_order_id')
        bag_number = request.POST.get('bag_number')
        received_by_name = request.POST.get('received_by_name')
        notes = request.POST.get('notes', '')

        if not all([manufacturing_order_id, bag_number, received_by_name]):
            return JsonResponse({
                'success': False,
                'message': 'جميع الحقول مطلوبة'
            })

        # الحصول على أمر التصنيع
        manufacturing_order = ManufacturingOrder.objects.get(id=manufacturing_order_id)

        # التحقق من عدم وجود استلام سابق
        if FabricReceipt.objects.filter(manufacturing_order=manufacturing_order).exists():
            return JsonResponse({
                'success': False,
                'message': 'تم استلام هذا الأمر من قبل'
            })

        # الحصول على بيانات التقطيع المرتبطة
        cutting_orders = manufacturing_order.order.cutting_orders.filter(status='completed')
        cutting_permit_number = None
        cutting_receiver_name = None

        if cutting_orders.exists():
            # أخذ البيانات من أول أمر تقطيع مكتمل
            cutting_order = cutting_orders.first()
            cutting_items = cutting_order.items.filter(
                receiver_name__isnull=False,
                permit_number__isnull=False
            )

            if cutting_items.exists():
                cutting_item = cutting_items.first()
                cutting_permit_number = cutting_item.permit_number
                cutting_receiver_name = cutting_item.receiver_name

        # إنشاء استلام الأقمشة
        fabric_receipt = FabricReceipt.objects.create(
            order=manufacturing_order.order,
            manufacturing_order=manufacturing_order,
            receipt_type='manufacturing_order',
            permit_number=cutting_permit_number or manufacturing_order.manufacturing_code,
            bag_number=bag_number,
            received_by_name=cutting_receiver_name or received_by_name,
            received_by=request.user,
            notes=notes
        )

        return JsonResponse({
            'success': True,
            'message': f'تم إنشاء استلام الأقمشة بنجاح',
            'receipt_id': fabric_receipt.id
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


@require_http_methods(["GET"])
@login_required
def get_cutting_data(request, manufacturing_order_id):
    """جلب بيانات التقطيع المرتبطة بأمر التصنيع"""
    try:
        manufacturing_order = ManufacturingOrder.objects.get(id=manufacturing_order_id)

        # الحصول على بيانات التقطيع المرتبطة
        cutting_orders = manufacturing_order.order.cutting_orders.filter(status='completed')
        cutting_permit_number = None
        cutting_receiver_name = None

        if cutting_orders.exists():
            cutting_order = cutting_orders.first()
            cutting_items = cutting_order.items.filter(
                receiver_name__isnull=False,
                permit_number__isnull=False
            )

            if cutting_items.exists():
                cutting_item = cutting_items.first()
                cutting_permit_number = cutting_item.permit_number
                cutting_receiver_name = cutting_item.receiver_name

        return JsonResponse({
            'success': True,
            'cutting_permit_number': cutting_permit_number,
            'cutting_receiver_name': cutting_receiver_name
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })


class ProductReceiptView(LoginRequiredMixin, TemplateView):
    """صفحة استلام المنتجات من المخازن"""
    template_name = 'manufacturing/product_receipt.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # الحصول على أوامر التقطيع المكتملة لطلبات المنتجات
        from cutting.models import CuttingOrder
        # الحصول على أوامر التقطيع المكتملة لطلبات المنتجات (حل جذري مبسط)
        from .models import ProductReceipt

        # جميع أوامر التقطيع المكتملة للمنتجات (إصلاح JSONField)
        from django.db.models import Q
        cutting_orders_ready = CuttingOrder.objects.filter(
            status='completed'
        ).filter(
            Q(order__selected_types__icontains='products')
        ).select_related(
            'order', 'order__customer', 'warehouse'
        ).prefetch_related(
            'items'
        ).order_by('-created_at')

        # استبعاد المستلمة بالفعل
        received_cutting_order_ids = ProductReceipt.objects.values_list('cutting_order_id', flat=True)
        cutting_orders_ready = cutting_orders_ready.exclude(id__in=received_cutting_order_ids)

        # Debug info
        print(f"DEBUG: أوامر التقطيع المكتملة للمنتجات: {CuttingOrder.objects.filter(status='completed').filter(Q(order__selected_types__icontains='products')).count()}")
        print(f"DEBUG: أوامر التقطيع المستلمة: {len(received_cutting_order_ids)}")
        print(f"DEBUG: أوامر التقطيع الجاهزة للاستلام: {cutting_orders_ready.count()}")

        # إحصائيات
        total_pending_items = cutting_orders_ready.count()
        received_today = ProductReceipt.objects.filter(
            receipt_date__date=timezone.now().date()
        ).count()

        # آخر الاستلامات
        recent_receipts = ProductReceipt.objects.select_related(
            'cutting_order', 'cutting_order__order', 'cutting_order__order__customer', 'cutting_order__warehouse'
        ).order_by('-receipt_date')[:10]

        context.update({
            'cutting_orders_ready': cutting_orders_ready,
            'total_pending_items': total_pending_items,
            'received_today': received_today,
            'total_cutting_ready': cutting_orders_ready.count(),
            'recent_receipts': recent_receipts
        })

        return context


class ProductReceiptsListView(TemplateView):
    """صفحة قائمة استلامات المنتجات"""
    template_name = 'manufacturing/product_receipts_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # الحصول على جميع الاستلامات مع التفاصيل
        from .models import ProductReceipt
        receipts = ProductReceipt.objects.select_related(
            'cutting_order',
            'cutting_order__order',
            'cutting_order__order__customer',
            'cutting_order__warehouse'
        ).prefetch_related(
            'cutting_order__items'
        ).order_by('-receipt_date')

        # تجميع الاستلامات حسب العميل
        receipts_by_customer = {}
        for receipt in receipts:
            customer_name = receipt.cutting_order.order.customer.name
            if customer_name not in receipts_by_customer:
                receipts_by_customer[customer_name] = []
            receipts_by_customer[customer_name].append(receipt)

        # إحصائيات
        total_receipts = receipts.count()
        today_receipts = receipts.filter(receipt_date__date=timezone.now().date()).count()

        context.update({
            'receipts_by_customer': receipts_by_customer,
            'total_receipts': total_receipts,
            'today_receipts': today_receipts,
        })

        return context


@require_http_methods(["POST"])
@login_required
def create_product_receipt(request):
    """إنشاء استلام منتج من المخزن"""
    try:
        cutting_order_id = request.POST.get('cutting_order_id')
        bag_number = request.POST.get('bag_number')
        received_by_name = request.POST.get('received_by_name')
        notes = request.POST.get('notes', '')

        if not all([cutting_order_id, bag_number, received_by_name]):
            return JsonResponse({
                'success': False,
                'message': 'جميع الحقول مطلوبة'
            })

        # الحصول على أمر التقطيع
        from cutting.models import CuttingOrder
        cutting_order = CuttingOrder.objects.get(id=cutting_order_id)

        # التحقق من أن الأمر مكتمل
        if cutting_order.status != 'completed':
            return JsonResponse({
                'success': False,
                'message': 'أمر التقطيع غير مكتمل بعد'
            })

        # التحقق من أن الطلب نوع "منتجات"
        if 'products' not in cutting_order.order.get_selected_types_list():
            return JsonResponse({
                'success': False,
                'message': 'هذا الطلب ليس من نوع المنتجات'
            })

        # التحقق من عدم وجود استلام سابق
        from .models import ProductReceipt
        if ProductReceipt.objects.filter(cutting_order=cutting_order).exists():
            return JsonResponse({
                'success': False,
                'message': 'تم استلام هذا الأمر من قبل'
            })

        # إنشاء استلام المنتج
        product_receipt = ProductReceipt.objects.create(
            order=cutting_order.order,
            cutting_order=cutting_order,
            permit_number=cutting_order.cutting_code,
            bag_number=bag_number,
            received_by_name=received_by_name,
            received_by_user=request.user,
            notes=notes
        )

        return JsonResponse({
            'success': True,
            'message': f'تم إنشاء استلام المنتج بنجاح',
            'receipt_id': product_receipt.id
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })
