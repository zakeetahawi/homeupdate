# تحديث نظام ترقيم العقود

## الملخص
تم تحديث نظام ترقيم العقود ليكون بالصيغة التالية:
```
{رقم_الطلب}-c{رقم_تسلسلي}
```

### مثال
- رقم الطلب: `13-0795-0007`
- رقم العقد الجديد: `13-0795-0007-c01`

## التغييرات المطبقة

### 1. ملف النموذج (models.py)

#### إضافة دالة توليد رقم العقد
تمت إضافة دالة جديدة `generate_unique_contract_number()` في ملف `/home/zakee/homeupdate/orders/models.py`:

```python
def generate_unique_contract_number(self):
    """توليد رقم عقد فريد بصيغة c01, c02, c03, إلخ"""
    # البحث عن آخر رقم عقد للعميل
    # توليد رقم تسلسلي جديد يبدأ من c01
    # التأكد من عدم التكرار
    return "c{num:02d}"  # مثل c01, c02, c03
```

#### تحديث دالة الحفظ
تم تحديث السطر 513 في دالة `save()`:
```python
# قديم
self.contract_number = self.order_number

# جديد
self.contract_number = self.generate_unique_contract_number()
```

### 2. قوالب العرض (Templates)

تم تحديث عرض رقم العقد في جميع القوالب التالية:

#### قالب العقد (contract_template.html)
- **الموقع**: `/home/zakee/homeupdate/orders/templates/orders/contract_template.html`
- **السطر 6**: عنوان الصفحة
- **السطر 704**: رقم العقد في رأس المستند

```html
<!-- قديم -->
{{ order.contract_number }}-{{ order.order_number }}

<!-- جديد -->
{{ order.order_number }}-{{ order.contract_number }}
```

#### صفحة تفاصيل الطلب (order_detail.html)
- **الموقع**: `/home/zakee/homeupdate/orders/templates/orders/order_detail.html`
- **السطر 773**: عرض رقم العقد في بطاقة معلومات العقد

```html
<!-- قديم -->
{{ order.contract_number|default:"00" }}-{{ order.order_number|stringformat:"04d" }}

<!-- جديد -->
{{ order.order_number }}-{{ order.contract_number|default:"c00" }}
```

#### صفحة نجاح الطلب (order_success.html)
- **الموقع**: `/home/zakee/homeupdate/orders/templates/orders/order_success.html`
- **السطر 243**: عرض رقم العقد في معلومات الطلب

```html
<!-- قديم -->
<span class="info-value">{{ order.contract_number }}</span>

<!-- جديد -->
<span class="info-value" dir="ltr">{{ order.order_number }}-{{ order.contract_number }}</span>
```

#### صفحة طلبات التسليم (tailoring_orders.html)
- **الموقع**: `/home/zakee/homeupdate/orders/templates/orders/tailoring_orders.html`
- **السطر 205**: عرض رقم العقد في جدول الطلبات

```html
<!-- قديم -->
<span class="fw-bold text-primary">{{ order.contract_number }}</span>

<!-- جديد -->
<span class="fw-bold text-primary" dir="ltr">{{ order.order_number }}-{{ order.contract_number }}</span>
```

### 3. سكريبت تحديث العقود الموجودة

تم إنشاء سكريبت لتحديث أرقام العقود الحالية:
- **الموقع**: `/home/zakee/homeupdate/update_contract_numbers.py`

#### طريقة الاستخدام
```bash
cd /home/zakee/homeupdate
source venv/bin/activate
python update_contract_numbers.py
```

#### ما يفعله السكريبت
1. البحث عن جميع الطلبات التي لها `contract_number` ولكن لا تبدأ بـ "c"
2. تجميع الطلبات حسب العميل
3. ترتيب الطلبات حسب تاريخ الإنشاء
4. توليد أرقام عقود جديدة بالترتيب (c01, c02, c03, ...)
5. التحديث في قاعدة البيانات

## كيفية التطبيق

### 1. تفعيل البيئة الافتراضية
```bash
cd /home/zakee/homeupdate
source venv/bin/activate
```

### 2. التحقق من عدم وجود أخطاء
```bash
python manage.py check
```

### 3. تحديث العقود الموجودة (اختياري)
```bash
python update_contract_numbers.py
```

### 4. إعادة تشغيل الخدمة
```bash
sudo systemctl restart homeupdate
```

## الصيغة النهائية لرقم العقد

### البنية
```
{branch_id}-{customer_code}-{date}-c{sequence}
```

### أمثلة
- `13-0795-0007-c01` - أول عقد للعميل
- `13-0795-0007-c02` - ثاني عقد للعميل
- `13-0795-0007-c03` - ثالث عقد للعميل
- وهكذا...

## ملاحظات مهمة

1. **حرف c ثابت**: حرف "c" هو دليل ثابت يشير إلى أن الرقم التالي هو رقم عقد
2. **التسلسل**: يبدأ الترقيم من c01 ويزيد تلقائياً لكل عميل
3. **عدم التكرار**: النظام يتحقق من عدم تكرار أرقام العقود لنفس العميل
4. **التوافق**: العقود القديمة يمكن تحديثها باستخدام السكريبت المرفق

## الملفات المعدلة

1. `/home/zakee/homeupdate/orders/models.py` - إضافة دالة توليد رقم العقد
2. `/home/zakee/homeupdate/orders/templates/orders/contract_template.html` - تحديث عرض رقم العقد
3. `/home/zakee/homeupdate/orders/templates/orders/order_detail.html` - تحديث عرض رقم العقد
4. `/home/zakee/homeupdate/orders/templates/orders/order_success.html` - تحديث عرض رقم العقد
5. `/home/zakee/homeupdate/orders/templates/orders/tailoring_orders.html` - تحديث عرض رقم العقد

## الملفات الجديدة

1. `/home/zakee/homeupdate/update_contract_numbers.py` - سكريبت تحديث العقود الموجودة
2. `/home/zakee/homeupdate/CONTRACT_NUMBER_C_FORMAT_UPDATE.md` - هذا الملف (التوثيق)

## الاختبار

بعد تطبيق التحديثات:
1. قم بإنشاء طلب تسليم أو تركيب جديد
2. تحقق من أن رقم العقد يظهر بالصيغة: `{رقم_الطلب}-c01`
3. قم بإنشاء طلب ثاني لنفس العميل
4. تحقق من أن رقم العقد يظهر بالصيغة: `{رقم_الطلب}-c02`
5. افتح صفحة تفاصيل الطلب وتأكد من ظهور الرقم بشكل صحيح
6. افتح ملف العقد PDF وتأكد من ظهور الرقم بشكل صحيح

## الدعم

في حالة وجود أي مشاكل:
1. تحقق من سجلات الأخطاء: `tail -f logs/django.log`
2. تأكد من تطبيق جميع التغييرات
3. تأكد من إعادة تشغيل الخدمة بعد التحديث
