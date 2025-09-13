from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView, TemplateView
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views_health import health_check
from accounts.views import admin_logout_view
from inventory.views import dashboard_view
from .csrf_views import get_csrf_token_view, csrf_debug_view, test_csrf_view
from accounts.api_views import dashboard_stats
from customers.views import customer_list, customer_detail
from . import api_monitoring

# تم حذف test_completion_view


from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)

# تعريف المسارات الرئيسية
urlpatterns = [
    # المسارات الأساسية
    path("", views.home, name="home"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    # مسارات API
    path("api/dashboard/", dashboard_view, name="dashboard"),
    path("api/dashboard/stats/", dashboard_stats, name="dashboard_stats"),
    # مسارات API للعملاء
    path("api/customers/", customer_list, name="customer_list"),
    path("api/customers/<int:pk>/", customer_detail, name="customer_detail"),
    # Manufacturing app URLs - using include with explicit namespace
    # مسارات لوحة التحكم
    path("admin/", admin.site.urls),
    path("admin/logout/", admin_logout_view, name="admin_logout"),
    # مسارات فحص الصحة
    path("health-check/", health_check, name="health_check"),
    path("health/", health_check, name="health"),
    # مسارات CSRF للتشخيص والاختبار
    path("csrf-token/", get_csrf_token_view, name="csrf_token"),
    path("csrf-debug/", csrf_debug_view, name="csrf_debug"),
    path("csrf-test/", test_csrf_view, name="csrf_test"),
    # مسار اختبار إشارات الإكمال - تم حذفه مؤقتاً
    # مسار خدمة ملفات الوسائط
    re_path(r"^media/(?P<path>.*)$", views.serve_media_file, name="serve_media"),
    # مسارات JWT للمصادقة في API
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    # مسارات التطبيقات
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("customers/", include("customers.urls", namespace="customers")),
    path("inventory/", include("inventory.urls", namespace="inventory")),
    path("orders/", include("orders.urls", namespace="orders")),
    path("reports/", include("reports.urls", namespace="reports")),
    path("inspections/", include("inspections.urls", namespace="inspections")),
    path(
        "manufacturing/",
        include(("manufacturing.urls", "manufacturing"), namespace="manufacturing"),
    ),
    path(
        "cutting/",
        include(("cutting.urls", "cutting"), namespace="cutting"),
    ),
    path(
        "complaints/", include("complaints.urls", namespace="complaints")
    ),  # نظام إدارة الشكاوى
    path(
        "notifications/", include("notifications.urls", namespace="notifications")
    ),  # نظام الإشعارات المتكامل
    # إعادة توجيه من factory إلى manufacturing
    path("factory/", RedirectView.as_view(url="/manufacturing/", permanent=True)),
    # إعادة توجيه من المسار القديم إلى المسار الجديد
    path(
        "data_management/",
        views.data_management_redirect,
        name="data_management_redirect",
    ),
    path("database/", views.data_management_redirect, name="database_redirect"),
    path(
        "odoo-db-manager/", include("odoo_db_manager.urls", namespace="odoo_db_manager")
    ),
    # تضمين مسارات التركيبات
    path(
        "installations/",
        include(("installations.urls", "installations"), namespace="installations"),
    ),
    # نظام النسخ الاحتياطي والاستعادة الجديد
    path("backup-system/", include("backup_system.urls", namespace="backup_system")),


    # لوحة مراقبة النظام
    path("monitoring/", views.monitoring_dashboard, name="monitoring_dashboard"),

    # API مراقبة النظام وقاعدة البيانات
    path("api/monitoring/status/", api_monitoring.monitoring_status, name="monitoring_status"),
    path("api/monitoring/database/", api_monitoring.database_stats, name="database_stats"),
    path("api/monitoring/system/", api_monitoring.system_stats, name="system_stats"),
    path("api/monitoring/pool/", api_monitoring.pool_stats, name="pool_stats"),
    path("api/monitoring/actions/", api_monitoring.DatabaseActionsView.as_view(), name="database_actions"),
    path("api/monitoring/health/", api_monitoring.health_check, name="health_check"),
    path("api/monitoring/alerts/", api_monitoring.alerts, name="monitoring_alerts"),

    # صفحة اختبار نظيفة
    path("test-clean/", TemplateView.as_view(template_name="test_clean.html"), name="test_clean"),
    path("test-minimal/", views.test_minimal_view, name="test_minimal"),

    # صفحة اختبار نوع الشكوى
    path("test-complaint-type/", TemplateView.as_view(template_name="test_complaint_type_debug.html"), name="test_complaint_type_debug"),

    # أداة مسح cache المتصفح
    path("clear-cache/", views.clear_cache_view, name="clear_cache"),

    # إنهاء طلبات الدردشة القديمة
    re_path(r'^ws/chat/.*$', views.chat_gone_view, name="chat_gone"),

]

# إضافة مسارات الملفات الثابتة ووسائط التحميل في وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # تم تعطيل Debug Toolbar URLs لتحسين الأداء
    # import debug_toolbar
    # urlpatterns = [
    #     path('__debug__/', include(debug_toolbar.urls)),
    # ] + urlpatterns
