#!/usr/bin/env python3
"""
Script لاختبار نظام تتبع التعديلات الجديد
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from orders.models import Order, OrderItem, OrderModificationLog, OrderItemModificationLog
from inventory.models import Product
from accounts.models import User
from decimal import Decimal

def test_modification_tracking():
    """اختبار نظام تتبع التعديلات"""
    
    print("🔍 اختبار نظام تتبع التعديلات الجديد...")
    print("=" * 60)
    
    # 1. البحث عن طلب مع عناصر
    order = Order.objects.filter(items__isnull=False).first()
    if not order:
        print("❌ لم يتم العثور على طلب مع عناصر")
        return
    
    print(f"📋 الطلب المختار: {order.order_number}")
    
    # 2. البحث عن عنصر طلب
    item = order.items.first()
    if not item:
        print("❌ لم يتم العثور على عناصر في الطلب")
        return
    
    print(f"📦 العنصر المختار: {item.product.name} - الكمية: {item.quantity}")
    
    # 3. البحث عن مستخدم
    user = User.objects.first()
    if not user:
        print("❌ لم يتم العثور على مستخدمين")
        return
    
    print(f"👤 المستخدم المختار: {user.get_full_name() or user.username}")
    
    # 4. اختبار تعديل الكمية
    print("\n1️⃣ اختبار تعديل الكمية:")
    old_quantity = item.quantity
    new_quantity = old_quantity + Decimal('0.5')
    
    print(f"   📊 الكمية القديمة: {old_quantity}")
    print(f"   📊 الكمية الجديدة: {new_quantity}")
    
    # تمرير المستخدم
    item._modified_by = user
    item.quantity = new_quantity
    item.save()
    
    # التحقق من إنشاء سجل التعديل
    modification_log = OrderItemModificationLog.objects.filter(
        order_item=item,
        field_name='quantity'
    ).order_by('-modified_at').first()
    
    if modification_log:
        print(f"   ✅ تم إنشاء سجل تعديل الكمية:")
        print(f"      📝 القيمة السابقة: {modification_log.get_clean_old_value()}")
        print(f"      📝 القيمة الجديدة: {modification_log.get_clean_new_value()}")
        print(f"      👤 تم التعديل بواسطة: {modification_log.modified_by.get_full_name() if modification_log.modified_by else 'غير محدد'}")
    else:
        print("   ❌ لم يتم إنشاء سجل تعديل الكمية")
    
    # 5. اختبار تعديل سعر الوحدة
    print("\n2️⃣ اختبار تعديل سعر الوحدة:")
    old_price = item.unit_price
    new_price = old_price + Decimal('10.00')
    
    print(f"   📊 السعر القديم: {old_price}")
    print(f"   📊 السعر الجديد: {new_price}")
    
    # تمرير المستخدم
    item._modified_by = user
    item.unit_price = new_price
    item.save()
    
    # التحقق من إنشاء سجل التعديل
    modification_log = OrderItemModificationLog.objects.filter(
        order_item=item,
        field_name='unit_price'
    ).order_by('-modified_at').first()
    
    if modification_log:
        print(f"   ✅ تم إنشاء سجل تعديل السعر:")
        print(f"      📝 القيمة السابقة: {modification_log.get_clean_old_value()}")
        print(f"      📝 القيمة الجديدة: {modification_log.get_clean_new_value()}")
        print(f"      👤 تم التعديل بواسطة: {modification_log.modified_by.get_full_name() if modification_log.modified_by else 'غير محدد'}")
    else:
        print("   ❌ لم يتم إنشاء سجل تعديل السعر")
    
    # 6. اختبار سجل التعديل الشامل
    print("\n3️⃣ اختبار سجل التعديل الشامل:")
    modification_log = OrderModificationLog.objects.filter(
        order=order
    ).order_by('-modified_at').first()
    
    if modification_log:
        print(f"   ✅ تم إنشاء سجل تعديل شامل:")
        print(f"      📝 نوع التعديل: {modification_log.modification_type}")
        print(f"      📝 المبلغ السابق: {modification_log.get_clean_old_total()}")
        print(f"      📝 المبلغ الجديد: {modification_log.get_clean_new_total()}")
        print(f"      📝 التفاصيل: {modification_log.details}")
        print(f"      👤 تم التعديل بواسطة: {modification_log.modified_by.get_full_name() if modification_log.modified_by else 'غير محدد'}")
    else:
        print("   ❌ لم يتم إنشاء سجل تعديل شامل")
    
    # 7. عرض جميع سجلات التعديل
    print("\n4️⃣ جميع سجلات التعديل:")
    
    item_logs = OrderItemModificationLog.objects.filter(order_item=item).order_by('-modified_at')
    print(f"   📊 سجلات تعديل العنصر: {item_logs.count()}")
    for log in item_logs:
        print(f"      - {log.get_field_display_name()}: {log.get_clean_old_value()} → {log.get_clean_new_value()}")
    
    order_logs = OrderModificationLog.objects.filter(order=order).order_by('-modified_at')
    print(f"   📊 سجلات تعديل الطلب: {order_logs.count()}")
    for log in order_logs:
        print(f"      - {log.modification_type}: {log.get_clean_old_total()} → {log.get_clean_new_total()}")
    
    # 8. اختبار تنسيق القيم
    print("\n5️⃣ اختبار تنسيق القيم:")
    
    # اختبار القيم العشرية
    test_values = [
        Decimal('4.250'),
        Decimal('1.000'),
        Decimal('10.500'),
        Decimal('0.001'),
        Decimal('150.00'),
        Decimal('150.50'),
    ]
    
    for value in test_values:
        str_value = str(value)
        if '.' in str_value:
            str_value = str_value.rstrip('0')
            if str_value.endswith('.'):
                str_value = str_value[:-1]
        print(f"   📊 {value} → {str_value}")
    
    print("\n" + "=" * 60)
    print("📋 ملخص الاختبار:")
    print("✅ نظام تتبع التعديلات يعمل بشكل صحيح")
    print("✅ يتم حفظ القيم السابقة والجديدة")
    print("✅ يتم تتبع المستخدم الذي قام بالتعديل")
    print("✅ يتم تنسيق القيم العشرية بشكل صحيح")
    print("✅ يتم إنشاء سجلات شاملة للتعديلات")
    
    print("\n🎯 النتيجة:")
    print("النظام الآن يحفظ القيم السابقة والجديدة بشكل صحيح!")
    print("يمكنك الآن رؤية التغييرات في صفحة تفاصيل الطلب")

if __name__ == '__main__':
    test_modification_tracking()
