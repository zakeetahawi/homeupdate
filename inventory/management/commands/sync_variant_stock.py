"""
أمر إدارة: مزامنة VariantStock من StockTransaction
====================================================
ينقل أرصدة المخزون من النظام القديم (StockTransaction.running_balance)
إلى النظام الجديد (VariantStock.current_quantity).

يستخدم آخر running_balance لكل منتج+مستودع كرصيد حالي.
آمن للتشغيل المتكرر — يستخدم update_or_create فلا يُنشئ تكرارات.

الاستخدام:
    python manage.py sync_variant_stock                  # معاينة فقط (dry-run)
    python manage.py sync_variant_stock --apply          # تنفيذ فعلي
    python manage.py sync_variant_stock --warehouse-id 5 # مستودع محدد
"""

import logging
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Max, Subquery, OuterRef
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "مزامنة VariantStock من running_balance في StockTransaction"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="تنفيذ المزامنة فعلياً (بدونه = معاينة فقط)",
        )
        parser.add_argument(
            "--warehouse-id",
            type=int,
            default=None,
            help="مزامنة مستودع محدد فقط",
        )

    def handle(self, *args, **options):
        from inventory.models import (
            Product,
            StockTransaction,
            VariantStock,
            Warehouse,
        )

        apply = options["apply"]
        warehouse_id = options["warehouse_id"]

        if not apply:
            self.stdout.write(
                self.style.WARNING("⚠️  وضع المعاينة — لن يتم تعديل أي بيانات. أضف --apply للتنفيذ.")
            )

        # --- الخطوة 1: جلب آخر transaction لكل منتج+مستودع ---
        txn_filter = {}
        if warehouse_id:
            txn_filter["warehouse_id"] = warehouse_id

        # Subquery: آخر id لكل (product, warehouse)
        latest_txn_ids = (
            StockTransaction.objects.filter(**txn_filter)
            .values("product_id", "warehouse_id")
            .annotate(last_id=Max("id"))
            .values_list("last_id", flat=True)
        )

        latest_txns = StockTransaction.objects.filter(
            id__in=latest_txn_ids
        ).select_related("product__variant_link", "warehouse")

        total = latest_txns.count()
        self.stdout.write(f"📊 إجمالي أزواج (منتج+مستودع): {total}")

        # --- فلتر: فقط المنتجات المرتبطة بمتغير ---
        linked_txns = [
            t for t in latest_txns
            if getattr(t.product, "variant_link", None) is not None
        ]
        self.stdout.write(f"🔗 منها مرتبطة بمتغير (variant_link): {len(linked_txns)}")

        # --- الخطوة 2: المقارنة مع VariantStock الحالي ---
        created_count = 0
        updated_count = 0
        unchanged_count = 0
        skipped_count = 0

        warehouses_summary = {}

        for txn in linked_txns:
            variant = txn.product.variant_link
            warehouse = txn.warehouse
            if not warehouse:
                skipped_count += 1
                continue
            new_qty = max(Decimal(str(txn.running_balance)), Decimal("0"))

            wh_name = warehouse.name
            if wh_name not in warehouses_summary:
                warehouses_summary[wh_name] = {"created": 0, "updated": 0, "unchanged": 0}

            # تحقق من الوضع الحالي
            existing = VariantStock.objects.filter(
                variant=variant, warehouse=warehouse
            ).first()

            if existing:
                if existing.current_quantity == new_qty:
                    unchanged_count += 1
                    warehouses_summary[wh_name]["unchanged"] += 1
                    continue
                else:
                    updated_count += 1
                    warehouses_summary[wh_name]["updated"] += 1
                    if apply:
                        existing.current_quantity = new_qty
                        existing.last_updated = timezone.now()
                        existing.save(update_fields=["current_quantity", "last_updated"])
            else:
                created_count += 1
                warehouses_summary[wh_name]["created"] += 1
                if apply:
                    VariantStock.objects.create(
                        variant=variant,
                        warehouse=warehouse,
                        current_quantity=new_qty,
                    )

        # --- الخطوة 3: التقرير ---
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📋 تقرير المزامنة:")
        self.stdout.write("=" * 60)

        for wh_name, stats in sorted(warehouses_summary.items()):
            self.stdout.write(
                f"  {wh_name}: "
                f"جديد={stats['created']}, "
                f"محدّث={stats['updated']}, "
                f"بدون تغيير={stats['unchanged']}"
            )

        self.stdout.write("-" * 60)
        self.stdout.write(f"  ✅ جديد (سيتم إنشاؤه): {created_count}")
        self.stdout.write(f"  🔄 محدّث (سيتم تعديل كميته): {updated_count}")
        self.stdout.write(f"  ⏩ بدون تغيير: {unchanged_count}")
        if skipped_count:
            self.stdout.write(f"  ⏭️  تم تخطيه (بدون مستودع): {skipped_count}")

        if apply:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ تم التنفيذ: {created_count} جديد + {updated_count} محدّث"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  معاينة فقط. أضف --apply للتنفيذ الفعلي."
                )
            )
