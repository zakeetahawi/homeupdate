from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse, path
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseRedirect
from datetime import datetime
from .models import (
    Order, OrderItem, Payment, OrderStatusLog, 
    ManufacturingDeletionLog, DeliveryTimeSettings
)
# from .extended_models import ExtendedOrder, AccessoryItem, FabricOrder # Deletion


class YearFilter(admin.SimpleListFilter):
    """فلتر السنة للطلبات"""
    title = _('السنة')
    parameter_name = 'year'

    def lookups(self, request, model_admin):
        years = Order.objects.dates('order_date', 'year', order='DESC')
        year_choices = [('all', _('جميع السنوات'))]
        for year in years:
            year_choices.append((str(year.year), str(year.year)))
        return year_choices

    def queryset(self, request, queryset):
        if self.value() == 'all':
            return queryset
        elif self.value():
            try:
                year = int(self.value())
                return queryset.filter(order_date__year=year)
            except (ValueError, TypeError):
                return queryset
        return queryset

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ('total_price',)
    
    def get_formset(self, request, obj=None, **kwargs):
        if obj is None:
            self.extra = 0
        else:
            self.extra = 1
        formset = super().get_formset(request, obj, **kwargs)
        
        # تخصيص widgets لدعم القيم العشرية
        formset.form.base_fields['quantity'].widget.attrs.update({
            'type': 'number',
            'min': '0.001',
            'step': '0.001',
            'placeholder': 'مثال: 4.25'
        })
        formset.form.base_fields['unit_price'].widget.attrs.update({
            'type': 'number',
            'min': '0',
            'step': '0.01',
            'placeholder': 'مثال: 150.50'
        })
        
        # تحسين: استخدام queryset محسن للمنتجات
        from inventory.models import Product
        formset.form.base_fields['product'].queryset = Product.objects.select_related('category').only(
            'id', 'name', 'price', 'category__name'
        )
        
        return formset

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1
    readonly_fields = ('payment_date',)

    def get_formset(self, request, obj=None, **kwargs):
        if obj is None:
            self.extra = 0
        else:
            self.extra = 1
        return super().get_formset(request, obj, **kwargs)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_per_page = 20  # تقليل من 50 إلى 20 لتحسين الأداء
    list_max_show_all = 50  # تقليل من 100 إلى 50
    show_full_result_count = False  # تعطيل عدد النتائج لتحسين الأداء
    list_display = (
        'order_number_display', 
        'customer', 
        'order_type_display',
        'status_display', 
        'tracking_status', 
        'salesperson',
        'branch',
        'final_price', 
        'payment_status', 
        'expected_delivery_date',
        'order_year', 
        'created_at'
    )
    def get_sortable_by(self, request):
        return self.list_display
    sortable_by = [
        'order_number',
        'customer__name',
        'order_type',
        'status',
        'tracking_status',
        'salesperson__user__username',
        'branch__name',
        'final_price',
        'payment_verified',
        'expected_delivery_date',
        'order_date',
        'created_at'
    ]
    ordering = ['-order_date', '-id']
    list_display_links = ['order_number_display']
    list_filter = (
        YearFilter,
        'status',
        'tracking_status',
        'order_status',
        'payment_verified',
        'delivery_type',
        'salesperson',
        'branch',
        'related_inspection_type',
    )
    search_fields = (
        'order_number', 
        'customer__name', 
        'customer__phone',
        'invoice_number', 
        'invoice_number_2', 
        'invoice_number_3', 
        'contract_number', 
        'contract_number_2', 
        'contract_number_3',
        'salesperson__name',
        'notes'
    )
    inlines = [OrderItemInline, PaymentInline]
    readonly_fields = (
        'created_at',
        'updated_at',
        'order_date',
        'order_number',
        'final_price',
    )
    date_hierarchy = 'order_date'
    actions = ['mark_as_paid', 'create_manufacturing_order', 'export_orders']
    
    def get_queryset(self, request):
        """تحسين الاستعلامات باستخدام select_related و prefetch_related"""
        return super().get_queryset(request).select_related(
            'customer', 'salesperson', 'branch'
        ).prefetch_related(
            'items__product', 'payments'
        )

    def mark_as_paid(self, request, queryset):
        updated = 0
        for order in queryset:
            if not order.is_fully_paid:
                order.paid_amount = order.final_price
                order.payment_verified = True
                order.save(update_fields=['paid_amount', 'payment_verified'])
                updated += 1
        self.message_user(
            request,
            f'تم تحديث {updated} طلب كمدفوع بالكامل.',
            level='SUCCESS' if updated > 0 else 'WARNING'
        )
    mark_as_paid.short_description = 'تحديد كمدفوع بالكامل'

    def create_manufacturing_order(self, request, queryset):
        from manufacturing.models import ManufacturingOrder
        created = 0
        for order in queryset:
            if not ManufacturingOrder.objects.filter(order=order).exists():
                order_types = order.get_selected_types_list()
                if any(t in ['installation', 'tailoring', 'accessory'] for t in order_types):
                    ManufacturingOrder.objects.create(
                        order=order,
                        order_type='installation' if 'installation' in order_types else 'detail',
                        contract_number=order.contract_number,
                        order_date=order.order_date.date() if order.order_date else timezone.now().date(),
                        expected_delivery_date=order.expected_delivery_date,
                        created_by=request.user
                    )
                    created += 1
        self.message_user(
            request,
            f'تم إنشاء {created} أمر تصنيع.',
            level='SUCCESS' if created > 0 else 'WARNING'
        )
    create_manufacturing_order.short_description = 'إنشاء أوامر تصنيع'

    def export_orders(self, request, queryset):
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow([
            'رقم الطلب', 'العميل', 'نوع الطلب', 'حالة الطلب', 
            'البائع', 'الفرع', 'السعر النهائي', 'المدفوع', 
            'تاريخ الإنشاء', 'تاريخ التسليم المتوقع'
        ])
        for order in queryset:
            writer.writerow([
                order.order_number,
                order.customer.name if order.customer else '',
                ', '.join(order.get_selected_types_list()),
                order.get_status_display(),
                order.salesperson.name if order.salesperson else '',
                order.branch.name if order.branch else '',
                order.final_price,
                order.paid_amount,
                order.created_at.strftime('%Y-%m-%d') if order.created_at else '',
                order.expected_delivery_date.strftime('%Y-%m-%d') if order.expected_delivery_date else ''
            ])
        return response
    export_orders.short_description = 'تصدير إلى CSV'

    fieldsets = (
        (_('معلومات العميل والطلب'), {
            'fields': ('customer', 'order_number', 'salesperson', 'branch')
        }),
        (_('نوع الطلب وحالته'), {
            'fields': ('selected_types', 'status', 'tracking_status', 'expected_delivery_date')
        }),
        (_('معلومات الفواتير والعقود'), {
            'fields': (
                'invoice_number', 'invoice_number_2', 'invoice_number_3',
                'contract_number', 'contract_number_2', 'contract_number_3',
                'contract_file'
            ),
            'classes': ('collapse',)
        }),
        (_('معلومات التسليم'), {
            'fields': ('delivery_type', 'delivery_address')
        }),
        (_('المعاينة المرتبطة'), {
            'fields': ('related_inspection', 'related_inspection_type'),
            'classes': ('collapse',)
        }),
        (_('معلومات مالية'), {
            'fields': ('final_price', 'paid_amount', 'payment_verified')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at', 'order_date', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def order_type_display(self, obj):
        selected_types = obj.get_selected_types_list()
        if selected_types:
            type_map = {
                'installation': '🔧 تركيب',
                'tailoring': '✂️ تفصيل', 
                'accessory': '💎 إكسسوار',
                'inspection': '👁️ معاينة'
            }
            type_names = [type_map.get(t, t) for t in selected_types]
            return ', '.join(type_names)
        return obj.get_order_type_display()
    order_type_display.short_description = 'نوع الطلب'
    order_type_display.admin_order_field = 'order_type'

    def status_display(self, obj):
        colors = {
            'normal': '#17a2b8',
            'vip': '#ffc107',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'وضع الطلب'
    status_display.admin_order_field = 'status'

    def order_status_display(self, obj):
        colors = {
            'pending_approval': '#ffc107',
            'pending': '#17a2b8',
            'in_progress': '#007bff',
            'ready_install': '#6f42c1',
            'completed': '#28a745',
            'delivered': '#20c997',
            'rejected': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.order_status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_order_status_display()
        )
    order_status_display.short_description = 'حالة الطلب'

    def payment_status(self, obj):
        if obj.is_fully_paid:
            return format_html('<span style="color: green;">مدفوع بالكامل</span>')
        elif obj.paid_amount > 0:
            return format_html('<span style="color: orange;">مدفوع جزئياً</span>')
        return format_html('<span style="color: red;">غير مدفوع</span>')
    payment_status.short_description = 'حالة الدفع'
    payment_status.admin_order_field = 'payment_verified'

    def order_year(self, obj):
        return obj.order_date.year if obj.order_date else '-'
    order_year.short_description = 'السنة'
    order_year.admin_order_field = 'order_date'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'customer', 'customer__branch', 'salesperson', 'branch', 'created_by', 'related_inspection'
        ).prefetch_related(
            'items__product', 'payments'
        ).only(
            'id', 'order_number', 'order_type', 'status', 'tracking_status', 'final_price',
            'payment_verified', 'expected_delivery_date', 'order_date', 'created_at',
            'customer__id', 'customer__name', 'customer__branch__name',
            'salesperson__id',
            'branch__id', 'branch__name',
            'created_by__id',
            'related_inspection__id'
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if hasattr(form.base_fields, 'salesperson'):
            if not request.user.is_superuser and hasattr(request.user, 'branch') and request.user.branch:
                form.base_fields['salesperson'].queryset = form.base_fields['salesperson'].queryset.filter(
                    branch=request.user.branch, 
                    is_active=True
                )
        if hasattr(form.base_fields, 'customer'):
            if not request.user.is_superuser:
                if hasattr(request.user, 'branch') and request.user.branch:
                    form.base_fields['customer'].queryset = form.base_fields['customer'].queryset.filter(
                        branch=request.user.branch,
                        status='active'
                    )
        return form

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'by-code/<str:order_code>/',
                self.admin_site.admin_view(self.order_by_code_view),
                name='orders_order_by_code',
            ),
        ]
        return custom_urls + urls

    def order_by_code_view(self, request, order_code):
        try:
            order = Order.objects.get(order_number=order_code)
            return HttpResponseRedirect(
                reverse('admin:orders_order_change', args=[order.pk])
            )
        except Order.DoesNotExist:
            self.message_user(request, f'الطلب بكود {order_code} غير موجود', level='error')
            return HttpResponseRedirect(reverse('admin:orders_order_changelist'))

    def order_number_display(self, obj):
        if not obj or not obj.order_number:
            return '-'
        try:
            view_url = reverse('orders:order_detail_by_code', kwargs={'order_code': obj.order_number})
            admin_url = reverse('admin:orders_order_by_code', kwargs={'order_code': obj.order_number})
            return format_html(
                '<strong>{}</strong><br/>'
                '<a href="{}" target="_blank" title="عرض في الواجهة">'
                '<span style="color: #0073aa;">👁️ عرض</span></a> | '
                '<a href="{}" title="تحرير في لوحة التحكم">'
                '<span style="color: #d63638;">✏️ تحرير</span></a>',
                obj.order_number,
                view_url,
                admin_url
            )
        except Exception:
            return obj.order_number
    order_number_display.short_description = 'رقم الطلب'
    order_number_display.admin_order_field = 'order_number'

@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('order', 'old_status_display', 'new_status_display', 'changed_by', 'notes', 'created_at')
    list_filter = ('old_status', 'new_status', 'changed_by', 'created_at')
    search_fields = ('order__order_number', 'notes')
    readonly_fields = ('order', 'old_status', 'new_status', 'changed_by', 'created_at')
    date_hierarchy = 'created_at'
    
    def old_status_display(self, obj):
        if obj.old_status:
            return obj.get_old_status_display()
        return '-'
    old_status_display.short_description = 'الحالة السابقة'
    old_status_display.admin_order_field = 'old_status'
    
    def new_status_display(self, obj):
        if obj.new_status:
            return obj.get_new_status_display()
        return '-'
    new_status_display.short_description = 'الحالة الجديدة'
    new_status_display.admin_order_field = 'new_status'
    
    def quantity_display(self, obj):
        """عرض الكمية بدون أصفار زائدة"""
        if hasattr(obj, 'get_clean_quantity_display'):
            return obj.get_clean_quantity_display()
        return str(obj.quantity) if obj.quantity else '0'
    quantity_display.short_description = 'الكمية'

@admin.register(DeliveryTimeSettings)
class DeliveryTimeSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات مواعيد التسليم"""
    list_per_page = 50
    list_display = [
        'order_type', 'delivery_days', 'is_active', 
        'created_at', 'updated_at'
    ]
    list_filter = ['order_type', 'is_active', 'created_at']
    search_fields = ['order_type']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('order_type', 'delivery_days', 'is_active')
        }),
        (_('معلومات النظام'), {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    def has_delete_permission(self, request, obj=None):
        if obj and obj.order_type in ['normal', 'vip', 'inspection']:
            return False
        return super().has_delete_permission(request, obj)
    def save_model(self, request, obj, form, change):
        if not change:
            existing = DeliveryTimeSettings.objects.filter(
                order_type=obj.order_type
            ).first()
            if existing:
                existing.delivery_days = obj.delivery_days
                existing.is_active = obj.is_active
                existing.save()
                return
        super().save_model(request, obj, form, change)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('order', 'amount', 'payment_method', 'payment_date', 'reference_number')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('order__order_number', 'reference_number', 'notes')
    date_hierarchy = 'payment_date'
    fieldsets = (
        (_('معلومات الدفع'), {
            'fields': ('order', 'amount', 'payment_method', 'reference_number')
        }),
        (_('ملاحظات'), {
            'fields': ('notes',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )


# استيراد إدارة الفواتير
from . import invoice_admin