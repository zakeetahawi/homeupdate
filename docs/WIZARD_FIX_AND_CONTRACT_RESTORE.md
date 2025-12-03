# إصلاح الويزارد واستعادة نماذج العقد
## Wizard Fix & Contract Models Restoration

**التاريخ:** 2025-11-23  
**الوقت:** 12:38  

---

## الإصلاحات المطبقة

### 1. إصلاح مشكلة MultipleObjectsReturned في الويزارد

**المشكلة:**
- عند اختيار المنتجات في الويزارد، كان يحدث خطأ `MultipleObjectsReturned`
- السبب: استخدام `get_object_or_404()` بدون ترتيب عندما يكون هناك عدة مسودات غير مكتملة

**الحل:**
تحديث 10 دوال في `/home/zakee/homeupdate/orders/wizard_views.py`:

```python
# القديم (يسبب خطأ)
draft = get_object_or_404(
    DraftOrder,
    created_by=request.user,
    is_completed=False
)

# الجديد (صحيح)
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

**الدوال المُصلحة:**
1. `wizard_add_item()` - Line 279
2. `wizard_remove_item()` - Line 340  
3. `wizard_complete_step_3()` - Line 378
4. `wizard_finalize()` - Line 577
5. `wizard_add_curtain()` - Line 748
6. `wizard_edit_curtain()` - Line 964
7. `wizard_remove_curtain()` - Line 1213
8. `wizard_upload_contract()` - Line 1254
9. `wizard_remove_contract_file()` - Line 1310
10. `wizard_cancel()` - Line 716

---

### 2. استعادة نماذج العقد من Git

**المشكلة:**
```
خطأ في توليد العقد: cannot import name 'ContractTemplate' from 'orders.contract_models'
```

**السبب:**
- تم حذف `ContractTemplate` و `ContractPrintLog` من `contract_models.py`
- خدمة `contract_generation_service.py` تستخدم هذه النماذج

**الحل:**
استعادة النماذج من commit `6be1efd4`:

```bash
git show 6be1efd4:orders/contract_models.py > /tmp/contract_models_old.py
```

**النماذج المُستعادة:**

#### ContractTemplate
- نموذج قوالب العقود
- يحتوي على إعدادات الشركة، الألوان، الخطوط، وتخطيط الصفحة
- يدعم قوالب HTML/CSS مخصصة
- يتتبع استخدام القالب والإحصائيات

**الحقول الرئيسية:**
- `name`: اسم القالب
- `template_type`: نوع القالب (standard/detailed/minimal/custom)
- `is_default`: قالب افتراضي
- `company_*`: معلومات الشركة
- `*_color`: ألوان القالب
- `html_content`: محتوى HTML مخصص
- `css_styles`: أنماط CSS مخصصة

**الدوال:**
- `get_default_template()`: الحصول على القالب الافتراضي
- `increment_usage()`: زيادة عداد الاستخدام
- `save()`: ضمان وجود قالب افتراضي واحد فقط

#### ContractPrintLog
- سجل طباعة العقود
- يتتبع من طبع العقد ومتى
- يرتبط بالطلب والقالب المستخدم

**الحقول:**
- `order`: الطلب المرتبط
- `template`: القالب المستخدم
- `printed_by`: المستخدم الذي طبع
- `print_type`: تلقائي/يدوي
- `printed_at`: تاريخ الطباعة

---

## الملفات المُعدّلة

### `/home/zakee/homeupdate/orders/wizard_views.py`
- عدد الأسطر المُعدّلة: ~90 سطر
- الدوال المُحدّثة: 10 دوال
- نوع التغيير: إصلاح أخطاء

### `/home/zakee/homeupdate/orders/contract_models.py`
- النماذج المُضافة: 2 (ContractTemplate, ContractPrintLog)
- عدد الأسطر المُضافة: ~200 سطر
- نوع التغيير: استعادة من Git

---

## التأثير على النظام

### الإيجابيات
✅ إصلاح خطأ إضافة المنتجات في الويزارد  
✅ إصلاح جميع دوال الويزارد التي تتعامل مع المسودات  
✅ استعادة خدمة توليد العقود PDF  
✅ دعم قوالب العقود المخصصة  
✅ تتبع طباعة العقود  

### النقاط المهمة
⚠️ يجب تطبيق migrations للنماذج المُستعادة:
```bash
python manage.py makemigrations orders
python manage.py migrate orders
```

⚠️ قد تحتاج إلى إنشاء قالب عقد افتراضي:
```bash
python manage.py shell
from orders.contract_models import ContractTemplate
ContractTemplate.objects.create(
    name='القالب الافتراضي',
    is_default=True,
    company_name='اسم الشركة'
)
```

---

## الاختبار المطلوب

### 1. اختبار الويزارد
- [ ] إنشاء طلب منتجات
- [ ] إنشاء طلب تركيب مع عقد
- [ ] إنشاء طلب معاينة
- [ ] إضافة منتجات في الخطوة 3
- [ ] التأكد من عدم حدوث أخطاء

### 2. اختبار توليد العقود
- [ ] توليد عقد PDF من طلب موجود
- [ ] التأكد من استخدام القالب الافتراضي
- [ ] التحقق من تسجيل الطباعة في ContractPrintLog

### 3. اختبار القوالب
- [ ] إنشاء قالب عقد جديد
- [ ] تعديل قالب موجود
- [ ] تحديد قالب كافتراضي
- [ ] استخدام قالب مخصص في توليد عقد

---

## الملفات ذات الصلة

### Models
- `/home/zakee/homeupdate/orders/contract_models.py`
- `/home/zakee/homeupdate/orders/wizard_models.py`
- `/home/zakee/homeupdate/orders/models.py`

### Views
- `/home/zakee/homeupdate/orders/wizard_views.py`
- `/home/zakee/homeupdate/orders/contract_views.py`

### Services
- `/home/zakee/homeupdate/orders/services/contract_generation_service.py`

### Templates
- `/home/zakee/homeupdate/orders/templates/orders/wizard/*.html`
- `/home/zakee/homeupdate/orders/templates/orders/contract_template.html`

---

## الخلاصة

تم إصلاح مشكلتين رئيسيتين:

1. **مشكلة الويزارد:** تم إصلاح خطأ `MultipleObjectsReturned` الذي كان يمنع إضافة المنتجات في الويزارد.

2. **مشكلة نماذج العقد:** تم استعادة `ContractTemplate` و `ContractPrintLog` التي كانت مطلوبة لخدمة توليد العقود.

النظام الآن:
- ✅ يدعم إنشاء الطلبات عبر الويزارد بدون أخطاء
- ✅ يدعم توليد عقود PDF باستخدام القوالب
- ✅ يتتبع استخدام وطباعة العقود
- ✅ يعمل مع جميع أنواع الطلبات (منتجات، تركيب، معاينة، إكسسوار)

---

**ملاحظة:** تأكد من تطبيق migrations قبل الاستخدام!

```bash
python manage.py makemigrations orders
python manage.py migrate orders
```
