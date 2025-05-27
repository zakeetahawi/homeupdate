from django.urls import path
from . import views

app_name = 'inspections'

urlpatterns = [
    # Dashboard
    path('', views.InspectionListView.as_view(), name='inspection_list'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('completed-details/', views.CompletedInspectionsDetailView.as_view(), name='completed_details'),
    path('cancelled-details/', views.CancelledInspectionsDetailView.as_view(), name='cancelled_details'),
    path('pending-details/', views.PendingInspectionsDetailView.as_view(), name='pending_details'),
    # alias for compatibility
    path('inspections/', views.InspectionListView.as_view(), name='inspections_list'),


    path('create/', views.InspectionCreateView.as_view(), name='inspection_create'),
    path('report/create/', views.InspectionReportCreateView.as_view(), name='inspection_report_create'),
    path('<int:pk>/', views.InspectionDetailView.as_view(), name='inspection_detail'),
    path('<int:pk>/update/', views.InspectionUpdateView.as_view(), name='inspection_update'),
    path('<int:pk>/delete/', views.InspectionDeleteView.as_view(), name='inspection_delete'),
    path('<int:pk>/iterate/', views.iterate_inspection, name='iterate_inspection'),
    path('ajax/duplicate-inspection/', views.ajax_duplicate_inspection, name='ajax_duplicate_inspection'),
    path('ajax/upload-to-google-drive/', views.ajax_upload_to_google_drive, name='ajax_upload_to_google_drive'),
    path('<int:pk>/check-upload-status/', views.check_upload_status, name='check_upload_status'),

    # Evaluations
    path('<int:inspection_pk>/evaluate/', views.EvaluationCreateView.as_view(), name='evaluation_create'),

    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification_list'),
    path('<int:inspection_pk>/notify/', views.NotificationCreateView.as_view(), name='notification_create'),
    path('notifications/<int:pk>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
]
