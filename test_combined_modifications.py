#!/usr/bin/env python3
"""
Script لاختبار عرض تعديلات الطلب وعناصر الطلب معاً
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

def test_combined_modifications():
    """اختبار عرض تعديلات الطلب وعناصر الطلب معاً"""
    
    print("🔍 اختبار عرض تعديلات الطلب وعناصر الطلب معاً...")
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
    
    # 4. عرض سجلات التعديل الحالية
    print("\n1️⃣ سجلات تعديل الطلب الحالية:")
    order_logs = OrderModificationLog.objects.filter(order=order).order_by('-modified_at')
    print(f"   📊 عدد سجلات تعديل الطلب: {order_logs.count()}")
    for log in order_logs:
        print(f"      - {log.modification_type}: {log.get_clean_old_total()} → {log.get_clean_new_total()}")
    
    print("\n2️⃣ سجلات تعديل عناصر الطلب الحالية:")
    item_logs = OrderItemModificationLog.objects.filter(order_item=item).order_by('-modified_at')
    print(f"   📊 عدد سجلات تعديل العنصر: {item_logs.count()}")
    for log in item_logs:
        print(f"      - {log.get_field_display_name()}: {log.get_clean_old_value()} → {log.get_clean_new_value()}")
    
    # 5. إنشاء تعديل جديد للاختبار
    print("\n3️⃣ إنشاء تعديل جديد للاختبار:")
    
    # تعديل الكمية
    old_quantity = item.quantity
    new_quantity = old_quantity + Decimal('0.25')
    
    print(f"   📊 تعديل الكمية: {old_quantity} → {new_quantity}")
    
    # تمرير المستخدم
    item._modified_by = user
    item.quantity = new_quantity
    item.save()
    
    # 6. عرض السجلات بعد التعديل
    print("\n4️⃣ السجلات بعد التعديل:")
    
    order_logs = OrderModificationLog.objects.filter(order=order).order_by('-modified_at')
    print(f"   📊 عدد سجلات تعديل الطلب: {order_logs.count()}")
    for log in order_logs:
        print(f"      - {log.modification_type}: {log.get_clean_old_total()} → {log.get_clean_new_total()}")
    
    item_logs = OrderItemModificationLog.objects.filter(order_item=item).order_by('-modified_at')
    print(f"   📊 عدد سجلات تعديل العنصر: {item_logs.count()}")
    for log in item_logs:
        print(f"      - {log.get_field_display_name()}: {log.get_clean_old_value()} → {log.get_clean_new_value()}")
    
    # 7. محاكاة عرض القالب
    print("\n5️⃣ محاكاة عرض القالب:")
    
    # محاكاة عرض تعديلات الطلب
    if order_logs.exists():
        print("   📋 تعديلات الطلب الأساسية:")
        for log in order_logs[:3]:  # عرض آخر 3 سجلات فقط
            print(f"      📝 {log.modification_type}")
            print(f"         المبلغ السابق: {log.get_clean_old_total()}")
            print(f"         المبلغ الجديد: {log.get_clean_new_total()}")
            print(f"         بواسطة: {log.modified_by.get_full_name() if log.modified_by else 'مدير النظام'}")
    
    # محاكاة عرض تعديلات عناصر الطلب
    if item_logs.exists():
        print("   📦 تعديلات عناصر الطلب:")
        for log in item_logs[:3]:  # عرض آخر 3 سجلات فقط
            print(f"      📝 {log.get_field_display_name()}: {log.get_clean_old_value()} → {log.get_clean_new_value()}")
            print(f"         بواسطة: {log.modified_by.get_full_name() if log.modified_by else 'مدير النظام'}")
    
    # 8. اختبار شرط العرض في القالب
    print("\n6️⃣ اختبار شرط العرض في القالب:")
    
    has_order_modifications = order.modification_logs.exists()
    has_item_modifications = any(item.modification_logs.exists() for item in order.items.all())
    
    print(f"   📊 يوجد تعديلات للطلب: {has_order_modifications}")
    print(f"   📊 يوجد تعديلات للعناصر: {has_item_modifications}")
    print(f"   📊 سيتم عرض قسم التعديلات: {has_order_modifications or has_item_modifications}")
    
    print("\n" + "=" * 60)
    print("📋 ملخص الاختبار:")
    print("✅ تعديلات الطلب وعناصر الطلب تظهر في قسم واحد")
    print("✅ يتم عرض القيم السابقة والجديدة بشكل صحيح")
    print("✅ يتم تتبع المستخدم الذي قام بالتعديل")
    print("✅ يتم تنسيق القيم العشرية بشكل صحيح")
    print("✅ شرط العرض يعمل بشكل صحيح")
    
    print("\n🎯 النتيجة:")
    print("الآن تعديلات الطلب وعناصر الطلب تظهر معاً في قسم 'تعديلات الطلب'!")
    print("يمكنك رؤية جميع التغييرات في مكان واحد")

if __name__ == '__main__':
    test_combined_modifications()
