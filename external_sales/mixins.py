from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class DecoratorDeptRequiredMixin(LoginRequiredMixin):
    """Allow only decorator dept staff, managers, and superusers"""

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (
            user.is_superuser
            or user.is_decorator_dept_manager
            or user.is_decorator_dept_staff
            or user.is_sales_manager
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class DecoratorManagerRequiredMixin(LoginRequiredMixin):
    """Allow only decorator dept managers and superusers"""

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (
            user.is_superuser
            or user.is_decorator_dept_manager
            or user.is_sales_manager
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
