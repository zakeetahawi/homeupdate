from django.urls import path
from . import views
from . import dashboard_views
from . import invoice_views
from . import contract_views
from . import wizard_views
from . import api_views
from .views import OrdersDashboardView

app_name = 'orders'

urlpatterns = [
    # الداشبورد الجديد كصفحة رئيسية
    path('', dashboard_views.orders_dashboard, name='orders_dashboard'),
    
    # الجدول الشامل للطلبات
    path('all/', views.order_list, name='order_list'),
    
    # API Endpoints
    path('api/products/search/', api_views.products_search_api, name='products_search_api'),
    path('api/check-invoice-number/', api_views.check_invoice_number_api, name='check_invoice_number_api'),
    path('api/salespersons/', api_views.salespersons_by_branch_api, name='salespersons_by_branch_api'),
    
    # Wizard URLs - Multi-step order creation
    path('wizard/', wizard_views.wizard_start, name='wizard_start'),
    path('wizard/new/', wizard_views.wizard_start_new, name='wizard_start_new'),
    path('wizard/confirm-new/', wizard_views.wizard_confirm_new, name='wizard_confirm_new'),
    path('wizard/delete-and-create-new/', wizard_views.wizard_delete_and_create_new, name='wizard_delete_and_create_new'),
    path('wizard/drafts/', wizard_views.wizard_drafts_list, name='wizard_drafts_list'),
    path('wizard/draft/<int:draft_id>/delete/', wizard_views.wizard_delete_draft, name='wizard_delete_draft'),
    path('wizard/step/<int:step>/', wizard_views.wizard_step, name='wizard_step'),
    path('wizard/add-item/', wizard_views.wizard_add_item, name='wizard_add_item'),
    path('wizard/remove-item/<int:item_id>/', wizard_views.wizard_remove_item, name='wizard_remove_item'),
    path('wizard/complete-step-3/', wizard_views.wizard_complete_step_3, name='wizard_complete_step_3'),
    path('wizard/finalize/', wizard_views.wizard_finalize, name='wizard_finalize'),
    path('wizard/cancel/', wizard_views.wizard_cancel, name='wizard_cancel'),
    path('wizard/add-curtain/', wizard_views.wizard_add_curtain, name='wizard_add_curtain'),
    path('wizard/edit-curtain/<int:curtain_id>/', wizard_views.wizard_edit_curtain, name='wizard_edit_curtain'),
    path('wizard/remove-curtain/<int:curtain_id>/', wizard_views.wizard_remove_curtain, name='wizard_remove_curtain'),
    path('wizard/upload-contract/', wizard_views.wizard_upload_contract, name='wizard_upload_contract'),
    path('wizard/remove-contract-file/', wizard_views.wizard_remove_contract_file, name='wizard_remove_contract_file'),
    path('wizard/delete-invoice-image/<int:image_id>/', wizard_views.delete_draft_invoice_image, name='delete_draft_invoice_image'),
    path('wizard/delete-main-invoice-image/', wizard_views.delete_main_draft_invoice_image, name='delete_main_draft_invoice_image'),
    path('wizard/edit-order/<int:order_pk>/', wizard_views.wizard_edit_order, name='wizard_edit_order'),
    
    # Wizard Edit Options - خيارات التعديل الذكية
    path('wizard/edit-options/<int:order_pk>/', wizard_views.wizard_edit_options, name='wizard_edit_options'),
    path('wizard/edit-type/<int:order_pk>/', wizard_views.wizard_edit_type, name='wizard_edit_type'),
    path('wizard/edit-items/<int:order_pk>/', wizard_views.wizard_edit_items, name='wizard_edit_items'),
    path('wizard/edit-contract/<int:order_pk>/', wizard_views.wizard_edit_contract, name='wizard_edit_contract'),
    
    # عرض العقد الإلكتروني
    path('order/<int:order_id>/contract/view/', wizard_views.view_contract_template, name='view_contract_template'),

    # صفحات الطلبات المنفصلة حسب النوع
    path('inspection/', dashboard_views.inspection_orders, name='inspection_orders'),
    path('installation/', dashboard_views.installation_orders, name='installation_orders'),
    path('accessory/', dashboard_views.accessory_orders, name='accessory_orders'),
    path('tailoring/', dashboard_views.tailoring_orders, name='tailoring_orders'),

    # Old dashboard (deactivated)
    path('dashboard/', OrdersDashboardView.as_view(), name='dashboard'),
    
    # URLs باستخدام رقم الطلب (order_number) - الأولوية الأولى
    path('order/<str:order_number>/', views.order_detail_by_number, name='order_detail_by_number'),
    path('order/<str:order_code>/', views.order_detail_by_code, name='order_detail_by_code'),
    path('order/<str:order_number>/success/', views.order_success_by_number, name='order_success_by_number'),
    path('order/<str:order_number>/update/', views.order_update_by_number, name='order_update_by_number'),
    path('order/<str:order_number>/delete/', views.order_delete_by_number, name='order_delete_by_number'),
    path('order/<str:order_number>/invoice/', views.invoice_print, name='invoice_print'),
    
    # URLs القديمة مع إعادة توجيه للجديدة
    path('<int:pk>/', views.order_detail_redirect, name='order_detail'),
    path('<int:pk>/success/', views.order_success_redirect, name='order_success'),
    path('<int:pk>/update/', views.order_update_redirect, name='order_update'),
    path('<int:pk>/delete/', views.order_delete_redirect, name='order_delete'),
    path('<int:pk>/invoice/', views.invoice_print_redirect, name='invoice_print_old'),
    path('<int:pk>/update-contract-number/', views.update_contract_number, name='update_contract_number'),
    
    path('create/', views.order_create, name='order_create'),

    # Payment Views
    path('payment/<int:order_pk>/create/', views.payment_create, name='payment_create'),
    path('payment/<int:pk>/delete/', views.payment_delete, name='payment_delete'),

    # Salesperson Views
    path('salesperson/', views.salesperson_list, name='salesperson_list'),

    # Update Order Status
    path('order/<int:order_id>/update-status/', views.update_order_status, name='update_status'),
    
    # Order Status History
    path('order/<int:order_id>/status-history/', views.order_status_history, name='status_history'),

    # API endpoints
    path('api/order-details/<int:order_id>/', views.get_order_details_api, name='order_details_api'),
    path('api/customer-inspections/', views.get_customer_inspections, name='customer_inspections_api'),

    # Contract file upload endpoints
    path('ajax/upload-contract-to-google-drive/', views.ajax_upload_contract_to_google_drive, name='ajax_upload_contract_to_google_drive'),
    path('<int:pk>/check-contract-upload-status/', views.check_contract_upload_status, name='check_contract_upload_status'),
    
    # Invoice Builder (GrapesJS-based)
    path('invoice-editor/', invoice_views.invoice_builder, name='invoice_editor'),
    path('invoice-editor/<int:template_id>/', invoice_views.invoice_builder, name='invoice_editor_edit'),
    path('templates/', invoice_views.template_list, name='template_list'),
    path('templates/analytics/', invoice_views.template_analytics, name='template_analytics'),
    
    # Template Management APIs
    path('api/templates/save/', invoice_views.save_template, name='save_template'),
    path('api/templates/<int:template_id>/load/', invoice_views.load_template, name='load_template'),
    path('api/templates/<int:template_id>/clone/', invoice_views.clone_template, name='clone_template'),
    path('api/templates/<int:template_id>/delete/', invoice_views.delete_template, name='delete_template'),
    path('api/templates/<int:template_id>/set-default/', invoice_views.set_default_template, name='set_default_template'),
    path('api/templates/<int:template_id>/export/', invoice_views.export_template, name='export_template'),
    path('api/templates/import/', invoice_views.import_template, name='import_template'),
    
    # Enhanced Invoice Printing
    path('order/<int:order_id>/preview/', invoice_views.preview_invoice, name='preview_invoice'),
    path('order/<int:order_id>/preview/<int:template_id>/', invoice_views.preview_invoice, name='preview_invoice_template'),
    path('order/<int:order_id>/print/', invoice_views.print_invoice_with_template, name='print_invoice_template'),
    path('order/<int:order_id>/print/<int:template_id>/', invoice_views.print_invoice_with_template, name='print_invoice_with_template'),

    # Contract Management URLs
    
    # ✅ تم حذف النظام القديم - استخدم الويزارد
    # path('order/<int:order_id>/contract/curtains/', ...) - محذوف
    # path('order/<int:order_id>/contract/curtains/data/', ...) - محذوف
    
    # عرض PDF فقط
    path('order/<int:order_id>/contract/pdf/', contract_views.contract_pdf_view, name='contract_pdf_view'),
    
    # إعادة توليد العقد
    path('order/<int:order_id>/contract/regenerate/', contract_views.regenerate_contract_pdf, name='regenerate_contract_pdf'),
]