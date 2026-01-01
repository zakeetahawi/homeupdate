from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from customers.models import Customer
from orders.models import Order
from installations.models import InstallationSchedule
from inspections.models import Inspection


class WhatsAppSettings(models.Model):
    """إعدادات WhatsApp API"""
    
    API_PROVIDERS = [
        ('meta', 'Meta Cloud API'),
    ]
    
    api_provider = models.CharField(
        max_length=20,
        choices=API_PROVIDERS,
        default='meta',
        verbose_name="مزود API"
    )
    account_sid = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Account SID"
    )
    auth_token = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Auth Token"
    )
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
    enable_welcome_messages = models.BooleanField(
        default=False,
        verbose_name="تفعيل الرسائل الترحيبية",
        help_text="إرسال رسالة ترحيبية تلقائياً عند إنشاء عميل جديد"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "إعدادات WhatsApp"
        verbose_name_plural = "إعدادات WhatsApp"
    
    def __str__(self):
        return f"WhatsApp Settings ({self.api_provider})"


class WhatsAppMessageTemplate(models.Model):
    """قوالب رسائل WhatsApp"""
    
    MESSAGE_TYPES = [
        ('ORDER_CREATED', 'إنشاء طلب'),
        ('ORDER_WITH_CONTRACT', 'طلب مع عقد'),
        ('ORDER_WITH_INVOICE', 'طلب مع فاتورة'),
        ('INSTALLATION_SCHEDULED', 'جدولة تركيب'),
        ('INSTALLATION_COMPLETED', 'اكتمال تركيب'),
        ('INSPECTION_CREATED', 'إنشاء معاينة'),
        ('INSPECTION_SCHEDULED', 'جدولة معاينة'),
        ('CUSTOM', 'رسالة مخصصة'),
    ]
    
    ORDER_TYPES = [
        ('installation', 'تركيب'),
        ('delivery', 'تسليم'),
        ('accessory', 'إكسسوار'),
        ('inspection', 'معاينة'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name="اسم القالب"
    )
    message_type = models.CharField(
        max_length=50,
        choices=MESSAGE_TYPES,
        verbose_name="نوع الرسالة"
    )
    template_text = models.TextField(
        verbose_name="نص القالب",
        help_text="استخدم {customer_name}, {order_number}, إلخ للمتغيرات"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="مفعل"
    )
    send_contract = models.BooleanField(
        default=False,
        verbose_name="إرسال العقد"
    )
    send_invoice = models.BooleanField(
        default=False,
        verbose_name="إرسال الفاتورة"
    )
    order_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name="أنواع الطلبات",
        help_text="أنواع الطلبات التي يطبق عليها هذا القالب"
    )
    meta_template_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="اسم القالب في Meta",
        help_text="اسم القالب المعتمد في Meta (مثل: order_confirmation, hello_world)"
    )
    language = models.CharField(
        max_length=5,
        default='ar',
        verbose_name="اللغة"
    )
    delay_minutes = models.IntegerField(
        default=0,
        verbose_name="تأخير الإرسال (دقائق)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "قالب رسالة"
        verbose_name_plural = "قوالب الرسائل"
        ordering = ['message_type', 'name']
    
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
