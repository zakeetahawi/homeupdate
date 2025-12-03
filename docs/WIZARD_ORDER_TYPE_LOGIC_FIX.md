# إصلاح منطق أنواع الطلبات في الويزارد
## Wizard Order Type Logic Fix

**التاريخ:** 2025-11-23  
**المبرمج:** AI Assistant

---

## المشكلة

كان هناك خطأ في نموذج إنشاء الطلب بالويزارد عند اختيار المنتجات (products)، حيث لم يكن المستخدم قادراً على إكمال الويزارد.

### السبب

استخدام `get_object_or_404()` بدون ترتيب في دوال الويزارد المختلفة، مما كان يسبب خطأ `MultipleObjectsReturned` في حال وجود أكثر من مسودة غير مكتملة للمستخدم.

---

## الحل المطبق

### 1. إصلاح دوال الويزارد

تم تحديث جميع الدوال التي تتعامل مع `DraftOrder` لاستخدام:

```python
draft = DraftOrder.objects.filter(
    created_by=request.user,
    is_completed=False
).order_by('-updated_at').first()

if not draft:
    return JsonResponse({
        'success': False,
        'message': 'لم يتم العثور على مسودة نشطة'
    }, status=404)
```

بدلاً من:

```python
draft = get_object_or_404(
    DraftOrder,
    created_by=request.user,
    is_completed=False
)
```

### 2. الدوال المُصلحة

- ✅ `wizard_add_item()` - إضافة عنصر للمسودة
- ✅ `wizard_remove_item()` - حذف عنصر من المسودة
- ✅ `wizard_complete_step_3()` - إكمال الخطوة 3
- ✅ `wizard_finalize()` - تحويل المسودة إلى طلب نهائي
- ✅ `wizard_add_curtain()` - إضافة ستارة للعقد
- ✅ `wizard_edit_curtain()` - تعديل ستارة في العقد
- ✅ `wizard_remove_curtain()` - حذف ستارة من العقد
- ✅ `wizard_upload_contract()` - رفع ملف عقد PDF
- ✅ `wizard_remove_contract_file()` - حذف ملف العقد
- ✅ `wizard_cancel()` - إلغاء الويزارد

---

## منطق أنواع الطلبات

### 1. طلبات التركيب / التسليم / الإكسسوار
**`installation`, `tailoring`, `accessory`**

- ✅ يحتاج **عقد** (الخطوة 5 في الويزارد)
- ✅ يحتاج **ستائر** (إذا كان عقد إلكتروني)
- ✅ يُنشئ **أمر تصنيع** تلقائياً (Manufacturing Order)
- ✅ يُنشئ **أوامر تقطيع** تلقائياً (Cutting Orders)
- ✅ يحتوي على **عناصر فاتورة**

**الكود المسؤول:**
- Signal: `orders/signals.py::create_manufacturing_order_on_order_creation()`
- Signal: `cutting/signals.py::create_cutting_orders_on_order_save()`

### 2. طلبات المنتجات
**`products`**

- ❌ لا يحتاج **عقد**
- ❌ لا يحتاج **ستائر**
- ❌ لا يُنشئ **أمر تصنيع**
- ✅ يُنشئ **أوامر تقطيع** تلقائياً (Cutting Orders)
- ✅ يحتوي على **عناصر فاتورة**

**الكود المسؤول:**
- Signal: `cutting/signals.py::create_cutting_orders_on_order_save()`

**منطق الخطوات في الويزارد:**
```python
# في wizard_step_4_invoice_payment()
needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
next_step = 5 if needs_contract else 6  # تخطي الخطوة 5 (العقد) للمنتجات
```

### 3. طلبات المعاينة
**`inspection`**

- ❌ لا يحتاج **عقد**
- ❌ لا يحتاج **ستائر**
- ❌ لا يُنشئ **أمر تصنيع**
- ❌ لا يُنشئ **أوامر تقطيع**
- ✅ يُنشئ **معاينة** تلقائياً في قسم المعاينات (Inspection)
- ✅ يحتوي على **عناصر فاتورة**

**الكود المسؤول:**
- Signal: `orders/signals.py::create_inspection_on_order_creation()`

**منطق الخطوات في الويزارد:**
```python
# في wizard_step_4_invoice_payment()
needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
next_step = 5 if needs_contract else 6  # تخطي الخطوة 5 (العقد) للمعاينة
```

---

## تدفق البيانات في الويزارد

### الخطوة 1: البيانات الأساسية
- العميل
- البائع
- الفرع
- ملاحظات

### الخطوة 2: نوع الطلب
- اختيار نوع واحد من: `products`, `installation`, `tailoring`, `accessory`, `inspection`
- يتم حفظ النوع في `draft.selected_type`

### الخطوة 3: عناصر الطلب (المنتجات)
- إضافة منتجات من المخزون
- تحديد الكمية والسعر والخصم
- يتم حفظ العناصر في `DraftOrderItem`

### الخطوة 4: الفاتورة والدفع
- أرقام الفاتورة (invoice_number)
- أرقام العقد (contract_number)
- معلومات الدفع
- **القرار:** هل ننتقل للخطوة 5 (العقد) أم الخطوة 6 (المراجعة)؟

### الخطوة 5: العقد (اختيارية)
**فقط لـ:** `installation`, `tailoring`, `accessory`

- إنشاء عقد إلكتروني (إضافة ستائر)
- أو رفع ملف PDF للعقد

### الخطوة 6: المراجعة والتأكيد
- عرض جميع البيانات
- تأكيد الطلب
- **التحويل:** من `DraftOrder` إلى `Order` نهائي

---

## الـ Signals التلقائية

### عند إنشاء Order جديد (from wizard_finalize)

```python
order = Order.objects.create(
    ...
    selected_types=[draft.selected_type] if draft.selected_type else [],
    ...
)
```

#### 1. إذا كان النوع `installation`, `tailoring`, أو `accessory`
- يتم تفعيل Signal: `create_manufacturing_order_on_order_creation()`
- ينشئ `ManufacturingOrder` تلقائياً
- يحدث order status إلى `pending_approval`
- يحدث tracking_status إلى `factory`

#### 2. إذا كان النوع `inspection`
- يتم تفعيل Signal: `create_inspection_on_order_creation()`
- ينشئ `Inspection` تلقائياً
- يحدث order status إلى `pending`
- يحدث tracking_status إلى `processing`

#### 3. إذا كان النوع `products` أو أي نوع آخر (ما عدا `inspection`)
- يتم تفعيل Signal: `create_cutting_orders_on_order_save()`
- ينشئ `CuttingOrder` واحد أو أكثر حسب المستودعات
- يُنشئ `CuttingOrderItem` لكل منتج في الطلب

---

## الفرق بين النظام التقليدي والويزارد

### النظام التقليدي (Traditional Form)
- يستخدم `orders/views.py::order_create()`
- نموذج واحد لكل البيانات
- لا يدعم إنشاء عقود إلكترونية (تم إزالتها)
- نفس الـ Signals تعمل بعد الحفظ

### نظام الويزارد (Wizard Form)
- يستخدم `orders/wizard_views.py`
- نماذج متعددة الخطوات
- يدعم إنشاء عقود إلكترونية مع الستائر
- يحفظ البيانات في `DraftOrder` أثناء العملية
- عند الانتهاء، يُحول إلى `Order` نهائي
- نفس الـ Signals تعمل بعد إنشاء Order

---

## الملفات المُعدّلة

### `/home/zakee/homeupdate/orders/wizard_views.py`

**التغييرات:**
- تحديث 10 دوال لاستخدام `.order_by('-updated_at').first()` بدلاً من `get_object_or_404()`
- إضافة معالجة صحيحة لحالة عدم وجود مسودة نشطة

**الأسطر المُعدلة:**
- Line 279-283: `wizard_add_item()`
- Line 334-338: `wizard_remove_item()`
- Line 368-372: `wizard_complete_step_3()`
- Line 563-567: `wizard_finalize()`
- Line 729-733: `wizard_add_curtain()`
- Line 940-944: `wizard_edit_curtain()`
- Line 1184-1188: `wizard_remove_curtain()`
- Line 1221-1225: `wizard_upload_contract()`
- Line 1271-1275: `wizard_remove_contract_file()`
- Line 696-700: `wizard_cancel()`

---

## الاختبار

### طريقة الاختبار

1. **إنشاء طلب منتجات:**
   - ابدأ الويزارد
   - اختر "منتجات" في الخطوة 2
   - أضف منتجات في الخطوة 3
   - أكمل الخطوة 4 (يجب الانتقال مباشرة للخطوة 6)
   - راجع وأكد الطلب
   - تحقق من إنشاء Cutting Orders تلقائياً

2. **إنشاء طلب تركيب:**
   - ابدأ الويزارد
   - اختر "تركيب" في الخطوة 2
   - أضف منتجات في الخطوة 3
   - أكمل الخطوة 4 (يجب الانتقال للخطوة 5)
   - أنشئ عقد إلكتروني أو ارفع PDF في الخطوة 5
   - راجع وأكد الطلب
   - تحقق من إنشاء Manufacturing Order و Cutting Orders

3. **إنشاء طلب معاينة:**
   - ابدأ الويزارد
   - اختر "معاينة" في الخطوة 2
   - أضف منتجات (اختياري) في الخطوة 3
   - أكمل الخطوة 4 (يجب الانتقال مباشرة للخطوة 6)
   - راجع وأكد الطلب
   - تحقق من إنشاء Inspection تلقائياً
   - لا يجب إنشاء Cutting Orders

---

## ملاحظات مهمة

### 1. التعامل مع المسودات المتعددة
- الآن يتم اختيار المسودة الأحدث دائماً (`order_by('-updated_at').first()`)
- هذا يحل مشكلة `MultipleObjectsReturned`
- يمكن للمستخدم رؤية جميع المسودات من صفحة `/orders/wizard/drafts/`

### 2. selected_type vs selected_types
- **DraftOrder:** يستخدم `selected_type` (CharField) - نوع واحد فقط
- **Order:** يستخدم `selected_types` (JSONField) - قائمة من الأنواع
- عند التحويل: `selected_types=[draft.selected_type]`

### 3. الـ Signals تعمل تلقائياً
- لا تحتاج إلى استدعاء يدوي
- تعمل مباشرة بعد `Order.objects.create()`
- Django signals تُطلق بعد `post_save`

### 4. العقود الإلكترونية
- فقط في نظام الويزارد
- لا تتوفر في النظام التقليدي (تم إزالتها)
- تُخزن في `ContractCurtain` model
- تُنقل من `draft_order` إلى `order` عند التأكيد

---

## الخلاصة

تم إصلاح جميع المشاكل المتعلقة بـ:
- ✅ إضافة المنتجات في الويزارد
- ✅ منطق أنواع الطلبات المختلفة
- ✅ إنشاء Manufacturing Orders تلقائياً
- ✅ إنشاء Cutting Orders تلقائياً
- ✅ إنشاء Inspections تلقائياً
- ✅ التعامل مع المسودات المتعددة

النظام الآن يعمل بنفس منطق النظام التقليدي مع ميزات إضافية للعقود الإلكترونية.

---

## مرجع سريع

### أنواع الطلبات ومتطلباتها

| النوع | عقد | ستائر | Manufacturing Order | Cutting Orders | Inspection |
|-------|-----|-------|---------------------|----------------|------------|
| `installation` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `tailoring` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `accessory` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `products` | ❌ | ❌ | ❌ | ✅ | ❌ |
| `inspection` | ❌ | ❌ | ❌ | ❌ | ✅ |

### خطوات الويزارد

| الخطوة | العنوان | مطلوبة | تُخطى لـ |
|--------|---------|--------|----------|
| 1 | البيانات الأساسية | ✅ | - |
| 2 | نوع الطلب | ✅ | - |
| 3 | عناصر الطلب | ✅ | - |
| 4 | الفاتورة والدفع | ✅ | - |
| 5 | العقد | ⚠️ | `products`, `inspection` |
| 6 | المراجعة | ✅ | - |

---

**تم الانتهاء من الإصلاح بنجاح ✅**
