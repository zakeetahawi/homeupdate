"""
تحسينات الأداء للوحة الإدارة
"""

from datetime import timedelta
from functools import wraps

from django.core.cache import cache
from django.db import models
from django.utils import timezone


def cache_queryset(timeout=300):
    """Decorator لتخزين نتائج الاستعلامات مؤقتاً"""

    def decorator(func):
        @wraps(func)
        def wrapper(self, request):
            # إنشاء مفتاح cache مبني على المستخدم والمعاملات
            cache_key = f"admin_queryset_{self.__class__.__name__}_{request.user.id}_{hash(str(request.GET))}"

            result = cache.get(cache_key)
            if result is None:
                result = func(self, request)
                cache.set(cache_key, result, timeout)

            return result

        return wrapper

    return decorator


class PerformanceMixin:
    """Mixin لتحسين أداء admin interfaces"""

    def get_queryset(self, request):
        """تحسين الاستعلامات مع تخزين مؤقت"""
        queryset = super().get_queryset(request)

        # إضافة only() للحقول المطلوبة فقط
        if hasattr(self, "performance_only_fields"):
            queryset = queryset.only(*self.performance_only_fields)

        # إضافة select_related للعلاقات
        if hasattr(self, "performance_select_related"):
            queryset = queryset.select_related(*self.performance_select_related)

        # إضافة prefetch_related للعلاقات المُعقدة
        if hasattr(self, "performance_prefetch_related"):
            queryset = queryset.prefetch_related(*self.performance_prefetch_related)

        return queryset

    def changelist_view(self, request, extra_context=None):
        """تحسين عرض قائمة التغييرات"""
        # تخزين مؤقت لإحصائيات الصفحة
        extra_context = extra_context or {}

        # إضافة معلومات الأداء
        cache_key = f"admin_stats_{self.__class__.__name__}_{request.user.id}"
        stats = cache.get(cache_key)

        if stats is None:
            # حساب الإحصائيات
            queryset = self.get_queryset(request)
            stats = {
                "total_count": queryset.count(),
                "recent_count": (
                    queryset.filter(
                        created_at__gte=timezone.now() - timedelta(days=7)
                    ).count()
                    if hasattr(queryset.model, "created_at")
                    else 0
                ),
            }
            cache.set(cache_key, stats, 60)  # cache لمدة دقيقة

        extra_context.update(stats)

        return super().changelist_view(request, extra_context)


# تطبيق التحسينات على النماذج الرئيسية
def optimize_admin_performance():
    """تطبيق تحسينات الأداء على جميع admin classes"""
    from django.contrib import admin

    from customers.models import Customer
    from inspections.models import Inspection
    from manufacturing.models import ManufacturingOrder
    from orders.models import Order

    # إضافة pagination كبيرة للجداول الكبيرة
    for model_admin in [
        admin.site._registry.get(Order),
        admin.site._registry.get(Customer),
        admin.site._registry.get(ManufacturingOrder),
        admin.site._registry.get(Inspection),
    ]:
        if model_admin:
            model_admin.list_per_page = 25  # تقليل العدد لتحسين الأداء
            model_admin.list_max_show_all = 100  # حد أقصى للعرض الكامل
