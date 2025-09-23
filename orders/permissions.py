"""
نظام الصلاحيات الشامل لقسم الطلبات
"""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


def get_user_orders_queryset(user):
    """الحصول على queryset الطلبات حسب صلاحيات المستخدم"""
    from .models import Order
    
    if user.is_superuser:
        return Order.objects.all()
    
    # المدير العام يرى جميع الطلبات
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return Order.objects.all()
    
    # مسؤول المصنع يرى جميع الطلبات
    if hasattr(user, 'is_factory_manager') and user.is_factory_manager:
        return Order.objects.all()
    
    # مسؤول المعاينات يرى جميع الطلبات التي تحتوي على معاينة
    if hasattr(user, 'is_inspection_manager') and user.is_inspection_manager:
        return Order.objects.filter(selected_types__icontains='inspection')
    
    # مسؤول التركيبات يرى جميع الطلبات التي تحتوي على تركيب
    if hasattr(user, 'is_installation_manager') and user.is_installation_manager:
        return Order.objects.filter(selected_types__icontains='installation')
    
    # مدير المنطقة يرى طلبات الفروع المُدارة
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        if managed_branches.exists():
            return Order.objects.filter(branch__in=managed_branches)
        else:
            # إذا لم يكن له فروع مُدارة، لا يرى أي طلبات
            return Order.objects.none()
    
    # مدير الفرع يرى طلبات فرعه فقط
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        if hasattr(user, 'branch') and user.branch:
            return Order.objects.filter(branch=user.branch)
        else:
            # إذا لم يكن له فرع، لا يرى أي طلبات
            return Order.objects.none()
    
    # البائع يرى طلباته فقط
    if hasattr(user, 'is_salesperson') and user.is_salesperson:
        return Order.objects.filter(created_by=user)
    
    # فني المعاينة يرى طلبات المعاينة فقط
    if hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        return Order.objects.filter(selected_types__icontains='inspection')

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

    # المدير العام يرى جميع الطلبات
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return True

    # مسؤول المصنع يرى جميع الطلبات
    if hasattr(user, 'is_factory_manager') and user.is_factory_manager:
        return True

    # إذا كان superuser بدون دور محدد، يتبع قواعد البائع
    if user.is_superuser:
        # البحث في الطلبات التي يمكن للمستخدم رؤيتها
        user_orders = get_user_orders_queryset(user)
        return user_orders.filter(id=order.id).exists()
    
    # المدير العام يرى جميع الطلبات
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return True
    
    # مسؤول المصنع يرى جميع الطلبات
    if hasattr(user, 'is_factory_manager') and user.is_factory_manager:
        return True
    
    # مسؤول المعاينات يرى جميع الطلبات التي تحتوي على معاينة
    if hasattr(user, 'is_inspection_manager') and user.is_inspection_manager:
        return 'inspection' in order.get_selected_types_list()
    
    # مسؤول التركيبات يرى جميع الطلبات التي تحتوي على تركيب
    if hasattr(user, 'is_installation_manager') and user.is_installation_manager:
        return 'installation' in order.get_selected_types_list()
    
    # مدير المنطقة يرى طلبات الفروع المُدارة
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        return order.branch in managed_branches
    
    # مدير الفرع يرى طلبات فرعه فقط
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        return hasattr(user, 'branch') and user.branch and order.branch == user.branch
    
    # البائع يرى طلباته فقط
    if hasattr(user, 'is_salesperson') and user.is_salesperson:
        return order.created_by == user
    
    # فني المعاينة يرى طلبات المعاينة فقط
    if hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        return 'inspection' in order.get_selected_types_list()
    
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
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return True
    
    # مسؤول المصنع يمكنه تعديل جميع الطلبات
    if hasattr(user, 'is_factory_manager') and user.is_factory_manager:
        return True
    
    # مسؤول المعاينات يمكنه تعديل الطلبات التي تحتوي على معاينة
    if hasattr(user, 'is_inspection_manager') and user.is_inspection_manager:
        return 'inspection' in order.get_selected_types_list()
    
    # مسؤول التركيبات يمكنه تعديل الطلبات التي تحتوي على تركيب
    if hasattr(user, 'is_installation_manager') and user.is_installation_manager:
        return 'installation' in order.get_selected_types_list()
    
    # مدير المنطقة يمكنه تعديل طلبات الفروع المُدارة
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        return order.branch in managed_branches
    
    # مدير الفرع يمكنه تعديل طلبات فرعه
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        return hasattr(user, 'branch') and user.branch and order.branch == user.branch
    
    # البائع يمكنه تعديل طلباته فقط
    if hasattr(user, 'is_salesperson') and user.is_salesperson:
        return order.created_by == user
    
    # فني المعاينة لا يمكنه تعديل الطلبات
    return False


def can_user_delete_order(user, order):
    """التحقق من إمكانية المستخدم لحذف طلب معين"""
    if user.is_superuser:
        return True
    
    # المدير العام يمكنه حذف جميع الطلبات
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return True
    
    # مسؤول المصنع يمكنه حذف جميع الطلبات
    if hasattr(user, 'is_factory_manager') and user.is_factory_manager:
        return True
    
    # مسؤول المعاينات يمكنه حذف الطلبات التي تحتوي على معاينة
    if hasattr(user, 'is_inspection_manager') and user.is_inspection_manager:
        return 'inspection' in order.get_selected_types_list()
    
    # مسؤول التركيبات يمكنه حذف الطلبات التي تحتوي على تركيب
    if hasattr(user, 'is_installation_manager') and user.is_installation_manager:
        return 'installation' in order.get_selected_types_list()
    
    # مدير المنطقة يمكنه حذف طلبات الفروع المُدارة
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        return order.branch in managed_branches
    
    # مدير الفرع يمكنه حذف طلبات فرعه
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        return hasattr(user, 'branch') and user.branch and order.branch == user.branch
    
    # البائع والفني لا يمكنهم حذف الطلبات
    return False


def can_user_create_order_type(user, order_type):
    """التحقق من إمكانية المستخدم لإنشاء نوع طلب معين"""
    if user.is_superuser:
        return True
    
    # المدير العام يمكنه إنشاء جميع أنواع الطلبات
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return True
    
    # مسؤول المصنع يمكنه إنشاء جميع أنواع الطلبات
    if hasattr(user, 'is_factory_manager') and user.is_factory_manager:
        return True
    
    # مسؤول المعاينات يمكنه إنشاء طلبات المعاينة
    if hasattr(user, 'is_inspection_manager') and user.is_inspection_manager:
        return order_type == 'inspection'
    
    # مسؤول التركيبات يمكنه إنشاء طلبات التركيب
    if hasattr(user, 'is_installation_manager') and user.is_installation_manager:
        return order_type == 'installation'
    
    # مدير المنطقة يمكنه إنشاء جميع أنواع الطلبات
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        return True
    
    # مدير الفرع يمكنه إنشاء جميع أنواع الطلبات
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        return True
    
    # البائع يمكنه إنشاء جميع أنواع الطلبات
    if hasattr(user, 'is_salesperson') and user.is_salesperson:
        return True
    
    # فني المعاينة يمكنه إنشاء طلبات المعاينة فقط
    if hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        return order_type == 'inspection'
    
    return False


def apply_order_permissions(user, orders_queryset):
    """تطبيق الصلاحيات على queryset الطلبات"""
    if user.is_superuser:
        return orders_queryset
    
    # المدير العام يرى جميع الطلبات
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return orders_queryset
    
    # مدير المنطقة يرى طلبات الفروع المُدارة
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        if managed_branches.exists():
            return orders_queryset.filter(branch__in=managed_branches)
        else:
            return orders_queryset.none()
    
    # مدير الفرع يرى طلبات فرعه فقط
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        if hasattr(user, 'branch') and user.branch:
            return orders_queryset.filter(branch=user.branch)
        else:
            return orders_queryset.none()
    
    # البائع يرى طلباته فقط
    if hasattr(user, 'is_salesperson') and user.is_salesperson:
        return orders_queryset.filter(created_by=user)
    
    # فني المعاينة يرى طلبات المعاينة فقط
    if hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        return orders_queryset.filter(selected_types__icontains='inspection')
    
    # المستخدم العادي لا يرى أي طلبات
    return orders_queryset.none()


def get_user_role_permissions(user):
    """الحصول على صلاحيات المستخدم حسب دوره"""
    permissions = {
        'can_view_all_orders': False,
        'can_view_branch_orders': False,
        'can_view_own_orders': False,
        'can_create_orders': False,
        'can_edit_orders': False,
        'can_delete_orders': False,
        'can_manage_dashboard': False,
    }
    
    if user.is_superuser:
        # المدير الأعلى له جميع الصلاحيات
        return {key: True for key in permissions.keys()}
    
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        # المدير العام له جميع الصلاحيات
        return {key: True for key in permissions.keys()}
    
    if hasattr(user, 'is_factory_manager') and user.is_factory_manager:
        # مسؤول المصنع له جميع الصلاحيات
        return {key: True for key in permissions.keys()}
    
    if hasattr(user, 'is_inspection_manager') and user.is_inspection_manager:
        # مسؤول المعاينات له صلاحيات واسعة على طلبات المعاينة
        permissions.update({
            'can_view_all_orders': True,  # يرى جميع طلبات المعاينة
            'can_view_branch_orders': True,
            'can_create_orders': True,
            'can_edit_orders': True,
            'can_delete_orders': True,
            'can_manage_dashboard': True,
        })
        return permissions
    
    if hasattr(user, 'is_installation_manager') and user.is_installation_manager:
        # مسؤول التركيبات له صلاحيات واسعة على طلبات التركيب
        permissions.update({
            'can_view_all_orders': True,  # يرى جميع طلبات التركيب
            'can_view_branch_orders': True,
            'can_create_orders': True,
            'can_edit_orders': True,
            'can_delete_orders': True,
            'can_manage_dashboard': True,
        })
        return permissions
    
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        # مدير المنطقة له صلاحيات واسعة
        permissions.update({
            'can_view_all_orders': False,  # يرى فروعه فقط
            'can_view_branch_orders': True,
            'can_create_orders': True,
            'can_edit_orders': True,
            'can_delete_orders': True,
            'can_manage_dashboard': True,
        })
    
    elif hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        # مدير الفرع له صلاحيات على فرعه
        permissions.update({
            'can_view_branch_orders': True,
            'can_create_orders': True,
            'can_edit_orders': True,
            'can_delete_orders': True,
            'can_manage_dashboard': True,
        })
    
    elif hasattr(user, 'is_salesperson') and user.is_salesperson:
        # البائع له صلاحيات محدودة
        permissions.update({
            'can_view_own_orders': True,
            'can_create_orders': True,
            'can_edit_orders': True,  # طلباته فقط
            'can_manage_dashboard': True,
        })
    
    elif hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        # فني المعاينة له صلاحيات محدودة جداً
        permissions.update({
            'can_view_own_orders': True,  # طلبات المعاينة فقط
            'can_create_orders': True,  # طلبات المعاينة فقط
            'can_manage_dashboard': True,
        })
    
    return permissions