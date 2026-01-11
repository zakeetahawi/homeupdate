#!/usr/bin/env python
"""
سكريبت شامل: إقفال كامل لأوامر التصنيع المكتملة
- إنشاء ManufacturingOrderItem المفقودة
- إقفال أوامر التقطيع
- استلام الأقمشة تلقائياً

الاستخدام:
    python manage.py shell < لينكس/complete_all_finished_manufacturing.py
"""

import os
import sys

import django

# إعداد Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeupdate.settings")

try:
    django.setup()
except:
    pass

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from cutting.models import CuttingOrder, CuttingOrderItem
from manufacturing.models import (
    FabricReceipt,
    FabricReceiptItem,
    ManufacturingOrder,
    ManufacturingOrderItem,
)

print("=" * 80)
print("🔄 سكريبت إقفال شامل لأوامر التصنيع المكتملة")
print("=" * 80)

# الحالات المكتملة
COMPLETED_STATUSES = ["completed", "ready_install", "delivered"]

# إحصائيات
stats = {
    "total_mfg_orders": 0,
    "mfg_items_created": 0,
    "cutting_orders_completed": 0,
    "fabric_items_received": 0,
    "errors": 0,
}

# الخطوة 1: إنشاء ManufacturingOrderItem المفقودة
print("\n" + "=" * 80)
print("📋 الخطوة 1: إنشاء عناصر التصنيع المفقودة")
print("=" * 80)

mfg_orders_completed = ManufacturingOrder.objects.filter(status__in=COMPLETED_STATUSES)
stats["total_mfg_orders"] = mfg_orders_completed.count()

print(f"\n📊 عدد أوامر التصنيع المكتملة: {stats['total_mfg_orders']}")

for mfg_order in mfg_orders_completed:
    try:
        # فحص عدد عناصر التصنيع الحالية
        existing_items_count = mfg_order.items.count()

        # البحث عن عناصر التقطيع
        cutting_items = CuttingOrderItem.objects.filter(
            cutting_order__order=mfg_order.order
        )
        cutting_items_count = cutting_items.count()

        if cutting_items_count == 0:
            continue

        # إذا كان العدد متطابق، تخطي
        if existing_items_count == cutting_items_count:
            continue

        # إنشاء العناصر المفقودة
        with transaction.atomic():
            for cutting_item in cutting_items:
                try:
                    # التحقق من وجود العنصر
                    if ManufacturingOrderItem.objects.filter(
                        cutting_item=cutting_item, manufacturing_order=mfg_order
                    ).exists():
                        continue

                    # التحقق من وجود order_item
                    if not cutting_item.order_item:
                        continue

                    # الحصول على اسم المنتج
                    try:
                        product_name = cutting_item.order_item.product.name
                    except:
                        product_name = "غير محدد"

                    # الكمية من order_item
                    try:
                        quantity = cutting_item.order_item.quantity or Decimal("1.00")
                    except:
                        quantity = Decimal("1.00")

                    # إنشاء ManufacturingOrderItem
                    ManufacturingOrderItem.objects.create(
                        manufacturing_order=mfg_order,
                        order_item=cutting_item.order_item,
                        cutting_item=cutting_item,
                        product_name=product_name,
                        quantity=quantity,
                        fabric_received=True,  # مستلم تلقائياً لأن الأمر مكتمل
                        fabric_received_date=timezone.now(),
                        fabric_notes="[تم الإنشاء والاستلام تلقائياً - أمر التصنيع مكتمل]",
                        bag_number="AUTO-COMPLETE",
                        permit_number=f"AUTO-{mfg_order.manufacturing_code}",
                    )

                    stats["mfg_items_created"] += 1

                except Exception as item_error:
                    continue

    except Exception as e:
        stats["errors"] += 1
        continue

print(f"\n✅ تم إنشاء {stats['mfg_items_created']} عنصر تصنيع")

# الخطوة 2: إقفال أوامر التقطيع
print("\n" + "=" * 80)
print("✂️ الخطوة 2: إقفال أوامر التقطيع للطلبات المكتملة")
print("=" * 80)

cutting_orders_to_check = CuttingOrder.objects.exclude(status="completed")

for cutting_order in cutting_orders_to_check:
    try:
        # البحث عن أمر التصنيع المرتبط
        manufacturing_order = (
            ManufacturingOrder.objects.filter(order=cutting_order.order)
            .order_by("-created_at")
            .first()
        )

        if not manufacturing_order:
            continue

        # التحقق من حالة أمر التصنيع
        if manufacturing_order.status not in COMPLETED_STATUSES:
            continue

        # إقفال أمر التقطيع
        with transaction.atomic():
            cutting_order.status = "completed"
            cutting_order.completed_at = timezone.now()
            cutting_order.notes = (
                (cutting_order.notes or "")
                + f"\n[إقفال تلقائي - أمر التصنيع: {manufacturing_order.get_status_display()}]"
            )
            cutting_order.save(update_fields=["status", "completed_at", "notes"])

            # إقفال جميع العناصر
            cutting_order.items.exclude(status="completed").update(status="completed")

            stats["cutting_orders_completed"] += 1

    except Exception as e:
        stats["errors"] += 1
        continue

print(f"\n✅ تم إقفال {stats['cutting_orders_completed']} أمر تقطيع")

# الخطوة 3: استلام الأقمشة
print("\n" + "=" * 80)
print("📦 الخطوة 3: استلام الأقمشة تلقائياً")
print("=" * 80)

for mfg_order in mfg_orders_completed:
    try:
        # البحث عن عناصر غير مستلمة
        unreceived_items = mfg_order.items.filter(fabric_received=False)

        if not unreceived_items.exists():
            continue

        with transaction.atomic():
            for item in unreceived_items:
                try:
                    # تحديث حالة الاستلام
                    item.fabric_received = True
                    item.fabric_received_date = timezone.now()
                    item.fabric_notes = (
                        item.fabric_notes or ""
                    ) + "\n[استلام تلقائي - أمر التصنيع مكتمل]"

                    if not item.bag_number:
                        item.bag_number = "AUTO-COMPLETE"

                    item.save(
                        update_fields=[
                            "fabric_received",
                            "fabric_received_date",
                            "fabric_notes",
                            "bag_number",
                        ]
                    )

                    # تحديث في CuttingOrderItem
                    if item.cutting_item:
                        item.cutting_item.fabric_received = True
                        item.cutting_item.save(update_fields=["fabric_received"])

                    # تحديث عبر order_item
                    if item.order_item:
                        CuttingOrderItem.objects.filter(
                            order_item=item.order_item, fabric_received=False
                        ).update(fabric_received=True)

                    # إنشاء FabricReceipt
                    fabric_receipt, created = FabricReceipt.objects.get_or_create(
                        manufacturing_order=mfg_order,
                        bag_number=item.bag_number,
                        defaults={
                            "receipt_type": "manufacturing_order",
                            "order": mfg_order.order,
                            "permit_number": item.permit_number
                            or f"AUTO-{mfg_order.manufacturing_code}",
                            "received_by_name": "نظام آلي",
                            "receipt_date": timezone.now(),
                            "notes": "استلام تلقائي - أمر التصنيع مكتمل",
                        },
                    )

                    # إنشاء FabricReceiptItem
                    if not FabricReceiptItem.objects.filter(
                        fabric_receipt=fabric_receipt, order_item=item.order_item
                    ).exists():
                        FabricReceiptItem.objects.create(
                            fabric_receipt=fabric_receipt,
                            order_item=item.order_item,
                            cutting_item=item.cutting_item,
                            product_name=item.product_name,
                            quantity_received=item.quantity,
                            item_notes="استلام تلقائي",
                        )

                    stats["fabric_items_received"] += 1

                except Exception as item_error:
                    continue

    except Exception as e:
        stats["errors"] += 1
        continue

print(f"\n✅ تم استلام {stats['fabric_items_received']} عنصر قماش")

# ملخص نهائي
print("\n" + "=" * 80)
print("📊 ملخص العمليات النهائي")
print("=" * 80)
print(f"   - أوامر التصنيع المكتملة: {stats['total_mfg_orders']}")
print(f"   - عناصر تصنيع تم إنشاؤها: {stats['mfg_items_created']}")
print(f"   - أوامر تقطيع تم إقفالها: {stats['cutting_orders_completed']}")
print(f"   - عناصر أقمشة تم استلامها: {stats['fabric_items_received']}")
print(f"   - أخطاء: {stats['errors']}")
print("=" * 80)
print("✅ اكتمل السكريبت الشامل!")
