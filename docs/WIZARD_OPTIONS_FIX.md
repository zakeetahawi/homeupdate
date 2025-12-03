# ✅ إصلاح مشكلة عدم ظهور الخيارات في الويزارد

## المشكلة
الحقول في الويزارد كانت موجودة لكن الخيارات لا تظهر (شفافة)

## السبب
بعد تبسيط النموذج، تم تغيير اسم الحقل من `display_name_ar` إلى `display_name`، لكن التمبلتس والكود كانت لا تزال تستخدم الاسم القديم.

## الإصلاح

### 1. تحديث التمبلت (step5_contract.html)
**قبل:**
```html
{{ option.display_name_ar }}
```

**بعد:**
```html
{{ option.display_name }}
```

### 2. تحديث contract_models.py
**الدوال المحدثة:**
- `get_installation_type_display()` - تستخدم `option.display_name`
- `get_tailoring_type_display()` - تستخدم `option.display_name`

### 3. الملفات المعدلة
- `orders/templates/orders/wizard/step5_contract.html` - تحديث التمبلت
- `orders/contract_models.py` - تحديث الدوال

## النتيجة ✅
- جميع الخيارات تظهر الآن بشكل صحيح في الويزارد
- 42 خيار نشط عبر 5 أنواع حقول
- النظام مبسط وسهل الاستخدام

## التحقق
```bash
python check_wizard_options.py
```
إجمالي الخيارات النشطة: 42 ✅
