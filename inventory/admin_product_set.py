"""
Admin configuration for ProductSet
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import ProductSet, ProductSetItem


class ProductSetItemInline(admin.TabularInline):
    model = ProductSetItem
    extra = 1
    min_num = 2
    max_num = 5
    fields = ("base_product", "display_order")
    autocomplete_fields = ["base_product"]


@admin.register(ProductSet)
class ProductSetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_products_count",
        "is_active",
        "sync_status",
        "last_synced_at",
        "created_at",
    )
    list_filter = (
        "is_active",
        "cloudflare_synced",
        "created_at",
    )
    search_fields = ("name", "description")
    inlines = [ProductSetItemInline]
    readonly_fields = ("cloudflare_synced", "last_synced_at", "created_at", "updated_at")
    actions = ["sync_to_cloudflare"]
    fieldsets = (
        (
            "معلومات أساسية",
            {
                "fields": ("name", "description", "is_active"),
            },
        ),
        (
            "معلومات المزامنة",
            {
                "fields": ("cloudflare_synced", "last_synced_at"),
            },
        ),
        (
            "معلومات النظام",
            {
                "fields": ("created_at", "updated_at", "created_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_products_count(self, obj):
        count = obj.base_products.count()
        return format_html('<span style="font-weight:bold">{}</span>', count)

    get_products_count.short_description = "عدد المنتجات"

    def sync_status(self, obj):
        if obj.cloudflare_synced:
            return format_html(
                '<span style="color:green">✔ متزامن</span>'
            )
        return format_html(
            '<span style="color:orange">⚠ غير متزامن</span>'
        )

    sync_status.short_description = "حالة المزامنة"

    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        
        # Mark as unsynced when saving
        obj.cloudflare_synced = False
        super().save_model(request, obj, form, change)
    
    def sync_to_cloudflare(self, request, queryset):
        """مزامنة المجموعات المختارة مع Cloudflare"""
        from accounting.cloudflare_sync import sync_product_sets_to_cloudflare
        
        result = sync_product_sets_to_cloudflare(queryset)
        
        if result.get("success"):
            self.message_user(
                request,
                f"✅ تمت مزامنة {result.get('count', 0)} مجموعة بنجاح",
                level="success"
            )
        else:
            self.message_user(
                request,
                f"❌ فشلت المزامنة: {result.get('error', 'خطأ غير معروف')}",
                level="error"
            )
    
    sync_to_cloudflare.short_description = "🔄 مزامنة مع Cloudflare"
