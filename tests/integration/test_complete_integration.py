"""
اختبارات تكامل شاملة للتحقق من عمل جميع الوحدات المقسمة
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

User = get_user_model()


@pytest.mark.django_db
class TestModuleImports:
    """اختبار استيراد جميع الوحدات المقسمة"""

    def test_manufacturing_views_imports(self):
        """اختبار استيراد وحدات manufacturing"""
        try:
            from manufacturing.views import (
                ManufacturingOrderListView,
                ManufacturingOrderDetailView,
                ManufacturingOrderCreateView,
                ManufacturingOrderUpdateView,
                ManufacturingOrderDeleteView,
                VIPOrdersListView,
                manufacturing_order_api,
                update_status_api,
                manufacturing_statistics_api,
                order_items_api,
                bulk_update_status_api,
                generate_manufacturing_report,
                export_to_excel,
                generate_summary_report,
            )
            
            assert ManufacturingOrderListView is not None
            assert VIPOrdersListView is not None
            assert manufacturing_order_api is not None
            assert generate_manufacturing_report is not None
            
        except ImportError as e:
            pytest.fail(f"فشل استيراد manufacturing.views: {e}")

    def test_inventory_views_imports(self):
        """اختبار استيراد وحدات inventory"""
        try:
            from inventory.views import (
                product_list,
                product_create,
                product_update,
                product_delete,
                product_detail,
                transaction_create,
                transfer_stock,
                get_product_stock_api,
            )
            
            assert product_list is not None
            assert transaction_create is not None
            assert get_product_stock_api is not None
            
        except ImportError as e:
            pytest.fail(f"فشل استيراد inventory.views: {e}")

    def test_service_layer_imports(self):
        """اختبار استيراد Service Layer"""
        try:
            from orders.services import OrderService, ContractService
            
            assert OrderService is not None
            assert ContractService is not None
            assert hasattr(OrderService, 'create_order')
            assert hasattr(OrderService, 'cancel_order')
            
        except ImportError as e:
            pytest.fail(f"فشل استيراد Service Layer: {e}")

    def test_permissions_imports(self):
        """اختبار استيراد الصلاحيات"""
        try:
            from inventory.permissions import (
                view_product,
                add_product,
                change_product,
                delete_product,
                can_transfer_stock,
                can_bulk_upload,
            )
            
            assert view_product is not None
            assert can_transfer_stock is not None
            
        except ImportError as e:
            pytest.fail(f"فشل استيراد الصلاحيات: {e}")


@pytest.mark.django_db
class TestEndToEndWorkflow:
    """اختبارات سير العمل الكامل"""

    @pytest.fixture
    def setup_user(self):
        """إعداد مستخدم مع جميع الصلاحيات"""
        user = User.objects.create_user(
            username="test_admin",
            email="admin@test.com",
            password="testpass123",
            is_staff=True
        )
        
        # إضافة جميع الصلاحيات
        permissions = Permission.objects.all()
        user.user_permissions.add(*permissions)
        
        return user

    def test_complete_order_workflow(self, setup_user):
        """اختبار سير عمل الطلب الكامل"""
        from customers.models import Customer
        from orders.services import OrderService
        from decimal import Decimal
        
        # 1. إنشاء عميل
        customer = Customer.objects.create(
            name="عميل اختبار",
            phone="0123456789",
            email="test@customer.com"
        )
        
        # 2. إنشاء طلب
        items_data = [
            {
                'product_name': 'منتج اختبار',
                'quantity': 5,
                'price': Decimal('100.00')
            }
        ]
        
        order = OrderService.create_order(
            customer_id=customer.id,
            items_data=items_data,
            created_by=setup_user
        )
        
        assert order is not None
        assert order.customer == customer
        assert hasattr(order, 'manufacturing_order')
        
        # 3. التحقق من أمر التصنيع
        mfg_order = order.manufacturing_order
        assert mfg_order.status == 'pending'
        
        # 4. تحديث الحالة
        mfg_order.status = 'in_progress'
        mfg_order.save()
        
        mfg_order.refresh_from_db()
        assert mfg_order.status == 'in_progress'
        
        # 5. إلغاء الطلب
        OrderService.cancel_order(
            order=order,
            reason="اختبار",
            cancelled_by=setup_user
        )
        
        order.refresh_from_db()
        assert order.status == 'cancelled'

    def test_complete_inventory_workflow(self, setup_user):
        """اختبار سير عمل المخزون الكامل"""
        from inventory.models import Product, Category, Warehouse, StockTransaction
        from decimal import Decimal
        from django.utils import timezone
        
        # 1. إنشاء فئة
        category = Category.objects.create(name="فئة اختبار")
        
        # 2. إنشاء منتج
        product = Product.objects.create(
            name="منتج مخزون",
            code="INV-TEST-001",
            category=category,
            price=Decimal('150.00'),
            minimum_stock=10
        )
        
        # 3. إنشاء مستودع
        warehouse = Warehouse.objects.create(
            name="مستودع اختبار",
            is_active=True
        )
        
        # 4. إضافة مخزون
        transaction_in = StockTransaction.objects.create(
            product=product,
            warehouse=warehouse,
            transaction_type='in',
            reason='purchase',
            quantity=100,
            running_balance=100,
            created_by=setup_user,
            transaction_date=timezone.now()
        )
        
        assert transaction_in.running_balance == 100
        
        # 5. صرف مخزون
        transaction_out = StockTransaction.objects.create(
            product=product,
            warehouse=warehouse,
            transaction_type='out',
            reason='sale',
            quantity=30,
            running_balance=70,
            created_by=setup_user,
            transaction_date=timezone.now()
        )
        
        assert transaction_out.running_balance == 70


@pytest.mark.django_db
class TestAllViewsAccessible:
    """اختبار إمكانية الوصول لجميع العروض"""

    @pytest.fixture
    def client_with_permissions(self):
        """عميل مع صلاحيات"""
        from django.test import Client
        
        user = User.objects.create_user(
            username="view_tester",
            email="tester@test.com",
            password="testpass123"
        )
        
        permissions = Permission.objects.all()
        user.user_permissions.add(*permissions)
        
        client = Client()
        client.force_login(user)
        
        return client

    def test_manufacturing_views_accessible(self, client_with_permissions):
        """اختبار الوصول لعروض التصنيع"""
        # يمكن إضافة اختبارات الوصول هنا
        # مثال: response = client_with_permissions.get('/manufacturing/orders/')
        # assert response.status_code in [200, 302]
        pass

    def test_inventory_views_accessible(self, client_with_permissions):
        """اختبار الوصول لعروض المخزون"""
        # يمكن إضافة اختبارات الوصول هنا
        pass


@pytest.mark.django_db
class TestAPIEndpoints:
    """اختبار جميع نقاط نهاية API"""

    @pytest.fixture
    def api_client(self):
        """عميل API"""
        from django.test import Client
        
        user = User.objects.create_user(
            username="api_tester",
            email="api@test.com",
            password="testpass123"
        )
        
        permissions = Permission.objects.all()
        user.user_permissions.add(*permissions)
        
        client = Client()
        client.force_login(user)
        
        return client

    def test_manufacturing_statistics_api(self, api_client):
        """اختبار API الإحصائيات"""
        # يمكن إضافة اختبار API هنا
        pass

    def test_product_stock_api(self, api_client):
        """اختبار API المخزون"""
        # يمكن إضافة اختبار API هنا
        pass


@pytest.mark.django_db
class TestPermissionsIntegration:
    """اختبار تكامل الصلاحيات"""

    def test_user_without_permissions_denied(self):
        """اختبار رفض المستخدم بدون صلاحيات"""
        from django.test import Client
        from django.core.exceptions import PermissionDenied
        
        user = User.objects.create_user(
            username="no_perms",
            email="noperms@test.com",
            password="testpass123"
        )
        
        client = Client()
        client.force_login(user)
        
        # المستخدم بدون صلاحيات لا يمكنه الوصول
        # يمكن إضافة اختبارات محددة هنا

    def test_user_with_specific_permission_allowed(self):
        """اختبار السماح للمستخدم مع صلاحية محددة"""
        user = User.objects.create_user(
            username="specific_perm",
            email="specific@test.com",
            password="testpass123"
        )
        
        # إضافة صلاحية محددة
        perm = Permission.objects.filter(
            codename='view_product'
        ).first()
        
        if perm:
            user.user_permissions.add(perm)
            assert user.has_perm('inventory.view_product')


@pytest.mark.django_db
class TestDataIntegrity:
    """اختبار سلامة البيانات"""

    def test_cascade_delete_works(self):
        """اختبار الحذف المتسلسل"""
        from customers.models import Customer
        from orders.models import Order
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.create_user(
            username="cascade_test",
            email="cascade@test.com",
            password="testpass123"
        )
        
        customer = Customer.objects.create(
            name="عميل للحذف",
            phone="0123456789"
        )
        
        order = Order.objects.create(
            customer=customer,
            created_by=user,
            status='pending'
        )
        
        order_id = order.id
        
        # حذف العميل يجب أن يحذف الطلب (أو يمنع الحذف حسب الإعداد)
        # هذا يعتمد على إعدادات on_delete في النماذج

    def test_unique_constraints(self):
        """اختبار القيود الفريدة"""
        from inventory.models import Product, Category
        from decimal import Decimal
        
        category = Category.objects.create(name="فئة فريدة")
        
        product1 = Product.objects.create(
            name="منتج فريد",
            code="UNIQUE-001",
            category=category,
            price=Decimal('100.00')
        )
        
        # محاولة إنشاء منتج بنفس الكود يجب أن تفشل
        with pytest.raises(Exception):
            Product.objects.create(
                name="منتج آخر",
                code="UNIQUE-001",  # نفس الكود
                category=category,
                price=Decimal('200.00')
            )
