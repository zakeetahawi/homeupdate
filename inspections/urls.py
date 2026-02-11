from django.urls import path

from . import views

app_name = "inspections"

urlpatterns = [
    # Dashboard removed
    path("", views.InspectionListView.as_view(), name="inspection_list"),
    
    # ═══════════════════════════════════════════════════════════════════
    # CRITICAL: Specific paths MUST come before catch-all <str:inspection_code>
    # ═══════════════════════════════════════════════════════════════════
    
    # Technician Dashboard (must come before <str:inspection_code>)
    path(
        "technician/",
        views.InspectionTechnicianDashboardView.as_view(),
        name="technician_dashboard_short",
    ),
    path(
        "technician/dashboard/",
        views.InspectionTechnicianDashboardView.as_view(),
        name="technician_dashboard",
    ),
    path(
        "technician/completed/",
        views.TechnicianCompletedInspectionsView.as_view(),
        name="technician_completed_inspections",
    ),
    
    # Schedule (must come before <str:inspection_code>)
    path("schedule/", views.inspection_schedule_view, name="inspection_schedule"),
    path("schedule/print/", views.print_daily_schedule, name="print_daily_schedule"),
    
    # Detail views (must come before <str:inspection_code>)
    path(
        "completed-details/",
        views.CompletedInspectionsDetailView.as_view(),
        name="completed_details",
    ),
    path(
        "cancelled-details/",
        views.CancelledInspectionsDetailView.as_view(),
        name="cancelled_details",
    ),
    path(
        "pending-details/",
        views.PendingInspectionsDetailView.as_view(),
        name="pending_details",
    ),
    
    # Create/Report (must come before <str:inspection_code>)
    path("create/", views.InspectionCreateView.as_view(), name="inspection_create"),
    path(
        "report/create/",
        views.InspectionReportCreateView.as_view(),
        name="inspection_report_create",
    ),
    
    # API Endpoints (must come before <str:inspection_code>)
    path(
        "api/update-status/<int:pk>/",
        views.update_inspection_status_api,
        name="update_status_api",
    ),
    path(
        "api/upload-file/<int:pk>/",
        views.upload_inspection_file_api,
        name="upload_file_api",
    ),
    path(
        "ajax/duplicate-inspection/",
        views.ajax_duplicate_inspection,
        name="ajax_duplicate_inspection",
    ),
    path(
        "ajax/upload-to-google-drive/",
        views.ajax_upload_to_google_drive,
        name="ajax_upload_to_google_drive",
    ),
    path(
        "api/file/<int:file_id>/delete/",
        views.delete_inspection_file,
        name="delete_inspection_file",
    ),
    path(
        "api/<int:inspection_id>/upload-files/",
        views.upload_inspection_files,
        name="upload_inspection_files",
    ),
    
    # Notifications (must come before <str:inspection_code>)
    path(
        "notifications/", views.NotificationListView.as_view(), name="notification_list"
    ),
    path(
        "notifications/<int:pk>/mark-read/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    
    # Secure Files (must come before <str:inspection_code>)
    path(
        "secure/file/<int:inspection_id>/",
        views.preview_inspection_file,
        name="preview_inspection_file",
    ),
    
    # Alias for compatibility
    path("inspections/", views.InspectionListView.as_view(), name="inspections_list"),
    
    # ═══════════════════════════════════════════════════════════════════
    # URLs باستخدام كود المعاينة - CATCH-ALL PATTERNS (MUST BE LAST)
    # ═══════════════════════════════════════════════════════════════════
    path(
        "<str:inspection_code>/",
        views.inspection_detail_by_code,
        name="inspection_detail_by_code",
    ),
    path(
        "<str:inspection_code>/update/",
        views.inspection_update_by_code,
        name="inspection_update_by_code",
    ),
    path(
        "<str:inspection_code>/delete/",
        views.inspection_delete_by_code,
        name="inspection_delete_by_code",
    ),
    path(
        "<str:inspection_code>/check-upload-status/",
        views.check_upload_status_by_code,
        name="check_upload_status_by_code",
    ),
    path(
        "<str:inspection_code>/iterate/",
        views.iterate_inspection_by_code,
        name="iterate_inspection_by_code",
    ),
    
    # ═══════════════════════════════════════════════════════════════════
    # URLs القديمة مع إعادة توجيه - OLD ID-BASED (DEPRECATED)
    # ═══════════════════════════════════════════════════════════════════
    path("<int:pk>/", views.inspection_detail_redirect, name="inspection_detail"),
    path(
        "<int:pk>/update/", views.inspection_update_redirect, name="inspection_update"
    ),
    path(
        "<int:pk>/delete/", views.inspection_delete_redirect, name="inspection_delete"
    ),
    path("<int:pk>/iterate/", views.iterate_inspection, name="iterate_inspection"),
    path(
        "<int:pk>/check-upload-status/",
        views.check_upload_status,
        name="check_upload_status",
    ),
    
    # Evaluations & Notifications with inspection PK
    path(
        "<int:inspection_pk>/evaluate/",
        views.EvaluationCreateView.as_view(),
        name="evaluation_create",
    ),
    path(
        "<int:inspection_pk>/notify/",
        views.NotificationCreateView.as_view(),
        name="notification_create",
    ),
]
