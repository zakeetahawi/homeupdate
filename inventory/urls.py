from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('', views.InventoryDashboardView.as_view(), name='dashboard'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/update/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/update/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # Transactions
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('products/<int:product_pk>/transaction/', views.transaction_create, name='transaction_create'),
    
    # Adjustments
    path('adjustments/', views.adjustment_list, name='adjustment_list'),
    path('adjustments/create/', views.adjustment_create, name='adjustment_create'),
    path('adjustments/<int:pk>/', views.adjustment_detail, name='adjustment_detail'),
    path('adjustments/<int:pk>/update/', views.adjustment_update, name='adjustment_update'),
    path('adjustments/<int:pk>/delete/', views.adjustment_delete, name='adjustment_delete'),
    
    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/update/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    
    # Warehouses
    path('warehouses/', views.warehouse_list, name='warehouse_list'),
    path('warehouses/create/', views.warehouse_create, name='warehouse_create'),
    path('warehouses/<int:pk>/', views.warehouse_detail, name='warehouse_detail'),
    path('warehouses/<int:pk>/update/', views.warehouse_update, name='warehouse_update'),
    path('warehouses/<int:pk>/delete/', views.warehouse_delete, name='warehouse_delete'),
    
    # Warehouse Locations
    path('warehouse-locations/', views.warehouse_location_list, name='warehouse_location_list'),
    path('warehouse-locations/create/', views.warehouse_location_create, name='warehouse_location_create'),
    path('warehouse-locations/<int:pk>/update/', views.warehouse_location_update, name='warehouse_location_update'),
    path('warehouse-locations/<int:pk>/delete/', views.warehouse_location_delete, name='warehouse_location_delete'),
    
    # Alerts
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/<int:pk>/', views.alert_detail, name='alert_detail'),
    path('alerts/<int:pk>/resolve/', views.alert_resolve, name='alert_resolve'),
    path('alerts/<int:pk>/delete/', views.alert_delete, name='alert_delete'),
    
    # Reports
    path('reports/', views.report_list, name='report_list'),
    path('reports/low-stock/', views.low_stock_report, name='low_stock_report'),
    path('reports/stock-movement/', views.stock_movement_report, name='stock_movement_report'),
    
    # Purchase Orders
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<int:pk>/update/', views.purchase_order_update, name='purchase_order_update'),
    path('purchase-orders/<int:pk>/delete/', views.purchase_order_delete, name='purchase_order_delete'),
    path('purchase-orders/<int:pk>/receive/', views.purchase_order_receive, name='purchase_order_receive'),
    
    # API endpoints
    path('api/products/<int:pk>/', views.product_api_detail, name='product_api_detail'),
    path('api/products/', views.product_api_list, name='product_api_list'),
    
    # AJAX endpoints
    path('ajax/validate-product/', views.validate_product_ajax, name='validate_product_ajax'),
    path('ajax/validate-transaction/', views.validate_transaction_ajax, name='validate_transaction_ajax'),
    path('ajax/stock/<int:product_id>/info/', views.get_stock_info_ajax, name='stock_info_ajax'),
]

