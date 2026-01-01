from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging
from orders.models import Order
from installations.models import InstallationSchedule
from inspections.models import Inspection
from .models import WhatsAppNotificationRule, WhatsAppMessageTemplate
from .services import WhatsAppService
from .tasks import send_whatsapp_notification_task

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def order_created_handler(sender, instance, created, **kwargs):
    """إرسال إشعار عند إنشاء طلب جديد"""
    if not created:
        return
    
    try:
        # التحقق من تفعيل القاعدة
        rule = WhatsAppNotificationRule.objects.filter(
            event_type='ORDER_CREATED',
            is_enabled=True
        ).first()
        
        if not rule or not rule.template:
            logger.info("No active rule or template for ORDER_CREATED")
            return
        
        # تحضير البيانات
        context = {
            'customer_name': instance.customer.name,
            'order_number': instance.order_number,
            'order_date': instance.created_at.strftime('%Y-%m-%d'),
            'order_type': instance.get_order_type_display() if instance.order_type else 'عام',
            'total_amount': f"{instance.total_amount:,.2f}",
            'paid_amount': f"{instance.paid_amount:,.2f}",
            'remaining_amount': f"{instance.remaining_amount:,.2f}",
            'company_phone': '01000000000',
        }
        
        # إرسال مباشر (بدون Celery للاختبار)
        service = WhatsAppService()
        
        # التحقق من إعدادات الإرسال
        from .models import WhatsAppSettings
        settings = WhatsAppSettings.objects.first()
        
        # الأولوية 1: إذا use_template مفعل، استخدم hello_world (يتجاهل كل شيء)
        if settings and settings.use_template:
            try:
                result = service.send_template_message(
                    to=instance.customer.phone,
                    template_name='hello_world',
                    language='en_US'
                )
                
                if result and result.get('messages'):
                    logger.info(f"WhatsApp hello_world template sent for order {instance.order_number}: {result['messages'][0].get('id')}")
                else:
                    logger.warning(f"Failed to send WhatsApp template for order {instance.order_number}")
            except Exception as e:
                logger.error(f"Error sending hello_world template: {e}")
        
        # الأولوية 2: إذا القالب له meta_template_name، استخدمه
        elif rule.template.meta_template_name:
            try:
                # تحضير المتغيرات للقالب
                components = [
                    instance.customer.name,           # {{customer_name}}
                    instance.order_number,            # {{order_number}}
                    instance.created_at.strftime('%Y-%m-%d'),  # {{order_date}}
                    f"{instance.total_amount:,.0f}",  # {{total_amount}}
                    f"{instance.paid_amount:,.0f}",   # {{paid_amount}}
                    f"{instance.remaining_amount:,.0f}"  # {{remaining_amount}}
                ]
                
                result = service.send_template_message(
                    to=instance.customer.phone,
                    template_name=rule.template.meta_template_name,
                    language='ar',
                    components=components
                )
                
                if result and result.get('messages'):
                    logger.info(f"WhatsApp {rule.template.meta_template_name} template sent for order {instance.order_number}: {result['messages'][0].get('id')}")
                else:
                    logger.warning(f"Failed to send WhatsApp template for order {instance.order_number}")
            except Exception as e:
                logger.error(f"Error sending {rule.template.meta_template_name} template: {e}")
        
        # الأولوية 3: استخدام الرسائل النصية العادية
        else:
            message_text = service.render_template(rule.template, context)
            
            result = service.send_message(
                customer=instance.customer,
                message_text=message_text,
                message_type='ORDER_CREATED',
                order=instance,
                template=rule.template
            )
            
            if result:
                logger.info(f"WhatsApp text message sent for order {instance.order_number}: {result.id}")
            else:
                logger.warning(f"Failed to send WhatsApp message for order {instance.order_number}")
        
    except Exception as e:
        logger.error(f"Error in order_created_handler: {e}", exc_info=True)


@receiver(post_save, sender=InstallationSchedule)
def installation_scheduled_handler(sender, instance, created, **kwargs):
    """إرسال إشعار عند جدولة تركيب"""
    if not created:
        return
    
    try:
        rule = WhatsAppNotificationRule.objects.filter(
            event_type='INSTALLATION_SCHEDULED',
            is_enabled=True
        ).first()
        
        if not rule or not rule.template:
            return
        
        # الحصول على معلومات الفني
        technician_name = instance.team.name if instance.team else 'سيتم تحديده'
        technician_phone = instance.team.contact_phone if instance.team else ''
        
        context = {
            'customer_name': instance.order.customer.name,
            'order_number': instance.order.order_number,
            'installation_date': instance.scheduled_date.strftime('%Y-%m-%d'),
            'technician_name': technician_name,
            'technician_phone': technician_phone,
        }
        
        send_whatsapp_notification_task.delay(
            customer_id=instance.order.customer.id,
            order_id=instance.order.id,
            installation_id=instance.id,
            template_id=rule.template.id,
            context=context,
            message_type='INSTALLATION_SCHEDULED'
        )
        
        logger.info(f"WhatsApp notification queued for installation {instance.id}")
        
    except Exception as e:
        logger.error(f"Error in installation_scheduled_handler: {e}")


@receiver(post_save, sender=Inspection)
def inspection_created_handler(sender, instance, created, **kwargs):
    """إرسال إشعار عند إنشاء معاينة"""
    if not created:
        return
    
    try:
        rule = WhatsAppNotificationRule.objects.filter(
            event_type='INSPECTION_CREATED',
            is_enabled=True
        ).first()
        
        if not rule or not rule.template:
            return
        
        context = {
            'customer_name': instance.customer.name,
            'order_number': instance.order.order_number if instance.order else 'N/A',
            'created_date': instance.created_at.strftime('%Y-%m-%d'),
        }
        
        send_whatsapp_notification_task.delay(
            customer_id=instance.customer.id,
            inspection_id=instance.id,
            template_id=rule.template.id,
            context=context,
            message_type='INSPECTION_CREATED'
        )
        
        logger.info(f"WhatsApp notification queued for order {instance.order.order_number if instance.order else 'N/A'}")
        
    except Exception as e:
        logger.error(f"Error in inspection_created_handler: {e}")


@receiver(post_save, sender='customers.Customer')
def customer_created_handler(sender, instance, created, **kwargs):
    """
    إرسال رسالة ترحيبية عند إنشاء عميل جديد
    """
    if not created:
        return
    
    try:
        from .models import WhatsAppSettings, WhatsAppNotificationRule
        from .services import WhatsAppService
        
        # التحقق من تفعيل الرسائل الترحيبية
        settings = WhatsAppSettings.objects.first()
        if not settings or not settings.is_active or not settings.enable_welcome_messages:
            logger.info("Welcome messages are disabled")
            return
        
        # البحث عن قاعدة الرسائل الترحيبية
        try:
            rule = WhatsAppNotificationRule.objects.get(
                event_type='CUSTOMER_WELCOME',
                is_enabled=True
            )
        except WhatsAppNotificationRule.DoesNotExist:
            logger.info("No active welcome message rule found")
            return
        
        # البحث عن القالب
        if not rule.template:
            logger.warning("Welcome rule has no template")
            return
        
        # إرسال الرسالة
        service = WhatsAppService()
        
        # التحقق من إعدادات الإرسال
        if settings.use_template:
            # استخدام hello_world template
            try:
                result = service.send_template_message(
                    to=instance.phone,
                    template_name='hello_world',
                    language='en_US'
                )
                
                if result and result.get('messages'):
                    logger.info(f"Welcome template sent to {instance.name}: {result['messages'][0].get('id')}")
                else:
                    logger.warning(f"Failed to send welcome template to {instance.name}")
            except Exception as e:
                logger.error(f"Error sending welcome template: {e}")
        else:
            # استخدام الرسائل النصية العادية
            # تحضير السياق
            context = {
                'customer_name': instance.name,
                'phone': instance.phone,
                'date': timezone.now().strftime('%Y-%m-%d'),
                'customer_id': instance.customer_number,
            }
            
            # تعبئة القالب
            message_text = service.render_template(rule.template, context)
            
            # إرسال
            result = service.send_message(
                customer=instance,
                message_text=message_text,
                message_type='CUSTOMER_WELCOME',
                template=rule.template
            )
            
            if result:
                logger.info(f"Welcome message sent to {instance.name}: {result.id}")
            else:
                logger.warning(f"Failed to send welcome message to {instance.name}")
        
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")
