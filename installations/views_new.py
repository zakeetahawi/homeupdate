"""
عروض النظام الجديد للتركيبات
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from datetime import datetime, timedelta
import json

from .models_new import (
    InstallationNew, 
    InstallationTeamNew, 
    InstallationTechnician,
    InstallationAlert,
    DailyInstallationReport
)
from .services.calendar_service import CalendarService
from .services.alert_system import AlertSystem
from .services.technician_analytics import TechnicianAnalyticsService
from .services.analytics_engine import AnalyticsEngine
from .services.order_completion import OrderCompletionService


@login_required
def installations_dashboard(request):
    """لوحة التحكم الرئيسية للتركيبات"""
    
    try:
        # الحصول على إحصائيات سريعة
        today = timezone.now().date()
        
        # إحصائيات اليوم
        today_installations = InstallationNew.objects.filter(scheduled_date=today)
        today_stats = {
            'total': today_installations.count(),
            'completed': today_installations.filter(status='completed').count(),
            'scheduled': today_installations.filter(status='scheduled').count(),
            'pending': today_installations.filter(status='pending').count(),
        }
        
        # إحصائيات للبطاقات التفاعلية
        pending_installations_count = InstallationNew.objects.filter(status='pending').count()
        in_progress_installations_count = InstallationNew.objects.filter(status='in_progress').count()
        completed_installations_count = InstallationNew.objects.filter(status='completed').count()
        overdue_installations_count = InstallationNew.objects.filter(
            scheduled_date__lt=today,
            status__in=['pending', 'scheduled']
        ).count()

        # التركيبات الأخيرة
        recent_installations = InstallationNew.objects.all().order_by('-created_at')[:6]

        # إحصائيات عامة
        total_stats = {
            'total_installations': InstallationNew.objects.count(),
            'active_teams': InstallationTeamNew.objects.filter(is_active=True).count(),
            'active_technicians': InstallationTechnician.objects.filter(is_active=True).count(),
        }

        # الإنذارات النشطة
        active_alerts = InstallationAlert.objects.filter(
            is_resolved=False
        ).order_by('-severity', '-created_at')[:5]

        context = {
            'today_stats': today_stats,
            'total_stats': total_stats,
            'active_alerts': active_alerts,
            'today_date': today,
            'pending_installations_count': pending_installations_count,
            'in_progress_installations_count': in_progress_installations_count,
            'completed_installations_count': completed_installations_count,
            'overdue_installations_count': overdue_installations_count,
            'recent_installations': recent_installations,
        }
        
        return render(request, 'installations/dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f'خطأ في تحميل لوحة التحكم: {str(e)}')
        return render(request, 'installations/dashboard.html', {})


@login_required
def installations_list(request):
    """قائمة التركيبات مع فلترة وبحث"""
    
    try:
        # الحصول على جميع التركيبات
        installations = InstallationNew.objects.select_related(
            'team', 'order'
        ).order_by('-created_at')
        
        # تطبيق الفلاتر
        status_filter = request.GET.get('status')
        if status_filter:
            installations = installations.filter(status=status_filter)
        
        priority_filter = request.GET.get('priority')
        if priority_filter:
            installations = installations.filter(priority=priority_filter)
        
        branch_filter = request.GET.get('branch')
        if branch_filter:
            installations = installations.filter(branch_name=branch_filter)
        
        team_filter = request.GET.get('team')
        if team_filter:
            installations = installations.filter(team_id=team_filter)
        
        # البحث
        search_query = request.GET.get('search')
        if search_query:
            installations = installations.filter(
                Q(customer_name__icontains=search_query) |
                Q(customer_phone__icontains=search_query) |
                Q(id__icontains=search_query)
            )
        
        # التقسيم إلى صفحات
        paginator = Paginator(installations, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # الحصول على قوائم الفلاتر
        teams = InstallationTeamNew.objects.filter(is_active=True)
        branches = InstallationNew.objects.values_list(
            'branch_name', flat=True
        ).distinct()

        # حساب الإحصائيات
        all_installations = InstallationNew.objects.all()
        total_count = all_installations.count()
        pending_count = all_installations.filter(status='pending').count()
        scheduled_count = all_installations.filter(status='scheduled').count()
        completed_count = all_installations.filter(status='completed').count()

        context = {
            'installations': page_obj,
            'page_obj': page_obj,
            'teams': teams,
            'branches': branches,
            'total_count': total_count,
            'pending_count': pending_count,
            'scheduled_count': scheduled_count,
            'completed_count': completed_count,
            'is_paginated': page_obj.has_other_pages(),
            'current_filters': {
                'status': status_filter,
                'priority': priority_filter,
                'branch': branch_filter,
                'team': team_filter,
                'search': search_query,
            }
        }
        
        return render(request, 'installations/list.html', context)
        
    except Exception as e:
        messages.error(request, f'خطأ في تحميل قائمة التركيبات: {str(e)}')
        return render(request, 'installations/list.html', {})


@login_required
def create_installation(request):
    """إنشاء تركيب جديد"""
    from .forms_new import InstallationForm

    if request.method == 'POST':
        form = InstallationForm(request.POST)
        if form.is_valid():
            try:
                installation = form.save(commit=False)
                installation.created_by = request.user

                # ربط التركيب بالطلب إذا تم اختياره
                selected_order = form.cleaned_data.get('order')
                if selected_order:
                    installation.order = selected_order

                installation.save()

                messages.success(request, f'تم إنشاء التركيب #{installation.id} بنجاح')
                return redirect('installations_new:detail', installation.id)

            except Exception as e:
                messages.error(request, f'خطأ في إنشاء التركيب: {str(e)}')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = InstallationForm()

    context = {
        'form': form,
    }

    return render(request, 'installations/create_simple.html', context)


@login_required
def installation_detail(request, installation_id):
    """تفاصيل التركيب"""
    
    try:
        installation = get_object_or_404(
            InstallationNew.objects.select_related('team', 'order'),
            id=installation_id
        )
        
        # الحصول على سجل الإكمال إذا كان متاحاً
        completion_log = getattr(installation, 'completion_log', None)
        
        # الحصول على الإنذارات المرتبطة
        related_alerts = InstallationAlert.objects.filter(
            installation=installation
        ).order_by('-created_at')
        
        context = {
            'installation': installation,
            'completion_log': completion_log,
            'related_alerts': related_alerts,
        }
        
        return render(request, 'installations/detail.html', context)
        
    except Exception as e:
        messages.error(request, f'خطأ في تحميل تفاصيل التركيب: {str(e)}')
        return redirect('installations:list')


@login_required
def edit_installation(request, installation_id):
    """تعديل التركيب"""
    
    try:
        installation = get_object_or_404(InstallationNew, id=installation_id)
        
        if request.method == 'POST':
            # تحديث البيانات
            data = request.POST
            
            installation.customer_name = data.get('customer_name', installation.customer_name)
            installation.customer_phone = data.get('customer_phone', installation.customer_phone)
            installation.customer_address = data.get('customer_address', installation.customer_address)
            installation.salesperson_name = data.get('salesperson_name', installation.salesperson_name)
            installation.branch_name = data.get('branch_name', installation.branch_name)
            installation.windows_count = int(data.get('windows_count', installation.windows_count))
            installation.location_type = data.get('location_type', installation.location_type)
            installation.priority = data.get('priority', installation.priority)
            installation.notes = data.get('notes', installation.notes)
            installation.updated_by = request.user
            
            # تحديث التواريخ والأوقات
            if data.get('scheduled_date'):
                installation.scheduled_date = data.get('scheduled_date')
            if data.get('scheduled_time_start'):
                installation.scheduled_time_start = data.get('scheduled_time_start')
            if data.get('scheduled_time_end'):
                installation.scheduled_time_end = data.get('scheduled_time_end')
            
            # تحديث الفريق
            team_id = data.get('team')
            if team_id:
                team = InstallationTeamNew.objects.get(id=team_id)
                installation.team = team
            
            installation.save()
            
            messages.success(request, 'تم تحديث التركيب بنجاح')
            return redirect('installations:detail', installation_id=installation.id)
        
        # عرض نموذج التعديل
        teams = InstallationTeamNew.objects.filter(is_active=True)
        branches = InstallationNew.objects.values_list(
            'branch_name', flat=True
        ).distinct()
        
        context = {
            'installation': installation,
            'teams': teams,
            'branches': branches,
        }
        
        return render(request, 'installations/edit.html', context)
        
    except Exception as e:
        messages.error(request, f'خطأ في تعديل التركيب: {str(e)}')
        return redirect('installations:detail', installation_id=installation_id)


@login_required
def smart_calendar_view(request):
    """عرض التقويم الذكي"""
    
    try:
        # الحصول على التاريخ المطلوب
        date_str = request.GET.get('date')
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()
        
        # الحصول على بيانات التقويم للشهر
        month_data = CalendarService.get_month_calendar(
            target_date.year, 
            target_date.month
        )
        
        context = {
            'month_data': month_data,
            'current_date': target_date,
            'today': timezone.now().date(),
        }
        
        return render(request, 'installations/smart_calendar.html', context)
        
    except Exception as e:
        messages.error(request, f'خطأ في تحميل التقويم: {str(e)}')
        return render(request, 'installations/smart_calendar.html', {})


@login_required
def technician_analytics_view(request):
    """عرض تحليل أداء الفنيين"""
    
    try:
        # الحصول على قائمة الفنيين
        technicians = InstallationTechnician.objects.filter(is_active=True)
        
        # الحصول على قائمة الفروع
        branches = InstallationNew.objects.values_list(
            'branch_name', flat=True
        ).distinct()
        
        # إحصائيات سريعة
        summary = TechnicianAnalyticsService.get_summary_statistics()
        
        context = {
            'technicians': technicians,
            'branches': branches,
            'summary': summary,
            'default_start_date': (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'default_end_date': timezone.now().date().strftime('%Y-%m-%d'),
        }
        
        return render(request, 'installations/technician_analytics.html', context)
        
    except Exception as e:
        messages.error(request, f'خطأ في تحميل تحليل الفنيين: {str(e)}')
        return render(request, 'installations/technician_analytics.html', {})


@login_required
def factory_interface_view(request):
    """واجهة المصنع"""
    
    try:
        # الحصول على التركيبات حسب الحالة
        installations = InstallationNew.objects.select_related(
            'team', 'order'
        ).order_by('priority', 'order_date')
        
        # فلترة حسب الفرع إذا كان محدداً
        branch_filter = request.GET.get('branch')
        if branch_filter:
            installations = installations.filter(branch_name=branch_filter)
        
        # إحصائيات المصنع
        stats = {
            'pending': installations.filter(status='pending').count(),
            'in_production': installations.filter(is_ready_for_installation=False, status='ready').count(),
            'ready': installations.filter(is_ready_for_installation=True).count(),
            'urgent': installations.filter(priority='urgent').count(),
            'total': installations.count(),
            'total_windows': installations.aggregate(total=Sum('windows_count'))['total'] or 0,
        }
        
        # قائمة الفروع
        branches = InstallationNew.objects.values_list(
            'branch_name', flat=True
        ).distinct()
        
        context = {
            'installations': installations,
            'stats': stats,
            'branches': branches,
        }
        
        return render(request, 'installations/factory_interface.html', context)
        
    except Exception as e:
        messages.error(request, f'خطأ في تحميل واجهة المصنع: {str(e)}')
        return render(request, 'installations/factory_interface.html', {})


# API Views
@login_required
@require_http_methods(["GET"])
def calendar_events_api(request):
    """API للحصول على أحداث التقويم"""
    try:
        date_str = request.GET.get('date')
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()

        events = CalendarService.get_daily_schedule(target_date)
        return JsonResponse({'success': True, 'events': events})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def daily_details_api(request):
    """API للحصول على تفاصيل اليوم"""
    try:
        date_str = request.GET.get('date')
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()

        details = CalendarService.get_daily_schedule(target_date)
        return JsonResponse({'success': True, 'details': details})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def technician_stats_api(request, technician_id):
    """API لإحصائيات الفني"""
    try:
        stats = TechnicianAnalyticsService.get_technician_monthly_stats(
            technician_id,
            timezone.now().year,
            timezone.now().month
        )
        return JsonResponse({'success': True, 'stats': stats})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def technician_comparison_api(request):
    """API لمقارنة الفنيين"""
    try:
        comparison = TechnicianAnalyticsService.get_technicians_comparison()
        return JsonResponse({'success': True, 'comparison': comparison})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def team_distribution_api(request, team_id):
    """API لتوزيع الفريق"""
    try:
        distribution = TechnicianAnalyticsService.get_team_workload_distribution(team_id)
        return JsonResponse({'success': True, 'distribution': distribution})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def factory_update_status(request, installation_id):
    """API لتحديث حالة التركيب من المصنع"""
    try:
        data = json.loads(request.body)
        status = data.get('status')
        is_ready = data.get('is_ready_for_installation', False)

        installation = get_object_or_404(InstallationNew, id=installation_id)
        installation.status = status
        installation.is_ready_for_installation = is_ready
        installation.updated_by = request.user
        installation.save()

        return JsonResponse({'success': True, 'message': 'تم تحديث الحالة'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def factory_bulk_update_status(request):
    """API للتحديث المجمع للحالة"""
    try:
        data = json.loads(request.body)
        installation_ids = data.get('installation_ids', [])
        status = data.get('status')

        updated_count = InstallationNew.objects.filter(
            id__in=installation_ids
        ).update(
            status=status,
            updated_by=request.user
        )

        return JsonResponse({
            'success': True,
            'message': f'تم تحديث {updated_count} تركيب'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def factory_update_priority(request, installation_id):
    """API لتحديث أولوية التركيب"""
    try:
        data = json.loads(request.body)
        priority = data.get('priority')

        installation = get_object_or_404(InstallationNew, id=installation_id)
        installation.priority = priority
        installation.updated_by = request.user
        installation.save()

        return JsonResponse({'success': True, 'message': 'تم تحديث الأولوية'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def factory_stats_api(request):
    """API لإحصائيات المصنع"""
    try:
        stats = {
            'pending': InstallationNew.objects.filter(status='pending').count(),
            'in_production': InstallationNew.objects.filter(status='in_production').count(),
            'ready': InstallationNew.objects.filter(is_ready_for_installation=True).count(),
            'urgent': InstallationNew.objects.filter(priority='urgent').count(),
        }
        return JsonResponse({'success': True, 'stats': stats})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def alerts_api(request):
    """API للحصول على الإنذارات"""
    try:
        alerts = InstallationAlert.objects.filter(
            is_resolved=False
        ).order_by('-severity', '-created_at')[:10]

        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity,
                'created_at': alert.created_at.isoformat(),
            })

        return JsonResponse({'success': True, 'alerts': alerts_data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def resolve_alert_api(request, alert_id):
    """API لحل الإنذار"""
    try:
        alert = get_object_or_404(InstallationAlert, id=alert_id)
        alert.is_resolved = True
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.save()

        return JsonResponse({'success': True, 'message': 'تم حل الإنذار'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def dashboard_analytics_api(request):
    """API لتحليلات لوحة التحكم"""
    try:
        analytics = AnalyticsEngine.get_dashboard_analytics()
        return JsonResponse({'success': True, 'analytics': analytics})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def branch_comparison_api(request):
    """API لمقارنة الفروع"""
    try:
        comparison = AnalyticsEngine.get_branch_comparison()
        return JsonResponse({'success': True, 'comparison': comparison})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def monthly_report_api(request):
    """API للتقرير الشهري"""
    try:
        year = int(request.GET.get('year', timezone.now().year))
        month = int(request.GET.get('month', timezone.now().month))

        report = AnalyticsEngine.get_monthly_report(year, month)
        return JsonResponse({'success': True, 'report': report})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def predictive_analytics_api(request):
    """API للتحليلات التنبؤية"""
    try:
        analytics = AnalyticsEngine.get_predictive_analytics()
        return JsonResponse({'success': True, 'analytics': analytics})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Views للصفحات الإضافية
@login_required
def teams_list(request):
    """قائمة الفرق"""
    teams = InstallationTeamNew.objects.filter(is_active=True)
    return render(request, 'installations/teams_list.html', {'teams': teams})


@login_required
def create_team(request):
    """إنشاء فريق جديد"""
    return render(request, 'installations/create_team.html')


@login_required
def team_detail(request, team_id):
    """تفاصيل الفريق"""
    team = get_object_or_404(InstallationTeamNew, id=team_id)
    return render(request, 'installations/team_detail.html', {'team': team})


@login_required
def edit_team(request, team_id):
    """تعديل الفريق"""
    team = get_object_or_404(InstallationTeamNew, id=team_id)
    return render(request, 'installations/edit_team.html', {'team': team})


@login_required
def team_schedule(request, team_id):
    """جدول الفريق"""
    team = get_object_or_404(InstallationTeamNew, id=team_id)
    return render(request, 'installations/team_schedule.html', {'team': team})


@login_required
def technicians_list(request):
    """قائمة الفنيين"""
    technicians = InstallationTechnician.objects.filter(is_active=True)
    return render(request, 'installations/technicians_list.html', {'technicians': technicians})


@login_required
def create_technician(request):
    """إنشاء فني جديد"""
    return render(request, 'installations/create_technician.html')


@login_required
def technician_detail(request, technician_id):
    """تفاصيل الفني"""
    technician = get_object_or_404(InstallationTechnician, id=technician_id)
    return render(request, 'installations/technician_detail.html', {'technician': technician})


@login_required
def edit_technician(request, technician_id):
    """تعديل الفني"""
    technician = get_object_or_404(InstallationTechnician, id=technician_id)
    return render(request, 'installations/edit_technician.html', {'technician': technician})


@login_required
def technician_performance(request, technician_id):
    """أداء الفني"""
    technician = get_object_or_404(InstallationTechnician, id=technician_id)
    return render(request, 'installations/technician_performance.html', {'technician': technician})


@login_required
def reports_dashboard(request):
    """لوحة التقارير"""
    return render(request, 'installations/reports_dashboard.html')


@login_required
def daily_report(request):
    """التقرير اليومي"""
    return render(request, 'installations/daily_report.html')


@login_required
def weekly_report(request):
    """التقرير الأسبوعي"""
    return render(request, 'installations/weekly_report.html')


@login_required
def monthly_report(request):
    """التقرير الشهري"""
    return render(request, 'installations/monthly_report.html')


@login_required
def custom_report(request):
    """تقرير مخصص"""
    return render(request, 'installations/custom_report.html')


@login_required
def analytics_report(request):
    """تقرير التحليلات"""
    return render(request, 'installations/analytics_report.html')


@login_required
def installation_settings(request):
    """إعدادات التركيبات"""
    return render(request, 'installations/settings.html')


@login_required
def alert_settings(request):
    """إعدادات الإنذارات"""
    return render(request, 'installations/alert_settings.html')


@login_required
def notification_settings(request):
    """إعدادات الإشعارات"""
    return render(request, 'installations/notification_settings.html')


@login_required
def system_settings(request):
    """إعدادات النظام"""
    return render(request, 'installations/system_settings.html')


@login_required
def sync_with_legacy(request):
    """مزامنة مع النظام القديم"""
    return render(request, 'installations/sync_legacy.html')


@login_required
def migrate_from_legacy(request):
    """هجرة من النظام القديم"""
    return render(request, 'installations/migrate_legacy.html')


@login_required
def compare_systems(request):
    """مقارنة الأنظمة"""
    return render(request, 'installations/compare_systems.html')
