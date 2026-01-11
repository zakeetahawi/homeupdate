from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import CuttingOrder, CuttingOrderItem, CuttingReport


class CuttingOrderItemInline(admin.TabularInline):
    model = CuttingOrderItem
    extra = 0
    readonly_fields = ("order_item", "updated_at", "updated_by")
    fields = (
        "order_item",
        "status",
        "cutter_name",
        "permit_number",
        "receiver_name",
        "cutting_date",
        "delivery_date",
        "bag_number",
        "additional_quantity",
        "notes",
        "rejection_reason",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == "completed":
            return self.readonly_fields + (
                "status",
                "cutter_name",
                "permit_number",
                "receiver_name",
            )
        return self.readonly_fields


@admin.register(CuttingOrder)
class CuttingOrderAdmin(admin.ModelAdmin):
    list_display = [
        "cutting_code",
        "order_link",
        "customer_name",
        "warehouse",
        "status_badge",
        "completion_progress",
        "created_at",
        "assigned_to",
    ]
    list_filter = ["status", "warehouse", "created_at", "assigned_to"]
    search_fields = [
        "cutting_code",
        "order__contract_number",
        "order__customer__name",
        "order__customer__phone",
        "notes",
    ]
    readonly_fields = ["cutting_code", "created_at", "completion_progress"]
    inlines = [CuttingOrderItemInline]

    fieldsets = (
        (
            "معلومات أساسية",
            {"fields": ("cutting_code", "order", "warehouse", "status")},
        ),
        ("التوقيتات", {"fields": ("created_at", "started_at", "completed_at")}),
        ("المسؤوليات", {"fields": ("assigned_to",)}),
        ("ملاحظات", {"fields": ("notes",)}),
        ("الإحصائيات", {"fields": ("completion_progress",), "classes": ("collapse",)}),
    )

    def order_link(self, obj):
        """رابط للطلب الأصلي"""
        if obj.order:
            url = reverse("admin:orders_order_change", args=[obj.order.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.order.contract_number or f"طلب #{obj.order.pk}",
            )
        return "-"

    order_link.short_description = "الطلب"

    def customer_name(self, obj):
        """اسم العميل"""
        return obj.order.customer.name if obj.order and obj.order.customer else "-"

    customer_name.short_description = "العميل"

    def status_badge(self, obj):
        """شارة الحالة الملونة"""
        colors = {
            "pending": "warning",
            "in_progress": "info",
            "completed": "success",
            "partially_completed": "primary",
            "cancelled": "danger",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span class="badge badge-{}">{}</span>', color, obj.get_status_display()
        )

    status_badge.short_description = "الحالة"

    def completion_progress(self, obj):
        """شريط تقدم الإنجاز"""
        percentage = obj.completion_percentage
        color = (
            "success" if percentage == 100 else "info" if percentage > 50 else "warning"
        )

        return format_html(
            """
            <div class="progress" style="width: 100px;">
                <div class="progress-bar bg-{}" role="progressbar" 
                     style="width: {}%" aria-valuenow="{}" 
                     aria-valuemin="0" aria-valuemax="100">
                    {}%
                </div>
            </div>
            <small>{}/{} عنصر</small>
            """,
            color,
            percentage,
            percentage,
            int(percentage),
            obj.completed_items,
            obj.total_items,
        )

    completion_progress.short_description = "نسبة الإنجاز"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("order", "order__customer", "warehouse", "assigned_to")
            .prefetch_related("items")
        )


@admin.register(CuttingOrderItem)
class CuttingOrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "cutting_order_code",
        "product_name",
        "quantity_display",
        "status_badge",
        "cutter_name",
        "permit_number",
        "receiver_name",
        "cutting_date",
        "updated_by",
    ]
    list_filter = ["status", "cutting_order__warehouse", "cutting_date", "updated_by"]
    search_fields = [
        "cutting_order__cutting_code",
        "order_item__product__name",
        "cutter_name",
        "permit_number",
        "receiver_name",
        "notes",
    ]
    readonly_fields = ["order_item", "updated_at", "updated_by"]

    fieldsets = (
        ("معلومات أساسية", {"fields": ("cutting_order", "order_item", "status")}),
        (
            "بيانات التقطيع",
            {"fields": ("cutter_name", "permit_number", "receiver_name")},
        ),
        ("التوقيتات", {"fields": ("cutting_date", "delivery_date")}),
        ("معلومات إضافية", {"fields": ("bag_number", "additional_quantity", "notes")}),
        ("الرفض", {"fields": ("rejection_reason",), "classes": ("collapse",)}),
        (
            "معلومات التحديث",
            {"fields": ("updated_by", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def cutting_order_code(self, obj):
        """كود أمر التقطيع"""
        return obj.cutting_order.cutting_code

    cutting_order_code.short_description = "كود التقطيع"

    def product_name(self, obj):
        """اسم المنتج"""
        return obj.order_item.product.name if obj.order_item.product else "-"

    product_name.short_description = "المنتج"

    def quantity_display(self, obj):
        """عرض الكمية"""
        original = obj.order_item.quantity
        additional = obj.additional_quantity
        total = obj.total_quantity

        if additional > 0:
            return format_html(
                "{} + {} = <strong>{}</strong>", original, additional, total
            )
        return str(original)

    quantity_display.short_description = "الكمية"

    def status_badge(self, obj):
        """شارة الحالة"""
        colors = {
            "pending": "warning",
            "in_progress": "info",
            "completed": "success",
            "rejected": "danger",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span class="badge badge-{}">{}</span>', color, obj.get_status_display()
        )

    status_badge.short_description = "الحالة"

    def save_model(self, request, obj, form, change):
        """حفظ النموذج مع تسجيل المستخدم المحدث"""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "cutting_order", "order_item", "order_item__product", "updated_by"
            )
        )


@admin.register(CuttingReport)
class CuttingReportAdmin(admin.ModelAdmin):
    list_display = [
        "report_type",
        "warehouse",
        "date_range",
        "total_orders",
        "completed_items",
        "rejected_items",
        "pending_items",
        "generated_at",
    ]
    list_filter = ["report_type", "warehouse", "generated_at", "generated_by"]
    search_fields = ["warehouse__name"]
    readonly_fields = [
        "total_orders",
        "completed_items",
        "rejected_items",
        "pending_items",
        "generated_at",
        "generated_by",
    ]

    def date_range(self, obj):
        """نطاق التاريخ"""
        return f"{obj.start_date} - {obj.end_date}"

    date_range.short_description = "الفترة"

    def save_model(self, request, obj, form, change):
        """حفظ التقرير مع تسجيل المنشئ"""
        if not change:  # إذا كان تقرير جديد
            obj.generated_by = request.user
        super().save_model(request, obj, form, change)


# تخصيص عنوان الإدارة
admin.site.site_header = "إدارة نظام التقطيع"
admin.site.site_title = "نظام التقطيع"
admin.site.index_title = "لوحة تحكم التقطيع"
