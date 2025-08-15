from django.urls import path
from . import views
from .dashboard_view import ImprovedDashboardView

app_name = 'manufacturing'

urlpatterns = [
    path('', ImprovedDashboardView.as_view(), name='dashboard'),
    path(
        'orders/',
        views.ManufacturingOrderListView.as_view(),
        name='order_list'
    ),
    path(
        'orders/overdue/',
        views.OverdueOrdersListView.as_view(),
        name='overdue_orders'
    ),
    path(
        'orders/vip/',
        views.VIPOrdersListView.as_view(),
        name='vip_orders'
    ),
    path(
        'orders/create/',
        views.ManufacturingOrderCreateView.as_view(),
        name='order_create'
    ),
    
    # URLs باستخدام كود التصنيع
    path(
        'order/<str:manufacturing_code>/',
        views.manufacturing_order_detail_by_code,
        name='order_detail_by_code'
    ),
    
    # URLs القديمة مع إعادة توجيه
    path(
        'orders/<int:pk>/',
        views.manufacturing_order_detail_redirect,
        name='order_detail'
    ),

    path(
        'orders/<int:pk>/delete/',
        views.ManufacturingOrderDeleteView.as_view(),
        name='order_delete'
    ),
    path(
        'orders/<int:pk>/print/',
        views.print_manufacturing_order,
        name='order_print'
    ),
    path(
        'api/update_status/<int:pk>/',
        views.update_order_status,
        name='update_order_status_api'
    ),
    path(
        'api/update_exit_permit/<int:pk>/',
        views.update_exit_permit,
        name='update_exit_permit_api'
    ),
    path(
        'approval/<int:pk>/',
        views.update_approval_status,
        name='update_approval_status'
    ),
    path(
        'send_reply/<int:pk>/',
        views.send_reply,
        name='send_reply'
    ),
    path(
        'order/<int:pk>/details/',
        views.get_order_details,
        name='get_order_details'
    ),
    path(
        're_approve/<int:pk>/',
        views.re_approve_after_reply,
        name='re_approve_after_reply'
    ),
    path(
        'production-line/<int:line_id>/print/',
        views.ProductionLinePrintView.as_view(),
        name='production_line_print'
    ),
    path(
        'production-line/<int:line_id>/print-template/',
        views.ProductionLinePrintTemplateView.as_view(),
        name='production_line_print_template'
    ),
    path(
        'production-line/<int:line_id>/pdf/',
        views.ProductionLinePDFView.as_view(),
        name='production_line_pdf'
    ),
    path(
        'api/change-production-line/<int:pk>/',
        views.ChangeProductionLineView.as_view(),
        name='change_production_line_api'
    ),
    path(
        'api/production-lines/',
        views.get_production_lines_api,
        name='production_lines_api'
    ),
]
