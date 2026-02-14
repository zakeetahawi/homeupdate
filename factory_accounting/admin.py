"""
Admin configuration for Factory Accounting
إعدادات لوحة الإدارة لحسابات المصنع
Factory Accounting Admin
إدارة حسابات المصنع
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    CardMeasurementSplit,
    FactoryAccountingSettings,
    FactoryCard,
    ProductionStatusLog,
    Tailor,
)


@admin.register(FactoryAccountingSettings)
class FactoryAccountingSettingsAdmin(admin.ModelAdmin):
    filter_horizontal = ["excluded_fabric_types", "double_meter_tailoring_types"]

    fieldsets = (
        (
            _("الاستبعادات"),
            {
                "fields": ("excluded_fabric_types",),
                "description": "حدد أنواع الأقمشة التي يجب استبعادها من حساب إجمالي الأمتار (مثل: الأحزمة، الكشاكيش، إلخ)",
            },
        ),
        (
            _("الأمتار المضاعفة"),
            {
                "fields": ("double_meter_tailoring_types",),
                "description": "حدد أنواع التفصيل التي يجب مضاعفة أمتارها في الحساب",
            },
        ),
        (
            _("التسعير"),
            {
                "fields": ("default_rate_per_meter", "default_cutter_rate"),
                "description": "السعر الافتراضي للمتر للخياطين والقصاصين",
            },
        ),
        (_("معلومات"), {"fields": ("updated_at",), "classes": ("collapse",)}),
    )
    readonly_fields = ["updated_at"]

    def has_add_permission(self, request):
        # Singleton - only one instance allowed
        return not FactoryAccountingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False
    
    def save_model(self, request, obj, form, change):
        """Save and notify about auto-recalculations"""
        from django.contrib import messages
        
        super().save_model(request, obj, form, change)
        
        # Notify user about automatic recalculations
        if change:
            messages.success(
                request,
                "✅ تم حفظ الإعدادات بنجاح. تم إعادة حساب جميع العناصر غير المدفوعة تلقائياً باستخدام الأسعار الجديدة."
            )


@admin.register(Tailor)
class TailorAdmin(admin.ModelAdmin):
    list_display = ["name", "get_rate_display", "phone", "is_active", "created_at"]
    list_filter = ["is_active", "use_custom_rate", "created_at"]
    search_fields = ["name", "phone"]
    readonly_fields = ["created_at", "updated_at", "created_by"]

    fieldsets = (
        (_("المعلومات الأساسية"), {"fields": ("name", "phone", "is_active")}),
        (
            _("التسعير"),
            {
                "fields": ("use_custom_rate", "default_rate"),
                "description": "حدد ما إذا كنت تريد استخدام سعر مخصص لهذا الخياط أو السعر العام من الإعدادات",
            },
        ),
        (_("ملاحظات"), {"fields": ("notes",)}),
        (
            _("معلومات النظام"),
            {
                "fields": ("created_at", "updated_at", "created_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_rate_display(self, obj):
        """Display the actual rate being used"""
        rate = obj.get_rate()
        if obj.use_custom_rate:
            return f"{rate} (مخصص)"
        return f"{rate} (عام)"

    get_rate_display.short_description = _("السعر")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        # Always set role to tailor (cutter comes from production line)
        obj.role = "tailor"
        super().save_model(request, obj, form, change)
        
        # Notify user about automatic recalculations
        if change and ('use_custom_rate' in form.changed_data or 'default_rate' in form.changed_data):
            from django.contrib import messages
            messages.success(
                request,
                f"✅ تم تحديث {obj.name} بنجاح. تم إعادة حساب جميع التقسيمات غير المدفوعة تلقائياً باستخدام السعر الجديد."
            )


@admin.register(ProductionStatusLog)
class ProductionStatusLogAdmin(admin.ModelAdmin):
    list_display = ["manufacturing_order", "status", "timestamp", "changed_by"]
    list_filter = ["status", "timestamp"]
    search_fields = ["manufacturing_order__order__order_number"]
    readonly_fields = ["timestamp"]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False  # Logs are created automatically

    def has_change_permission(self, request, obj=None):
        return False  # Logs should not be edited

    def has_delete_permission(self, request, obj=None):
        return False  # Logs should not be deleted


class CardMeasurementSplitInline(admin.TabularInline):
    model = CardMeasurementSplit
    extra = 1
    fields = [
        "tailor",
        "share_amount",
        "unit_rate",
        "current_rate_display",
        "monetary_value",
        "current_value_display",
        "is_paid",
        "paid_date",
    ]
    readonly_fields = ["monetary_value", "current_rate_display", "current_value_display"]
    
    def current_rate_display(self, obj):
        """Display current rate based on payment status"""
        if obj.pk:  # Only for existing objects
            current_rate = obj.get_current_unit_rate()
            if obj.is_paid:
                return format_html('<span style="color: green;">{} ج.م (مدفوع - محفوظ)</span>', current_rate)
            else:
                return format_html('<span style="color: orange;">{} ج.م (حالي)</span>', current_rate)
        return "-"
    
    current_rate_display.short_description = _("السعر الحالي")
    
    def current_value_display(self, obj):
        """Display current monetary value based on payment status"""
        if obj.pk:  # Only for existing objects
            current_value = obj.get_current_monetary_value()
            if obj.is_paid:
                return format_html('<span style="color: green;">{} ج.م (مدفوع - محفوظ)</span>', current_value)
            else:
                return format_html('<span style="color: orange;">{} ج.م (سيتم التحديث)</span>', current_value)
        return "-"
    
    current_value_display.short_description = _("القيمة الحالية")


@admin.register(FactoryCard)
class FactoryCardAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "customer_name",
        "invoice_number",
        "production_date",
        "total_billable_meters",
        "cutter_price_display",
        "cutter_cost_display",
        "status",
        "created_at",
    ]
    list_filter = ["status", "production_date", "created_at"]
    search_fields = [
        "manufacturing_order__order__order_number",
        "manufacturing_order__order__customer__name",
        "manufacturing_order__order__invoice_number",
    ]
    readonly_fields = [
        "manufacturing_order",
        "production_date",
        "cutter_price_display",
        "cutter_cost_display",
        "created_at",
        "updated_at",
        "created_by",
    ]
    date_hierarchy = "production_date"
    inlines = [CardMeasurementSplitInline]

    fieldsets = (
        (
            _("معلومات الطلب"),
            {"fields": ("manufacturing_order", "status", "production_date")},
        ),
        (
            _("الحسابات"), 
            {
                "fields": (
                    "total_billable_meters", 
                    "cutter_price_display", 
                    "cutter_cost_display"
                )
            }
        ),
        (_("ملاحظات"), {"fields": ("notes",)}),
        (
            _("معلومات النظام"),
            {
                "fields": ("created_at", "updated_at", "created_by"),
                "classes": ("collapse",),
            },
        ),
    )
    
    def cutter_price_display(self, obj):
        """Display current cutter price based on payment status"""
        current_price = obj.get_current_cutter_price()
        if obj.status == "paid":
            return format_html('<span style="color: green;">{} ج.م (مدفوع - محفوظ)</span>', current_price)
        else:
            return format_html('<span style="color: orange;">{} ج.م (حالي)</span>', current_price)
    
    cutter_price_display.short_description = _("سعر القصاص للمتر")
    
    def cutter_cost_display(self, obj):
        """Display current cutter cost based on payment status"""
        current_cost = obj.get_current_cutter_cost()
        if obj.status == "paid":
            return format_html('<span style="color: green;">{} ج.م (مدفوع - محفوظ)</span>', current_cost)
        else:
            return format_html('<span style="color: orange;">{} ج.م (سيتم التحديث)</span>', current_cost)
    
    cutter_cost_display.short_description = _("تكلفة القصاص الإجمالية")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CardMeasurementSplit)
class CardMeasurementSplitAdmin(admin.ModelAdmin):
    list_display = [
        "factory_card",
        "tailor",
        "share_amount",
        "unit_rate",
        "current_rate_display",
        "monetary_value",
        "current_value_display",
        "is_paid",
        "paid_date",
    ]
    list_filter = ["is_paid", "tailor", "paid_date"]
    search_fields = [
        "factory_card__manufacturing_order__order__order_number",
        "tailor__name",
    ]
    readonly_fields = ["monetary_value", "current_rate_display", "current_value_display", "created_at", "updated_at"]
    date_hierarchy = "paid_date"

    fieldsets = (
        (
            _("التخصيص"),
            {
                "fields": (
                    "factory_card",
                    "tailor",
                    "share_amount",
                    "unit_rate",
                    "current_rate_display",
                    "monetary_value",
                    "current_value_display",
                )
            },
        ),
        (_("الدفع"), {"fields": ("is_paid", "paid_date")}),
        (_("ملاحظات"), {"fields": ("notes",)}),
        (
            _("معلومات النظام"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    
    def current_rate_display(self, obj):
        """Display current rate based on payment status"""
        current_rate = obj.get_current_unit_rate()
        if obj.is_paid:
            return format_html('<span style="color: green;">{} ج.م (مدفوع - محفوظ)</span>', current_rate)
        else:
            return format_html('<span style="color: orange;">{} ج.م (حالي - سيتم التحديث)</span>', current_rate)
    
    current_rate_display.short_description = _("السعر الحالي للمتر")
    
    def current_value_display(self, obj):
        """Display current monetary value based on payment status"""
        current_value = obj.get_current_monetary_value()
        if obj.is_paid:
            return format_html('<span style="color: green;">{} ج.م (مدفوع - محفوظ)</span>', current_value)
        else:
            return format_html('<span style="color: orange;">{} ج.م (حالي - سيتم التحديث)</span>', current_value)
    
    current_value_display.short_description = _("القيمة المالية الحالية")
