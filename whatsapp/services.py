"""
Meta WhatsApp Service - Meta Cloud API
"""
import requests
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class WhatsAppService:
    """خدمة WhatsApp عبر Meta Cloud API"""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def __init__(self):
        from .models import WhatsAppSettings
        
        self.settings = WhatsAppSettings.objects.first()
        if not self.settings:
            raise ValueError("WhatsApp settings not configured")
        
        if self.settings.api_provider != 'meta':
            raise ValueError("API provider is not set to Meta Cloud API")
        
        self.phone_id = self.settings.phone_number_id
        self.token = self.settings.access_token
        
        if not self.phone_id or not self.token:
            raise ValueError("Phone Number ID and Access Token are required for Meta Cloud API")
    
    def _get_headers(self):
        """الحصول على headers للطلبات"""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        }
    
    def _format_phone_number(self, phone):
        """تنسيق رقم الهاتف"""
        if not phone:
            return None
        
        # إزالة المسافات والرموز
        phone = ''.join(filter(str.isdigit, phone))
        
        # إضافة رمز الدولة إذا لم يكن موجوداً
        if not phone.startswith('20'):  # مصر
            if phone.startswith('0'):
                phone = '20' + phone[1:]
            else:
                phone = '20' + phone
        
        return phone
    
    def send_text_message(self, to, message):
        """
        إرسال رسالة نصية
        
        Args:
            to: رقم الهاتف
            message: نص الرسالة
        
        Returns:
            dict: استجابة API
        """
        url = f"{self.BASE_URL}/{self.phone_id}/messages"
        
        # تنسيق الرقم
        to = self._format_phone_number(to)
        
        payload = {
            'messaging_product': 'whatsapp',
            'to': to,
            'type': 'text',
            'text': {'body': message}
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending WhatsApp message via Meta Cloud API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    def send_template_message(self, to, template_name, language='ar', components=None):
        """
        إرسال رسالة قالب معتمد
        
        Args:
            to: رقم الهاتف
            template_name: اسم القالب
            language: كود اللغة (ar, en_US, etc.)
            components: قائمة بقيم المتغيرات (strings)
        
        Returns:
            dict: استجابة API
        """
        url = f"{self.BASE_URL}/{self.phone_id}/messages"
        
        # تنسيق رقم الهاتف
        formatted_phone = self._format_phone_number(to)
        
        # بناء payload القالب
        template_payload = {
            "name": template_name,
            "language": {
                "code": language
            }
        }
        
        # إضافة المتغيرات إذا وجدت
        if components:
            # تحويل القائمة إلى تنسيق Meta API الصحيح
            template_payload["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": str(value)
                        }
                        for value in components
                    ]
                }
            ]
        
        payload = {
            "messaging_product": "whatsapp",
            "to": formatted_phone,
            "type": "template",
            "template": template_payload
        }
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending template message via Meta Cloud API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    def send_message(self, customer, message_text, message_type, order=None, 
                    installation=None, inspection=None, template=None):
        """
        إرسال رسالة WhatsApp (واجهة موحدة)
        
        Args:
            customer: كائن العميل
            message_text: نص الرسالة
            message_type: نوع الرسالة
            order: الطلب (اختياري)
            installation: التركيب (اختياري)
            inspection: المعاينة (اختياري)
            template: القالب المستخدم (اختياري)
        
        Returns:
            WhatsAppMessage: سجل الرسالة
        """
        from .models import WhatsAppMessage
        
        # إنشاء سجل الرسالة
        whatsapp_message = WhatsAppMessage.objects.create(
            customer=customer,
            order=order,
            installation=installation,
            inspection=inspection,
            message_type=message_type,
            template_used=template,
            message_text=message_text,
            phone_number=f"+{self._format_phone_number(customer.phone)}",
            status='PENDING'
        )
        
        try:
            # وضع الاختبار
            if self.settings.test_mode:
                logger.info(f"TEST MODE: Would send message to {customer.phone}")
                whatsapp_message.status = 'SENT'
                whatsapp_message.external_id = f"TEST_{whatsapp_message.id}"
                whatsapp_message.sent_at = timezone.now()
                whatsapp_message.save()
                return whatsapp_message
            
            # الإرسال الفعلي
            result = self.send_text_message(customer.phone, message_text)
            
            # تحديث السجل
            if result.get('messages'):
                message_id = result['messages'][0].get('id')
                whatsapp_message.external_id = message_id
                whatsapp_message.status = 'SENT'
                whatsapp_message.sent_at = timezone.now()
            else:
                whatsapp_message.status = 'FAILED'
                whatsapp_message.error_message = str(result)
            
            whatsapp_message.save()
            return whatsapp_message
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            whatsapp_message.status = 'FAILED'
            whatsapp_message.error_message = str(e)
            whatsapp_message.save()
            return whatsapp_message
    
    def retry_failed_message(self, message_id):
        """
        إعادة محاولة إرسال رسالة فاشلة
        
        Args:
            message_id: معرف الرسالة
            
        Returns:
            bool: True إذا نجحت، False إذا فشلت
        """
        from .models import WhatsAppMessage
        
        try:
            message = WhatsAppMessage.objects.get(id=message_id)
            
            if message.status != 'FAILED':
                return False
            
            # إعادة تعيين الحالة
            message.status = 'PENDING'
            message.error_message = ''
            message.save()
            
            # إعادة الإرسال
            result = self.send_text_message(
                to=message.customer.phone,
                message=message.message_text
            )
            
            if result.get('messages'):
                message.status = 'SENT'
                message.external_id = result['messages'][0].get('id')
                message.sent_at = timezone.now()
            else:
                message.status = 'FAILED'
                message.error_message = str(result.get('error', 'Unknown error'))
            
            message.save()
            return message.status == 'SENT'
            
        except Exception as e:
            logger.error(f"Error retrying message {message_id}: {e}")
            return False
    
    def render_template(self, template, context):
        """تعبئة قالب بالبيانات"""
        text = template.template_text
        for key, value in context.items():
            text = text.replace(f'{{{key}}}', str(value))
        return text
