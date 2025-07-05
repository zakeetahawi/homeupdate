from django.urls import path
from django.contrib.auth.decorators import login_required, permission_required
from . import views

app_name = 'manufacturing'

urlpatterns = [
    # Manufacturing Orders
    path('', 
         login_required(views.ManufacturingOrderListView.as_view()), 
         name='order_list'),
    
    path('create/', 
         permission_required('manufacturing.add_manufacturingorder')(
             views.ManufacturingOrderCreateView.as_view()
         ), 
         name='order_create'),
    
    path('<int:pk>/', 
         permission_required('manufacturing.view_manufacturingorder')(
             views.ManufacturingOrderDetailView.as_view()
         ), 
         name='order_detail'),
    
    path('<int:pk>/update/', 
         permission_required('manufacturing.change_manufacturingorder')(
             views.ManufacturingOrderUpdateView.as_view()
         ), 
         name='order_update'),
    
    path('<int:pk>/delete/', 
         permission_required('manufacturing.delete_manufacturingorder')(
             views.ManufacturingOrderDeleteView.as_view()
         ), 
         name='order_delete'),
    
    # API Endpoints
    path('api/orders/<int:pk>/status/', 
         views.update_order_status, 
         name='api_update_order_status'),
    
    path('api/orders/<int:pk>/exit-permit/', 
         views.update_exit_permit, 
         name='api_update_exit_permit'),
    
    # Print Manufacturing Order
    path('<int:pk>/print/', 
         permission_required('manufacturing.view_manufacturingorder')(
             views.print_manufacturing_order
         ), 
         name='order_print'),
    
    # Create from Order
    path('from-order/<int:order_id>/', 
         permission_required('manufacturing.add_manufacturingorder')(
             views.create_from_order
         ), 
         name='create_from_order'),
]
