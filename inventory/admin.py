from django.contrib import admin

from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from .models import (
    Category, Product, StockTransaction, Supplier, PurchaseOrder, PurchaseOrderItem,
    Warehouse, WarehouseLocation, ProductBatch, InventoryAdjustment, StockAlert,
    StockTransfer, StockTransferItem
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('name', 'parent')
    list_filter = ('parent',)
    search_fields = ('name', 'description')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_per_page = 20  # تقليل من 50 إلى 20 لتحسين الأداء
    show_full_result_count = False  # تعطيل عدد النتائج لتحسين الأداء
    list_display = ('name', 'code', 'category', 'price', 'get_current_stock', 'get_stock_status')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('get_current_stock', 'created_at', 'updated_at')

    def get_queryset(self, request):
        """تحسين الاستعلامات لتقليل N+1 queries"""
        return super().get_queryset(request).select_related(
            'category'
        ).only(
            'id', 'name', 'code', 'price', 'minimum_stock',
            'created_at', 'updated_at', 'category__id', 'category__name'
        )

    fieldsets = (
        (_('معلومات المنتج'), {
            'fields': ('name', 'code', 'category', 'description')
        }),
        (_('التفاصيل'), {
            'fields': ('unit', 'price', 'minimum_stock')
        }),
        (_('معلومات المخزون'), {
            'fields': ('get_current_stock', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_current_stock(self, obj):
        # استخدام خاصية current_stock المحسنة من النموذج
        return obj.current_stock
    get_current_stock.short_description = _('المخزون الحالي')

    def get_stock_status(self, obj):
        current_stock = self.get_current_stock(obj)
        if current_stock <= 0:
            return _('نفذ من المخزون')
        elif current_stock <= obj.minimum_stock:
            return _('مخزون منخفض')
        return _('متوفر')
    get_stock_status.short_description = _('حالة المخزون')

    def get_queryset(self, request):
        """استعلام محسن للمنتجات مع تحسين حساب المخزون"""
        return super().get_queryset(request).select_related(
            'category'
        ).only(
            'id', 'name', 'code', 'description', 'unit', 'price', 'minimum_stock',
            'created_at', 'updated_at',
            'category__id', 'category__name'
        )

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('product', 'transaction_type', 'reason', 'quantity', 'date')
    list_filter = ('transaction_type', 'reason', 'date')
    search_fields = ('product__name', 'reference', 'notes')
    readonly_fields = ('date', 'created_by')

    fieldsets = (
        (_('معلومات الحركة'), {
            'fields': ('product', 'transaction_type', 'reason', 'quantity')
        }),
        (_('التفاصيل'), {
            'fields': ('reference', 'notes')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'date'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('name', 'contact_person', 'phone', 'email')
    search_fields = ('name', 'contact_person', 'phone', 'email', 'address')

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('order_number', 'supplier', 'status', 'order_date', 'total_amount')
    list_filter = ('status', 'order_date')
    search_fields = ('order_number', 'supplier__name', 'notes')
    readonly_fields = ('order_date', 'created_by')

    fieldsets = (
        (_('معلومات طلب الشراء'), {
            'fields': ('order_number', 'supplier', 'warehouse', 'status')
        }),
        (_('التواريخ'), {
            'fields': ('expected_date',)
        }),
        (_('المعلومات المالية'), {
            'fields': ('total_amount',)
        }),
        (_('ملاحظات إضافية'), {
            'fields': ('notes',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('purchase_order', 'product', 'quantity', 'unit_price', 'received_quantity')
    list_filter = ('purchase_order__status',)
    search_fields = ('purchase_order__order_number', 'product__name')

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('name', 'code', 'branch', 'manager', 'is_active')
    list_filter = ('branch', 'is_active')
    search_fields = ('name', 'code', 'address')

@admin.register(WarehouseLocation)
class WarehouseLocationAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('name', 'code', 'warehouse')
    list_filter = ('warehouse',)
    search_fields = ('name', 'code', 'description')

@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('product', 'batch_number', 'location', 'quantity', 'expiry_date')
    list_filter = ('location__warehouse', 'manufacturing_date', 'expiry_date')
    search_fields = ('product__name', 'batch_number', 'barcode')
    readonly_fields = ('barcode', 'created_at')

@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('product', 'adjustment_type', 'quantity_before', 'quantity_after', 'date')
    list_filter = ('adjustment_type', 'date')
    search_fields = ('product__name', 'reason')
    readonly_fields = ('date', 'created_by')

@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('product', 'alert_type', 'status', 'created_at')
    list_filter = ('alert_type', 'status', 'created_at')
    search_fields = ('product__name', 'message')
    readonly_fields = ('created_at', 'resolved_at', 'resolved_by')


class StockTransferItemInline(admin.TabularInline):
    """عرض عناصر التحويل المخزني"""
    model = StockTransferItem
    extra = 1
    fields = ['product', 'quantity', 'received_quantity', 'notes']
    autocomplete_fields = ['product']


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    """إدارة التحويلات المخزنية"""
    list_per_page = 50
    list_display = [
        'transfer_number', 'from_warehouse', 'to_warehouse',
        'status', 'total_items', 'total_quantity',
        'transfer_date', 'created_by'
    ]
    list_filter = ['status', 'from_warehouse', 'to_warehouse', 'transfer_date', 'created_at']
    search_fields = ['transfer_number', 'notes', 'reason']
    readonly_fields = [
        'transfer_number', 'created_at', 'updated_at', 'created_by',
        'approved_by', 'approved_at', 'completed_by', 'completed_at',
        'total_items', 'total_quantity'
    ]
    fieldsets = (
        (_('معلومات التحويل'), {
            'fields': (
                'transfer_number', 'from_warehouse', 'to_warehouse',
                'status', 'transfer_date'
            )
        }),
        (_('التواريخ'), {
            'fields': (
                'expected_arrival_date', 'actual_arrival_date'
            )
        }),
        (_('التفاصيل'), {
            'fields': ('reason', 'notes')
        }),
        (_('الإحصائيات'), {
            'fields': ('total_items', 'total_quantity'),
            'classes': ('collapse',)
        }),
        (_('معلومات التتبع'), {
            'fields': (
                'created_at', 'created_by', 'updated_at',
                'approved_by', 'approved_at',
                'completed_by', 'completed_at'
            ),
            'classes': ('collapse',)
        }),
    )
    inlines = [StockTransferItemInline]

    def save_model(self, request, obj, form, change):
        if not change:  # إذا كان إنشاء جديد
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(StockTransferItem)
class StockTransferItemAdmin(admin.ModelAdmin):
    """إدارة عناصر التحويل المخزني"""
    list_per_page = 50
    list_display = [
        'transfer', 'product', 'quantity',
        'received_quantity', 'is_fully_received'
    ]
    list_filter = ['transfer__status', 'transfer__from_warehouse', 'transfer__to_warehouse']
    search_fields = ['transfer__transfer_number', 'product__name', 'product__code']
    autocomplete_fields = ['transfer', 'product']