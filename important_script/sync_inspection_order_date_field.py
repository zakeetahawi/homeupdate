#!/usr/bin/env python
"""
مزامنة تواريخ المعاينات مع تواريخ الطلبات الرئيسية بما في ذلك حقل تاريخ الطلب في جدول المعاينات
"""
import os
import sys
from datetime import datetime

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
    مزامنة تواريخ المعاينات مع تواريخ الطلبات الرئيسية وتحديث حقل تاريخ الطلب
    """
    # أرقام الطلبات التي تحتاج مزامنة معايناتها
    target_order_numbers = [
        "12-0389-0004",  # احمد عبد الفتاح
        "9-0628-0002",  # احمد السيد عبد السلام
        "9-0627-0002",  # حسام محمد طلعت
        "13-0470-0004",  # ميادة الشريف
        "10-0652-0004",  # كريم حسام الدين
        "11-0261-0002",  # عادل حمزة الخضر
        "13-0476-0002",  # فريدة عزام
        "10-0146-0006",  # محمد عبد المنعم
        "13-0759-0002",  # نهلة حسين خليفه
        "10-0888-0002",  # مجدي عويس محمود
        "8-0405-0004",  # ايمن جمال
        "7-0832-0003",  # محمد فؤاد احمد
        "14-0373-0008",  # سحر محمود
    ]

    print("🔄 بدء مزامنة تواريخ المعاينات مع تواريخ الطلبات الرئيسية...")
    print("=" * 80)

    # البحث عن الطلبات
    target_orders = Order.objects.filter(order_number__in=target_order_numbers)

    if not target_orders.exists():
        print("❌ لم يتم العثور على أي من الطلبات المحددة.")
        return

    found_orders = list(target_orders.values_list("order_number", flat=True))
    missing_orders = set(target_order_numbers) - set(found_orders)

    print(
        f"✅ تم العثور على {target_orders.count()} طلب من أصل {len(target_order_numbers)}"
    )
    print(f"📋 الطلبات الموجودة: {', '.join(found_orders)}")

    if missing_orders:
        print(f"⚠️ الطلبات غير الموجودة: {', '.join(missing_orders)}")

    # استخدام معاملة لضمان أن جميع التحديثات تتم بنجاح أو لا يتم أي منها
    with transaction.atomic():

        print(f"\n🔄 مزامنة وإنهاء المعاينات...")
        print("-" * 60)

        total_inspections_updated = 0
        total_inspections_completed = 0
        orders_processed = 0

        for order in target_orders.order_by("order_number"):
            print(f"\n🔸 معالجة الطلب: {order.order_number}")
            print(f"   📅 تاريخ الطلب الرئيسي: {order.order_date}")

            # البحث عن المعاينات المرتبطة بهذا الطلب
            inspections = Inspection.objects.filter(order=order)

            if not inspections.exists():
                print(f"   ⚠️ لا توجد معاينات مرتبطة بهذا الطلب")
                continue

            inspections_updated_for_order = 0
            inspections_completed_for_order = 0

            for inspection in inspections:
                print(f"   🔍 معاينة ID: {inspection.id}")
                print(f"      📊 الحالة الحالية: {inspection.status}")
                print(f"      📅 تاريخ الإنشاء الحالي: {inspection.created_at}")
                print(f"      ⏰ تاريخ الإكمال الحالي: {inspection.completed_at}")

                # عرض جميع التواريخ الحالية في المعاينة
                possible_order_date_fields = [
                    "order_date",
                    "order_request_date",
                    "request_date",
                    "main_order_date",
                    "parent_order_date",
                ]

                for field_name in possible_order_date_fields:
                    if hasattr(inspection, field_name):
                        field_value = getattr(inspection, field_name)
                        print(f"      📋 {field_name} الحالي: {field_value}")

                if hasattr(inspection, "inspection_date"):
                    print(
                        f"      📋 تاريخ المع��ينة الحالي: {inspection.inspection_date}"
                    )

                if hasattr(inspection, "scheduled_date"):
                    print(f"      📅 تاريخ الجدولة الحالي: {inspection.scheduled_date}")

                if hasattr(inspection, "appointment_date"):
                    print(
                        f"      📅 تاريخ الموعد الحالي: {inspection.appointment_date}"
                    )

                # التحديث بناءً على تاريخ الطلب الرئيسي
                if order.order_date:
                    order_date = order.order_date

                    # 1. تحديث تاريخ إنشاء المعاينة (تاريخ طلب المعاينة)
                    old_created = inspection.created_at
                    inspection.created_at = order_date
                    print(
                        f"      ✅ تحديث تاريخ طلب المعاينة: {old_created} → {inspection.created_at}"
                    )

                    # 2. تحديث حقل تاريخ الطلب في جدول المعاينات (جميع الاحتمالات)
                    for field_name in possible_order_date_fields:
                        if hasattr(inspection, field_name):
                            old_value = getattr(inspection, field_name)
                            # تحديد نوع البيانات المطلوب (date أو datetime)
                            if old_value is not None:
                                if isinstance(old_value, datetime):
                                    setattr(inspection, field_name, order_date)
                                else:
                                    setattr(inspection, field_name, order_date.date())
                            else:
                                # إذا كان الحقل فارغ، نحدد النوع بناءً على اسم الحقل
                                if (
                                    "date" in field_name.lower()
                                    and "time" not in field_name.lower()
                                ):
                                    setattr(inspection, field_name, order_date.date())
                                else:
                                    setattr(inspection, field_name, order_date)

                            new_value = getattr(inspection, field_name)
                            print(
                                f"      ✅ تحديث {field_name}: {old_value} → {new_value}"
                            )

                    # 3. تحديث جميع تواريخ المعاينة المتاحة
                    if hasattr(inspection, "inspection_date"):
                        old_inspection_date = inspection.inspection_date
                        inspection.inspection_date = order_date.date()
                        print(
                            f"      ✅ تحديث تاريخ المعاينة: {old_inspection_date} → {inspection.inspection_date}"
                        )

                    if hasattr(inspection, "scheduled_date"):
                        old_scheduled = inspection.scheduled_date
                        inspection.scheduled_date = order_date.date()
                        print(
                            f"      ✅ تحديث تاريخ الجدولة: {old_scheduled} → {inspection.scheduled_date}"
                        )

                    if hasattr(inspection, "appointment_date"):
                        old_appointment = inspection.appointment_date
                        inspection.appointment_date = order_date.date()
                        print(
                            f"      ✅ تحديث تاريخ الموعد: {old_appointment} → {inspection.appointment_date}"
                        )

                    if hasattr(inspection, "visit_date"):
                        old_visit = inspection.visit_date
                        inspection.visit_date = order_date.date()
                        print(
                            f"      ✅ تحديث تاريخ الزيارة: {old_visit} → {inspection.visit_date}"
                        )

                    # 4. إنهاء المعاينة بنفس تاريخ الطلب
                    if inspection.status != "completed":
                        inspection.status = "completed"
                        inspection.result = "passed"  # نتيجة ناجحة
                        print(f"      ✅ تحديث حالة المعاينة إلى: مكتملة وناجحة")
                        inspections_completed_for_order += 1

                    # 5. تحديث تاريخ إكمال المعاينة
                    old_completed = inspection.completed_at
                    inspection.completed_at = order_date
                    print(
                        f"      ✅ تحديث تاريخ إكمال المعاينة: {old_completed} → {inspection.completed_at}"
                    )

                    # 6. تحديث تاريخ التحديث
                    if hasattr(inspection, "updated_at"):
                        inspection.updated_at = timezone.now()

                    # حفظ جميع التغييرات
                    inspection.save()
                    inspections_updated_for_order += 1
                    total_inspections_updated += 1

                    print(f"      💾 تم حفظ جميع التغييرات للمعاينة")

                else:
                    print(f"      ⚠️ لا يوجد تاريخ للطلب الرئيسي - لا يمكن المزامنة")

            total_inspections_completed += inspections_completed_for_order

            print(f"   📊 تم تحديث {inspections_updated_for_order} معاينة لهذا الطلب")
            print(f"   ✅ تم إكمال {inspections_completed_for_order} معاينة جديدة")

            # تحديث حالة الطلب الرئيسي
            if inspections_updated_for_order > 0:
                order.update_inspection_status()
                order.update_completion_status()
                print(f"   🔄 تم تحديث حالة الطلب الرئيسي")

            orders_processed += 1

        print(f"\n📊 إحصائيات المزامنة النهائية:")
        print("=" * 50)
        print(f"   📋 الطلبات المعالجة: {orders_processed}")
        print(f"   🔍 إجمالي المعاينات المحدثة: {total_inspections_updated}")
        print(f"   ✅ إجمالي المعاينات المكتملة: {total_inspections_completed}")
        print(f"   🕐 وقت التنفيذ: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # التحقق من النتائج
        print(f"\n🔍 التحقق من النتائج...")

        for order in target_orders[:3]:  # عرض أول 3 طلبات للتحقق
            inspections = Inspection.objects.filter(order=order)
            print(f"   📋 الطلب {order.order_number}:")
            print(f"      📅 تاريخ الطلب الرئيسي: {order.order_date}")

            for inspection in inspections:
                print(f"      🔍 معاينة {inspection.id}:")
                print(f"         📊 الحالة: {inspection.status}")
                print(f"         🎯 النتيجة: {inspection.result}")
                print(f"         📅 تاريخ طلب المعاينة: {inspection.created_at}")
                print(f"         ⏰ تاريخ إكمال المعاينة: {inspection.completed_at}")

                # عرض جميع حقول التاريخ المحدثة
                possible_order_date_fields = [
                    "order_date",
                    "order_request_date",
                    "request_date",
                    "main_order_date",
                    "parent_order_date",
                ]

                for field_name in possible_order_date_fields:
                    if hasattr(inspection, field_name):
                        field_value = getattr(inspection, field_name)
                        if field_value:
                            print(f"         📋 {field_name}: {field_value}")

                if (
                    hasattr(inspection, "inspection_date")
                    and inspection.inspection_date
                ):
                    print(f"         📋 تاريخ المعاينة: {inspection.inspection_date}")

                if hasattr(inspection, "scheduled_date") and inspection.scheduled_date:
                    print(f"         📅 تاريخ الجدولة: {inspection.scheduled_date}")

                # التحقق من التطابق
                if inspection.created_at and order.order_date:
                    if inspection.created_at.date() == order.order_date.date():
                        print(
                            f"         ✅ تاريخ طلب المعاينة يطابق تاريخ الطلب الرئيسي"
                        )
                    else:
                        print(
                            f"         ⚠️ تاريخ طلب المعاينة لا يطابق تاريخ الطلب الرئيسي"
                        )

                if inspection.completed_at and order.order_date:
                    if inspection.completed_at.date() == order.order_date.date():
                        print(
                            f"         ✅ تاريخ إكمال المعاينة يطابق تاريخ الطلب الرئيسي"
                        )
                    else:
                        print(
                            f"         ⚠️ تاريخ إكمال المعاينة لا يطابق تاريخ الطلب الرئيسي"
                        )

    print(f"\n🎉 تم إنجاز مزامنة وإنهاء جميع المعاينات بنجاح!")
    print("✨ جميع المعاينات الآن:")
    print("   📅 تاريخ طلب المعاينة = تاريخ الطلب الرئيسي")
    print("   📋 تاريخ الطلب في ��دول المعاينات = تاريخ الطلب الرئيسي")
    print("   ⏰ تاريخ إكمال المعاينة = تاريخ الطلب الرئيسي")
    print("   📊 الحالة = مكتملة وناجحة")


if __name__ == "__main__":
    main()
