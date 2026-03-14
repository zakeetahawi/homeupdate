"""
اختبارات شاملة لـ manufacturing/utils.py
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model

from customers.models import Customer
from orders.models import Order
from orders.contract_models import ContractCurtain, CurtainFabric, CurtainAccessory
from manufacturing.utils import get_material_summary_context
from inventory.models import Product, Category

User = get_user_model()


@pytest.fixture
def test_user(db):
    """إنشاء مستخدم للاختبار"""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def test_customer(db):
    """إنشاء عميل للاختبار"""
    return Customer.objects.create(
        name="عميل تجريبي",
        phone="0123456789",
        email="customer@test.com",
    )


@pytest.fixture
def test_category(db):
    """إنشاء فئة للاختبار"""
    return Category.objects.create(name="أقمشة")


@pytest.fixture
def test_product(db, test_category):
    """إنشاء منتج للاختبار"""
    return Product.objects.create(
        name="قماش تجريبي",
        code="FAB001",
        category=test_category,
        price=Decimal("100.00"),
    )


@pytest.mark.django_db
class TestGetMaterialSummaryContext:
    """اختبارات دالة get_material_summary_context"""

    def test_returns_dict(self, test_customer, test_user):
        """اختبار أن الدالة ترجع قاموس"""
    
    def test_handles_empty_order(self):
        """اختبار التعامل مع طلب فارغ"""
        order = Order.objects.create(customer_id=1)
        result = get_material_summary_context(order)
        
        self.assertEqual(len(result['materials_summary']), 0)
        self.assertEqual(result['grand_total_quantity'], 0.0)
        self.assertEqual(result['grand_total_sewing'], 0.0)
