"""
مسارات إدارة قواعد البيانات على طراز أودو
"""

from django.urls import path
from . import views

app_name = 'odoo_db_manager'

urlpatterns = [
    # الصفحة الرئيسية - داشبورد إدارة قواعد البيانات
    path('', views.dashboard, name='dashboard'),

    # قواعد البيانات
    path('databases/', views.database_list, name='database_list'),
    path('databases/discover/', views.database_discover, name='database_discover'),
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

    # Google Drive
    path('google-drive/settings/', views.google_drive_settings, name='google_drive_settings'),
    path('google-drive/test-connection/', views.google_drive_test_connection, name='google_drive_test_connection'),
    path('google-drive/create-test-folder/', views.google_drive_create_test_folder, name='google_drive_create_test_folder'),
    path('google-drive/test-file-upload/', views.google_drive_test_file_upload, name='google_drive_test_file_upload'),

]
