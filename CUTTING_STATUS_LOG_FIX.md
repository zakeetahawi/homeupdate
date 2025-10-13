# إصلاح سجلات حالة التقطيع - Cutting Status Log Fix

## 📋 المشكلة الأصلية

عند إكمال التقطيع، كانت تظهر المشاكل التالية:

### 1. **سجلات مكررة (13 سجل!)**
```
تم تبديل حالة التركيب من قيد الانتظار إلى مكتمل تركيب
 تم تغيير حالة التقطيع
 القيمة السابقة: pending
 القيمة الجديدة: completed
 النظام (تلقائي)
```
- تكرر هذا السجل **13 مرة** (عدد عناصر التقطيع)
- كل مرة يتم إكمال عنصر، يُنشأ سجل جديد

### 2. **عنوان خاطئ**
- العنوان يقول "تم تبديل حالة **التركيب**"
- لكن المحتوى يقول "تم تغيير حالة **التقطيع**"
- القيم هي حالات التقطيع (pending, completed)

### 3. **مستخدم تلقائي**
- يظهر "النظام (تلقائي)" بدلاً من اسم المستخدم الحقيقي
- `changed_by = None`

---

## 🔍 تحليل السبب

### **الحلقة اللانهائية:**

```
1. المستخدم يكمل CuttingOrderItem
   ↓
2. item.save() يطلق signal: update_cutting_order_status
   ↓
3. Signal يحدث cutting_order.status ويحفظه
   ↓
4. cutting_order.save() يطلق signal: update_products_order_status
   ↓
5. Signal ينشئ OrderStatusLog
   ↓
6. يتكرر لكل عنصر (13 مرة!)
```

### **مشكلة العنوان:**

- `change_type='general'` كان يتحول تلقائياً إلى `'status'` في `save()` method
- `get_detailed_description()` يستخدم نوع الطلب (installation) بدلاً من `change_type`

### **مشكلة المستخدم:**

- `changed_by` يحاول الحصول على `assigned_to` أو `completed_by` من `CuttingOrder`
- لكن المستخدم الحقيقي موجود في `CuttingOrderItem.updated_by`

---

## ✅ الإصلاحات المطبقة

### **1. منع تكرار السجلات**

**الملف:** `cutting/signals.py` (السطر 248-277)

**قبل:**
```python
@receiver(post_save, sender=CuttingOrderItem)
def update_cutting_order_status(sender, instance, **kwargs):
    cutting_order = instance.cutting_order
    
    # تحديث الحالة
    if completed_items == total_items:
        cutting_order.status = 'completed'
    
    cutting_order.save()  # ← يحفظ دائماً!
```

**بعد:**
```python
@receiver(post_save, sender=CuttingOrderItem)
def update_cutting_order_status(sender, instance, **kwargs):
    cutting_order = instance.cutting_order
    old_status = cutting_order.status  # ← حفظ الحالة القديمة
    
    # تحديث الحالة
    if completed_items == total_items:
        cutting_order.status = 'completed'
    
    # حفظ فقط إذا تغيرت الحالة
    if old_status != cutting_order.status:  # ← شرط جديد
        cutting_order.save()
```

**النتيجة:** سجل واحد فقط عند الإكمال النهائي ✅

---

### **2. إضافة change_type='cutting' جديد**

**الملف:** `orders/models.py` (السطر 2027-2041)

**قبل:**
```python
CHANGE_TYPE_CHOICES = [
    ('status', 'تغيير حالة'),
    ('manufacturing', 'تحديث تصنيع'),
    ('installation', 'تحديث تركيب'),
    ('general', 'تحديث عام'),
]
```

**بعد:**
```python
CHANGE_TYPE_CHOICES = [
    ('status', 'تغيير حالة'),
    ('manufacturing', 'تحديث تصنيع'),
    ('installation', 'تحديث تركيب'),
    ('cutting', 'تحديث تقطيع'),        # ← جديد
    ('inspection', 'تحديث معاينة'),    # ← جديد
    ('complaint', 'تحديث شكوى'),       # ← جديد
    ('general', 'تحديث عام'),
]
```

---

### **3. تحديث cutting/models.py لاستخدام change_type='cutting'**

**الملف:** `cutting/models.py` (السطر 484-506)

**قبل:**
```python
changed_by = getattr(instance, 'assigned_to', None)

OrderStatusLog.objects.create(
    order=instance.order,
    changed_by=changed_by,  # ← قد يكون None
    change_type='general',  # ← نوع عام
    notes=f'تم إكمال أمر التقطيع #{instance.cutting_code}'
)
```

**بعد:**
```python
# الحصول على المستخدم من آخر عنصر تم تحديثه
changed_by = None
last_updated_item = instance.items.filter(
    updated_by__isnull=False
).order_by('-updated_at').first()

if last_updated_item:
    changed_by = last_updated_item.updated_by  # ← المستخدم الحقيقي

OrderStatusLog.objects.create(
    order=instance.order,
    changed_by=changed_by,
    change_type='cutting',  # ← نوع محدد
    notes=f'تم إكمال أمر التقطيع #{instance.cutting_code}'
)
```

**النتيجة:** يظهر اسم المستخدم الحقيقي ✅

---

### **4. إضافة أيقونات وألوان للأنواع الجديدة**

**الملف:** `orders/models.py`

**الأيقونات:**
```python
base_icons = {
    'cutting': 'fas fa-cut',           # ← مقص
    'inspection': 'fas fa-search',     # ← عدسة مكبرة
    'complaint': 'fas fa-exclamation-triangle',  # ← تحذير
}
```

**الألوان:**
```python
colors = {
    'cutting': 'warning',      # ← أصفر
    'inspection': 'info',      # ← أزرق
    'complaint': 'danger',     # ← أحمر
}
```

---

### **5. إضافة عرض خاص في get_detailed_description**

**الملف:** `orders/models.py` (السطر 2238-2258)

```python
elif self.change_type == 'cutting':
    return self.notes or f'تحديث حالة التقطيع من {self.old_status_pretty} إلى {self.new_status_pretty}'

elif self.change_type == 'inspection':
    return self.notes or f'تحديث حالة المعاينة من {self.old_status_pretty} إلى {self.new_status_pretty}'

elif self.change_type == 'complaint':
    return self.notes or f'تحديث حالة الشكوى من {self.old_status_pretty} إلى {self.new_status_pretty}'
```

**النتيجة:** عنوان صحيح يطابق المحتوى ✅

---

### **6. منع تغيير change_type تلقائياً**

**الملف:** `orders/models.py` (السطر 2262-2269)

**قبل:**
```python
if not self.change_type or self.change_type == 'status':  # ← يغير 'general' إلى 'status'
    if not self.old_status:
        self.change_type = 'creation'
```

**بعد:**
```python
if not self.change_type:  # ← فقط إذا كان فارغاً
    if not self.old_status:
        self.change_type = 'creation'
```

**النتيجة:** `change_type='cutting'` يبقى كما هو ✅

---

## 🎯 النتيجة النهائية

### **قبل الإصلاح:**
```
❌ 13 سجل مكرر
❌ عنوان: "تم تبديل حالة التركيب"
❌ محتوى: "تم تغيير حالة التقطيع"
❌ مستخدم: "النظام (تلقائي)"
```

### **بعد الإصلاح:**
```
✅ سجل واحد فقط
✅ عنوان: "تم إكمال أمر التقطيع #C-16-0177-0001"
✅ نوع: "تحديث تقطيع" (badge أصفر)
✅ مستخدم: "أحمد محمد" (badge أزرق)
✅ أيقونة: مقص (fas fa-cut)
```

---

## 📊 ملخص الملفات المعدلة

| الملف | السطور | التغيير |
|------|--------|---------|
| `cutting/signals.py` | 248-277 | منع تكرار السجلات |
| `cutting/models.py` | 484-506 | استخدام change_type='cutting' + المستخدم الحقيقي |
| `orders/models.py` | 2027-2041 | إضافة أنواع جديدة |
| `orders/models.py` | 2122-2134 | إضافة أيقونات |
| `orders/models.py` | 2198-2213 | إضافة ألوان |
| `orders/models.py` | 2238-2258 | عرض خاص للأنواع الجديدة |
| `orders/models.py` | 2262-2269 | منع تغيير change_type |

---

## 🧪 اختبار الإصلاح

### **خطوات الاختبار:**

1. افتح طلب يحتوي على أمر تقطيع
2. أكمل جميع عناصر التقطيع
3. افتح سجل حالة الطلب
4. تحقق من:
   - ✅ سجل واحد فقط
   - ✅ عنوان صحيح
   - ✅ اسم المستخدم الحقيقي
   - ✅ أيقونة مقص
   - ✅ badge أصفر

---

**تاريخ الإصلاح:** 2025-10-13  
**المطور:** النظام  
**الحالة:** ✅ مكتمل ومختبر

