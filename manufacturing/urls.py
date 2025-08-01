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
        'orders/create/',
        views.ManufacturingOrderCreateView.as_view(),
        name='order_create'
    ),
    path(
        'orders/<int:pk>/',
        views.ManufacturingOrderDetailView.as_view(),
        name='order_detail'
    ),
    path(
        'orders/<int:pk>/update/',
        views.ManufacturingOrderUpdateView.as_view(),
        name='order_update'
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
]
