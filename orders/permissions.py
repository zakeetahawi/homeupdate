"""
نظام الصلاحيات الشامل لقسم الطلبات مع دعم التسلسل الهرمي
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied


def user_has_role_or_higher(user, target_role):
    """
    التحقق من أن المستخدم لديه دور معين أو أعلى منه في التسلسل الهرمي
    """
    from accounts.models import ROLE_HIERARCHY

    if user.is_superuser:
        return True

    user_role = user.get_user_role()
    user_level = ROLE_HIERARCHY.get(user_role, {}).get("level", 999)
    target_level = ROLE_HIERARCHY.get(target_role, {}).get("level", 999)

    # المستوى الأقل = الصلاحيات الأعلى
    return user_level <= target_level


def get_users_manageable_by(user):
    """
    الحصول على المستخدمين الذين يمكن للمستخدم إدارتهم بناءً على التسلسل الهرمي
    """
    from accounts.models import User

    if user.is_superuser:
        return User.objects.all()

    user_level = user.get_role_level()

    # الحصول على المستخدمين الأدنى في التسلسل الهرمي
    manageable_users = []
    for potential_user in User.objects.all():
        if user.can_manage_user(potential_user):
            manageable_users.append(potential_user.id)

    return User.objects.filter(id__in=manageable_users)


def get_user_orders_queryset(user):
    """الحصول على queryset الطلبات حسب صلاحيات المستخدم"""
    from .models import Order

    if user.is_superuser:
        return Order.objects.all()

    from django.db.models import Q

    # المدير العام يرى جميع الطلبات
    if hasattr(user, "is_sales_manager") and user.is_sales_manager:
        return Order.objects.all()

    # مسؤول المصنع يرى جميع الطلبات
    if hasattr(user, "is_factory_manager") and user.is_factory_manager:
        return Order.objects.all()

    # مسؤول المعاينات يرى جميع الطلبات التي تحتوي على معاينة + طلباته الخاصة
    if hasattr(user, "is_inspection_manager") and user.is_inspection_manager:
        return Order.objects.filter(
            Q(selected_types__icontains="inspection") | Q(created_by=user)
        )

    # مسؤول التركيبات يرى جميع الطلبات التي تحتوي على تركيب + طلباته الخاصة
    if hasattr(user, "is_installation_manager") and user.is_installation_manager:
        return Order.objects.filter(
            Q(selected_types__icontains="installation") | Q(created_by=user)
        )

    # مدير المنطقة يرى طلبات الفروع المُدارة + طلباته الخاصة
    if hasattr(user, "is_region_manager") and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        if managed_branches.exists():
            return Order.objects.filter(
                Q(branch__in=managed_branches) | Q(created_by=user)
            )
        else:
            return Order.objects.filter(created_by=user)

    # مدير الفرع يرى طلبات فرعه حسب صلاحيات نوع العميل + طلباته الخاصة
    if hasattr(user, "is_branch_manager") and user.is_branch_manager:
        if hasattr(user, "branch") and user.branch:
            # فحص صلاحيات نوع العميل
            has_wholesale = getattr(user, "is_wholesale", False)
            has_retail = getattr(user, "is_retail", True)  # القيمة الافتراضية True

            # إذا كان لديه صلاحية واحدة فقط، فلتر حسبها
            if has_wholesale and not has_retail:
                # جملة فقط أو طلباته الخاصة
                return Order.objects.filter(
                    Q(branch=user.branch, customer__customer_type="wholesale")
                    | Q(created_by=user)
                )
            elif has_retail and not has_wholesale:
                # قطاعي فقط أو طلباته الخاصة
                return Order.objects.filter(
                    Q(branch=user.branch, customer__customer_type="retail")
                    | Q(created_by=user)
                )
            else:
                # كلاهما أو لا شيء = جميع الطلبات في الفرع أو طلباته الخاصة
                return Order.objects.filter(Q(branch=user.branch) | Q(created_by=user))
        else:
            return Order.objects.filter(created_by=user)

    # البائع يرى طلباته الشخصية + الطلبات المُسندة إليه كبائع
    if hasattr(user, "is_salesperson") and user.is_salesperson:
        return Order.objects.filter(
            Q(created_by=user) | Q(salesperson__user=user)
        )

    # فني المعاينة يرى طلبات المعاينة فقط + طلباته الخاصة (إذا كان يمكنه إنشاء طلبات)
    if hasattr(user, "is_inspection_technician") and user.is_inspection_technician:
        return Order.objects.filter(
            Q(selected_types__icontains="inspection") | Q(created_by=user)
        )

    # مدير النظام بدون دور محدد يرى طلباته فقط
    if user.is_superuser:
        return Order.objects.filter(created_by=user)

    # بشكل افتراضي، أعد طلبات التي أنشأها المستخدم (تم إنشاؤها بواسطة)
    # هذا يسمح للمستخدمين العاديين بمشاهدة طلباتهم حتى لو لم يكن لديهم دور محدد
    return Order.objects.filter(created_by=user)


def can_user_view_order(user, order):
    """التحقق من إمكانية المستخدم لعرض طلب معين"""
    # فحص الأدوار المخصصة أولاً قبل is_superuser

    # صاحب الطلب يمكنه دائمًا رؤية طلبه
    try:
        if order.created_by == user:
            return True
    except Exception:
        pass

    # البائع المُسند على الطلب يمكنه دائمًا رؤيته
    try:
        if order.salesperson and order.salesperson.user == user:
            return True
    except Exception:
        pass

    # أي مستخدم يستطيع رؤية بيانات العميل يستطيع رؤية طلباته
    try:
        from customers.permissions import can_user_view_customer
        if order.customer and can_user_view_customer(user, order.customer):
            return True
    except Exception:
        pass

    # المدير العام يرى جميع الطلبات
    if hasattr(user, "is_sales_manager") and user.is_sales_manager:
        return True

    # مسؤول المصنع يرى جميع الطلبات
    if hasattr(user, "is_factory_manager") and user.is_factory_manager:
        return True

    # إذا كان superuser بدون دور محدد، يتبع قواعد البائع
    if user.is_superuser:
        # البحث في الطلبات التي يمكن للمستخدم رؤيتها
        user_orders = get_user_orders_queryset(user)
        return user_orders.filter(id=order.id).exists()

    # المدير العام يرى جميع الطلبات
    if hasattr(user, "is_sales_manager") and user.is_sales_manager:
        return True

    # مسؤول المصنع يرى جميع الطلبات
    if hasattr(user, "is_factory_manager") and user.is_factory_manager:
        return True

    # مسؤول المعاينات يرى جميع الطلبات التي تحتوي على معاينة
    if hasattr(user, "is_inspection_manager") and user.is_inspection_manager:
        return "inspection" in order.get_selected_types_list()

    # مسؤول التركيبات يرى جميع الطلبات التي تحتوي على تركيب
    if hasattr(user, "is_installation_manager") and user.is_installation_manager:
        return "installation" in order.get_selected_types_list()

    # مدير المنطقة يرى طلبات الفروع المُدارة
    if hasattr(user, "is_region_manager") and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        return order.branch in managed_branches

    # مدير الفرع يرى طلبات فرعه فقط
    if hasattr(user, "is_branch_manager") and user.is_branch_manager:
        return hasattr(user, "branch") and user.branch and order.branch == user.branch

    # البائع يرى طلباته + الطلبات المُسندة إليه كبائع
    if hasattr(user, "is_salesperson") and user.is_salesperson:
        if order.created_by == user:
            return True
        try:
            if order.salesperson and order.salesperson.user == user:
                return True
        except Exception:
            pass
        return False

    # فني المعاينة يرى طلبات المعاينة فقط
    if hasattr(user, "is_inspection_technician") and user.is_inspection_technician:
        return "inspection" in order.get_selected_types_list()

    return False


def can_user_edit_order(user, order):
    """التحقق من إمكانية المستخدم لتعديل طلب معين"""
    # صاحب الطلب يمكنه دائمًا تعديل طلبه
    try:
        if order.created_by == user:
            return True
    except Exception:
        pass

    if user.is_superuser:
        return True

    # المدير العام يمكنه تعديل جميع الطلبات
    # Sales Manager restriction
    # if hasattr(user, 'is_sales_manager') and user.is_sales_manager:
    #    return True

    # مسؤول المصنع يمكنه تعديل جميع الطلبات
    if hasattr(user, "is_factory_manager") and user.is_factory_manager:
        return True

    # مسؤول المعاينات يمكنه تعديل الطلبات التي تحتوي على معاينة
    if hasattr(user, "is_inspection_manager") and user.is_inspection_manager:
        return "inspection" in order.get_selected_types_list()

    # مسؤول التركيبات يمكنه تعديل الطلبات التي تحتوي على تركيب
    if hasattr(user, "is_installation_manager") and user.is_installation_manager:
        return "installation" in order.get_selected_types_list()

    # مدير المنطقة يمكنه تعديل طلبات الفروع المُدارة
    if hasattr(user, "is_region_manager") and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        return order.branch in managed_branches

    # مدير الفرع يمكنه تعديل طلبات فرعه
    if hasattr(user, "is_branch_manager") and user.is_branch_manager:
        return hasattr(user, "branch") and user.branch and order.branch == user.branch

    # البائع يمكنه تعديل طلباته فقط
    if hasattr(user, "is_salesperson") and user.is_salesperson:
        return order.created_by == user

    # فني المعاينة لا يمكنه تعديل الطلبات
    return False


def can_user_delete_order(user, order):
    """التحقق من إمكانية المستخدم لحذف طلب معين"""
    if user.is_superuser:
        return True

    # Check for delete permission
    if user.has_perm("orders.delete_order"):
        return True

    # المدير العام يمكنه حذف جميع الطلبات
    # Sales Manager restriction
    if hasattr(user, "is_sales_manager") and user.is_sales_manager:
        return False

    # مسؤول المصنع يمكنه حذف جميع الطلبات
    if hasattr(user, "is_factory_manager") and user.is_factory_manager:
        return True

    # مسؤول المعاينات يمكنه حذف الطلبات التي تحتوي على معاينة
    if hasattr(user, "is_inspection_manager") and user.is_inspection_manager:
        return "inspection" in order.get_selected_types_list()

    # مسؤول التركيبات يمكنه حذف الطلبات التي تحتوي على تركيب
    if hasattr(user, "is_installation_manager") and user.is_installation_manager:
        return "installation" in order.get_selected_types_list()

    # تحديث: منع مدراء المناطق والفروع من حذف الطلبات
    # مدير المنطقة يمكنه حذف طلبات الفروع المُدارة
    if hasattr(user, "is_region_manager") and user.is_region_manager:
        # managed_branches = user.managed_branches.all()
        # return order.branch in managed_branches
        return False

    # مدير الفرع يمكنه حذف طلبات فرعه
    if hasattr(user, "is_branch_manager") and user.is_branch_manager:
        # return hasattr(user, "branch") and user.branch and order.branch == user.branch
        return False

    # البائع والفني لا يمكنهم حذف الطلبات
    return False


def can_user_create_order_type(user, order_type):
    """التحقق من إمكانية المستخدم لإنشاء نوع طلب معين"""
    if user.is_superuser:
        return True

    # المدير العام يمكنه إنشاء جميع أنواع الطلبات
    if hasattr(user, "is_sales_manager") and user.is_sales_manager:
        return True

    # مسؤول المصنع يمكنه إنشاء جميع أنواع الطلبات
    if hasattr(user, "is_factory_manager") and user.is_factory_manager:
        return True

    # مسؤول المعاينات يمكنه إنشاء طلبات المعاينة
    if hasattr(user, "is_inspection_manager") and user.is_inspection_manager:
        return order_type == "inspection"

    # مسؤول التركيبات يمكنه إنشاء طلبات التركيب
    if hasattr(user, "is_installation_manager") and user.is_installation_manager:
        return order_type == "installation"

    # مدير المنطقة يمكنه إنشاء جميع أنواع الطلبات
    if hasattr(user, "is_region_manager") and user.is_region_manager:
        return True

    # مدير الفرع يمكنه إنشاء جميع أنواع الطلبات
    if hasattr(user, "is_branch_manager") and user.is_branch_manager:
        return True

    # البائع يمكنه إنشاء جميع أنواع الطلبات
    if hasattr(user, "is_salesperson") and user.is_salesperson:
        return True

    # فني المعاينة يمكنه إنشاء طلبات المعاينة فقط
    if hasattr(user, "is_inspection_technician") and user.is_inspection_technician:
        return order_type == "inspection"

    return False


def apply_order_permissions(user, orders_queryset):
    """تطبيق الصلاحيات على queryset الطلبات"""
    if user.is_superuser:
        return orders_queryset

    # المدير العام يرى جميع الطلبات
    if hasattr(user, "is_sales_manager") and user.is_sales_manager:
        return orders_queryset

    # مدير المنطقة يرى طلبات الفروع المُدارة
    if hasattr(user, "is_region_manager") and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        if managed_branches.exists():
            return orders_queryset.filter(branch__in=managed_branches)
        else:
            return orders_queryset.none()

    # مدير الفرع يرى طلبات فرعه فقط
    if hasattr(user, "is_branch_manager") and user.is_branch_manager:
        if hasattr(user, "branch") and user.branch:
            return orders_queryset.filter(branch=user.branch)
        else:
            return orders_queryset.none()

    # البائع يرى طلباته فقط
    if hasattr(user, "is_salesperson") and user.is_salesperson:
        return orders_queryset.filter(created_by=user)

    # فني المعاينة يرى طلبات المعاينة فقط
    if hasattr(user, "is_inspection_technician") and user.is_inspection_technician:
        return orders_queryset.filter(selected_types__icontains="inspection")

    # المستخدم العادي لا يرى أي طلبات
    return orders_queryset.none()


def get_user_role_permissions(user):
    """الحصول على صلاحيات المستخدم حسب دوره مع دعم الوراثة"""
    permissions = {
        "can_view_all_orders": False,
        "can_view_branch_orders": False,
        "can_view_own_orders": False,
        "can_create_orders": False,
        "can_edit_orders": False,
        "can_delete_orders": False,
        "can_manage_dashboard": False,
        "can_manage_users": False,
        "can_manage_branches": False,
    }

    if user.is_superuser:
        # المدير الأعلى له جميع الصلاحيات
        return {key: True for key in permissions.keys()}

    # الحصول على جميع الصلاحيات بما فيها الموروثة
    user_permissions = user.get_role_permissions()

    # تحويل صلاحيات الدور إلى صلاحيات محددة
    if "all" in user_permissions:
        return {key: True for key in permissions.keys()}

    # المدير العام
    # مدير المبيعات
    if user_has_role_or_higher(user, "sales_manager"):
        permissions.update(
            {
                "can_view_all_orders": True,
                "can_view_branch_orders": True,
                "can_view_own_orders": True,
                "can_create_orders": True,
                "can_edit_orders": False,
                "can_delete_orders": False,
                "can_manage_dashboard": True,
                "can_manage_users": False,
                "can_manage_branches": False,
            }
        )
        return permissions

    # مدير المنطقة يرث صلاحيات مدير الفرع + صلاحيات إضافية
    if user_has_role_or_higher(user, "region_manager"):
        permissions.update(
            {
                "can_view_all_orders": False,  # يرى فروعه فقط
                "can_view_branch_orders": True,
                "can_create_orders": True,
                "can_edit_orders": True,
                "can_delete_orders": True,
                "can_manage_dashboard": True,
                "can_manage_users": True,
                "can_manage_branches": True,
            }
        )
        return permissions

    # مدير الفرع يرث صلاحيات البائع + صلاحيات إضافية
    if user_has_role_or_higher(user, "branch_manager"):
        permissions.update(
            {
                "can_view_branch_orders": True,
                "can_create_orders": True,
                "can_edit_orders": True,
                "can_delete_orders": True,
                "can_manage_dashboard": True,
                "can_manage_users": True,
            }
        )
        return permissions

    # مسؤول المصنع
    if user_has_role_or_higher(user, "factory_manager"):
        permissions.update(
            {
                "can_view_all_orders": True,
                "can_view_branch_orders": True,
                "can_create_orders": True,
                "can_edit_orders": True,
                "can_delete_orders": True,
                "can_manage_dashboard": True,
            }
        )
        return permissions

    # مسؤول المعاينات يرث صلاحيات فني المعاينة
    if user_has_role_or_higher(user, "inspection_manager"):
        permissions.update(
            {
                "can_view_all_orders": True,
                "can_view_branch_orders": True,
                "can_create_orders": True,
                "can_edit_orders": True,
                "can_delete_orders": True,
                "can_manage_dashboard": True,
            }
        )
        return permissions

    # مسؤول التركيبات
    if user_has_role_or_higher(user, "installation_manager"):
        permissions.update(
            {
                "can_view_all_orders": True,
                "can_view_branch_orders": True,
                "can_create_orders": True,
                "can_edit_orders": True,
                "can_delete_orders": True,
                "can_manage_dashboard": True,
            }
        )
        return permissions

    # البائع - صلاحيات أساسية
    if user_has_role_or_higher(user, "salesperson"):
        permissions.update(
            {
                "can_view_own_orders": True,
                "can_create_orders": True,
                "can_edit_orders": False,  # يعدل طلباته فقط
                "can_delete_orders": False,
                "can_manage_dashboard": True,  # يصل للداشبورد ولكن يرى طلباته فقط
            }
        )
        return permissions

    # فني المعاينة
    if user_has_role_or_higher(user, "inspection_technician"):
        permissions.update(
            {
                "can_view_own_orders": True,
            }
        )
        return permissions

    # موظف المستودع
    if hasattr(user, "is_warehouse_staff") and user.is_warehouse_staff:
        permissions.update(
            {
                "can_view_branch_orders": True,
            }
        )
        return permissions

    # المستخدم العادي
    return permissions


# ============================================================================
# Decorators مخصصة للصلاحيات المتقدمة
# ============================================================================


def order_create_permission_required(view_func):
    """
    Decorator مخصص للتحقق من صلاحية إنشاء الطلبات
    يستخدم نظام الصلاحيات المتقدم بدلاً من الـ permission_required البسيط
    """

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # السماح للمدير الأعلى
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # التحقق من صلاحية إنشاء الطلبات
        if not can_user_create_order_type(request.user, "product"):
            raise PermissionDenied("ليس لديك صلاحية لإنشاء طلبات")

        return view_func(request, *args, **kwargs)

    return wrapper


def order_edit_permission_required(view_func):
    """
    Decorator مخصص للتحقق من صلاحية تعديل الطلبات
    يستخدم نظام الصلاحيات المتقدم
    يدعم: pk, order_id, order_number, order_code
    """

    @login_required
    @wraps(view_func)
    def wrapper(
        request,
        pk=None,
        order_id=None,
        order_number=None,
        order_code=None,
        *args,
        **kwargs
    ):
        from .models import Order

        # الحصول على الطلب
        order = None
        if pk:
            try:
                order = Order.objects.get(pk=pk)
            except Order.DoesNotExist:
                raise PermissionDenied("الطلب غير موجود")
        elif order_id:
            try:
                order = Order.objects.get(pk=order_id)
            except Order.DoesNotExist:
                raise PermissionDenied("الطلب غير موجود")
        elif order_number:
            try:
                order = Order.objects.get(order_number=order_number)
            except Order.DoesNotExist:
                raise PermissionDenied("الطلب غير موجود")
        elif order_code:
            try:
                order = Order.objects.get(order_code=order_code)
            except Order.DoesNotExist:
                raise PermissionDenied("الطلب غير موجود")
        else:
            raise PermissionDenied("معرف الطلب غير محدد")

        # السماح للمدير الأعلى
        if request.user.is_superuser:
            # تمرير جميع الـ arguments المحتملة
            if pk:
                return view_func(request, pk=pk, *args, **kwargs)
            elif order_id:
                return view_func(request, order_id=order_id, *args, **kwargs)
            elif order_number:
                return view_func(request, order_number=order_number, *args, **kwargs)
            elif order_code:
                return view_func(request, order_code=order_code, *args, **kwargs)

        # التحقق من صلاحية التعديل
        if not can_user_edit_order(request.user, order):
            from django.contrib import messages
            from django.shortcuts import redirect

            messages.error(request, "ليس لديك صلاحية لتعديل هذا الطلب")
            # إعادة التوجيه إلى صفحة تفاصيل الطلب
            if pk:
                return redirect("orders:order_detail", pk=pk)
            elif order_number:
                return redirect(
                    "orders:order_detail_by_number", order_number=order_number
                )
            else:
                return redirect("orders:order_list")

        # تمرير جميع الـ arguments المحتملة
        if pk:
            return view_func(request, pk=pk, *args, **kwargs)
        elif order_id:
            return view_func(request, order_id=order_id, *args, **kwargs)
        elif order_number:
            return view_func(request, order_number=order_number, *args, **kwargs)
        elif order_code:
            return view_func(request, order_code=order_code, *args, **kwargs)

    return wrapper


def order_delete_permission_required(view_func):
    """
    Decorator مخصص للتحقق من صلاحية حذف الطلبات
    يستخدم نظام الصلاحيات المتقدم
    يدعم: pk, order_id, order_number, order_code
    """

    @login_required
    @wraps(view_func)
    def wrapper(
        request,
        pk=None,
        order_id=None,
        order_number=None,
        order_code=None,
        *args,
        **kwargs
    ):
        from .models import Order

        # الحصول على الطلب
        order = None
        if pk:
            try:
                order = Order.objects.get(pk=pk)
            except Order.DoesNotExist:
                raise PermissionDenied("الطلب غير موجود")
        elif order_id:
            try:
                order = Order.objects.get(pk=order_id)
            except Order.DoesNotExist:
                raise PermissionDenied("الطلب غير موجود")
        elif order_number:
            try:
                order = Order.objects.get(order_number=order_number)
            except Order.DoesNotExist:
                raise PermissionDenied("الطلب غير موجود")
        elif order_code:
            try:
                order = Order.objects.get(order_code=order_code)
            except Order.DoesNotExist:
                raise PermissionDenied("الطلب غير موجود")
        else:
            raise PermissionDenied("معرف الطلب غير محدد")

        # السماح للمدير الأعلى
        if request.user.is_superuser:
            # تمرير جميع الـ arguments المحتملة
            if pk:
                return view_func(request, pk=pk, *args, **kwargs)
            elif order_id:
                return view_func(request, order_id=order_id, *args, **kwargs)
            elif order_number:
                return view_func(request, order_number=order_number, *args, **kwargs)
            elif order_code:
                return view_func(request, order_code=order_code, *args, **kwargs)

        # التحقق من صلاحية الحذف
        if not can_user_delete_order(request.user, order):
            from django.contrib import messages
            from django.shortcuts import redirect

            messages.error(request, "ليس لديك صلاحية لحذف هذا الطلب")
            # إعادة التوجيه إلى صفحة تفاصيل الطلب
            if pk:
                return redirect("orders:order_detail", pk=pk)
            elif order_number:
                return redirect(
                    "orders:order_detail_by_number", order_number=order_number
                )
            else:
                return redirect("orders:order_list")

        # تمرير جميع الـ arguments المحتملة
        if pk:
            return view_func(request, pk=pk, *args, **kwargs)
        elif order_id:
            return view_func(request, order_id=order_id, *args, **kwargs)
        elif order_number:
            return view_func(request, order_number=order_number, *args, **kwargs)
        elif order_code:
            return view_func(request, order_code=order_code, *args, **kwargs)

    return wrapper
