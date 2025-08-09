"""
إدارة قوالب الفواتير في لوحة التحكم
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from .invoice_models import InvoiceTemplate, InvoicePrintLog


@admin.register(InvoiceTemplate)
class InvoiceTemplateAdmin(admin.ModelAdmin):
    """إدارة قوالب الفواتير"""
    
    list_display = [
        'name', 
        'template_type', 
        'is_default_display', 
        'is_active', 
        'company_name',
        'created_at',
        'preview_link'
    ]
    
    list_filter = [
        'template_type',
        'is_active',
        'is_default',
        'created_at'
    ]
    
    search_fields = [
        'name',
        'company_name',
        'company_address'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'created_by'
    ]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': (
                'name',
                'template_type',
                'is_active',
                'is_default'
            )
        }),
        ('معلومات الشركة', {
            'fields': (
                'company_name',
                'company_logo',
                'company_address',
                'company_phone',
                'company_email',
                'company_website'
            )
        }),
        ('إعدادات التصميم', {
            'fields': (
                'primary_color',
                'secondary_color',
                'font_family',
                'font_size'
            ),
            'classes': ('collapse',)
        }),
        ('إعدادات المحتوى', {
            'fields': (
                'show_company_logo',
                'show_order_details',
                'show_customer_details',
                'show_payment_details',
                'show_notes',
                'show_terms'
            ),
            'classes': ('collapse',)
        }),
        ('النصوص المخصصة', {
            'fields': (
                'header_text',
                'footer_text',
                'terms_text'
            ),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': (
                'created_at',
                'updated_at',
                'created_by'
            ),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        """حفظ النموذج مع تسجيل المنشئ"""
        if not change:  # إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def is_default_display(self, obj):
        """عرض حالة القالب الافتراضي"""
        if obj.is_default:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ افتراضي</span>'
            )
        return format_html(
            '<span style="color: #999;">-</span>'
        )
    is_default_display.short_description = 'افتراضي'
    
    def preview_link(self, obj):
        """رابط معاينة القالب"""
        if obj.pk:
            simple_editor_url = reverse('orders:simple_invoice_editor_edit', args=[obj.pk])
            return format_html(
                '<a href="{}" class="button" target="_blank" style="background-color: #198754; color: white; margin-left: 5px;">تحرير القالب</a>'
                '<a href="#" onclick="previewTemplate({})" class="button">معاينة</a>',
                simple_editor_url, obj.pk
            )
        return '-'
    preview_link.short_description = 'الإجراءات'
    
    class Media:
        css = {
            'all': ('admin/css/invoice_template_admin.css',)
        }
        js = ('admin/js/invoice_template_admin.js',)


@admin.register(InvoicePrintLog)
class InvoicePrintLogAdmin(admin.ModelAdmin):
    """إدارة سجلات طباعة الفواتير"""
    
    list_display = [
        'order_link',
        'template_name',
        'printed_by',
        'printed_at',
        'print_type'
    ]
    
    list_filter = [
        'print_type',
        'printed_at',
        'template__name'
    ]
    
    search_fields = [
        'order__order_number',
        'order__customer__name',
        'printed_by__username'
    ]
    
    readonly_fields = [
        'order',
        'template',
        'printed_by',
        'printed_at',
        'print_type'
    ]
    
    def has_add_permission(self, request):
        """منع الإضافة اليدوية"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """منع التعديل"""
        return False
    
    def order_link(self, obj):
        """رابط للطلب"""
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.order.order_number
            )
        return '-'
    order_link.short_description = 'الطلب'
    
    def template_name(self, obj):
        """اسم القالب"""
        return obj.template.name if obj.template else 'قالب محذوف'
    template_name.short_description = 'القالب'


# تخصيص عنوان لوحة التحكم
admin.site.site_header = "نظام إدارة الفواتير - شركة الخواجه"
admin.site.site_title = "إدارة الفواتير"
admin.site.index_title = "لوحة التحكم"