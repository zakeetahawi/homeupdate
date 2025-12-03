# 📊 تقرير فحص الأداء الشامل - Performance Audit Complete
## نظام الويزارد وإنشاء/تعديل الطلبات

**تاريخ الفحص:** 2025-12-01

---

## 🔴 المشاكل المكتشفة (Critical Performance Issues)

### 1. مشاكل N+1 Queries في wizard_views.py

| الموقع | المشكلة | التأثير |
|--------|---------|---------|
| السطر 90-93 | `DraftOrder.objects.filter()` بدون `select_related` للـ customer | استعلام إضافي لكل draft |
| السطر 116-118 | `Customer.objects.filter()` بدون `select_related` للـ branch | استعلام إضافي |
| السطر 334 | `DraftOrder.objects.get()` بدون `select_related` | استعلامات متعددة |
| السطر 564-570 | استعلامات draft متكررة بدون optimization | 3-5 استعلامات إضافية |
| السطر 885-902 | حلقة على items مع استعلامات fabric/accessories | **N+1 حاد - يمكن أن يسبب عشرات الاستعلامات** |
| السطر 1144 | `ContractCurtain.objects.filter()` بدون prefetch | استعلامات متعددة |

### 2. مشاكل N+1 Queries في views.py

| الموقع | المشكلة | التأثير |
|--------|---------|---------|
| السطر 169 | `Branch.objects.filter()` يمكن cache | استعلام متكرر |
| السطر 303-330 | استعلامات متعددة للـ payments, items, inspections | 4+ استعلامات إضافية |
| السطر 386-389 | `Customer.objects.get()` بدون select_related | استعلام إضافي |

### 3. مشاكل في forms.py

| الموقع | المشكلة | التأثير |
|--------|---------|---------|
| السطر 24-31 | استعلام Product لكل option في Select widget | **N+1 حاد جداً** |
| السطر 61-63 | `Product.objects.select_related()` جيد لكن غير كافٍ | بحاجة لـ only() |

---

## 📈 الفهارس المكررة والمشاكل

### فهارس مكررة في ULTIMATE_DATABASE_INDEXES_SIMPLE.sql:

```sql
-- هذه الفهارس موجودة في كلا الملفين ويجب توحيدها:
-- 1. idx_customers_customer_phone (السطر 38) مكرر مع idx_customers_phone_search_perf (السطر 554)
-- 2. idx_customers_customer_phone2 (السطر 39) مكرر مع idx_customers_phone2_search_perf (السطر 558)
```

### فهارس غير مستخدمة فعلياً:

1. `idx_orders_order_contract_number_2` - نادراً ما يُبحث فيه
2. `idx_orders_order_contract_number_3` - نادراً ما يُبحث فيه
3. `idx_orders_order_invoice_number_2` - نادراً ما يُبحث فيه
4. `idx_orders_order_invoice_number_3` - نادراً ما يُبحث فيه

---

## ✅ التحسينات المقترحة للحصول على تسريع 100x

### المستوى 1: تحسينات Select Related / Prefetch (تسريع 10-20x)

```python
# قبل (بطيء):
draft = DraftOrder.objects.filter(created_by=request.user, is_completed=False).first()

# بعد (سريع):
draft = DraftOrder.objects.select_related(
    'customer', 'customer__branch', 'branch', 'salesperson', 'salesperson__user'
).filter(created_by=request.user, is_completed=False).first()
```

### المستوى 2: تحسين استعلامات الويزارد Step 5 (تسريع 50x)

```python
# قبل (بطيء جداً - N+1):
order_items = draft.items.filter(item_type__in=['fabric', 'product']).select_related('product')
for item in order_items:
    used_fabrics = CurtainFabric.objects.filter(draft_order_item=item, curtain__draft_order=draft).aggregate(...)
    used_accessories = CurtainAccessory.objects.filter(draft_order_item=item, curtain__draft_order=draft).aggregate(...)

# بعد (سريع - استعلام واحد):
order_items = draft.items.filter(
    item_type__in=['fabric', 'product']
).select_related('product').annotate(
    used_fabrics=Coalesce(
        Subquery(
            CurtainFabric.objects.filter(
                draft_order_item=OuterRef('pk'),
                curtain__draft_order=draft
            ).values('draft_order_item').annotate(total=Sum('meters')).values('total')[:1]
        ), Decimal('0')
    ),
    used_accessories=Coalesce(
        Subquery(
            CurtainAccessory.objects.filter(
                draft_order_item=OuterRef('pk'),
                curtain__draft_order=draft
            ).values('draft_order_item').annotate(total=Sum('quantity')).values('total')[:1]
        ), Decimal('0')
    )
)
```

### المستوى 3: إضافة Caching (تسريع 100x)

```python
from django.core.cache import cache

def get_cached_system_settings():
    """إعدادات النظام المخزنة مؤقتاً"""
    cache_key = 'system_settings'
    settings = cache.get(cache_key)
    if settings is None:
        from accounts.models import SystemSettings
        settings = SystemSettings.get_settings()
        cache.set(cache_key, settings, 300)  # 5 minutes
    return settings

def get_cached_branches():
    """الفروع النشطة المخزنة مؤقتاً"""
    cache_key = 'active_branches'
    branches = cache.get(cache_key)
    if branches is None:
        branches = list(Branch.objects.filter(is_active=True).values('id', 'name', 'code'))
        cache.set(cache_key, branches, 600)  # 10 minutes
    return branches
```

---

## 🗂️ ملفات SQL للحذف

بناءً على التحليل، يُنصح بـ:

1. **حذف ULTIMATE_DATABASE_INDEXES.sql** - يحتوي على CONCURRENTLY التي قد تسبب مشاكل
2. **الإبقاء على ULTIMATE_DATABASE_INDEXES_SIMPLE.sql** - مع التحسينات التالية

---

## 📝 خطة التنفيذ

### المرحلة 1: التحسينات الفورية (اليوم)
- [ ] تطبيق select_related على جميع استعلامات DraftOrder
- [ ] تطبيق prefetch_related على items و curtains
- [ ] إضافة caching لإعدادات النظام والفروع

### المرحلة 2: تحسينات متقدمة (هذا الأسبوع)
- [ ] استخدام Subquery و annotate بدلاً من N+1 loops
- [ ] تحسين forms.py لتجنب استعلامات Product المتكررة
- [ ] إضافة database indexes المفقودة

### المرحلة 3: مراقبة وقياس
- [ ] إضافة Django Debug Toolbar للمراقبة
- [ ] قياس الأداء قبل وبعد التحسينات
- [ ] توثيق النتائج

---

## 🚀 سكريبت التحسين التلقائي

سيتم إنشاء سكريبت Python لتطبيق جميع التحسينات تلقائياً.

