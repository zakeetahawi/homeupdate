from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from customers.models import Customer
from orders.models import Order
from installations.models import InstallationSchedule
from inspections.models import Inspection


class WhatsAppSettings(models.Model):
    """إعدادات WhatsApp Meta Cloud API"""
    
    phone_number = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],
        verbose_name="رقم WhatsApp"
    )
    business_account_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Business Account ID",
        help_text="معرف حساب WhatsApp Business"
    )
    # حقول Meta Cloud API
    phone_number_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Phone Number ID",
        help_text="معرف الرقم في Meta Cloud API"
    )
    access_token = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Access Token",
        help_text="مفتاح الوصول لـ Meta Cloud API"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="مفعل"
    )
    test_mode = models.BooleanField(
        default=False,
        verbose_name="وضع الاختبار"
    )
    retry_failed_messages = models.BooleanField(
        default=True,
        verbose_name="إعادة محاولة الرسائل الفاشلة"
    )
    max_retry_attempts = models.IntegerField(
        default=3,
        verbose_name="عدد محاولات الإعادة"
    )
    default_language = models.CharField(
        max_length=5,
        default='ar',
        verbose_name="اللغة الافتراضية"
    )
    use_template = models.BooleanField(
        default=False,
        verbose_name="استخدام قالب hello_world",
        help_text="إرسال قالب hello_world بدلاً من رسائل نصية (للتأكد من الوصول)"
    )
    
    # صورة Header للقوالب
    header_image = models.ImageField(
        upload_to='whatsapp/header/',
        blank=True,
        null=True,
        verbose_name="صورة الهيدر",
        help_text="صورة اللوغو التي تظهر في رأس الرسائل (PNG أو JPG)"
    )
    header_media_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Media ID للصورة",
        help_text="معرف الصورة المرفوعة على WhatsApp (يُملأ تلقائياً بعد الرفع)"
    )
    
    # القوالب المفعلة - ديناميكية
    enabled_templates = models.ManyToManyField(
        'WhatsAppMessageTemplate',
        blank=True,
        verbose_name="القوالب المفعلة",
        help_text="اختر القوالب التي تريد تفعيلها للإرسال التلقائي"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "إعدادات WhatsApp"
        verbose_name_plural = "إعدادات WhatsApp"
    
    def __str__(self):
        return f"WhatsApp Settings ({self.phone_number})"
    
    def is_template_enabled(self, message_type):
        """التحقق من تفعيل قالب حسب نوع الرسالة"""
        return self.enabled_templates.filter(message_type=message_type, is_active=True).exists()
    
    def get_template_for_type(self, message_type):
        """الحصول على القالب المفعل لنوع رسالة معين"""
        return self.enabled_templates.filter(message_type=message_type, is_active=True).first()


class WhatsAppMessageTemplate(models.Model):
    """قوالب رسائل WhatsApp - مبسط"""
    
    MESSAGE_TYPES = [
        ('WELCOME', 'ترحيب بعميل جديد'),
        ('ORDER_CREATED', 'تأكيد طلب'),
        ('INSPECTION_SCHEDULED', 'موعد معاينة'),
        ('INSPECTION_COMPLETED', 'اكتمال معاينة'),
        ('INSTALLATION_SCHEDULED', 'موعد تركيب'),
        ('INSTALLATION_COMPLETED', 'اكتمال تركيب'),
        ('INVOICE', 'فاتورة'),
        ('CONTRACT', 'عقد'),
        ('CUSTOM', 'مخصص'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name="اسم القالب (للعرض)"
    )
    message_type = models.CharField(
        max_length=50,
        choices=MESSAGE_TYPES,
        unique=True,
        verbose_name="نوع الرسالة",
        help_text="كل نوع يمكن أن يكون له قالب واحد فقط"
    )
    meta_template_name = models.CharField(
        max_length=100,
        verbose_name="اسم القالب في Meta",
        help_text="اسم القالب المعتمد في Meta (مثل: customer_welcome, inspection_date)"
    )
    language = models.CharField(
        max_length=10,
        default='ar',
        verbose_name="اللغة"
    )
    test_variables = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="متغيرات الاختبار",
        help_text='مثال: {"customer_name": "عميل تجريبي", "order_number": "TEST-001"}'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="مفعل"
    )
    description = models.TextField(
        blank=True,
        verbose_name="وصف/ملاحظات",
        help_text="وصف اختياري للقالب"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "قالب رسالة"
        verbose_name_plural = "قوالب الرسائل"
        ordering = ['message_type']
    
    def __str__(self):
        return f"{self.name} ({self.get_message_type_display()})"


class WhatsAppMessage(models.Model):
    """سجل رسائل WhatsApp المرسلة"""
    
    STATUS_CHOICES = [
        ('PENDING', 'قيد الانتظار'),
        ('SENT', 'تم الإرسال'),
        ('DELIVERED', 'تم التسليم'),
        ('READ', 'تمت القراءة'),
        ('FAILED', 'فشل'),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='whatsapp_messages',
        verbose_name="العميل"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_messages',
        verbose_name="الطلب"
    )
    installation = models.ForeignKey(
        InstallationSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_messages',
        verbose_name="التركيب"
    )
    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_messages',
        verbose_name="المعاينة"
    )
    message_type = models.CharField(
        max_length=50,
        verbose_name="نوع الرسالة"
    )
    template_used = models.ForeignKey(
        WhatsAppMessageTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="القالب المستخدم"
    )
    message_text = models.TextField(
        verbose_name="نص الرسالة"
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name="رقم الهاتف"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="الحالة"
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="معرف خارجي",
        help_text="Message SID من Twilio"
    )
    attachments = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="المرفقات"
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="رسالة الخطأ"
    )
    retry_count = models.IntegerField(
        default=0,
        verbose_name="عدد المحاولات"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="وقت الإرسال"
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="وقت التسليم"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="وقت القراءة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "رسالة WhatsApp"
        verbose_name_plural = "رسائل WhatsApp"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['customer', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.customer.name} - {self.message_type} ({self.status})"

class WhatsAppEventType(models.Model):
    """أنواع الأحداث القابلة للتعديل"""
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="كود الحدث",
        help_text="الكود الداخلي (مثل: ORDER_CREATED)"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="اسم الحدث",
        help_text="الاسم الذي يظهر في لوحة التحكم"
    )
    description = models.TextField(
        blank=True,
        verbose_name="وصف الحدث"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="مفعل"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "نوع حدث"
        verbose_name_plural = "أنواع الأحداث"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class WhatsAppNotificationRule(models.Model):
    """قواعد الإشعارات التلقائية"""
    
    EVENT_TYPES = [
        ('ORDER_CREATED', 'إنشاء طلب'),
        ('ORDER_UPDATED', 'تحديث طلب'),
        ('INSTALLATION_SCHEDULED', 'جدولة تركيب'),
        ('INSTALLATION_COMPLETED', 'اكتمال تركيب'),
        ('INSPECTION_CREATED', 'إنشاء معاينة'),
        ('INSPECTION_SCHEDULED', 'جدولة معاينة'),
        ('PAYMENT_REMINDER', 'تذكير بالدفع'),
        ('CUSTOMER_WELCOME', 'ترحيب بالعميل'),
    ]
    
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        unique=True,
        verbose_name="نوع الحدث"
    )
    is_enabled = models.BooleanField(
        default=True,
        verbose_name="مفعل"
    )
    template = models.ForeignKey(
        WhatsAppMessageTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="القالب"
    )
    delay_minutes = models.IntegerField(
        default=0,
        verbose_name="تأخير الإرسال (دقائق)"
    )
    conditions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="الشروط",
        help_text="شروط إضافية لتفعيل القاعدة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "قاعدة إشعار"
        verbose_name_plural = "قواعد الإشعارات"
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {'مفعل' if self.is_enabled else 'معطل'}"
