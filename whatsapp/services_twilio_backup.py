```python
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.utils import timezone
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from .models import WhatsAppSettings, WhatsAppMessage, WhatsAppMessageTemplate
import qrcode
from io import BytesIO
import base64
from .meta_cloud_service import MetaCloudService # New import

logger = logging.getLogger(__name__)


class WhatsAppService:
    """خدمة WhatsApp موحدة تدعم عدة مزودين""" # Updated docstring
    
    def __init__(self):
    def _initialize_client(self):
        """تهيئة عميل Twilio"""
        if not self.settings:
            return
        
        try:
            if self.settings.api_provider == 'twilio':
                self.client = Client(
                    self.settings.account_sid,
                    self.settings.auth_token
                )
        except Exception as e:
            logger.error(f"Error initializing Twilio client: {e}")
    
    def send_message(
        self,
        customer,
        message_text: str,
        message_type: str,
        order=None,
        installation=None,
        inspection=None,
        template: Optional[WhatsAppMessageTemplate] = None,
        attachments: Optional[Dict] = None
    ) -> Optional[WhatsAppMessage]:
        """
        إرسال رسالة WhatsApp
        
        Args:
            customer: كائن العميل
            message_text: نص الرسالة
            message_type: نوع الرسالة
            order: الطلب (اختياري)
            installation: التركيب (اختياري)
            inspection: المعاينة (اختياري)
            template: القالب المستخدم (اختياري)
            attachments: المرفقات (اختياري)
        
        Returns:
            كائن WhatsAppMessage أو None في حالة الفشل
        """
        if not self.settings or not self.settings.is_active:
            logger.warning("WhatsApp service is not active")
            return None
        
        if not self.client:
            logger.error("Twilio client not initialized")
            return None
        
        # الحصول على رقم الهاتف
        phone_number = self._format_phone_number(customer.phone)
        if not phone_number:
            logger.error(f"Invalid phone number for customer {customer.id}")
            return None
        
        # إنشاء سجل الرسالة
        whatsapp_message = WhatsAppMessage.objects.create(
            customer=customer,
            order=order,
            installation=installation,
            inspection=inspection,
            message_type=message_type,
            template_used=template,
            message_text=message_text,
            phone_number=phone_number,
            status='PENDING',
            attachments=attachments or {}
        )
        
        try:
            # إرسال الرسالة
            if self.settings.test_mode:
                # في وضع الاختبار، لا نرسل فعلياً
                logger.info(f"TEST MODE: Would send message to {phone_number}")
                whatsapp_message.status = 'SENT'
                whatsapp_message.external_id = f"TEST_{whatsapp_message.id}"
                whatsapp_message.sent_at = timezone.now()
            else:
                # إرسال فعلي عبر Twilio
                message = self._send_via_twilio(
                    phone_number,
                    message_text,
                    attachments
                )
                
                whatsapp_message.status = 'SENT'
                whatsapp_message.external_id = message.sid
                whatsapp_message.sent_at = timezone.now()
            
            whatsapp_message.save()
            logger.info(f"WhatsApp message sent successfully to {customer.name}")
            return whatsapp_message
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            whatsapp_message.status = 'FAILED'
            whatsapp_message.error_message = str(e)
            whatsapp_message.save()
            return whatsapp_message
    
    def _send_via_twilio(
        self,
        to_number: str,
        message_text: str,
        attachments: Optional[Dict] = None
    ):
        """إرسال رسالة عبر Twilio"""
        from_number = f"whatsapp:{self.settings.phone_number}"
        to_number = f"whatsapp:{to_number}"
        
        message_params = {
            'from_': from_number,
            'to': to_number,
            'body': message_text
        }
        
        # إضافة المرفقات إن وجدت
        if attachments and 'media_url' in attachments:
            message_params['media_url'] = [attachments['media_url']]
        
        return self.client.messages.create(**message_params)
    
    def _format_phone_number(self, phone: str) -> Optional[str]:
        """تنسيق رقم الهاتف للصيغة الدولية"""
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
        
        # إضافة + في البداية
        if not phone.startswith('+'):
            phone = '+' + phone
        
        return phone
    
    def generate_qr_code(self, data: str) -> str:
        """
        توليد QR Code وإرجاعه كـ base64
        
        Args:
            data: البيانات المراد تحويلها لـ QR Code
        
        Returns:
            QR Code كـ base64 string
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # تحويل الصورة إلى base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def render_template(
        self,
        template: WhatsAppMessageTemplate,
        context: Dict[str, Any]
    ) -> str:
        """
        تعبئة قالب الرسالة بالمتغيرات
        
        Args:
            template: قالب الرسالة
            context: قاموس المتغيرات
        
        Returns:
            نص الرسالة المعبأ
        """
        message_text = template.template_text
        
        # استبدال المتغيرات
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in message_text:
                message_text = message_text.replace(placeholder, str(value))
        
        return message_text
    
    def retry_failed_message(self, message_id: int) -> bool:
        """
        إعادة محاولة إرسال رسالة فاشلة
        
        Args:
            message_id: معرف الرسالة
        
        Returns:
            True إذا نجحت الإعادة، False otherwise
        """
        try:
            message = WhatsAppMessage.objects.get(id=message_id)
            
            if message.status != 'FAILED':
                logger.warning(f"Message {message_id} is not in FAILED status")
                return False
            
            if message.retry_count >= self.settings.max_retry_attempts:
                logger.warning(f"Message {message_id} exceeded max retry attempts")
                return False
            
            # إعادة الإرسال
            message.retry_count += 1
            message.status = 'PENDING'
            message.error_message = ''
            message.save()
            
            # إرسال الرسالة
            result = self.send_message(
                customer=message.customer,
                message_text=message.message_text,
                message_type=message.message_type,
                order=message.order,
                installation=message.installation,
                inspection=message.inspection,
                template=message.template_used,
                attachments=message.attachments
            )
            
            return result is not None and result.status == 'SENT'
            
        except Exception as e:
            logger.error(f"Error retrying message {message_id}: {e}")
            return False
