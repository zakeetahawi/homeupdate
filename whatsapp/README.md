# WhatsApp Integration

نظام تكامل WhatsApp الكامل مع Django

## الميزات

- ✅ إرسال إشعارات تلقائية عبر WhatsApp
- ✅ 8 قوالب رسائل جاهزة
- ✅ لوحة تحكم كاملة في Django Admin
- ✅ تكامل مع Twilio API
- ✅ دعم المرفقات (عقود، فواتير، QR Codes)
- ✅ نظام إعادة محاولة ذكي
- ✅ Celery Tasks للأداء
- ✅ وضع اختبار آمن

## التثبيت

التطبيق مثبت بالفعل في المشروع.

## الإعداد السريع

### 1. إنشاء القوالب الافتراضية

```bash
python manage.py create_whatsapp_templates
```

### 2. إنشاء قواعد الإشعارات

```bash
python manage.py create_notification_rules
```

### 3. إعداد Twilio

1. الذهاب إلى Django Admin: `/admin/whatsapp/whatsappsettings/`
2. إضافة إعدادات Twilio:
   - API Provider: `Twilio`
   - Account SID: من Twilio Console
   - Auth Token: من Twilio Console
   - Phone Number: رقم WhatsApp من Twilio
   - Is Active: ✓
   - Test Mode: ✓ (للاختبار)

## الاستخدام

### إرسال رسالة يدوياً

```python
from whatsapp.services import WhatsAppService
from customers.models import Customer

service = WhatsAppService()
customer = Customer.objects.get(id=1)

service.send_message(
    customer=customer,
    message_text="مرحباً بك!",
    message_type='CUSTOM'
)
```

### تخصيص قالب

```python
from whatsapp.models import WhatsAppMessageTemplate

template = WhatsAppMessageTemplate.objects.get(
    name='إنشاء طلب عادي'
)
template.template_text = "نص جديد مع {customer_name}"
template.save()
```

## القوالب المتاحة

1. **إنشاء طلب عادي** - عند إنشاء أي طلب
2. **إنشاء طلب تركيب** - طلبات التركيب مع تنبيه 72 ساعة
3. **طلب مع عقد** - إرسال العقد الإلكتروني
4. **جدولة تركيب** - عند جدولة موعد التركيب
5. **اكتمال تركيب** - عند إتمام التركيب
6. **إنشاء معاينة** - عند إنشاء طلب معاينة
7. **جدولة معاينة** - عند جدولة موعد المعاينة
8. **فاتورة** - إرسال الفاتورة

## المتغيرات المدعومة

- `{customer_name}` - اسم العميل
- `{order_number}` - رقم الطلب
- `{order_date}` - تاريخ الطلب
- `{total_amount}` - المبلغ الإجمالي
- `{paid_amount}` - المبلغ المدفوع
- `{remaining_amount}` - المبلغ المتبقي
- `{installation_date}` - تاريخ التركيب
- `{technician_name}` - اسم الفني
- `{technician_phone}` - هاتف الفني
- `{inspector_name}` - اسم المعاين
- `{inspector_phone}` - هاتف المعاين

## الإشعارات التلقائية

يتم إرسال الإشعارات تلقائياً عند:

- إنشاء طلب جديد
- جدولة تركيب
- اكتمال تركيب
- إنشاء معاينة
- جدولة معاينة

يمكن تفعيل/تعطيل كل إشعار من Django Admin.

## الأمان

- ✅ بيانات API محمية في قاعدة البيانات
- ✅ وضع اختبار لتجنب الإرسال الخاطئ
- ✅ Validation لأرقام الهواتف
- ✅ Rate limiting من Twilio

## الدعم

للمزيد من المعلومات، راجع:
- [Twilio WhatsApp API Docs](https://www.twilio.com/docs/whatsapp)
- [Django Signals](https://docs.djangoproject.com/en/stable/topics/signals/)
- [Celery](https://docs.celeryproject.org/)
