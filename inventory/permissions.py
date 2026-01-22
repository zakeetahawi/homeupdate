"""
صلاحيات مخصصة لوحدة المخزون
"""

from functools import wraps
from typing import Callable, Any

from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest


def inventory_permission_required(
    perm: str, raise_exception: bool = True
) -> Callable[[Callable], Callable]:
    """
    مزخرف مخصص لصلاحيات المخزون

    Args:
        perm: اسم الصلاحية (مثل: 'view_product', 'add_product')
        raise_exception: رفع استثناء إذا لم يكن لدى المستخدم الصلاحية

    Usage:
        @view_product
        def product_list(request):
            ...
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        @permission_required(f"inventory.{perm}", raise_exception=raise_exception)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# ✅ صلاحيات محددة جاهزة للاستخدام
view_product = inventory_permission_required("view_product")
add_product = inventory_permission_required("add_product")
change_product = inventory_permission_required("change_product")
delete_product = inventory_permission_required("delete_product")

view_warehouse = inventory_permission_required("view_warehouse")
add_warehouse = inventory_permission_required("add_warehouse")
change_warehouse = inventory_permission_required("change_warehouse")
delete_warehouse = inventory_permission_required("delete_warehouse")

view_category = inventory_permission_required("view_category")
add_category = inventory_permission_required("add_category")
change_category = inventory_permission_required("change_category")
delete_category = inventory_permission_required("delete_category")


# ✅ صلاحيات مخصصة للعمليات الخاصة
def can_transfer_stock(view_func: Callable) -> Callable:
    """صلاحية نقل المخزون بين المستودعات"""

    @wraps(view_func)
    @permission_required("inventory.change_product", raise_exception=True)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        return view_func(request, *args, **kwargs)

    return wrapper


def can_adjust_stock(view_func: Callable) -> Callable:
    """صلاحية تعديل كميات المخزون"""

    @wraps(view_func)
    @permission_required("inventory.change_product", raise_exception=True)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        return view_func(request, *args, **kwargs)

    return wrapper


def can_bulk_upload(view_func: Callable) -> Callable:
    """صلاحية الرفع الجماعي للمنتجات"""

    @wraps(view_func)
    @permission_required("inventory.add_product", raise_exception=True)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        # تحقق إضافي: فقط المديرين والمشرفين
        if not (request.user.is_superuser or request.user.is_staff):
            raise PermissionDenied("فقط المديرين يمكنهم الرفع الجماعي")
        return view_func(request, *args, **kwargs)

    return wrapper
