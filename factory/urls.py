from django.urls import path
from . import views

app_name = 'factory'

urlpatterns = [
    # Main page as factory dashboard
    path('', views.factory_dashboard, name='dashboard'),
    path('list/', views.factory_list, name='factory_list'),
    
    # Production Lines
    path('production-lines/', views.production_line_list, name='production_line_list'),
    path('production-line/<int:pk>/', views.production_line_detail, name='production_line_detail'),
    path('production-line/create/', views.production_line_create, name='production_line_create'),
    path('production-line/<int:pk>/update/', views.production_line_update, name='production_line_update'),
    path('production-line/<int:pk>/delete/', views.production_line_delete, name='production_line_delete'),
    
    # Production Orders
    path('orders/', views.production_order_list, name='production_order_list'),
    path('order/<int:pk>/', views.production_order_detail, name='production_order_detail'),
    path('order/create/', views.production_order_create, name='production_order_create'),
    path('order/<int:pk>/update/', views.production_order_update, name='production_order_update'),
    path('order/<int:pk>/delete/', views.production_order_delete, name='production_order_delete'),
    
    # Production Stages
    path('order/<int:order_pk>/stage/create/', views.production_stage_create, name='production_stage_create'),
    path('stage/<int:pk>/update/', views.production_stage_update, name='production_stage_update'),
    path('stage/<int:pk>/delete/', views.production_stage_delete, name='production_stage_delete'),
    
    # Production Issues
    path('order/<int:order_pk>/issue/create/', views.production_issue_create, name='production_issue_create'),
    path('issue/<int:pk>/update/', views.production_issue_update, name='production_issue_update'),
    path('issue/<int:pk>/delete/', views.production_issue_delete, name='production_issue_delete'),
]
