"""
أمر إدارة لتنظيف سجلات الطلبات المكررة والوهمية

يقوم بـ:
1. حذف سجلات الأسعار الوهمية (phantom) حيث القيمة القديمة = الجديدة
2. حذف السجلات المكررة (نفس الطلب + نفس النوع + نفس الحقل + خلال 5 ثوانٍ)
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db.models import Count, Min
from django.utils import timezone

from orders.models import OrderModificationLog, OrderStatusLog


class Command(BaseCommand):
    help = "تنظيف سجلات الطلبات المكررة والوهمية"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض ما سيتم حذفه دون تنفيذ الحذف فعلياً",
        )
        parser.add_argument(
            "--order-id",
            type=int,
            help="تنظيف طلب محدد فقط",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        order_id = options.get("order_id")

        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(self.style.NOTICE("تنظيف سجلات الطلبات المكررة والوهمية"))
        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  وضع المعاينة — لن يتم حذف أي شيء"))
        self.stdout.write(self.style.NOTICE("=" * 60))

        total_deleted = 0

        # === 1. حذف سجلات الأسعار الوهمية ===
        self.stdout.write("\n📋 1. البحث عن سجلات أسعار وهمية...")
        qs = OrderStatusLog.objects.filter(change_type="price")
        if order_id:
            qs = qs.filter(order_id=order_id)

        phantom_ids = []
        for log in qs.iterator():
            cd = log.change_details or {}
            old_p = cd.get("old_price", 0)
            new_p = cd.get("new_price", 0)
            try:
                old_dec = Decimal(str(old_p)).quantize(Decimal("0.01"))
                new_dec = Decimal(str(new_p)).quantize(Decimal("0.01"))
                if old_dec == new_dec:
                    phantom_ids.append(log.id)
            except (InvalidOperation, TypeError, ValueError):
                continue

        self.stdout.write(f"   وُجد {len(phantom_ids)} سجل سعر وهمي")
        if phantom_ids and not dry_run:
            deleted = OrderStatusLog.objects.filter(id__in=phantom_ids).delete()[0]
            total_deleted += deleted
            self.stdout.write(self.style.SUCCESS(f"   ✅ تم حذف {deleted} سجل"))

        # === 2. حذف سجلات StatusLog المكررة ===
        self.stdout.write("\n📋 2. البحث عن سجلات StatusLog مكررة...")
        dup_status_ids = self._find_duplicate_status_logs(order_id)
        self.stdout.write(f"   وُجد {len(dup_status_ids)} سجل مكرر")
        if dup_status_ids and not dry_run:
            deleted = OrderStatusLog.objects.filter(id__in=dup_status_ids).delete()[0]
            total_deleted += deleted
            self.stdout.write(self.style.SUCCESS(f"   ✅ تم حذف {deleted} سجل"))

        # === 3. حذف سجلات ModificationLog المكررة ===
        self.stdout.write("\n📋 3. البحث عن سجلات ModificationLog مكررة...")
        dup_mod_ids = self._find_duplicate_modification_logs(order_id)
        self.stdout.write(f"   وُجد {len(dup_mod_ids)} سجل مكرر")
        if dup_mod_ids and not dry_run:
            deleted = OrderModificationLog.objects.filter(id__in=dup_mod_ids).delete()[0]
            total_deleted += deleted
            self.stdout.write(self.style.SUCCESS(f"   ✅ تم حذف {deleted} سجل"))

        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"سيتم حذف إجمالي: {len(phantom_ids) + len(dup_status_ids) + len(dup_mod_ids)} سجل"
                )
            )
            self.stdout.write(self.style.WARNING("أعد التشغيل بدون --dry-run للتنفيذ"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ تم حذف إجمالي: {total_deleted} سجل"))

    def _find_duplicate_status_logs(self, order_id=None):
        """البحث عن سجلات StatusLog مكررة (نفس الطلب + النوع + نافذة 5 ثوانٍ)"""
        qs = OrderStatusLog.objects.all()
        if order_id:
            qs = qs.filter(order_id=order_id)

        # Group by order + change_type and check for near-time duplicates
        duplicate_ids = []
        orders_with_logs = qs.values("order_id").annotate(
            log_count=Count("id")
        ).filter(log_count__gt=1)

        for entry in orders_with_logs:
            oid = entry["order_id"]
            logs = list(
                qs.filter(order_id=oid)
                .order_by("created_at")
                .values("id", "change_type", "created_at", "change_details")
            )

            seen = {}  # (change_type, field_name) -> (id, created_at)
            for log in logs:
                ct = log["change_type"]
                cd = log["change_details"] or {}
                fn = cd.get("field_name", "")
                key = (ct, fn)
                lid = log["id"]
                ts = log["created_at"]

                if key in seen:
                    prev_id, prev_ts = seen[key]
                    # If within 5 seconds of the previous one, this is a duplicate
                    if ts and prev_ts and abs((ts - prev_ts).total_seconds()) <= 5:
                        duplicate_ids.append(lid)
                        continue  # Keep seen pointing to the first one

                seen[key] = (lid, ts)

        return duplicate_ids

    def _find_duplicate_modification_logs(self, order_id=None):
        """البحث عن سجلات ModificationLog مكررة"""
        qs = OrderModificationLog.objects.all()
        if order_id:
            qs = qs.filter(order_id=order_id)

        duplicate_ids = []
        orders_with_logs = qs.values("order_id").annotate(
            log_count=Count("id")
        ).filter(log_count__gt=1)

        for entry in orders_with_logs:
            oid = entry["order_id"]
            logs = list(
                qs.filter(order_id=oid)
                .order_by("modified_at")
                .values("id", "modification_type", "modified_at", "modified_fields")
            )

            seen = {}  # modification_type -> (id, modified_at)
            for log in logs:
                mt = log["modification_type"]
                lid = log["id"]
                ts = log["modified_at"]

                if mt in seen:
                    prev_id, prev_ts = seen[mt]
                    if ts and prev_ts and abs((ts - prev_ts).total_seconds()) <= 5:
                        duplicate_ids.append(lid)
                        continue

                seen[mt] = (lid, ts)

        return duplicate_ids
