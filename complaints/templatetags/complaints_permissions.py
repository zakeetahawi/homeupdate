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
    يظهر فقط لمدير النظام أو من لديه دور "مدير" (Managers)
    """
    if not user or not user.is_authenticated:
        return False

    # مدير النظام يرى أزرار الشكاوى
    if user.is_superuser:
        return True

    # فقط مجموعة Managers (المدراء)
    if user.groups.filter(name="Managers").exists():
        return True

    return False


@register.filter
def has_assignment_permissions(user):
    """
    فحص ما إذا كان المستخدم له صلاحيات للوصول إلى إشعارات التعيين
    يظهر فقط لمدير النظام أو من لديه دور "مدير" (Managers)
    """
    if not user or not user.is_authenticated:
        return False

    # مدير النظام يرى إشعارات التعيين
    if user.is_superuser:
        return True

    # فقط مجموعة Managers (المدراء)
    if user.groups.filter(name="Managers").exists():
        return True

    return False


@register.simple_tag
def user_complaints_role(user):
    """
    إرجاع دور المستخدم في نظام الشكاوى
    """
    if not user or not user.is_authenticated:
        return "none"

    if user.is_superuser:
        return "superuser"

    if user.groups.filter(name="Complaints_Managers").exists():
        return "manager"

    if user.groups.filter(name="Complaints_Supervisors").exists():
        return "supervisor"

    if user.groups.filter(name="Managers").exists():
        return "general_manager"

    try:
        permissions = user.complaint_permissions
        if permissions.is_active:
            if permissions.can_edit_all_complaints:
                return "editor"
            elif permissions.can_be_assigned_complaints:
                return "assignee"
            else:
                return "viewer"
    except Exception:
        pass

    return "none"
