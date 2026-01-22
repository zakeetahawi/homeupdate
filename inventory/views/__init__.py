"""
Inventory Views - Base Module
نقطة الدخول الرئيسية لعروض المخزون

تم تقسيم inventory/views.py (1336 سطر) إلى وحدات معيارية
"""

# استيراد عروض المنتجات
from .product_views import (
    product_list,
    product_create,
    product_update,
    product_delete,
    product_detail,
)

# استيراد عروض المعاملات
from .transaction_views import (
    transaction_create,
    transfer_stock,
    get_product_stock_api,
)

# استيراد لوحة التحكم
from .dashboard_views import dashboard_view

# استيراد InventoryDashboardView من الملف القديم
from ..views import InventoryDashboardView

# Placeholder functions for views not yet migrated
# These will return a simple message until they are properly migrated
from django.http import HttpResponse

def bulk_upload_products(request):
    """Placeholder - to be migrated"""
    return HttpResponse("This view is being migrated. Please use the old inventory.views for now.")

def bulk_stock_update(request):
    """Placeholder - to be migrated"""
    return HttpResponse("This view is being migrated. Please use the old inventory.views for now.")

def stock_transfer_list(request):
    """Placeholder - to be migrated"""
    return HttpResponse("This view is being migrated. Please use the old inventory.views for now.")

def stock_transfer_create(request):
    """Placeholder - to be migrated"""
    return HttpResponse("This view is being migrated. Please use the old inventory.views for now.")

def stock_transfer_detail(request, pk):
    """Placeholder - to be migrated"""
    return HttpResponse("This view is being migrated. Please use the old inventory.views for now.")

def stock_transfer_receive(request, pk):
    """Placeholder - to be migrated"""
    return HttpResponse("This view is being migrated. Please use the old inventory.views for now.")

def stock_transfer_cancel(request, pk):
    """Placeholder - to be migrated"""
    return HttpResponse("This view is being migrated. Please use the old inventory.views for now.")

__all__ = [
    # Product Views
    "product_list",
    "product_create",
    "product_update",
    "product_delete",
    "product_detail",
    
    # Transaction Views
    "transaction_create",
    "transfer_stock",
    "get_product_stock_api",
    
    # Dashboard
    "dashboard_view",
    "InventoryDashboardView",
    
    # Placeholders (to be migrated)
    "bulk_upload_products",
    "bulk_stock_update",
    "stock_transfer_list",
    "stock_transfer_create",
    "stock_transfer_detail",
    "stock_transfer_receive",
    "stock_transfer_cancel",
]

# معلومات الوحدة
__version__ = "2.0.0"
__author__ = "ERP Development Team"
__description__ = "Modular inventory views for better maintainability"
