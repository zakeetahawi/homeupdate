"""
صفحة تقارير الأجهزة - Device Reports Dashboard
تتبع شامل لجميع الأجهزة والمشاكل والأخطاء
"""

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Q, Max
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta
from .models import BranchDevice, UnauthorizedDeviceAttempt, ActivityLog, Branch


@staff_member_required
def device_dashboard_view(request):
    """
    لوحة معلومات شاملة للأجهزة
    """
    # إحصائيات عامة
    total_devices = BranchDevice.objects.count()
    active_devices = BranchDevice.objects.filter(is_active=True).count()
    blocked_devices = BranchDevice.objects.filter(is_blocked=True).count()
    inactive_devices = total_devices - active_devices
    
    # الأجهزة المستخدمة مؤخراً (آخر 7 أيام)
    week_ago = timezone.now() - timedelta(days=7)
    recently_used = BranchDevice.objects.filter(
        last_used__gte=week_ago
    ).order_by('-last_used')[:10]
    
    # الأجهزة الخاملة (لم تُستخدم منذ أكثر من 30 يوم)
    month_ago = timezone.now() - timedelta(days=30)
    inactive_long = BranchDevice.objects.filter(
        Q(last_used__lt=month_ago) | Q(last_used__isnull=True),
        is_active=True
    ).count()
    
    # محاولات الوصول غير المصرح بها (آخر 7 أيام)
    unauthorized_attempts = UnauthorizedDeviceAttempt.objects.filter(
        attempted_at__gte=week_ago
    ).order_by('-attempted_at')[:20]
    
    unauthorized_count = UnauthorizedDeviceAttempt.objects.filter(
        attempted_at__gte=week_ago
    ).count()
    
    # الفروع الأكثر نشاطاً
    active_branches = Branch.objects.annotate(
        device_count=Count('branchdevice', filter=Q(branchdevice__is_active=True))
    ).filter(device_count__gt=0).order_by('-device_count')[:10]
    
    # الأجهزة بدون device_token (أجهزة قديمة)
    devices_without_token = BranchDevice.objects.filter(
        Q(device_token__isnull=True) | Q(device_token='')
    ).count()
    
    # الأجهزة بدون fingerprint
    devices_without_fingerprint = BranchDevice.objects.filter(
        Q(device_fingerprint__isnull=True) | Q(device_fingerprint='')
    ).count()
    
    # احصائيات استخدام البصمة vs التوكن (من الـ logs - آخر 100 عملية)
    # Note: يحتاج لتعديل API لتسجيل found_by في جدول منفصل
    
    context = {
        'title': '📊 تقارير الأجهزة - Device Analytics Dashboard',
        'total_devices': total_devices,
        'active_devices': active_devices,
        'blocked_devices': blocked_devices,
        'inactive_devices': inactive_devices,
        'recently_used': recently_used,
        'inactive_long_count': inactive_long,
        'unauthorized_attempts': unauthorized_attempts,
        'unauthorized_count': unauthorized_count,
        'active_branches': active_branches,
        'devices_without_token': devices_without_token,
        'devices_without_fingerprint': devices_without_fingerprint,
        'week_ago': week_ago,
        'month_ago': month_ago,
    }
    
    return render(request, 'admin/accounts/device_dashboard.html', context)


@staff_member_required
def device_detail_report(request, device_id):
    """
    تقرير تفصيلي عن جهاز واحد
    """
    try:
        device = BranchDevice.objects.get(id=device_id)
    except BranchDevice.DoesNotExist:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'الجهاز غير موجود')
        return redirect('accounts:device_dashboard')
    
    # محاولات الوصول غير المصرح بها من هذا الجهاز
    unauthorized = UnauthorizedDeviceAttempt.objects.filter(
        Q(device_fingerprint=device.device_fingerprint) |
        Q(hardware_serial=device.hardware_serial)
    ).order_by('-attempted_at')[:50]
    
    # آخر المستخدمين الذين سجلوا الدخول
    users_logged = device.users_logged.all()
    
    # احصائيات
    total_unauthorized = unauthorized.count()
    last_30_days = timezone.now() - timedelta(days=30)
    unauthorized_last_month = UnauthorizedDeviceAttempt.objects.filter(
        Q(device_fingerprint=device.device_fingerprint) |
        Q(hardware_serial=device.hardware_serial),
        attempted_at__gte=last_30_days
    ).count()
    
    # حساب مدة عدم الاستخدام
    if device.last_used:
        days_inactive = (timezone.now() - device.last_used).days
    else:
        days_inactive = None
    
    context = {
        'title': f'📋 تقرير تفصيلي - {device.device_name}',
        'device': device,
        'unauthorized': unauthorized,
        'users_logged': users_logged,
        'total_unauthorized': total_unauthorized,
        'unauthorized_last_month': unauthorized_last_month,
        'days_inactive': days_inactive,
    }
    
    return render(request, 'admin/accounts/device_detail_report.html', context)
