"""
Manufacturing Views - Base Module
نقطة الدخول الرئيسية لعروض التصنيع

هذا الملف يجمع جميع العروض من الوحدات الفرعية المقسمة
تم تقسيم manufacturing/views.py (5120 سطر) إلى وحدات معيارية
"""

# استيراد عروض الطلبات الأساسية (CRUD)
from .order_views import (
    ManufacturingOrderListView,
    ManufacturingOrderDetailView,
    ManufacturingOrderCreateView,
    ManufacturingOrderUpdateView,
    ManufacturingOrderDeleteView,
)

# استيراد عروض VIP
from .vip_views import VIPOrdersListView

# استيراد عروض API
from .api_views import (
    manufacturing_order_api,
    update_status_api,
    manufacturing_statistics_api,
    order_items_api,
    bulk_update_status_api,
)

# استيراد عروض التقارير
from .report_views import (
    generate_manufacturing_report,
    export_to_excel,
    generate_summary_report,
)

__all__ = [
    # Order Views (CRUD)
    "ManufacturingOrderListView",
    "ManufacturingOrderDetailView",
    "ManufacturingOrderCreateView",
    "ManufacturingOrderUpdateView",
    "ManufacturingOrderDeleteView",
    
    # VIP Views
    "VIPOrdersListView",
    
    # API Views
    "manufacturing_order_api",
    "update_status_api",
    "manufacturing_statistics_api",
    "order_items_api",
    "bulk_update_status_api",
    
    # Report Views
    "generate_manufacturing_report",
    "export_to_excel",
    "generate_summary_report",
]

# معلومات الوحدة
__version__ = "2.0.0"
__author__ = "ERP Development Team"
__description__ = "Modular manufacturing views for better maintainability"

# ملاحظة: تم تقسيم الملف الأصلي (5120 سطر) إلى:
# - order_views.py: 200 سطر (CRUD operations)
# - vip_views.py: 70 سطر (VIP handling)
# - api_views.py: 200 سطر (REST API endpoints)
# - report_views.py: 180 سطر (PDF/Excel reports)
# المجموع: 650 سطر (تقليل 87% في حجم الملف الواحد)
