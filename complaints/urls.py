from django.urls import path
from . import views, api_views
from .views import ExportComplaintsView
from .api_views import clear_complaints_notifications, assigned_complaints_api

app_name = 'complaints'

urlpatterns = [
    # لوحة التحكم
    path('', views.ComplaintDashboardView.as_view(), name='dashboard'),
    
    # إدارة الشكاوى
    path('list/', views.ComplaintListView.as_view(), name='complaint_list'),
    path('admin/', views.AdminComplaintListView.as_view(), name='admin_complaint_list'),
    path('reports/', views.ComplaintReportsView.as_view(), name='reports'),
    path('create/', views.ComplaintCreateView.as_view(), name='complaint_create'),
    path('<int:pk>/', views.ComplaintDetailView.as_view(), name='complaint_detail'),
    path('<int:pk>/edit/', views.ComplaintUpdateView.as_view(), name='complaint_edit'),
    
    # إجراءات الشكوى
    path('<int:pk>/status/', views.complaint_status_update, name='complaint_status_update'),
    path('<int:pk>/start-working/', views.start_working_on_complaint, name='start_working_on_complaint'),
    path('<int:pk>/start-action-escalated/', views.start_action_on_escalated_complaint, name='start_action_on_escalated_complaint'),
    path('<int:pk>/close/', views.close_complaint, name='close_complaint'),
    path('<int:pk>/mark-resolved/', views.mark_complaint_as_resolved, name='mark_complaint_as_resolved'),
    path('<int:pk>/assign/', views.complaint_assignment, name='complaint_assignment'),
    path('<int:pk>/escalate/', views.complaint_escalate, name='complaint_escalate'),
    path('<int:pk>/resolve/', views.complaint_resolve, name='complaint_resolve'),
    path('<int:pk>/attachment/', views.complaint_add_attachment, name='complaint_add_attachment'),
    path('<int:pk>/rating/', views.customer_rating, name='customer_rating'),
    
    # عرض شكاوى العميل
    path('customer/<int:customer_id>/', views.customer_complaints, name='customer_complaints'),
    
    # الإحصائيات والتصدير
    path('statistics/', views.complaints_statistics, name='statistics'),
    path('export/', ExportComplaintsView.as_view(), name='export_complaints'),

    # التقييمات
    path('evaluations/report/', views.ComplaintEvaluationReportView.as_view(), name='evaluation_report'),
    path('<int:complaint_id>/evaluate/', views.create_evaluation, name='create_evaluation'),
    
    # الإجراءات المجمعة
    path('bulk-action/', views.bulk_action, name='bulk_action'),
    
    # AJAX
    path('ajax/stats/', views.ajax_complaint_stats, name='ajax_stats'),
        path('ajax/customer-info/<int:customer_id>/', views.get_customer_info, name='ajax_customer_info'),
    path('ajax/customer-orders/<int:customer_id>/', views.get_customer_orders, name='ajax_customer_orders'),
    path('ajax/customers/search/', views.search_customers, name='ajax_search_customers'),
    path('api/complaint-types/<int:type_id>/', views.get_complaint_type_fields, name='api_complaint_type_fields'),
    
    # الإشعارات
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('analysis/', views.complaints_analysis, name='analysis'),
    path('notifications/bulk-action/',
         views.notification_bulk_action, name='notification_bulk_action'),
    path('notifications/mark-all-as-read/',
         views.mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
    path('notifications/<int:notification_id>/read/',
         views.mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/<int:notification_id>/delete/',
         views.delete_notification, name='delete_notification'),

    # Enhanced API Endpoints
    path('api/<int:complaint_id>/status/',
         api_views.ComplaintStatusUpdateView.as_view(), name='api_status_update'),
    path('api/<int:complaint_id>/assignment/',
         api_views.ComplaintAssignmentUpdateView.as_view(), name='api_assignment_update'),
    path('api/<int:complaint_id>/escalate/',
         api_views.ComplaintEscalationView.as_view(), name='api_escalate'),
    path('api/<int:complaint_id>/assign/',
         api_views.ComplaintAssignmentView.as_view(), name='api_assign'),
    path('api/<int:complaint_id>/note/',
         api_views.ComplaintNoteView.as_view(), name='api_note'),
    path('api/search/', api_views.complaint_search_api, name='api_search'),
    path('api/stats/', api_views.complaint_stats_api, name='api_stats'),
    path('api/notifications/', api_views.complaints_notifications_api, name='api_notifications'),
    path('api/notifications/clear/', api_views.clear_complaints_notifications, name='api_clear_notifications'),
    path('api/notifications/<int:notification_id>/read/', api_views.mark_complaint_notification_read, name='api_mark_notification_read'),
    path('api/assigned/', api_views.assigned_complaints_api, name='api_assigned_complaints'),
    path('api/escalated/', api_views.escalated_complaints_api, name='api_escalated_complaints'),
    path('api/assignment-notifications/', api_views.AssignmentNotificationsView.as_view(), name='api_assignment_notifications'),
    path('api/assignment-notifications/<int:notification_id>/read/', api_views.mark_assignment_notification_read, name='api_mark_assignment_read'),
    path('api/resolution-methods/', api_views.ResolutionMethodsView.as_view(), name='api_resolution_methods'),
    path('api/users-for-escalation/', api_views.UsersForEscalationView.as_view(), name='api_users_for_escalation'),
    path('api/users-for-assignment/', api_views.UsersForAssignmentView.as_view(), name='api_users_for_assignment'),
    path('api/unresolved-stats/', api_views.UnresolvedComplaintsStatsView.as_view(), name='api_unresolved_stats'),
    path('api/complaint-type/<int:complaint_type_id>/responsible-staff/', api_views.get_complaint_type_responsible_staff, name='api_complaint_type_responsible_staff'),
]
