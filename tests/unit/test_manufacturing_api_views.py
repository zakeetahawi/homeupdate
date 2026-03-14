"""
اختبارات شاملة لـ manufacturing/views/api_views.py
"""

import pytest
import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, Client

from customers.models import Customer
from orders.models import Order
from manufacturing.models import ManufacturingOrder

User = get_user_model()


@pytest.fixture
def user_with_permissions(db):
    """مستخدم مع صلاحيات"""
    user = User.objects.create_user(
        username="api_user",
        email="api@test.com",
        password="testpass123"
    )
    permissions = Permission.objects.filter(
        content_type__app_label='manufacturing'
    )
    user.user_permissions.add(*permissions)
    return user


@pytest.fixture
def test_customer(db):
    """عميل للاختبار"""
    return Customer.objects.create(
        name="عميل API",
        phone="0123456789",
        email="api@customer.com"
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
        contract_number="API-001"
    )


@pytest.fixture
def client_logged_in(user_with_permissions):
    """عميل مسجل دخول"""
    client = Client()
    client.force_login(user_with_permissions)
    return client


@pytest.mark.django_db
class TestManufacturingOrderAPI:
    """اختبارات API أمر التصنيع"""

    def test_get_order_returns_json(self, client_logged_in, test_manufacturing_order):
        """اختبار إرجاع JSON"""
        response = client_logged_in.get(f'/manufacturing/api/orders/{test_manufacturing_order.pk}/')
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

    def test_get_order_contains_correct_data(self, client_logged_in, test_manufacturing_order):
        """اختبار البيانات الصحيحة"""
        response = client_logged_in.get(f'/manufacturing/api/orders/{test_manufacturing_order.pk}/')
        data = response.json()
        
        assert data['id'] == test_manufacturing_order.pk
        assert data['contract_number'] == "API-001"
        assert data['status'] == "pending"

    def test_get_nonexistent_order_returns_404(self, client_logged_in):
        """اختبار طلب غير موجود"""
        response = client_logged_in.get('/manufacturing/api/orders/99999/')
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestUpdateStatusAPI:
    """اختبارات API تحديث الحالة"""

    def test_update_status_success(self, client_logged_in, test_manufacturing_order):
        """اختبار تحديث ناجح"""
        response = client_logged_in.post(
            f'/manufacturing/api/orders/{test_manufacturing_order.pk}/update-status/',
            {'status': 'in_progress'}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['new_status'] == 'in_progress'

    def test_update_status_changes_database(self, client_logged_in, test_manufacturing_order):
        """اختبار تغيير قاعدة البيانات"""
        client_logged_in.post(
            f'/manufacturing/api/orders/{test_manufacturing_order.pk}/update-status/',
            {'status': 'completed'}
        )
        
        test_manufacturing_order.refresh_from_db()
        assert test_manufacturing_order.status == 'completed'

    def test_update_with_invalid_status_returns_error(self, client_logged_in, test_manufacturing_order):
        """اختبار حالة غير صالحة"""
        response = client_logged_in.post(
            f'/manufacturing/api/orders/{test_manufacturing_order.pk}/update-status/',
            {'status': 'invalid_status'}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data

    def test_update_without_status_returns_error(self, client_logged_in, test_manufacturing_order):
        """اختبار بدون حالة"""
        response = client_logged_in.post(
            f'/manufacturing/api/orders/{test_manufacturing_order.pk}/update-status/',
            {}
        )
        
        assert response.status_code == 400


@pytest.mark.django_db
class TestStatisticsAPI:
    """اختبارات API الإحصائيات"""

    def test_statistics_returns_json(self, client_logged_in):
        """اختبار إرجاع JSON"""
        response = client_logged_in.get('/manufacturing/api/statistics/')
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

    def test_statistics_contains_all_fields(self, client_logged_in, test_manufacturing_order):
        """اختبار وجود جميع الحقول"""
        response = client_logged_in.get('/manufacturing/api/statistics/')
        data = response.json()
        
        assert 'total_orders' in data
        assert 'pending' in data
        assert 'in_progress' in data
        assert 'completed' in data
        assert 'cancelled' in data

    def test_statistics_are_accurate(self, client_logged_in, test_manufacturing_order):
        """اختبار دقة الإحصائيات"""
        response = client_logged_in.get('/manufacturing/api/statistics/')
        data = response.json()
        
        assert data['total_orders'] >= 1
        assert data['pending'] >= 1


@pytest.mark.django_db
class TestOrderItemsAPI:
    """اختبارات API عناصر الطلب"""

    def test_get_items_returns_json(self, client_logged_in, test_manufacturing_order):
        """اختبار إرجاع JSON"""
        response = client_logged_in.get(f'/manufacturing/api/orders/{test_manufacturing_order.pk}/items/')
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

    def test_get_items_contains_order_id(self, client_logged_in, test_manufacturing_order):
        """اختبار وجود معرف الطلب"""
        response = client_logged_in.get(f'/manufacturing/api/orders/{test_manufacturing_order.pk}/items/')
        data = response.json()
        
        assert 'order_id' in data
        assert data['order_id'] == test_manufacturing_order.pk

    def test_get_items_returns_list(self, client_logged_in, test_manufacturing_order):
        """اختبار إرجاع قائمة"""
        response = client_logged_in.get(f'/manufacturing/api/orders/{test_manufacturing_order.pk}/items/')
        data = response.json()
        
        assert 'items' in data
        assert isinstance(data['items'], list)


@pytest.mark.django_db
class TestBulkUpdateAPI:
    """اختبارات API التحديث الجماعي"""

    def test_bulk_update_multiple_orders(
        self, client_logged_in, test_customer, user_with_permissions
    ):
        """اختبار تحديث عدة أوامر"""
        # إنشاء عدة أوامر
        orders = []
        for i in range(3):
            order = Order.objects.create(
                customer=test_customer,
                created_by=user_with_permissions,
                status="pending"
            )
            mfg_order = ManufacturingOrder.objects.create(
                order=order,
                created_by=user_with_permissions,
                status="pending"
            )
            orders.append(mfg_order)
        
        order_ids = [o.id for o in orders]
        
        # التحديث الجماعي
        response = client_logged_in.post(
            '/manufacturing/api/bulk-update-status/',
            data=json.dumps({'order_ids': order_ids, 'status': 'in_progress'}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['updated_count'] == 3

    def test_bulk_update_changes_database(
        self, client_logged_in, test_customer, user_with_permissions
    ):
        """اختبار تغيير قاعدة البيانات"""
        # إنشاء أوامر
        orders = []
        for i in range(2):
            order = Order.objects.create(
                customer=test_customer,
                created_by=user_with_permissions,
                status="pending"
            )
            mfg_order = ManufacturingOrder.objects.create(
                order=order,
                created_by=user_with_permissions,
                status="pending"
            )
            orders.append(mfg_order)
        
        order_ids = [o.id for o in orders]
        
        # التحديث
        client_logged_in.post(
            '/manufacturing/api/bulk-update-status/',
            data=json.dumps({'order_ids': order_ids, 'status': 'completed'}),
            content_type='application/json'
        )
        
        # التحقق
        for order in orders:
            order.refresh_from_db()
            assert order.status == 'completed'
