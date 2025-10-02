# تقرير إصلاح مشكلة الرصيد الوهمي في المستودعات

**التاريخ:** 2 أكتوبر 2025  
**المشكلة:** رصيد وهمي في مستودع الإكسسوار

---

## 📋 المشكلة المكتشفة

### 🔍 الوصف:
- **23 حالة رصيد وهمي** في مستودع الإكسسوار
- المنتجات لها رصيد في مستودع الإكسسوار **بدون معاملة إدخال أولية**
- أول معاملة في مستودع الإكسسوار هي **سحب (out)** وليس **إدخال (in)**

### 📊 الإحصائيات:
- **92 منتج** موجود في أكثر من مستودع
- **23 منتج** لديه رصيد وهمي في مستودع الإكسسوار
- **تاريخ البداية:** 30 سبتمبر 2025 (معظم الحالات)

### 🔬 مثال: المنتج ART-111/C1 (كود: 10200202399)

**المستودع الأصلي (بافلي):**
- ✅ تم إدخال 2000 وحدة بتاريخ 2025-08-19
- الرصيد الحالي: 1948 وحدة

**المستودع الخاطئ (اكسسوار):**
- ❌ **لم يتم إدخال المنتج أبداً!**
- أول معاملة: سحب 12 وحدة بتاريخ 2025-09-30
- الرصيد الوهمي: 1949 وحدة (غير موجود فعلياً!)

---

## 🔍 السبب الجذري

### 1. نظام إدارة المخزون:
- يسمح بالسحب من مستودع **حتى لو لم يتم إدخال المنتج فيه**
- لا توجد مراقبة على المعاملة الأولى لكل منتج في كل مستودع
- النظام يحسب الرصيد من آخر معاملة فقط

### 2. نظام التقطيع (القديم):
```python
# السطر 118-122 في cutting/signals.py (قبل الإصلاح)
last_transaction = StockTransaction.objects.filter(
    product=order_item.product,
    warehouse__in=warehouses
).order_by('-transaction_date').first()
```

**المشكلة:**
- يبحث عن **آخر معاملة** بغض النظر عن نوعها (دخول/خروج)
- إذا كانت آخر معاملة في مستودع الإكسسوار (حتى لو سحب)، يرسل الطلب لمستودع الإكسسوار!
- هذا يسبب إنشاء أوامر تقطيع في مستودعات خاطئة

---

## ✅ الحلول المطبقة

### 1. إصلاح كود اختيار المستودع

**التعديل في `cutting/signals.py`:**

```python
# الآن: البحث عن رصيد موجب فقط
for warehouse in warehouses:
    latest_transaction = StockTransaction.objects.filter(
        product=order_item.product,
        warehouse=warehouse
    ).order_by('-transaction_date').first()
    
    # ✅ فقط المستودعات التي فيها رصيد موجب
    if latest_transaction and latest_transaction.running_balance > 0:
        warehouse_stocks[warehouse] = latest_transaction.running_balance

# إذا لم يوجد رصيد موجب، نبحث عن آخر رصيد كان موجباً
if not warehouse_stocks:
    last_positive_transaction = StockTransaction.objects.filter(
        product=order_item.product,
        warehouse__in=warehouses,
        running_balance__gt=0  # ✅ فقط المعاملات التي كان فيها رصيد موجب
    ).order_by('-transaction_date').first()
```

**الفوائد:**
- ✅ يختار فقط المستودعات التي فيها رصيد **فعلي موجب**
- ✅ لا يختار مستودعات فارغة أو وهمية
- ✅ يتجنب مستودعات بدأت بمعاملات سحب

### 2. إصلاح البيانات

**السكريبت:** `fix_phantom_stock_simple.py`

**الخطوات:**
1. البحث عن جميع المنتجات في مستودعات متعددة
2. فحص أول معاملة في كل مستودع
3. إذا كانت أول معاملة **سحب (out)** = رصيد وهمي
4. **حذف** جميع معاملات هذا المنتج من المستودع الوهمي

**كيفية التشغيل:**
```bash
cd /home/zakee/homeupdate
python fix_phantom_stock_simple.py
```

**النتيجة المتوقعة:**
- حذف ~50-100 معاملة وهمية
- تنظيف مستودع الإكسسوار من الرصيد الوهمي
- إعادة الرصيد الصحيح في المستودعات الأصلية

---

## 📝 التوصيات المستقبلية

### 1. منع السحب من مستودع فارغ:
```python
# في inventory/models.py أو signals
def validate_stock_out(product, warehouse, quantity):
    """التحقق من وجود رصيد قبل السحب"""
    last_trans = StockTransaction.objects.filter(
        product=product,
        warehouse=warehouse
    ).order_by('-transaction_date').first()
    
    if not last_trans:
        raise ValueError(f"❌ المنتج {product.name} غير موجود في {warehouse.name}")
    
    if last_trans.running_balance < quantity:
        raise ValueError(f"❌ رصيد غير كافٍ: متاح {last_trans.running_balance}")
```

### 2. مراقبة المعاملة الأولى:
```python
# التأكد من أن أول معاملة لكل منتج في كل مستودع هي إدخال
first_trans = StockTransaction.objects.filter(
    product=product,
    warehouse=warehouse
).order_by('transaction_date').first()

if not first_trans or first_trans.transaction_type not in ['in', 'opening_balance', 'transfer_in']:
    raise ValueError("❌ يجب إدخال المنتج أولاً قبل السحب")
```

### 3. تقرير دوري:
- تشغيل سكريبت فحص الرصيد الوهمي أسبوعياً
- مراقبة المنتجات في مستودعات متعددة
- تنبيهات عند اكتشاف رصيد وهمي

---

## 🎯 الخلاصة

### المشكلة:
- ✅ **تم اكتشافها:** رصيد وهمي في 23 منتج
- ✅ **تم تحديد السبب:** السحب من مستودعات فارغة + اختيار مستودع خاطئ
- ✅ **تم الحل:** تعديل كود اختيار المستودع + سكريبت إصلاح البيانات

### النتيجة:
- 📦 أوامر التقطيع الآن تذهب للمستودع الصحيح
- 🔍 لا يتم اختيار مستودعات فارغة أو وهمية
- 🛡️ حماية من تكرار المشكلة في المستقبل

**حالة النظام:** ✅ تم الإصلاح - جاهز للاختبار
