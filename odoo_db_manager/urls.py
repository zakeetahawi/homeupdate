"""
مسارات إدارة قواعد البيانات على طراز أودو
"""

from django.urls import path
from . import views
from . import google_sync_views
from . import views_advanced_sync


app_name = 'odoo_db_manager'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Databases
    path('databases/', views.database_list, name='database_list'),
    path('databases/discover/', views.database_discover, name='database_discover'),
    path('databases/register/', views.database_register, name='database_register'),
    path('databases/refresh-status/', views.database_refresh_status, name='database_refresh_status'),
    path('databases/create/', views.database_create, name='database_create'),
    path('databases/<int:pk>/', views.database_detail, name='database_detail'),
    path('databases/<int:pk>/activate/', views.database_activate, name='activate_database'),
    path('databases/<int:pk>/delete/', views.database_delete, name='delete_database'),

    # تم حذف URLs النسخ الاحتياطي القديمة - استخدم backup_system بدلاً من ذلك

    # Schedules
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
    path('google-drive/test-contract-upload/', views.google_drive_test_contract_upload, name='google_drive_test_contract_upload'),

    # Google Sync
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

    # Advanced Google Sync
    path('google-unified/', views_advanced_sync.advanced_sync_dashboard, name='google_unified_dashboard'),
    path('advanced-sync/', views_advanced_sync.advanced_sync_dashboard, name='advanced_sync_dashboard'),
    path('advanced-sync/mappings/', views_advanced_sync.mapping_list, name='mapping_list'),
    path('advanced-sync/mappings/create/', views_advanced_sync.mapping_create, name='mapping_create'),
    path('advanced-sync/mappings/<int:mapping_id>/', views_advanced_sync.mapping_detail, name='mapping_detail'),
    path('advanced-sync/mappings/<int:mapping_id>/edit/', views_advanced_sync.mapping_edit, name='mapping_edit'),
    path('advanced-sync/mappings/<int:mapping_id>/delete/', views_advanced_sync.mapping_delete, name='mapping_delete'),
    path('advanced-sync/mappings/<int:mapping_id>/update-columns/', views_advanced_sync.mapping_update_columns, name='mapping_update_columns'),
    path('advanced-sync/mappings/<int:mapping_id>/sync/', views_advanced_sync.start_sync, name='start_sync'),
    path('advanced-sync/mappings/<int:mapping_id>/schedule/', views_advanced_sync.schedule_sync, name='schedule_sync'),
    path('advanced-sync/tasks/<int:task_id>/', views_advanced_sync.task_detail, name='task_detail'),
    path('advanced-sync/tasks/<int:task_id>/status/', views_advanced_sync.get_task_status, name='get_task_status'),
    path('advanced-sync/conflicts/', views_advanced_sync.conflict_list, name='conflict_list'),
    path('advanced-sync/conflicts/<int:conflict_id>/resolve/', views_advanced_sync.resolve_conflict, name='resolve_conflict'),

    # API endpoints
    path('advanced-sync/api/run-sync/<int:mapping_id>/', views_advanced_sync.api_run_sync, name='api_run_sync'),
    path('advanced-sync/api/run-sync-all/', views_advanced_sync.api_run_sync_all, name='api_run_sync_all'),
    path('advanced-sync/api/get-sheets/', views_advanced_sync.get_sheets_by_id, name='get_sheets_by_id'),
    path('advanced-sync/api/sheet-columns/', views_advanced_sync.get_sheet_columns, name='get_sheet_columns'),
    path('advanced-sync/api/preview-data/', views_advanced_sync.preview_sheet_data, name='preview_sheet_data'),

    # Restore Progress
    path('restore-progress/<str:session_id>/stream/', views.restore_progress_stream, name='restore_progress_stream'),
    path('restore-progress/<str:session_id>/status/', views.restore_progress_status, name='restore_progress_status'),
    path('refresh-session/', views.refresh_session, name='refresh_session'),
]
