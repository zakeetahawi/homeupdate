"""
سكريبت تنظيف أوامر التقطيع الخاطئة للأقمشة الخارجية

هذا السكريبت يحذف جميع عناصر التقطيع التي تم وضع علامة "خارجي" عليها بالخطأ
ثم يعيد معالجة الأقمشة الخارجية الفعلية فقط

الاستخدام:
python manage.py shell < cleanup_external_fabrics.py
"""

from cutting.models import CuttingOrder, CuttingOrderItem
from cutting.signals import process_external_fabrics
from orders.models import Order

# 1. حذف جميع عناصر التقطيع الخارجية الموجودة
external_items = CuttingOrderItem.objects.filter(is_external=True)
count = external_items.count()
print(f"🔍 تم العثور على {count} عنصر تقطيع خارجي")

if count > 0:
    external_items.delete()
    print(f"✅ تم حذف {count} عنصر تقطيع خارجي")

# 2. حذف أوامر التقطيع الفارغة
empty_orders = CuttingOrder.objects.filter(items__isnull=True)
empty_count = empty_orders.count()
if empty_count > 0:
    empty_orders.delete()
    print(f"✅ تم حذف {empty_count} أمر تقطيع فارغ")

# 3. إعادة معالجة الأقمشة الخارجية لجميع الطلبات
orders = Order.objects.all()
processed = 0

for order in orders:
    try:
        process_external_fabrics(order)
        processed += 1
    except Exception as e:
        print(f"❌ خطأ في معالجة الطلب {order.order_number}: {e}")

print(f"✅ تمت إعادة معالجة {processed} طلب")
print("✅ اكتمل التنظيف!")
