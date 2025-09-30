#!/usr/bin/env python
"""
اختبار بسيط لحذف الطلب
"""
import os
import sys
import django

# إضافة المسار الحالي
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from django.db import transaction, connection

print("=" * 60)
print("اختبار حذف الطلب")
print("=" * 60)

# البحث عن طلب للاختبار
test_order = Order.objects.filter(order_number__startswith='1-0001').first()

if not test_order:
    print("❌ لا يوجد طلب للاختبار")
    sys.exit(1)

print(f"\n✅ تم العثور على الطلب: {test_order.order_number}")
print(f"   - العميل: {test_order.customer}")
print(f"   - عدد العناصر: {test_order.items.count()}")
print(f"   - عدد السجلات: {test_order.status_logs.count()}")

order_id = test_order.pk
order_number = test_order.order_number

print(f"\n🗑️  محاولة حذف الطلب...")

try:
    with transaction.atomic():
        # حذف سجلات الحالة أولاً باستخدام raw SQL
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM orders_orderstatuslog WHERE order_id = %s', [order_id])
            deleted_logs = cursor.rowcount
            print(f"   ✓ تم حذف {deleted_logs} سجل حالة")
        
        # حذف الطلب
        test_order.delete()
        print(f"   ✓ تم حذف الطلب من قاعدة البيانات")
    
    print(f"\n🎉 نجح الحذف! تم حذف الطلب {order_number} بنجاح!")
    
    # التحقق
    if not Order.objects.filter(pk=order_id).exists():
        print(f"✅ تم التأكد: الطلب لم يعد موجوداً في قاعدة البيانات")
    else:
        print(f"⚠️  تحذير: الطلب لا يزال موجوداً!")
        
except Exception as e:
    print(f"\n❌ فشل الحذف!")
    print(f"   الخطأ: {e}")
    print(f"   النوع: {type(e).__name__}")
    
    import traceback
    print("\n" + "=" * 60)
    print("تفاصيل الخطأ:")
    print("=" * 60)
    traceback.print_exc()

print("\n" + "=" * 60)

