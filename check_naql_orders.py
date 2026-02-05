"""
فحص الطلبات التي تحتوي على 'نقل 450' بأي سعر
"""

from orders.models import OrderItem
from inventory.models import Product
from decimal import Decimal
from django.db import transaction

print("=" * 80)
print("البحث عن منتج 'نقل 450' وأسعاره في الطلبات")
print("=" * 80)

# البحث عن المنتج "نقل 450"
naql_product = Product.objects.filter(name__icontains="نقل 450").first()

if not naql_product:
    print("❌ لم يتم العثور على منتج 'نقل 450'")
else:
    print(f"\n✅ المنتج: {naql_product.name}")
    print(f"   - ID: {naql_product.id}")
    print(f"   - السعر الحالي: {naql_product.price} ج.م")
    print(f"   - الكود: {naql_product.code}")
    
    # البحث عن جميع عناصر الطلب لهذا المنتج
    all_items = OrderItem.objects.filter(
        product=naql_product
    ).select_related('order').order_by('order__order_number')
    
    print(f"\n📊 إحصائيات:")
    print(f"   - إجمالي العناصر: {all_items.count()}")
    
    # عرض الأسعار المختلفة
    from django.db.models import Count
    price_stats = all_items.values('unit_price').annotate(
        count=Count('id')
    ).order_by('unit_price')
    
    print("\n📈 توزيع الأسعار:")
    for stat in price_stats:
        print(f"   - {stat['unit_price']} ج.م: {stat['count']} عنصر")
    
    # البحث عن العناصر بسعر 25 جنيه
    items_25 = all_items.filter(unit_price=Decimal("25.00"))
    
    if items_25.exists():
        print(f"\n✅ تم العثور على {items_25.count()} عنصر بسعر 25 ج.م:")
        print("-" * 80)
        
        for idx, item in enumerate(items_25[:20], 1):  # عرض أول 20 فقط
            print(f"\n{idx}. رقم الطلب: {item.order.order_number}")
            print(f"   - ID العنصر: {item.id}")
            print(f"   - الكمية: {item.quantity}")
            print(f"   - السعر: {item.unit_price} ج.م")
            print(f"   - الإجمالي: {float(item.quantity) * float(item.unit_price)} ج.م")
            print(f"   - العميل: {item.order.customer}")
            print(f"   - تاريخ الطلب: {item.order.created_at.strftime('%Y-%m-%d')}")
        
        if items_25.count() > 20:
            print(f"\n... وهناك {items_25.count() - 20} عنصر آخر")
    else:
        print("\n❌ لا توجد عناصر بسعر 25 ج.م لهذا المنتج")

print("\n" + "=" * 80)
print("البحث عن منتج الاستبدال: تفصيل مجاني")
print("-" * 80)

replacement_products = Product.objects.filter(name__icontains="تفصيل مجاني")

if replacement_products.exists():
    replacement = replacement_products.first()
    print(f"✅ منتج الاستبدال:")
    print(f"   - الاسم: {replacement.name}")
    print(f"   - ID: {replacement.id}")
    print(f"   - السعر: {replacement.price} ج.م")
    print(f"   - الكود: {replacement.code}")
    
    if naql_product and items_25.exists():
        print("\n" + "=" * 80)
        print("هل تريد استبدال جميع العناصر؟")
        print(f"من: {naql_product.name} (سعر: 25 ج.م)")
        print(f"إلى: {replacement.name} (سعر: {replacement.price} ج.م)")
        print(f"عدد العناصر المتأثرة: {items_25.count()}")
        print("=" * 80)
        print("\nلتنفيذ الاستبدال، قم بتشغيل السكريبت التالي:")
        print("python manage.py shell < replace_naql_product.py")
else:
    print("❌ لم يتم العثور على منتج 'تفصيل مجاني'")

print("\n" + "=" * 80)
