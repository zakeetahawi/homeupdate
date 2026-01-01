from django.test import TestCase
from django.utils import timezone
from unittest.mock import Mock, patch
from whatsapp.models import (
    WhatsAppSettings,
    WhatsAppMessageTemplate,
    WhatsAppMessage,
    WhatsAppNotificationRule
)
from whatsapp.services import WhatsAppService
from customers.models import Customer
from orders.models import Order


class WhatsAppSettingsTestCase(TestCase):
    """اختبارات نموذج WhatsAppSettings"""
    
    def setUp(self):
        self.settings = WhatsAppSettings.objects.create(
            api_provider='twilio',
            account_sid='TEST_SID',
            auth_token='TEST_TOKEN',
            phone_number='+14155238886',
            is_active=True,
            test_mode=True
        )
    
    def test_settings_creation(self):
        """اختبار إنشاء الإعدادات"""
        self.assertEqual(self.settings.api_provider, 'twilio')
        self.assertTrue(self.settings.is_active)
        self.assertTrue(self.settings.test_mode)
    
    def test_settings_str(self):
        """اختبار __str__"""
        expected = "WhatsApp Settings (twilio)"
        self.assertEqual(str(self.settings), expected)


class WhatsAppMessageTemplateTestCase(TestCase):
    """اختبارات نموذج WhatsAppMessageTemplate"""
    
    def setUp(self):
        self.template = WhatsAppMessageTemplate.objects.create(
            name='Test Template',
            message_type='ORDER_CREATED',
            template_text='Hello {customer_name}, order {order_number}',
            is_active=True
        )
    
    def test_template_creation(self):
        """اختبار إنشاء القالب"""
        self.assertEqual(self.template.name, 'Test Template')
        self.assertEqual(self.template.message_type, 'ORDER_CREATED')
        self.assertTrue(self.template.is_active)
    
    def test_template_str(self):
        """اختبار __str__"""
        self.assertIn('Test Template', str(self.template))


class WhatsAppServiceTestCase(TestCase):
    """اختبارات خدمة WhatsApp"""
    
    def setUp(self):
        # إنشاء إعدادات
        self.settings = WhatsAppSettings.objects.create(
            api_provider='twilio',
            account_sid='TEST_SID',
            auth_token='TEST_TOKEN',
            phone_number='+14155238886',
            is_active=True,
            test_mode=True
        )
        
        # إنشاء عميل
        self.customer = Customer.objects.create(
            name='Test Customer',
            phone='01234567890',
            email='test@example.com'
        )
        
        # إنشاء قالب
        self.template = WhatsAppMessageTemplate.objects.create(
            name='Test Template',
            message_type='ORDER_CREATED',
            template_text='Hello {customer_name}',
            is_active=True
        )
        
        self.service = WhatsAppService()
    
    def test_service_initialization(self):
        """اختبار تهيئة الخدمة"""
        self.assertIsNotNone(self.service.settings)
        self.assertEqual(self.service.settings.api_provider, 'twilio')
    
    def test_format_phone_number(self):
        """اختبار تنسيق رقم الهاتف"""
        # رقم مصري بدون رمز الدولة
        phone = self.service._format_phone_number('01234567890')
        self.assertEqual(phone, '+201234567890')
        
        # رقم مصري مع رمز الدولة
        phone = self.service._format_phone_number('201234567890')
        self.assertEqual(phone, '+201234567890')
        
        # رقم مع +
        phone = self.service._format_phone_number('+201234567890')
        self.assertEqual(phone, '+201234567890')
    
    def test_render_template(self):
        """اختبار تعبئة القالب"""
        context = {'customer_name': 'أحمد'}
        result = self.service.render_template(self.template, context)
        self.assertEqual(result, 'Hello أحمد')
    
    def test_send_message_test_mode(self):
        """اختبار إرسال رسالة في وضع الاختبار"""
        message = self.service.send_message(
            customer=self.customer,
            message_text='Test message',
            message_type='ORDER_CREATED'
        )
        
        self.assertIsNotNone(message)
        self.assertEqual(message.status, 'SENT')
        self.assertTrue(message.external_id.startswith('TEST_'))
        self.assertEqual(message.customer, self.customer)
    
    @patch('whatsapp.services.Client')
    def test_send_message_production_mode(self, mock_client):
        """اختبار إرسال رسالة في وضع الإنتاج"""
        # تعطيل وضع الاختبار
        self.settings.test_mode = False
        self.settings.save()
        
        # محاكاة Twilio Client
        mock_message = Mock()
        mock_message.sid = 'SM123456789'
        mock_client.return_value.messages.create.return_value = mock_message
        
        # إعادة تهيئة الخدمة
        service = WhatsAppService()
        
        message = service.send_message(
            customer=self.customer,
            message_text='Test message',
            message_type='ORDER_CREATED'
        )
        
        self.assertIsNotNone(message)
        self.assertEqual(message.external_id, 'SM123456789')


class WhatsAppMessageTestCase(TestCase):
    """اختبارات نموذج WhatsAppMessage"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            name='Test Customer',
            phone='01234567890',
            email='test@example.com'
        )
        
        self.message = WhatsAppMessage.objects.create(
            customer=self.customer,
            message_type='ORDER_CREATED',
            message_text='Test message',
            phone_number='+201234567890',
            status='PENDING'
        )
    
    def test_message_creation(self):
        """اختبار إنشاء الرسالة"""
        self.assertEqual(self.message.customer, self.customer)
        self.assertEqual(self.message.status, 'PENDING')
    
    def test_message_str(self):
        """اختبار __str__"""
        expected = f"{self.customer.name} - ORDER_CREATED (PENDING)"
        self.assertEqual(str(self.message), expected)


class WhatsAppNotificationRuleTestCase(TestCase):
    """اختبارات نموذج WhatsAppNotificationRule"""
    
    def setUp(self):
        self.template = WhatsAppMessageTemplate.objects.create(
            name='Test Template',
            message_type='ORDER_CREATED',
            template_text='Test',
            is_active=True
        )
        
        self.rule = WhatsAppNotificationRule.objects.create(
            event_type='ORDER_CREATED',
            is_enabled=True,
            template=self.template,
            delay_minutes=0
        )
    
    def test_rule_creation(self):
        """اختبار إنشاء القاعدة"""
        self.assertEqual(self.rule.event_type, 'ORDER_CREATED')
        self.assertTrue(self.rule.is_enabled)
        self.assertEqual(self.rule.template, self.template)
    
    def test_rule_str(self):
        """اختبار __str__"""
        self.assertIn('إنشاء طلب', str(self.rule))
        self.assertIn('مفعل', str(self.rule))
