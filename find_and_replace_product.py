#!/usr/bin/env python
"""
سكريبت للبحث عن الطلبات التي تحتوي على منتج "نقل 450" بسعر 25 جنيه
واستبداله بمنتج "تفصيل مجاني"
"""

import os
import sys
import django

# إعداد Django
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "homeupdate.settings")
django.setup()

from django.db import transaction
from orders.models import OrderItem
from inventory.models import Product
from decimal import Decimal


def find_orders_with_product():
    """البحث عن الطلبات التي تحتوي على 'نقل 450' بسعر 25 جنيه"""
    
    print("=" * 80)
    print("البحث عن الطلبات التي تحتوي على: نقل 450 - بسعر 25 جنيه")
    print("=" * 80)
    
    # البحث عن المنتج "نقل 450" بسعر 25
    order_items = OrderItem.objects.filter(
        product__name__icontains="نقل 450",
        unit_price=Decimal("25.00")
    ).select_related('order', 'product').order_by('order__order_number')
    
    if not order_items.exists():
        print("\n❌ لم يتم العثور على أي طلبات بهذه المواصفات")
        return []
    
    print(f"\n✅ تم العثور على {order_items.count()} عنصر في الطلبات:")
    print("-" * 80)
    
    # عرض تفاصيل الطلبات
    orders_data = []
    for idx, item in enumerate(order_items, 1):
        print(f"\n{idx}. رقم الطلب: {item.order.order_number}")
        print(f"   - اسم المنتج: {item.product.name}")
        print(f"   - الكمية: {item.quantity}")
        print(f"   - السعر: {item.unit_price} ج.م")
        print(f"   - الإجمالي: {item.quantity * item.unit_price} ج.م")
        print(f"   - العميل: {item.order.customer}")
        print(f"   - تاريخ الطلب: {item.order.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"   - حالة الطلب: {item.order.get_order_status_display()}")
        
        orders_data.append({
            'item_id': item.id,
            'order_number': item.order.order_number,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'order_id': item.order.id
        })
    
    print("\n" + "=" * 80)
    return orders_data


def find_replacement_product():
    """البحث عن منتج 'تفصيل مجاني'"""
    
    print("\nالبحث عن منتج الاستبدال: تفصيل مجاني")
    print("-" * 80)
    
    # البحث عن المنتج البديل
    replacement_products = Product.objects.filter(
        name__icontains="تفصيل مجاني"
    )
    
    if not replacement_products.exists():
        print("❌ لم يتم العثور على منتج 'تفصيل مجاني'")
        print("\nقائمة المنتجات المتاحة التي تحتوي على 'تفصيل':")
        similar = Product.objects.filter(name__icontains="تفصيل")[:10]
        for p in similar:
            print(f"  - {p.name} (السعر: {p.price} ج.م)")
        return None
    
    if replacement_products.count() > 1:
        print(f"⚠️  تم العثور على {replacement_products.count()} منتجات:")
        for idx, p in enumerate(replacement_products, 1):
            print(f"  {idx}. {p.name} - السعر: {p.price} ج.م - الكود: {p.code}")
        print("\nسيتم استخدام أول منتج")
    
    replacement = replacement_products.first()
    print(f"✅ تم العثور على منتج الاستبدال:")
    print(f"   - الاسم: {replacement.name}")
    print(f"   - السعر: {replacement.price} ج.م")
    print(f"   - الكود: {replacement.code}")
    
    return replacement


def replace_products(orders_data, replacement_product, confirm=True):
    """استبدال المنتجات في الطلبات"""
    
    if not orders_data or not replacement_product:
        return
    
    print("\n" + "=" * 80)
    print("معاينة التغييرات المقترحة:")
    print("=" * 80)
    
    for data in orders_data:
        print(f"\n📦 الطلب: {data['order_number']}")
        print(f"   من: {data['product_name']} (سعر: {data['unit_price']} ج.م)")
        print(f"   إلى: {replacement_product.name} (سعر: {replacement_product.price} ج.م)")
        print(f"   الكمية: {data['quantity']}")
    
    if confirm:
        print("\n" + "=" * 80)
        response = input("\n❓ هل تريد تنفيذ هذه التغييرات؟ (نعم/لا): ").strip().lower()
        
        if response not in ['نعم', 'yes', 'y']:
            print("\n❌ تم إلغاء العملية")
            return
    
    print("\n🔄 جاري تنفيذ التغييرات...")
    print("-" * 80)
    
    try:
        with transaction.atomic():
            updated_count = 0
            
            for data in orders_data:
                item = OrderItem.objects.get(id=data['item_id'])
                old_product = item.product.name
                old_price = item.unit_price
                
                # تحديث المنتج
                item.product = replacement_product
                item.unit_price = replacement_product.price
                item.save()
                
                updated_count += 1
                print(f"✅ تم تحديث الطلب {data['order_number']}")
                print(f"   القديم: {old_product} - {old_price} ج.م")
                print(f"   الجديد: {replacement_product.name} - {replacement_product.price} ج.م")
            
            print("\n" + "=" * 80)
            print(f"✅ تم تحديث {updated_count} عنصر بنجاح")
            print("=" * 80)
            
    except Exception as e:
        print(f"\n❌ خطأ أثناء التحديث: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """الدالة الرئيسية"""
    
    print("\n" + "=" * 80)
    print("سكريبت استبدال المنتج: نقل 450 → تفصيل مجاني")
    print("=" * 80)
    
    # الخطوة 1: البحث عن الطلبات
    orders_data = find_orders_with_product()
    
    if not orders_data:
        return
    
    # الخطوة 2: البحث عن المنتج البديل
    replacement_product = find_replacement_product()
    
    if not replacement_product:
        print("\n❌ لا يمكن المتابعة بدون منتج بديل")
        return
    
    # الخطوة 3: استبدال المنتجات
    replace_products(orders_data, replacement_product, confirm=True)


if __name__ == "__main__":
    main()
