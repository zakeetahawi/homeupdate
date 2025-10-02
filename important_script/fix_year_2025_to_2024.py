#!/usr/bin/env python
"""
تصحيح السنة من 2025 إلى 2024 للطلبات المحددة وما يتعلق بها من معاينات وأوامر تصنيع وتركيبات
"""
import os
import sys
from datetime import datetime, timedelta

import django
from django.db import transaction
from django.utils import timezone

# إعداد Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
# Adjust path to be relative to the script's location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from inspections.models import Inspection
from installations.models import InstallationSchedule
from manufacturing.models import ManufacturingOrder
from orders.models import Order


def fix_date_year(date_obj, target_year=2024):
    """
    تغيير سنة التاريخ إلى السنة المحددة مع الحفاظ على الشهر واليوم والوقت
    """
    if date_obj is None:
        return None

    try:
        return date_obj.replace(year=target_year)
    except ValueError:
        # في حالة 29 فبراير في سنة غير كبيسة
        return date_obj.replace(year=target_year, day=28)


def main():
    """
    الوظيفة الرئيسية لتصحيح السنة من 2025 إلى 2024
    """
    # أرقام الطلبات التي تحتاج تصحيح السنة
    target_order_numbers = [
        "9-0628-0002",
        "9-0627-0002",
        "12-0389-0004",
        "13-0470-0004",
        "10-0652-0004",
        "11-0261-0002",
        "13-0476-0002",
        "10-0146-0006",
        "13-0759-0002",
        "10-0888-0002",
        "8-0405-0004",
        "7-0832-0003",
        "14-0373-0008",
    ]

    print("🔧 بدء تصحيح السنة من 2025 إلى 2024 للطلبات المحددة...")
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

        orders_updated = 0
        inspections_updated = 0
        manufacturing_updated = 0
        installations_updated = 0

        # 1. تصحيح تواريخ الطلبات
        print(f"\n🔄 الخطوة 1: تصحيح تواريخ الطلبات...")

        orders_to_update = []
        for order in target_orders:
            print(f"   🔸 معالجة الطلب: {order.order_number}")

            # تصحيح تاريخ الطلب
            if order.order_date and order.order_date.year == 2025:
                old_date = order.order_date
                order.order_date = fix_date_year(order.order_date, 2024)
                print(f"      📅 تاريخ الطلب: {old_date} → {order.order_date}")
                orders_to_update.append(order)

            # تصحيح تواريخ أخرى في الطلب إذا وجدت
            if (
                hasattr(order, "created_at")
                and order.created_at
                and order.created_at.year == 2025
            ):
                order.created_at = fix_date_year(order.created_at, 2024)

            if (
                hasattr(order, "updated_at")
                and order.updated_at
                and order.updated_at.year == 2025
            ):
                order.updated_at = fix_date_year(order.updated_at, 2024)

        # تحديث الطلبات بالتحديث المجمع
        if orders_to_update:
            Order.objects.bulk_update(
                orders_to_update,
                ["order_date", "created_at", "updated_at"],
                batch_size=50,
            )
            orders_updated = len(orders_to_update)
            print(f"✅ تم تحديث {orders_updated} طلب.")

        # 2. تصحيح تواريخ المعاينات
        print(f"\n🔄 الخطوة 2: تصحيح تواريخ المعاينات...")

        inspections = Inspection.objects.filter(order__in=target_orders)
        inspections_to_update = []

        for inspection in inspections:
            updated = False
            print(
                f"   🔍 معالجة معاينة ID: {inspection.id} للطلب: {inspection.order.order_number}"
            )

            # تصحيح تاريخ الإكمال
            if inspection.completed_at and inspection.completed_at.year == 2025:
                old_date = inspection.completed_at
                inspection.completed_at = fix_date_year(inspection.completed_at, 2024)
                print(f"      ⏰ تاريخ الإكمال: {old_date} → {inspection.completed_at}")
                updated = True

            # تصحيح تاريخ الإنشاء
            if inspection.created_at and inspection.created_at.year == 2025:
                old_date = inspection.created_at
                inspection.created_at = fix_date_year(inspection.created_at, 2024)
                print(f"      📅 تاريخ الإنشاء: {old_date} → {inspection.created_at}")
                updated = True

            # تصحيح تاريخ التحديث
            if (
                hasattr(inspection, "updated_at")
                and inspection.updated_at
                and inspection.updated_at.year == 2025
            ):
                inspection.updated_at = fix_date_year(inspection.updated_at, 2024)
                updated = True

            if updated:
                inspections_to_update.append(inspection)

        # تحديث المعاينات بالتحديث المجمع
        if inspections_to_update:
            Inspection.objects.bulk_update(
                inspections_to_update,
                ["completed_at", "created_at", "updated_at"],
                batch_size=50,
            )
            inspections_updated = len(inspections_to_update)
            print(f"✅ تم تحديث {inspections_updated} معاينة.")

        # 3. تصحيح تواريخ أوامر التصنيع
        print(f"\n🔄 الخطوة 3: تصحيح تواريخ أوامر التصنيع...")

        manufacturing_orders = ManufacturingOrder.objects.filter(
            order__in=target_orders
        )
        manufacturing_to_update = []

        for manu_order in manufacturing_orders:
            updated = False
            print(
                f"   🏭 معالجة أمر تصنيع ID: {manu_order.id} للطلب: {manu_order.order.order_number}"
            )

            # تصحيح تاريخ الإكمال
            if manu_order.completion_date and manu_order.completion_date.year == 2025:
                old_date = manu_order.completion_date
                manu_order.completion_date = fix_date_year(
                    manu_order.completion_date, 2024
                )
                print(
                    f"      ⏰ تاريخ الإكمال: {old_date} → {manu_order.completion_date}"
                )
                updated = True

            # تصحيح تاريخ التسليم
            if manu_order.delivery_date and manu_order.delivery_date.year == 2025:
                old_date = manu_order.delivery_date
                manu_order.delivery_date = fix_date_year(manu_order.delivery_date, 2024)
                print(
                    f"      🚚 تاريخ التسليم: {old_date} → {manu_order.delivery_date}"
                )
                updated = True

            # تصحيح تاريخ الإنشاء
            if manu_order.created_at and manu_order.created_at.year == 2025:
                manu_order.created_at = fix_date_year(manu_order.created_at, 2024)
                updated = True

            if updated:
                manufacturing_to_update.append(manu_order)

        # تحديث أوامر التصنيع بالتحديث المجمع
        if manufacturing_to_update:
            ManufacturingOrder.objects.bulk_update(
                manufacturing_to_update,
                ["completion_date", "delivery_date", "created_at"],
                batch_size=50,
            )
            manufacturing_updated = len(manufacturing_to_update)
            print(f"✅ تم تحديث {manufacturing_updated} أمر تصنيع.")

        # 4. تصحيح تواريخ التركي��ات
        print(f"\n🔄 الخطوة 4: تصحيح تواريخ التركيبات...")

        installations = InstallationSchedule.objects.filter(order__in=target_orders)
        installations_to_update = []

        for installation in installations:
            updated = False
            print(
                f"   🔧 معالجة تركيب ID: {installation.id} للطلب: {installation.order.order_number}"
            )

            # تصحيح تاريخ الجدولة
            if installation.scheduled_date and installation.scheduled_date.year == 2025:
                old_date = installation.scheduled_date
                installation.scheduled_date = installation.scheduled_date.replace(
                    year=2024
                )
                print(
                    f"      📅 تاريخ الجدولة: {old_date} → {installation.scheduled_date}"
                )
                updated = True

            # تصحيح تاريخ الإكمال
            if (
                installation.completion_date
                and installation.completion_date.year == 2025
            ):
                old_date = installation.completion_date
                installation.completion_date = fix_date_year(
                    installation.completion_date, 2024
                )
                print(
                    f"      ⏰ تاريخ الإكمال: {old_date} → {installation.completion_date}"
                )
                updated = True

            # تصحيح تاريخ الإنشاء
            if installation.created_at and installation.created_at.year == 2025:
                installation.created_at = fix_date_year(installation.created_at, 2024)
                updated = True

            if updated:
                installations_to_update.append(installation)

        # تحديث التركيبات بالتحديث المجمع
        if installations_to_update:
            InstallationSchedule.objects.bulk_update(
                installations_to_update,
                ["scheduled_date", "completion_date", "created_at"],
                batch_size=50,
            )
            installations_updated = len(installations_to_update)
            print(f"✅ تم تحديث {installations_updated} تركيب.")

        # 5. تحديث حالات الطلبات
        print(f"\n🔄 الخطوة 5: تحديث حالات الطلبات...")

        for order in target_orders:
            order.update_all_statuses()

        print(f"✅ تم تحديث حالات جميع الطلبات.")

    # 6. إحصائيات نهائية
    print(f"\n📊 إحصائيات التصحيح النهائية:")
    print("=" * 50)
    print(f"   📋 الطلبات المحدثة: {orders_updated}")
    print(f"   🔍 المعاينات المحدثة: {inspections_updated}")
    print(f"   🏭 أوامر التصنيع المحدثة: {manufacturing_updated}")
    print(f"   🔧 التركيبات المحدثة: {installations_updated}")
    print(f"   🕐 وقت التنفيذ: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n🎉 تم إنجاز تصحيح جميع التواريخ من 2025 إلى 2024 بنجاح!")
    print("✨ جميع التواريخ الآن في السنة الصحيحة 2024")


if __name__ == "__main__":
    main()
