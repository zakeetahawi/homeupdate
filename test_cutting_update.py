#!/usr/bin/env python
"""
اختبار تحديث أوامر التقطيع عند نقل المنتجات
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from inventory.models import Product, Warehouse, StockTransaction
from cutting.models import CuttingOrder, CuttingOrderItem
from orders.models import Order, OrderItem
from django.db.models import Sum

User = get_user_model()

def test_cutting_update():
    """اختبار تحديث أوامر التقطيع"""
    
    print("=" * 60)
    print("🧪 اختبار تحديث أوامر التقطيع التلقائي")
    print("=" * 60)
    
    # 1. البحث عن منتج موجود في أمر تقطيع
    print("\n1️⃣ البحث عن منتج في أمر تقطيع...")
    
    # البحث عن أمر تقطيع نشط
    cutting_order = CuttingOrder.objects.filter(
        status__in=['pending', 'in_progress']
    ).first()
    
    if not cutting_order:
        print("❌ لا توجد أوامر تقطيع نشطة للاختبار")
        print("💡 قم بإنشاء أمر تقطيع أولاً")
        return
    
    print(f"✅ أمر تقطيع موجود: {cutting_order.cutting_code}")
    print(f"   المستودع الحالي: {cutting_order.warehouse.name}")
    print(f"   الحالة: {cutting_order.status}")
    
    # البحث عن منتج في هذا الأمر
    cutting_item = cutting_order.items.first()
    if not cutting_item:
        print("❌ الأمر فارغ - لا يحتوي على عناصر")
        return
    
    product = cutting_item.order_item.product
    print(f"✅ منتج في الأمر: {product.name} (كود: {product.code})")
    
    # 2. فحص المستودع الحالي للمنتج
    print("\n2️⃣ فحص المستودع الحالي للمنتج...")
    
    current_stocks = StockTransaction.objects.filter(
        product=product
    ).values('warehouse__name').annotate(
        total=Sum('quantity')
    ).filter(total__gt=0)
    
    print(f"المنتج موجود في {len(current_stocks)} مستودع:")
    for stock in current_stocks:
        print(f"   - {stock['warehouse__name']}: {stock['total']} وحدة")
    
    # 3. محاكاة نقل المنتج
    print("\n3️⃣ محاكاة نقل المنتج...")
    
    # البحث عن مستودع آخر
    other_warehouse = Warehouse.objects.exclude(
        id=cutting_order.warehouse.id
    ).filter(is_active=True).first()
    
    if not other_warehouse:
        print("❌ لا يوجد مستودع آخر للاختبار")
        return
    
    print(f"📦 سنقوم بنقل المنتج إلى: {other_warehouse.name}")
    
    # 4. اختبار دالة التحديث
    print("\n4️⃣ اختبار دالة update_cutting_orders_after_move...")
    
    from inventory.smart_upload_logic import update_cutting_orders_after_move
    
    user = User.objects.filter(is_staff=True).first()
    
    result = update_cutting_orders_after_move(
        product=product,
        old_warehouse=cutting_order.warehouse,
        new_warehouse=other_warehouse,
        user=user
    )
    
    print("\n📊 نتيجة التحديث:")
    print(f"   ✅ أوامر محدثة: {result.get('updated', 0)}")
    print(f"   🔀 أوامر منقسمة: {result.get('split', 0)}")
    print(f"   📋 إجمالي متأثر: {result.get('total_affected', 0)}")
    print(f"   💬 رسالة: {result.get('message', 'N/A')}")
    
    if 'error' in result:
        print(f"   ❌ خطأ: {result['error']}")
    
    # 5. التحقق من التحديث
    print("\n5️⃣ التحقق من التحديث...")
    
    cutting_order.refresh_from_db()
    
    print(f"المستودع بعد التحديث: {cutting_order.warehouse.name}")
    
    if cutting_order.warehouse.id == other_warehouse.id:
        print("✅ تم التحديث بنجاح!")
    else:
        print(f"⚠️ المستودع لم يتغير (ربما كان الأمر مختلط)")
        
        # فحص إذا تم التقسيم
        new_orders = CuttingOrder.objects.filter(
            order=cutting_order.order,
            cutting_code__startswith=cutting_order.cutting_code + '-S'
        )
        
        if new_orders.exists():
            print(f"🔀 تم إنشاء {new_orders.count()} أمر جديد بعد التقسيم:")
            for order in new_orders:
                print(f"   - {order.cutting_code} → {order.warehouse.name}")
    
    print("\n" + "=" * 60)
    print("✅ اكتمل الاختبار")
    print("=" * 60)


if __name__ == '__main__':
    test_cutting_update()
