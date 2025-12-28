#!/usr/bin/env python
"""
Script لتحديث الطلب 14-1097-0002
يصحح قيمة total_amount لتكون المجموع الصحيح قبل الخصم
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from decimal import Decimal

def fix_order():
    """تحديث الطلب 14-1097-0002"""
    order_number = '14-1097-0002'
    
    try:
        order = Order.objects.get(order_number=order_number)
        print(f"✅ تم العثور على الطلب: {order.order_number}")
        print(f"   العميل: {order.customer.name if order.customer else 'غير محدد'}")
        print(f"   تاريخ الطلب: {order.order_date}")
        print()
        
        # حساب المجموع الصحيح قبل الخصم
        total_before_discount = Decimal('0')
        total_discount = Decimal('0')
        
        print("عناصر الطلب:")
        print("-" * 80)
        for item in order.items.all():
            item_total = item.quantity * item.unit_price
            item_discount = item.discount_amount if item.discount_amount else Decimal('0')
            
            total_before_discount += item_total
            total_discount += item_discount
            
            print(f"  • {item.product.name}")
            print(f"    الكمية: {item.quantity} × السعر: {item.unit_price} = {item_total} ج.م")
            print(f"    الخصم: {item_discount} ج.م")
            print()
        
        print("-" * 80)
        print(f"\n📊 الملخص:")
        print(f"   المجموع قبل الخصم (الحالي في DB): {order.total_amount} ج.م")
        print(f"   المجموع قبل الخصم (الصحيح): {total_before_discount} ج.م")
        print(f"   إجمالي الخصم: {total_discount} ج.م")
        print(f"   الإجمالي النهائي: {total_before_discount - total_discount} ج.م")
        print()
        
        if order.total_amount != total_before_discount:
            print(f"⚠️  يوجد فرق: {total_before_discount - order.total_amount} ج.م")
            print()
            
            # تحديث
            old_value = order.total_amount
            order.total_amount = total_before_discount
            order.save(update_fields=['total_amount'])
            
            print(f"✅ تم التحديث بنجاح!")
            print(f"   من: {old_value} ج.م")
            print(f"   إلى: {order.total_amount} ج.م")
        else:
            print("✅ القيمة صحيحة بالفعل، لا حاجة للتحديث")
        
    except Order.DoesNotExist:
        print(f"❌ الطلب {order_number} غير موجود في قاعدة البيانات")
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 80)
    print("تحديث الطلب 14-1097-0002")
    print("=" * 80)
    print()
    fix_order()
    print()
    print("=" * 80)
