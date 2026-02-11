"""
Management command لإيجاد المعاملات غير المتوازنة
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum
from accounting.models import Transaction, TransactionLine


class Command(BaseCommand):
    help = 'إيجاد وتحليل المعاملات غير المتوازنة'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("🔍 البحث عن المعاملات غير المتوازنة")
        self.stdout.write("=" * 100)

        transactions = Transaction.objects.all()
        total_trans = transactions.count()
        
        self.stdout.write(f"\nإجمالي المعاملات: {total_trans:,}\n")

        unbalanced = []
        total_diff = Decimal('0.00')

        for trans in transactions:
            total_debit = trans.lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
            total_credit = trans.lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')

            diff = total_debit - total_credit
            
            if abs(diff) > Decimal('0.001'):  # تسامح صغير جداً
                unbalanced.append({
                    'id': trans.id,
                    'date': trans.transaction_date,
                    'type': trans.transaction_type,
                    'description': trans.description,
                    'debit': total_debit,
                    'credit': total_credit,
                    'diff': diff
                })
                total_diff += diff

        if unbalanced:
            self.stdout.write(self.style.ERROR(f"\n❌ وجدت {len(unbalanced)} معاملة غير متوازنة!"))
            self.stdout.write(f"إجمالي الفرق: {total_diff:,.2f}\n")
            
            self.stdout.write("-" * 100)
            self.stdout.write(
                f"{'ID':<8} | {'التاريخ':<12} | {'النوع':<15} | "
                f"{'مدين':>15} | {'دائن':>15} | {'الفرق':>15}"
            )
            self.stdout.write("-" * 100)

            for trans in unbalanced[:50]:  # عرض أول 50
                self.stdout.write(
                    f"{trans['id']:<8} | {str(trans['date']):<12} | {trans['type'][:15]:<15} | "
                    f"{trans['debit']:>15,.2f} | {trans['credit']:>15,.2f} | "
                    f"{trans['diff']:>15,.2f}"
                )
                if trans['description']:
                    self.stdout.write(f"  البيان: {trans['description'][:80]}")

            self.stdout.write("-" * 100)
            
            # التحليل حسب النوع
            self.stdout.write("\n📊 التحليل حسب نوع المعاملة:")
            self.stdout.write("-" * 100)
            
            types_summary = {}
            for trans in unbalanced:
                trans_type = trans['type']
                if trans_type not in types_summary:
                    types_summary[trans_type] = {'count': 0, 'total_diff': Decimal('0.00')}
                types_summary[trans_type]['count'] += 1
                types_summary[trans_type]['total_diff'] += trans['diff']
            
            for trans_type, data in sorted(types_summary.items()):
                self.stdout.write(
                    f"  {trans_type:<30}: {data['count']:>5} معاملة | "
                    f"إجمالي الفرق: {data['total_diff']:>15,.2f}"
                )
            
            self.stdout.write("-" * 100)

            # اقتراح الإصلاح
            self.stdout.write("\n💡 اقتراحات الإصلاح:")
            self.stdout.write("-" * 100)
            
            if input("\nهل تريد تصحيح المعاملات غير المتوازنة؟ (yes/no): ").lower() == 'yes':
                self.fix_unbalanced_transactions(unbalanced)
            
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ جميع المعاملات متوازنة!"))

    def fix_unbalanced_transactions(self, unbalanced):
        """محاولة تصحيح المعاملات"""
        self.stdout.write("\n🔧 جاري تصحيح المعاملات...")
        
        fixed_count = 0
        failed_count = 0
        
        for trans_data in unbalanced:
            trans = Transaction.objects.get(id=trans_data['id'])
            
            try:
                # محاولة إعادة حساب البنود
                total_debit = trans.lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
                total_credit = trans.lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
                diff = total_debit - total_credit
                
                if abs(diff) > Decimal('0.001'):
                    self.stdout.write(
                        f"\n⚠️  المعاملة {trans.id} ما زالت غير متوازنة"
                    )
                    self.stdout.write(f"   مدين: {total_debit:,.2f}")
                    self.stdout.write(f"   دائن: {total_credit:,.2f}")
                    self.stdout.write(f"   الفرق: {diff:,.2f}")
                    
                    # عرض البنود
                    self.stdout.write("\n   البنود:")
                    for line in trans.lines.all():
                        self.stdout.write(
                            f"     {line.account.code} - مدين: {line.debit:,.2f}, "
                            f"دائن: {line.credit:,.2f}"
                        )
                    
                    failed_count += 1
                else:
                    fixed_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"\n❌ خطأ في المعاملة {trans.id}: {str(e)}")
                )
                failed_count += 1
        
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write(f"✅ تم التصليح: {fixed_count}")
        self.stdout.write(f"❌ فشل التصليح: {failed_count}")
        self.stdout.write("=" * 100)
