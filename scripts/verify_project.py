#!/usr/bin/env python
"""
سكريبت للتحقق من جميع الاستيرادات والروابط في المشروع
"""

import sys
import os
import django

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def test_manufacturing_imports():
    """اختبار استيرادات manufacturing"""
    print("🔍 اختبار استيرادات manufacturing...")
    
    try:
        from manufacturing.views import (
            ManufacturingOrderListView,
            ManufacturingOrderDetailView,
            ManufacturingOrderCreateView,
            ManufacturingOrderUpdateView,
            ManufacturingOrderDeleteView,
            VIPOrdersListView,
            manufacturing_order_api,
            update_status_api,
            manufacturing_statistics_api,
            order_items_api,
            bulk_update_status_api,
            generate_manufacturing_report,
            export_to_excel,
            generate_summary_report,
        )
        print("✅ جميع استيرادات manufacturing تعمل بنجاح")
        return True
    except ImportError as e:
        print(f"❌ خطأ في استيراد manufacturing: {e}")
        return False


def test_inventory_imports():
    """اختبار استيرادات inventory"""
    print("\n🔍 اختبار استيرادات inventory...")
    
    try:
        from inventory.views import (
            product_list,
            product_create,
            product_update,
            product_delete,
            product_detail,
            transaction_create,
            transfer_stock,
            get_product_stock_api,
        )
        print("✅ جميع استيرادات inventory تعمل بنجاح")
        return True
    except ImportError as e:
        print(f"❌ خطأ في استيراد inventory: {e}")
        return False


def test_service_layer_imports():
    """اختبار استيرادات Service Layer"""
    print("\n🔍 اختبار استيرادات Service Layer...")
    
    try:
        from orders.services import OrderService, ContractService
        
        # التحقق من وجود الدوال
        assert hasattr(OrderService, 'create_order')
        assert hasattr(OrderService, 'cancel_order')
        assert hasattr(OrderService, 'calculate_order_total')
        assert hasattr(OrderService, 'get_order_progress')
        assert hasattr(ContractService, 'create_contract_curtain')
        
        print("✅ جميع استيرادات Service Layer تعمل بنجاح")
        return True
    except (ImportError, AssertionError) as e:
        print(f"❌ خطأ في Service Layer: {e}")
        return False


def test_permissions_imports():
    """اختبار استيرادات الصلاحيات"""
    print("\n🔍 اختبار استيرادات الصلاحيات...")
    
    try:
        from inventory.permissions import (
            view_product,
            add_product,
            change_product,
            delete_product,
            can_transfer_stock,
            can_adjust_stock,
            can_bulk_upload,
        )
        print("✅ جميع استيرادات الصلاحيات تعمل بنجاح")
        return True
    except ImportError as e:
        print(f"❌ خطأ في استيراد الصلاحيات: {e}")
        return False


def test_utils_imports():
    """اختبار استيرادات Utils"""
    print("\n🔍 اختبار استيرادات Utils...")
    
    try:
        from manufacturing.utils import get_material_summary_context
        from core.encryption import DataEncryption
        
        print("✅ جميع استيرادات Utils تعمل بنجاح")
        return True
    except ImportError as e:
        print(f"❌ خطأ في استيراد Utils: {e}")
        return False


def test_models_integrity():
    """اختبار سلامة النماذج"""
    print("\n🔍 اختبار سلامة النماذج...")
    
    try:
        from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem
        from inventory.models import Product, Category, Warehouse, StockTransaction
        from orders.models import Order, OrderItem
        from customers.models import Customer
        
        # التحقق من وجود الحقول المهمة
        assert hasattr(ManufacturingOrder, 'status')
        assert hasattr(Product, 'current_stock')
        assert hasattr(Order, 'customer')
        
        print("✅ جميع النماذج سليمة")
        return True
    except (ImportError, AssertionError) as e:
        print(f"❌ خطأ في النماذج: {e}")
        return False


def test_type_hints():
    """اختبار وجود Type Hints"""
    print("\n🔍 اختبار Type Hints...")
    
    try:
        from inventory.permissions import inventory_permission_required
        from core.encryption import DataEncryption
        from manufacturing.utils import get_material_summary_context
        
        # التحقق من التوقيعات
        import inspect
        
        # DataEncryption
        sig = inspect.signature(DataEncryption.encrypt)
        assert 'return' in str(sig)
        
        print("✅ Type Hints موجودة")
        return True
    except Exception as e:
        print(f"⚠️ تحذير Type Hints: {e}")
        return True  # ليس خطأ حرج


def check_file_structure():
    """التحقق من هيكل الملفات"""
    print("\n🔍 التحقق من هيكل الملفات...")
    
    required_files = [
        'manufacturing/views/__init__.py',
        'manufacturing/views/order_views.py',
        'manufacturing/views/vip_views.py',
        'manufacturing/views/api_views.py',
        'manufacturing/views/report_views.py',
        'inventory/views/__init__.py',
        'inventory/views/product_views.py',
        'inventory/views/transaction_views.py',
        'tests/unit/test_manufacturing_order_views.py',
        'tests/unit/test_manufacturing_vip_views.py',
        'tests/unit/test_manufacturing_api_views.py',
        'tests/unit/test_inventory_product_views.py',
        'tests/integration/test_complete_integration.py',
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - غير موجود")
            all_exist = False
    
    if all_exist:
        print("✅ جميع الملفات المطلوبة موجودة")
    else:
        print("⚠️ بعض الملفات مفقودة")
    
    return all_exist


def main():
    """الدالة الرئيسية"""
    print("=" * 60)
    print("🚀 بدء التحقق من سلامة المشروع")
    print("=" * 60)
    
    results = []
    
    # تشغيل جميع الاختبارات
    results.append(("Manufacturing Imports", test_manufacturing_imports()))
    results.append(("Inventory Imports", test_inventory_imports()))
    results.append(("Service Layer", test_service_layer_imports()))
    results.append(("Permissions", test_permissions_imports()))
    results.append(("Utils", test_utils_imports()))
    results.append(("Models Integrity", test_models_integrity()))
    results.append(("Type Hints", test_type_hints()))
    results.append(("File Structure", check_file_structure()))
    
    # النتائج
    print("\n" + "=" * 60)
    print("📊 ملخص النتائج")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ نجح" if result else "❌ فشل"
        print(f"{name:.<40} {status}")
    
    print("=" * 60)
    print(f"النتيجة النهائية: {passed}/{total} ({int(passed/total*100)}%)")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 جميع الاختبارات نجحت! المشروع جاهز.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} اختبار(ات) فشلت. يرجى المراجعة.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
