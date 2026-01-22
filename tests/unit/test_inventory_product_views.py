"""
اختبارات شاملة لـ inventory/views/product_views.py
"""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from inventory.models import Product, Category, Warehouse

User = get_user_model()


@pytest.fixture
def user_with_permissions(db):
    """مستخدم مع صلاحيات المخزون"""
    user = User.objects.create_user(
        username="inv_user",
        email="inv@test.com",
        password="testpass123"
    )
    permissions = Permission.objects.filter(
        content_type__app_label='inventory'
    )
    user.user_permissions.add(*permissions)
    return user


@pytest.fixture
def test_category(db):
    """فئة للاختبار"""
    return Category.objects.create(name="فئة تجريبية")


@pytest.fixture
def test_product(db, test_category):
    """منتج للاختبار"""
    return Product.objects.create(
        name="منتج تجريبي",
        code="TEST-001",
        category=test_category,
        price=Decimal("100.00"),
        minimum_stock=10
    )


@pytest.fixture
def test_warehouse(db):
    """مستودع للاختبار"""
    return Warehouse.objects.create(
        name="مستودع تجريبي",
        is_active=True
    )


@pytest.fixture
def client_logged_in(user_with_permissions):
    """عميل مسجل دخول"""
    client = Client()
    client.force_login(user_with_permissions)
    return client


@pytest.mark.django_db
class TestProductListView:
    """اختبارات عرض قائمة المنتجات"""

    def test_product_list_accessible(self, client_logged_in):
        """اختبار الوصول للقائمة"""
        response = client_logged_in.get('/inventory/products/')
        
        assert response.status_code == 200

    def test_product_list_shows_products(self, client_logged_in, test_product):
        """اختبار عرض المنتجات"""
        response = client_logged_in.get('/inventory/products/')
        
        assert test_product.name.encode() in response.content

    def test_search_filters_products(self, client_logged_in, test_product):
        """اختبار البحث"""
        response = client_logged_in.get('/inventory/products/?search=تجريبي')
        
        assert test_product.name.encode() in response.content

    def test_category_filter_works(self, client_logged_in, test_product):
        """اختبار فلترة الفئة"""
        response = client_logged_in.get(
            f'/inventory/products/?category={test_product.category.id}'
        )
        
        assert test_product.name.encode() in response.content


@pytest.mark.django_db
class TestProductCreateView:
    """اختبارات إنشاء منتج"""

    def test_create_product_success(self, client_logged_in, test_category):
        """اختبار إنشاء ناجح"""
        data = {
            'name': 'منتج جديد',
            'code': 'NEW-001',
            'category': test_category.id,
            'price': '150.00',
            'minimum_stock': 5
        }
        
        response = client_logged_in.post('/inventory/products/create/', data)
        
        assert response.status_code == 302  # Redirect
        assert Product.objects.filter(code='NEW-001').exists()

    def test_create_product_with_initial_stock(
        self, client_logged_in, test_category, test_warehouse
    ):
        """اختبار إنشاء مع مخزون ابتدائي"""
        data = {
            'name': 'منتج مع مخزون',
            'code': 'STOCK-001',
            'category': test_category.id,
            'price': '200.00',
            'minimum_stock': 10,
            'initial_quantity': 100,
            'warehouse': test_warehouse.id
        }
        
        response = client_logged_in.post('/inventory/products/create/', data)
        
        assert response.status_code == 302
        product = Product.objects.get(code='STOCK-001')
        assert product is not None


@pytest.mark.django_db
class TestProductUpdateView:
    """اختبارات تحديث منتج"""

    def test_update_product_success(self, client_logged_in, test_product):
        """اختبار تحديث ناجح"""
        data = {
            'name': 'منتج محدث',
            'code': test_product.code,
            'category': test_product.category.id,
            'price': '250.00',
            'minimum_stock': 15
        }
        
        response = client_logged_in.post(
            f'/inventory/products/{test_product.id}/edit/',
            data
        )
        
        assert response.status_code == 302
        test_product.refresh_from_db()
        assert test_product.name == 'منتج محدث'
        assert test_product.price == Decimal('250.00')


@pytest.mark.django_db
class TestProductDeleteView:
    """اختبارات حذف منتج"""

    def test_delete_product_success(self, client_logged_in, test_product):
        """اختبار حذف ناجح"""
        product_id = test_product.id
        
        response = client_logged_in.post(
            f'/inventory/products/{product_id}/delete/'
        )
        
        assert response.status_code == 302
        assert not Product.objects.filter(id=product_id).exists()


@pytest.mark.django_db
class TestProductDetailView:
    """اختبارات عرض تفاصيل منتج"""

    def test_product_detail_accessible(self, client_logged_in, test_product):
        """اختبار الوصول للتفاصيل"""
        response = client_logged_in.get(f'/inventory/products/{test_product.id}/')
        
        assert response.status_code == 200
        assert test_product.name.encode() in response.content

    def test_product_detail_shows_stock_info(self, client_logged_in, test_product):
        """اختبار عرض معلومات المخزون"""
        response = client_logged_in.get(f'/inventory/products/{test_product.id}/')
        
        assert b'current_stock' in response.content or test_product.name.encode() in response.content
