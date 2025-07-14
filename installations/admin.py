from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Technician, Driver, InstallationTeam, InstallationSchedule,
    ModificationReport, ReceiptMemo, InstallationPayment, InstallationArchive
)


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'specialization', 'is_active', 'created_at']
    list_filter = ['is_active', 'specialization', 'created_at']
    search_fields = ['name', 'phone', 'specialization']
    list_editable = ['is_active']
    ordering = ['name']


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'license_number', 'vehicle_number', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'phone', 'license_number', 'vehicle_number']
    list_editable = ['is_active']
    ordering = ['name']


@admin.register(InstallationTeam)
class InstallationTeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'driver', 'technicians_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    list_editable = ['is_active']
    filter_horizontal = ['technicians']
    ordering = ['name']

    def technicians_count(self, obj):
        return obj.technicians.count()
    technicians_count.short_description = 'عدد الفنيين'


@admin.register(InstallationSchedule)
class InstallationScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'order_link', 'customer_name', 'scheduled_date', 'scheduled_time',
        'team', 'status', 'created_at'
    ]
    list_filter = ['status', 'scheduled_date', 'team', 'created_at']
    search_fields = ['order__order_number', 'order__customer__name']
    list_editable = ['status', 'team']
    date_hierarchy = 'scheduled_date'
    ordering = ['-scheduled_date', '-scheduled_time']
    
    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('order', 'status')
        }),
        ('جدولة التركيب', {
            'fields': ('team', 'scheduled_date', 'scheduled_time')
        }),
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def order_link(self, obj):
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return '-'
    order_link.short_description = 'رقم الطلب'

    def customer_name(self, obj):
        if obj.order and obj.order.customer:
            return obj.order.customer.name
        return '-'
    customer_name.short_description = 'اسم العميل'


@admin.register(ModificationReport)
class ModificationReportAdmin(admin.ModelAdmin):
    list_display = ['installation', 'description', 'created_at']
    list_filter = ['created_at']
    search_fields = ['installation__order__order_number', 'description']
    ordering = ['-created_at']


@admin.register(ReceiptMemo)
class ReceiptMemoAdmin(admin.ModelAdmin):
    list_display = ['installation', 'receipt_image_preview', 'customer_signature', 'amount_received', 'created_at']
    list_filter = ['customer_signature', 'created_at']
    search_fields = ['installation__order__order_number']
    ordering = ['-created_at']

    def receipt_image_preview(self, obj):
        if obj.receipt_image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.receipt_image.url
            )
        return '-'
    receipt_image_preview.short_description = 'صورة المذكرة'


@admin.register(InstallationPayment)
class InstallationPaymentAdmin(admin.ModelAdmin):
    list_display = ['installation', 'payment_type', 'amount', 'payment_method', 'created_at']
    list_filter = ['payment_type', 'payment_method', 'created_at']
    search_fields = ['installation__order__order_number', 'receipt_number']
    ordering = ['-created_at']


@admin.register(InstallationArchive)
class InstallationArchiveAdmin(admin.ModelAdmin):
    list_display = ['installation', 'completion_date', 'archived_by']
    list_filter = ['completion_date', 'archived_by']
    search_fields = ['installation__order__order_number']
    ordering = ['-completion_date']
    readonly_fields = ['completion_date', 'archived_by']


# تخصيص عنوان لوحة الإدارة
admin.site.site_header = "إدارة قسم التركيبات"
admin.site.site_title = "قسم التركيبات"
admin.site.index_title = "مرحباً بك في إدارة قسم التركيبات"
