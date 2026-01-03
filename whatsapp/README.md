# WhatsApp Integration

نظام تكامل WhatsApp مع Meta Cloud API

## الميزات

- ✅ إرسال إشعارات تلقائية عبر WhatsApp
- ✅ تكامل مع Meta WhatsApp Cloud API
- ✅ رفع تلقائي للصور في رأس القوالب
- ✅ تفعيل ديناميكي للقوالب
- ✅ لوحة تحكم كاملة في Django Admin
- ✅ نظام إعادة محاولة ذكي
- ✅ وضع اختبار آمن

## التثبيت

التطبيق مثبت بالفعل. عند تشغيل `migrate` لأول مرة، سيتم إنشاء:
- 5 قوالب رسائل جاهزة
- إعدادات WhatsApp الأساسية (بدون بيانات الاعتماد)

## الإعداد السريع

### 1. تشغيل الترحيلات

```bash
python manage.py migrate whatsapp
```

### 2. إعداد Meta Cloud API

1. الذهاب إلى Django Admin: `/admin/whatsapp/whatsappsettings/`
2. تعديل الإعدادات وإضافة:
   - **Phone Number**: رقم WhatsApp Business
   - **Business Account ID**: من Meta Business Suite
   - **Phone Number ID**: من Meta WhatsApp Manager
   - **Access Token**: Token دائم من Meta
   - **Is Active**: ✓
   - **صورة الهيدر**: رفع اللوغو (PNG أو JPG)

### 3. تفعيل القوالب

في نفس صفحة الإعدادات، اختر القوالب المراد تفعيلها من قسم "القوالب المفعلة".

## القوالب المتاحة

| القالب | اسم Meta | الوصف |
|--------|----------|-------|
| ترحيب بالعميل | `customer_welcome` | عند إضافة عميل جديد |
| تأكيد الطلب | `confirm_order` | عند إنشاء طلب |
| موعد المعاينة | `inspection_date` | عند جدولة معاينة |
| موعد التركيب | `installation_date` | عند جدولة تركيب |
| انتهاء التركيب | `installing_done` | عند اكتمال التركيب |

## الاستخدام

### إرسال قالب يدوياً

```python
from whatsapp.services import WhatsAppService

service = WhatsAppService()
result = service.send_template_message(
    to='01234567890',
    template_name='customer_welcome',
    variables={'customer_name': 'أحمد محمد'},
    language='ar'
)
```

### الإرسال التلقائي

الإرسال يتم تلقائياً عبر Django Signals عند:
- إضافة عميل جديد ← قالب الترحيب
- إنشاء طلب ← قالب تأكيد الطلب
- جدولة معاينة ← قالب موعد المعاينة
- جدولة تركيب ← قالب موعد التركيب
- اكتمال تركيب ← قالب انتهاء التركيب

## إضافة قالب جديد

1. أنشئ القالب في **Meta Business Suite** واحصل على الموافقة
2. أضف القالب من Django Admin: `/admin/whatsapp/whatsappmessagetemplate/add/`
3. فعّله من إعدادات WhatsApp

## الأمان

- ✅ بيانات API محمية في قاعدة البيانات
- ✅ لا يتم حفظ بيانات الاعتماد في الكود أو الترحيلات
- ✅ وضع اختبار لتجنب الإرسال الخاطئ
- ✅ Validation لأرقام الهواتف

## الدعم

للمزيد من المعلومات، راجع:
- [Meta WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Django Signals](https://docs.djangoproject.com/en/stable/topics/signals/)
