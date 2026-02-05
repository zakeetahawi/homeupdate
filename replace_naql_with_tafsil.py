"""
سكريبت لاستبدال 'نقل 450' بـ 'تفصيل مجاني' في جميع الطلبات
"""

from orders.models import OrderItem
from inventory.models import Product
from django.db import transaction

print("="*80)
print("سكريبت استبدال 'نقل 450' بـ 'تفصيل مجاني'")
print("="*80)

# البحث عن المنتجين
naql_product = Product.objects.filter(name__icontains="نقل 450").first()
tafsil_product = Product.objects.filter(code="0008").first()

if not naql_product:
    print("❌ خطأ: لم يتم العثور على منتج 'نقل 450'")
    exit(1)

if not tafsil_product:
    print("❌ خطأ: لم يتم العثور على منتج 'تفصيل مجاني'")
    exit(1)

print(f"\n✅ المنتج القديم: {naql_product.name} (ID: {naql_product.id})")
print(f"✅ المنتج الجديد: {tafsil_product.name} (ID: {tafsil_product.id}, السعر: {tafsil_product.price})")

# البحث عن جميع عناصر الطلبات التي تحتوي على "نقل 450" بسعر 0
order_items = OrderItem.objects.filter(
    product=naql_product,
    unit_price=0
).select_related('order', 'order__customer')

print(f"\n📊 عدد العناصر المطابقة: {order_items.count()}")

if order_items.count() == 0:
    print("❌ لا توجد عناصر للاستبدال")
    exit(0)

# تجميع حسب الطلبات
orders_dict = {}
for item in order_items:
    order_id = item.order.id
    if order_id not in orders_dict:
        orders_dict[order_id] = {
            'order': item.order,
            'items': []
        }
    orders_dict[order_id]['items'].append(item)

print(f"📦 عدد الطلبات المتأثرة: {len(orders_dict)}")

# عرض أول 10 طلبات كمعاينة
print("\n" + "="*80)
print("معاينة أول 10 طلبات:")
print("="*80)

for i, (order_id, data) in enumerate(list(orders_dict.items())[:10], 1):
    order = data['order']
    items = data['items']
    customer_name = order.customer.name if order.customer else "بدون عميل"
    
    print(f"\n{i}. الطلب #{order.id} - {customer_name}")
    print(f"   التاريخ: {order.created_at.strftime('%Y-%m-%d')}")
    
    for item in items:
        print(f"   ❌ من: {item.product.name} × {item.quantity}")
        print(f"   ✅ إلى: {tafsil_product.name} × {item.quantity}")

if len(orders_dict) > 10:
    print(f"\n... وهناك {len(orders_dict) - 10} طلب آخر")

# طلب التأكيد
print("\n" + "="*80)
response = input(f"\n❓ هل تريد استبدال {order_items.count()} عنصر في {len(orders_dict)} طلب؟ (نعم/لا): ").strip().lower()

if response not in ['نعم', 'yes', 'y']:
    print("\n❌ تم إلغاء العملية")
    exit(0)

# تنفيذ الاستبدال
print("\n🔄 جاري تنفيذ الاستبدال...")
print("="*80)

try:
    with transaction.atomic():
        updated_count = 0
        
        for item in order_items:
            # حفظ معلومات العنصر القديم
            old_product_name = item.product.name
            order_number = item.order.id
            
            # تحديث المنتج
            item.product = tafsil_product
            item.unit_price = tafsil_product.price
            item.save()
            
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"   تم تحديث {updated_count} عنصر...")
        
        print(f"\n✅ تم تحديث {updated_count} عنصر بنجاح في {len(orders_dict)} طلب")
        print("="*80)
        
except Exception as e:
    print(f"\n❌ خطأ أثناء التحديث: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n✅ اكتملت العملية بنجاح!")
