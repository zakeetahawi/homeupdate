"""
واجهة إدارة Django لنظام تخصيص الويزارد
Django Admin Interface for Wizard Customization System
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .wizard_customization_models import (
    WizardFieldOption,
    WizardGlobalSettings,
    WizardStepConfiguration,
)


@admin.register(WizardFieldOption)
class WizardFieldOptionAdmin(admin.ModelAdmin):
    """واجهة إدارة خيارات حقول الويزارد - مبسطة"""

    list_display = [
        "field_type_display",
        "display_name",
        "value",
        "sequence",
        "is_active",
        "is_default",
    ]

    list_filter = ["field_type", "is_active", "is_default"]
    search_fields = ["display_name", "value"]
    list_editable = ["is_active", "is_default", "sequence"]

    fieldsets = (
        ("المعلومات الأساسية", {"fields": ("field_type", "value", "display_name")}),
        ("الإعدادات", {"fields": ("sequence", "is_active", "is_default")}),
        (
            "بيانات إضافية (اختياري)",
            {"fields": ("extra_data",), "classes": ("collapse",)},
        ),
    )

    ordering = ["field_type", "sequence"]

    def field_type_display(self, obj):
        return obj.get_field_type_display()

    field_type_display.short_description = "نوع الحقل"

    def save_model(self, request, obj, form, change):
        """حفظ مع إلغاء الافتراضي السابق"""
        if obj.is_default:
            WizardFieldOption.objects.filter(
                field_type=obj.field_type, is_default=True
            ).exclude(pk=obj.pk).update(is_default=False)

        super().save_model(request, obj, form, change)


@admin.register(WizardStepConfiguration)
class WizardStepConfigurationAdmin(admin.ModelAdmin):
    """
    واجهة إدارة تخصيص خطوات الويزارد
    """

    list_display = [
        "step_number_display",
        "step_title_ar",
        "is_required_display",
        "is_active_display",
        "icon_display",
    ]

    list_filter = [
        "is_required",
        "is_active",
    ]

    search_fields = ["step_title_ar", "step_title_en", "step_description"]

    fieldsets = (
        (
            "معلومات الخطوة",
            {"fields": ("step_number", "step_title_ar", "step_title_en", "icon")},
        ),
        ("الوصف والمساعدة", {"fields": ("step_description", "help_text")}),
        ("الإعدادات", {"fields": ("is_required", "is_active")}),
        (
            "قواعد التحقق المتقدمة",
            {"fields": ("validation_rules",), "classes": ("collapse",)},
        ),
    )

    ordering = ["step_number"]

    def step_number_display(self, obj):
        """عرض رقم الخطوة"""
        return format_html(
            '<span class="badge badge-primary" style="background: #007bff; color: white; padding: 5px 10px; border-radius: 50%; font-size: 14px;">{}</span>',
            obj.step_number,
        )

    step_number_display.short_description = "الخطوة"

    def is_required_display(self, obj):
        """عرض حالة الإجبارية"""
        if obj.is_required:
            return format_html(
                '<span class="badge badge-danger" style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
                "إجبارية",
            )
        else:
            return format_html(
                '<span class="badge badge-secondary" style="background: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
                "اختيارية",
            )

    is_required_display.short_description = "النوع"

    def is_active_display(self, obj):
        """عرض حالة النشاط"""
        if obj.is_active:
            return format_html(
                '<span class="badge badge-success" style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
                "✓ نشطة",
            )
        else:
            return format_html(
                '<span class="badge badge-warning" style="background: #ffc107; color: #212529; padding: 3px 8px; border-radius: 3px;">{}</span>',
                "معطلة",
            )

    is_active_display.short_description = "الحالة"

    def icon_display(self, obj):
        """عرض الأيقونة"""
        if obj.icon:
            return format_html(
                '<i class="{}" style="font-size: 20px; color: #007bff;"></i>', obj.icon
            )
        return "-"

    icon_display.short_description = "الأيقونة"


@admin.register(WizardGlobalSettings)
class WizardGlobalSettingsAdmin(admin.ModelAdmin):
    """
    واجهة إدارة الإعدادات العامة للويزارد
    """

    # عرض سجل واحد فقط
    def has_add_permission(self, request):
        """منع إضافة أكثر من سجل واحد"""
        return not WizardGlobalSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """منع حذف السجل"""
        return False

    fieldsets = (
        (
            "⚙️ الإعدادات العامة",
            {
                "fields": (
                    "enable_wizard",
                    "enable_draft_auto_save",
                    "draft_expiry_days",
                ),
                "description": "الإعدادات الأساسية لنظام الويزارد",
            },
        ),
        (
            "💰 إعدادات الدفع",
            {
                "fields": ("minimum_payment_percentage", "allow_payment_exceed_total"),
                "description": "إعدادات الحد الأدنى للدفع والسماح بتجاوز المبلغ الإجمالي",
            },
        ),
        (
            "📄 إعدادات العقد",
            {
                "fields": (
                    (
                        "require_contract_for_installation",
                        "require_contract_for_tailoring",
                    ),
                    (
                        "require_contract_for_accessory",
                        "require_contract_for_inspection",
                    ),
                    "require_contract_for_products",
                    ("enable_electronic_contract", "enable_pdf_contract_upload"),
                ),
                "description": "تحديد أنواع الطلبات التي تتطلب عقد",
            },
        ),
        (
            "🔍 إعدادات المعاينة",
            {
                "fields": (
                    (
                        "require_inspection_for_installation",
                        "require_inspection_for_tailoring",
                    ),
                    (
                        "require_inspection_for_accessory",
                        "require_inspection_for_inspection",
                    ),
                    "require_inspection_for_products",
                    "allow_customer_side_measurements",
                ),
                "description": "تحديد أنواع الطلبات التي تتطلب معاينة",
            },
        ),
        (
            "🔔 إعدادات الإشعارات",
            {
                "fields": (
                    "send_notification_on_draft_created",
                    "send_notification_on_order_created",
                ),
                "description": "إعدادات إرسال الإشعارات للمدراء",
            },
        ),
        (
            "🎨 إعدادات العرض",
            {
                "fields": ("show_progress_bar", "theme_color"),
                "description": "إعدادات واجهة المستخدم وشريط التقدم",
            },
        ),
    )

    def changelist_view(self, request, extra_context=None):
        """عرض صفحة التعديل مباشرة"""
        obj = WizardGlobalSettings.get_settings()
        return self.changeform_view(request, str(obj.pk), "", extra_context)

    class Media:
        css = {"all": ("admin/css/wizard_customization.css",)}
        js = ("admin/js/wizard_settings.js",)
