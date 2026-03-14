"""
اختبارات صلاحيات المخزون
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.test import RequestFactory

from inventory.permissions import (
    add_product,
    can_bulk_upload,
    can_transfer_stock,
    change_product,
    delete_product,
    view_product,
)

User = get_user_model()


@pytest.fixture
def user_factory():
    """مصنع إنشاء المستخدمين"""

    def _create_user(username="testuser", **permissions):
        user = User.objects.create_user(
            username=username, email=f"{username}@test.com", password="testpass123"
        )
        # إضافة الصلاحيات المطلوبة
        for perm_name in permissions.get("permissions", []):
            try:
                perm = Permission.objects.get(codename=perm_name)
                user.user_permissions.add(perm)
            except Permission.DoesNotExist:
                pass
        return user

    return _create_user


@pytest.fixture
def request_factory():
    """مصنع الطلبات"""
    return RequestFactory()


@pytest.mark.django_db
class TestViewProductPermission:
    """اختبارات صلاحية عرض المنتجات"""

    def test_user_with_permission_can_view(self, user_factory, request_factory):
        """مستخدم لديه صلاحية يمكنه العرض"""
        user = user_factory(permissions=["view_product"])
        request = request_factory.get("/inventory/products/")
        request.user = user

        @view_product
        def test_view(request):
            return "success"

        result = test_view(request)
        assert result == "success"

    def test_user_without_permission_cannot_view(self, user_factory, request_factory):
        """مستخدم بدون صلاحية لا يمكنه العرض"""
        user = user_factory()  # بدون صلاحيات
        request = request_factory.get("/inventory/products/")
        request.user = user

        @view_product
        def test_view(request):
            return "success"

        with pytest.raises(PermissionDenied):
            test_view(request)


@pytest.mark.django_db
class TestAddProductPermission:
    """اختبارات صلاحية إضافة المنتجات"""

    def test_user_with_permission_can_add(self, user_factory, request_factory):
        """مستخدم لديه صلاحية يمكنه الإضافة"""
        user = user_factory(permissions=["add_product"])
        request = request_factory.post("/inventory/products/create/")
        request.user = user

        @add_product
        def test_view(request):
            return "created"

        result = test_view(request)
        assert result == "created"

    def test_user_without_permission_cannot_add(self, user_factory, request_factory):
        """مستخدم بدون صلاحية لا يمكنه الإضافة"""
        user = user_factory()
        request = request_factory.post("/inventory/products/create/")
        request.user = user

        @add_product
        def test_view(request):
            return "created"

        with pytest.raises(PermissionDenied):
            test_view(request)


@pytest.mark.django_db
class TestChangeProductPermission:
    """اختبارات صلاحية تعديل المنتجات"""

    def test_user_with_permission_can_change(self, user_factory, request_factory):
        """مستخدم لديه صلاحية يمكنه التعديل"""
        user = user_factory(permissions=["change_product"])
        request = request_factory.post("/inventory/products/1/edit/")
        request.user = user

        @change_product
        def test_view(request, pk):
            return f"updated {pk}"

        result = test_view(request, pk=1)
        assert result == "updated 1"


@pytest.mark.django_db
class TestDeleteProductPermission:
    """اختبارات صلاحية حذف المنتجات"""

    def test_user_with_permission_can_delete(self, user_factory, request_factory):
        """مستخدم لديه صلاحية يمكنه الحذف"""
        user = user_factory(permissions=["delete_product"])
        request = request_factory.post("/inventory/products/1/delete/")
        request.user = user

        @delete_product
        def test_view(request, pk):
            return f"deleted {pk}"

        result = test_view(request, pk=1)
        assert result == "deleted 1"


@pytest.mark.django_db
class TestTransferStockPermission:
    """اختبارات صلاحية نقل المخزون"""

    def test_user_with_permission_can_transfer(self, user_factory, request_factory):
        """مستخدم لديه صلاحية يمكنه النقل"""
        user = user_factory(permissions=["change_product"])
        request = request_factory.post("/inventory/transfer/")
        request.user = user

        @can_transfer_stock
        def test_view(request):
            return "transferred"

        result = test_view(request)
        assert result == "transferred"

    def test_user_without_permission_cannot_transfer(
        self, user_factory, request_factory
    ):
        """مستخدم بدون صلاحية لا يمكنه النقل"""
        user = user_factory()
        request = request_factory.post("/inventory/transfer/")
        request.user = user

        @can_transfer_stock
        def test_view(request):
            return "transferred"

        with pytest.raises(PermissionDenied):
            test_view(request)


@pytest.mark.django_db
class TestBulkUploadPermission:
    """اختبارات صلاحية الرفع الجماعي"""

    def test_superuser_can_bulk_upload(self, request_factory):
        """المدير الأعلى يمكنه الرفع الجماعي"""
        user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin123"
        )
        request = request_factory.post("/inventory/bulk-upload/")
        request.user = user

        @can_bulk_upload
        def test_view(request):
            return "uploaded"

        result = test_view(request)
        assert result == "uploaded"

    def test_staff_with_permission_can_bulk_upload(
        self, user_factory, request_factory
    ):
        """موظف لديه صلاحية يمكنه الرفع الجماعي"""
        user = user_factory(permissions=["add_product"])
        user.is_staff = True
        user.save()

        request = request_factory.post("/inventory/bulk-upload/")
        request.user = user

        @can_bulk_upload
        def test_view(request):
            return "uploaded"

        result = test_view(request)
        assert result == "uploaded"

    def test_regular_user_cannot_bulk_upload(self, user_factory, request_factory):
        """مستخدم عادي لا يمكنه الرفع الجماعي"""
        user = user_factory(permissions=["add_product"])
        # is_staff = False by default

        request = request_factory.post("/inventory/bulk-upload/")
        request.user = user

        @can_bulk_upload
        def test_view(request):
            return "uploaded"

        with pytest.raises(PermissionDenied):
            test_view(request)


@pytest.mark.django_db
class TestPermissionIntegration:
    """اختبارات تكامل الصلاحيات"""

    def test_multiple_permissions_on_same_view(self, user_factory, request_factory):
        """اختبار عدة صلاحيات على نفس العرض"""
        user = user_factory(permissions=["view_product", "change_product"])
        request = request_factory.get("/inventory/products/1/")
        request.user = user

        @view_product
        @change_product
        def test_view(request, pk):
            return f"viewing and can edit {pk}"

        result = test_view(request, pk=1)
        assert result == "viewing and can edit 1"

    def test_permission_denied_message(self, user_factory, request_factory):
        """اختبار رسالة رفض الصلاحية"""
        user = user_factory()
        request = request_factory.get("/inventory/products/")
        request.user = user

        @view_product
        def test_view(request):
            return "success"

        with pytest.raises(PermissionDenied):
            test_view(request)
