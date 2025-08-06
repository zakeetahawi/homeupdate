from django.urls import path
from . import views

app_name = 'installations'

urlpatterns = [
    # لوحة التحكم الرئيسية
    path('', views.dashboard, name='dashboard'),

    # إدارة حالات التركيب
    path('installation/<int:installation_id>/change-status/', views.change_installation_status, name='change_installation_status'),

    # نظام التعديلات
    path('installation/<int:installation_id>/create-modification/', views.create_modification_request, name='create_modification_request'),
    path('modification/<int:modification_id>/', views.modification_detail, name='modification_detail'),
    path('modification/<int:modification_id>/upload-images/', views.upload_modification_images, name='upload_modification_images'),
    path('modification/<int:modification_id>/create-manufacturing-order/', views.create_manufacturing_order, name='create_manufacturing_order'),
    path('modification-requests/', views.modification_requests_list, name='modification_requests_list'),

    # أوامر التصنيع للتعديلات
    path('manufacturing-order/<int:order_id>/', views.manufacturing_order_detail, name='manufacturing_order_detail'),
    path('manufacturing-order/<int:order_id>/complete/', views.complete_manufacturing_order, name='complete_manufacturing_order'),
    path('manufacturing-orders/', views.manufacturing_orders_list, name='manufacturing_orders_list'),

    # إدارة مديونية العملاء
    path('order/<int:order_id>/manage-debt/', views.manage_customer_debt, name='manage_customer_debt'),
    path('debt/<int:debt_id>/pay/', views.pay_debt, name='pay_debt'),

    # API Views
    path('api/orders-modal/', views.orders_modal, name='orders_modal'),
    path('api/installation-stats/', views.installation_stats_api, name='installation_stats_api'),
    path('schedule-manufacturing-order/<int:manufacturing_order_id>/', views.schedule_manufacturing_order, name='schedule_manufacturing_order'),

    # URLs الموجودة مسبقاً
    path('installation/<int:installation_id>/schedule/', views.schedule_installation, name='schedule_installation'),
    path('quick-schedule/<int:order_id>/', views.quick_schedule_installation, name='quick_schedule_installation'),
    path('check-debt/<int:order_id>/', views.check_debt_before_schedule, name='check_debt_before_schedule'),
    path('installation/<int:installation_id>/schedule-from-needs/', views.schedule_from_needs_scheduling, name='schedule_from_needs_scheduling'),
    
    # URLs باستخدام كود التركيب
    path('installation/<str:installation_code>/', views.installation_detail_by_code, name='installation_detail_by_code'),
    
    # URLs القديمة مع إعادة توجيه
    path('installation/<int:installation_id>/', views.installation_detail_redirect, name='installation_detail'),
    path('daily-schedule/', views.daily_schedule, name='daily_schedule'),
    path('print-daily-schedule/', views.print_daily_schedule, name='print_daily_schedule'),
    path('debt-list/', views.debt_list, name='debt_list'),

    # URLs المفقودة
    path('installation-list/', views.installation_list, name='installation_list'),
    path('team-management/', views.team_management, name='team_management'),
    path('add-team/', views.add_team, name='add_team'),
    path('add-technician/', views.add_technician, name='add_technician'),
    path('add-driver/', views.add_driver, name='add_driver'),
    path('team/<int:team_id>/', views.team_detail, name='team_detail'),
    path('team/<int:team_id>/edit/', views.edit_team, name='edit_team'),
    path('team/<int:team_id>/delete/', views.delete_team, name='delete_team'),
    path('technician/<int:technician_id>/edit/', views.edit_technician, name='edit_technician'),
    path('technician/<int:technician_id>/delete/', views.delete_technician, name='delete_technician'),
    path('driver/<int:driver_id>/edit/', views.edit_driver, name='edit_driver'),
    path('driver/<int:driver_id>/delete/', views.delete_driver, name='delete_driver'),
    path('archive-list/', views.archive_list, name='archive_list'),
    path('installation/<int:installation_id>/update-status/', views.update_status, name='update_status'),
    path('installation/<int:installation_id>/add-payment/', views.add_payment, name='add_payment'),
    path('installation/<int:installation_id>/add-modification-report/', views.add_modification_report, name='add_modification_report'),
    path('installation/<int:installation_id>/add-receipt-memo/', views.add_receipt_memo, name='add_receipt_memo'),
    path('installation/<int:installation_id>/complete/', views.complete_installation, name='complete_installation'),
    path('installation/<int:installation_id>/edit-schedule/', views.edit_schedule, name='edit_schedule'),
    path('installation/<int:installation_id>/edit-schedule/', views.edit_schedule, name='edit_schedule'),
    path('installation/<int:installation_id>/delete/', views.delete_installation, name='installation_delete'),

    # تحليل الأخطاء
    path('error-analysis/', views.modification_error_analysis, name='modification_error_analysis'),
    path('add-error-analysis/<int:modification_id>/', views.add_error_analysis, name='add_error_analysis'),

    # التحليل الشهري
    path('analytics/', views.installation_analytics, name='installation_analytics'),
    
    # سجل الأحداث والتركيبات قيد التنفيذ
    path('event-logs/', views.installation_event_logs, name='installation_event_logs'),
    path('in-progress/', views.installation_in_progress_list, name='installation_in_progress_list'),
    path('print-schedule/', views.print_installation_schedule, name='print_installation_schedule'),
    
    # إعدادات الجدولة
    path('installation/<int:installation_id>/scheduling-details/', views.view_scheduling_details, name='view_scheduling_details'),
    path('installation/<int:installation_id>/edit-scheduling-settings/', views.edit_scheduling_settings, name='edit_scheduling_settings'),
    path('installation/<int:installation_id>/update-date-from-scheduled/', views.update_installation_date_from_scheduled, name='update_installation_date_from_scheduled'),
    
    # جدول المديونية
    path('debt-orders/', views.debt_orders_list, name='debt_orders_list'),
]
