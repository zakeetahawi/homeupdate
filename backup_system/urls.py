"""
مسارات نظام النسخ الاحتياطي والاستعادة
"""

from django.urls import path

from . import views

app_name = "backup_system"

urlpatterns = [
    # لوحة التحكم الرئيسية
    path("", views.dashboard, name="dashboard"),
    # النسخ الاحتياطية
    path("backups/", views.backup_list, name="backup_list"),
    path("backups/create/", views.backup_create, name="backup_create"),
    path("backups/<uuid:pk>/", views.backup_detail, name="backup_detail"),
    path("backups/<uuid:pk>/download/", views.backup_download, name="backup_download"),
    path("backups/<uuid:pk>/delete/", views.backup_delete, name="backup_delete"),
    # الاستعادة
    path("restore/", views.restore_list, name="restore_list"),
    path("restore/upload/", views.restore_upload, name="restore_upload"),
    path(
        "restore/from-backup/<uuid:backup_pk>/",
        views.restore_from_backup,
        name="restore_from_backup",
    ),
    path("restore/<uuid:pk>/", views.restore_detail, name="restore_detail"),
    # API للحصول على حالة المهام
    path(
        "api/backup/<uuid:pk>/status/",
        views.backup_status_api,
        name="backup_status_api",
    ),
    path(
        "api/restore/<uuid:pk>/status/",
        views.restore_status_api,
        name="restore_status_api",
    ),
]
