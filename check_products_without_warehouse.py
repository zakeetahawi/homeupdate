#!/usr/bin/env python
"""
سكريبت فحص المنتجات التي ليس لها مستودعات
يعرض المنتجات المستخدمة في الطلبات ولكن ليس لها معاملات مخزون في أي مستودع
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'home_update.settings')
django.setup()

from inventory.models import Product, StockTransaction, Warehouse
from orders.models import Order, OrderItem
from cutting.models import CuttingOrder, CuttingOrderItem
from datetime import datetime, timedelta

def check_products_without_warehouse():
    """فحص المنتجات المستخدمة في الطلبات بدون معاملات مخزون"""
    
    print("="*80)
    print("📊 فحص المنتجات التي ليس لها مستودعات")
    print("="*80)
    
    # البحث عن المنتجات المستخدمة في طلبات حديثة (آخر 7 أيام)
    recent_date = datetime.now() - timedelta(days=7)
    recent_order_items = OrderItem.objects.filter(
        order__created_at__gte=recent_date
    ).select_related('product', 'order')
    
    print(f"\n🔍 فحص {recent_order_items.count()} عنصر من الطلبات الحديثة (آخر 7 أيام)...")
    
    products_without_warehouse = []
    products_checked = set()
    
    for item in recent_order_items:
        if not item.product or item.product.id in products_checked:
            continue
            
        products_checked.add(item.product.id)
        
        # التحقق من وجود معاملات في المستودعات
        has_stock = StockTransaction.objects.filter(product=item.product).exists()
        
        if not has_stock:
            products_without_warehouse.append({
                'product': item.product,
                'order': item.order,
                'order_item': item
            })
    
    print("\n" + "="*80)
    print(f"📊 النتائج: {len(products_without_warehouse)} منتج بدون مستودع")
    print("="*80)
    
    if products_without_warehouse:
        print("\n⚠️ المنتجات التي ليس لها معاملات مخزون:")
        print("-"*80)
        
        for idx, data in enumerate(products_without_warehouse, 1):
            product = data['product']
            order = data['order']
            
            print(f"\n{idx}. 📦 المنتج: {product.name}")
            print(f"   🆔 الكود: {product.code}")
            print(f"   🏷️ الفئة: {product.category.name if product.category else 'غير محدد'}")
            print(f"   📝 الطلب: {order.order_number}")
            print(f"   👤 العميل: {order.customer.name if order.customer else 'غير محدد'}")
            print(f"   📅 تاريخ الطلب: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
            
            # التحقق من وجود أمر تقطيع
            cutting_items = CuttingOrderItem.objects.filter(
                order_item__product=product,
                cutting_order__order=order
            ).select_related('cutting_order__warehouse')
            
            if cutting_items.exists():
                for ci in cutting_items:
                    print(f"   🏪 أمر التقطيع: {ci.cutting_order.cutting_code} - مستودع {ci.cutting_order.warehouse.name}")
            else:
                print(f"   ❌ لا يوجد أمر تقطيع")
            
            print("-"*80)
        
        print("\n💡 التوصيات:")
        print("="*80)
        print("1. قم بنقل هذه المنتجات إلى المستودعات المناسبة")
        print("2. أو قم بإنشاء معاملة مخزون أولية لكل منتج")
        print("3. بعد النقل، يمكنك إعادة إنشاء أوامر التقطيع المفقودة")
        print("="*80)
        
    else:
        print("\n✅ جميع المنتجات المستخدمة في الطلبات الحديثة لها معاملات مخزون")
    
    # فحص إضافي: منتجات لها أوامر تقطيع في مستودعات لكن رصيدها صفر
    print("\n" + "="*80)
    print("📊 فحص المنتجات في أوامر تقطيع برصيد صفر")
    print("="*80)
    
    recent_cutting_orders = CuttingOrder.objects.filter(
        created_at__gte=recent_date
    ).prefetch_related('items__order_item__product')
    
    zero_stock_products = []
    
    for co in recent_cutting_orders:
        for item in co.items.all():
            if not item.order_item.product:
                continue
                
            # التحقق من الرصيد في المستودع
            last_transaction = StockTransaction.objects.filter(
                product=item.order_item.product,
                warehouse=co.warehouse
            ).order_by('-transaction_date').first()
            
            if last_transaction and last_transaction.running_balance <= 0:
                zero_stock_products.append({
                    'product': item.order_item.product,
                    'warehouse': co.warehouse,
                    'cutting_order': co,
                    'balance': last_transaction.running_balance
                })
    
    if zero_stock_products:
        print(f"\n⚠️ وجد {len(zero_stock_products)} منتج في أوامر تقطيع برصيد صفر:")
        print("-"*80)
        
        for data in zero_stock_products[:10]:  # عرض أول 10 فقط
            print(f"\n📦 {data['product'].name} ({data['product'].code})")
            print(f"   🏪 المستودع: {data['warehouse'].name}")
            print(f"   📊 الرصيد: {data['balance']}")
            print(f"   🆔 أمر التقطيع: {data['cutting_order'].cutting_code}")
            print("-"*80)
        
        if len(zero_stock_products) > 10:
            print(f"\n... وعناصر أخرى ({len(zero_stock_products) - 10} عنصر)")
    else:
        print("\n✅ جميع المنتجات في أوامر التقطيع لها رصيد متاح")
    
    print("\n" + "="*80)
    print("✅ انتهى الفحص")
    print("="*80)

if __name__ == '__main__':
    check_products_without_warehouse()
