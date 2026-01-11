#!/usr/bin/env python
"""
إعادة تعيين حالة الطلبات وما يتعلق بها من معاينات وأوامر تصنيع وتركيبات إلى الحالة الأساسية
للطلبات التي لها تاريخ من 30-6-2025 إلى تاريخ اليوم
"""
import os
import sys
from datetime import date, datetime

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


def main():
    """
    الوظيفة الرئيسية لإعادة تعيين حالات الطلبات وما يتعلق بها إلى الحالة الأساسية
    للطلبات التي لها تاريخ من 30-6-2025 إلى تاريخ اليوم
    """
    # تحديد نطاق التواريخ
    start_date = date(2025, 6, 30)
    end_date = timezone.now().date()

    print(f"🔄 بدء إعادة تعيين الطلبات من {start_date} إلى {end_date}...")

    # الحصول على الطلبات في النطاق الزمني المحدد
    target_orders = Order.objects.filter(
        order_date__date__gte=start_date, order_date__date__lte=end_date
    )

    if not target_orders.exists():
        print("❌ لا توجد طلبات في النطاق الزمني المحدد.")
        return

    print(f"📋 تم العثور على {target_orders.count()} طلب في النطاق الزمني المحدد.")

    # استخدام معاملة لضمان أن جميع التحديثات تتم بنجاح أو لا يتم أي منها
    with transaction.atomic():

        # 1. إعادة تعيين المعاينات إلى الحالة الأساسية
        print("🔄 بدء إعادة تعيين المعاينات إلى الحالة الأساسية...")

        inspections_to_reset = Inspection.objects.filter(order__in=target_orders)
        inspection_count = 0

        for inspection in inspections_to_reset:
            # إعادة تعيين إلى الحالة الأساسية
            inspection.status = "pending"  # الحالة الأساسية للمعاينة
            inspection.result = None  # إزالة النتيجة
            inspection.completed_at = None  # إزالة تاريخ الإكمال
            inspection.notes = ""  # مسح الملاحظات
            inspection.save()
            inspection_count += 1

        print(f"✅ تم إعادة تعيين {inspection_count} معاينة إلى الحالة الأساسية.")

        # 2. إعادة تعيين أوامر التصنيع إلى الحالة الأساسية
        print("🔄 بدء إعادة تعيين أوامر التصنيع إلى الحالة الأساسية...")

        manufacturing_orders_to_reset = ManufacturingOrder.objects.filter(
            order__in=target_orders
        )
        manufacturing_count = 0

        for manu_order in manufacturing_orders_to_reset:
            # إعادة تعيين إلى الحالة الأساسية
            manu_order.status = "pending"  # الحالة الأساسية لأمر التصنيع
            manu_order.completion_date = None  # إزالة تاريخ الإكمال
            manu_order.delivery_date = None  # إزالة تاريخ التسليم
            manu_order.delivery_recipient_name = ""  # مسح اسم المستلم
            manu_order.delivery_permit_number = ""  # مسح رقم تصريح التسليم
            manu_order.notes = ""  # مسح الملاحظات
            manu_order.save()

            # تحديث حالة الطلب المرتبط
            if manu_order.order:
                manu_order.update_order_status()

            manufacturing_count += 1

        print(f"✅ تم إعادة تعيين {manufacturing_count} أمر تصنيع إلى الحالة الأساسية.")

        # 3. إعادة تعيين جدولة التركيب إلى الحالة الأساسية أو حذفها
        print("🔄 بدء إعادة تعيين جدولة التركيب إلى الحالة الأساسية...")

        installations_to_reset = InstallationSchedule.objects.filter(
            order__in=target_orders
        )
        installation_count = 0
        deleted_count = 0

        for installation in installations_to_reset:
            # التحقق من وجود ملاحظة تشير إلى أنه�� تم إنشاؤها تلقائياً
            if "تم إنشاء الجدولة تلقائياً" in (installation.notes or ""):
                # حذف الجدولة التي تم إنشاؤها تلقائياً
                installation.delete()
                deleted_count += 1
            else:
                # إعادة تعيين إلى الحالة الأساسية
                installation.status = "scheduled"  # الحالة الأساسية للتركيب
                installation.completion_date = None  # إزالة تاريخ الإكمال
                installation.notes = ""  # مسح الملاحظات
                installation.save()
                installation_count += 1

        print(f"✅ تم إعادة تعيين {installation_count} تركيب إلى الحالة الأساسية.")
        print(f"✅ تم حذف {deleted_count} جدولة تركيب تم إنشاؤها تلقائياً.")

        # 4. إعادة مزامنة جميع حالات الطلبات المستهدفة
        print("🔄 إعادة مزامنة حالات الطلبات المستهدفة...")

        order_count = 0
        for order in target_orders:
            # إعادة تعيين حالات الطلب إلى الحالة الأساسية
            order.inspection_status = "pending"
            order.manufacturing_status = "pending"
            order.installation_status = "pending"
            order.completion_status = "pending"
            order.save()

            # تحديث الحالات بناءً على الوضع الحالي
            order.update_all_statuses()
            order_count += 1

        print(f"✅ تمت إعادة مزامنة {order_count} طلب.")

    print(
        f"\n🎉 تم إنجاز إعادة تعيين جميع الطلبات من {start_date} إلى {end_date} بنجاح!"
    )
    print(f"📊 إجمالي الطلبات المعالجة: {target_orders.count()}")
    print(f"📊 المعاينات المعاد تعيينها: {inspection_count}")
    print(f"📊 أوامر التصنيع المعاد تعيينها: {manufacturing_count}")
    print(f"📊 التركيبات المعاد تعيينها: {installation_count}")
    print(f"📊 جدولة التركيب المحذوفة: {deleted_count}")


if __name__ == "__main__":
    main()
