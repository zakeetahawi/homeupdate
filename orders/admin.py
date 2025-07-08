from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
# from django.utils import timezone
from .models import Order, OrderItem, Payment, OrderStatusLog
# from .extended_models import ExtendedOrder, AccessoryItem, FabricOrder # Deletion

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
    list_display = ('order_number', 'customer', 'order_status_display', 'tracking_status', 'final_price', 'payment_status', 'created_at')
    list_filter = (
        'tracking_status',
        'payment_verified',
        'delivery_type',
    )
    search_fields = ('order_number', 'customer__name', 'invoice_number')
    inlines = [OrderItemInline, PaymentInline]
    readonly_fields = (
        'created_at',
        'updated_at',
        'order_date',
        'modified_at',
    )

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
    payment_status.short_description = 'حالة الدفع'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs

@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'old_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('old_status', 'new_status', 'changed_by')
    search_fields = ('order__order_number',)

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


