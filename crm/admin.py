"""
تخصيص لوحة تحكم Django Admin مع Jazzmin
"""

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect


# تطبيق الإعدادات على الموقع الافتراضي
admin.site.site_header = "نظام إدارة الخواجة"
admin.site.site_title = "لوحة التحكم"
admin.site.index_title = "مرحباً بك في نظام إدارة الخواجة"


def get_admin_stats():
    """إحصائيات سريعة للوحة التحكم"""
    try:
        from customers.models import Customer
        from orders.models import Order
        from inspections.models import Inspection
        from manufacturing.models import ManufacturingOrder
        
        stats = {
            'total_customers': Customer.objects.count(),
            'total_orders': Order.objects.count(),
            'pending_inspections': Inspection.objects.filter(status='pending').count(),
            'active_manufacturing': ManufacturingOrder.objects.filter(status='in_progress').count(),
        }
        return stats
    except Exception:
        return {
            'total_customers': 0,
            'total_orders': 0,
            'pending_inspections': 0,
            'active_manufacturing': 0,
        }


def admin_dashboard_view(request):
    """عرض لوحة تحكم مخصصة"""
    if not request.user.is_staff:
        return HttpResponseRedirect(reverse('admin:login'))
    
    # إعادة توجيه إلى الصفحة الرئيسية للإدارة
    return HttpResponseRedirect(reverse('admin:index'))


# تخصيص إضافي للـ admin site
class JazzminAdminConfig:
    """إعدادات إضافية لـ Jazzmin"""
    
    @staticmethod
    def get_dashboard_stats():
        """إحصائيات للوحة التحكم"""
        return get_admin_stats()
    
    @staticmethod
    def get_recent_actions():
        """الإجراءات الأخيرة"""
        try:
            from django.contrib.admin.models import LogEntry
            return LogEntry.objects.select_related('content_type', 'user').order_by('-action_time')[:10]
        except Exception:
            return []
