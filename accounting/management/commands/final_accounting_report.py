"""
تقرير شامل نهائي للنظام المحاسبي
يفحص جميع جوانب النظام ويقدم تقريراً تفصيلياً
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, Q, F
from decimal import Decimal
from accounting.models import Account, Transaction, TransactionLine
from orders.models import Order
from customers.models import Customer


class Command(BaseCommand):
    help = "تقرير شامل نهائي للنظام المحاسبي"

    def handle(self, *args, **options):
        """التنفيذ الرئيسي"""

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(" التقرير النهائي الشامل للنظام المحاسبي "))
        self.stdout.write("=" * 80)

        # القسم الأول: القيد المزدوج
        self.check_double_entry()

        # القسم الثاني: الحسابات
        self.check_accounts()

        # القسم الثالث: المعاملات
        self.check_transactions()

        # القسم الرابع: طلبات 2026
        self.check_orders_2026()

        # القسم الخامس: ميزان المراجعة
        self.trial_balance()

        # الخاتمة
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ اكتمل التقرير الشامل!"))
        self.stdout.write("=" * 80)

    def check_double_entry(self):
        """فحص القيد المزدوج"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("1️⃣  فحص القيد المزدوج"))
        self.stdout.write("=" * 80)

        transactions = Transaction.objects.all()
        total = transactions.count()
        balanced = 0
        unbalanced = 0
        unbalanced_trans = []

        for trans in transactions:
            total_debit = (
                trans.lines.aggregate(total=Sum("debit"))["total"] or Decimal("0")
            )
            total_credit = (
                trans.lines.aggregate(total=Sum("credit"))["total"] or Decimal("0")
            )

            if total_debit == total_credit:
                balanced += 1
            else:
                unbalanced += 1
                unbalanced_trans.append((trans.id, total_debit, total_credit))

        self.stdout.write(f"إجمالي المعاملات: {total:,}")
        self.stdout.write(
            self.style.SUCCESS(f"  ✅ معاملات متوازنة: {balanced:,} ({balanced*100/total:.1f}%)")
        )

        if unbalanced > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"  ❌ معاملات غير متوازنة: {unbalanced:,} ({unbalanced*100/total:.1f}%)"
                )
            )
            for trans_id, debit, credit in unbalanced_trans[:5]:
                self.stdout.write(f"     المعاملة #{trans_id}: مدين={debit} / دائن={credit}")
        else:
            self.stdout.write(self.style.SUCCESS("  ✅ جميع المعاملات متوازنة!"))

    def check_accounts(self):
        """فحص الحسابات"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("2️⃣  فحص الحسابات"))
        self.stdout.write("=" * 80)

        # إحصائيات الحسابات
        accounts = Account.objects.all()
        total = accounts.count()

        by_type = accounts.values("account_type__category", "account_type__name").annotate(count=Count("id"))

        self.stdout.write(f"إجمالي الحسابات: {total:,}\n")

        for item in by_type:
            type_name = item["account_type__name"] or "غير محدد"
            self.stdout.write(f"  • {type_name}: {item['count']:,}")

        # فحص حسابات العملاء
        customers = Customer.objects.all()
        customers_with_account = customers.exclude(accounting_account__isnull=True).count()
        customers_without_account = customers.filter(accounting_account__isnull=True).count()

        self.stdout.write(f"\nحسابات العملاء:")
        self.stdout.write(f"  • إجمالي العملاء: {customers.count():,}")
        self.stdout.write(
            self.style.SUCCESS(f"  ✅ لهم حساب: {customers_with_account:,}")
        )
        if customers_without_account > 0:
            self.stdout.write(
                self.style.ERROR(f"  ❌ بدون حساب: {customers_without_account:,}")
            )

    def check_transactions(self):
        """فحص المعاملات"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("3️⃣  فحص المعاملات"))
        self.stdout.write("=" * 80)

        # أنواع المعاملات
        trans_types = (
            Transaction.objects.values("transaction_type")
            .annotate(count=Count("id"), total=Sum("lines__debit"))
            .order_by("-count")
        )

        self.stdout.write("أنواع المعاملات:\n")

        type_names = {
            "invoice": "فواتير البيع",
            "payment": "الدفعات",
            "journal": "قيود يومية",
            "opening": "أرصدة افتتاحية",
        }

        for item in trans_types:
            type_name = type_names.get(item["transaction_type"], item["transaction_type"])
            total = item["total"] or Decimal("0")
            self.stdout.write(f"  • {type_name}: {item['count']:,} معاملة")
            self.stdout.write(f"    الإجمالي: {total:,.2f} ج.م")

    def check_orders_2026(self):
        """فحص طلبات 2026"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("4️⃣  فحص طلبات 2026"))
        self.stdout.write("=" * 80)

        orders_2026 = Order.objects.filter(order_date__year=2026)
        total = orders_2026.count()

        # الطلبات بحسب القيود
        with_invoice = orders_2026.filter(
            accounting_transactions__transaction_type="invoice"
        ).distinct().count()

        with_payment = orders_2026.filter(
            accounting_transactions__transaction_type="payment"
        ).distinct().count()

        without_trans = orders_2026.filter(accounting_transactions__isnull=True).count()

        # الإحصائيات المالية
        total_value = (
            orders_2026.aggregate(total=Sum("final_price"))["total"] or Decimal("0")
        )
        total_paid = (
            orders_2026.aggregate(total=Sum("paid_amount"))["total"] or Decimal("0")
        )
        remaining = total_value - total_paid

        self.stdout.write(f"إجمالي الطلبات: {total:,}\n")
        self.stdout.write(f"القيود المحاسبية:")
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✅ قيود الفواتير: {with_invoice:,} ({with_invoice*100/total:.1f}%)"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✅ قيود الدفعات: {with_payment:,} ({with_payment*100/total:.1f}%)"
            )
        )

        if without_trans > 0:
            # فحص إذا كانت قيمتها = 0
            zero_value_orders = orders_2026.filter(
                accounting_transactions__isnull=True, final_price=0
            ).count()

            if zero_value_orders == without_trans:
                self.stdout.write(
                    f"  ⚠️  بدون قيود: {without_trans:,} (جميعها قيمتها = 0.00)"
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ❌ بدون قيود: {without_trans:,} ({(without_trans*100/total):.1f}%)"
                    )
                )

        self.stdout.write(f"\nالإحصائيات المالية:")
        self.stdout.write(f"  • إجمالي القيمة:  {total_value:,.2f} ج.م")
        self.stdout.write(f"  • المدفوع:         {total_paid:,.2f} ج.م")
        self.stdout.write(f"  • المتبقي:         {remaining:,.2f} ج.م")
        self.stdout.write(
            f"  • نسبة التحصيل:   {(total_paid*100/total_value):.1f}%"
        )

    def trial_balance(self):
        """ميزان المراجعة"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("5️⃣  ميزان المراجعة"))
        self.stdout.write("=" * 80)

        accounts = Account.objects.all()
        total_debit = Decimal("0")
        total_credit = Decimal("0")

        for account in accounts:
            # حساب المدين
            debit = (
                account.transaction_lines.aggregate(total=Sum("debit"))["total"]
                or Decimal("0")
            )

            # حساب الدائن
            credit = (
                account.transaction_lines.aggregate(total=Sum("credit"))["total"]
                or Decimal("0")
            )

            total_debit += debit
            total_credit += credit

        self.stdout.write(f"إجمالي المدين:  {total_debit:,.2f} ج.م")
        self.stdout.write(f"إجمالي الدائن:  {total_credit:,.2f} ج.م")
        self.stdout.write(f"الفرق:           {abs(total_debit - total_credit):,.2f} ج.م")

        if total_debit == total_credit:
            self.stdout.write(
                self.style.SUCCESS("\n✅ ميزان المراجعة متوازن تماماً!")
            )
        else:
            diff_percent = abs(total_debit - total_credit) * 100 / total_debit
            if diff_percent < 0.01:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n⚠️  فرق بسيط في ميزان المراجعة ({diff_percent:.4f}%)"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"\n❌ ميزان المراجعة غير متوازن ({diff_percent:.2f}%)"
                    )
                )
