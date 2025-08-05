from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models import Q
from django.utils import timezone
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
        """إرجاع قائمة السنوات المتاحة"""
        years = Order.objects.dates('order_date', 'year', order='DESC')
        year_choices = [('all', _('جميع السنوات'))]
        
        for year in years:
            year_choices.append((str(year.year), str(year.year)))
        
        return year_choices

    def queryset(self, request, queryset):
        """تطبيق الفلتر على الاستعلام"""
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
        """Override to make sure we don't try to create inline items for unsaved objects"""
        if obj is None:  # obj is None when we're adding a new object
            self.extra = 0  # Don't show any extra forms for new objects
        else:
            self.extra = 1  # Show extra forms for existing objects
        return super().get_formset(request, obj, **kwargs)

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1
    readonly_fields = ('payment_date',)

    def get_formset(self, request, obj=None, **kwargs):
        """Override to make sure we don't try to create inline items for unsaved objects"""
        if obj is None:  # obj is None when we're adding a new object
            self.extra = 0  # Don't show any extra forms for new objects
        else:
            self.extra = 1  # Show extra forms for existing objects
        return super().get_formset(request, obj, **kwargs)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'order_status_display', 'tracking_status', 'final_price', 'payment_status', 'order_year', 'created_at')
    list_filter = (
        YearFilter,
        'tracking_status',
        'order_status',
        'payment_verified',
        'delivery_type',
        'status',
    )
    search_fields = ('order_number', 'customer__name', 'invoice_number', 'invoice_number_2', 'invoice_number_3', 'contract_number', 'contract_number_2', 'contract_number_3')
    inlines = [OrderItemInline, PaymentInline]
    readonly_fields = (
        'created_at',
        'updated_at',
        'order_date',
        'modified_at',
    )
    date_hierarchy = 'order_date'

    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('customer', 'order_number', 'tracking_status')
        }),
        (_('معلومات التسليم'), {
            'fields': ('delivery_type', 'delivery_address')
        }),
        (_('معلومات مالية'), {
            'fields': ('paid_amount', 'payment_verified')
        }),
        (_('معلومات السعر'), {
            'fields': (
                'final_price',
                'modified_at'
            )
        }),
        (_('معلومات إضافية'), {
            'fields': ('notes',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at', 'order_date', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def order_status_display(self, obj):
        """عرض حالة الطلب مع الألوان"""
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
    payment_status.short_description = 'حالة ��لدفع'

    def order_year(self, obj):
        """عرض سنة الطلب"""
        return obj.order_date.year if obj.order_date else '-'
    order_year.short_description = 'السنة'
    order_year.admin_order_field = 'order_date'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs

@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'old_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('old_status', 'new_status', 'changed_by')
    search_fields = ('order__order_number',)

@admin.register(DeliveryTimeSettings)
class DeliveryTimeSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات مواعيد التسليم"""
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
        """منع حذف الإعدادات الافتراضية"""
        if obj and obj.order_type in ['normal', 'vip', 'inspection']:
            return False
        return super().has_delete_permission(request, obj)
    
    def save_model(self, request, obj, form, change):
        """تأكد من وجود إعداد واحد فقط لكل نوع طلب"""
        if not change:  # إنشاء جديد
            # التحقق من وجود إعداد آخر لنفس النوع
            existing = DeliveryTimeSettings.objects.filter(
                order_type=obj.order_type
            ).first()
            if existing:
                # تحديث الإعداد الموجود بدلاً من إنشاء واحد جديد
                existing.delivery_days = obj.delivery_days
                existing.is_active = obj.is_active
                existing.save()
                return
        super().save_model(request, obj, form, change)

# ExtendedOrder models are no longer used and have been removed.
# class AccessoryItemInline(admin.TabularInline):
#     model = AccessoryItem
#     extra = 1

# class FabricOrderInline(admin.StackedInline):
#     model = FabricOrder
#     can_delete = False

# @admin.register(ExtendedOrder)
# class ExtendedOrderAdmin(admin.ModelAdmin):
#     list_display = ('order', 'order_type', 'branch', 'payment_verified')
#     list_filter = ('order_type', 'branch', 'payment_verified')
#     inlines = [AccessoryItemInline, FabricOrderInline]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
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


