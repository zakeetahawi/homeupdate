from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class DepartmentRequiredMixin(UserPassesTestMixin):
    """
    مخلط للتحقق من أن المستخدم ينتمي إلى قسم معين
    """

    department_code = None  # يجب تعريفه في الفئة الفرعية
    permission_denied_message = _("ليس لديك صلاحية للوصول إلى هذه الصفحة")

    def test_func(self):
        # السماح للمستخدم المشرف بالوصول إلى جميع الصفحات
        if self.request.user.is_superuser:
            return True

        # التحقق من أن المستخدم ينتمي إلى القسم المطلوب
        if not self.department_code:
            return False

        user_departments = self.request.user.departments.values_list("code", flat=True)
        return self.department_code in user_departments

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return redirect(reverse_lazy("home"))


class PermissionRequiredMixin(UserPassesTestMixin):
    """
    مخلط للتحقق من أن المستخدم لديه صلاحية معينة
    """

    required_permission = None  # يجب تعريفه في الفئة الفرعية
    permission_denied_message = _("ليس لديك صلاحية للوصول إلى هذه الصفحة")

    def test_func(self):
        # السماح للمستخدم المشرف بالوصول إلى جميع الصفحات
        if self.request.user.is_superuser:
            return True

        # التحقق من أن المستخدم لديه الصلاحية المطلوبة
        if not self.required_permission:
            return False

        return self.request.user.has_perm(self.required_permission)

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return redirect(reverse_lazy("home"))


class BranchAccessMixin(UserPassesTestMixin):
    """
    مخلط للتحقق من أن المستخدم ينتمي إلى نفس الفرع
    """

    permission_denied_message = _("ليس لديك صلاحية للوصول إلى بيانات فرع آخر")

    def test_func(self):
        # السماح للمستخدم المشرف بالوصول إلى جميع الصفحات
        if self.request.user.is_superuser:
            return True

        # الحصول على الكائن
        obj = self.get_object()

        # التحقق من أن الكائن له حقل branch
        if not hasattr(obj, "branch"):
            return True

        # التحقق من أن المستخدم ينتمي إلى نفس الفرع
        return obj.branch == self.request.user.branch

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return redirect(reverse_lazy("home"))


class StaffRequiredMixin(UserPassesTestMixin):
    """
    مخلط للتحقق من أن المستخدم من طاقم الإدارة
    """

    permission_denied_message = _("هذه الصفحة متاحة فقط لطاقم الإدارة")

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return redirect(reverse_lazy("home"))
