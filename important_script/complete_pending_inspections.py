#!/usr/bin/env python
"""
تحديث جميع المعاينات قيد الانتظار إلى مكتملة وناجحة باستخدام التحديث المجمع
وتعيين وقت الإكمال بناءً على وقت الطلب لجميع المعاينات
"""
import os
import sys

import django
from django.db import transaction
from django.utils import timezone

# إعداد Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
# Adjust path to be relative to the script's location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from inspections.models import Inspection
from orders.models import Order


def main():
    """
    الوظيفة الرئيسية لتحديث المعاينات وتعيين أوقات الإكمال بناءً على وقت الطلب
    """
    print("🔄 بدء تحديث المعاينات وتعيين أوقات الإكمال...")

    # استخدام معاملة لضمان أن جميع التحديثات تتم بنجاح أو لا يتم أي منها
    with transaction.atomic():

        # 1. تحديث المعاينات قيد الانتظار إلى مكتملة
        print("\n🔄 الخطوة 1: تحديث المعاينات قيد الانتظار...")
        pending_inspections = Inspection.objects.filter(
            status="pending"
        ).select_related("order")

        pending_count = pending_inspections.count()
        print(f"📋 تم العثور على {pending_count} معاينة قيد الانتظار.")

        if pending_count > 0:
            # تحضير البيانات للتحديث المجمع للمعاينات قيد الانتظار
            pending_to_update = []
            for inspection in pending_inspections:
                inspection.status = "completed"
                inspection.result = "passed"
                # تعيين وقت الإكمال بناءً على وقت الطلب
                if inspection.order and inspection.order.order_date:
                    inspection.completed_at = inspection.order.order_date
                else:
                    inspection.completed_at = timezone.now()
                pending_to_update.append(inspection)

            # تنفيذ التحديث المجمع للمعاينات قيد الانتظار
            updated_pending = Inspection.objects.bulk_update(
                pending_to_update, ["status", "result", "completed_at"], batch_size=100
            )
            print(f"✅ تم تحديث {updated_pending} معاينة من قيد الانتظار إلى مكتملة.")

        # 2. تحديث أوقات الإكمال لجميع المعاينات المكتملة بناءً على وقت الطلب
        print("\n🔄 الخطوة 2: تحديث أوقات الإكمال لجميع المعاينات المكتملة...")

        completed_inspections = Inspection.objects.filter(
            status="completed"
        ).select_related("order")

        completed_count = completed_inspections.count()
        print(f"📋 تم العثور على {completed_count} معاينة مكتملة لتحديث أوقات الإكمال.")

        if completed_count > 0:
            # تحضير البيانات للتحديث المجمع لأوقات الإكمال
            completed_to_update = []
            updated_times_count = 0

            for inspection in completed_inspections:
                if inspection.order and inspection.order.order_date:
                    # تحديث وقت الإكمال فقط إذا كان مختلفاً عن وقت الطلب
                    if inspection.completed_at != inspection.order.order_date:
                        inspection.completed_at = inspection.order.order_date
                        completed_to_update.append(inspection)
                        updated_times_count += 1

            # تنفيذ التحديث المجمع لأوقات الإكمال
            if completed_to_update:
                Inspection.objects.bulk_update(
                    completed_to_update, ["completed_at"], batch_size=100
                )
                print(
                    f"✅ تم تحديث أوقات الإكمال لـ {updated_times_count} معاينة مكتملة."
                )
            else:
                print("ℹ️ جميع المعاينات المكتملة لها أوقات إكمال صحيحة بالفعل.")

        # 3. تحديث حالات الطلبات المرتبطة
        print("\n🔄 الخطوة 3: تحديث حالات الطلبات المرتبطة...")

        # الحصول على جميع الطلبات التي لها معاينات
        orders_with_inspections = Order.objects.filter(
            id__in=Inspection.objects.values_list("order_id", flat=True)
        ).distinct()

        orders_updated = 0
        for order in orders_with_inspections:
            if order:
                # تحديث حالة المعاي��ة في الطلب
                order.update_inspection_status()
                # تحديث حالة الإكمال العامة
                order.update_completion_status()
                orders_updated += 1

        print(f"✅ تم تحديث حالات {orders_updated} طلب مرتبط.")

        # 4. إحصائيات نهائية شاملة
        print(f"\n📊 إحصائيات التحديث النهائية:")

        # إحصائيات المعاينات
        total_completed = Inspection.objects.filter(status="completed").count()
        total_pending = Inspection.objects.filter(status="pending").count()
        total_passed = Inspection.objects.filter(result="passed").count()

        print(f"   📋 إجمالي المعاينات المكتملة: {total_completed}")
        print(f"   ⏳ إجمالي المعاينات قيد الانتظار: {total_pending}")
        print(f"   ✅ إجمالي المعاينات الناجحة: {total_passed}")
        print(f"   🔄 المعاينات المحولة من قيد الانتظار: {pending_count}")
        print(
            f"   ⏰ المعاينات المحدثة الأوقات: {updated_times_count if 'updated_times_count' in locals() else 0}"
        )
        print(f"   📋 الطلبات المحدثة: {orders_updated}")
        print(f"   🕐 وقت التنفيذ: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n🎉 تم إنجاز جميع التحديثات بنجاح!")
    print("✨ جميع المعاينات الآن لها أوقات إكمال تتطابق مع أوقات طلباتها")


if __name__ == "__main__":
    main()
