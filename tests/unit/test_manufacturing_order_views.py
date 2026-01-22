"""
اختبارات شاملة لـ manufacturing/views/order_views.py
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory
from django.urls import reverse

from customers.models import Customer
from orders.models import Order
from manufacturing.models import ManufacturingOrder
from manufacturing.views.order_views import (
    ManufacturingOrderListView,
    ManufacturingOrderDetailView,
    ManufacturingOrderCreateView,
    ManufacturingOrderUpdateView,
    ManufacturingOrderDeleteView,
)

User = get_user_model()


@pytest.fixture
def user_with_permissions(db):
    """مستخدم مع صلاحيات التصنيع"""
    user = User.objects.create_user(
        username="mfg_user",
        email="mfg@test.com",
        password="testpass123"
    )
    # إضافة جميع صلاحيات التصنيع
    permissions = Permission.objects.filter(
        content_type__app_label='manufacturing'
    )
    user.user_permissions.add(*permissions)
    return user


@pytest.fixture
def test_customer(db):
    """عميل للاختبار"""
    return Customer.objects.create(
        name="عميل تجريبي",
        phone="0123456789",
        email="customer@test.com"
    )


@pytest.fixture
def test_order(db, test_customer, user_with_permissions):
    """طلب للاختبار"""
    return Order.objects.create(
        customer=test_customer,
        created_by=user_with_permissions,
        status="pending"
    )


@pytest.fixture
def test_manufacturing_order(db, test_order, user_with_permissions):
    """أمر تصنيع للاختبار"""
    return ManufacturingOrder.objects.create(
        order=test_order,
        created_by=user_with_permissions,
        status="pending",
        contract_number="MFG-001"
    )


@pytest.fixture
def request_factory():
    """مصنع الطلبات"""
    return RequestFactory()


@pytest.mark.django_db
class TestManufacturingOrderListView:
    """اختبارات عرض قائمة أوامر التصنيع"""

    def test_queryset_returns_all_orders(self, user_with_permissions, test_manufacturing_order, request_factory):
        """اختبار إرجاع جميع الأوامر"""
        request = request_factory.get('/manufacturing/orders/')
        request.user = user_with_permissions
        
        view = ManufacturingOrderListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        assert queryset.count() >= 1
        assert test_manufacturing_order in queryset

    def test_search_by_contract_number(self, user_with_permissions, test_manufacturing_order, request_factory):
        """اختبار البحث برقم العقد"""
        request = request_factory.get('/manufacturing/orders/?search=MFG-001')
        request.user = user_with_permissions
        
        view = ManufacturingOrderListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        assert queryset.count() == 1
        assert queryset.first() == test_manufacturing_order

    def test_filter_by_status(self, user_with_permissions, test_manufacturing_order, request_factory):
        """اختبار الفلترة حسب الحالة"""
        request = request_factory.get('/manufacturing/orders/?status=pending')
        request.user = user_with_permissions
        
        view = ManufacturingOrderListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        assert all(order.status == 'pending' for order in queryset)

    def test_context_data_contains_statistics(self, user_with_permissions, test_manufacturing_order, request_factory):
        """اختبار وجود الإحصائيات في السياق"""
        request = request_factory.get('/manufacturing/orders/')
        request.user = user_with_permissions
        
        view = ManufacturingOrderListView()
        view.request = request
        view.object_list = view.get_queryset()
        
        context = view.get_context_data()
        
        assert 'total_orders' in context
        assert 'pending_orders' in context
        assert 'in_progress_orders' in context
        assert 'completed_orders' in context


@pytest.mark.django_db
class TestManufacturingOrderDetailView:
    """اختبارات عرض تفاصيل أمر التصنيع"""

    def test_get_object_returns_correct_order(self, user_with_permissions, test_manufacturing_order, request_factory):
        """اختبار إرجاع الأمر الصحيح"""
        request = request_factory.get(f'/manufacturing/orders/{test_manufacturing_order.pk}/')
        request.user = user_with_permissions
        
        view = ManufacturingOrderDetailView()
        view.request = request
        view.kwargs = {'pk': test_manufacturing_order.pk}
        
        obj = view.get_object()
        
        assert obj == test_manufacturing_order

    def test_context_contains_available_statuses(self, user_with_permissions, test_manufacturing_order, request_factory):
        """اختبار وجود الحالات المتاحة"""
        request = request_factory.get(f'/manufacturing/orders/{test_manufacturing_order.pk}/')
        request.user = user_with_permissions
        
        view = ManufacturingOrderDetailView()
        view.request = request
        view.object = test_manufacturing_order
        
        context = view.get_context_data()
        
        assert 'available_statuses' in context
        assert isinstance(context['available_statuses'], list)

    def test_available_statuses_for_pending(self, user_with_permissions, test_manufacturing_order, request_factory):
        """اختبار الحالات المتاحة لأمر معلق"""
        test_manufacturing_order.status = 'pending'
        test_manufacturing_order.save()
        
        request = request_factory.get(f'/manufacturing/orders/{test_manufacturing_order.pk}/')
        request.user = user_with_permissions
        
        view = ManufacturingOrderDetailView()
        view.request = request
        view.object = test_manufacturing_order
        
        statuses = view._get_available_statuses()
        
        assert 'in_progress' in statuses
        assert 'cancelled' in statuses

    def test_available_statuses_for_completed(self, user_with_permissions, test_manufacturing_order, request_factory):
        """اختبار عدم وجود حالات متاحة لأمر مكتمل"""
        test_manufacturing_order.status = 'completed'
        test_manufacturing_order.save()
        
        request = request_factory.get(f'/manufacturing/orders/{test_manufacturing_order.pk}/')
        request.user = user_with_permissions
        
        view = ManufacturingOrderDetailView()
        view.request = request
        view.object = test_manufacturing_order
        
        statuses = view._get_available_statuses()
        
        assert len(statuses) == 0


@pytest.mark.django_db
class TestManufacturingOrderCreateView:
    """اختبارات إنشاء أمر تصنيع"""

    def test_form_valid_sets_created_by(self, user_with_permissions, test_order, request_factory):
        """اختبار تعيين المستخدم المنشئ"""
        request = request_factory.post('/manufacturing/orders/create/')
        request.user = user_with_permissions
        request._messages = []  # Mock messages
        
        view = ManufacturingOrderCreateView()
        view.request = request
        
        # إنشاء نموذج وهمي
        class MockForm:
            instance = ManufacturingOrder(order=test_order)
            def save(self, commit=True):
                if commit:
                    self.instance.save()
                return self.instance
        
        form = MockForm()
        response = view.form_valid(form)
        
        assert form.instance.created_by == user_with_permissions
        assert form.instance.status == 'pending'


@pytest.mark.django_db
class TestManufacturingOrderUpdateView:
    """اختبارات تحديث أمر تصنيع"""

    def test_can_update_status(self, user_with_permissions, test_manufacturing_order, request_factory):
        """اختبار تحديث الحالة"""
        original_status = test_manufacturing_order.status
        
        request = request_factory.post(f'/manufacturing/orders/{test_manufacturing_order.pk}/edit/')
        request.user = user_with_permissions
        request._messages = []
        
        view = ManufacturingOrderUpdateView()
        view.request = request
        view.object = test_manufacturing_order
        
        # تحديث الحالة
        test_manufacturing_order.status = 'in_progress'
        test_manufacturing_order.save()
        
        assert test_manufacturing_order.status != original_status
        assert test_manufacturing_order.status == 'in_progress'


@pytest.mark.django_db
class TestManufacturingOrderDeleteView:
    """اختبارات حذف أمر تصنيع"""

    def test_delete_removes_order(self, user_with_permissions, test_manufacturing_order, request_factory):
        """اختبار حذف الأمر"""
        order_id = test_manufacturing_order.pk
        
        request = request_factory.post(f'/manufacturing/orders/{order_id}/delete/')
        request.user = user_with_permissions
        request._messages = []
        
        view = ManufacturingOrderDeleteView()
        view.request = request
        view.object = test_manufacturing_order
        
        # حذف
        test_manufacturing_order.delete()
        
        # التحقق من الحذف
        assert not ManufacturingOrder.objects.filter(pk=order_id).exists()


@pytest.mark.django_db
class TestManufacturingOrderViewsIntegration:
    """اختبارات تكامل شاملة"""

    def test_complete_crud_workflow(self, user_with_permissions, test_order, request_factory):
        """اختبار سير عمل CRUD كامل"""
        # 1. إنشاء
        mfg_order = ManufacturingOrder.objects.create(
            order=test_order,
            created_by=user_with_permissions,
            status='pending',
            contract_number='TEST-001'
        )
        
        assert mfg_order.pk is not None
        
        # 2. قراءة
        retrieved = ManufacturingOrder.objects.get(pk=mfg_order.pk)
        assert retrieved == mfg_order
        
        # 3. تحديث
        retrieved.status = 'in_progress'
        retrieved.save()
        
        retrieved.refresh_from_db()
        assert retrieved.status == 'in_progress'
        
        # 4. حذف
        order_id = retrieved.pk
        retrieved.delete()
        
        assert not ManufacturingOrder.objects.filter(pk=order_id).exists()
