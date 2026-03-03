"""
أمر إدارة: إصلاح الأرصدة السالبة في المخزون
================================================
يبحث عن المنتجات ذات الرصيد السالب في مستودع معين ويصحّح الرصيد
بإنشاء معاملة تسوية (adjustment/inventory_check) برصيد يعيده إلى الصفر.

الاستخدام:
    python manage.py fix_negative_stock
    python manage.py fix_negative_stock --warehouse-id 24   (مستودع الادويه)
    python manage.py fix_negative_stock --dry-run            (فحص فقط بدون تعديل)
    python manage.py fix_negative_stock --fix                (إصلاح فعلي)
    python manage.py fix_negative_stock --all-warehouses     (جميع المستودعات)
"""

import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = "إصلاح الأرصدة السالبة في المخزون بإنشاء معاملات تسوية"

    def add_arguments(self, parser):
        parser.add_argument(
            "--warehouse-id",
            type=int,
            default=None,
            help="معرّف المستودع (الافتراضي: جميع المستودعات)",
        )
        parser.add_argument(
            "--all-warehouses",
            action="store_true",
            default=False,
            help="فحص وإصلاح جميع المستودعات",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="فحص فقط بدون تعديل",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            default=False,
            help="تنفيذ الإصلاح الفعلي",
        )

    def handle(self, *args, **options):
        from inventory.models import (
            InventoryAdjustment,
            Product,
            StockTransaction,
            Warehouse,
        )

        dry_run = not options["fix"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 وضع الفحص فقط — استخدم --fix لتنفيذ الإصلاح")
            )
        else:
            self.stdout.write(self.style.SUCCESS("🔧 وضع الإصلاح الفعلي"))

        # تحديد المستودعات المستهدفة
        if options["warehouse_id"]:
            warehouses = Warehouse.objects.filter(id=options["warehouse_id"], is_active=True)
            if not warehouses.exists():
                self.stdout.write(
                    self.style.ERROR(f"❌ لم يُوجد مستودع بمعرّف {options['warehouse_id']}")
                )
                return
        elif options["all_warehouses"]:
            warehouses = Warehouse.objects.filter(is_active=True)
        else:
            # الافتراضي: مستودع الادويه
            warehouses = Warehouse.objects.filter(name__icontains="دوي", is_active=True)
            if not warehouses.exists():
                self.stdout.write(
                    self.style.WARNING(
                        "⚠️ لم يُوجد مستودع 'الادويه'، استخدم --warehouse-id أو --all-warehouses"
                    )
                )
                return

        # الحصول على مستخدم النظام للمعاملات
        system_user = User.objects.filter(is_superuser=True).first()

        total_fixed = 0
        total_warehouses_affected = 0

        for warehouse in warehouses:
            self.stdout.write(f"\n📦 فحص مستودع: {warehouse.name} (ID: {warehouse.id})")

            # إيجاد آخر رصيد لكل منتج في هذا المستودع
            latest_balance_subq = (
                StockTransaction.objects.filter(
                    warehouse=warehouse,
                    product=OuterRef("pk"),
                )
                .order_by("-transaction_date", "-id")
                .values("running_balance")[:1]
            )

            products_with_neg = (
                Product.objects.annotate(last_balance=Subquery(latest_balance_subq))
                .filter(last_balance__lt=0)
                .order_by("last_balance")
            )

            count = products_with_neg.count()
            if count == 0:
                self.stdout.write(self.style.SUCCESS("  ✅ لا توجد أرصدة سالبة"))
                continue

            total_warehouses_affected += 1
            self.stdout.write(
                self.style.WARNING(f"  ⚠️ عدد المنتجات برصيد سالب: {count}")
            )

            # طباعة التفاصيل
            self.stdout.write(
                f"\n  {'المنتج':<35} {'الكود':<20} {'الرصيد':>12} {'التسوية':>12}"
            )
            self.stdout.write("  " + "-" * 82)

            for product in products_with_neg:
                neg_balance = Decimal(str(product.last_balance))
                correction = abs(neg_balance)

                self.stdout.write(
                    f"  {str(product.name)[:34]:<35} "
                    f"{str(product.code)[:19]:<20} "
                    f"{neg_balance:>12.3f} "
                    f"{correction:>+12.3f}"
                )

                if not dry_run:
                    try:
                        with transaction.atomic():
                            # إنشاء معاملة تسوية لرفع الرصيد إلى الصفر
                            StockTransaction.objects.create(
                                product=product,
                                warehouse=warehouse,
                                transaction_type="adjustment",
                                reason="inventory_check",
                                quantity=correction,
                                reference=f"AUTO-FIX-{timezone.now().strftime('%Y%m%d')}",
                                transaction_date=timezone.now(),
                                notes=(
                                    f"تسوية تلقائية: تصحيح رصيد سالب "
                                    f"({neg_balance} → 0) "
                                    f"- أمر fix_negative_stock"
                                ),
                                running_balance=Decimal("0"),
                                created_by=system_user,
                            )

                            # سجل InventoryAdjustment للمراجعة
                            InventoryAdjustment.objects.create(
                                product=product,
                                warehouse=warehouse,
                                adjustment_type="increase",
                                quantity_before=neg_balance,
                                quantity_after=Decimal("0"),
                                reason=(
                                    f"تصحيح تلقائي: رصيد سالب ({neg_balance})"
                                    f" — أمر fix_negative_stock {timezone.now().strftime('%Y-%m-%d')}"
                                ),
                                created_by=system_user,
                            )

                            total_fixed += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"    ❌ خطأ في {product.name}: {e}")
                        )

        # ملخص النتائج
        self.stdout.write("\n" + "=" * 85)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"📋 ملخص الفحص: {total_warehouses_affected} مستودع متأثر\n"
                    f"    استخدم --fix لتنفيذ الإصلاح الفعلي"
                )
            )
        else:
            if total_fixed > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ تم إصلاح {total_fixed} منتج عبر {total_warehouses_affected} مستودع"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING("⚠️ لم يُنفَّذ أي إصلاح")
                )
