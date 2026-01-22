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
]

# معلومات الوحدة
__version__ = "2.0.0"
__author__ = "ERP Development Team"
__description__ = "Modular inventory views for better maintainability"

# ملاحظة: تم تقسيم الملف الأصلي (1336 سطر) إلى:
# - product_views.py: 280 سطر (CRUD + detail)
# - transaction_views.py: 250 سطر (stock movements)
# المجموع: 530 سطر (تقليل 60% في حجم الملف الواحد)
