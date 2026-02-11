"""
Management command لفحص الأرصدة الافتتاحية
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum
from accounting.models import Account, AccountType


class Command(BaseCommand):
    help = 'فحص الأرصدة الافتتاحية'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("🔍 فحص الأرصدة الافتتاحية")
        self.stdout.write("=" * 100)

        # إجمالي الأرصدة الافتتاحية
        total_opening = Account.objects.aggregate(
            total=Sum('opening_balance')
        )['total'] or Decimal('0.00')
        
        self.stdout.write(f"\nإجمالي الأرصدة الافتتاحية: {total_opening:,.2f}")

        # تحليل حسب نوع الحساب
        self.stdout.write("\n📊 الأرصدة الافتتاحية حسب نوع الحساب:")
        self.stdout.write("-" * 100)
        
        account_types = AccountType.objects.all()
        
        total_debit_opening = Decimal('0.00')
        total_credit_opening = Decimal('0.00')
        
        for acc_type in account_types:
            accounts = Account.objects.filter(account_type=acc_type)
            total = accounts.aggregate(total=Sum('opening_balance'))['total'] or Decimal('0.00')
            count = accounts.exclude(opening_balance=0).count()
            
            if count > 0:
                self.stdout.write(
                    f"{acc_type.name:<30}: {total:>15,.2f} ({count:>5} حساب) | "
                    f"طبيعة الرصيد: {acc_type.normal_balance}"
                )
                
                # حساب المدين والدائن حسب الطبيعة
                if acc_type.normal_balance == 'debit':
                    total_debit_opening += max(total, Decimal('0.00'))
                    total_credit_opening += abs(min(total, Decimal('0.00')))
                else:
                    total_credit_opening += max(total, Decimal('0.00'))
                    total_debit_opening += abs(min(total, Decimal('0.00')))

        self.stdout.write("-" * 100)
        self.stdout.write(f"{'إجمالي افتتاحي مدين':<30}: {total_debit_opening:>15,.2f}")
        self.stdout.write(f"{'إجمالي افتتاحي دائن':<30}: {total_credit_opening:>15,.2f}")
        self.stdout.write(f"{'الفرق':<30}: {abs(total_debit_opening - total_credit_opening):>15,.2f}")
        self.stdout.write("-" * 100)

        if total_debit_opening != total_credit_opening:
            self.stdout.write(
                self.style.ERROR(
                    f"\n❌ الأرصدة الافتتاحية غير متوازنة!"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ الأرصدة الافتتاحية متوازنة"
                )
            )

        # فحص إجمالي حركة المدين والدائن
        self.stdout.write("\n📊 إجمالي الحركة على الحسابات:")
        self.stdout.write("-" * 100)
        
        from accounting.models import TransactionLine
        
        total_all_debits = TransactionLine.objects.aggregate(
            total=Sum('debit')
        )['total'] or Decimal('0.00')
        
        total_all_credits = TransactionLine.objects.aggregate(
            total=Sum('credit')
        )['total'] or Decimal('0.00')
        
        self.stdout.write(f"{'إجمالي المدين في القيود':<30}: {total_all_debits:>15,.2f}")
        self.stdout.write(f"{'إجمالي الدائن في القيود':<30}: {total_all_credits:>15,.2f}")
        self.stdout.write(f"{'الفرق':<30}: {abs(total_all_debits - total_all_credits):>15,.2f}")
        self.stdout.write("-" * 100)

        if total_all_debits != total_all_credits:
            self.stdout.write(
                self.style.ERROR(
                    f"\n❌ القيود غير متوازنة!"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ القيود متوازنة"
                )
            )

        # الإجمالي النهائي
        self.stdout.write("\n📊 الإجمالي النهائي (افتتاحي + حركة):")
        self.stdout.write("-" * 100)
        
        final_debit = total_debit_opening + total_all_debits
        final_credit = total_credit_opening + total_all_credits
        
        self.stdout.write(f"{'إجمالي مدين نهائي':<30}: {final_debit:>15,.2f}")
        self.stdout.write(f"{'إجمالي دائن نهائي':<30}: {final_credit:>15,.2f}")
        self.stdout.write(f"{'الفرق':<30}: {abs(final_debit - final_credit):>15,.2f}")
        self.stdout.write("-" * 100)
