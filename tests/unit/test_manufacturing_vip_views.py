"""
اختبارات شاملة لـ manufacturing/views/vip_views.py
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory

from customers.models import Customer
from orders.models import Order
from manufacturing.models import ManufacturingOrder
from manufacturing.views.vip_views import VIPOrdersListView

User = get_user_model()


@pytest.fixture
def user_with_permissions(db):
    """مستخدم مع صلاحيات"""
    user = User.objects.create_user(
        username="vip_user",
        email="vip@test.com",
        password="testpass123"
    )
    permissions = Permission.objects.filter(
        content_type__app_label='manufacturing'
    )
    user.user_permissions.add(*permissions)
    return user


@pytest.fixture
def vip_customer(db):
    """عميل VIP"""
    return Customer.objects.create(
        name="عميل VIP",
        phone="0111111111",
        email="vip@customer.com",
        is_vip=True
    )


@pytest.fixture
def regular_customer(db):
    """عميل عادي"""
    return Customer.objects.create(
        name="عميل عادي",
        phone="0122222222",
        email="regular@customer.com",
        is_vip=False
    )


@pytest.fixture
def vip_order(db, vip_customer, user_with_permissions):
    """طلب VIP"""
    order = Order.objects.create(
        customer=vip_customer,
        created_by=user_with_permissions,
        status="pending",
        priority="high"
    )
    return ManufacturingOrder.objects.create(
        order=order,
        created_by=user_with_permissions,
        status="pending"
    )


@pytest.fixture
def regular_order(db, regular_customer, user_with_permissions):
    """طلب عادي"""
    order = Order.objects.create(
        customer=regular_customer,
        created_by=user_with_permissions,
        status="pending",
        priority="normal"
    )
    return ManufacturingOrder.objects.create(
        order=order,
        created_by=user_with_permissions,
        status="pending"
    )


@pytest.fixture
def urgent_order(db, regular_customer, user_with_permissions):
    """طلب عاجل"""
    order = Order.objects.create(
        customer=regular_customer,
        created_by=user_with_permissions,
        status="pending",
        is_urgent=True
    )
    return ManufacturingOrder.objects.create(
        order=order,
        created_by=user_with_permissions,
        status="pending"
    )


@pytest.fixture
def request_factory():
    """مصنع الطلبات"""
    return RequestFactory()


@pytest.mark.django_db
class TestVIPOrdersListView:
    """اختبارات عرض طلبات VIP"""

    def test_queryset_includes_vip_customers(self, user_with_permissions, vip_order, regular_order, request_factory):
        """اختبار تضمين عملاء VIP فقط"""
        request = request_factory.get('/manufacturing/vip-orders/')
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        assert vip_order in queryset
        assert regular_order not in queryset

    def test_queryset_includes_high_priority_orders(self, user_with_permissions, vip_order, request_factory):
        """اختبار تضمين الطلبات ذات الأولوية العالية"""
        request = request_factory.get('/manufacturing/vip-orders/')
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        assert vip_order in queryset
        assert vip_order.order.priority == 'high'

    def test_queryset_includes_urgent_orders(self, user_with_permissions, urgent_order, regular_order, request_factory):
        """اختبار تضمين الطلبات العاجلة"""
        request = request_factory.get('/manufacturing/vip-orders/')
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        assert urgent_order in queryset
        assert regular_order not in queryset

    def test_search_filters_vip_orders(self, user_with_permissions, vip_order, request_factory):
        """اختبار البحث في طلبات VIP"""
        request = request_factory.get(f'/manufacturing/vip-orders/?search={vip_order.order.customer.name}')
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        assert queryset.count() >= 1
        assert vip_order in queryset

    def test_status_filter_works(self, user_with_permissions, vip_order, request_factory):
        """اختبار فلترة الحالة"""
        vip_order.status = 'in_progress'
        vip_order.save()
        
        request = request_factory.get('/manufacturing/vip-orders/?status=in_progress')
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        assert all(order.status == 'in_progress' for order in queryset)

    def test_context_contains_vip_statistics(self, user_with_permissions, vip_order, urgent_order, request_factory):
        """اختبار وجود إحصائيات VIP"""
        request = request_factory.get('/manufacturing/vip-orders/')
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        view.object_list = view.get_queryset()
        
        context = view.get_context_data()
        
        assert 'total_vip_orders' in context
        assert 'pending_vip' in context
        assert 'in_progress_vip' in context
        assert 'urgent_orders' in context

    def test_vip_statistics_are_accurate(self, user_with_permissions, vip_order, urgent_order, request_factory):
        """اختبار دقة إحصائيات VIP"""
        request = request_factory.get('/manufacturing/vip-orders/')
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        view.object_list = view.get_queryset()
        
        context = view.get_context_data()
        
        assert context['total_vip_orders'] >= 2  # vip_order + urgent_order
        assert context['urgent_orders'] >= 1  # urgent_order

    def test_empty_queryset_when_no_vip_orders(self, user_with_permissions, regular_order, request_factory):
        """اختبار قائمة فارغة عند عدم وجود طلبات VIP"""
        request = request_factory.get('/manufacturing/vip-orders/')
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        # يجب ألا يحتوي على الطلب العادي
        assert regular_order not in queryset

    def test_pagination_works(self, user_with_permissions, vip_customer, request_factory):
        """اختبار التقسيم إلى صفحات"""
        # إنشاء عدة طلبات VIP
        for i in range(30):
            order = Order.objects.create(
                customer=vip_customer,
                created_by=user_with_permissions,
                status="pending"
            )
            ManufacturingOrder.objects.create(
                order=order,
                created_by=user_with_permissions,
                status="pending"
            )
        
        request = request_factory.get('/manufacturing/vip-orders/')
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        # يجب أن يكون هناك أكثر من 25 (حجم الصفحة)
        assert queryset.count() > 25


@pytest.mark.django_db
class TestVIPOrdersIntegration:
    """اختبارات تكامل طلبات VIP"""

    def test_vip_and_urgent_orders_both_included(
        self, user_with_permissions, vip_order, urgent_order, regular_order, request_factory
    ):
        """اختبار تضمين كل من VIP والعاجل"""
        request = request_factory.get('/manufacturing/vip-orders/')
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        assert vip_order in queryset
        assert urgent_order in queryset
        assert regular_order not in queryset

    def test_search_and_filter_combined(
        self, user_with_permissions, vip_order, request_factory
    ):
        """اختبار البحث والفلترة معاً"""
        vip_order.status = 'pending'
        vip_order.save()
        
        request = request_factory.get(
            f'/manufacturing/vip-orders/?search={vip_order.order.customer.name}&status=pending'
        )
        request.user = user_with_permissions
        
        view = VIPOrdersListView()
        view.request = request
        
        queryset = view.get_queryset()
        
        assert vip_order in queryset
        assert all(order.status == 'pending' for order in queryset)
