"""
سكريبت تنفيذ استبدال 'نقل 450' بـ 'تفصيل مجاني' في جميع الطلبات
"""

from orders.models import OrderItem
from inventory.models import Product
from django.db import transaction

print("="*80)
print("استبدال 'نقل 450' بـ 'تفصيل مجاني'")
print("="*80)

# البحث عن المنتجين
naql_product = Product.objects.filter(name__icontains="نقل 450").first()
tafsil_product = Product.objects.filter(code="0008").first()

if not naql_product or not tafsil_product:
    print("❌ خطأ في العثور على المنتجات")
    exit(1)

print(f"\n✅ من: {naql_product.name} (ID: {naql_product.id})")
print(f"✅ إلى: {tafsil_product.name} (ID: {tafsil_product.id}, السعر: {tafsil_product.price})")

# البحث عن العناصر
order_items = OrderItem.objects.filter(
    product=naql_product,
    unit_price=0
).select_related('order')

print(f"\n📊 عدد العناصر: {order_items.count()}")

if order_items.count() == 0:
    print("❌ لا توجد عناصر للاستبدال")
    exit(0)

# تنفيذ الاستبدال
print("\n🔄 جاري التنفيذ...")
print("="*80)

try:
    with transaction.atomic():
        updated_count = 0
        
        for item in order_items:
            item.product = tafsil_product
            item.unit_price = tafsil_product.price
            item.save()
            
            updated_count += 1
            
            if updated_count % 100 == 0:
                print(f"   تم تحديث {updated_count} عنصر...")
        
        print(f"\n✅ نجح تحديث {updated_count} عنصر")
        print("="*80)
        
except Exception as e:
    print(f"\n❌ خطأ: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n✅ اكتملت العملية!")
