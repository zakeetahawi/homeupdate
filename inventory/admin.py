from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from .models import (
    Category, Product, StockTransaction, Supplier, PurchaseOrder, PurchaseOrderItem,
    Warehouse, WarehouseLocation, ProductBatch, InventoryAdjustment, StockAlert,
    StockTransfer, StockTransferItem, BulkUploadLog, BulkUploadError,
    # Variant System Models
    BaseProduct, ProductVariant, ColorAttribute, VariantStock, PriceHistory
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
    list_display = ('name', 'code', 'category', 'price', 'get_current_stock', 'get_stock_status', 'has_qr')
    list_filter = ('category', 'created_at', ('qr_code_base64', admin.EmptyFieldListFilter))
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('get_current_stock', 'created_at', 'updated_at', 'qr_preview')
    actions = ['regenerate_qr_codes']

    fieldsets = (
        (_('معلومات المنتج'), {
            'fields': ('name', 'code', 'category', 'description')
        }),
        (_('التفاصيل'), {
            'fields': ('unit', 'price', 'minimum_stock')
        }),
        (_('رمز QR'), {
            'fields': ('qr_preview',),
            'classes': ('collapse',)
        }),
        (_('معلومات المخزون'), {
            'fields': ('get_current_stock', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_qr(self, obj):
        return bool(obj.qr_code_base64)
    has_qr.boolean = True
    has_qr.short_description = _('QR')

    def qr_preview(self, obj):
        if obj.qr_code_base64:
            return format_html(
                '<img src="data:image/png;base64,{}" style="width:150px; height:150px; border:1px solid #ddd; border-radius:8px;" />',
                obj.qr_code_base64
            )
        return _('لا يوجد QR - سيتم توليده عند الحفظ')
    qr_preview.short_description = _('معاينة QR')

    @admin.action(description=_('إعادة توليد رموز QR للمنتجات المحددة'))
    def regenerate_qr_codes(self, request, queryset):
        count = 0
        for product in queryset:
            if product.code:
                product.generate_qr(force=True)
                product.save(update_fields=['qr_code_base64'])
                count += 1
        self.message_user(request, f'تم توليد {count} رمز QR بنجاح')

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
            'created_at', 'updated_at', 'qr_code_base64',
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


class BulkUploadErrorInline(admin.TabularInline):
    """عرض أخطاء الرفع الجماعي"""
    model = BulkUploadError
    extra = 0
    fields = ['row_number', 'error_type', 'error_message', 'product_name']
    readonly_fields = ['row_number', 'error_type', 'error_message', 'product_name', 'created_at']
    can_delete = False
    max_num = 0  # لا يمكن إضافة أخطاء من الأدمن

    def product_name(self, obj):
        return obj.product_name
    product_name.short_description = _('اسم المنتج')


@admin.register(BulkUploadLog)
class BulkUploadLogAdmin(admin.ModelAdmin):
    """إدارة سجلات الرفع الجماعي"""
    list_per_page = 50
    list_display = [
        'id', 'upload_type', 'file_name', 'status',
        'total_rows', 'created_count', 'updated_count', 'error_count',
        'success_rate', 'created_at', 'created_by'
    ]
    list_filter = ['upload_type', 'status', 'created_at', 'warehouse']
    search_fields = ['file_name', 'summary', 'created_by__username']
    readonly_fields = [
        'upload_type', 'status', 'file_name', 'warehouse',
        'total_rows', 'processed_count', 'created_count', 'updated_count', 'error_count',
        'options', 'created_warehouses', 'summary',
        'created_at', 'completed_at', 'created_by',
        'success_rate', 'duration', 'has_errors'
    ]
    fieldsets = (
        (_('معلومات العملية'), {
            'fields': (
                'upload_type', 'status', 'file_name', 'warehouse'
            )
        }),
        (_('الإحصائيات'), {
            'fields': (
                'total_rows', 'processed_count',
                'created_count', 'updated_count', 'error_count',
                'success_rate', 'duration'
            )
        }),
        (_('التفاصيل'), {
            'fields': ('options', 'created_warehouses', 'summary'),
            'classes': ('collapse',)
        }),
        (_('معلومات التتبع'), {
            'fields': ('created_at', 'completed_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    inlines = [BulkUploadErrorInline]

    def success_rate(self, obj):
        return f"{obj.success_rate}%"
    success_rate.short_description = _('نسبة النجاح')

    def duration(self, obj):
        if obj.duration:
            return f"{obj.duration:.2f} ثانية"
        return '-'
    duration.short_description = _('المدة')

    def has_errors(self, obj):
        return '✓' if obj.has_errors else '✗'
    has_errors.short_description = _('يوجد أخطاء')
    has_errors.boolean = True

    def has_add_permission(self, request):
        return False  # لا يمكن إضافة سجلات يدوياً


@admin.register(BulkUploadError)
class BulkUploadErrorAdmin(admin.ModelAdmin):
    """إدارة أخطاء الرفع الجماعي"""
    list_per_page = 100
    list_display = [
        'upload_log', 'row_number', 'error_type',
        'product_name', 'product_code', 'short_error_message', 'created_at'
    ]
    list_filter = ['error_type', 'upload_log__upload_type', 'created_at']
    search_fields = ['error_message', 'upload_log__file_name']
    readonly_fields = [
        'upload_log', 'row_number', 'error_type', 'error_message',
        'row_data', 'product_name', 'product_code', 'created_at'
    ]
    fieldsets = (
        (_('معلومات الخطأ'), {
            'fields': (
                'upload_log', 'row_number', 'error_type', 'error_message'
            )
        }),
        (_('بيانات الصف'), {
            'fields': ('row_data', 'product_name', 'product_code'),
            'classes': ('collapse',)
        }),
        (_('معلومات التسجيل'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def product_name(self, obj):
        return obj.product_name
    product_name.short_description = _('اسم المنتج')

    def product_code(self, obj):
        return obj.product_code or '-'
    product_code.short_description = _('الكود')

    def short_error_message(self, obj):
        return obj.error_message[:100] + '...' if len(obj.error_message) > 100 else obj.error_message
    short_error_message.short_description = _('رسالة الخطأ')

    def has_add_permission(self, request):
        return False  # لا يمكن إضافة أخطاء يدوياً


# ==================== Variant System Admin ====================

class ProductVariantInline(admin.TabularInline):
    """Inline لعرض المتغيرات داخل المنتج الأساسي"""
    model = ProductVariant
    extra = 0
    fields = ('variant_code', 'color', 'color_code', 'price_override', 'is_active')
    readonly_fields = ()
    show_change_link = True


@admin.register(BaseProduct)
class BaseProductAdmin(admin.ModelAdmin):
    list_per_page = 25
    list_display = ('code', 'name', 'category', 'base_price', 'variants_count', 'is_active')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'description')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    inlines = [ProductVariantInline]
    
    fieldsets = (
        (_('معلومات المنتج الأساسي'), {
            'fields': ('name', 'code', 'category', 'description')
        }),
        (_('التسعير'), {
            'fields': ('base_price', 'currency', 'unit')
        }),
        (_('المخزون'), {
            'fields': ('minimum_stock', 'is_active')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def variants_count(self, obj):
        return obj.variants.count()
    variants_count.short_description = _('عدد المتغيرات')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_per_page = 25
    list_display = ('full_code', 'base_product', 'variant_code', 'color', 'effective_price', 'has_custom_price', 'is_active')
    list_filter = ('base_product', 'color', 'is_active')
    search_fields = ('variant_code', 'base_product__name', 'base_product__code', 'barcode')
    readonly_fields = ('full_code', 'effective_price', 'created_at', 'updated_at')
    raw_id_fields = ('base_product', 'legacy_product')
    
    fieldsets = (
        (_('معلومات المتغير'), {
            'fields': ('base_product', 'variant_code', 'full_code')
        }),
        (_('اللون'), {
            'fields': ('color', 'color_code')
        }),
        (_('التسعير'), {
            'fields': ('price_override', 'effective_price')
        }),
        (_('معلومات إضافية'), {
            'fields': ('barcode', 'description', 'is_active')
        }),
        (_('الربط بالنظام القديم'), {
            'fields': ('legacy_product',),
            'classes': ('collapse',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def full_code(self, obj):
        return obj.full_code
    full_code.short_description = _('الكود الكامل')
    
    def effective_price(self, obj):
        return obj.effective_price
    effective_price.short_description = _('السعر الفعلي')
    
    def has_custom_price(self, obj):
        return obj.has_custom_price
    has_custom_price.short_description = _('سعر مخصص')
    has_custom_price.boolean = True


@admin.register(ColorAttribute)
class ColorAttributeAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('name', 'code', 'hex_code', 'display_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('display_order', 'name')


@admin.register(VariantStock)
class VariantStockAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ('variant', 'warehouse', 'current_quantity', 'reserved_quantity', 'available_quantity', 'last_updated')
    list_filter = ('warehouse', 'last_updated')
    search_fields = ('variant__base_product__name', 'variant__variant_code')
    raw_id_fields = ('variant',)
    readonly_fields = ('available_quantity', 'last_updated')
    
    def available_quantity(self, obj):
        return obj.available_quantity
    available_quantity.short_description = _('المتاح')


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        'variant_code', 'base_product_name', 'old_price', 'new_price', 
        'price_change', 'change_percentage', 'change_type', 'changed_at', 'changed_by'
    )
    list_filter = (
        'change_type',
        ('changed_at', admin.DateFieldListFilter),
        ('changed_by', admin.RelatedOnlyFieldListFilter),
        ('variant__base_product', admin.RelatedOnlyFieldListFilter),
        ('variant__base_product__category', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        'variant__base_product__name', 
        'variant__base_product__code',
        'variant__variant_code',
        'variant__barcode',
        'notes',
        'changed_by__username',
    )
    readonly_fields = (
        'variant', 'old_price', 'new_price', 'change_type', 
        'change_value', 'changed_at', 'changed_by', 'notes'
    )
    date_hierarchy = 'changed_at'
    list_select_related = ('variant', 'variant__base_product', 'changed_by')
    ordering = ('-changed_at',)
    
    fieldsets = (
        ('معلومات المتغير', {
            'fields': ('variant',)
        }),
        ('تفاصيل التغيير', {
            'fields': ('old_price', 'new_price', 'change_type', 'change_value')
        }),
        ('معلومات إضافية', {
            'fields': ('changed_at', 'changed_by', 'notes')
        }),
    )
    
    class Media:
        css = {
            'all': ('admin/css/price_history.css',)
        }
    
    def _truncate_text(self, text, max_length=25):
        """تقصير النص مع إظهار النص الكامل عند التمرير"""
        if not text:
            return '-'
        text = str(text)
        if len(text) > max_length:
            return format_html(
                '<span title="{}" style="cursor:help;">{}&hellip;</span>',
                text,
                text[:max_length]
            )
        return text
    
    @admin.display(description='كود المتغير')
    def variant_code(self, obj):
        code = obj.variant.full_code
        return self._truncate_text(code, 20)
    
    @admin.display(description='المنتج الأساسي')
    def base_product_name(self, obj):
        name = obj.variant.base_product.name
        return self._truncate_text(name, 25)
    
    @admin.display(description='الفرق')
    def price_change(self, obj):
        diff = obj.new_price - obj.old_price
        diff_str = f'{diff:.2f}'
        if diff > 0:
            return format_html('<span style="color:green;">+{}</span>', diff_str)
        elif diff < 0:
            return format_html('<span style="color:red;">{}</span>', diff_str)
        return '0.00'
    
    @admin.display(description='النسبة %')
    def change_percentage(self, obj):
        if obj.old_price and obj.old_price != 0:
            perc = ((obj.new_price - obj.old_price) / obj.old_price) * 100
            perc_str = f'{perc:.1f}%'
            if perc > 0:
                return format_html('<span style="color:green;">+{}</span>', perc_str)
            elif perc < 0:
                return format_html('<span style="color:red;">{}</span>', perc_str)
            return '0%'
        return '-'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # السماح للمشرفين فقط بالحذف
        return request.user.is_superuser