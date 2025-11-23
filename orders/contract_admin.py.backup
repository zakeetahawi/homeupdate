"""
إدارة قوالب العقود في لوحة التحكم
"""
from django.contrib import admin
from .contract_models import ContractTemplate, ContractCurtain, ContractPrintLog


@admin.register(ContractTemplate)
class ContractTemplateAdmin(admin.ModelAdmin):
    """إدارة قوالب العقود"""
    
    list_display = [
        'name', 
        'template_type', 
        'is_active', 
        'is_default',
        'usage_count',
        'last_used',
        'created_at'
    ]
    
    list_filter = [
        'is_active',
        'is_default',
        'template_type',
        'created_at'
    ]
    
    search_fields = [
        'name',
        'company_name'
    ]
    
    readonly_fields = [
        'usage_count',
        'last_used',
        'created_at',
        'updated_at'
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
                'company_website',
                'company_tax_number',
                'company_commercial_register'
            )
        }),
        ('إعدادات التصميم', {
            'fields': (
                'primary_color',
                'secondary_color',
                'accent_color',
                'font_family',
                'font_size',
                'page_size',
                'page_margins'
            )
        }),
        ('محتوى القالب', {
            'fields': (
                'html_content',
                'css_styles',
                'advanced_settings'
            )
        }),
        ('إعدادات العرض', {
            'fields': (
                'show_company_logo',
                'show_order_details',
                'show_customer_details',
                'show_items_table',
                'show_payment_details',
                'show_terms',
                'show_signatures'
            )
        }),
        ('نصوص مخصصة', {
            'fields': (
                'header_text',
                'footer_text',
                'terms_text'
            )
        }),
        ('إحصائيات', {
            'fields': (
                'usage_count',
                'last_used',
                'created_at',
                'updated_at',
                'created_by'
            )
        })
    )
    
    def save_model(self, request, obj, form, change):
        """حفظ القالب مع تسجيل المستخدم"""
        if not change:  # إذا كان قالب جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ContractCurtain)
class ContractCurtainAdmin(admin.ModelAdmin):
    """إدارة ستائر العقود"""

    list_display = [
        'order',
        'sequence',
        'room_name',
        'width',
        'height',
        'created_at'
    ]

    list_filter = [
        'created_at',
        'order__order_type'
    ]

    search_fields = [
        'room_name',
        'order__order_number',
        'order__customer__name'
    ]

    readonly_fields = [
        'created_at',
        'updated_at'
    ]

    fieldsets = (
        ('معلومات الطلب', {
            'fields': ('order', 'sequence')
        }),
        ('معلومات الغرفة والمقاسات', {
            'fields': (
                'room_name',
                'width',
                'height',
                'curtain_image'
            )
        }),
        ('القماش الخفيف', {
            'fields': (
                'light_fabric',
                'light_fabric_meters',
                'light_fabric_tailoring',
                'light_fabric_tailoring_size'
            )
        }),
        ('القماش الثقيل', {
            'fields': (
                'heavy_fabric',
                'heavy_fabric_meters',
                'heavy_fabric_tailoring',
                'heavy_fabric_tailoring_size'
            )
        }),
        ('قماش البلاك أوت', {
            'fields': (
                'blackout_fabric',
                'blackout_fabric_meters',
                'blackout_fabric_tailoring',
                'blackout_fabric_tailoring_size'
            )
        }),
        ('الإكسسوارات - الخشب والمجرى', {
            'fields': (
                'wood_quantity',
                'wood_type',
                'track_type',
                'track_quantity'
            )
        }),
        ('الإكسسوارات - المواسير والكوابيل', {
            'fields': (
                'pipe',
                'pipe_quantity',
                'bracket',
                'bracket_quantity'
            )
        }),
        ('الإكسسوارات - النهايات والطبة', {
            'fields': (
                'finial',
                'finial_quantity',
                'ring',
                'ring_quantity'
            )
        }),
        ('الإكسسوارات - الشماعات والفرانشة', {
            'fields': (
                'hanger',
                'hanger_quantity',
                'valance',
                'valance_quantity'
            )
        }),
        ('الإكسسوارات - الشرابة والمرابط', {
            'fields': (
                'tassel',
                'tassel_quantity',
                'tieback_fabric',
                'tieback_quantity'
            )
        }),
        ('الإكسسوارات - حزام الوسط', {
            'fields': (
                'belt',
                'belt_quantity'
            )
        }),
        ('ملاحظات', {
            'fields': ('notes',)
        }),
        ('معلومات النظام', {
            'fields': (
                'created_at',
                'updated_at'
            )
        })
    )


@admin.register(ContractPrintLog)
class ContractPrintLogAdmin(admin.ModelAdmin):
    """إدارة سجلات طباعة العقود"""
    
    list_display = [
        'order',
        'template',
        'printed_by',
        'print_type',
        'printed_at'
    ]
    
    list_filter = [
        'print_type',
        'printed_at',
        'template'
    ]
    
    search_fields = [
        'order__order_number',
        'order__customer__name'
    ]
    
    readonly_fields = [
        'order',
        'template',
        'printed_by',
        'print_type',
        'printed_at'
    ]
    
    def has_add_permission(self, request):
        """منع إضافة سجلات يدوياً"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """منع تعديل السجلات"""
        return False

