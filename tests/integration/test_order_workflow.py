"""
Integration Tests for Order Workflow
"""
import pytest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from orders.services import OrderService
from customers.models import Customer

User = get_user_model()


class OrderWorkflowIntegrationTest(TransactionTestCase):
    """اختبارات تكامل لسير عمل الطلبات"""
    
    def setUp(self):
        """إعداد بيانات الاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.customer = Customer.objects.create(
            name='عميل تجريبي',
            phone='0123456789'
        )
    
    def test_create_order_workflow(self):
        """اختبار سير عمل إنشاء طلب كامل"""
        # بيانات الطلب
        items_data = [
            {
                'product_id': 1,
                'quantity': 2,
                'price': 100.0
            }
        ]
        
        # إنشاء الطلب
        order = OrderService.create_order(
            customer_id=self.customer.id,
            items_data=items_data,
            created_by=self.user,
            delivery_date='2026-02-01'
        )
        
        # التحقق من إنشاء الطلب
        self.assertIsNotNone(order)
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.status, 'pending')
        
        # التحقق من إنشاء أمر التصنيع
        self.assertTrue(hasattr(order, 'manufacturing_order'))
        
        # التحقق من إنشاء جدول التركيب
        self.assertTrue(hasattr(order, 'installation_schedule'))
    
    def test_cancel_order_workflow(self):
        """اختبار سير عمل إلغاء طلب"""
        # إنشاء طلب
        order = OrderService.create_order(
            customer_id=self.customer.id,
            items_data=[{'product_id': 1, 'quantity': 1, 'price': 50.0}],
            created_by=self.user
        )
        
        # إلغاء الطلب
        OrderService.cancel_order(
            order=order,
            reason='طلب العميل',
            cancelled_by=self.user
        )
        
        # التحقق من الإلغاء
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(order.cancellation_reason, 'طلب العميل')
