import os
import sys
import django
from datetime import datetime, timedelta
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files import File

# إعداد بيئة Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order, OrderItem
from products.models import Product
from customers.models import Customer
from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem

User = get_user_model()

class ManufacturingIntegrationTest(TestCase):
    """
    فئة اختبار تكامل أوامر التصنيع مع الطلبات
    """
    
    def setUp(self):
        """تهيئة بيانات الاختبار"""
        # إنشاء مستخدم للاختبار
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        
        # إنشاء عميل للاختبار
        self.customer = Customer.objects.create(
            name='عميل اختباري',
            phone='+966501234567',
            email='test@example.com'
        )
        
        # إنشاء منتج للاختبار
        self.product = Product.objects.create(
            name='منتج اختباري',
            sku='TEST001',
            price=1000.00,
            product_type='installation'  # نوع التركيب للاختبار
        )
        
        # إنشاء طلب اختباري
        self.order = Order.objects.create(
            customer=self.customer,
            order_type='installation',
            contract_number='CONTRACT-001',
            order_date=datetime.now().date(),
            expected_delivery_date=(datetime.now() + timedelta(days=14)).date(),
            status='pending',
            created_by=self.user
        )
        
        # إضافة عنصر للطلب
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price=1000.00,
            specifications='مواصفات اختبارية',
            status='pending'
        )
        
        # تسجيل الدخول كمسؤول
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_manufacturing_order_creation(self):
        """
        اختبار إنشاء أمر تصنيع تلقائي عند إنشاء طلب جديد
        """
        # التأكد من عدم وجود أوامر تصنيع
        self.assertEqual(ManufacturingOrder.objects.count(), 0)
        
        # إنشاء طلب جديد من نوع تركيب
        new_order = Order.objects.create(
            customer=self.customer,
            order_type='installation',
            contract_number='CONTRACT-TEST-001',
            order_date=datetime.now().date(),
            expected_delivery_date=(datetime.now() + timedelta(days=10)).date(),
            status='pending',
            created_by=self.user
        )
        
        # إضافة عنصر للطلب
        OrderItem.objects.create(
            order=new_order,
            product=self.product,
            quantity=2,
            unit_price=1500.00,
            specifications='مواصفات اختبارية للطلب الجديد'
        )
        
        # التحقق من إنشاء أمر التصنيع تلقائياً
        self.assertEqual(ManufacturingOrder.objects.count(), 1)
        manufacturing_order = ManufacturingOrder.objects.first()
        self.assertEqual(manufacturing_order.order, new_order)
        self.assertEqual(manufacturing_order.status, 'pending')
        
        # التحقق من عناصر أمر التصنيع
        self.assertEqual(manufacturing_order.items.count(), 1)
        item = manufacturing_order.items.first()
        self.assertEqual(item.product_name, self.product.name)
        self.assertEqual(item.quantity, 2)
    
    def test_order_status_update_when_manufacturing_completed(self):
        """
        اختبار تحديث حالة الطلب عند اكتمال التصنيع
        """
        # إنشاء أمر تصنيع يدوياً
        manufacturing_order = ManufacturingOrder.objects.create(
            order=self.order,
            order_type='installation',
            contract_number=self.order.contract_number,
            order_date=self.order.order_date,
            expected_delivery_date=self.order.expected_delivery_date,
            status='in_progress'
        )
        
        # إضافة عنصر لأمر التصنيع
        ManufacturingOrderItem.objects.create(
            manufacturing_order=manufacturing_order,
            product_name=self.product.name,
            quantity=1,
            specifications='مواصفات اختبارية',
            status='in_progress'
        )
        
        # تحديث حالة عنصر أمر التصنيع إلى مكتمل
        item = manufacturing_order.items.first()
        item.status = 'completed'
        item.save()
        
        # تحديث حالة أمر التصنيع يدوياً (يجب أن يتم تلقائياً عبر الإشارات)
        manufacturing_order.refresh_from_db()
        
        # التحقق من تحديث حالة أمر التصنيع
        self.assertEqual(manufacturing_order.status, 'completed')
        
        # التحقق من تحديث حالة الطلب الأصلي
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'ready_for_installation')
    
    def test_manufacturing_order_ui(self):
        """
        اختبار واجهة المستخدم لأوامر التصنيع
        """
        # إنشاء أمر تصنيع للاختبار
        manufacturing_order = ManufacturingOrder.objects.create(
            order=self.order,
            order_type='installation',
            contract_number=self.order.contract_number,
            order_date=self.order.order_date,
            expected_delivery_date=self.order.expected_delivery_date,
            status='pending'
        )
        
        # اختبار صفحة قائمة أوامر التصنيع
        response = self.client.get(reverse('manufacturing:order_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, manufacturing_order.contract_number)
        
        # اختبار صفحة تفاصيل أمر التصنيع
        detail_url = reverse('manufacturing:order_detail', args=[manufacturing_order.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, manufacturing_order.contract_number)
    
    def test_manufacturing_order_status_update_api(self):
        """
        اختبار واجهة برمجة التطبيقات لتحديث حالة أمر التصنيع
        """
        # إنشاء أمر تصنيع للاختبار
        manufacturing_order = ManufacturingOrder.objects.create(
            order=self.order,
            order_type='installation',
            contract_number=self.order.contract_number,
            order_date=self.order.order_date,
            expected_delivery_date=self.order.expected_delivery_date,
            status='pending'
        )
        
        # تحديث حالة أمر التصنيع عبر واجهة برمجة التطبيقات
        update_url = reverse('manufacturing:api_update_order_status', args=[manufacturing_order.id])
        response = self.client.post(
            update_url,
            {'status': 'in_progress'},
            content_type='application/json'
        )
        
        # التحقق من نجاح التحديث
        self.assertEqual(response.status_code, 200)
        manufacturing_order.refresh_from_db()
        self.assertEqual(manufacturing_order.status, 'in_progress')
        
        # التحقق من تحديث حالة الطلب الأصلي
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'in_progress')


if __name__ == '__main__':
    import unittest
    unittest.main()
