from django.urls import path

from . import api_views, views
from .views_user_management import (
    user_manage_edit,
    user_manage_list,
    user_permissions_api,
    user_toggle_role_api,
)
from .activity_views import (
    activity_logs_list,
    login_history_list,
    online_users_api,
    update_current_page,
    user_activities_api,
    user_activity_dashboard,
    user_activity_detail,
)
from .admin_device_reports import device_dashboard_view, device_detail_report
from .auth_compat import auth_compat_view
from .messages_views import (
    api_check_new_messages,
    api_get_chat_history,
    api_recent_conversations,
    api_send_chat_message,
    compose_message,
    delete_message,
    get_online_users_with_messages,
    get_unread_count,
    inbox,
    mark_all_as_read,
    mark_as_read,
    reply_to_message,
    sent_messages,
    view_message,
)

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    # Device Management
    path("register-device/", views.register_device_view, name="register_device"),
    path("device-diagnostic/", views.device_diagnostic_view, name="device_diagnostic"),
    path("qr-master/<int:qr_id>/print/", views.print_qr_master, name="print_qr_master"),
    path(
        "validate-qr-master/", views.validate_qr_master_ajax, name="validate_qr_master"
    ),
    # Device Reports (Admin) - يجب أن تكون قبل check-device API
    path(
        "admin/device-reports/dashboard/",
        device_dashboard_view,
        name="device_dashboard",
    ),
    path(
        "admin/device-reports/<int:device_id>/report/",
        device_detail_report,
        name="device_report",
    ),
    # Device API
    path("api/check-device/", api_views.check_device_api, name="check_device_api"),
    # API Authentication URLs
    path("api/login/", api_views.login_api, name="api_login"),
    path("api/user/", api_views.current_user, name="api_current_user"),
    path("api/user/info/", api_views.user_info, name="api_user_info"),
    path("auth/login/", auth_compat_view, name="auth_compat_login"),
    path("api/auth/login/", auth_compat_view, name="auth_compat_login_alias"),
    # Company Info URLs
    path("company-info/", views.company_info_view, name="company_info"),
    # Form Field Management URLs
    path("form-fields/", views.form_field_list, name="form_field_list"),
    path("form-fields/create/", views.form_field_create, name="form_field_create"),
    path(
        "form-fields/<int:pk>/update/",
        views.form_field_update,
        name="form_field_update",
    ),
    path(
        "form-fields/<int:pk>/delete/",
        views.form_field_delete,
        name="form_field_delete",
    ),
    path(
        "form-fields/<int:pk>/toggle/",
        views.toggle_form_field,
        name="toggle_form_field",
    ),
    # Department Management URLs
    path("departments/", views.department_list, name="department_list"),
    path("departments/create/", views.department_create, name="department_create"),
    path(
        "departments/<int:pk>/update/",
        views.department_update,
        name="department_update",
    ),
    path(
        "departments/<int:pk>/delete/",
        views.department_delete,
        name="department_delete",
    ),
    path(
        "departments/<int:pk>/toggle/",
        views.toggle_department,
        name="toggle_department",
    ),
    # Salesperson Management URLs
    path("salespersons/", views.salesperson_list, name="salesperson_list"),
    path("salespersons/create/", views.salesperson_create, name="salesperson_create"),
    path(
        "salespersons/<int:pk>/update/",
        views.salesperson_update,
        name="salesperson_update",
    ),
    path(
        "salespersons/<int:pk>/delete/",
        views.salesperson_delete,
        name="salesperson_delete",
    ),
    path(
        "salespersons/<int:pk>/toggle/",
        views.toggle_salesperson,
        name="toggle_salesperson",
    ),
    # Role Management URLs
    path("roles/", views.role_management, name="role_management"),
    path("roles/list/", views.role_list, name="role_list"),
    path("roles/create/", views.role_create, name="role_create"),
    path("roles/<int:pk>/update/", views.role_update, name="role_update"),
    path("roles/<int:pk>/delete/", views.role_delete, name="role_delete"),
    path("roles/<int:pk>/assign/", views.role_assign, name="role_assign"),
    # User Management (Custom Page)
    path("manage/users/", user_manage_list, name="user_manage_list"),
    path("manage/users/<int:pk>/edit/", user_manage_edit, name="user_manage_edit"),
    path("manage/users/<int:pk>/toggle-role/", user_toggle_role_api, name="user_toggle_role_api"),
    path("manage/users/<int:pk>/permissions/", user_permissions_api, name="user_permissions_api"),
    # Theme Management
    path("save-theme/", views.set_default_theme, name="set_default_theme"),
    # 🎨 نظام الإشعارات - تم إزالته
    # 📊 نظام تتبع النشاط والمستخدمين النشطين
    path("activity/dashboard/", user_activity_dashboard, name="activity_dashboard"),
    path(
        "activity/user/<int:user_id>/",
        user_activity_detail,
        name="user_activity_detail",
    ),
    path("activity/logs/", activity_logs_list, name="activity_logs_list"),
    path("activity/logins/", login_history_list, name="login_history_list"),
    # APIs للمستخدمين النشطين
    path("api/online-users/", online_users_api, name="online_users_api"),
    path(
        "api/user-activities/<int:user_id>/",
        user_activities_api,
        name="user_activities_api",
    ),
    path("api/update-current-page/", update_current_page, name="update_current_page"),
    # 📧 نظام الرسائل الداخلية
    path("messages/inbox/", inbox, name="inbox"),
    path("messages/sent/", sent_messages, name="sent_messages"),
    path("messages/compose/", compose_message, name="compose_message"),
    path("messages/<int:message_id>/", view_message, name="view_message"),
    path("messages/<int:message_id>/delete/", delete_message, name="delete_message"),
    path("messages/<int:message_id>/mark-read/", mark_as_read, name="mark_as_read"),
    path("messages/<int:message_id>/reply/", reply_to_message, name="reply_to_message"),
    path("messages/mark-all-read/", mark_all_as_read, name="mark_all_as_read"),
    # APIs للرسائل
    path("api/messages/unread-count/", get_unread_count, name="get_unread_count"),
    path(
        "api/messages/online-users/",
        get_online_users_with_messages,
        name="get_online_users_with_messages",
    ),
    # Chat APIs
    path(
        "api/messages/history/<int:user_id>/",
        api_get_chat_history,
        name="api_get_chat_history",
    ),
    path(
        "api/messages/send/<int:user_id>/",
        api_send_chat_message,
        name="api_send_chat_message",
    ),
    path(
        "api/messages/check-new/", api_check_new_messages, name="api_check_new_messages"
    ),
    path(
        "api/messages/recent/",
        api_recent_conversations,
        name="api_recent_conversations",
    ),
]
