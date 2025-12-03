# إعداد قالب العقد - Contract Template Setup

## المشكلة التي تم حلها
كان النظام يعطي خطأ "لا يوجد قالب عقد متاح" عند محاولة توليد العقد تلقائياً بعد إنشاء طلب من الويزارد.

### السبب
- جدول `ContractTemplate` في قاعدة البيانات كان فارغاً
- خدمة توليد العقود (`ContractGenerationService`) تتطلب وجود قالب نشط في قاعدة البيانات

## الحل المطبق

### 1. إنشاء قالب افتراضي
تم إنشاء قالب افتراضي في قاعدة البيانات بالخصائص التالية:
- **الاسم**: قالب العقد الافتراضي
- **النوع**: standard (قياسي)
- **الحالة**: نشط وافتراضي
- **القالب HTML**: يستخدم `/orders/templates/orders/contract_template.html`

### 2. آلية عمل النظام

#### عند إنشاء طلب من الويزارد:
1. يتم حفظ بيانات الطلب والستائر
2. تلقائياً يتم استدعاء `ContractGenerationService` (السطر 772-782 في `wizard_views.py`)
3. يتم توليد ملف PDF للعقد وحفظه في حقل `order.contract_file`

#### كود التوليد التلقائي:
```python
# في wizard_finalize - السطر 772
try:
    from .services.contract_generation_service import ContractGenerationService
    contract_service = ContractGenerationService(order)
    contract_saved = contract_service.save_contract_to_order(user=request.user)
    
    if contract_saved:
        logger.info(f"Contract PDF auto-generated for order {order.order_number}")
    else:
        logger.warning(f"Failed to auto-generate contract PDF for order {order.order_number}")
except Exception as e:
    logger.error(f"Error auto-generating contract PDF: {e}", exc_info=True)
```

### 3. مكونات النظام

#### ملف القالب HTML
- **المسار**: `/orders/templates/orders/contract_template.html`
- **الوصف**: قالب HTML/CSS متقدم لعرض تفاصيل العقد
- **المميزات**:
  - تصميم احترافي بألوان ذهبية
  - عرض بيانات العميل والطلب
  - جداول للستائر والأقمشة والإكسسوارات
  - علامة مائية وشعار الشركة
  - جاهز للطباعة وتحويل PDF

#### خدمة توليد العقود
- **المسار**: `/orders/services/contract_generation_service.py`
- **الفئة الرئيسية**: `ContractGenerationService`
- **الوظائف**:
  - `generate_html()`: توليد HTML من القالب
  - `generate_pdf()`: تحويل HTML إلى PDF باستخدام WeasyPrint
  - `save_contract_to_order()`: حفظ ملف PDF في الطلب

#### نموذج قاعدة البيانات
- **الملف**: `/orders/contract_models.py`
- **الجدول**: `ContractTemplate`
- **الحقول الرئيسية**:
  - بيانات الشركة (الاسم، الشعار، العنوان، الهاتف...)
  - إعدادات التصميم (الألوان، الخطوط، الهوامش...)
  - النصوص المخصصة (الرأس، التذييل، الشروط...)
  - إحصائيات الاستخدام

## كيفية استخدام النظام

### للمستخدمين
1. أنشئ طلب جديد من الويزارد
2. أضف الستائر والتفاصيل في الخطوة 5
3. راجع البيانات في الخطوة 6
4. عند الضغط على "حفظ الطلب":
   - ✅ يتم إنشاء الطلب
   - ✅ يتم توليد ملف PDF للعقد تلقائياً
   - ✅ يتم حفظ الملف في الطلب

### للمطورين

#### إنشاء قالب جديد يدوياً:
```python
from orders.contract_models import ContractTemplate

template = ContractTemplate.objects.create(
    name='قالب مخصص',
    template_type='custom',
    is_active=True,
    is_default=False,  # واحد فقط يمكن أن يكون افتراضي
    company_name='اسم الشركة',
    primary_color='#a67c52',
    # ... باقي الإعدادات
)
```

#### إعادة توليد عقد موجود:
```python
from orders.models import Order
from orders.services.contract_generation_service import ContractGenerationService

order = Order.objects.get(order_number='1-0003-0001')
service = ContractGenerationService(order)
service.save_contract_to_order(user=request.user)
```

#### استخدام قالب محدد:
```python
from orders.contract_models import ContractTemplate

template = ContractTemplate.objects.get(id=2)
service = ContractGenerationService(order, template=template)
service.save_contract_to_order()
```

## الصيانة والتحديثات

### تحديث تصميم العقد
- عدّل ملف `/orders/templates/orders/contract_template.html`
- لا حاجة لتعديل قاعدة البيانات
- التغييرات ستطبق على جميع العقود الجديدة

### تحديث بيانات الشركة
```python
template = ContractTemplate.objects.get(is_default=True)
template.company_name = 'الاسم الجديد'
template.company_phone = '+966 XX XXX XXXX'
template.save()
```

### إضافة CSS مخصص
```python
template = ContractTemplate.objects.get(is_default=True)
template.css_styles = """
@page {
    margin: 2cm;
}
body {
    font-size: 12px;
}
"""
template.save()
```

## ملفات ذات صلة

- `orders/wizard_views.py` - السطر 772-782: كود التوليد التلقائي
- `orders/contract_views.py` - السطر 76-155: إعادة توليد العقد
- `orders/services/contract_generation_service.py` - خدمة التوليد
- `orders/contract_models.py` - نماذج قاعدة البيانات
- `orders/templates/orders/contract_template.html` - قالب HTML

## الاختبار

### اختبار توليد عقد لطلب موجود:
```bash
python manage.py shell << 'EOF'
from orders.models import Order
from orders.services.contract_generation_service import ContractGenerationService

order = Order.objects.get(order_number='رقم_الطلب')
service = ContractGenerationService(order)
success = service.save_contract_to_order()
print(f"النتيجة: {'نجح' if success else 'فشل'}")
print(f"مسار الملف: {order.contract_file.url if order.contract_file else 'لا يوجد'}")
EOF
```

## الملاحظات المهمة

1. ⚠️ يجب وجود قالب نشط واحد على الأقل في النظام
2. ✅ القالب الافتراضي يُستخدم تلقائياً إذا لم يُحدد قالب آخر
3. 📝 يتم حفظ سجل لكل عملية طباعة في جدول `ContractPrintLog`
4. 🔄 يمكن إعادة توليد العقد في أي وقت دون فقدان البيانات
5. 📦 ملفات PDF تُحفظ في مجلد `media/contracts/`

## الدعم الفني

في حالة ظهور خطأ "لا يوجد قالب عقد متاح":
1. تحقق من وجود قالب نشط: `ContractTemplate.objects.filter(is_active=True).count()`
2. أنشئ قالب افتراضي باستخدام الكود في هذا الملف
3. تحقق من صلاحيات الملفات في مجلد `media/contracts/`

---
**تاريخ الإنشاء**: 2025-11-24  
**الحالة**: ✅ تم الحل والاختبار بنجاح
