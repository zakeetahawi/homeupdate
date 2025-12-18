from django.urls import path
from . import views, api_views
from .auth_compat import auth_compat_view
from .activity_views import (
    user_activity_dashboard, user_activity_detail, activity_logs_list,
    login_history_list, online_users_api, update_current_page, user_activities_api
)
from .messages_views import (
    inbox, sent_messages, compose_message, view_message, delete_message,
    mark_as_read, mark_all_as_read, get_unread_count, 
    get_online_users_with_messages, reply_to_message
)

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # Device Management
    path('register-device/', views.register_device_view, name='register_device'),
    path('device-diagnostic/', views.device_diagnostic_view, name='device_diagnostic'),
    path('qr-master/<int:qr_id>/print/', views.print_qr_master, name='print_qr_master'),
    path('validate-qr-master/', views.validate_qr_master_ajax, name='validate_qr_master'),
    
    # Device API
    path('api/check-device/', api_views.check_device_api, name='check_device_api'),

    # API Authentication URLs
    path('api/login/', api_views.login_api, name='api_login'),
    path('api/user/', api_views.current_user, name='api_current_user'),
    path('api/user/info/', api_views.user_info, name='api_user_info'),
    path('auth/login/', auth_compat_view, name='auth_compat_login'),
    path(
        'api/auth/login/',
        auth_compat_view,
        name='auth_compat_login_alias'
    ),



    # Company Info URLs
    path('company-info/', views.company_info_view, name='company_info'),

    # Form Field Management URLs
    path('form-fields/', views.form_field_list, name='form_field_list'),
    path('form-fields/create/',
         views.form_field_create, name='form_field_create'),
    path('form-fields/<int:pk>/update/',
         views.form_field_update, name='form_field_update'),
    path('form-fields/<int:pk>/delete/',
         views.form_field_delete, name='form_field_delete'),
    path('form-fields/<int:pk>/toggle/',
         views.toggle_form_field, name='toggle_form_field'),

    # Department Management URLs
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/',
         views.department_create, name='department_create'),
    path('departments/<int:pk>/update/',
         views.department_update, name='department_update'),
    path('departments/<int:pk>/delete/',
         views.department_delete, name='department_delete'),
    path('departments/<int:pk>/toggle/',
         views.toggle_department, name='toggle_department'),

    # Salesperson Management URLs
    path('salespersons/',
         views.salesperson_list, name='salesperson_list'),
    path('salespersons/create/',
         views.salesperson_create, name='salesperson_create'),
    path('salespersons/<int:pk>/update/',
         views.salesperson_update, name='salesperson_update'),
    path('salespersons/<int:pk>/delete/',
         views.salesperson_delete, name='salesperson_delete'),
    path('salespersons/<int:pk>/toggle/',
         views.toggle_salesperson, name='toggle_salesperson'),

    # Role Management URLs
    path('roles/', views.role_management, name='role_management'),
    path('roles/list/', views.role_list, name='role_list'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/<int:pk>/update/', views.role_update, name='role_update'),
    path('roles/<int:pk>/delete/', views.role_delete, name='role_delete'),
    path('roles/<int:pk>/assign/', views.role_assign, name='role_assign'),

    # Theme Management
    path('save-theme/', views.set_default_theme, name='set_default_theme'),

    # 🎨 نظام الإشعارات - تم إزالته

    # 📊 نظام تتبع النشاط والمستخدمين النشطين
    path('activity/dashboard/', user_activity_dashboard, name='activity_dashboard'),
    path('activity/user/<int:user_id>/', user_activity_detail, name='user_activity_detail'),
    path('activity/logs/', activity_logs_list, name='activity_logs_list'),
    path('activity/logins/', login_history_list, name='login_history_list'),

    # APIs للمستخدمين النشطين
    path('api/online-users/', online_users_api, name='online_users_api'),
    path('api/user-activities/<int:user_id>/', user_activities_api, name='user_activities_api'),
    path('api/update-current-page/', update_current_page, name='update_current_page'),
    
    # 📧 نظام الرسائل الداخلية
    path('messages/inbox/', inbox, name='inbox'),
    path('messages/sent/', sent_messages, name='sent_messages'),
    path('messages/compose/', compose_message, name='compose_message'),
    path('messages/<int:message_id>/', view_message, name='view_message'),
    path('messages/<int:message_id>/delete/', delete_message, name='delete_message'),
    path('messages/<int:message_id>/mark-read/', mark_as_read, name='mark_as_read'),
    path('messages/<int:message_id>/reply/', reply_to_message, name='reply_to_message'),
    path('messages/mark-all-read/', mark_all_as_read, name='mark_all_as_read'),
    
    # APIs للرسائل
    path('api/messages/unread-count/', get_unread_count, name='get_unread_count'),
    path('api/messages/online-users/', get_online_users_with_messages, name='get_online_users_with_messages'),
]
