from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from .views_health import health_check
from accounts.views import admin_logout_view
from inventory.views import dashboard_view
from accounts.api_views import dashboard_stats
from customers.views import customer_list, customer_detail

# Manufacturing app URLs
from manufacturing import urls as manufacturing_urls

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)

# تعريف المسارات الرئيسية
urlpatterns = [
    # المسارات الأساسية
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    # مسارات API
    path('api/dashboard/', dashboard_view, name='dashboard'),
    path('api/dashboard/stats/', dashboard_stats, name='dashboard_stats'),

    # مسارات API للعملاء
    path('api/customers/', customer_list, name='customer_list'),
    
    # Manufacturing app URLs
    path('factory/', include(manufacturing_urls)),
    path(
        'api/customers/<int:pk>/',
        customer_detail,
        name='customer_detail'
    ),

    # مسارات لوحة التحكم
    path('admin/', admin.site.urls),
    path('admin/logout/', admin_logout_view, name='admin_logout'),

    # مسارات فحص الصحة
    path('health-check/', health_check, name='health_check'),
    path('health/', health_check, name='health'),

    # مسار خدمة ملفات الوسائط
    re_path(
        r'^media/(?P<path>.*)$',
        views.serve_media_file,
        name='serve_media'
    ),

    # مسارات JWT للمصادقة في API
    path(
        'api/token/',
        TokenObtainPairView.as_view(),
        name='token_obtain_pair'
    ),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # مسارات التطبيقات
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('customers/', include('customers.urls', namespace='customers')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('inspections/', include('inspections.urls', namespace='inspections')),
    path('factory/', include(manufacturing_urls, namespace='manufacturing')),
    # إعادة توجيه من المسار القديم إلى المسار الجديد
    path('data_management/', views.data_management_redirect, name='data_management_redirect'),
    path('database/', views.data_management_redirect, name='database_redirect'),
    path('odoo-db-manager/', include('odoo_db_manager.urls', namespace='odoo_db_manager')),
]

# إضافة مسارات الملفات الثابتة ووسائط التحميل في وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
