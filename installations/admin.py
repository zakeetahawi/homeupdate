from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from accounts.models import SystemSettings

from .models import (
    InstallationSchedule, InstallationTeam, Technician, Driver,
    ModificationRequest, ModificationImage, ManufacturingOrder,
    ModificationReport, ReceiptMemo, InstallationPayment, InstallationArchive, CustomerDebt,
    InstallationAnalytics, ModificationErrorAnalysis, ModificationErrorType
)


def currency_format(amount):
    """تنسيق المبلغ مع عملة النظام"""
    try:
        settings = SystemSettings.get_settings()
        symbol = settings.currency_symbol
        formatted_amount = f"{amount:,.2f}"
        return f"{formatted_amount} {symbol}"
    except Exception:
        return f"{amount:,.2f} ر.س"


@admin.register(CustomerDebt)
class CustomerDebtAdmin(admin.ModelAdmin):
    list_per_page = 50  # زيادة العدد إلى 50
    list_display = ['customer', 'order', 'debt_amount_formatted', 'is_paid', 'payment_date', 'created_at']
    list_filter = ['is_paid', 'created_at', 'payment_date']
    search_fields = ['customer__name', 'order__order_number']
    list_editable = ['is_paid']
    ordering = ['-created_at']
    
    # إضافة إمكانية الترتيب لجميع الأعمدة
    sortable_by = [
        'customer__name', 'order__order_number', 'debt_amount',
        'is_paid', 'payment_date', 'created_at'
    ]

    def debt_amount_formatted(self, obj):
        return currency_format(obj.debt_amount)
    debt_amount_formatted.short_description = 'مبلغ المديونية'
    debt_amount_formatted.admin_order_field = 'debt_amount'  # تمكين الترتيب


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['name', 'phone', 'specialization', 'is_active', 'created_at']
    list_filter = ['is_active', 'specialization', 'created_at']
    search_fields = ['name', 'phone', 'specialization']
    list_editable = ['is_active']
    ordering = ['name']


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['name', 'phone', 'license_number', 'vehicle_number', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'phone', 'license_number', 'vehicle_number']
    list_editable = ['is_active']
    ordering = ['name']


@admin.register(InstallationTeam)
class InstallationTeamAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
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
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        'installation_code', 'customer_name', 'scheduled_date', 'scheduled_time',
        'team', 'status_display', 'created_at'
    ]
    list_filter = ['status', 'scheduled_date', 'team', 'created_at']
    search_fields = ['order__order_number', 'order__customer__name']
    list_editable = ['team']
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

    def status_display(self, obj):
        """عرض حالة التركيب بألوان"""
        colors = {
            'needs_scheduling': '#ffc107',         # أصفر
            'scheduled': '#17a2b8',               # أزرق فاتح
            'in_installation': '#007bff',         # أزرق
            'completed': '#28a745',               # أخضر
            'cancelled': '#dc3545',               # أحمر
            'modification_required': '#fd7e14',   # برتقالي
            'modification_in_progress': '#6f42c1', # بنفسجي
            'modification_completed': '#20c997',   # أخضر فاتح
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 12px; font-weight: bold; font-size: 11px; white-space: nowrap;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'

    def customer_name(self, obj):
        if obj.order and obj.order.customer:
            return obj.order.customer.name
        return '-'
    customer_name.short_description = 'اسم العميل'

    def get_urls(self):
        """إضافة URLs مخصصة للوصول للتركيبات باستخدام الكود"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'by-code/<str:installation_code>/',
                self.admin_site.admin_view(self.installation_by_code_view),
                name='installations_installationschedule_by_code',
            ),
        ]
        return custom_urls + urls

    def installation_by_code_view(self, request, installation_code):
        """عرض التركيب باستخدام الكود وإعادة التوجيه لصفحة التحرير"""
        try:
            # البحث باستخدام order_number إذا كان يحتوي على رقم الطلب
            if installation_code.endswith('-T'):
                base_code = installation_code[:-2]  # إزالة '-T'
                if base_code.startswith('#'):
                    # البحث باستخدام ID مباشرة
                    installation_id = base_code[1:]  # إزالة '#'
                    installation = InstallationSchedule.objects.get(id=installation_id)
                else:
                    # البحث باستخدام order_number
                    installation = InstallationSchedule.objects.get(order__order_number=base_code)
            else:
                # محاولة البحث المباشر بالكود
                installation = InstallationSchedule.objects.get(id=installation_code)
                
            return HttpResponseRedirect(
                reverse('admin:installations_installationschedule_change', args=[installation.pk])
            )
        except (InstallationSchedule.DoesNotExist, ValueError):
            self.message_user(request, f'التركيب بكود {installation_code} غير موجود', level='error')
            return HttpResponseRedirect(reverse('admin:installations_installationschedule_changelist'))

    def installation_code(self, obj):
        """عرض رقم طلب التركيب الموحد مع روابط محسنة - تحديث للاستخدام الكود في admin"""
        code = obj.installation_code
        
        try:
            # رابط عرض التركيب في الواجهة
            view_url = reverse('installations:installation_detail_by_code', args=[code])
            # رابط تحرير التركيب في لوحة التحكم باستخدام الكود
            admin_url = reverse('admin:installations_installationschedule_by_code', kwargs={'installation_code': code})
            
            return format_html(
                '<strong>{}</strong><br/>'
                '<a href="{}" target="_blank" title="عرض في الواجهة">'
                '<span style="color: #0073aa;">👁️ عرض</span></a> | '
                '<a href="{}" title="تحرير في لوحة التحكم">'
                '<span style="color: #d63638;">✏️ تحرير</span></a>',
                code,
                view_url,
                admin_url
            )
        except Exception:
            return code
    installation_code.short_description = 'رقم طلب التركيب'

    def get_queryset(self, request):
        """تحسين الاستعلامات لتحسين الأداء"""
        return super().get_queryset(request).select_related(
            'order', 'order__customer', 'order__branch', 'installer', 'created_by'
        )


@admin.register(ModificationRequest)
class ModificationRequestAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['installation', 'customer', 'modification_type', 'priority', 'estimated_cost_formatted', 'customer_approval', 'created_at']
    list_filter = ['priority', 'customer_approval', 'created_at']
    search_fields = ['installation__order__order_number', 'customer__name', 'modification_type']
    list_editable = ['priority', 'customer_approval']
    ordering = ['-created_at']

    def estimated_cost_formatted(self, obj):
        return currency_format(obj.estimated_cost)
    estimated_cost_formatted.short_description = 'التكلفة المتوقعة'


@admin.register(ModificationImage)
class ModificationImageAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['modification', 'image_preview', 'description', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['modification__installation__order__order_number', 'description']
    ordering = ['-uploaded_at']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'معاينة الصورة'


@admin.register(ManufacturingOrder)
class ManufacturingOrderAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['modification_request', 'order_type', 'status', 'assigned_to', 'created_at']
    list_filter = ['order_type', 'status', 'assigned_to', 'created_at']
    search_fields = ['modification_request__installation__order__order_number']
    list_editable = ['status', 'assigned_to']
    ordering = ['-created_at']


@admin.register(ModificationReport)
class ModificationReportAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['modification_request', 'manufacturing_order', 'created_by', 'created_at']
    list_filter = ['created_at', 'created_by']
    search_fields = ['modification_request__installation__order__order_number', 'description']
    ordering = ['-created_at']


@admin.register(ReceiptMemo)
class ReceiptMemoAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['installation', 'receipt_image_preview', 'customer_signature', 'amount_received_formatted', 'created_at']
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

    def amount_received_formatted(self, obj):
        return currency_format(obj.amount_received)
    amount_received_formatted.short_description = 'المبلغ المستلم'


@admin.register(InstallationPayment)
class InstallationPaymentAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['installation', 'payment_type', 'amount_formatted', 'payment_method', 'created_at']
    list_filter = ['payment_type', 'payment_method', 'created_at']
    search_fields = ['installation__order__order_number', 'receipt_number']
    ordering = ['-created_at']

    def amount_formatted(self, obj):
        return currency_format(obj.amount)
    amount_formatted.short_description = 'المبلغ'


@admin.register(InstallationArchive)
class InstallationArchiveAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['installation', 'completion_date', 'archived_by']
    list_filter = ['completion_date', 'archived_by']
    search_fields = ['installation__order__order_number']
    ordering = ['-completion_date']
    readonly_fields = ['completion_date', 'archived_by']


@admin.register(InstallationAnalytics)
class InstallationAnalyticsAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['month', 'total_installations', 'completed_installations', 'total_customers', 
                   'total_modifications', 'completion_rate', 'modification_rate']
    list_filter = ['month']
    search_fields = ['month']
    readonly_fields = ['completion_rate', 'modification_rate']
    
    def save_model(self, request, obj, form, change):
        obj.calculate_rates()
        super().save_model(request, obj, form, change)


@admin.register(ModificationErrorAnalysis)
class ModificationErrorAnalysisAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['modification_request', 'error_type', 'cost_impact_formatted', 'time_impact_hours', 'created_at']
    list_filter = ['error_type', 'created_at']
    search_fields = ['modification_request__installation__order__order_number', 'error_description']
    readonly_fields = ['created_at', 'updated_at']

    def cost_impact_formatted(self, obj):
        return currency_format(obj.cost_impact)
    cost_impact_formatted.short_description = 'التأثير المالي'


@admin.register(ModificationErrorType)
class ModificationErrorTypeAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']


# تخصيص عنوان لوحة الإدارة
admin.site.site_header = "إدارة التركيبات - نظام الخواجه"
admin.site.site_title = "إدارة التركيبات"
admin.site.index_title = "مرحباً بك في إدارة التركيبات"
