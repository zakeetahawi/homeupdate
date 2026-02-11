"""
أمر لإنشاء القيود المحاسبية للطلبات والدفعات الموجودة
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounting.signals import create_order_transaction, create_payment_transaction


class Command(BaseCommand):
    help = "إنشاء القيود المحاسبية للطلبات والدفعات الموجودة"

    def add_arguments(self, parser):
        parser.add_argument(
            "--orders-only",
            action="store_true",
            help="إنشاء قيود الطلبات فقط",
        )
        parser.add_argument(
            "--payments-only",
            action="store_true",
            help="إنشاء قيود الدفعات فقط",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="عدد محدد من السجلات",
        )
        parser.add_argument(
            "--from-date",
            type=str,
            help="تاريخ البداية (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--to-date",
            type=str,
            help="تاريخ النهاية (YYYY-MM-DD)",
        )

    def handle(self, *args, **options):
        from accounting.models import AccountingSettings, Transaction
        from orders.models import Order, Payment

        # التحقق من وجود الإعدادات
        settings = AccountingSettings.objects.first()
        if not settings:
            self.stdout.write(
                self.style.ERROR(
                    "❌ الإعدادات المحاسبية غير موجودة! شغّل: python manage.py setup_accounting_defaults"
                )
            )
            return

        orders_only = options.get("orders_only")
        payments_only = options.get("payments_only")
        limit = options.get("limit")
        from_date = options.get("from_date")
        to_date = options.get("to_date")

        # إنشاء قيود الطلبات
        if not payments_only:
            self.stdout.write(
                self.style.SUCCESS("\n🔄 إنشاء قيود الطلبات...")
            )

            # الطلبات التي ليس لها قيود
            orders = Order.objects.filter(
                accounting_transactions__isnull=True
            ).select_related("customer")
            
            # تطبيق فلاتر التاريخ
            if from_date:
                orders = orders.filter(order_date__gte=from_date)
                self.stdout.write(f"  فلترة من تاريخ: {from_date}")
            if to_date:
                orders = orders.filter(order_date__lte=to_date)
                self.stdout.write(f"  فلترة إلى تاريخ: {to_date}")

            if limit:
                orders = orders[:limit]

            total = orders.count()
            self.stdout.write(f"  وجدنا {total} طلب بدون قيود\n")

            created = 0
            errors = 0

            for i, order in enumerate(orders, 1):
                try:
                    with transaction.atomic():
                        txn = create_order_transaction(order)
                        if txn:
                            created += 1
                            if i % 100 == 0:
                                self.stdout.write(
                                    f"  ✓ تم معالجة {i}/{total}..."
                                )
                        else:
                            errors += 1
                except Exception as e:
                    errors += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ❌ خطأ في طلب {order.order_number}: {str(e)}"
                        )
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ الطلبات: تم إنشاء {created} قيد، {errors} خطأ"
                )
            )

        # إنشاء قيود الدفعات
        if not orders_only:
            self.stdout.write(
                self.style.SUCCESS("\n🔄 إنشاء قيود الدفعات...")
            )

            # الدفعات التي ليس لها قيود
            payments = Payment.objects.filter(
                accounting_transactions__isnull=True
            ).select_related("order", "order__customer")
            
            # تطبيق فلاتر التاريخ
            if from_date:
                payments = payments.filter(payment_date__gte=from_date)
            if to_date:
                payments = payments.filter(payment_date__lte=to_date)

            if limit:
                payments = payments[:limit]

            total = payments.count()
            self.stdout.write(f"  وجدنا {total} دفعة بدون قيود\n")

            created = 0
            errors = 0

            for i, payment in enumerate(payments, 1):
                try:
                    with transaction.atomic():
                        txn = create_payment_transaction(payment)
                        if txn:
                            created += 1
                            if i % 100 == 0:
                                self.stdout.write(
                                    f"  ✓ تم معالجة {i}/{total}..."
                                )
                        else:
                            errors += 1
                except Exception as e:
                    errors += 1
                    self.stdout.write(
                        self.style.ERROR(f"  ❌ خطأ في دفعة {payment.id}: {str(e)}")
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ الدفعات: تم إنشاء {created} قيد، {errors} خطأ"
                )
            )

        # الإجماليات النهائية
        total_transactions = Transaction.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ اكتمل! إجمالي القيود في النظام: {total_transactions}"
            )
        )
