from django.urls import path
from . import views

app_name = 'cutting'

urlpatterns = [
    # الصفحة الرئيسية لنظام التقطيع
    path('', views.CuttingDashboardView.as_view(), name='dashboard'),
    
    # أوامر التقطيع
    path('orders/', views.CuttingOrderListView.as_view(), name='order_list'),
    path('orders/warehouse/<int:warehouse_id>/', views.CuttingOrderListView.as_view(), name='order_list_by_warehouse'),
    path('orders/<int:pk>/', views.CuttingOrderDetailView.as_view(), name='order_detail'),
    path('orders/<str:cutting_code>/', views.cutting_order_detail_by_code, name='order_detail_by_code'),
    path('orders/create-from-order/<int:order_id>/', views.create_cutting_order_from_order, name='create_from_order'),
    path('orders/<int:order_id>/start/', views.start_cutting_order, name='start_order'),
    
    # إدارة عناصر التقطيع
    path('items/<int:pk>/update/', views.update_cutting_item, name='update_item'),
    path('items/<int:pk>/complete/', views.complete_cutting_item, name='complete_item'),
    path('items/<int:pk>/reject/', views.reject_cutting_item, name='reject_item'),
    
    # العمليات المجمعة
    path('orders/<int:order_id>/bulk-update/', views.bulk_update_items, name='bulk_update'),
    path('orders/<int:order_id>/bulk-complete/', views.bulk_complete_items, name='bulk_complete'),
    
    # التقارير
    path('reports/', views.CuttingReportsView.as_view(), name='reports'),
    path('reports/generate/', views.generate_cutting_report, name='generate_report'),
    path('reports/daily/<int:warehouse_id>/', views.daily_cutting_report, name='daily_report'),
    path('reports/print/<int:report_id>/', views.print_cutting_report, name='print_report'),
    
    # طباعة التقارير اليومية
    path('print/daily/<str:date>/<str:receiver>/', views.print_daily_delivery_report, name='print_daily_delivery'),
    
    # API endpoints
    path('api/warehouse-stats/<int:warehouse_id>/', views.warehouse_cutting_stats, name='warehouse_stats_api'),
    path('api/item-status/<int:item_id>/', views.get_item_status, name='item_status_api'),
    path('api/notifications/', views.cutting_notifications_api, name='notifications_api'),
    
    # إعدادات المستودعات
    path('settings/warehouses/', views.WarehouseSettingsView.as_view(), name='warehouse_settings'),
    path('settings/permissions/', views.UserPermissionsView.as_view(), name='user_permissions'),
]
