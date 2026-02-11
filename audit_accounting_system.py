#!/usr/bin/env python
"""
فحص شامل للنظام المحاسبي
Comprehensive Accounting System Audit
"""

from decimal import Decimal
from datetime import datetime
from django.db.models import Sum, Count, Q, F
from accounting.models import Account, Transaction, TransactionLine, AccountType
from orders.models import Payment, PaymentAllocation


class AccountingAuditor:
    """مدقق النظام المحاسبي"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = {}
        
    def log_error(self, message):
        self.errors.append(message)
        print(f"❌ خطأ: {message}")
        
    def log_warning(self, message):  
        self.warnings.append(message)
        print(f"⚠️  تحذير: {message}")
        
    def log_info(self, message):
        print(f"ℹ️  {message}")
    
    def log_success(self, message):
        print(f"✅ {message}")
        
    def check_double_entry(self):
        """التحقق من صحة القيد المزدوج"""
        print("\n" + "="*60)
        print("1️⃣  فحص القيد المزدوج (Double Entry)")
        print("="*60)
        
        transactions = Transaction.objects.all()
        total_trans = transactions.count()
        self.log_info(f"إجمالي المعاملات: {total_trans}")
        
        unbalanced = []
        
        for trans in transactions:
            total_debit = trans.lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')
            total_credit = trans.lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')
            
            if total_debit != total_credit:
                diff = total_debit - total_credit
                unbalanced.append({
                    'id': trans.id,
                    'date': trans.transaction_date,
                    'description': trans.description,
                    'debit': total_debit,
                    'credit': total_credit,
                    'diff': diff
                })
                
        if unbalanced:
            self.log_error(f"وجدت {len(unbalanced)} معاملة غير متوازنة!")
            print("\nالمعاملات غير المتوازنة:")
            print("-" * 100)
            for trans in unbalanced[:10]:  # عرض أول 10
                print(f"  ID: {trans['id']} | التاريخ: {trans['date']} | "
                      f"مدين: {trans['debit']:,.2f} | دائن: {trans['credit']:,.2f} | "
                      f"الفرق: {trans['diff']:,.2f}")
                print(f"  البيان: {trans['description'][:80]}")
                print("-" * 100)
        else:
            self.log_success("جميع المعاملات متوازنة (مدين = دائن) ✓")
            
        self.stats['total_transactions'] = total_trans
        self.stats['unbalanced_transactions'] = len(unbalanced)
        
        return unbalanced
        
    def check_account_balances(self):
        """فحص أرصدة الحسابات"""
        print("\n" + "="*60)
        print("2️⃣  فحص أرصدة الحسابات")
        print("="*60)
        
        accounts = Account.objects.all()
        total_accounts = accounts.count()
        self.log_info(f"إجمالي الحسابات: {total_accounts}")
        
        incorrect_balances = []
        
        for account in accounts:
            calculated_balance = account.get_balance()
            current_balance = account.current_balance
            
            if calculated_balance != current_balance:
                incorrect_balances.append({
                    'code': account.code,
                    'name': account.name,
                    'current': current_balance,
                    'calculated': calculated_balance,
                    'diff': calculated_balance - current_balance
                })
                
        if incorrect_balances:
            self.log_error(f"وجدت {len(incorrect_balances)} حساب برصيد خاطئ!")
            print("\nالحسابات ذات الأرصدة الخاطئة:")
            print("-" * 120)
            for acc in incorrect_balances[:20]:  # عرض أول 20
                print(f"  {acc['code']} - {acc['name'][:50]}")
                print(f"    الرصيد المسجل: {acc['current']:>15,.2f}")
                print(f"    الرصيد المحسوب: {acc['calculated']:>15,.2f}")
                print(f"    الفرق: {acc['diff']:>15,.2f}")
                print("-" * 120)
        else:
            self.log_success("جميع أرصدة الحسابات صحيحة ✓")
            
        self.stats['total_accounts'] = total_accounts
        self.stats['incorrect_balances'] = len(incorrect_balances)
        
        return incorrect_balances
        
    def check_transaction_lines(self):
        """فحص بنود القيود"""
        print("\n" + "="*60)
        print("3️⃣  فحص بنود القيود")
        print("="*60)
        
        # فحص البنود التي لها مدين ودائن معاً
        dual_lines = TransactionLine.objects.filter(
            debit__gt=0, 
            credit__gt=0
        )
        
        if dual_lines.exists():
            self.log_error(f"وجدت {dual_lines.count()} بنود لها مدين ودائن معاً!")
            for line in dual_lines[:5]:
                print(f"  المعاملة {line.transaction.id}: "
                      f"{line.account.code} - مدين: {line.debit}, دائن: {line.credit}")
        else:
            self.log_success("لا توجد بنود لها مدين ودائن معاً ✓")
            
        # فحص البنود الفارغة
        empty_lines = TransactionLine.objects.filter(
            debit=0,
            credit=0
        )
        
        if empty_lines.exists():
            self.log_warning(f"وجدت {empty_lines.count()} بنود فارغة (مدين=0 ودائن=0)")
        else:
            self.log_success("لا توجد بنود فارغة ✓")
            
        self.stats['dual_entry_lines'] = dual_lines.count()
        self.stats['empty_lines'] = empty_lines.count()
        
        return {
            'dual_lines': list(dual_lines[:10]),
            'empty_lines': list(empty_lines[:10])
        }
        
    def check_payment_allocations(self):
        """فحص تخصيص الدفعات"""
        print("\n" + "="*60)
        print("4️⃣  فحص تخصيص الدفعات")
        print("="*60)
        
        payments = Payment.objects.all()
        total_payments = payments.count()
        self.log_info(f"إجمالي الدفعات: {total_payments}")
        
        over_allocated = []
        
        for payment in payments:
            allocated = payment.allocated_amount or Decimal('0.00')
            if allocated > payment.amount:
                over_allocated.append({
                    'id': payment.id,
                    'amount': payment.amount,
                    'allocated': allocated,
                    'diff': allocated - payment.amount
                })
                
        if over_allocated:
            self.log_error(f"وجدت {len(over_allocated)} دفعة مخصصة أكثر من قيمتها!")
            for pay in over_allocated[:10]:
                print(f"  الدفعة {pay['id']}: "
                      f"المبلغ: {pay['amount']:,.2f}, "
                      f"المخصص: {pay['allocated']:,.2f}, "
                      f"الزيادة: {pay['diff']:,.2f}")
        else:
            self.log_success("جميع الدفعات مخصصة بشكل صحيح ✓")
            
        # فحص التخصيصات
        allocations = PaymentAllocation.objects.all()
        self.log_info(f"إجمالي التخصيصات: {allocations.count()}")
        
        self.stats['total_payments'] = total_payments
        self.stats['over_allocated_payments'] = len(over_allocated)
        self.stats['total_allocations'] = allocations.count()
        
        return over_allocated
        
    def check_customer_accounts(self):
        """فحص حسابات العملاء"""
        print("\n" + "="*60)
        print("5️⃣  فحص حسابات العملاء")
        print("="*60)
        
        customer_accounts = Account.objects.filter(is_customer_account=True)
        total = customer_accounts.count()
        self.log_info(f"إجمالي حسابات العملاء: {total}")
        
        # حسابات عملاء بدون customer_id
        orphan_accounts = customer_accounts.filter(customer__isnull=True)
        if orphan_accounts.exists():
            self.log_warning(f"وجدت {orphan_accounts.count()} حساب عميل بدون ربط بعميل!")
        else:
            self.log_success("جميع حسابات العملاء مربوطة بعملاء ✓")
            
        # عملاء بدون حسابات
        from customers.models import Customer
        customers_without_account = Customer.objects.filter(
            accounting_account__isnull=True
        )
        if customers_without_account.exists():
            self.log_warning(f"وجدت {customers_without_account.count()} عميل بدون حساب محاسبي!")
        else:
            self.log_success("جميع العملاء لديهم حسابات محاسبية ✓")
            
        self.stats['customer_accounts'] = total
        self.stats['orphan_accounts'] = orphan_accounts.count()
        self.stats['customers_without_account'] = customers_without_account.count()
        
    def check_account_types(self):
        """فحص أنواع الحسابات"""
        print("\n" + "="*60)
        print("6️⃣  فحص أنواع الحسابات")
        print("="*60)
        
        account_types = AccountType.objects.all()
        self.log_info(f"إجمالي أنواع الحسابات: {account_types.count()}")
        
        for acc_type in account_types:
            count = acc_type.accounts.count()
            print(f"  {acc_type.code_prefix} - {acc_type.name}: {count} حساب")
            
    def generate_summary(self):
        """ملخص نتائج الفحص"""
        print("\n" + "="*60)
        print("📊 ملخص نتائج الفحص")
        print("="*60)
        
        print(f"\n📈 الإحصائيات:")
        for key, value in self.stats.items():
            print(f"  {key}: {value:,}")
            
        print(f"\n❌ الأخطاء: {len(self.errors)}")
        if self.errors:
            for error in self.errors:
                print(f"  • {error}")
                
        print(f"\n⚠️  التحذيرات: {len(self.warnings)}")
        if self.warnings:
            for warning in self.warnings:
                print(f"  • {warning}")
                
        if not self.errors and not self.warnings:
            print("\n🎉 النظام المحاسبي سليم تماماً!")
        elif self.errors:
            print(f"\n⚠️  يوجد {len(self.errors)} خطأ يحتاج إصلاح!")
            
    def run_full_audit(self):
        """تشغيل الفحص الكامل"""
        print("\n" + "="*60)
        print("🔍 فحص شامل للنظام المحاسبي")
        print("="*60)
        print(f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.check_double_entry()
        self.check_account_balances()
        self.check_transaction_lines()
        self.check_payment_allocations()
        self.check_customer_accounts()
        self.check_account_types()
        self.generate_summary()
        
        return {
            'errors': self.errors,
            'warnings': self.warnings,
            'stats': self.stats
        }


if __name__ == '__main__':
    auditor = AccountingAuditor()
    results = auditor.run_full_audit()
    
    # حفظ النتائج
    print(f"\n{'='*60}")
    print("الفحص اكتمل!")
    print(f"{'='*60}")
