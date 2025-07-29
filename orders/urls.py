from django.urls import path
from . import views
from . import dashboard_views
from .views import OrdersDashboardView

app_name = 'orders'

urlpatterns = [
    # الداشبورد الجديد كصفحة رئيسية
    path('', dashboard_views.orders_dashboard, name='orders_dashboard'),
    
    # الجدول الشامل للطلبات
    path('all/', views.order_list, name='order_list'),

    # صفحات الطلبات المنفصلة حسب النوع
    path('inspection/', dashboard_views.inspection_orders, name='inspection_orders'),
    path('installation/', dashboard_views.installation_orders, name='installation_orders'),
    path('accessory/', dashboard_views.accessory_orders, name='accessory_orders'),
    path('tailoring/', dashboard_views.tailoring_orders, name='tailoring_orders'),

    # Old dashboard (deactivated)
    path('dashboard/', OrdersDashboardView.as_view(), name='dashboard'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
    path('<int:pk>/success/', views.order_success, name='order_success'),
    path('create/', views.order_create, name='order_create'),
    path('<int:pk>/update/', views.order_update, name='order_update'),
    path('<int:pk>/delete/', views.order_delete, name='order_delete'),

    # Payment Views
    path('payment/<int:order_pk>/create/', views.payment_create, name='payment_create'),
    path('payment/<int:pk>/delete/', views.payment_delete, name='payment_delete'),

    # Salesperson Views
    path('salesperson/', views.salesperson_list, name='salesperson_list'),

    # Update Order Status
    path('order/<int:order_id>/update-status/', views.update_order_status, name='update_status'),

    # API endpoints
    path('api/order-details/<int:order_id>/', views.get_order_details_api, name='order_details_api'),
    path('api/customer-inspections/', views.get_customer_inspections, name='customer_inspections_api'),
]