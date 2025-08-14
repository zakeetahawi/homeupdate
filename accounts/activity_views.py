"""
Views لنظام تتبع النشاط والمستخدمين النشطين
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta
import json

from accounts.models import User
from user_activity.models import OnlineUser, UserActivityLog, UserSession, UserLoginHistory


@login_required
@require_http_methods(["GET"])
def online_users_api(request):
    """API لجلب المستخدمين النشطين حالياً"""
    try:
        # تنظيف المستخدمين غير المتصلين
        OnlineUser.cleanup_offline_users()
        
        # جلب المستخدمين النشطين
        online_users = OnlineUser.get_online_users().select_related('user')
        
        users_data = []
        for online_user in online_users:
            user_data = {
                'id': online_user.user.id,
                'username': online_user.user.username,
                'full_name': online_user.user.get_full_name() or online_user.user.username,
                'role': online_user.user.get_user_role_display(),
                'current_page': online_user.current_page_title or 'غير محدد',
                'online_duration': online_user.online_duration_formatted,
                'last_seen': online_user.last_seen.strftime('%H:%M'),
                'pages_visited': online_user.pages_visited,
                'actions_performed': online_user.actions_performed,
                'device_info': online_user.device_info,
                'avatar_url': online_user.user.image.url if online_user.user.image else None,
            }
            users_data.append(user_data)
        
        return JsonResponse({
            'success': True,
            'users': users_data,
            'total_online': len(users_data),
            'timestamp': timezone.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
def user_activity_dashboard(request):
    """لوحة تحكم نشاط المستخدمين"""
    # إحصائيات عامة
    total_users = User.objects.count()
    online_users_count = OnlineUser.get_online_users().count()
    
    # إحصائيات اليوم
    today = timezone.now().date()
    today_logins = UserLoginHistory.objects.filter(
        login_time__date=today
    ).count()
    
    today_activities = UserActivityLog.objects.filter(
        timestamp__date=today
    ).count()
    
    # أكثر المستخدمين نشاطاً اليوم
    most_active_users = User.objects.filter(
        activity_logs__timestamp__date=today
    ).annotate(
        activity_count=Count('activity_logs')
    ).order_by('-activity_count')[:10]
    
    # أحدث الأنشطة
    recent_activities = UserActivityLog.objects.select_related('user').order_by('-timestamp')[:20]
    
    # المستخدمون النشطون
    online_users = OnlineUser.get_online_users().select_related('user')
    
    context = {
        'total_users': total_users,
        'online_users_count': online_users_count,
        'today_logins': today_logins,
        'today_activities': today_activities,
        'most_active_users': most_active_users,
        'recent_activities': recent_activities,
        'online_users': online_users,
    }
    
    return render(request, 'accounts/activity_dashboard.html', context)


@staff_member_required
def user_activity_detail(request, user_id):
    """تفاصيل نشاط مستخدم معين"""
    user = get_object_or_404(User, id=user_id)
    
    # فلترة حسب التاريخ
    date_filter = request.GET.get('date', 'today')
    if date_filter == 'today':
        start_date = timezone.now().date()
        end_date = start_date
    elif date_filter == 'week':
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
    elif date_filter == 'month':
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
    else:
        start_date = None
        end_date = None
    
    # جلب الأنشطة
    activities = UserActivityLog.objects.filter(user=user)
    if start_date and end_date:
        activities = activities.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        )
    
    # فلترة حسب نوع النشاط
    activity_type = request.GET.get('type')
    if activity_type:
        activities = activities.filter(action_type=activity_type)
    
    # ترتيب وتقسيم الصفحات
    activities = activities.order_by('-timestamp')
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات المستخدم
    user_stats = {
        'total_activities': activities.count(),
        'login_count': UserLoginHistory.objects.filter(user=user).count(),
        'last_login': UserLoginHistory.objects.filter(user=user).order_by('-login_time').first(),
        'is_online': hasattr(user, 'online_status') and user.online_status.is_online,
    }
    
    # أنواع الأنشطة المتاحة للفلترة
    activity_types = UserActivityLog.ACTION_TYPES
    
    context = {
        'target_user': user,
        'activities': page_obj,
        'user_stats': user_stats,
        'activity_types': activity_types,
        'current_filters': {
            'date': date_filter,
            'type': activity_type,
        }
    }
    
    return render(request, 'accounts/user_activity_detail.html', context)


@staff_member_required
def activity_logs_list(request):
    """قائمة جميع سجلات النشاط"""
    # فلاتر البحث
    search_query = request.GET.get('search', '')
    user_filter = request.GET.get('user')
    action_filter = request.GET.get('action')
    date_filter = request.GET.get('date', 'today')
    
    # بناء الاستعلام
    activities = UserActivityLog.objects.select_related('user').all()
    
    # فلترة حسب البحث
    if search_query:
        activities = activities.filter(
            Q(user__username__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(url_path__icontains=search_query)
        )
    
    # فلترة حسب المستخدم
    if user_filter:
        activities = activities.filter(user_id=user_filter)
    
    # فلترة حسب نوع النشاط
    if action_filter:
        activities = activities.filter(action_type=action_filter)
    
    # فلترة حسب التاريخ
    if date_filter == 'today':
        activities = activities.filter(timestamp__date=timezone.now().date())
    elif date_filter == 'week':
        week_ago = timezone.now() - timedelta(days=7)
        activities = activities.filter(timestamp__gte=week_ago)
    elif date_filter == 'month':
        month_ago = timezone.now() - timedelta(days=30)
        activities = activities.filter(timestamp__gte=month_ago)
    
    # ترتيب وتقسيم الصفحات
    activities = activities.order_by('-timestamp')
    paginator = Paginator(activities, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # بيانات للفلاتر
    users = User.objects.filter(activity_logs__isnull=False).distinct()
    action_types = UserActivityLog.ACTION_TYPES
    
    context = {
        'activities': page_obj,
        'users': users,
        'action_types': action_types,
        'current_filters': {
            'search': search_query,
            'user': user_filter,
            'action': action_filter,
            'date': date_filter,
        }
    }
    
    return render(request, 'accounts/activity_logs_list.html', context)


@staff_member_required
def login_history_list(request):
    """قائمة سجلات تسجيل الدخول"""
    # فلاتر البحث
    user_filter = request.GET.get('user')
    date_filter = request.GET.get('date', 'week')
    
    # بناء الاستعلام
    logins = UserLoginHistory.objects.select_related('user').all()
    
    # فلترة حسب المستخدم
    if user_filter:
        logins = logins.filter(user_id=user_filter)
    
    # فلترة حسب التاريخ
    if date_filter == 'today':
        logins = logins.filter(login_time__date=timezone.now().date())
    elif date_filter == 'week':
        week_ago = timezone.now() - timedelta(days=7)
        logins = logins.filter(login_time__gte=week_ago)
    elif date_filter == 'month':
        month_ago = timezone.now() - timedelta(days=30)
        logins = logins.filter(login_time__gte=month_ago)
    
    # ترتيب وتقسيم الصفحات
    logins = logins.order_by('-login_time')
    paginator = Paginator(logins, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # بيانات للفلاتر
    users = User.objects.filter(login_history__isnull=False).distinct()
    
    context = {
        'logins': page_obj,
        'users': users,
        'current_filters': {
            'user': user_filter,
            'date': date_filter,
        }
    }
    
    return render(request, 'accounts/login_history_list.html', context)


@login_required
@require_http_methods(["POST"])
def update_current_page(request):
    """تحديث الصفحة الحالية للمستخدم"""
    try:
        data = json.loads(request.body)
        page_path = data.get('page_path', '')
        page_title = data.get('page_title', '')
        
        # تحديث المستخدم المتصل
        online_user, created = OnlineUser.objects.get_or_create(
            user=request.user,
            defaults={
                'ip_address': request.META.get('REMOTE_ADDR', ''),
                'session_key': request.session.session_key,
                'login_time': timezone.now(),
            }
        )
        
        online_user.update_activity(
            page_path=page_path,
            page_title=page_title
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
