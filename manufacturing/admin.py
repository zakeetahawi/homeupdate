from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ManufacturingOrder, ManufacturingOrderItem
)


class ManufacturingOrderItemInline(admin.TabularInline):
    model = ManufacturingOrderItem
    extra = 1
    fields = ('product_name', 'quantity', 'specifications', 'status')
    readonly_fields = ('status',)


@admin.register(ManufacturingOrder)
class ManufacturingOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order_link',
        'contract_number',
        'order_type_display',
        'status_display',
        'order_date',
        'expected_delivery_date',
        'exit_permit_number',
        'delivery_info',
        'created_at',
    )

    list_filter = (
        'status',
        'order_type',
        'order_date',
        'expected_delivery_date',
        'delivery_date',
    )

    search_fields = (
        'id',
        'order__id',
        'contract_number',
        'invoice_number',
        'exit_permit_number',
        'delivery_permit_number',
        'delivery_recipient_name',
    )

    readonly_fields = (
        'created_at', 'updated_at', 'completion_date', 'delivery_date'
    )
    inlines = [ManufacturingOrderItemInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('معلومات الطلب', {
            'fields': (
                'order',
                'contract_number',
                'invoice_number',
                'order_type',
                'status',
                'order_date',
                'expected_delivery_date',
                'exit_permit_number',
                'notes',
                'rejection_reason',
            )
        }),
        ('معلومات التسليم', {
            'fields': (
                'delivery_permit_number',
                'delivery_recipient_name',
                'delivery_date',
            ),
            'classes': ('collapse',),
        }),
        ('الملفات', {
            'fields': (
                'contract_file',
                'inspection_file',
            )
        }),
        ('التواريخ', {
            'fields': (
                'completion_date',
                'created_at',
                'updated_at',
            )
        }),
    )

    def order_link(self, obj):
        if obj.order:
            url = f'/admin/orders/order/{obj.order.id}/change/'
            return format_html(
                '<a href="{}">{}</a>', url, f'طلب #{obj.order.id}'
            )
        return "-"
    order_link.short_description = 'الطلب'

    def order_type_display(self, obj):
        return obj.get_order_type_display()
    order_type_display.short_description = 'نوع الطلب'

    def status_display(self, obj):
        colors = {
            'pending_approval': '#ffc107',
            'pending': '#17a2b8',
            'in_progress': '#007bff',
            'ready_for_installation': '#6f42c1',
            'completed': '#28a745',
            'delivered': '#20c997',
            'rejected': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'

    def delivery_info(self, obj):
        if obj.status == 'delivered' and obj.delivery_permit_number:
            return format_html(
                '<strong>إذن:</strong> {}<br><strong>المستلم:</strong> {}',
                obj.delivery_permit_number,
                obj.delivery_recipient_name or '-'
            )
        return "-"
    delivery_info.short_description = 'معلومات التسليم'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'order__customer', 'order__customer__branch', 'created_by'
        ).prefetch_related(
            'items', 'items__product'
        )

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'pending_approval':
            # Only users with approval permission can change pending_approval
            return (request.user.has_perm('manufacturing.can_approve_orders')
                    or request.user.is_superuser)
        return super().has_change_permission(request, obj)


@admin.register(ManufacturingOrderItem)
class ManufacturingOrderItemAdmin(admin.ModelAdmin):
    list_display = ('manufacturing_order', 'product_name', 'quantity', 'status')
    list_filter = ('status',)
    search_fields = ('manufacturing_order__id', 'product_name')

# The user management code has been moved to accounts/admin.py
