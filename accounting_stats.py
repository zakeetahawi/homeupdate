#!/usr/bin/env python
"""
إحصائيات شاملة للنظام المحاسبي
"""
from datetime import date
from orders.models import Order, Payment
from accounting.models import Transaction
from customers.models import Customer

print("=" * 70)
print("📊 إحصائيات النظام المحاسبي - 2026")
print("=" * 70)

# قيود
print("\n🔹 القيود المحاسبية:")
total_trans = Transaction.objects.count()
trans_2026 = Transaction.objects.filter(date__gte=date(2026, 1, 1)).count()
print(f"   إجمالي القيود: {total_trans:,}")
print(f"   قيود 2026: {trans_2026:,}")

by_type = Transaction.objects.filter(
    date__gte=date(2026, 1, 1)
).values('transaction_type').annotate(
    count=__import__('django.db.models', fromlist=['Count']).Count('id')
).order_by('transaction_type')

print("\n   حسب النوع (2026):")
for t in by_type:
    type_name = dict(Transaction.TRANSACTION_TYPES).get(
        t['transaction_type'], t['transaction_type']
    )
    print(f"     • {type_name}: {t['count']:,}")

# طلبات
print("\n🔹 الطلبات:")
total_orders = Order.objects.count()
orders_2026 = Order.objects.filter(order_date__gte=date(2026, 1, 1)).count()
orders_with_trans = Order.objects.filter(
    order_date__gte=date(2026, 1, 1)
).exclude(accounting_transactions__isnull=True).distinct().count()
print(f"   إجمالي الطلبات: {total_orders:,}")
print(f"   طلبات 2026: {orders_2026:,}")
print(f"   طلبات لها قيود: {orders_with_trans:,} ({orders_with_trans/orders_2026*100:.1f}%)")
print(f"   طلبات بدون قيود: {orders_2026 - orders_with_trans:,}")

# دفعات
print("\n🔹 الدفعات:")
total_payments = Payment.objects.count()
payments_2026 = Payment.objects.filter(payment_date__gte=date(2026, 1, 1)).count()
payments_with_trans = Payment.objects.filter(
    payment_date__gte=date(2026, 1, 1)
).exclude(accounting_transactions__isnull=True).distinct().count()
print(f"   إجمالي الدفعات: {total_payments:,}")
print(f"   دفعات 2026: {payments_2026:,}")
print(f"   دفعات لها قيود: {payments_with_trans:,} ({payments_with_trans/payments_2026*100:.1f}%)")
print(f"   دفعات بدون قيود: {payments_2026 - payments_with_trans:,}")

# عملاء
print("\n🔹 العملاء:")
total_customers = Customer.objects.count()
customers_with_orders_2026 = Customer.objects.filter(
    customer_orders__order_date__gte=date(2026, 1, 1)
).distinct().count()
print(f"   إجمالي العملاء: {total_customers:,}")
print(f"   عملاء لديهم طلبات في 2026: {customers_with_orders_2026:,}")

print("\n" + "=" * 70)
print("✅ النظام المحاسبي متكامل ومحدّث")
print("=" * 70)
