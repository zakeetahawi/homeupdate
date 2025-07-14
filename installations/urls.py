from django.urls import path
from . import views

app_name = 'installations'

urlpatterns = [
    # لوحة التحكم الرئيسية
    path('', views.dashboard, name='dashboard'),
    
    # إدارة التركيبات
    path('list/', views.installation_list, name='installation_list'),
    path('detail/<int:installation_id>/', views.installation_detail, name='installation_detail'),
    path('schedule/<int:installation_id>/', views.schedule_installation, name='schedule_installation'),
    path('update-status/<int:installation_id>/', views.update_status, name='update_status'),
    
    # الجدول اليومي
    path('daily-schedule/', views.daily_schedule, name='daily_schedule'),
    path('print-daily-schedule/', views.print_daily_schedule, name='print_daily_schedule'),
    
    # المدفوعات والتقارير
    path('add-payment/<int:installation_id>/', views.add_payment, name='add_payment'),
    path('add-modification-report/<int:installation_id>/', views.add_modification_report, name='add_modification_report'),
    path('add-receipt-memo/<int:installation_id>/', views.add_receipt_memo, name='add_receipt_memo'),
    
    # إكمال التركيب
    path('complete/<int:installation_id>/', views.complete_installation, name='complete_installation'),
    
    # إدارة الفرق
    path('teams/', views.team_management, name='team_management'),
    path('add-team/', views.add_team, name='add_team'),
    path('add-technician/', views.add_technician, name='add_technician'),
    path('add-driver/', views.add_driver, name='add_driver'),
    
    # الأرشيف
    path('archive/', views.archive_list, name='archive_list'),
    
    # APIs
    path('api/receive-order/', views.receive_completed_order, name='receive_completed_order'),
    path('api/stats/', views.installation_stats_api, name='installation_stats_api'),
]
