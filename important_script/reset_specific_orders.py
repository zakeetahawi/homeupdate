#!/usr/bin/env python
"""
إعادة تعيين حالة طلبات محددة وما يتعلق بها من معاينات وأوامر تصنيع وتركيبات إلى الحالة الأساسية
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
from installations.models import InstallationSchedule
from manufacturing.models import ManufacturingOrder
from orders.models import Order


def main():
    """
    الوظيفة الرئيسية لإعادة تعيين حالات الطلبات المحددة وما يتعلق بها إلى الحالة الأساسية
    """
    # أرقام الطلبات المستهدفة
    target_order_numbers = ["7-0790-0001", "8-0769-0001", "16-0085-0001", "7-0888-0001"]

    print(f"🔄 بدء إعادة تعيين الطلبات المحددة...")
    print(f"📋 أرقام الطلبات المستهدفة: {', '.join(target_order_numbers)}")

    # الحصول على الطلبات المحددة
    target_orders = Order.objects.filter(order_number__in=target_order_numbers)

    if not target_orders.exists():
        print("❌ لا توجد طلبات تطابق الأرقام المحددة.")
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

        # 1. إعادة تعيين المعاينات إلى الحالة الأساسية
        print("\n🔄 بدء إعادة تعيين المعاينات إلى الحالة الأساسية...")

        inspections_to_reset = Inspection.objects.filter(order__in=target_orders)
        inspection_count = 0

        for inspection in inspections_to_reset:
            print(f"   🔧 إعادة تعيين معاينة للطلب: {inspection.order.order_number}")
            # إعادة تعيين إلى الحالة الأساسية
            inspection.status = "pending"  # الحالة الأساسية للمعاينة
            inspection.result = None  # إزالة النتيجة
            inspection.completed_at = None  # إزالة تاريخ الإكمال
            inspection.notes = ""  # مسح الملاحظات
            inspection.save()
            inspection_count += 1

        print(f"✅ تم إعادة تعيين {inspection_count} معاينة إلى الحالة الأساسية.")

        # 2. إعادة تعيين أوامر التصنيع إلى الحالة الأساسية
        print("\n🔄 بدء إعادة تعيين أوامر التصنيع إلى الحالة الأساسية...")

        manufacturing_orders_to_reset = ManufacturingOrder.objects.filter(
            order__in=target_orders
        )
        manufacturing_count = 0

        for manu_order in manufacturing_orders_to_reset:
            print(f"   🔧 إعادة تعيين أمر تصنيع للطلب: {manu_order.order.order_number}")
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
        print("\n🔄 بدء إعادة تعيين جدولة التركيب إلى الحالة الأساسية...")

        installations_to_reset = InstallationSchedule.objects.filter(
            order__in=target_orders
        )
        installation_count = 0
        deleted_count = 0

        for installation in installations_to_reset:
            print(f"   🔧 معالجة تركيب للطلب: {installation.order.order_number}")
            # التحقق من وجود ملاحظة تشير إلى أنها تم إنشاؤها تلقائياً
            if "تم إنشاء الجدولة تلقائياً" in (installation.notes or ""):
                # حذف الجدولة التي تم إنشاؤها تلقائياً
                print(f"     ❌ حذف جدولة تركيب تم إنشاؤها تلقائياً")
                installation.delete()
                deleted_count += 1
            else:
                # إعادة تعيين إلى الحالة الأساسية
                print(f"     🔄 إعادة تعيين جدولة التركيب إلى الحالة الأساسية")
                installation.status = "scheduled"  # الحالة الأساسية للتركيب
                installation.completion_date = None  # إزالة تاريخ الإكمال
                installation.notes = ""  # مسح الملاحظات
                installation.save()
                installation_count += 1

        print(f"✅ تم إعادة تعيين {installation_count} تركيب إلى الحالة الأساسية.")
        print(f"✅ تم حذف {deleted_count} جدولة تركيب تم إنشاؤها تلقائياً.")

        # 4. إعادة مزامنة جميع حالات الطلبات المستهدفة
        print("\n🔄 إعادة مزامنة حالات الطلبات المستهدفة...")

        order_count = 0
        for order in target_orders:
            print(f"   🔄 مزامنة الطلب: {order.order_number}")
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

    print(f"\n🎉 تم إنجاز إعادة تعيين الطلبات المحددة بنجاح!")
    print(f"\n📊 تقرير نهائي:")
    print(f"   📋 إجمالي الطلبات المعالجة: {target_orders.count()}")
    print(f"   📋 الطلبات المعالجة: {', '.join(found_orders)}")
    print(f"   🔍 المعاينات المعاد تعيينها: {inspection_count}")
    print(f"   🏭 أوامر التصنيع المعاد تعيينها: {manufacturing_count}")
    print(f"   🔧 التركيبات المعاد تعيينها: {installation_count}")
    print(f"   ❌ جدولة التركيب المحذوفة: {deleted_count}")


if __name__ == "__main__":
    main()
