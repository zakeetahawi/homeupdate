from django.urls import path
from . import views
from .views import OrdersDashboardView

app_name = 'orders'

urlpatterns = [
    # Order list as main page
    path('', views.order_list, name='order_list'),

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
