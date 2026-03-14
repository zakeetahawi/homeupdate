"""
اختبارات شاملة لـ Service Layer
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from customers.models import Customer
from orders.models import Order, OrderItem
from orders.services.order_service import OrderService, ContractService
from manufacturing.models import ManufacturingOrder
from installations.models import InstallationSchedule

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
        address="عنوان تجريبي",
    )


@pytest.mark.django_db
class TestOrderService:
    """اختبارات خدمة الطلبات"""

    def test_create_order_success(self, test_customer, test_user):
        """اختبار إنشاء طلب بنجاح"""
        items_data = [
            {"product_name": "منتج 1", "quantity": 2, "price": Decimal("100.00")},
            {"product_name": "منتج 2", "quantity": 1, "price": Decimal("200.00")},
        ]

        order = OrderService.create_order(
            customer_id=test_customer.id,
            items_data=items_data,
            created_by=test_user,
            notes="ملاحظات تجريبية",
        )

        assert order is not None
        assert order.customer == test_customer
        assert order.created_by == test_user
        assert order.status == "pending"
        assert order.items.count() == 2

    def test_create_order_creates_manufacturing_order(self, test_customer, test_user):
        """اختبار إنشاء أمر تصنيع تلقائياً"""
        items_data = [{"product_name": "منتج", "quantity": 1, "price": Decimal("100")}]

        order = OrderService.create_order(
            customer_id=test_customer.id, items_data=items_data, created_by=test_user
        )

        assert hasattr(order, "manufacturing_order")
        assert order.manufacturing_order.status == "pending"

    def test_create_order_creates_installation_schedule(
        self, test_customer, test_user
    ):
        """اختبار إنشاء جدول تركيب تلقائياً"""
        items_data = [{"product_name": "منتج", "quantity": 1, "price": Decimal("100")}]

        order = OrderService.create_order(
            customer_id=test_customer.id,
            items_data=items_data,
            created_by=test_user,
            installation_required=True,
        )

        assert hasattr(order, "installation_schedule")
        assert order.installation_schedule.status == "pending"

    def test_create_order_invalid_customer(self, test_user):
        """اختبار إنشاء طلب بعميل غير موجود"""
        items_data = [{"product_name": "منتج", "quantity": 1, "price": Decimal("100")}]

        with pytest.raises(ValidationError):
            OrderService.create_order(
                customer_id=99999,  # معرف غير موجود
                items_data=items_data,
                created_by=test_user,
            )

    def test_calculate_order_total(self, test_customer, test_user):
        """اختبار حساب إجمالي الطلب"""
        items_data = [
            {"product_name": "منتج 1", "quantity": 2, "price": Decimal("100.00")},
            {"product_name": "منتج 2", "quantity": 3, "price": Decimal("50.00")},
        ]

        order = OrderService.create_order(
            customer_id=test_customer.id, items_data=items_data, created_by=test_user
        )

        # تحديث total_price لكل عنصر
        for item in order.items.all():
            item.total_price = item.quantity * item.price
            item.save()

        total = OrderService.calculate_order_total(order)
        expected_total = (2 * 100) + (3 * 50)  # 200 + 150 = 350

        assert float(total) == float(expected_total)

    def test_cancel_order(self, test_customer, test_user):
        """اختبار إلغاء طلب"""
        items_data = [{"product_name": "منتج", "quantity": 1, "price": Decimal("100")}]

        order = OrderService.create_order(
            customer_id=test_customer.id, items_data=items_data, created_by=test_user
        )

        OrderService.cancel_order(
            order=order, reason="سبب الإلغاء", cancelled_by=test_user
        )

        order.refresh_from_db()
        assert order.status == "cancelled"
        assert order.cancellation_reason == "سبب الإلغاء"
        assert order.cancelled_by == test_user
        assert order.cancelled_at is not None

    def test_cancel_order_cancels_manufacturing(self, test_customer, test_user):
        """اختبار إلغاء أمر التصنيع عند إلغاء الطلب"""
        items_data = [{"product_name": "منتج", "quantity": 1, "price": Decimal("100")}]

        order = OrderService.create_order(
            customer_id=test_customer.id, items_data=items_data, created_by=test_user
        )

        OrderService.cancel_order(order=order, reason="إلغاء", cancelled_by=test_user)

        order.manufacturing_order.refresh_from_db()
        assert order.manufacturing_order.status == "cancelled"

    def test_cancel_order_cancels_installation(self, test_customer, test_user):
        """اختبار إلغاء جدول التركيب عند إلغاء الطلب"""
        items_data = [{"product_name": "منتج", "quantity": 1, "price": Decimal("100")}]

        order = OrderService.create_order(
            customer_id=test_customer.id,
            items_data=items_data,
            created_by=test_user,
            installation_required=True,
        )

        OrderService.cancel_order(order=order, reason="إلغاء", cancelled_by=test_user)

        order.installation_schedule.refresh_from_db()
        assert order.installation_schedule.status == "cancelled"

    def test_get_order_progress(self, test_customer, test_user):
        """اختبار الحصول على تقدم الطلب"""
        items_data = [{"product_name": "منتج", "quantity": 1, "price": Decimal("100")}]

        order = OrderService.create_order(
            customer_id=test_customer.id, items_data=items_data, created_by=test_user
        )

        progress = OrderService.get_order_progress(order)

        assert "order_status" in progress
        assert "manufacturing_status" in progress
        assert "installation_status" in progress
        assert "overall_progress" in progress
        assert progress["order_status"] == "pending"

    def test_validate_order_data_success(self):
        """اختبار التحقق من بيانات طلب صحيحة"""
        data = {
            "customer_id": 1,
            "items": [{"product": "منتج", "quantity": 1}],
            "delivery_date": timezone.now().date() + timezone.timedelta(days=7),
        }

        is_valid, error = OrderService.validate_order_data(data)

        assert is_valid is True
        assert error is None

    def test_validate_order_data_missing_customer(self):
        """اختبار التحقق من بيانات بدون عميل"""
        data = {"items": [{"product": "منتج", "quantity": 1}]}

        is_valid, error = OrderService.validate_order_data(data)

        assert is_valid is False
        assert "معرف العميل مطلوب" in error

    def test_validate_order_data_missing_items(self):
        """اختبار التحقق من بيانات بدون عناصر"""
        data = {"customer_id": 1, "items": []}

        is_valid, error = OrderService.validate_order_data(data)

        assert is_valid is False
        assert "عنصر واحد على الأقل" in error

    def test_validate_order_data_past_delivery_date(self):
        """اختبار التحقق من تاريخ تسليم في الماضي"""
        data = {
            "customer_id": 1,
            "items": [{"product": "منتج"}],
            "delivery_date": timezone.now().date() - timezone.timedelta(days=1),
        }

        is_valid, error = OrderService.validate_order_data(data)

        assert is_valid is False
        assert "المستقبل" in error


@pytest.mark.django_db
class TestContractService:
    """اختبارات خدمة العقود"""

    def test_create_contract_curtain(self, test_customer, test_user):
        """اختبار إنشاء ستارة عقد"""
        # إنشاء طلب أولاً
        items_data = [{"product_name": "منتج", "quantity": 1, "price": Decimal("100")}]
        order = OrderService.create_order(
            customer_id=test_customer.id, items_data=items_data, created_by=test_user
        )

        # إنشاء ستارة عقد
        curtain_data = {
            "name": "ستارة تجريبية",
            "width": Decimal("2.5"),
            "height": Decimal("3.0"),
        }

        curtain = ContractService.create_contract_curtain(
            order=order, curtain_data=curtain_data
        )

        assert curtain is not None
        assert curtain.order == order
        assert curtain.name == "ستارة تجريبية"
        assert curtain.width == Decimal("2.5")

    def test_calculate_curtain_cost_zero_when_empty(self, test_customer, test_user):
        """اختبار حساب تكلفة ستارة بدون أقمشة أو إكسسوارات"""
        items_data = [{"product_name": "منتج", "quantity": 1, "price": Decimal("100")}]
        order = OrderService.create_order(
            customer_id=test_customer.id, items_data=items_data, created_by=test_user
        )

        curtain_data = {"name": "ستارة"}
        curtain = ContractService.create_contract_curtain(
            order=order, curtain_data=curtain_data
        )

        cost = ContractService.calculate_curtain_cost(curtain)

        assert float(cost) == 0.0


@pytest.mark.django_db
class TestOrderServiceIntegration:
    """اختبارات تكامل شاملة"""

    def test_complete_order_workflow(self, test_customer, test_user):
        """اختبار سير عمل الطلب الكامل"""
        # 1. إنشاء طلب
        items_data = [
            {"product_name": "منتج 1", "quantity": 2, "price": Decimal("100")},
        ]

        order = OrderService.create_order(
            customer_id=test_customer.id,
            items_data=items_data,
            created_by=test_user,
            installation_required=True,
        )

        # 2. التحقق من الإنشاء
        assert order.status == "pending"
        assert hasattr(order, "manufacturing_order")
        assert hasattr(order, "installation_schedule")

        # 3. الحصول على التقدم
        progress = OrderService.get_order_progress(order)
        assert progress["overall_progress"] >= 0

        # 4. حساب الإجمالي
        for item in order.items.all():
            item.total_price = item.quantity * item.price
            item.save()

        total = OrderService.calculate_order_total(order)
        assert float(total) == 200.0

        # 5. الإلغاء
        OrderService.cancel_order(order=order, reason="اختبار", cancelled_by=test_user)

        order.refresh_from_db()
        assert order.status == "cancelled"
        assert order.manufacturing_order.status == "cancelled"
        assert order.installation_schedule.status == "cancelled"
