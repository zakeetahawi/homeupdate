#!/usr/bin/env python
"""
سكريبت اختبار المزامنة الشاملة مع Google Sheets
يمكن تشغيله عبر: python manage.py shell < test_comprehensive_sync.py
"""

import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

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
    create_sheets_service,
    GoogleSyncConfig
)

def test_comprehensive_sync():
    """اختبار المزامنة الشاملة"""
    print("=== بدء اختبار المزامنة الشاملة ===")
    
    # الحصول على إعداد المزامنة
    config = GoogleSyncConfig.get_active_config()
    if not config:
        print("❌ لا يوجد إعداد مزامنة نشط")
        return
    
    print(f"✅ تم العثور على إعداد المزامنة: {config.name}")
    
    # الحصول على بيانات الاعتماد
    credentials = config.get_credentials()
    if not credentials:
        print("❌ فشل قراءة بيانات الاعتماد")
        return
    
    print("✅ تم قراءة بيانات الاعتماد بنجاح")
    
    # إنشاء خدمة Google Sheets
    sheets_service = create_sheets_service(credentials)
    if not sheets_service:
        print("❌ فشل إنشاء خدمة Google Sheets")
        return
    
    print("✅ تم إنشاء خدمة Google Sheets بنجاح")
    
    # اختبار الدوال الجديدة
    test_functions = [
        ("أوامر التصنيع", sync_manufacturing_orders),
        ("الفنيين", sync_technicians),
        ("فرق التركيب", sync_installation_teams),
        ("الموردين", sync_suppliers),
        ("البائعين", sync_salespersons),
        ("العملاء الشامل", sync_comprehensive_customers),
        ("المستخدمين الشامل", sync_comprehensive_users),
        ("المنتجات والمخزون الشامل", sync_comprehensive_inventory),
        ("إعدادات النظام الشامل", sync_comprehensive_system_settings),
    ]
    
    results = {}
    
    for name, func in test_functions:
        print(f"\n🔄 اختبار مزامنة {name}...")
        try:
            result = func(sheets_service, config.spreadsheet_id)
            if result['status'] == 'success':
                print(f"✅ {name}: {result['message']}")
                results[name] = 'نجح'
            else:
                print(f"❌ {name}: {result['message']}")
                results[name] = f"فشل: {result['message']}"
        except Exception as e:
            print(f"❌ {name}: خطأ في التنفيذ - {str(e)}")
            results[name] = f"خطأ: {str(e)}"
    
    # طباعة النتائج النهائية
    print("\n" + "="*50)
    print("📊 ملخص نتائج الاختبار:")
    print("="*50)
    
    success_count = 0
    for name, status in results.items():
        if status == 'نجح':
            print(f"✅ {name}: {status}")
            success_count += 1
        else:
            print(f"❌ {name}: {status}")
    
    print(f"\n📈 النتيجة النهائية: {success_count}/{len(results)} نجح")
    
    if success_count == len(results):
        print("🎉 تم اختبار جميع الدوال بنجاح!")
    else:
        print("⚠️ بعض الدوال تحتاج إلى مراجعة")

if __name__ == "__main__":
    test_comprehensive_sync()
