"""
Management command لإنشاء ميزان المراجعة
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum, Q
from accounting.models import Account, TransactionLine, AccountType
from datetime import datetime


class Command(BaseCommand):
    help = 'إنشاء ميزان المراجعة (Trial Balance)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--export',
            action='store_true',
            help='تصدير النتائج إلى ملف',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("📊 ميزان المراجعة (Trial Balance)")
        self.stdout.write("=" * 100)
        self.stdout.write(f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # جمع البيانات
        accounts_data = []
        total_debit = Decimal('0.00')
        total_credit = Decimal('0.00')
        total_balance_debit = Decimal('0.00')
        total_balance_credit = Decimal('0.00')

        # جلب جميع الحسابات مع الحركة
        accounts = Account.objects.filter(
            allow_transactions=True
        ).select_related('account_type').order_by('code')

        for account in accounts:
            # حساب إجمالي المدين والدائن
            aggregates = account.transaction_lines.aggregate(
                total_debit=Sum('debit'),
                total_credit=Sum('credit')
            )

            debit = aggregates['total_debit'] or Decimal('0.00')
            credit = aggregates['total_credit'] or Decimal('0.00')

            # تخطي الحسابات بدون حركة
            if debit == 0 and credit == 0 and account.opening_balance == 0:
                continue

            # حساب الرصيد
            balance = account.get_balance()

            # تحديد طبيعة الرصيد
            if balance > 0:
                if account.account_type.normal_balance == 'debit':
                    balance_debit = balance
                    balance_credit = Decimal('0.00')
                else:
                    balance_debit = Decimal('0.00')
                    balance_credit = balance
            elif balance < 0:
                if account.account_type.normal_balance == 'debit':
                    balance_debit = Decimal('0.00')
                    balance_credit = abs(balance)
                else:
                    balance_debit = abs(balance)
                    balance_credit = Decimal('0.00')
            else:
                balance_debit = Decimal('0.00')
                balance_credit = Decimal('0.00')

            accounts_data.append({
                'code': account.code,
                'name': account.name,
                'type': account.account_type.name,
                'debit': debit,
                'credit': credit,
                'balance_debit': balance_debit,
                'balance_credit': balance_credit,
                'balance': balance
            })

            total_debit += debit
            total_credit += credit
            total_balance_debit += balance_debit
            total_balance_credit += balance_credit

        # طباعة الجدول
        self.print_table(accounts_data, total_debit, total_credit, 
                        total_balance_debit, total_balance_credit)

        # تصدير إلى ملف إذا طُلب
        if options['export']:
            self.export_to_file(accounts_data, total_debit, total_credit,
                              total_balance_debit, total_balance_credit)

    def print_table(self, data, total_debit, total_credit, 
                   total_balance_debit, total_balance_credit):
        """طباعة جدول ميزان المراجعة"""

        # الترويسة
        header = (
            f"{'الكود':<12} | {'اسم الحساب':<40} | "
            f"{'مدين':>15} | {'دائن':>15} | "
            f"{'رصيد مدين':>15} | {'رصيد دائن':>15}"
        )
        
        self.stdout.write("-" * 130)
        self.stdout.write(header)
        self.stdout.write("-" * 130)

        # البيانات
        for item in data:
            row = (
                f"{item['code']:<12} | {item['name'][:40]:<40} | "
                f"{item['debit']:>15,.2f} | {item['credit']:>15,.2f} | "
                f"{item['balance_debit']:>15,.2f} | {item['balance_credit']:>15,.2f}"
            )
            self.stdout.write(row)

        # الإجماليات
        self.stdout.write("=" * 130)
        total_row = (
            f"{'الإجمالي':<12} | {'':<40} | "
            f"{total_debit:>15,.2f} | {total_credit:>15,.2f} | "
            f"{total_balance_debit:>15,.2f} | {total_balance_credit:>15,.2f}"
        )
        self.stdout.write(self.style.SUCCESS(total_row))
        self.stdout.write("=" * 130)

        # التحقق من التوازن
        self.stdout.write("\n📊 التحقق من التوازن:")
        self.stdout.write("-" * 130)
        
        if total_debit == total_credit:
            self.stdout.write(self.style.SUCCESS(
                f"✅ إجمالي المدين = إجمالي الدائن: {total_debit:,.2f}"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"❌ خطأ: إجمالي المدين ({total_debit:,.2f}) ≠ "
                f"إجمالي الدائن ({total_credit:,.2f})"
            ))

        if total_balance_debit == total_balance_credit:
            self.stdout.write(self.style.SUCCESS(
                f"✅ إجمالي الأرصدة المدينة = إجمالي الأرصدة الدائنة: {total_balance_debit:,.2f}"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"❌ خطأ: إجمالي الأرصدة المدينة ({total_balance_debit:,.2f}) ≠ "
                f"إجمالي الأرصدة الدائنة ({total_balance_credit:,.2f})"
            ))

        self.stdout.write(f"\n📈 الإحصائيات:")
        self.stdout.write(f"  عدد الحسابات النشطة: {len(data):,}")
        self.stdout.write(f"  إجمالي الحركة المدينة: {total_debit:,.2f}")
        self.stdout.write(f"  إجمالي الحركة الدائنة: {total_credit:,.2f}")

    def export_to_file(self, data, total_debit, total_credit,
                      total_balance_debit, total_balance_credit):
        """تصدير ميزان المراجعة إلى ملف"""
        filename = f"trial_balance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 130 + "\n")
            f.write("📊 ميزان المراجعة (Trial Balance)\n")
            f.write("=" * 130 + "\n")
            f.write(f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # الجدول
            f.write("-" * 130 + "\n")
            header = (
                f"{'الكود':<12} | {'اسم الحساب':<40} | "
                f"{'مدين':>15} | {'دائن':>15} | "
                f"{'رصيد مدين':>15} | {'رصيد دائن':>15}\n"
            )
            f.write(header)
            f.write("-" * 130 + "\n")

            for item in data:
                row = (
                    f"{item['code']:<12} | {item['name'][:40]:<40} | "
                    f"{item['debit']:>15,.2f} | {item['credit']:>15,.2f} | "
                    f"{item['balance_debit']:>15,.2f} | {item['balance_credit']:>15,.2f}\n"
                )
                f.write(row)

            # الإجماليات
            f.write("=" * 130 + "\n")
            total_row = (
                f"{'الإجمالي':<12} | {'':<40} | "
                f"{total_debit:>15,.2f} | {total_credit:>15,.2f} | "
                f"{total_balance_debit:>15,.2f} | {total_balance_credit:>15,.2f}\n"
            )
            f.write(total_row)
            f.write("=" * 130 + "\n")

        self.stdout.write(self.style.SUCCESS(f"\n✅ تم التصدير إلى: {filename}"))
