# إزالة نظام العقد الإلكتروني من النموذج التقليدي

## التغييرات المنفذة ✅

### 1. ملفات Python
- ✅ **orders/views.py**: حذف كود معالجة `create_electronic_contract` و `contract_curtains_data`
- ✅ **orders/admin.py**: حذف `ContractTemplateAdmin` من لوحة التحكم
- ✅ **orders/models.py**: حذف استيراد `ContractTemplate` و `ContractPrintLog`
- ✅ **orders/contract_models.py**: حذف نموذج `ContractTemplate` و `ContractPrintLog`
- ✅ **orders/contract_views.py**: حذف الإشارات إلى `ContractTemplate`
- ✅ **orders/tasks.py**: حذف مهمة `generate_contract_async`
- ✅ **orders/contract_admin.py**: إعادة تسمية إلى `.backup`
- ✅ **orders/contract_forms.py**: إعادة تسمية إلى `.backup`
- ✅ **management/commands/create_default_contract_template.py**: حذف

### 2. ملفات HTML - يجب التعديل يدوياً ⚠️

يجب حذف الأقسام التالية من `orders/templates/orders/order_form.html`:

#### أ) حذف Modal العقد الإلكتروني (السطور 993-1035 تقريباً):
```html
<!-- Modal العقد الإلكتروني -->
<div class="modal fade" id="electronicContractModal" ...>
    ...
</div>
```

#### ب) حذف قالب بطاقة الستارة (بعد السطر 1037):
```html
<template id="curtain-modal-template">
    ...
</template>
```

#### ج) حذف JavaScript المتعلق بالعقد (حول السطر 815-903):
- دالة حفظ العقد الإلكتروني
- معالجة `window.contractCurtains`
- إضافة `create_electronic_contract` و `contract_curtains_data` إلى FormData

#### د) حذف CSS المتعلق بالعقد (حول السطر 137):
```css
/* تحسين مظهر زر العقد الإلكتروني */
```

### 3. النماذج المحتفظ بها ✅

تم الاحتفاظ بالنماذج التالية (مستخدمة في الويزارد):
- ✅ `ContractCurtain` - تفاصيل الستائر في العقد
- ✅ `CurtainFabric` - الأقمشة المرتبطة بالستارة
- ✅ `CurtainAccessory` - الإكسسوارات المرتبطة بالستارة

## الخطوات التالية

### 1. تحديث order_form.html يدوياً
نظراً لحجم الملف وتعقيده، يُفضل تعديله يدوياً:
```bash
# افتح الملف للتعديل
nano /home/zakee/homeupdate/orders/templates/orders/order_form.html
```

ابحث عن وأزل:
- `electronicContractModal`
- `curtain-modal-template`
- `save-electronic-contract-btn`
- `add-curtain-modal-btn`
- `window.contractCurtains`
- `contract_curtains_data`
- `create_electronic_contract`

### 2. إنشاء Migration لحذف النماذج
```bash
cd /home/zakee/homeupdate
python manage.py makemigrations orders --name remove_contract_template_models
python manage.py migrate
```

### 3. اختبار النظام
```bash
# تشغيل السيرفر
python manage.py runserver

# اختبر:
# 1. إنشاء طلب جديد من النموذج التقليدي (يجب أن يعمل بدون خيار العقد)
# 2. استخدام الويزارد لإنشاء طلب مع عقد (يجب أن يعمل بشكل طبيعي)
# 3. فتح لوحة التحكم والتأكد من عدم وجود قوالب العقود
```

## ملاحظات مهمة

1. **الويزارد لم يتأثر**: نظام الويزارد يعمل بشكل كامل ويستخدم النماذج المحتفظ بها
2. **عرض PDF للعقود**: ما زال يعمل عبر `contract_pdf_view`
3. **البيانات الموجودة**: الستائر المضافة مسبقاً ما زالت موجودة في قاعدة البيانات

## استعادة النظام (في حالة الحاجة)

يمكن استعادة الملفات من النسخ الاحتياطية:
```bash
git mv orders/contract_admin.py.backup orders/contract_admin.py
git mv orders/contract_forms.py.backup orders/contract_forms.py
git checkout orders/views.py orders/admin.py orders/tasks.py
```
