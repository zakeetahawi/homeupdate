"""
WhatsApp Signals - النسخة المبسطة مع تفعيل ديناميكي للقوالب
إرسال إشعارات WhatsApp تلقائياً عند الأحداث
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


def get_whatsapp_settings():
    """الحصول على إعدادات WhatsApp"""
    from .models import WhatsAppSettings
    return WhatsAppSettings.objects.first()


def is_template_enabled(settings, message_type):
    """التحقق من تفعيل قالب معين"""
    if not settings:
        return False
    return settings.is_template_enabled(message_type)


def get_template(settings, message_type):
    """الحصول على القالب المفعل"""
    if not settings:
        return None
    return settings.get_template_for_type(message_type)


def send_template_notification(phone, template, variables, customer=None, order=None, 
                               installation=None, inspection=None):
    """
    إرسال إشعار باستخدام قالب مع حفظ السجل
    
    Args:
        phone: رقم الهاتف
        template: كائن WhatsAppMessageTemplate
        variables: dict بالمتغيرات
        customer: العميل (اختياري)
        order: الطلب (اختياري)
        installation: التركيب (اختياري)
        inspection: المعاينة (اختياري)
    """
    from .models import WhatsAppMessage
    from django.utils import timezone
    
    try:
        from .services import WhatsAppService
        service = WhatsAppService()
        
        # إنشاء سجل الرسالة
        formatted_phone = service._format_phone_number(phone)
        whatsapp_message = WhatsAppMessage.objects.create(
            customer=customer,
            order=order,
            installation=installation,
            inspection=inspection,
            message_type=template.message_type,
            template_used=template,
            message_text=f"Template: {template.meta_template_name} | Variables: {variables}",
            phone_number=formatted_phone,
            status='PENDING'
        )
        
        # إرسال الرسالة
        result = service.send_template_message(
            to=phone,
            template_name=template.meta_template_name,
            variables=variables,
            language=template.language
        )
        
        if result and result.get('messages'):
            msg_id = result['messages'][0].get('id')
            whatsapp_message.external_id = msg_id
            whatsapp_message.status = 'SENT'
            whatsapp_message.sent_at = timezone.now()
            whatsapp_message.save()
            logger.info(f"✅ WhatsApp sent: {template.meta_template_name} to {phone} - ID: {msg_id}")
            return result
        else:
            whatsapp_message.status = 'FAILED'
            whatsapp_message.error_message = str(result)
            whatsapp_message.save()
            logger.warning(f"⚠️ WhatsApp failed: {template.meta_template_name} to {phone}")
            return None
            
    except Exception as e:
        logger.error(f"❌ WhatsApp error: {template.meta_template_name} - {e}")
        # محاولة تحديث الرسالة إذا تم إنشاؤها
        try:
            if 'whatsapp_message' in locals():
                whatsapp_message.status = 'FAILED'
                whatsapp_message.error_message = str(e)
                whatsapp_message.save()
        except:
            pass
        return None


# ==========================================
# إشعار ترحيب العميل الجديد
# ==========================================
@receiver(post_save, sender='customers.Customer')
def customer_welcome_handler(sender, instance, created, **kwargs):
    """إرسال رسالة ترحيبية عند إنشاء عميل جديد"""
    if not created:
        return
    
    settings = get_whatsapp_settings()
    if not settings or not settings.is_active:
        return
    
    template = get_template(settings, 'WELCOME')
    if not template:
        return
    
    send_template_notification(
        phone=instance.phone,
        template=template,
        variables={'customer_name': instance.name},
        customer=instance
    )


# ==========================================
# إشعار إنشاء طلب
# ==========================================
@receiver(post_save, sender='orders.Order')
def order_created_handler(sender, instance, created, **kwargs):
    """إرسال إشعار عند إنشاء طلب جديد"""
    if not created:
        return
    
    settings = get_whatsapp_settings()
    if not settings or not settings.is_active:
        return
    
    template = get_template(settings, 'ORDER_CREATED')
    if not template:
        return
    
    send_template_notification(
        phone=instance.customer.phone,
        template=template,
        variables={
            'customer_name': instance.customer.name,
            'order_number': instance.order_number,
            'order_date': instance.created_at.strftime('%Y-%m-%d')
        },
        customer=instance.customer,
        order=instance
    )


# ==========================================
# إشعار جدولة المعاينة
# ==========================================
@receiver(post_save, sender='inspections.Inspection')
def inspection_scheduled_handler(sender, instance, created, **kwargs):
    """إرسال إشعار عند جدولة معاينة"""
    
    settings = get_whatsapp_settings()
    if not settings or not settings.is_active:
        return
    
    template = get_template(settings, 'INSPECTION_SCHEDULED')
    if not template:
        return
    
    # إرسال الرسالة فقط عند جدولة المعاينة (status = 'scheduled')
    if instance.status != 'scheduled':
        return
    
    # تحقق من وجود تاريخ معاينة محدد
    if not instance.scheduled_date:
        return
    
    send_template_notification(
        phone=instance.customer.phone,
        template=template,
        variables={
            'customer_name': instance.customer.name,
            'order_number': instance.order.order_number if instance.order else 'N/A',
            'inspection_date': instance.scheduled_date.strftime('%Y-%m-%d')
        },
        customer=instance.customer,
        order=instance.order,
        inspection=instance
    )


# ==========================================
# إشعار جدولة التركيب
# ==========================================
@receiver(post_save, sender='installations.InstallationSchedule')
def installation_scheduled_handler(sender, instance, created, **kwargs):
    """إرسال إشعار عند جدولة تركيب"""
    if not created:
        return
    
    settings = get_whatsapp_settings()
    if not settings or not settings.is_active:
        return
    
    template = get_template(settings, 'INSTALLATION_SCHEDULED')
    if not template:
        return
    
    # تحقق من وجود تاريخ تركيب
    if not instance.scheduled_date:
        return
    
    send_template_notification(
        phone=instance.order.customer.phone,
        template=template,
        variables={
            'customer_name': instance.order.customer.name,
            'order_number': instance.order.order_number,
            'installation_date': instance.scheduled_date.strftime('%Y-%m-%d')
        },
        customer=instance.order.customer,
        order=instance.order,
        installation=instance
    )


# ==========================================
# إشعار اكتمال التركيب
# ==========================================
@receiver(post_save, sender='installations.InstallationSchedule')
def installation_completed_handler(sender, instance, created, **kwargs):
    """إرسال إشعار عند اكتمال التركيب"""
    if created:
        return
    
    settings = get_whatsapp_settings()
    if not settings or not settings.is_active:
        return
    
    template = get_template(settings, 'INSTALLATION_COMPLETED')
    if not template:
        return
    
    # تحقق من أن الحالة تغيرت إلى "مكتمل"
    if instance.status != 'completed':
        return
    
    send_template_notification(
        phone=instance.order.customer.phone,
        template=template,
        variables={
            'customer_name': instance.order.customer.name,
            'order_number': instance.order.order_number
        },
        customer=instance.order.customer,
        order=instance.order,
        installation=instance
    )
