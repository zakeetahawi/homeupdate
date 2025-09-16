#!/usr/bin/env python3
"""
نظام رفع الملفات التلقائي - بسيط وفعال
"""

import os
import sys
import django
import time
from datetime import datetime

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from inspections.models import Inspection
from celery import Celery

def emergency_fix():
    """إصلاح طارئ للمشاكل"""
    print("🚨 بدء الإصلاح الطارئ...")

    # 1. تنظيف مهام Celery المعلقة
    print("🧹 تنظيف مهام Celery...")
    try:
        # الاتصال بـ Redis
        r = redis.Redis(host='localhost', port=6379, db=0)

        # حذف جميع المهام المعلقة
        r.flushdb()
        print("✅ تم تنظيف مهام Celery")
    except Exception as e:
        print(f"❌ خطأ في تنظيف Celery: {e}")

    # 1.5. إصلاح المعاينات التي تسبب timeout
    print("🔧 إصلاح المعاينات المشكلة...")
    try:
        # البحث عن المعاينة 5059 التي تسبب مشاكل
        problem_inspection = Inspection.objects.filter(id=5059).first()
        if problem_inspection:
            if problem_inspection.inspection_file and not os.path.exists(problem_inspection.inspection_file.path):
                print(f"🗑️ إزالة ملف المعاينة المفقود: {problem_inspection.id}")
                problem_inspection.inspection_file = None
                problem_inspection.save()
            elif problem_inspection.google_drive_file_id:
                print(f"✅ المعاينة {problem_inspection.id} مرفوعة بالفعل")

        # البحث عن جميع المعاينات التي قد تسبب مشاكل مشابهة
        problematic_inspections = Inspection.objects.filter(
            inspection_file__isnull=False,
            google_drive_file_id__isnull=True
        )

        fixed_count = 0
        for inspection in problematic_inspections:
            if inspection.inspection_file and not os.path.exists(inspection.inspection_file.path):
                inspection.inspection_file = None
                inspection.save()
                fixed_count += 1

        print(f"✅ تم إصلاح {fixed_count} معاينة مشكلة")

    except Exception as e:
        print(f"❌ خطأ في إصلاح المعاينات: {e}")
    
    # 2. إيقاف محاولات الرفع للملفات المفقودة
    print("🔍 البحث عن الملفات المفقودة...")
    
    # العقود المفقودة
    missing_contracts = []
    orders_with_missing_files = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=True
    )
    
    for order in orders_with_missing_files:
        if order.contract_file:
            file_path = order.contract_file.path
            if not os.path.exists(file_path):
                missing_contracts.append(order.order_number)
                # إزالة مسار الملف المفقود
                order.contract_file = None
                order.save()
                print(f"🗑️ تم إزالة مسار الملف المفقود للطلب: {order.order_number}")
    
    # المعاينات المفقودة
    missing_inspections = []
    inspections_with_missing_files = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    )

    for inspection in inspections_with_missing_files:
        if inspection.inspection_file:
            file_path = inspection.inspection_file.path
            if not os.path.exists(file_path):
                missing_inspections.append(inspection.id)
                # إزالة مسار الملف المفقود
                inspection.inspection_file = None
                inspection.save()
                print(f"🗑️ تم إزالة مسار الملف المفقود للمعاينة: {inspection.id}")
    
    # 3. رفع جميع الملفات غير المرفوعة بشكل ذكي
    print("📤 رفع جميع الملفات غير المرفوعة...")

    valid_contracts = 0
    valid_inspections = 0
    skipped_contracts = 0
    skipped_inspections = 0

    # العقود غير المرفوعة
    print("🔍 البحث عن العقود غير المرفوعة...")
    contracts_to_upload = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=True
    )

    print(f"📋 وجدت {contracts_to_upload.count()} عقد غير مرفوع")

    for order in contracts_to_upload:
        if order.contract_file and os.path.exists(order.contract_file.path):
            # التحقق من عدم وجود رفع مكرر
            if not order.contract_google_drive_file_id:
                print(f"📤 جدولة رفع عقد الطلب: {order.order_number}")
                from orders.tasks import upload_contract_to_drive_async
                upload_contract_to_drive_async.delay(order.id)
                valid_contracts += 1
            else:
                skipped_contracts += 1
        else:
            print(f"⚠️ ملف العقد مفقود للطلب: {order.order_number}")

    # المعاينات غير المرفوعة
    print("🔍 البحث عن المعاينات غير المرفوعة...")
    inspections_to_upload = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    )

    print(f"📋 وجدت {inspections_to_upload.count()} معاينة غير مرفوعة")

    for inspection in inspections_to_upload:
        if inspection.inspection_file and os.path.exists(inspection.inspection_file.path):
            # التحقق من عدم وجود رفع مكرر
            if not inspection.google_drive_file_id:
                print(f"📤 جدولة رفع معاينة: {inspection.id}")
                from orders.tasks import upload_inspection_to_drive_async
                upload_inspection_to_drive_async.delay(inspection.id)
                valid_inspections += 1
            else:
                skipped_inspections += 1
        else:
            print(f"⚠️ ملف المعاينة مفقود: {inspection.id}")
    
    # 4. تقرير النتائج
    print("\n📊 تقرير الرفع الشامل:")
    print(f"   - ملفات عقود مفقودة تم إزالتها: {len(missing_contracts)}")
    print(f"   - ملفات معاينات مفقودة تم إزالتها: {len(missing_inspections)}")
    print(f"   - عقود تم جدولة رفعها: {valid_contracts}")
    print(f"   - معاينات تم جدولة رفعها: {valid_inspections}")
    print(f"   - عقود تم تخطيها (مرفوعة بالفعل): {skipped_contracts}")
    print(f"   - معاينات تم تخطيها (مرفوعة بالفعل): {skipped_inspections}")

    if missing_contracts:
        print(f"\n⚠️ العقود المفقودة: {missing_contracts[:10]}...")

    if missing_inspections:
        print(f"\n⚠️ المعاينات المفقودة: {missing_inspections[:10]}...")

    print("\n✅ تم الرفع الشامل بنجاح!")
    print("💡 جميع الملفات الموجودة تم جدولة رفعها")
    print("🔄 لن يتم رفع الملفات مرة أخرى إذا كانت مرفوعة بالفعل")

    return {
        'missing_contracts': len(missing_contracts),
        'missing_inspections': len(missing_inspections),
        'valid_contracts': valid_contracts,
        'valid_inspections': valid_inspections,
        'skipped_contracts': skipped_contracts,
        'skipped_inspections': skipped_inspections
    }

if __name__ == "__main__":
    try:
        result = emergency_fix()
        print(f"\n🎉 الإصلاح مكتمل: {result}")
    except Exception as e:
        print(f"\n❌ خطأ في الإصلاح: {e}")
        sys.exit(1)
