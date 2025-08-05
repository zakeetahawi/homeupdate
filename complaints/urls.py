from django.urls import path
from . import views

app_name = 'complaints'

urlpatterns = [
    # لوحة التحكم
    path('', views.ComplaintDashboardView.as_view(), name='dashboard'),
    
    # إدارة الشكاوى
    path('list/', views.ComplaintListView.as_view(), name='complaint_list'),
    path('create/', views.ComplaintCreateView.as_view(), name='complaint_create'),
    path('<int:pk>/', views.ComplaintDetailView.as_view(), name='complaint_detail'),
    path('<int:pk>/edit/', views.ComplaintUpdateView.as_view(), name='complaint_edit'),
    
    # إجراءات الشكوى
    path('<int:pk>/status/', views.complaint_status_update, name='complaint_status_update'),
    path('<int:pk>/assign/', views.complaint_assignment, name='complaint_assignment'),
    path('<int:pk>/update/', views.complaint_add_update, name='complaint_add_update'),
    path('<int:pk>/escalate/', views.complaint_escalate, name='complaint_escalate'),
    path('<int:pk>/resolve/', views.complaint_resolve, name='complaint_resolve'),
    path('<int:pk>/attachment/', views.complaint_add_attachment, name='complaint_add_attachment'),
    path('<int:pk>/rating/', views.customer_rating, name='customer_rating'),
    
    # عرض شكاوى العميل
    path('customer/<int:customer_id>/', views.customer_complaints, name='customer_complaints'),
    
    # الإحصائيات
    path('statistics/', views.complaints_statistics, name='statistics'),
    
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
    path('notifications/bulk-action/',
         views.notification_bulk_action, name='notification_bulk_action'),
    path('notifications/mark-all-as-read/',
         views.mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
    path('notifications/<int:notification_id>/read/',
         views.mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/<int:notification_id>/delete/',
         views.delete_notification, name='delete_notification'),
]
