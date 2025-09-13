#!/usr/bin/env python3
"""
نظام رفع الملفات التلقائي - بسيط وفعال
لا ضغط على السيرفر - تجاهل الملفات غير الموجودة
"""

import os
import sys
import django
import time

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from inspections.models import Inspection

def smart_upload_system():
    """نظام رفع ذكي وبسيط"""
    print("🚀 نظام الرفع التلقائي الذكي")
    print("=" * 40)
    
    # 1. رفع العقود المعلقة
    contracts_uploaded = upload_pending_contracts()
    
    # 2. رفع المعاينات المعلقة  
    inspections_uploaded = upload_pending_inspections()
    
    # 3. عرض التقرير النهائي
    show_final_report(contracts_uploaded, inspections_uploaded)

def upload_pending_contracts():
    """رفع العقود المعلقة فقط"""
    print("📤 رفع العقود المعلقة...")
    
    # البحث عن العقود غير المرفوعة
    pending_contracts = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=True
    )
    
    uploaded_count = 0
    skipped_count = 0
    
    # رفع 20 عقد فقط في كل مرة لتجنب الضغط على السيرفر
    for order in pending_contracts[:20]:
        if order.contract_file:
            file_path = order.contract_file.path
            if os.path.exists(file_path):
                # الملف موجود - جدولة الرفع
                try:
                    from orders.tasks import upload_contract_to_drive_async
                    upload_contract_to_drive_async.delay(order.id)
                    uploaded_count += 1
                    print(f"   ✅ جدولة عقد: {order.order_number}")
                except Exception as e:
                    print(f"   ❌ خطأ عقد {order.order_number}: {e}")
            else:
                # الملف غير موجود - تجاهل بصمت
                skipped_count += 1
    
    print(f"📊 العقود: جدولة {uploaded_count}, تجاهل {skipped_count}")
    return uploaded_count

def upload_pending_inspections():
    """رفع المعاينات المعلقة فقط"""
    print("📤 رفع المعاينات المعلقة...")
    
    # البحث عن المعاينات غير المرفوعة
    pending_inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    )
    
    uploaded_count = 0
    skipped_count = 0
    
    # رفع 20 معاينة فقط في كل مرة
    for inspection in pending_inspections[:20]:
        if inspection.inspection_file:
            file_path = inspection.inspection_file.path
            if os.path.exists(file_path):
                # الملف موجود - جدولة الرفع
                try:
                    from orders.tasks import upload_inspection_to_drive_async
                    upload_inspection_to_drive_async.delay(inspection.id)
                    uploaded_count += 1
                    print(f"   ✅ جدولة معاينة: {inspection.id}")
                except Exception as e:
                    print(f"   ❌ خطأ معاينة {inspection.id}: {e}")
            else:
                # الملف غير موجود - تجاهل بصمت
                skipped_count += 1
    
    print(f"📊 المعاينات: جدولة {uploaded_count}, تجاهل {skipped_count}")
    return uploaded_count

def show_final_report(contracts_uploaded, inspections_uploaded):
    """عرض التقرير النهائي"""
    print("\n" + "=" * 40)
    print("📊 تقرير الجلسة:")
    print(f"📤 تم جدولة {contracts_uploaded} عقد")
    print(f"📤 تم جدولة {inspections_uploaded} معاينة")
    
    # إحصائيات عامة
    total_contracts = Order.objects.filter(contract_file__isnull=False).count()
    uploaded_contracts = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=False
    ).count()
    
    total_inspections = Inspection.objects.filter(inspection_file__isnull=False).count()
    uploaded_inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=False
    ).count()
    
    print(f"\n📋 الحالة العامة:")
    print(f"   عقود: {uploaded_contracts}/{total_contracts}")
    print(f"   معاينات: {uploaded_inspections}/{total_inspections}")
    print("=" * 40)

def continuous_upload_mode():
    """وضع الرفع المستمر"""
    print("🔄 وضع الرفع المستمر")
    print("سيتم رفع 40 ملف كل 5 دقائق")
    print("اضغط Ctrl+C للتوقف")
    print("=" * 40)
    
    try:
        while True:
            smart_upload_system()
            print("\n⏳ انتظار 5 دقائق...")
            time.sleep(300)  # 5 دقائق
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف النظام")

def main():
    """الدالة الرئيسية"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "continuous":
            continuous_upload_mode()
            return
        elif sys.argv[1] == "single":
            smart_upload_system()
            return
    
    # الوضع الافتراضي - رفع واحد
    smart_upload_system()
    
    print("\n💡 للرفع المستمر: python auto_upload_system.py continuous")
    print("💡 للرفع مرة واحدة: python auto_upload_system.py single")

if __name__ == "__main__":
    main()
