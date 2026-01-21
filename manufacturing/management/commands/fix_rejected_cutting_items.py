"""
إعادة تعيين عناصر التقطيع المرفوضة وربطها بأوامر التصنيع

Command: python manage.py fix_rejected_cutting_items

Options:
    --dry-run: معاينة بدون تنفيذ
    --reset-only: إعادة تعيين المرفوضات فقط
    --link-only: ربط عناصر التصنيع فقط
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cutting.models import CuttingOrder, CuttingOrderItem
from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem


class Command(BaseCommand):
    """
    إعادة تعيين عناصر التقطيع المرفوضة وربطها بأوامر التصنيع.

    يقوم هذا الأمر بـ:
    1. إعادة تعيين جميع عناصر التقطيع المرفوضة إلى pending
    2. إنشاء ManufacturingOrderItem لأي عنصر تقطيع ليس له واحد
    """

    help = "إعادة تعيين عناصر التقطيع المرفوضة وربطها بأوامر التصنيع"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="معاينة التغييرات بدون تنفيذها",
        )
        parser.add_argument(
            "--reset-only",
            action="store_true",
            help="إعادة تعيين المرفوضات فقط بدون الربط",
        )
        parser.add_argument(
            "--link-only",
            action="store_true",
            help="ربط عناصر التصنيع فقط بدون إعادة التعيين",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        reset_only = options["reset_only"]
        link_only = options["link_only"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("⚠️ وضع المعاينة - لن يتم تنفيذ أي تغييرات")
            )
            self.stdout.write("")

        # المرحلة 1: إعادة تعيين المرفوضات
        if not link_only:
            self.reset_rejected_items(dry_run)

        # المرحلة 2: ربط عناصر التصنيع
        if not reset_only:
            self.link_manufacturing_items(dry_run)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✅ تم الانتهاء"))

    def reset_rejected_items(self, dry_run):
        """إعادة تعيين جميع عناصر التقطيع المرفوضة إلى pending"""
        self.stdout.write("=" * 50)
        self.stdout.write("المرحلة 1: إعادة تعيين العناصر المرفوضة")
        self.stdout.write("=" * 50)

        rejected_items = CuttingOrderItem.objects.filter(status="rejected")
        count = rejected_items.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("لا توجد عناصر مرفوضة"))
            return

        self.stdout.write(f"وُجد {count} عنصر مرفوض")
        self.stdout.write("")

        reset_count = 0
        for item in rejected_items:
            order_num = item.cutting_order.order.order_number
            product = (
                item.order_item.product.name
                if item.order_item and item.order_item.product
                else "غير محدد"
            )
            old_reason = (
                item.rejection_reason if hasattr(item, "rejection_reason") else ""
            )

            self.stdout.write(f"  • {product[:40]}")
            self.stdout.write(f"    طلب: {order_num}")
            self.stdout.write(f"    سبب الرفض: {old_reason}")

            if not dry_run:
                item.status = "pending"
                item.rejection_reason = ""
                item.save()
                self.stdout.write(self.style.SUCCESS("    ✅ تم إعادة التعيين"))
            else:
                self.stdout.write(self.style.WARNING("    [سيتم إعادة التعيين]"))

            self.stdout.write("")
            reset_count += 1

        self.stdout.write(f"إجمالي: {reset_count} عنصر")
        self.stdout.write("")

    def link_manufacturing_items(self, dry_run):
        """ربط عناصر التقطيع بأوامر التصنيع"""
        self.stdout.write("=" * 50)
        self.stdout.write("المرحلة 2: ربط عناصر التصنيع")
        self.stdout.write("=" * 50)

        # البحث عن عناصر التقطيع التي ليس لها manufacturing_item
        unlinked_items = (
            CuttingOrderItem.objects.filter(manufacturing_items__isnull=True)
            .exclude(status="cancelled")
            .select_related(
                "cutting_order__order",
                "order_item__product",
            )
        )

        count = unlinked_items.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("جميع العناصر مرتبطة"))
            return

        self.stdout.write(f"وُجد {count} عنصر غير مرتبط")
        self.stdout.write("")

        linked_count = 0
        skipped_count = 0

        for ci in unlinked_items:
            order = ci.cutting_order.order
            product = (
                ci.order_item.product.name
                if ci.order_item and ci.order_item.product
                else "غير محدد"
            )

            self.stdout.write(f"  • {product[:40]}")
            self.stdout.write(f"    طلب: {order.order_number}")

            # التحقق من نوع الطلب (استبعاد المنتجات والمعاينات)
            order_types = order.get_selected_types_list()
            if "products" in order_types or "inspection" in order_types:
                self.stdout.write(
                    self.style.WARNING(f"    ⏭️ تخطي - نوع الطلب: {order_types}")
                )
                self.stdout.write("")
                skipped_count += 1
                continue

            # البحث عن أمر التصنيع (لا ننشئ جديد - نربط فقط بالموجود)
            try:
                mfg_order = ManufacturingOrder.objects.get(order=order)
            except ManufacturingOrder.DoesNotExist:
                # تخطي - لا يوجد أمر تصنيع
                self.stdout.write(
                    self.style.WARNING(f"    ⏭️ تخطي - لا يوجد أمر تصنيع للطلب")
                )
                self.stdout.write("")
                skipped_count += 1
                continue
            except ManufacturingOrder.MultipleObjectsReturned:
                mfg_order = ManufacturingOrder.objects.filter(order=order).first()

            # إنشاء manufacturing_item
            if mfg_order or dry_run:
                if not dry_run:
                    mfg_item = ManufacturingOrderItem.objects.create(
                        manufacturing_order=mfg_order,
                        cutting_item=ci,
                        order_item=ci.order_item,
                        product_name=product,
                        quantity=ci.order_item.quantity if ci.order_item else 1,
                        fabric_received=False,
                        delivered_to_production=False,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"    ✅ تم إنشاء عنصر تصنيع (ID: {mfg_item.id})"
                        )
                    )
                else:
                    self.stdout.write(self.style.WARNING("    [سيتم إنشاء عنصر تصنيع]"))

                linked_count += 1

            self.stdout.write("")

        self.stdout.write(f"إجمالي الربط: {linked_count} عنصر")
        self.stdout.write(f"تم تخطيهم: {skipped_count}")
        self.stdout.write("")
