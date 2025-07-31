
from django.db import models
"""
نظام الصلاحيات الشامل لقسم العملاء
"""


def get_user_customers_queryset(user):
    """الحصول على queryset العملاء حسب صلاحيات المستخدم"""
    from .models import Customer
    
    if user.is_superuser:
        return Customer.objects.all()
    
    # المدير العام يرى جميع العملاء
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return Customer.objects.all()
    
    # مدير المنطقة يرى عملاء الفروع المُدارة
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        if managed_branches.exists():
            return Customer.objects.filter(branch__in=managed_branches)
        else:
            # إذا لم يكن له فروع مُدارة، لا يرى أي عملاء
            return Customer.objects.none()
    
    # مدير الفرع يرى عملاء فرعه فقط
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        if hasattr(user, 'branch') and user.branch:
            return Customer.objects.filter(branch=user.branch)
        else:
            # إذا لم يكن له فرع، لا يرى أي عملاء
            return Customer.objects.none()
    
    # البائع يرى عملاء فرعه أو العملاء الذين أنشأهم
    if hasattr(user, 'is_salesperson') and user.is_salesperson:
        if hasattr(user, 'branch') and user.branch:
            # يرى عملاء فرعه والعملاء الذين أنشأهم
            return Customer.objects.filter(
                models.Q(branch=user.branch) | models.Q(created_by=user)
            )
        else:
            # إذا لم يكن له فرع، يرى العملاء الذين أنشأهم فقط
            return Customer.objects.filter(created_by=user)
    
    # فني المعاينة يرى عملاء فرعه فقط (للقراءة)
    if hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        if hasattr(user, 'branch') and user.branch:
            return Customer.objects.filter(branch=user.branch)
        else:
            return Customer.objects.none()
    
    # المستخدم العادي يرى العملاء الذين أنشأهم فقط
    if hasattr(user, 'branch') and user.branch:
        return Customer.objects.filter(
            models.Q(branch=user.branch) | models.Q(created_by=user)
        )
    else:
        return Customer.objects.filter(created_by=user)


def can_user_view_customer(user, customer):
    """التحقق من إمكانية المستخدم لعرض عميل معين"""
    if user.is_superuser:
        return True
    
    # المدير العام يرى جميع العملاء
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return True
    
    # مدير المنطقة يرى عملاء الفروع المُدارة
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        return customer.branch in managed_branches
    
    # مدير الفرع يرى عملاء فرعه فقط
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        return hasattr(user, 'branch') and user.branch and customer.branch == user.branch
    
    # البائع يرى عملاء فرعه أو العملاء الذين أنشأهم
    if hasattr(user, 'is_salesperson') and user.is_salesperson:
        return (customer.created_by == user or 
                (hasattr(user, 'branch') and user.branch and customer.branch == user.branch))
    
    # فني المعاينة يرى ��ملاء فرعه فقط
    if hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        return hasattr(user, 'branch') and user.branch and customer.branch == user.branch
    
    # المستخدم العادي يرى العملاء الذين أنشأهم أو عملاء فرعه
    return (customer.created_by == user or 
            (hasattr(user, 'branch') and user.branch and customer.branch == user.branch))


def can_user_edit_customer(user, customer):
    """التحقق من إمكانية المستخدم لتعديل عميل معين"""
    if user.is_superuser:
        return True
    
    # المدير العام يمكنه تعديل جميع العملاء
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return True
    
    # مدير المنطقة يمكنه تعديل عملاء الفروع المُدارة
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        return customer.branch in managed_branches
    
    # مدير الفرع يمكنه تعديل عملاء فرعه
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        return hasattr(user, 'branch') and user.branch and customer.branch == user.branch
    
    # البائع يمكنه تعديل العملاء الذين أنشأهم أو عملاء فرعه
    if hasattr(user, 'is_salesperson') and user.is_salesperson:
        return (customer.created_by == user or 
                (hasattr(user, 'branch') and user.branch and customer.branch == user.branch))
    
    # فني المعاينة لا يمكنه تعديل العملاء
    if hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        return False
    
    # المستخدم العادي يمكنه تعديل العملاء الذين أنشأهم فقط
    return customer.created_by == user


def can_user_delete_customer(user, customer):
    """التحقق من إمكانية المستخدم لحذف عميل معين"""
    if user.is_superuser:
        return True
    
    # المدير العام يمكنه حذف جميع العملاء
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return True
    
    # مدير المنطقة يمكنه حذف عملاء الفروع المُدارة
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        return customer.branch in managed_branches
    
    # مدير الفرع يمكنه حذف عملاء فرعه
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        return hasattr(user, 'branch') and user.branch and customer.branch == user.branch
    
    # البائع وفني المعاينة لا يمكنهم حذف العملاء
    return False


def can_user_create_customer(user):
    """التحقق من إمكانية المستخدم لإنشاء عميل جديد"""
    if user.is_superuser:
        return True
    
    # المدير العام يمكنه إنشاء عملاء
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return True
    
    # مدير المنطقة يمكنه إنشاء عملاء
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        return True
    
    # مدير الفرع يمكنه إنشاء عملاء
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        return True
    
    # البائع يمكنه إنشاء عملاء
    if hasattr(user, 'is_salesperson') and user.is_salesperson:
        return True
    
    # فني المعاينة لا يمكنه إنشاء عملاء
    if hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        return False
    
    # المستخدم العادي يمكنه إنشاء عملاء
    return True


def apply_customer_permissions(user, customers_queryset):
    """تطبيق الصلاحيات على queryset العملاء"""
    if user.is_superuser:
        return customers_queryset
    
    # المدير العام يرى جميع العملاء
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        return customers_queryset
    
    # مدير المنطقة يرى عملاء الفروع المُدارة
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        managed_branches = user.managed_branches.all()
        if managed_branches.exists():
            return customers_queryset.filter(branch__in=managed_branches)
        else:
            return customers_queryset.none()
    
    # مدير الفرع يرى عملاء فرعه فقط
    if hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        if hasattr(user, 'branch') and user.branch:
            return customers_queryset.filter(branch=user.branch)
        else:
            return customers_queryset.none()
    
    # البائع يرى عملاء فرعه أو ا��عملاء الذين أنشأهم
    if hasattr(user, 'is_salesperson') and user.is_salesperson:
        from django.db import models
        if hasattr(user, 'branch') and user.branch:
            return customers_queryset.filter(
                models.Q(branch=user.branch) | models.Q(created_by=user)
            )
        else:
            return customers_queryset.filter(created_by=user)
    
    # فني المعاينة يرى عملاء فرعه فقط
    if hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        if hasattr(user, 'branch') and user.branch:
            return customers_queryset.filter(branch=user.branch)
        else:
            return customers_queryset.none()
    
    # المستخدم العادي يرى العملاء الذين أنشأهم أو عملاء فرعه
    from django.db import models
    if hasattr(user, 'branch') and user.branch:
        return customers_queryset.filter(
            models.Q(branch=user.branch) | models.Q(created_by=user)
        )
    else:
        return customers_queryset.filter(created_by=user)


def get_user_customer_permissions(user):
    """الحصول على صلاحيات المستخدم في قسم العملاء"""
    permissions = {
        'can_view_all_customers': False,
        'can_view_branch_customers': False,
        'can_view_own_customers': False,
        'can_create_customers': False,
        'can_edit_customers': False,
        'can_delete_customers': False,
        'can_export_customers': False,
    }
    
    if user.is_superuser:
        # المدير الأعلى له جميع الصلاحيات
        return {key: True for key in permissions.keys()}
    
    if hasattr(user, 'is_general_manager') and user.is_general_manager:
        # المدير العام له جميع الصلاحيات
        return {key: True for key in permissions.keys()}
    
    if hasattr(user, 'is_region_manager') and user.is_region_manager:
        # مدير المنطقة له صلاحيات واسعة
        permissions.update({
            'can_view_all_customers': False,  # يرى فروعه فقط
            'can_view_branch_customers': True,
            'can_create_customers': True,
            'can_edit_customers': True,
            'can_delete_customers': True,
            'can_export_customers': True,
        })
    
    elif hasattr(user, 'is_branch_manager') and user.is_branch_manager:
        # مدير الفرع له صلاحيات على فرعه
        permissions.update({
            'can_view_branch_customers': True,
            'can_create_customers': True,
            'can_edit_customers': True,
            'can_delete_customers': True,
            'can_export_customers': True,
        })
    
    elif hasattr(user, 'is_salesperson') and user.is_salesperson:
        # البائع له صلاحيات محدودة
        permissions.update({
            'can_view_branch_customers': True,
            'can_view_own_customers': True,
            'can_create_customers': True,
            'can_edit_customers': True,  # عملاؤه وعملاء فرعه
        })
    
    elif hasattr(user, 'is_inspection_technician') and user.is_inspection_technician:
        # فني المعاينة له صلاحيات محدودة جداً
        permissions.update({
            'can_view_branch_customers': True,  # للقراءة فقط
        })
    
    else:
        # المستخدم العادي
        permissions.update({
            'can_view_own_customers': True,
            'can_create_customers': True,
            'can_edit_customers': True,  # عملاؤه فقط
        })
    
    return permissions