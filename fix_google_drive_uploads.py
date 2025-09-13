#!/usr/bin/env python3
"""
سكريبت لإصلاح مشاكل رفع الملفات إلى Google Drive
يفحص الملفات المفقودة ويعيد جدولة رفعها
"""

import os
import sys
import django
from pathlib import Path

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.db import transaction
from orders.models import Order
from inspections.models import Inspection
from orders.tasks import upload_contract_to_drive_async
from orders.tasks import upload_inspection_to_drive_async
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_and_fix_contract_files():
    """
    فحص وإصلاح ملفات العقود
    """
    print("🔍 فحص ملفات العقود...")
    
    # البحث عن الطلبات التي لديها ملفات عقود ولم يتم رفعها
    orders_with_contracts = Order.objects.filter(
        contract_file__isnull=False,
        is_contract_uploaded_to_drive=False
    )
    
    print(f"📊 وجدت {orders_with_contracts.count()} طلب يحتاج رفع ملف العقد")
    
    fixed_count = 0
    missing_count = 0
    rescheduled_count = 0
    
    for order in orders_with_contracts:
        try:
            # التحقق من وجود الملف
            if order.contract_file and hasattr(order.contract_file, 'path'):
                file_path = Path(order.contract_file.path)
                
                if file_path.exists():
                    print(f"✅ الملف موجود للطلب {order.order_number}: {file_path.name}")
                    
                    # إعادة جدولة رفع الملف
                    try:
                        upload_contract_to_drive_async.delay(order.pk)
                        rescheduled_count += 1
                        print(f"📤 تم جدولة رفع الملف للطلب {order.order_number}")
                    except Exception as e:
                        print(f"❌ خطأ في جدولة رفع الملف للطلب {order.order_number}: {e}")
                        
                else:
                    print(f"❌ الملف مفقود للطلب {order.order_number}: {file_path}")
                    missing_count += 1
                    
                    # البحث عن الملف في مجلدات أخرى
                    found_file = find_missing_file(file_path.name)
                    if found_file:
                        print(f"🔍 وجدت الملف في: {found_file}")
                        # يمكن إضافة منطق لنقل الملف هنا
                        
            else:
                print(f"⚠️ لا يوجد مسار ملف للطلب {order.order_number}")
                
        except Exception as e:
            print(f"❌ خطأ في معالجة الطلب {order.pk}: {e}")
    
    print(f"\n📈 النتائج:")
    print(f"   - ملفات تم جدولة رفعها: {rescheduled_count}")
    print(f"   - ملفات مفقودة: {missing_count}")
    
    return rescheduled_count, missing_count

def check_and_fix_inspection_files():
    """
    فحص وإصلاح ملفات المعاينات
    """
    print("\n🔍 فحص ملفات المعاينات...")
    
    # البحث عن المعاينات التي لديها ملفات ولم يتم رفعها
    inspections_with_files = Inspection.objects.filter(
        inspection_file__isnull=False,
        is_uploaded_to_drive=False
    )
    
    print(f"📊 وجدت {inspections_with_files.count()} معاينة تحتاج رفع الملف")
    
    rescheduled_count = 0
    missing_count = 0
    
    for inspection in inspections_with_files:
        try:
            # التحقق من وجود الملف
            if inspection.inspection_file and hasattr(inspection.inspection_file, 'path'):
                file_path = Path(inspection.inspection_file.path)
                
                if file_path.exists():
                    print(f"✅ الملف موجود للمعاينة {inspection.pk}: {file_path.name}")
                    
                    # إعادة جدولة رفع الملف
                    try:
                        upload_inspection_to_drive_async.delay(inspection.pk)
                        rescheduled_count += 1
                        print(f"📤 تم جدولة رفع الملف للمعاينة {inspection.pk}")
                    except Exception as e:
                        print(f"❌ خطأ في جدولة رفع الملف للمعاينة {inspection.pk}: {e}")
                        
                else:
                    print(f"❌ الملف مفقود للمعاينة {inspection.pk}: {file_path}")
                    missing_count += 1
                    
        except Exception as e:
            print(f"❌ خطأ في معالجة المعاينة {inspection.pk}: {e}")
    
    print(f"\n📈 النتائج:")
    print(f"   - ملفات تم جدولة رفعها: {rescheduled_count}")
    print(f"   - ملفات مفقودة: {missing_count}")
    
    return rescheduled_count, missing_count

def find_missing_file(filename):
    """
    البحث عن ملف مفقود في مجلدات مختلفة
    """
    search_paths = [
        '/home/zakee/homeupdate/media/contracts/',
        '/home/zakee/homeupdate/media/inspections/files/',
        '/home/zakee/homeupdate/media/',
    ]
    
    for search_path in search_paths:
        for root, dirs, files in os.walk(search_path):
            for file in files:
                if filename in file or file in filename:
                    return os.path.join(root, file)
    
    return None

def main():
    """
    الدالة الرئيسية
    """
    print("🚀 بدء إصلاح مشاكل رفع الملفات إلى Google Drive")
    print("=" * 60)
    
    try:
        # فحص وإصلاح ملفات العقود
        contract_rescheduled, contract_missing = check_and_fix_contract_files()
        
        # فحص وإصلاح ملفات المعاينات
        inspection_rescheduled, inspection_missing = check_and_fix_inspection_files()
        
        print("\n" + "=" * 60)
        print("📊 ملخص النتائج النهائية:")
        print(f"   - إجمالي ملفات العقود المجدولة: {contract_rescheduled}")
        print(f"   - إجمالي ملفات المعاينات المجدولة: {inspection_rescheduled}")
        print(f"   - إجمالي الملفات المفقودة: {contract_missing + inspection_missing}")
        
        if contract_rescheduled + inspection_rescheduled > 0:
            print("\n✅ تم جدولة الملفات بنجاح! ستبدأ عملية الرفع خلال دقائق.")
            print("💡 يمكنك مراقبة التقدم في ملف logs/celery_optimized.log")
        
        if contract_missing + inspection_missing > 0:
            print(f"\n⚠️ يوجد {contract_missing + inspection_missing} ملف مفقود يحتاج مراجعة يدوية")
        
    except Exception as e:
        print(f"❌ خطأ في تنفيذ السكريبت: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
