from django.urls import path
from . import views

app_name = 'manufacturing'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('list/', views.ManufacturingOrderListView.as_view(), name='order_list'),
    path('create/', views.ManufacturingOrderCreateView.as_view(), name='order_create'),
    path('<int:pk>/', views.ManufacturingOrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/edit/', views.ManufacturingOrderUpdateView.as_view(), name='order_update'),
    path('<int:pk>/delete/', views.ManufacturingOrderDeleteView.as_view(), name='order_delete'),
    
    # AJAX validation URLs
    path('ajax/validate-order/', views.validate_manufacturing_order_ajax, name='validate_order_ajax'),
    path('ajax/validate-item/', views.validate_manufacturing_item_ajax, name='validate_item_ajax'),
    path('ajax/product/<int:product_id>/', views.get_product_info_ajax, name='get_product_info_ajax'),
    path('ajax/order/<int:order_id>/', views.get_order_info_ajax, name='get_order_info_ajax'),
]
