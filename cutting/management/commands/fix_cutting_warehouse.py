"""
أمر إدارة لإصلاح BUG-013: إعادة تعيين مستودع أوامر التقطيع من مستودع فارغ
إلى المستودع الذي يحتوي على أعلى رصيد للمنتج.
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "BUG-013: إعادة تعيين مستودع أوامر التقطيع التي تشير إلى مستودع بلا رصيد"

    def add_arguments(self, parser):
        parser.add_argument(
            "--warehouse-name",
            type=str,
            default="الادويه",
            help="اسم المستودع المراد تصحيحه (افتراضي: الادويه)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض التغييرات فقط دون تطبيقها",
        )
        parser.add_argument(
            "--statuses",
            nargs="*",
            default=["pending", "in_progress"],
            help="حالات أوامر التقطيع المراد تصحيحها (افتراضي: pending in_progress)",
        )

    def handle(self, *args, **options):
        from cutting.models import CuttingOrder
        from inventory.models import StockTransaction, Warehouse

        warehouse_name = options["warehouse_name"]
        dry_run = options["dry_run"]
        statuses = options["statuses"]

        self.stdout.write(
            self.style.WARNING(
                f"{'[DRY RUN] ' if dry_run else ''}تصحيح أوامر التقطيع التي تشير إلى: {warehouse_name}"
            )
        )

        # 1. إيجاد المستودع المشكل
        try:
            problem_warehouse = Warehouse.objects.get(name=warehouse_name)
        except Warehouse.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"المستودع '{warehouse_name}' غير موجود"))
            return
        except Warehouse.MultipleObjectsReturned:
            problem_warehouse = Warehouse.objects.filter(name=warehouse_name).first()
            self.stdout.write(
                self.style.WARNING(f"تم العثور على أكثر من مستودع باسم '{warehouse_name}'، سيتم استخدام id={problem_warehouse.id}")
            )

        # 2. إيجاد أوامر التقطيع التي تشير إلى هذا المستودع
        cutting_orders = CuttingOrder.objects.filter(
            warehouse=problem_warehouse,
            status__in=statuses,
            is_deleted=False,
        ).prefetch_related("items")

        total_orders = cutting_orders.count()
        self.stdout.write(f"عدد أوامر التقطيع المتأثرة: {total_orders}")

        if total_orders == 0:
            self.stdout.write(self.style.SUCCESS("✅ لا يوجد شيء لتصحيحه!"))
            return

        fixed_count = 0
        skipped_count = 0

        for cutting_order in cutting_orders:
            # جمع جميع المنتجات في هذا الأمر
            products = []
            for item in cutting_order.items.filter(is_deleted=False):
                if item.order_item and item.order_item.product:
                    products.append(item.order_item.product)

            if not products:
                self.stdout.write(
                    self.style.WARNING(
                        f"  أمر #{cutting_order.id}: لا توجد منتجات محددة — تخطي"
                    )
                )
                skipped_count += 1
                continue

            # إيجاد أفضل مستودع لأول منتج في الأمر
            best_warehouse = None
            for product in products:
                best_trans = (
                    StockTransaction.objects.filter(
                        product=product,
                        warehouse__is_active=True,
                        running_balance__gt=0,
                    )
                    .exclude(warehouse=problem_warehouse)
                    .select_related("warehouse")
                    .order_by("-running_balance", "-transaction_date")
                    .first()
                )
                if best_trans:
                    best_warehouse = best_trans.warehouse
                    break

            if not best_warehouse:
                # احتياطي: أول مستودع نشط غير مستودع المشكلة
                best_warehouse = (
                    Warehouse.objects.filter(is_active=True)
                    .exclude(id=problem_warehouse.id)
                    .first()
                )

            if not best_warehouse:
                self.stdout.write(
                    self.style.ERROR(
                        f"  أمر #{cutting_order.id}: لم يتم العثور على بديل — تخطي"
                    )
                )
                skipped_count += 1
                continue

            product_names = ", ".join([p.name for p in products[:3]])
            self.stdout.write(
                f"  أمر #{cutting_order.id} | منتجات: {product_names} | "
                f"{problem_warehouse.name} → {best_warehouse.name}"
            )

            if not dry_run:
                with transaction.atomic():
                    cutting_order.warehouse = best_warehouse
                    cutting_order.save(update_fields=["warehouse"])
                fixed_count += 1
            else:
                fixed_count += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY RUN] سيتم تصحيح {fixed_count} أمر، تخطي {skipped_count} أمر."
                    f"\nشغّل الأمر بدون --dry-run لتطبيق التغييرات."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ تم تصحيح {fixed_count} أمر، تخطي {skipped_count} أمر."
                )
            )
