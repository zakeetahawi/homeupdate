# تحديث الويزارد ليكون 5 أو 6 خطوات حسب نوع الطلب
## Dynamic Wizard Steps Update

**التاريخ:** 2025-11-23  
**الوقت:** 12:46

---

## التغييرات

### المشكلة
- عند اختيار "معاينة" أو "منتجات"، كان الويزارد يتخطى الخطوة 5 لكن يبقى يعرض 6 خطوات
- الخطوة 6 لا تعمل بشكل صحيح للأنواع التي لا تحتاج عقد

### الحل
تحديث الويزارد ليكون ديناميكياً:

#### للأنواع **التي تحتاج عقد** (تركيب، تسليم، إكسسوار):
```
الخطوة 1: البيانات الأساسية
الخطوة 2: نوع الطلب
الخطوة 3: عناصر الطلب
الخطوة 4: الفاتورة والدفع
الخطوة 5: العقد ← (موجودة)
الخطوة 6: المراجعة والتأكيد
───────────────────────
المجموع: 6 خطوات
```

#### للأنواع **التي لا تحتاج عقد** (منتجات، معاينة):
```
الخطوة 1: البيانات الأساسية
الخطوة 2: نوع الطلب
الخطوة 3: عناصر الطلب
الخطوة 4: الفاتورة والدفع
الخطوة 5: المراجعة والتأكيد ← (تخطي العقد)
───────────────────────
المجموع: 5 خطوات
```

---

## التحديثات التقنية

### 1. إضافة دوال مساعدة

```python
def get_total_steps(draft):
    """حساب عدد الخطوات الفعلي بناءً على نوع الطلب"""
    if draft and draft.selected_type:
        needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
        return 6 if needs_contract else 5
    return 6  # افتراضياً
```

### 2. تحديث دالة wizard_step()

```python
elif step == 5:
    # الخطوة 5 يمكن أن تكون العقد أو المراجعة حسب نوع الطلب
    needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
    if needs_contract:
        return wizard_step_5_contract(request, draft)
    else:
        return wizard_step_6_review(request, draft)  # المراجعة تصبح الخطوة 5

elif step == 6:
    # الخطوة 6 موجودة فقط للأنواع التي تحتاج عقد
    needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
    if needs_contract:
        return wizard_step_6_review(request, draft)
    else:
        return redirect('orders:wizard_step', step=5)  # توجيه للخطوة 5
```

### 3. تحديث wizard_step_4_invoice_payment()

```python
# تحديد الخطوة التالية بناءً على نوع الطلب
needs_contract = draft.selected_type in ['installation', 'tailoring', 'accessory']
next_step = 5  # دائماً الخطوة 5 (العقد أو المراجعة)
draft.current_step = next_step
```

### 4. تحديث جميع context في كل خطوة

```python
total_steps = get_total_steps(draft)
context = {
    ...
    'total_steps': total_steps,
    'progress_percentage': round((current_step / total_steps) * 100, 2),
}
```

---

## التأثير

### الإيجابيات
✅ الويزارد يتكيف تلقائياً مع نوع الطلب  
✅ تجربة مستخدم أفضل (5 خطوات للأنواع البسيطة)  
✅ شريط التقدم يعمل بشكل صحيح  
✅ لا توجد خطوات زائدة أو غير ضرورية  

### الاختبار
- [x] اختيار "منتجات" → 5 خطوات
- [x] اختيار "معاينة" → 5 خطوات  
- [x] اختيار "تركيب" → 6 خطوات
- [x] اختيار "تسليم" → 6 خطوات
- [x] اختيار "إكسسوار" → 6 خطوات

---

## الملفات المُعدّلة

### `/home/zakee/homeupdate/orders/wizard_views.py`

**الدوال الجديدة:**
- `get_total_steps(draft)` - Line ~30
- `get_step_number(draft, logical_step)` - Line ~39

**الدوال المُحدّثة:**
- `wizard_step()` - Line ~155
- `wizard_step_1_basic_info()` - Line ~200
- `wizard_step_2_order_type()` - Line ~243
- `wizard_step_3_order_items()` - Line ~286
- `wizard_step_4_invoice_payment()` - Line ~438
- `wizard_step_5_contract()` - Line ~541
- `wizard_step_6_review()` - Line ~598

**عدد الأسطر المُعدّلة:** ~60 سطر

---

## الخلاصة

الويزارد الآن:
- **ذكي** - يتكيف مع نوع الطلب
- **مرن** - 5 أو 6 خطوات حسب الحاجة
- **دقيق** - شريط التقدم يعرض النسبة الصحيحة
- **واضح** - المستخدم يعرف عدد الخطوات المتبقية

---

**تم التحديث بنجاح ✅**
