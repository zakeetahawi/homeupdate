#!/usr/bin/env python
"""
فحص قيود الدفعات
"""
from datetime import date
from orders.models import Payment
from accounting.models import Transaction

# اختبار payment واحد
p = Payment.objects.filter(payment_date__gte=date(2026, 1, 1)).first()
if p:
    print(f'✅ Payment ID: {p.id}')
    print(f'   Amount: {p.amount}')
    print(f'   Date: {p.payment_date}')
    
    # البحث عن transactions مرتبطة
    transactions = Transaction.objects.filter(payment=p)
    print(f'   Transactions via filter: {transactions.count()}')
    
    # عبر related_name
    print(f'   Transactions via related: {p.accounting_transactions.count()}')
    
    # عرض التفاصيل
    for txn in p.accounting_transactions.all():
        print(f'     - Transaction #{txn.transaction_number}: {txn.description}')
else:
    print('❌ No payments found from 2026')

# إحصائيات عامة
print('\n📊 إحصائيات:')
total_payments_2026 = Payment.objects.filter(payment_date__gte=date(2026, 1, 1)).count()
payments_with_trans = Payment.objects.filter(
    payment_date__gte=date(2026, 1, 1)
).exclude(accounting_transactions__isnull=True).distinct().count()

print(f'   إجمالي دفعات 2026: {total_payments_2026}')
print(f'   دفعات لها قيود: {payments_with_trans}')
print(f'   دفعات بدون قيود: {total_payments_2026 - payments_with_trans}')

# عدد قيود الدفعات
payment_trans = Transaction.objects.filter(
    transaction_type='payment',
    date__gte=date(2026, 1, 1)
).count()
print(f'   قيود دفعات (نوع payment): {payment_trans}')
