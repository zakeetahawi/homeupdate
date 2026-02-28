#!/usr/bin/env python
"""
سكريبت إصلاح حالات أوامر التقطيع وعناصرها
==============================================
يقوم بالإصلاحات التالية:

1. إصلاح عناصر التقطيع التي لديها بيانات إكمال ولكن الحالة ليست "مكتمل"
2. إصلاح أوامر التقطيع التي جميع عناصرها مكتملة ولكن حالة الأمر ليست "مكتمل"
3. إصلاح أوامر التقطيع الفارغة (تم نقل جميع عناصرها)

الاستخدام:
    python fix_cutting_status.py              # وضع المعاينة (لا يغير شيئاً)
    python fix_cutting_status.py --apply      # تطبيق الإصلاحات
    python fix_cutting_status.py --apply -v   # تطبيق مع تفاصيل مطولة

آمن للتشغيل على الإنتاج - يعمل داخل transaction واحدة.
"""

import argparse
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from cutting.models import CuttingOrder, CuttingOrderItem


def fix_cutting_item_status(apply=False, verbose=False):
    """إصلاح عناصر التقطيع التي لديها بيانات إكمال ولكن الحالة خاطئة"""

    bad_items = CuttingOrderItem.objects.filter(
        Q(status="pending") | Q(status="in_progress"),
        cutter_name__isnull=False,
        receiver_name__isnull=False,
        permit_number__isnull=False,
        cutting_date__isnull=False,
    ).exclude(
        cutter_name=""
    ).exclude(
        receiver_name=""
    ).exclude(
        permit_number=""
    ).select_related(
        "cutting_order",
        "order_item",
        "order_item__product",
    )

    count = bad_items.count()
    print(f"\n{'='*60}")
    print(f"1. عناصر تقطيع لديها بيانات إكمال ولكن الحالة خاطئة: {count}")
    print(f"{'='*60}")

    if count == 0:
        print("   ✅ لا توجد عناصر تحتاج إصلاح")
        return 0

    for item in bad_items:
        product_name = "خارجي" if item.is_external else (
            item.order_item.product.name[:40] if item.order_item and item.order_item.product else "غير محدد"
        )
        if verbose:
            print(
                f"   [{item.id}] {product_name} | "
                f"أمر: {item.cutting_order.cutting_code} | "
                f"الحالة: {item.status} → completed | "
                f"إذن: {item.permit_number} | "
                f"مستلم: {item.receiver_name}"
            )

    if apply:
        updated = bad_items.update(status="completed")
        print(f"   ✅ تم إصلاح {updated} عنصر")
        return updated
    else:
        print(f"   ⚠️  سيتم إصلاح {count} عنصر (استخدم --apply للتطبيق)")
        return 0


def fix_cutting_order_status(apply=False, verbose=False):
    """إصلاح أوامر التقطيع التي جميع عناصرها مكتملة ولكنها ليست مكتملة"""

    # أوامر تقطيع غير مكتملة
    orders = CuttingOrder.objects.filter(
        Q(status="pending") | Q(status="in_progress") | Q(status="partially_completed")
    ).annotate(
        total=Count("items"),
        completed=Count(
            "items",
            filter=Q(items__status="completed"),
        ),
        pending_count=Count(
            "items",
            filter=Q(items__status="pending"),
        ),
        rejected_count=Count(
            "items",
            filter=Q(items__status="rejected"),
        ),
    )

    stuck_orders = []
    for order in orders:
        non_pending = order.completed + order.rejected_count
        if order.total == 0 or non_pending >= order.total:
            stuck_orders.append(order)

    count = len(stuck_orders)
    print(f"\n{'='*60}")
    print(f"2. أوامر تقطيع مكتملة فعلياً ولكن الحالة خاطئة: {count}")
    print(f"{'='*60}")

    if count == 0:
        print("   ✅ لا توجد أوامر تحتاج إصلاح")
        return 0

    for order in stuck_orders:
        detail = f"عناصر: {order.total} (مكتمل: {order.completed}, مرفوض: {order.rejected_count})"
        if order.total == 0:
            detail = "أمر فارغ (تم نقل جميع العناصر)"

        if verbose:
            print(
                f"   [{order.id}] {order.cutting_code} | "
                f"الحالة: {order.status} → completed | "
                f"{detail}"
            )

    if apply:
        fixed = 0
        for order in stuck_orders:
            order.status = "completed"
            if not order.completed_at:
                order.completed_at = timezone.now()
            order.save(update_fields=["status", "completed_at"])
            fixed += 1
        print(f"   ✅ تم إصلاح {fixed} أمر تقطيع")
        return fixed
    else:
        print(f"   ⚠️  سيتم إصلاح {count} أمر (استخدم --apply للتطبيق)")
        return 0


def fix_empty_cutting_orders(apply=False, verbose=False):
    """إصلاح أوامر التقطيع الفارغة التي تم نقل جميع عناصرها"""

    empty_orders = CuttingOrder.objects.annotate(
        total=Count("items")
    ).filter(
        total=0
    ).exclude(
        status="completed"
    )

    count = empty_orders.count()
    print(f"\n{'='*60}")
    print(f"3. أوامر تقطيع فارغة (تم نقل عناصرها) وليست مكتملة: {count}")
    print(f"{'='*60}")

    if count == 0:
        print("   ✅ لا توجد أوامر فارغة تحتاج إصلاح")
        return 0

    for order in empty_orders:
        if verbose:
            print(
                f"   [{order.id}] {order.cutting_code} | "
                f"الحالة: {order.status} → completed"
            )

    if apply:
        fixed = 0
        for order in empty_orders:
            order.status = "completed"
            if not order.completed_at:
                order.completed_at = timezone.now()
            order.save(update_fields=["status", "completed_at"])
            fixed += 1
        print(f"   ✅ تم إصلاح {fixed} أمر فارغ")
        return fixed
    else:
        print(f"   ⚠️  سيتم إصلاح {count} أمر (استخدم --apply للتطبيق)")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="إصلاح حالات أوامر التقطيع وعناصرها"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="تطبيق الإصلاحات (بدون هذا الخيار يعمل كمعاينة فقط)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="عرض تفاصيل كل عنصر",
    )
    args = parser.parse_args()

    print("=" * 60)
    if args.apply:
        print("   إصلاح حالات التقطيع - وضع التطبيق")
    else:
        print("   إصلاح حالات التقطيع - وضع المعاينة")
    print("=" * 60)

    total_fixed = 0

    with transaction.atomic():
        # الخطوة 1: إصلاح العناصر أولاً
        total_fixed += fix_cutting_item_status(apply=args.apply, verbose=args.verbose)

        # الخطوة 2: إصلاح أوامر التقطيع (بعد إصلاح العناصر)
        total_fixed += fix_cutting_order_status(apply=args.apply, verbose=args.verbose)

        # الخطوة 3: إصلاح الأوامر الفارغة
        total_fixed += fix_empty_cutting_orders(apply=args.apply, verbose=args.verbose)

    print(f"\n{'='*60}")
    if args.apply:
        print(f"   تم الانتهاء - إجمالي الإصلاحات: {total_fixed}")
    else:
        print(f"   معاينة فقط - سيتم إصلاح: {total_fixed} عنصر/أمر")
        print(f"   لتطبيق الإصلاحات: python fix_cutting_status.py --apply")
    print("=" * 60)


if __name__ == "__main__":
    main()
