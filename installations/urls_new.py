"""
URLs للنظام الجديد للتركيبات
"""
from django.urls import path, include
from . import views_new, views_quick_edit, views_export, views_completion, views_unified_dashboard

app_name = 'installations_new'

urlpatterns = [
    # لوحة التحكم الموحدة
    path('', views_unified_dashboard.unified_dashboard, name='dashboard'),
    path('unified/', views_unified_dashboard.unified_dashboard, name='unified_dashboard'),

    # الصفحات الرئيسية
    path('old-dashboard/', views_new.installations_dashboard, name='old_dashboard'),
    path('list/', views_new.installations_list, name='list'),
    path('create/', views_new.create_installation, name='create'),
    path('<int:installation_id>/', views_new.installation_detail, name='detail'),
    path('<int:installation_id>/edit/', views_new.edit_installation, name='edit'),
    
    # التعديل السريع
    path('quick-edit/', views_quick_edit.quick_edit_table_view, name='quick_edit'),
    
    # التقويم الذكي
    path('calendar/', views_new.smart_calendar_view, name='calendar'),
    
    # تحليل الفنيين
    path('technician-analytics/', views_new.technician_analytics_view, name='technician_analytics'),
    
    # واجهة المصنع
    path('factory/', views_new.factory_interface_view, name='factory_interface'),
    
    # إكمال التركيبات
    path('<int:installation_id>/complete/', views_completion.complete_installation, name='complete'),
    path('<int:installation_id>/cancel/', views_completion.cancel_installation, name='cancel'),
    path('<int:installation_id>/reschedule/', views_completion.reschedule_installation, name='reschedule'),
    path('<int:installation_id>/completion-form/', views_completion.installation_completion_form, name='completion_form'),
    path('<int:installation_id>/status-history/', views_completion.installation_status_history, name='status_history'),
    path('pending-completions/', views_completion.pending_completions, name='pending_completions'),
    path('completion-summary/', views_completion.installation_completion_summary, name='completion_summary'),
    path('bulk-complete/', views_completion.bulk_complete_installations, name='bulk_complete'),
    
    # API endpoints
    path('api/', include([
        # التحديث السريع
        path('quick-update/<int:installation_id>/', views_quick_edit.quick_update_installation, name='api_quick_update'),
        path('bulk-update/', views_quick_edit.bulk_update_installations, name='api_bulk_update'),
        path('bulk-action/', views_quick_edit.bulk_action_installations, name='api_bulk_action'),
        
        # التقويم
        path('calendar-events/', views_new.calendar_events_api, name='api_calendar_events'),
        path('daily-details/', views_new.daily_details_api, name='api_daily_details'),
        
        # تحليل الفنيين
        path('technician-stats/<int:technician_id>/', views_new.technician_stats_api, name='api_technician_stats'),
        path('technician-comparison/', views_new.technician_comparison_api, name='api_technician_comparison'),
        path('team-distribution/<int:team_id>/', views_new.team_distribution_api, name='api_team_distribution'),
        
        # واجهة المصنع
        path('factory/update-status/<int:installation_id>/', views_new.factory_update_status, name='api_factory_update_status'),
        path('factory/bulk-update-status/', views_new.factory_bulk_update_status, name='api_factory_bulk_update_status'),
        path('factory/update-priority/<int:installation_id>/', views_new.factory_update_priority, name='api_factory_update_priority'),
        path('factory/stats/', views_new.factory_stats_api, name='api_factory_stats'),
        
        # الإنذارات
        path('alerts/', views_new.alerts_api, name='api_alerts'),
        path('alerts/<int:alert_id>/resolve/', views_new.resolve_alert_api, name='api_resolve_alert'),
        
        # التحليلات
        path('analytics/dashboard/', views_new.dashboard_analytics_api, name='api_dashboard_analytics'),
        path('analytics/branch-comparison/', views_new.branch_comparison_api, name='api_branch_comparison'),
        path('analytics/monthly-report/', views_new.monthly_report_api, name='api_monthly_report'),
        path('analytics/predictive/', views_new.predictive_analytics_api, name='api_predictive_analytics'),
    ])),
    
    # التصدير والطباعة
    path('export/', include([
        path('daily-schedule-pdf/', views_export.export_daily_schedule_pdf, name='export_daily_schedule_pdf'),
        path('technician-report-pdf/', views_export.export_technician_report_pdf, name='export_technician_report_pdf'),
        path('monthly-summary-pdf/', views_export.export_monthly_summary_pdf, name='export_monthly_summary_pdf'),
        path('team-performance-pdf/', views_export.export_team_performance_pdf, name='export_team_performance_pdf'),
        path('installations-excel/', views_export.export_installations_excel, name='export_installations_excel'),
        path('custom-report/', views_export.generate_custom_report, name='generate_custom_report'),
    ])),
    
    # الطباعة
    path('print/', include([
        path('daily-schedule/', views_export.print_daily_schedule, name='print_daily_schedule'),
    ])),
    
    # إدارة الفرق
    path('teams/', include([
        path('', views_new.teams_list, name='teams_list'),
        path('create/', views_new.create_team, name='create_team'),
        path('<int:team_id>/', views_new.team_detail, name='team_detail'),
        path('<int:team_id>/edit/', views_new.edit_team, name='edit_team'),
        path('<int:team_id>/schedule/', views_new.team_schedule, name='team_schedule'),
    ])),
    
    # إدارة الفنيين
    path('technicians/', include([
        path('', views_new.technicians_list, name='technicians_list'),
        path('create/', views_new.create_technician, name='create_technician'),
        path('<int:technician_id>/', views_new.technician_detail, name='technician_detail'),
        path('<int:technician_id>/edit/', views_new.edit_technician, name='edit_technician'),
        path('<int:technician_id>/performance/', views_new.technician_performance, name='technician_performance'),
    ])),
    
    # التقارير
    path('reports/', include([
        path('', views_new.reports_dashboard, name='reports_dashboard'),
        path('daily/', views_new.daily_report, name='daily_report'),
        path('weekly/', views_new.weekly_report, name='weekly_report'),
        path('monthly/', views_new.monthly_report, name='monthly_report'),
        path('custom/', views_new.custom_report, name='custom_report'),
        path('analytics/', views_new.analytics_report, name='analytics_report'),
    ])),
    
    # الإعدادات
    path('settings/', include([
        path('', views_new.installation_settings, name='settings'),
        path('alerts/', views_new.alert_settings, name='alert_settings'),
        path('notifications/', views_new.notification_settings, name='notification_settings'),
        path('system/', views_new.system_settings, name='system_settings'),
    ])),
]

# URLs إضافية للتكامل مع النظام القديم
legacy_urlpatterns = [
    # روابط للتوافق مع النظام القديم
    path('legacy/', include([
        path('sync/', views_new.sync_with_legacy, name='sync_legacy'),
        path('migrate/', views_new.migrate_from_legacy, name='migrate_legacy'),
        path('compare/', views_new.compare_systems, name='compare_systems'),
    ])),
]

urlpatterns += legacy_urlpatterns
