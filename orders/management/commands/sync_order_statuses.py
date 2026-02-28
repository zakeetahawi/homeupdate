import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F, Q

from manufacturing.models import ManufacturingOrder
from orders.models import Order


class Command(BaseCommand):
    help = (
        "مزامنة حالات الطلبات مع حالات التصنيع (مُحسَّنة: تطبع تقدم وتحدّث فقط الاختلافات)"
    )

    def handle(self, *args, **options):
        """مزامنة حالات الطلبات مع حالات التصنيع بشكل مُحسَّن"""

        self.stdout.write(self.style.SUCCESS("بدء مزامنة حالات الطلبات..."))

        updated_count = 0

        # تحديث فقط أوامر التصنيع التي تختلف عن حالة الطلب
        mismatch_qs = ManufacturingOrder.objects.filter(
            ~Q(status=F("order__order_status"))
        ).select_related("order")
        total_mismatch = mismatch_qs.count()
        self.stdout.write(f"عدد أوامر التصنيع التي تحتاج تحديث: {total_mismatch}")

        # تحسين: تحديث الأوامر المعلقة في دفعات باستخدام bulk_update
        chunk = 1000
        # اجلب قائمة tuples (order_id, new_status)
        mismatch_pairs = list(mismatch_qs.values_list("order_id", "status"))
        total_pairs = len(mismatch_pairs)
        self.stdout.write(
            f"المعالَجة (دفعات): {total_pairs} أوامر تصنيع مختلفة عن حالة الطلب"
        )

        updated_from_mfg = 0
        for start in range(0, total_pairs, chunk):
            batch_pairs = mismatch_pairs[start : start + chunk]
            order_ids = [p[0] for p in batch_pairs]
            # جلب كائنات الطلب دفعة واحدة
            orders = list(Order.objects.filter(pk__in=order_ids))
            order_map = {o.pk: o for o in orders}

            # تعيين الحقول محلياً
            changed = []
            for oid, new_status in batch_pairs:
                o = order_map.get(oid)
                if not o:
                    continue
                # فقط إذا اختلفت الحالة فعلاً
                if o.order_status != new_status:
                    o.order_status = new_status
                    changed.append(o)

            if not changed:
                self.stdout.write(
                    f"دفعة {min(start+chunk, total_pairs)}/{total_pairs}: لا تغييرات"
                )
                continue

            with transaction.atomic():
                Order.objects.bulk_update(changed, ["order_status"])

            updated_from_mfg += len(changed)
            self.stdout.write(
                f"دفعة {min(start+chunk, total_pairs)}/{total_pairs}: محدثة {updated_from_mfg} إجمالاً"
            )

        updated_count += updated_from_mfg

        # ----- مزامنة الطلبات بناءً على حالة التركيبات (إذا وُجدت) -----
        try:
            from installations.models import InstallationSchedule
        except Exception:
            InstallationSchedule = None

        if InstallationSchedule:
            inst_order_ids_qs = (
                InstallationSchedule.objects.filter(status="completed")
                .values_list("order_id", flat=True)
                .distinct()
            )
            inst_order_ids = list(inst_order_ids_qs)
            total_inst_orders = len(inst_order_ids)
            self.stdout.write(f"عدد الطلبات ذات تركيب مكتمل: {total_inst_orders}")

            updated_by_install = 0
            chunk = 1000
            for start in range(0, total_inst_orders, chunk):
                batch_ids = inst_order_ids[start : start + chunk]
                with transaction.atomic():
                    qs = Order.objects.filter(pk__in=batch_ids).exclude(
                        order_status="completed"
                    )
                    # bulk update via QuerySet.update to avoid per-row save
                    updated = qs.update(order_status="completed")
                    updated_by_install += updated
                    self.stdout.write(
                        f"معالجة التركيبات: {min(start + chunk, total_inst_orders)}/{total_inst_orders} (محدثة حتى الآن {updated_by_install})"
                    )

            updated_count += updated_by_install

        # الآن معالجة الطلبات التي لا تحتوي على أوامر تصنيع (مُحسَّنة)
        start_time = time.time()
        # 1) إكمال الطلبات التي لها معاينة مكتملة وناجحة
        try:
            insp_completed_qs = Order.objects.filter(
                manufacturing_order__isnull=True,
                inspections__status="completed",
                inspections__result="passed",
            ).distinct()
            to_complete_qs = insp_completed_qs.exclude(order_status="completed")
            completed_count = to_complete_qs.update(order_status="completed")
            updated_count += completed_count
            self.stdout.write(
                f"تم تحديث حالات المعاينات المكتملة إلى مكتمل: {completed_count}"
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطأ عند تحديث حالات المعاينات: {e}"))

        # 2) باقي الطلبات بدون تصنيع: اجعل حالتها 'pending' إذا لم تكن مكتملة
        try:
            remaining_qs = Order.objects.filter(
                manufacturing_order__isnull=True
            ).exclude(order_status="completed")
            # قد نريد استثناء الطلبات التي للتصنيع أو أنواع أخرى، لكن هذا يحاكي السلوك الأصلي
            pending_updated = (
                remaining_qs.exclude(
                    inspections__status="completed", inspections__result="passed"
                )
                .distinct()
                .update(order_status="pending")
            )
            updated_count += pending_updated
            self.stdout.write(
                f"تم تحديث حالات الطلبات بدون تصنيع إلى pending: {pending_updated}"
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"خطأ عند تحديث حالات الطلبات بدون تصنيع: {e}")
            )

        elapsed = time.time() - start_time
        self.stdout.write(f"انتهت معالجة الطلبات بدون تصنيع في {elapsed:.2f}s")

        self.stdout.write(
            self.style.SUCCESS(
                f"تم الانتهاء من المزامنة. إجمالي الطلبات المحدثة: {updated_count}"
            )
        )
