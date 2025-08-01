from django.urls import path
from . import views
from .views import InventoryDashboardView
from .dashboard_view_append import optimized_product_detail
from .views_extended import (
    category_list, category_create, category_update, category_delete,
    warehouse_list, warehouse_create,
    supplier_list,
    purchase_order_list,
    alert_list, alert_resolve, alert_ignore, alert_resolve_multiple
)
from .views_warehouse_locations import (
    warehouse_location_list, warehouse_location_create, warehouse_location_update,
    warehouse_location_delete, warehouse_location_detail
)
from .views_reports import (
    report_list, low_stock_report, stock_movement_report
)

app_name = 'inventory'

urlpatterns = [
    # Dashboard as main page
    path('', InventoryDashboardView.as_view(), name='dashboard'),

    # Products
    path('products/', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/create/', views.product_create, name='product_create'),
    path('product/<int:pk>/update/', views.product_update, name='product_update'),
    path('product/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('product/<int:product_pk>/transaction/create/', views.transaction_create, name='transaction_create'),

    # Categories
    path('categories/', category_list, name='category_list'),
    path('category/create/', category_create, name='category_create'),
    path('category/<int:pk>/update/', category_update, name='category_update'),
    path('category/<int:pk>/delete/', category_delete, name='category_delete'),

    # Stock Transactions
    path('transactions/', views.product_list, name='transaction_list'),  # مؤقتاً يستخدم نفس صفحة المنتجات

    # Stock Adjustments
    path('adjustments/', views.product_list, name='adjustment_list'),  # مؤقتاً يستخدم نفس صفحة المنتجات

    # Purchase Orders
    path('purchase-orders/', purchase_order_list, name='purchase_order_list'),
    path('purchase-order/create/', views.product_list, name='purchase_order_create'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('purchase-order/<int:pk>/', views.product_list, name='purchase_order_detail'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('purchase-order/<int:pk>/update/', views.product_list, name='purchase_order_update'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('purchase-order/<int:pk>/delete/', views.product_list, name='purchase_order_delete'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('purchase-order/<int:pk>/receive/', views.product_list, name='purchase_order_receive'),  # مؤقتاً يستخدم نفس صفحة المنتجات

    # Suppliers
    path('suppliers/', supplier_list, name='supplier_list'),
    path('supplier/create/', views.product_list, name='supplier_create'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('supplier/<int:pk>/update/', views.product_list, name='supplier_update'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('supplier/<int:pk>/delete/', views.product_list, name='supplier_delete'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('supplier/<int:pk>/', views.product_list, name='supplier_detail'),  # مؤقتاً يستخدم نفس صفحة المنتجات

    # Warehouses
    path('warehouses/', warehouse_list, name='warehouse_list'),
    path('warehouse/create/', warehouse_create, name='warehouse_create'),
    path('warehouse/<int:pk>/update/', views.product_list, name='warehouse_update'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('warehouse/<int:pk>/delete/', views.product_list, name='warehouse_delete'),  # مؤقتاً يستخدم نفس صفحة المنتجات
    path('warehouse/<int:pk>/', views.product_list, name='warehouse_detail'),  # مؤقتاً يستخدم نفس صفحة المنتجات

    # Warehouse Locations
    path('warehouse-locations/', warehouse_location_list, name='warehouse_location_list'),
    path('warehouse-location/create/', warehouse_location_create, name='warehouse_location_create'),
    path('warehouse-location/<int:pk>/update/', warehouse_location_update, name='warehouse_location_update'),
    path('warehouse-location/<int:pk>/delete/', warehouse_location_delete, name='warehouse_location_delete'),
    path('warehouse-location/<int:pk>/', warehouse_location_detail, name='warehouse_location_detail'),

    # Reports
    path('reports/', report_list, name='report_list'),
    path('reports/low-stock/', low_stock_report, name='low_stock_report'),
    path('reports/stock-movement/', stock_movement_report, name='stock_movement_report'),
    path('product/<int:product_id>/detail/', optimized_product_detail, name='optimized_product_detail'),

    # Stock Alerts
    path('alerts/', alert_list, name='alert_list'),
    path('alert/<int:pk>/resolve/', alert_resolve, name='alert_resolve'),
    path('alert/<int:pk>/ignore/', alert_ignore, name='alert_ignore'),
    path('alerts/resolve-multiple/', alert_resolve_multiple, name='alert_resolve_multiple'),

    # API Endpoints
    path('api/product/<int:pk>/', views.product_api_detail, name='product_api_detail'),
    path('api/products/', views.product_api_list, name='product_api_list'),
    path('api/product-autocomplete/', views.product_api_autocomplete, name='product_api_autocomplete'),
]

