# نظام المتغيرات والتسعير (Variant System)

## ملخص التنفيذ

تم إنشاء نظام متكامل لإدارة المنتجات ومتغيراتها (الألوان) مع دعم:
- **المنتجات الأساسية (BaseProduct)**: منتج واحد بسعر أساسي
- **المتغيرات (ProductVariant)**: ألوان/موديلات مختلفة لكل منتج
- **التسعير المرن**: سعر أساسي مع إمكانية تخصيص سعر لكل متغير
- **المخزون**: إدارة المخزون على مستوى المتغير + المستودع

## البنية التقنية

### النماذج (Models)
```python
# inventory/models.py
- BaseProduct       # المنتج الأساسي (ORION, HARMONY)
- ProductVariant    # المتغير (C 004, C1)
- ColorAttribute    # تعريف الألوان
- VariantStock      # مخزون المتغير حسب المستودع
- PriceHistory      # سجل تغييرات الأسعار
```

### الخدمات (Services)
```python
# inventory/variant_services.py
- VariantService    # عمليات المتغيرات والترحيل
- PricingService    # عمليات التسعير والتحديث الجماعي
- StockService      # عمليات المخزون والنقل
```

### النماذج (Forms)
```python
# inventory/forms_variants.py
- BaseProductForm
- ProductVariantForm
- ColorAttributeForm
- BulkPriceUpdateForm
- VariantStockUpdateForm
- VariantStockTransferForm
```

## الروابط (URLs)

### المنتجات الأساسية
- `/inventory/base-products/` - قائمة المنتجات
- `/inventory/base-product/create/` - إنشاء منتج
- `/inventory/base-product/<id>/` - تفاصيل المنتج
- `/inventory/base-product/<id>/update/` - تعديل المنتج
- `/inventory/base-product/<id>/delete/` - حذف المنتج

### المتغيرات
- `/inventory/base-product/<id>/variant/create/` - إنشاء متغير
- `/inventory/variant/<id>/` - تفاصيل المتغير
- `/inventory/variant/<id>/update/` - تعديل المتغير
- `/inventory/variant/<id>/delete/` - حذف المتغير

### التسعير
- `/inventory/base-product/<id>/bulk-price-update/` - تحديث جماعي للأسعار
- `/inventory/variant/<id>/update-price/` - تحديث سعر متغير
- `/inventory/variant/<id>/reset-price/` - إعادة السعر للأساسي

### المخزون
- `/inventory/variant/<id>/stock-update/` - تحديث المخزون
- `/inventory/variant/<id>/stock-transfer/` - نقل بين المستودعات

### الألوان
- `/inventory/colors/` - قائمة الألوان
- `/inventory/color/create/` - إضافة لون
- `/inventory/color/<id>/update/` - تعديل لون
- `/inventory/color/<id>/delete/` - حذف لون

### الترحيل
- `/inventory/migrate-products/` - ترحيل المنتجات القديمة

### API
- `/inventory/api/base-product/<id>/variants/` - متغيرات المنتج
- `/inventory/api/variant/<id>/stock/` - مخزون المتغير
- `/inventory/api/variants/search/` - بحث في المتغيرات

## التشغيل

### 1. تشغيل الترحيل (Migrations)
```bash
python manage.py migrate inventory
```

### 2. الوصول للنظام
- افتح: `http://localhost:8000/inventory/base-products/`
- أو من الإدارة: `http://localhost:8000/admin/inventory/baseproduct/`

### 3. ترحيل المنتجات القديمة
- افتح: `http://localhost:8000/inventory/migrate-products/`
- اختر "تجربة" أولاً للمعاينة
- ثم "تنفيذ الترحيل"

## صيغة الكود

المنتجات التي تحتوي على `/` في الكود يتم تحليلها:
```
ORION/C 004  →  Base: ORION,  Variant: C 004
HARMONY /C1  →  Base: HARMONY, Variant: C1
MM-1159/C2   →  Base: MM-1159, Variant: C2
```

## الصلاحيات

```python
# صلاحيات محددة في النماذج
'manage_base_products'    # إدارة المنتجات الأساسية
'manage_variants'         # إدارة المتغيرات
'bulk_price_update'       # تحديث الأسعار بالجملة
'override_variant_price'  # تخصيص سعر المتغير
```

## التكامل مع النظام الحالي

- **المنتج القديم**: يُربط بالمتغير عبر `legacy_product`
- **المخزون**: نظام منفصل للمتغيرات (`VariantStock`)
- **التقارير**: يمكن إضافة تقارير للمتغيرات لاحقاً

## الملفات المُنشأة/المُعدلة

### ملفات جديدة:
- `inventory/variant_services.py`
- `inventory/forms_variants.py`
- `inventory/views_variants.py`
- `inventory/templates/inventory/variants/*.html` (10 قوالب)

### ملفات معدلة:
- `inventory/models.py` (إضافة 5 نماذج)
- `inventory/urls.py` (إضافة ~40 رابط)
- `inventory/admin.py` (تسجيل النماذج الجديدة)

## التاريخ
- **تاريخ الإنشاء**: 2025
- **الإصدار**: 1.0
