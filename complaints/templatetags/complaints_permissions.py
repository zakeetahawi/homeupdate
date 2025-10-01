"""
Template tags لفحص صلاحيات الشكاوى
"""
from django import template
from django.contrib.auth.models import Group

register = template.Library()


@register.filter
def has_complaints_permissions(user):
    """
    فحص ما إذا كان المستخدم له صلاحيات للوصول إلى إشعارات الشكاوى
    يظهر فقط للمستخدمين في المجموعات الإدارية أو لديهم صلاحيات مخصصة
    (لا يظهر لمدير النظام إلا إذا كان في مجموعة إدارية)
    """
    if not user or not user.is_authenticated:
        return False

    # فحص المجموعات الإدارية فقط (بدون superuser)
    admin_groups = ['Complaints_Supervisors', 'Managers', 'Complaints_Managers']
    if user.groups.filter(name__in=admin_groups).exists():
        return True

    # فحص صلاحيات الشكاوى المخصصة
    try:
        permissions = user.complaint_permissions
        if permissions.is_active and (
            permissions.can_be_assigned_complaints or
            permissions.can_escalate_complaints or
            permissions.can_view_all_complaints or
            permissions.can_edit_all_complaints
        ):
            return True
    except:
        pass

    return False


@register.filter
def has_assignment_permissions(user):
    """
    فحص ما إذا كان المستخدم له صلاحيات للوصول إلى إشعارات التعيين
    يظهر فقط للمستخدمين في المجموعات الإدارية أو لديهم صلاحيات مخصصة
    (لا يظهر لمدير النظام إلا إذا كان في مجموعة إدارية)
    """
    if not user or not user.is_authenticated:
        return False

    # فحص المجموعات الإدارية فقط (بدون superuser)
    admin_groups = ['Complaints_Supervisors', 'Managers', 'Complaints_Managers']
    if user.groups.filter(name__in=admin_groups).exists():
        return True

    # فحص صلاحيات التعيين والتصعيد المخصصة
    try:
        permissions = user.complaint_permissions
        if permissions.is_active and (
            permissions.can_assign_complaints or
            permissions.can_escalate_complaints or
            permissions.can_be_assigned_complaints
        ):
            return True
    except:
        pass

    return False


@register.simple_tag
def user_complaints_role(user):
    """
    إرجاع دور المستخدم في نظام الشكاوى
    """
    if not user or not user.is_authenticated:
        return 'none'
    
    if user.is_superuser:
        return 'superuser'
    
    if user.groups.filter(name='Complaints_Managers').exists():
        return 'manager'
    
    if user.groups.filter(name='Complaints_Supervisors').exists():
        return 'supervisor'
    
    if user.groups.filter(name='Managers').exists():
        return 'general_manager'
    
    try:
        permissions = user.complaint_permissions
        if permissions.is_active:
            if permissions.can_edit_all_complaints:
                return 'editor'
            elif permissions.can_be_assigned_complaints:
                return 'assignee'
            else:
                return 'viewer'
    except:
        pass
    
    return 'none'
