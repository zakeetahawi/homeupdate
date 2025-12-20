from django.urls import path
from . import views

app_name = 'public'

urlpatterns = [
    # QR Code export for printing (A4 layout)
    path('qr-export/', views.qr_export_page, name='qr_export'),
    
    # PDF download (all QR codes) - MUST be before <str:product_code>
    path('qr-pdf/', views.qr_pdf_download, name='qr_pdf_download'),
    
    # QR code image download
    path('qr/<str:product_code>.png', views.generate_product_qr, name='product_qr_image'),
    
    # Public product page - short URL for QR codes (catch-all, must be LAST)
    path('<str:product_code>/', views.product_qr_view, name='product_qr_page'),
]
