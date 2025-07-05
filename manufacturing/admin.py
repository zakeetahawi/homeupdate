from django.contrib import admin
from .models import ManufacturingOrder, ManufacturingOrderItem
from django.utils.html import format_html


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
        'created_at',
    )
    
    list_filter = (
        'status',
        'order_type',
        'order_date',
        'expected_delivery_date',
    )
    
    search_fields = (
        'id',
        'order__id',
        'contract_number',
        'invoice_number',
        'exit_permit_number',
    )
    
    readonly_fields = ('created_at', 'updated_at')
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
            )
        }),
        ('الملفات', {
            'fields': (
                'contract_file',
                'inspection_file',
            )
        }),
        ('التواريخ', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def order_link(self, obj):
        if obj.order:
            url = f'/admin/orders/order/{obj.order.id}/change/'
            return format_html('<a href="{}">{}</a>', url, f'طلب #{obj.order.id}')
        return "-"
    order_link.short_description = 'الطلب'
    
    def order_type_display(self, obj):
        return obj.get_order_type_display()
    order_type_display.short_description = 'نوع الطلب'
    
    def status_display(self, obj):
        status_colors = {
            'pending': 'gray',
            'in_progress': 'blue',
            'ready_for_installation': 'orange',
            'completed': 'green',
            'cancelled': 'red',
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'
    status_display.admin_order_field = 'status'


@admin.register(ManufacturingOrderItem)
class ManufacturingOrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'manufacturing_order_link',
        'product_name',
        'quantity',
        'status_display',
    )
    
    list_filter = ('status',)
    search_fields = ('product_name', 'manufacturing_order__id')
    
    def manufacturing_order_link(self, obj):
        if obj.manufacturing_order:
            url = f'/admin/manufacturing/manufacturingorder/{obj.manufacturing_order.id}/change/'
            return format_html('<a href="{}">{}</a>', url, f'أمر التصنيع #{obj.manufacturing_order.id}')
        return "-"
    manufacturing_order_link.short_description = 'أمر التصنيع'
    
    def status_display(self, obj):
        return obj.get_status_display()
    status_display.short_description = 'الحالة'
