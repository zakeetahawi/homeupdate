from django.urls import path
from . import views, api_views
from .auth_compat import auth_compat_view

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

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

    # Notification URLs
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/<int:notification_id>/',
         views.notification_detail, name='notification_detail'),
    path('notifications/<int:notification_id>/mark-read/',
         views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/',
         views.mark_all_notifications_read, name='mark_all_notifications_read'),

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
]
