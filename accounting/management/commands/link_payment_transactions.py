"""
أمر لربط قيود الدفعات الموجودة مع سجلات Payment المقابلة
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import timedelta

from accounting.models import Transaction
from orders.models import Payment


class Command(BaseCommand):
    help = "ربط قيود الدفعات الموجودة مع سجلات Payment المقابلة"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="فقط عرض ما سيتم ربطه بدون تنفيذ",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run")

        # الحصول على قيود الدفعات التي ليس لها payment مرتبطة
        payment_transactions = Transaction.objects.filter(
            transaction_type="payment", payment__isnull=True
        ).select_related("order", "customer")

        total = payment_transactions.count()
        self.stdout.write(f"\n📊 وجدنا {total} قيد دفعة بدون رابط Payment\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️ وضع الاختبار (لن يتم التعديل)\n"))

        linked = 0
        not_found = 0
        multiple_found = 0

        for i, txn in enumerate(payment_transactions, 1):
            # محاولة إيجاد Payment المقابل بناءً على:
            # 1. الطلب
            # 2. التاريخ (تقريبي ±3 أيام)
            # 3. المبلغ (من السطور)

            if not txn.order:
                not_found += 1
                if i % 100 == 0:
                    self.stdout.write(f"  ⏳ تم معالجة {i}/{total}...")
                continue

            # حساب مبلغ القيد من السطور
            debit_total = sum(line.debit for line in txn.lines.all())
            credit_total = sum(line.credit for line in txn.lines.all())
            amount = max(debit_total, credit_total)

            # البحث عن Payment مطابقة
            payments = Payment.objects.filter(
                order=txn.order,
                amount=amount,
                payment_date__gte=txn.date - timedelta(days=3),
                payment_date__lte=txn.date + timedelta(days=3),
            )

            count = payments.count()

            if count == 0:
                not_found += 1
                self.stdout.write(
                    f"  ⚠️  لم نجد Payment للقيد #{txn.transaction_number} (الطلب: {txn.order.order_number}, المبلغ: {amount})"
                )
            elif count == 1:
                payment = payments.first()
                if not dry_run:
                    with transaction.atomic():
                        txn.payment = payment
                        txn.save(update_fields=["payment"])
                linked += 1
            else:
                # عدة نتائج - نأخذ الأقرب في التاريخ
                payment = min(
                    payments, key=lambda p: abs((p.payment_date.date() - txn.date).days)
                )
                if not dry_run:
                    with transaction.atomic():
                        txn.payment = payment
                        txn.save(update_fields=["payment"])
                multiple_found += 1
                linked += 1
                self.stdout.write(
                    f"  ⚠️  وجدنا {count} دفعات للقيد #{txn.transaction_number}، اخترنا الأقرب"
                )

            if i % 100 == 0:
                self.stdout.write(f"  ⏳ تم معالجة {i}/{total}...")

        # النتائج
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"\n✅ تم الانتهاء!"))
        self.stdout.write(f"  📝 إجمالي القيود المعالجة: {total}")
        self.stdout.write(f"  ✅ تم الربط: {linked}")
        self.stdout.write(f"  ⚠️  لم نجد Payment: {not_found}")
        self.stdout.write(f"  🔄 خيارات متعددة: {multiple_found}\n")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️ هذا كان اختباراً فقط. شغّل بدون --dry-run للتنفيذ الفعلي.\n"
                )
            )
