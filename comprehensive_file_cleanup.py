#!/usr/bin/env python3
"""
تنظيف شامل للملفات المفقودة ومنع الرفع المتكرر
"""

import os
import sys
import django
import redis

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from inspections.models import Inspection

def comprehensive_cleanup():
    """تنظيف شامل للملفات المفقودة"""
    print("🚀 بدء التنظيف الشامل للملفات المفقودة...")
    
    # 1. تنظيف مهام Celery أولاً
    print("🧹 تنظيف مهام Celery...")
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.flushdb()
        print("✅ تم تنظيف مهام Celery")
    except Exception as e:
        print(f"❌ خطأ في تنظيف Celery: {e}")
    
    # 2. تنظيف العقود المفقودة
    print("\n🔍 تنظيف العقود المفقودة...")
    
    contracts_cleaned = 0
    contracts_kept = 0
    
    all_orders = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=True
    )
    
    print(f"📋 فحص {all_orders.count()} عقد...")
    
    for order in all_orders:
        if order.contract_file:
            file_path = order.contract_file.path
            if not os.path.exists(file_path):
                # إزالة مسار الملف المفقود
                order.contract_file = None
                order.save()
                contracts_cleaned += 1
                if contracts_cleaned % 100 == 0:
                    print(f"   تم تنظيف {contracts_cleaned} عقد...")
            else:
                contracts_kept += 1
    
    print(f"✅ تم تنظيف {contracts_cleaned} عقد مفقود")
    print(f"✅ تم الاحتفاظ بـ {contracts_kept} عقد موجود")
    
    # 3. تنظيف المعاينات المفقودة
    print("\n🔍 تنظيف المعاينات المفقودة...")
    
    inspections_cleaned = 0
    inspections_kept = 0
    
    all_inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    )
    
    print(f"📋 فحص {all_inspections.count()} معاينة...")
    
    for inspection in all_inspections:
        if inspection.inspection_file:
            file_path = inspection.inspection_file.path
            if not os.path.exists(file_path):
                # إزالة مسار الملف المفقود
                inspection.inspection_file = None
                inspection.save()
                inspections_cleaned += 1
                if inspections_cleaned % 100 == 0:
                    print(f"   تم تنظيف {inspections_cleaned} معاينة...")
            else:
                inspections_kept += 1
    
    print(f"✅ تم تنظيف {inspections_cleaned} معاينة مفقودة")
    print(f"✅ تم الاحتفاظ بـ {inspections_kept} معاينة موجودة")
    
    # 4. جدولة رفع الملفات الموجودة فقط
    print("\n📤 جدولة رفع الملفات الموجودة...")
    
    # العقود الموجودة
    valid_contracts = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=True
    )
    
    contracts_scheduled = 0
    for order in valid_contracts:
        if order.contract_file and os.path.exists(order.contract_file.path):
            from orders.tasks import upload_contract_to_drive_async
            upload_contract_to_drive_async.delay(order.id)
            contracts_scheduled += 1
    
    # المعاينات الموجودة
    valid_inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    )
    
    inspections_scheduled = 0
    for inspection in valid_inspections:
        if inspection.inspection_file and os.path.exists(inspection.inspection_file.path):
            from orders.tasks import upload_inspection_to_drive_async
            upload_inspection_to_drive_async.delay(inspection.id)
            inspections_scheduled += 1
    
    print(f"✅ تم جدولة {contracts_scheduled} عقد للرفع")
    print(f"✅ تم جدولة {inspections_scheduled} معاينة للرفع")
    
    # 5. تقرير النتائج النهائي
    print("\n" + "="*60)
    print("📊 تقرير التنظيف الشامل:")
    print("="*60)
    print(f"🗑️ عقود مفقودة تم تنظيفها: {contracts_cleaned:,}")
    print(f"🗑️ معاينات مفقودة تم تنظيفها: {inspections_cleaned:,}")
    print(f"📤 عقود صحيحة تم جدولة رفعها: {contracts_scheduled}")
    print(f"📤 معاينات صحيحة تم جدولة رفعها: {inspections_scheduled}")
    print(f"💾 إجمالي الملفات المحفوظة: {contracts_kept + inspections_kept}")
    print("="*60)
    
    if contracts_cleaned > 0 or inspections_cleaned > 0:
        print("🎉 تم حل مشكلة الرفع المتكرر!")
        print("💡 الآن لن يحاول النظام رفع ملفات غير موجودة")
    
    return {
        'contracts_cleaned': contracts_cleaned,
        'inspections_cleaned': inspections_cleaned,
        'contracts_scheduled': contracts_scheduled,
        'inspections_scheduled': inspections_scheduled,
        'contracts_kept': contracts_kept,
        'inspections_kept': inspections_kept
    }

def verify_cleanup():
    """التحقق من نجاح التنظيف"""
    print("\n🔍 التحقق من نجاح التنظيف...")
    
    # فحص العقود
    remaining_missing_contracts = 0
    for order in Order.objects.filter(contract_file__isnull=False, contract_google_drive_file_id__isnull=True):
        if order.contract_file and not os.path.exists(order.contract_file.path):
            remaining_missing_contracts += 1
    
    # فحص المعاينات
    remaining_missing_inspections = 0
    for inspection in Inspection.objects.filter(inspection_file__isnull=False, google_drive_file_id__isnull=True):
        if inspection.inspection_file and not os.path.exists(inspection.inspection_file.path):
            remaining_missing_inspections += 1
    
    if remaining_missing_contracts == 0 and remaining_missing_inspections == 0:
        print("✅ التنظيف مكتمل - لا توجد ملفات مفقودة متبقية")
        return True
    else:
        print(f"⚠️ لا يزال هناك {remaining_missing_contracts} عقد و {remaining_missing_inspections} معاينة مفقودة")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء التنظيف الشامل للنظام")
    print("=" * 60)
    
    # تنفيذ التنظيف
    result = comprehensive_cleanup()
    
    # التحقق من النتائج
    success = verify_cleanup()
    
    if success:
        print("\n🎉 تم التنظيف الشامل بنجاح!")
        print("🔄 النظام الآن لن يرفع ملفات مكررة أو مفقودة")
        print("📤 فقط الملفات الموجودة ستتم جدولة رفعها")
    else:
        print("\n⚠️ قد تحتاج لتشغيل التنظيف مرة أخرى")
    
    return result

if __name__ == "__main__":
    result = main()
    print(f"\n📋 النتائج النهائية: {result}")
