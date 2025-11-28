# إصلاحات إضافية - نظام ويزارد إنشاء الطلبات

**التاريخ:** 2025-11-28  
**الجلسة:** 2

---

## 🔧 الإصلاح 1: نظام رفع صور الفاتورة (الخطوة 4)

### المشكلة:
1. ✅ أول صورة للفاتورة **إجبارية** ولا يمكن حذفها
2. ❌ الحقول الإضافية تُفتح تلقائياً في وضع التعديل ولا يمكن حذفها
3. ❌ الحقل الفارغ المفتوح يمنع من إكمال النموذج كونه مطلوب

### الحل المطبّق:

#### أ) في Template (step4_invoice_payment.html):

**قبل:**
```html
<div id="invoice-images-container">
    <div class="invoice-image-input mb-2">
        {{ form.invoice_image }}  <!-- دائماً مطلوب -->
    </div>
</div>
```

**بعد:**
```html
<div id="invoice-images-container">
    {% if not draft.invoice_image and not draft.invoice_images_new.exists %}
    <!-- الحقل الأول إجباري فقط إذا لم توجد صور محفوظة -->
    <div class="invoice-image-input mb-2">
        {{ form.invoice_image }}
    </div>
    {% else %}
    <!-- إذا كانت هناك صور محفوظة، الحقل اختياري مع زر حذف -->
    <div class="invoice-image-input mb-2 d-flex gap-2">
        <input type="file" name="invoice_image" class="form-control" accept="image/*">
        <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    </div>
    {% endif %}
</div>
```

#### ب) في Form (wizard_forms.py):

**قبل:**
```python
if self.draft_order and self.draft_order.selected_type != 'inspection':
    self.fields['invoice_image'].required = True
```

**بعد:**
```python
if self.draft_order and self.draft_order.selected_type != 'inspection':
    has_saved_images = (
        (self.draft_order.invoice_image) or 
        (self.draft_order.invoice_images_new.exists())
    )
    
    if not has_saved_images:
        # لا توجد صور محفوظة - الحقل إجباري
        self.fields['invoice_image'].required = True
        self.fields['invoice_image'].widget.attrs['required'] = 'required'
    else:
        # توجد صور محفوظة - الحقل اختياري
        self.fields['invoice_image'].required = False
        if 'required' in self.fields['invoice_image'].widget.attrs:
            del self.fields['invoice_image'].widget.attrs['required']
```

#### ج) تحديث التحقق من الصحة:

**قبل:**
```python
def clean_invoice_image(self):
    invoice_image = self.cleaned_data.get('invoice_image')
    
    if self.draft_order and self.draft_order.selected_type != 'inspection':
        if not invoice_image and not (self.draft_order and self.draft_order.invoice_image):
            raise ValidationError('يجب إرفاق صورة الفاتورة')
```

**بعد:**
```python
def clean_invoice_image(self):
    invoice_image = self.cleaned_data.get('invoice_image')
    
    if self.draft_order and self.draft_order.selected_type != 'inspection':
        has_saved_images = (
            (self.draft_order.invoice_image) or 
            (self.draft_order.invoice_images_new.exists())
        )
        
        # إذا لم توجد صور محفوظة ولم يتم رفع صورة جديدة
        if not invoice_image and not has_saved_images:
            raise ValidationError('يجب إرفاق صورة الفاتورة على الأقل')
```

### النتيجة:
- ✅ **الحقل الأول إجباري** عند إنشاء طلب جديد (لا توجد صور)
- ✅ **الحقل الأول اختياري مع زر حذف** عند التعديل (توجد صور محفوظة)
- ✅ **جميع الحقول الإضافية** لها زر حذف دائماً
- ✅ **لا يُفتح حقل فارغ تلقائياً** في وضع التعديل

---

## 🔧 الإصلاح 2: عرض الكميات العشرية بشكل صحيح (الخطوة 5)

### المشكلة:
عند إضافة كميات عشرية في الفاتورة (مثل 22.5 أو 7.5 متر)، كان النظام يعرض فقط الجزء الصحيح (22 أو 7).

### السبب:
Django template لا يحافظ على الأرقام العشرية عند تحويلها إلى string في JavaScript.

**مثال:**
```django-html
parseFloat('{{ item.quantity }}')
<!-- إذا كانت quantity = 22.5 قد تصبح "22" أو "22.500000" -->
```

### الحل المطبّق:

#### 1. في fabricUsageTracker:

**قبل:**
```javascript
fabricUsageTracker['{{ item.id }}'] = {
    total: parseFloat('{{ item.quantity }}'),
    used: 0,
    name: '{{ item.product.name|escapejs }}'
};
```

**بعد:**
```javascript
fabricUsageTracker['{{ item.id }}'] = {
    total: parseFloat('{{ item.quantity|stringformat:"f" }}'),
    used: 0,
    name: '{{ item.product.name|escapejs }}'
};
```

#### 2. في data-available attributes:

**قبل:**
```html
<option value="{{ item.id }}" data-available="{{ item.quantity }}">
```

**بعد:**
```html
<option value="{{ item.id }}" data-available="{{ item.quantity|stringformat:'f' }}">
```

#### 3. في العرض للمستخدم:

```html
{{ item.quantity|floatformat:"-3" }}
<!-- يعرض حتى 3 خانات عشرية ويزيل الأصفار الزائدة -->
<!-- 22.5 → "22.5" -->
<!-- 22.50 → "22.5" -->
<!-- 22.0 → "22" -->
```

### النتيجة:
- ✅ عرض الكميات العشرية بشكل صحيح (22.5 بدلاً من 22)
- ✅ حساب دقيق للكميات المتاحة
- ✅ عمل صحيح مع الأرقام الصحيحة والعشرية

---

## 📊 الملفات المعدّلة في هذه الجلسة:

1. **orders/templates/orders/wizard/step4_invoice_payment.html**
   - تحديث منطق عرض حقل الصورة الأول
   - إضافة شرط للتحقق من وجود صور محفوظة
   - إضافة زر حذف للحقل الأول عند وجود صور

2. **orders/wizard_forms.py** (Step4InvoicePaymentForm)
   - تحديث `__init__` لجعل الحقل إجباري/اختياري حسب الحالة
   - تحديث `clean_invoice_image` للتحقق من الصور المحفوظة والجديدة

3. **orders/templates/orders/wizard/step5_contract.html**
   - إضافة `stringformat:'f'` للكميات في JavaScript
   - إضافة `stringformat:'f'` لـ data-available
   - الحفاظ على `floatformat:"-3"` للعرض

---

## ✅ الاختبارات المطلوبة:

### اختبار 1: صور الفاتورة - طلب جديد
```
1. إنشاء طلب جديد
2. الوصول للخطوة 4 (الفاتورة)
3. التحقق: الحقل الأول مطلوب (لا يوجد زر حذف)
4. رفع صورة
5. النقر على "إضافة صورة إضافية"
6. التحقق: الحقل الجديد له زر حذف ✓
7. حذف الحقل الإضافي بنجاح ✓
```

### اختبار 2: صور الفاتورة - وضع التعديل
```
1. فتح طلب موجود به صورة محفوظة
2. الوصول للخطوة 4
3. التحقق: الحقل الأول له زر حذف ✓
4. التحقق: يمكن حذف الحقل الفارغ ✓
5. إضافة حقول إضافية وحذفها ✓
6. الحفظ بدون رفع صورة جديدة (يعتمد على المحفوظة) ✓
```

### اختبار 3: الكميات العشرية
```
1. إضافة قماش بكمية 22.5 متر في الفاتورة
2. إضافة قماش آخر بكمية 7.5 متر
3. الانتقال للخطوة 5 (العقد)
4. التحقق: يعرض "متوفر: 22.5 متر" و "متوفر: 7.5 متر" ✓
5. إضافة ستارة واختيار القماش الأول
6. التحقق: "المتبقي للاختيار: 22.5 متر" ✓
7. إضافة 10.5 متر
8. التحقق: "المتبقي للاختيار: 12 متر" ✓
```

---

## 📝 ملاحظات إضافية:

### استخدام stringformat في Django:
- `stringformat:'f'` - تنسيق كـ float (مثل: 22.500000)
- `floatformat:"-3"` - عرض حتى 3 خانات عشرية وإزالة الأصفار (مثل: 22.5)

### لماذا نستخدم الاثنين؟
- `stringformat:'f'` - للبيانات في JavaScript (دقة كاملة)
- `floatformat:"-3"` - للعرض للمستخدم (شكل جميل)

---

**تم الإصلاح بنجاح!** ✅
