#!/usr/bin/env python
"""
فحص الطلبات التي بدون قيود
"""
from datetime import date
from orders.models import Order

# الطلبات بدون قيود
orders_without_trans = Order.objects.filter(
    order_date__gte=date(2026, 1, 1),
    accounting_transactions__isnull=True
).select_related('customer')

print(f"🔍 فحص {orders_without_trans.count()} طلب بدون قيود:\n")

for order in orders_without_trans:
    print(f"📦 الطلب: {order.order_number}")
    print(f"   العميل: {order.customer.name if order.customer else 'بدون عميل'}")
    print(f"   التاريخ: {order.order_date}")
    print(f"   الحالة: {order.get_status_display()}")
    print(f"   الإجمالي: {order.final_price}")
    print(f"   المدفوع: {order.paid_amount}")
    print(f"   المتبقي: {order.remaining_amount}")
    
    # فحص السبب المحتمل
    if not order.customer:
        print(f"   ⚠️  السبب: لا يوجد عميل")
    elif order.final_price == 0:
        print(f"   ⚠️  السبب: المبلغ صفر")
    elif order.status == 'draft':
        print(f"   ⚠️  السبب: مسودة")
    else:
        print(f"   ❓ السبب غير واضح")
    
    print()
