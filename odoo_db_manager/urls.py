"""
مسارات إدارة قواعد البيانات على طراز أودو
"""

from django.urls import path
from . import views
from . import views_import
from . import google_sync_views

app_name = 'odoo_db_manager'

urlpatterns = [
    # الصفحة الرئيسية - داشبورد إدارة قواعد البيانات
    path('', views.dashboard, name='dashboard'),

    # قواعد البيانات
    path('databases/', views.database_list, name='database_list'),
    path('databases/discover/', views.database_discover, name='database_discover'),
    path('databases/register/', views.database_register, name='database_register'),
    path('databases/refresh-status/', views.database_refresh_status, name='database_refresh_status'),
    path('databases/create/', views.database_create, name='database_create'),
    path('databases/<int:pk>/', views.database_detail, name='database_detail'),
    path('databases/<int:pk>/activate/', views.database_activate, name='activate_database'),
    path('databases/<int:pk>/delete/', views.database_delete, name='delete_database'),

    # النسخ الاحتياطية
    path('backups/create/', views.backup_create, name='backup_create'),
    path('backups/create/<int:database_id>/', views.backup_create, name='backup_create_for_database'),
    path('backups/<int:pk>/', views.backup_detail, name='backup_detail'),
    path('backups/<int:pk>/restore/', views.backup_restore, name='backup_restore'),
    path('backups/<int:pk>/delete/', views.backup_delete, name='backup_delete'),
    path('backups/<int:pk>/download/', views.backup_download, name='backup_download'),
    path('backups/upload/', views.backup_upload, name='backup_upload'),
    path('backups/upload/<int:database_id>/', views.backup_upload, name='backup_upload_for_database'),

    # جدولة النسخ الاحتياطية
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/create/', views.schedule_create, name='schedule_create'),
    path('schedules/create/<int:database_id>/', views.schedule_create, name='schedule_create_for_database'),
    path('schedules/<int:pk>/', views.schedule_detail, name='schedule_detail'),
    path('schedules/<int:pk>/update/', views.schedule_update, name='schedule_update'),
    path('schedules/<int:pk>/delete/', views.schedule_delete, name='schedule_delete'),
    path('schedules/<int:pk>/toggle/', views.schedule_toggle, name='schedule_toggle'),
    path('schedules/<int:pk>/run/', views.schedule_run_now, name='schedule_run_now'),
    path('scheduler/status/', views.scheduler_status, name='scheduler_status'),

    # Google Drive
    path('google-drive/settings/', views.google_drive_settings, name='google_drive_settings'),
    path('google-drive/test-connection/', views.google_drive_test_connection, name='google_drive_test_connection'),
    path('google-drive/create-test-folder/', views.google_drive_create_test_folder, name='google_drive_create_test_folder'),
    path('google-drive/test-file-upload/', views.google_drive_test_file_upload, name='google_drive_test_file_upload'),

    # مزامنة غوغل
    path('google-sync/', google_sync_views.google_sync, name='google_sync'),
    path('google-sync/config/', google_sync_views.google_sync_config, name='google_sync_config'),
    path('google-sync/config/save/', google_sync_views.google_sync_config_save, name='google_sync_config_save'),
    path('google-sync/delete-credentials/', google_sync_views.google_sync_delete_credentials, name='google_sync_delete_credentials'),
    path('google-sync/options/', google_sync_views.google_sync_options, name='google_sync_options'),
    path('google-sync/now/', google_sync_views.google_sync_now, name='google_sync_now'),
    path('google-sync/test/', google_sync_views.google_sync_test, name='google_sync_test'),
    path('google-sync/reset/', google_sync_views.google_sync_reset, name='google_sync_reset'),
    path('google-sync/advanced-settings/', google_sync_views.google_sync_advanced_settings, name='google_sync_advanced_settings'),
    path('google-sync/logs-api/', google_sync_views.google_sync_logs_api, name='google_sync_logs_api'),

    # استيراد البيانات
    path('import/', views_import.import_dashboard, name='import_dashboard'),
    path('import/select/', views_import.import_select, name='import_select'),
    path('import/preview/', views_import.import_preview, name='import_preview'),
    path('import/execute/', views_import.import_execute, name='import_execute'),
    path('import/result/<int:log_id>/', views_import.import_result, name='import_result'),
    path('import/progress/', views_import.import_progress, name='import_progress'),
]
