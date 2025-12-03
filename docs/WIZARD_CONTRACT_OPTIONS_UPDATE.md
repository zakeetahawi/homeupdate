# تحديث خيارات العقد في الويزارد
# Wizard Contract Options Update

## التاريخ / Date
2025-11-20

## الملخص / Summary
تم تحديث الخطوة الخامسة من ويزارد إنشاء الطلب لتوفير خيارين للعقد:
1. **عقد إلكتروني**: إضافة تفاصيل الستائر والأقمشة
2. **رفع ملف PDF**: رفع ملف عقد جاهز بصيغة PDF (تلقائياً عند الاختيار)

The fifth step of the order creation wizard has been updated to provide two contract options:
1. **Electronic Contract**: Add curtain and fabric details
2. **PDF Upload**: Upload a ready-made PDF contract file (automatically upon selection)

## التحسينات الأخيرة / Latest Improvements

### 1. رفع ملف PDF تلقائياً
- عند اختيار ملف PDF، يتم رفعه تلقائياً دون الحاجة للضغط على زر "رفع"
- يظهر مؤشر تحميل أثناء رفع الملف
- عند نجاح الرفع، يتم إعادة تحميل الصفحة لعرض الملف

When selecting a PDF file, it uploads automatically without needing to click "Upload"
Shows loading indicator during upload
Page reloads upon successful upload to display the file

### 2. تحسين زر "التالي"
- إزالة كلمة "تخطي العقد" من النص
- يظهر فقط "التالي"
- يتحقق من وجود عقد قبل الانتقال

Removed "Skip Contract" text
Shows only "Next"
Checks for contract before proceeding

### 3. منطق التحقق المحسّن
- الخطوة 5 اختيارية تماماً
- إذا لم يتم إضافة عقد، يتم سؤال المستخدم للتأكيد
- إذا تم إضافة عقد (إلكتروني أو PDF)، يتم الانتقال مباشرة

Step 5 is completely optional
If no contract is added, user is asked to confirm
If contract is added (electronic or PDF), proceeds directly

### 4. نموذج إضافة ستارة تدريجي متطور
تم تحويل نموذج إضافة الستارة إلى wizard متعدد المراحل:

**المرحلة 1: المعلومات الأساسية**
- اسم الغرفة (مطلوب)
- العرض بالمتر (مطلوب)
- الارتفاع بالمتر (مطلوب)
- تم إزالة عرض المساحة المربعة

**المرحلة 2: إضافة الأقمشة**
- نوع القماش: خفيف، ثقيل، بلاك أوت، إضافي
- اسم القماش (اختياري)
- الكمية بالمتر
- عدد القطع
- طريقة التفصيل: حلقات، شريط، كبس، كسرة مزدوجة، كسرة ثلاثية، كسرة قلم، عراوي، عروة علوية
- إمكانية إضافة أقمشة متعددة
- عرض الأقمشة المضافة مع إمكانية الحذف

**المرحلة 3: الإكسسوارات**
- خيار: مع إكسسوار / بدون إكسسوار
- إذا تم اختيار "مع إكسسوار"، تظهر حقول الإكسسوار:
  - اسم الإكسسوار (قائمة منسدلة): كورنيش، عصا، براكيت، حلقات، كرات، خطاف، مشبك، شريط لاصق، أخرى
  - الكمية
  - ملاحظات
  - إمكانية إضافة إكسسوارات متعددة

Multi-stage curtain addition wizard:
- Stage 1: Basic info (room name, width, height)
- Stage 2: Fabrics with types, quantities, pieces, and tailoring methods
- Stage 3: Accessories with customizable options

## التغييرات / Changes

### 1. نموذج البيانات / Database Models
**File**: `orders/wizard_models.py`

تمت إضافة حقلين جديدين لـ `DraftOrder`:
- `contract_type`: نوع العقد (electronic أو pdf)
- `contract_file`: ملف العقد المرفوع

Added two new fields to `DraftOrder`:
- `contract_type`: Contract type (electronic or pdf)
- `contract_file`: Uploaded contract file

### 2. العروض / Views
**File**: `orders/wizard_views.py`

تمت إضافة أربع دوال جديدة:
1. `wizard_add_curtain()`: إضافة ستارة للعقد الإلكتروني
2. `wizard_remove_curtain()`: حذف ستارة من العقد الإلكتروني
3. `wizard_upload_contract()`: رفع ملف PDF للعقد
4. `wizard_remove_contract_file()`: حذف ملف العقد المرفوع

Added four new view functions:
1. `wizard_add_curtain()`: Add curtain to electronic contract
2. `wizard_remove_curtain()`: Remove curtain from electronic contract
3. `wizard_upload_contract()`: Upload PDF contract file
4. `wizard_remove_contract_file()`: Remove uploaded contract file

تم تحديث `wizard_finalize()` لنقل ملف العقد إلى الطلب النهائي:
```python
# نقل ملف العقد إذا وجد
if draft.contract_file:
    order.contract_file = draft.contract_file
    order.save(update_fields=['contract_file'])
```

### 3. الروابط / URLs
**File**: `orders/urls.py`

تمت إضافة المسارات الجديدة:
```python
path('wizard/add-curtain/', wizard_views.wizard_add_curtain, name='wizard_add_curtain'),
path('wizard/remove-curtain/<int:curtain_id>/', wizard_views.wizard_remove_curtain, name='wizard_remove_curtain'),
path('wizard/upload-contract/', wizard_views.wizard_upload_contract, name='wizard_upload_contract'),
path('wizard/remove-contract-file/', wizard_views.wizard_remove_contract_file, name='wizard_remove_contract_file'),
```

### 4. القالب / Template
**File**: `orders/templates/orders/wizard/step5_contract.html`

التحديثات الرئيسية:
1. إضافة اختيار نوع العقد (راديو buttons)
2. قسم العقد الإلكتروني (يظهر عند اختيار electronic)
3. قسم رفع PDF (يظهر عند اختيار pdf)
4. دوال JavaScript للتبديل بين الخيارين
5. دوال لرفع وحذف ملف PDF

Main updates:
1. Added contract type selection (radio buttons)
2. Electronic contract section (shown when electronic is selected)
3. PDF upload section (shown when pdf is selected)
4. JavaScript functions to toggle between options
5. Functions to upload and delete PDF file

### 5. الترحيل / Migration
**File**: `orders/migrations/0041_draftorder_contract_file_draftorder_contract_type.py`

تم إنشاء وتطبيق ترحيل قاعدة البيانات لإضافة الحقول الجديدة.
Database migration created and applied to add the new fields.

## الاستخدام / Usage

### للمستخدم / For Users
1. في الخطوة الخامسة من الويزارد، اختر أحد الخيارات:
   - **عقد إلكتروني**: انقر "إضافة ستارة جديدة" وأدخل التفاصيل
   - **رفع PDF**: اختر ملف PDF واضغط "رفع الملف"

2. يمكن التبديل بين الخيارين في أي وقت
3. عند اختيار خيار جديد، سيتم إخفاء الخيار الآخر

In the fifth step of the wizard, choose one option:
- **Electronic Contract**: Click "Add New Curtain" and enter details
- **PDF Upload**: Choose a PDF file and click "Upload File"

You can switch between options at any time.

### للمطورين / For Developers

#### إضافة ستارة (AJAX)
```javascript
fetch('/orders/wizard/add-curtain/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({
        room_name: 'غرفة النوم',
        width: 3.5,
        height: 2.8
    })
})
```

#### رفع ملف PDF (AJAX)
```javascript
const formData = new FormData();
formData.append('contract_file', fileInput.files[0]);

fetch('/orders/wizard/upload-contract/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrfToken
    },
    body: formData
})
```

## التحقق / Testing

1. ✅ إنشاء طلب جديد عبر الويزارد
2. ✅ الوصول للخطوة 5 (العقد)
3. ✅ اختيار "عقد إلكتروني" وإضافة ستارة
4. ✅ حذف الستارة
5. ✅ التبديل إلى "رفع PDF"
6. ✅ رفع ملف PDF
7. ✅ حذف ملف PDF
8. ✅ إكمال الطلب والتحقق من نقل ملف العقد

## الملاحظات / Notes

- الخطوة 5 اختيارية - يمكن تخطيها
- يمكن اختيار خيار واحد فقط في كل مرة
- عند اختيار "عقد إلكتروني"، يتم تحديث `contract_type` إلى `electronic`
- عند رفع PDF، يتم تحديث `contract_type` إلى `pdf`
- ملف العقد يُنقل تلقائياً إلى الطلب النهائي عند الإكمال

Step 5 is optional - can be skipped
Only one option can be selected at a time
When choosing "Electronic Contract", `contract_type` is set to `electronic`
When uploading PDF, `contract_type` is set to `pdf`
Contract file is automatically transferred to final order upon completion

## الأخطاء التي تم إصلاحها / Fixed Errors

### خطأ 404 على `/orders/wizard/add-curtain/`
**السبب**: المسار غير موجود في URLs
**الحل**: إضافة المسار والدالة المطابقة في wizard_views.py

### "حدث خطأ أثناء حفظ الستارة"
**السبب**: عدم وجود endpoint للحفظ
**الحل**: إضافة `wizard_add_curtain()` view function

### SyntaxError: Unexpected token '<'
**السبب**: الصفحة تُرجع HTML بدلاً من JSON عند وجود خطأ 404
**الحل**: إصلاح المسارات وإضافة معالجة الأخطاء الصحيحة

## الملفات المتأثرة / Affected Files

1. `orders/wizard_models.py` - إضافة حقول جديدة
2. `orders/wizard_views.py` - إضافة دوال جديدة
3. `orders/urls.py` - إضافة مسارات جديدة
4. `orders/templates/orders/wizard/step5_contract.html` - تحديث القالب
5. `orders/migrations/0041_draftorder_contract_file_draftorder_contract_type.py` - ترحيل جديد

## المتطلبات / Requirements

- Django 5.2.6+
- Bootstrap 5 (للواجهة)
- Font Awesome (للأيقونات)

## الصيانة المستقبلية / Future Maintenance

### احتمالات التحسين / Potential Improvements
1. إضافة معاينة للملف المرفوع قبل الرفع
2. التحقق من حجم الملف (حد أقصى مثلاً 10MB)
3. إضافة إمكانية رفع صور العقد الممسوحة ضوئياً
4. دعم تنسيقات ملفات إضافية (DOC, DOCX)
5. إضافة توقيع إلكتروني للعقود

### ملاحظات للتطوير / Development Notes
- تأكد من تحديث حقل `contract_type` عند أي تغيير في العقد
- تعامل مع حذف الملفات بشكل صحيح عند حذف المسودة
- فكّر في إضافة سجل تدقيق (audit log) لتتبع التغييرات على العقود
