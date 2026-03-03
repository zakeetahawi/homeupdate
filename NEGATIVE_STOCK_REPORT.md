# تقرير: مشكلة الأرصدة السالبة في مستودع الادويه
**تاريخ التحليل:** 2026-03-03  
**المحلل:** GitHub Copilot  
**الحالة:** ⚠️ بانتظار الإصلاح من جهاز التطوير

---

## 🔍 تشخيص السبب الجذري

### المشكلة الأساسية: نقل مخزون غير مكتمل

المنتجات كانت في **مستودع الادوية** ثم نُقلت إلى **المستودع الرئيسي**، لكن معاملات القص والبيع اللاحقة استمرت تُسجَّل على **الادوية** (المستودع القديم الفارغ) بدلاً من **الرئيسي** — مما أنتج رصيداً سالباً في الادوية ورصيداً صحيحاً في الرئيسي.

```
الادوية     → خُصم منها بيع/قص → رصيد سالب  ❌
الرئيسي    → المخزون الحقيقي   → رصيد موجب ✅
```

### دليل من البيانات (مثال: CITO-FN/C SQUASH)

| ID | المستودع | النوع | الكمية | الرصيد المتحرك |
|----|----------|-------|--------|---------------|
| 3665-73308 | الرئيسى | in/out | متعدد | **19,998.500** |
| **74509** | **الادويه** | **out** | **78.000** | **-78.000** ← المشكلة |
| 74571 | الرئيسى | out | 78.000 | 19,920.500 |

> **السبب:** المعاملة 74509 أُسندت خطأً لمستودع "الادوية" بدلاً من "الرئيسي".  
> المخزون الفعلي موجود في الرئيسي بـ ~20,000 متر.

---

## 📊 حجم المشكلة الكاملة (26 منتجاً)

| المنتج | الكود | رصيد الادوية | رصيد الرئيسي | العجز |
|--------|-------|-------------|-------------|-------|
| CITO-FN/C SQUASH | 10100303953 | -78.000 | 19,920.500 | 78 |
| KOYA/C51 | 10100300375 | -60.000 | 18,012.500 | 60 |
| MO - GERMAN/C5 | 10100300457 | -58.000 | 20,032.750 | 58 |
| dona/C STEEL 1989 | 10100300247 | -41.000 | 18,005.000 | 41 |
| HARMONY /C1 | 10100303955 | -40.000 | 18,051.500 | 40 |
| CAROLINA/C1 | 10100303330 | -35.000 | 33,960.000 | 35 |
| KOYA/C20 | 10100300349 | -20.500 | 18,062.500 | 20.5 |
| NEW M-3V/C OFF WHITE | 10200202691 | -20.000 | 17,984.750 | 20 |
| BLACKOUT-E/C WHITE | 10200100279 | -17.000 | 18,128.500 | 17 |
| MOSHA PD /C17 | 10100303368 | -15.000 | 18,025.000 | 15 |
| FLIX/C7 | 10200201988 | -10.000 | 17,990.000 | 10 |
| FERRARI/C جينز 2535 | 10100301975 | -8.000 | 18,067.000 | 8 |
| OKAA/C16 | 10100302649 | -8.000 | 19,987.000 | 8 |
| PRINT-KASTER | 10100200001 | -8.000 | 38,245.000 | 8 |
| M-boucle/C OFFWHITE | 10200201488 | -7.000 | 18,026.500 | 7 |
| FLIX/C4 | 10200202238 | -7.000 | 17,966.000 | 7 |
| VILLA-NEW \C8 | 10100304007 | -6.500 | 26,000.000 | 6.5 |
| ONTARIO-280/C CASTEL | 10100302661 | -5.250 | 216,724.000 | 5.25 |
| KOYA/C5 | 10100300373 | -5.000 | 18,103.000 | 5 |
| MO - GERMAN/C19 | 10100300426 | -4.000 | 20,001.000 | 4 |
| ONTARIO-280/C BLUE | 10100302659 | -4.000 | 169,848.000 | 4 |
| FERRARI/C كحلى 2514 | 10100301986 | -4.000 | 18,044.750 | 4 |
| KOYA/C1 | 10100300340 | -3.500 | 18,132.000 | 3.5 |
| ATX/C2 | 10100300120 | -3.000 | 18,048.500 | 3 |
| SABIA/C JAVA 2200 | 10100300733 | -2.000 | 18,000.000 | 2 |
| قص ولحمة 50%/C 1 | 10200100329 | -1.500 | 18,000.000 | 1.5 |

**إجمالي العجز:** ~531.25 متر موزعة على 26 منتجاً

---

## 🔧 خطة الإصلاح المقترحة

### الفكرة العامة
لكل منتج ذي رصيد سالب في الادوية:
1. **تحديد معاملات الخصم الخاطئة** المسجّلة على "الادوية" (out/sale/production)
2. **تعديل `warehouse`** في هذه المعاملات من "الادوية" → "الرئيسي"
3. **إعادة حساب `running_balance`** لكل من الادوية والرئيسي
4. تسجيل `InventoryAdjustment` للمراجعة والتدقيق

### الآلية التقنية في الكود

`running_balance` محسوب **لكل مستودع منفصل** داخل `StockTransaction.save()`:

```python
# من inventory/models.py السطر 636-695
def save(self, *args, **kwargs):
    with transaction.atomic():
        previous_balance = StockTransaction.objects.filter(
            product=self.product,
            warehouse=self.warehouse,        # ← مفصول بالمستودع
            transaction_date__lt=self.transaction_date,
        ).order_by("-transaction_date", "-id").first()
        
        # يحسب الرصيد بناءً على المعاملة السابقة في نفس المستودع
        # ثم يُحدّث كل المعاملات اللاحقة في نفس المستودع
```

**إذن الإصلاح الصحيح:** تعديل `warehouse` في المعاملة الخاطئة ثم استدعاء `.save()` على نفس المعاملة يُصحّح التسلسل تلقائياً.

---

## 💻 الكود المقترح للإصلاح (على جهاز التطوير)

```python
# python manage.py shell_plus
from inventory.models import StockTransaction, Warehouse, Product
from django.db.models import OuterRef, Subquery
from django.db import transaction as db_transaction

warehouse_ada = Warehouse.objects.get(id=24)     # الادويه
warehouse_main = Warehouse.objects.get(name='الرئيسى')

# ===== STEP 1: الحصول على المنتجات ذات الرصيد السالب =====
latest_balance_subq = StockTransaction.objects.filter(
    warehouse=warehouse_ada, product=OuterRef('pk')
).order_by('-transaction_date', '-id').values('running_balance')[:1]

neg_products = Product.objects.annotate(
    last_balance=Subquery(latest_balance_subq)
).filter(last_balance__lt=0)

print(f'عدد المنتجات المتأثرة: {neg_products.count()}')

# ===== STEP 2: لكل منتج — تحديد المعاملات الخاطئة وإصلاحها =====
fixed_count = 0
errors = []

for product in neg_products:
    print(f'\n🔧 معالجة: {product.name} ({product.code})')
    
    # المعاملات المسجّلة خطأ على "الادوية" (out فقط، ليس نقل)
    wrong_txns = StockTransaction.objects.filter(
        product=product,
        warehouse=warehouse_ada,
        transaction_type__in=['out', 'adjustment'],
    ).order_by('transaction_date', 'id')
    
    print(f'  معاملات خاطئة على الادوية: {wrong_txns.count()}')
    
    with db_transaction.atomic():
        for txn in wrong_txns:
            print(f'  → تعديل معاملة ID={txn.id} | {txn.reason} | {txn.quantity} | {txn.transaction_date}')
            # تعديل المستودع → save() يُعيد حساب running_balance تلقائياً
            txn.warehouse = warehouse_main
            txn.save()  # ← هذا يُحدّث running_balance للمستودعين
            fixed_count += 1
    
    # تحقق من النتيجة
    latest = StockTransaction.objects.filter(
        product=product, warehouse=warehouse_ada
    ).order_by('-transaction_date', '-id').first()
    
    if latest and latest.running_balance < 0:
        print(f'  ⚠️ لا يزال سالباً: {latest.running_balance}')
        errors.append(product.code)
    else:
        remaining = latest.running_balance if latest else 0
        print(f'  ✅ الرصيد في الادوية الآن: {remaining}')

print(f'\n✅ تم تعديل {fixed_count} معاملة')
if errors:
    print(f'❌ منتجات تحتاج مراجعة يدوية: {errors}')
```

### بديل أبسط — إنشاء معاملة تسوية (إذا تعذّر تعديل المعاملات القديمة)

```python
# لكل منتج سالب: إنشاء "in" بالكمية المطلوبة في "الرئيسي"
# وإنشاء "adjustment" بالكمية نفسها في "الادوية" لإعادتها للصفر

from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

User = get_user_model()
system_user = User.objects.filter(is_superuser=True).first()

for product in neg_products:
    neg_balance = product.last_balance  # مثلاً -78
    correction = abs(Decimal(str(neg_balance)))
    
    with db_transaction.atomic():
        # 1. تسوية في الادوية لرفع الرصيد إلى الصفر
        StockTransaction.objects.create(
            product=product,
            warehouse=warehouse_ada,
            transaction_type='adjustment',
            reason='inventory_check',
            quantity=correction,
            reference=f'FIX-{timezone.now().strftime("%Y%m%d")}',
            notes=f'تصحيح رصيد سالب: تسوية ناتجة عن نقل غير مكتمل',
            created_by=system_user,
        )
```

---

## ⚠️ نقطة مهمة: منع تكرار المشكلة

### السبب في signal موجود لكنه يُحذّر فقط
في `inventory/signals.py` السطر 82-93 يوجد تحذير عند إدخال منتج في مستودع آخر لكنه **لا يمنع العملية**.

### التوصية: إضافة `unique_together` على مستودع المنتج

```python
# في inventory/models.py — نموذج ProductWarehouse أو إضافة قيد على StockAlert
# يمنع وجود رصيد إيجابي لنفس المنتج في أكثر من مستودع واحد في نفس الوقت
```

أو **في واجهة إدخال الطلب/القص**: إضافة validation يتحقق من المستودع الصحيح قبل تسجيل المعاملة:

```python
# في views/forms الخاص بالقص والبيع
def clean_warehouse(self):
    warehouse = self.cleaned_data['warehouse']
    product = self.cleaned_data.get('product')
    if product:
        # المستودع الذي به رصيد فعلي
        correct_warehouse = StockTransaction.objects.filter(
            product=product
        ).order_by('-transaction_date', '-id').first()
        if correct_warehouse and correct_warehouse.warehouse != warehouse:
            raise ValidationError(
                f'المنتج موجود في مستودع {correct_warehouse.warehouse.name}، '
                f'وليس في {warehouse.name}'
            )
    return warehouse
```

---

## 📋 ترتيب أولويات الإصلاح

| # | الخطوة | الأسلوب | الأولوية |
|---|--------|---------|---------|
| 1 | **تعديل warehouse في المعاملات الخاطئة** | `txn.warehouse = main; txn.save()` | 🔴 عاجل |
| 2 | أو تسوية بـ adjustment إن تعذّر التعديل | `StockTransaction.create(type=adjustment)` | 🔴 عاجل |
| 3 | **التحقق من المستودع عند إدخال القص/البيع** | Validation في الـ form/view | 🟠 مهم |
| 4 | تعديل signal ليمنع بدلاً من الإنذار فقط | `signals.py` → raise ValidationError | 🟡 مستقبلي |

---

## 🗂️ الملفات ذات الصلة

| الملف | الاستخدام |
|-------|-----------|
| `inventory/models.py` L636-695 | `StockTransaction.save()` — حساب running_balance |
| `inventory/signals.py` L50-93 | التحذير عند إدخال منتج في مستودع آخر |
| `inventory/management/commands/fix_negative_stock.py` | أمر تسوية موجود (يُعيد للصفر، يحتاج تعديل) |
| `inventory/views_extended.py` L927-939 | كيفية إنشاء StockTransaction في الـ views |

---

*تحليل: GitHub Copilot — 2026-03-03*
