from celery import shared_task
import logging
from .models import WhatsAppMessage, WhatsAppMessageTemplate
from .services import WhatsAppService
from customers.models import Customer
from orders.models import Order
from installations.models import InstallationSchedule
from inspections.models import Inspection

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, autoretry_for=(Exception,))
def send_whatsapp_notification_task(
    self,
    customer_id,
    template_id,
    context,
    message_type,
    order_id=None,
    installation_id=None,
    inspection_id=None
):
    """
    مهمة Celery لإرسال إشعار WhatsApp
    
    Args:
        customer_id: معرف العميل
        template_id: معرف القالب
        context: قاموس المتغيرات
        message_type: نوع الرسالة
        order_id: معرف الطلب (اختياري)
        installation_id: معرف التركيب (اختياري)
        inspection_id: معرف المعاينة (اختياري)
    """
    try:
        # الحصول على الكائنات
        customer = Customer.objects.get(id=customer_id)
        template = WhatsAppMessageTemplate.objects.get(id=template_id)
        
        order = Order.objects.get(id=order_id) if order_id else None
        installation = InstallationSchedule.objects.get(id=installation_id) if installation_id else None
        inspection = Inspection.objects.get(id=inspection_id) if inspection_id else None
        
        # إنشاء خدمة WhatsApp
        service = WhatsAppService()
        
        # تعبئة القالب
        message_text = service.render_template(template, context)
        
        # إرسال الرسالة
        result = service.send_message(
            customer=customer,
            message_text=message_text,
            message_type=message_type,
            order=order,
            installation=installation,
            inspection=inspection,
            template=template
        )
        
        if result and result.status == 'SENT':
            logger.info(f"WhatsApp message sent successfully: {result.id}")
            return {'status': 'success', 'message_id': result.id}
        else:
            logger.error(f"Failed to send WhatsApp message")
            return {'status': 'failed'}
            
    except Exception as e:
        logger.error(f"Error in send_whatsapp_notification_task: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=3, default_retry_delay=300, autoretry_for=(Exception,))
def retry_failed_messages_task(self):
    """مهمة دورية لإعادة محاولة إرسال الرسائل الفاشلة"""
    service = WhatsAppService()
    
    # الحصول على الرسائل الفاشلة
    failed_messages = WhatsAppMessage.objects.filter(
        status='FAILED',
        retry_count__lt=service.settings.max_retry_attempts if service.settings else 3
    )
    
    retry_count = 0
    for message in failed_messages:
        if service.retry_failed_message(message.id):
            retry_count += 1
    
    logger.info(f"Retried {retry_count} failed WhatsApp messages")
    return {'retried': retry_count}
