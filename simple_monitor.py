#!/usr/bin/env python3
"""
مراقب بسيط لحالة الرفع
"""

import os
import sys
import django

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from inspections.models import Inspection

def show_status():
    """عرض حالة الرفع"""
    print("📊 حالة الرفع الحالية")
    print("=" * 30)
    
    # العقود
    total_contracts = Order.objects.filter(contract_file__isnull=False).count()
    uploaded_contracts = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=False
    ).count()
    pending_contracts = total_contracts - uploaded_contracts
    
    # المعاينات
    total_inspections = Inspection.objects.filter(inspection_file__isnull=False).count()
    uploaded_inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=False
    ).count()
    pending_inspections = total_inspections - uploaded_inspections
    
    # حساب النسب
    contract_percentage = (uploaded_contracts / total_contracts * 100) if total_contracts > 0 else 0
    inspection_percentage = (uploaded_inspections / total_inspections * 100) if total_inspections > 0 else 0
    
    print(f"📋 العقود:")
    print(f"   مرفوع: {uploaded_contracts:,}")
    print(f"   معلق: {pending_contracts:,}")
    print(f"   النسبة: {contract_percentage:.1f}%")
    
    print(f"\n📋 المعاينات:")
    print(f"   مرفوع: {uploaded_inspections:,}")
    print(f"   معلق: {pending_inspections:,}")
    print(f"   النسبة: {inspection_percentage:.1f}%")
    
    print("=" * 30)

def count_existing_files():
    """عد الملفات الموجودة فعلياً"""
    print("🔍 فحص الملفات الموجودة...")
    
    # فحص العقود
    existing_contracts = 0
    missing_contracts = 0
    
    for order in Order.objects.filter(contract_file__isnull=False, contract_google_drive_file_id__isnull=True):
        if order.contract_file and os.path.exists(order.contract_file.path):
            existing_contracts += 1
        else:
            missing_contracts += 1
    
    # فحص المعاينات
    existing_inspections = 0
    missing_inspections = 0
    
    for inspection in Inspection.objects.filter(inspection_file__isnull=False, google_drive_file_id__isnull=True):
        if inspection.inspection_file and os.path.exists(inspection.inspection_file.path):
            existing_inspections += 1
        else:
            missing_inspections += 1
    
    print(f"📁 ملفات موجودة:")
    print(f"   عقود: {existing_contracts}")
    print(f"   معاينات: {existing_inspections}")
    
    print(f"\n❌ ملفات مفقودة:")
    print(f"   عقود: {missing_contracts}")
    print(f"   معاينات: {missing_inspections}")

def main():
    """الدالة الرئيسية"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "files":
        count_existing_files()
    else:
        show_status()

if __name__ == "__main__":
    main()
