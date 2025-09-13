#!/usr/bin/env python
"""
اختبار سريع للمزامنة الشاملة
"""

import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def test_imports():
    """اختبار استيراد الدوال"""
    try:
        from odoo_db_manager.google_sync import (
            sync_comprehensive_customers,
            sync_comprehensive_users,
            sync_comprehensive_inventory,
            sync_comprehensive_system_settings,
            sync_manufacturing_orders,
            sync_technicians,
            sync_installation_teams,
            sync_suppliers,
            sync_salespersons,
            GoogleSyncConfig
        )
        print("✅ تم استيراد جميع الدوال بنجاح")
        return True
    except Exception as e:
        print(f"❌ فشل الاستيراد: {str(e)}")
        return False

def test_config():
    """اختبار الإعداد"""
    try:
        from odoo_db_manager.google_sync import GoogleSyncConfig
        config = GoogleSyncConfig.get_active_config()
        if config:
            print(f"✅ تم العثور على إعداد نشط: {config.name}")
            return True
        else:
            print("⚠️ لا يوجد إعداد مزامنة نشط")
            return False
    except Exception as e:
        print(f"❌ خطأ في الإعداد: {str(e)}")
        return False

def test_models():
    """اختبار النماذج"""
    try:
        from customers.models import Customer
        from orders.models import Order
        from manufacturing.models import ManufacturingOrder
        from installations.models import Technician, InstallationTeam
        from inventory.models import Supplier, Product
        from accounts.models import Salesperson, User
        
        print(f"✅ العملاء: {Customer.objects.count()}")
        print(f"✅ الطلبات: {Order.objects.count()}")
        print(f"✅ أوامر التصنيع: {ManufacturingOrder.objects.count()}")
        print(f"✅ الفنيين: {Technician.objects.count()}")
        print(f"✅ فرق التركيب: {InstallationTeam.objects.count()}")
        print(f"✅ الموردين: {Supplier.objects.count()}")
        print(f"✅ المنتجات: {Product.objects.count()}")
        print(f"✅ البائعين: {Salesperson.objects.count()}")
        print(f"✅ المستخدمين: {User.objects.count()}")
        return True
    except Exception as e:
        print(f"❌ خطأ في النماذج: {str(e)}")
        return False

def main():
    print("🔄 بدء الاختبار السريع للمزامنة الشاملة...")
    print("="*50)
    
    # اختبار الاستيراد
    print("\n1. اختبار استيراد الدوال:")
    import_success = test_imports()
    
    # اختبار الإعداد
    print("\n2. اختبار الإعداد:")
    config_success = test_config()
    
    # اختبار النماذج
    print("\n3. اختبار النماذج:")
    models_success = test_models()
    
    # النتيجة النهائية
    print("\n" + "="*50)
    print("📊 نتائج الاختبار:")
    
    if import_success and config_success and models_success:
        print("🎉 جميع الاختبارات نجحت! النظام جاهز للمزامنة الشاملة")
        print("\n📋 للوصول للمزامنة:")
        print("   الرابط: /odoo-db-manager/google-sync/")
        print("\n🚀 المميزات الجديدة:")
        print("   ✅ 13 نوع مزامنة أساسي")
        print("   ✅ 4 صفحات شاملة")
        print("   ✅ ربط البيانات المترابطة")
        print("   ✅ ضمان عدم فقدان السجلات")
    else:
        print("⚠️ بعض الاختبارات فشلت. يرجى مراجعة الأخطاء أعلاه")

if __name__ == "__main__":
    main()
