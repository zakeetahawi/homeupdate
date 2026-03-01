"""
أمر إدارة: إصلاح المعاملات المخزنية المكررة
================================================
يبحث عن سجلات StockTransaction متكررة (نفس المنتج + المستودع + التاريخ)
ويحذف النسخ الزائدة، ثم يعيد حساب running_balance للمنتجات المتأثرة.

الاستخدام:
    python manage.py fix_duplicate_transactions
    python manage.py fix_duplicate_transactions --dry-run   (فحص فقط بدون تعديل)
    python manage.py fix_duplicate_transactions --fix        (إصلاح فعلي)
"""

import logging
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Min

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "إصلاح المعاملات المخزنية المكررة وإعادة حساب الأرصدة"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="فحص فقط بدون تعديل (الافتراضي)",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            default=False,
            help="تنفيذ الإصلاح الفعلي",
        )

    def handle(self, *args, **options):
        from inventory.models import StockTransaction

        dry_run = not options["fix"]

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 وضع الفحص فقط (--fix لتنفيذ الإصلاح)"))
        else:
            self.stdout.write(self.style.SUCCESS("🔧 وضع الإصلاح الفعلي"))

        # 1. البحث عن التكرارات
        duplicates = (
            StockTransaction.objects.values("product", "warehouse", "transaction_date")
            .annotate(count=Count("id"), min_id=Min("id"))
            .filter(count__gt=1)
        )

        total_duplicate_groups = duplicates.count()
        self.stdout.write(f"📊 مجموعات مكررة: {total_duplicate_groups}")

        if total_duplicate_groups == 0:
            self.stdout.write(self.style.SUCCESS("✅ لا توجد معاملات مكررة"))
            return

        # عرض التفاصيل
        total_to_delete = 0
        affected_products = set()
        affected_warehouses = set()

        for dup in duplicates:
            ids = list(
                StockTransaction.objects.filter(
                    product_id=dup["product"],
                    warehouse_id=dup["warehouse"],
                    transaction_date=dup["transaction_date"],
                )
                .order_by("id")
                .values_list("id", flat=True)
            )
            # احتفظ بأول ID (الأقدم) وسنحذف الباقي
            ids_to_delete = ids[1:]
            total_to_delete += len(ids_to_delete)
            affected_products.add(dup["product"])
            if dup["warehouse"]:
                affected_warehouses.add(dup["warehouse"])

            if not dry_run:
                self.stdout.write(
                    f"  حذف {len(ids_to_delete)} سجل مكرر "
                    f"(product={dup['product']}, warehouse={dup['warehouse']}, "
                    f"date={dup['transaction_date']})"
                )

        self.stdout.write(
            f"🗑️  إجمالي السجلات المكررة للحذف: {total_to_delete}"
        )
        self.stdout.write(
            f"📦 منتجات متأثرة: {len(affected_products)}"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("⚠️  تشغيل بـ --fix لتنفيذ الحذف وإعادة الحساب")
            )
            return

        # 2. تنفيذ الحذف
        deleted_count = 0
        with transaction.atomic():
            for dup in duplicates:
                ids = list(
                    StockTransaction.objects.filter(
                        product_id=dup["product"],
                        warehouse_id=dup["warehouse"],
                        transaction_date=dup["transaction_date"],
                    )
                    .order_by("id")
                    .values_list("id", flat=True)
                )
                ids_to_delete = ids[1:]  # احتفظ بالأول، احذف الباقي
                count, _ = StockTransaction.objects.filter(
                    id__in=ids_to_delete
                ).delete()
                deleted_count += count
            self.stdout.write(f"✅ تم حذف {deleted_count} سجل مكرر")

        # 3. إعادة حساب running_balance للمنتجات المتأثرة
        self.stdout.write("🔄 إعادة حساب الأرصدة للمنتجات المتأثرة...")
        recalc_count = 0
        errors = []

        from inventory.models import Warehouse

        for product_id in affected_products:
            for warehouse_id in (
                StockTransaction.objects.filter(product_id=product_id)
                .values_list("warehouse_id", flat=True)
                .distinct()
            ):
                try:
                    with transaction.atomic():
                        transactions = list(
                            StockTransaction.objects.filter(
                                product_id=product_id, warehouse_id=warehouse_id
                            )
                            .order_by("transaction_date", "id")
                            .select_for_update()
                        )

                        balance = Decimal("0")
                        for trans in transactions:
                            qty = Decimal(str(trans.quantity))
                            if trans.transaction_type == "in":
                                balance += qty
                            else:
                                balance -= qty
                            StockTransaction.objects.filter(id=trans.id).update(
                                running_balance=balance
                            )
                        recalc_count += 1
                except Exception as e:
                    errors.append(
                        f"product={product_id}, warehouse={warehouse_id}: {e}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ تم إعادة حساب الأرصدة لـ {recalc_count} مجموعة (منتج/مستودع)"
            )
        )

        if errors:
            self.stdout.write(self.style.ERROR(f"❌ أخطاء ({len(errors)}):"))
            for err in errors:
                self.stdout.write(f"  - {err}")

        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 اكتمل الإصلاح: حُذف {deleted_count} سجل، "
                f"أُعيد حساب {recalc_count} رصيد"
            )
        )
