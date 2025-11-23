# تحديث تعديل الستائر في الويزارد
## Wizard Curtain Edit Feature Update

تاريخ التحديث: 2025-11-22

## المشاكل التي تم حلها

### 1. خطأ NoReverseMatch في صفحة تفاصيل الطلب
**المشكلة:**
```
NoReverseMatch at /orders/order/1-0001-0014/
Reverse for 'contract_curtains_manage' not found
```

**الحل:**
- تم حذف الزر "إدارة ستائر العقد" من صفحة تفاصيل الطلب لأن النظام القديم تم حذفه
- الآن يتم إدارة الستائر من خلال الويزارد فقط

**الملف المعدل:**
- `orders/templates/orders/order_detail.html` (السطر 18-20)

---

### 2. عدم القدرة على تعديل الستائر في الويزارد
**المشكلة:**
- كان يوجد زر حذف فقط
- لا يمكن تعديل الستارة بعد إضافتها
- لا يمكن تعديل الأقمشة أو الإكسسوارات

**الحل:**
تم إضافة وظيفة تعديل كاملة للستائر تشمل:

#### أ. زر التعديل في واجهة الستائر
```html
<button type="button" class="btn btn-sm btn-primary me-2" onclick="editCurtain({{ curtain.id }})">
    <i class="fas fa-edit"></i> تعديل
</button>
```

#### ب. دالة JavaScript للتعديل
```javascript
function editCurtain(curtainId) {
    // جلب بيانات الستارة من السيرفر
    // تعبئة النموذج بالبيانات
    // فتح المودال في وضع التعديل
}
```

#### ج. View جديد للتعديل
```python
@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def wizard_edit_curtain(request, curtain_id):
    """
    تعديل ستارة موجودة في العقد الإلكتروني
    GET: جلب بيانات الستارة
    POST: حفظ التعديلات
    """
```

#### د. URL جديد
```python
path('wizard/edit-curtain/<int:curtain_id>/', wizard_views.wizard_edit_curtain, name='wizard_edit_curtain'),
```

---

### 3. تحديث clean() method لدعم draft_order_item

**المشكلة:**
- كان يتحقق فقط من `order_item`
- لم يكن يدعم التحقق من `draft_order_item`

**الحل:**
تم تحديث `CurtainFabric.clean()` للتحقق من كلا النوعين:

```python
def clean(self):
    """التحقق من صحة البيانات"""
    from django.core.exceptions import ValidationError
    errors = {}
    
    # التحقق من عدم تجاوز الكمية المتاحة للطلبات النهائية
    if self.order_item and self.meters:
        used_total = CurtainFabric.objects.filter(
            order_item=self.order_item
        ).exclude(pk=self.pk).aggregate(
            total=models.Sum('meters')
        )['total'] or 0
        
        available = self.order_item.quantity - used_total
        
        if self.meters > available:
            errors['meters'] = f'الكمية المطلوبة ({self.meters}م) أكبر من المتاح ({available}م من {self.order_item.quantity}م)'
    
    # التحقق من عدم تجاوز الكمية المتاحة للمسودات
    if self.draft_order_item and self.meters:
        used_total = CurtainFabric.objects.filter(
            draft_order_item=self.draft_order_item
        ).exclude(pk=self.pk).aggregate(
            total=models.Sum('meters')
        )['total'] or 0
        
        available = self.draft_order_item.quantity - used_total
        
        if self.meters > available:
            errors['meters'] = f'الكمية المطلوبة ({self.meters}م) أكبر من المتاح ({available}م من {self.draft_order_item.quantity}م)'
    
    if errors:
        raise ValidationError(errors)
```

**الملف المعدل:**
- `orders/contract_models.py` (السطور 696-732)

---

## الملفات المعدلة

1. **orders/templates/orders/order_detail.html**
   - حذف زر "إدارة ستائر العقد"

2. **orders/templates/orders/wizard/step5_contract.html**
   - إضافة زر "تعديل" بجانب زر "حذف"
   - إضافة دالة `editCurtain()` في JavaScript
   - تحديث دالة `saveCurtainComplete()` لدعم وضع التعديل
   - إضافة متغير `editingCurtainId` لتتبع حالة التعديل
   - تحديث دالة `resetCurtainModal()` لإعادة تعيين حالة التعديل

3. **orders/wizard_views.py**
   - إضافة دالة `wizard_edit_curtain()` جديدة
   - تدعم GET لجلب البيانات
   - تدعم POST لحفظ التعديلات

4. **orders/urls.py**
   - إضافة URL جديد للتعديل: `wizard/edit-curtain/<int:curtain_id>/`

5. **orders/contract_models.py**
   - تحديث `CurtainFabric.clean()` للتحقق من `draft_order_item`
   - تحديث `CurtainFabric.__str__()` لعرض اسم القماش من المسودة

---

## كيفية الاستخدام

### تعديل ستارة موجودة:
1. اذهب إلى الخطوة 5 في الويزارد (العقد)
2. اضغط على زر "تعديل" بجانب الستارة المراد تعديلها
3. ستفتح نافذة التعديل مع البيانات المحملة
4. عدّل ما تريد (المعلومات الأساسية، الأقمشة، الإكسسوارات)
5. اضغط "حفظ الستارة"

### إضافة أقمشة وإكسسوارات:
- في وضع التعديل، يمكنك:
  - إضافة أقمشة جديدة
  - حذف أقمشة موجودة
  - تعديل كميات الأقمشة
  - إضافة إكسسوارات جديدة
  - حذف إكسسوارات موجودة

---

## التحقق من الأخطاء

تم اختبار النظام:
```bash
python manage.py check
# System check identified no issues (0 silenced).
```

---

## ملاحظات مهمة

1. **التحقق من الكميات:**
   - يتم التحقق تلقائياً من عدم تجاوز الكميات المتاحة
   - يتم عرض رسالة خطأ واضحة إذا تجاوزت الكمية

2. **حذف البيانات القديمة:**
   - عند التعديل، يتم حذف الأقمشة والإكسسوارات القديمة
   - ثم يتم إضافة البيانات الجديدة
   - هذا يضمن عدم وجود بيانات مكررة

3. **دعم المسودات والطلبات النهائية:**
   - النظام يدعم كلاً من `draft_order_item` و `order_item`
   - التحقق من الكميات يعمل لكلا النوعين

---

## الخطوات التالية (اختياري)

إذا أردت تحسينات إضافية:
1. إضافة تأكيد قبل التعديل
2. إضافة سجل التغييرات (Audit Log)
3. إضافة إمكانية نسخ الستارة
4. إضافة معاينة قبل الحفظ

---

تم الانتهاء بنجاح! ✅
