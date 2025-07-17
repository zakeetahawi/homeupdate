#!/usr/bin/env python3
"""
سكريبت اختبار لعرض حالة المعاينة في جدول الطلبات
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from orders.models import Order
from inspections.models import Inspection

def test_inspection_status_display():
    """اختبار عرض حالة المعاينة في جدول الطلبات"""
    
    print("🔍 اختبار عرض حالة المعاينة في جدول الطلبات")
    print("=" * 50)
    
    # البحث عن طلبات المعاينة
    all_orders = Order.objects.all()
    inspection_orders = []
    
    for order in all_orders:
        if 'inspection' in order.get_selected_types_list():
            inspection_orders.append(order)
    
    if not inspection_orders:
        print("❌ لا توجد طلبات معاينة في النظام")
        return
    
    print(f"✅ تم العثور على {len(inspection_orders)} طلب معاينة")
    print()
    
    for order in inspection_orders:
        print(f"📋 الطلب: {order.order_number}")
        print(f"   العميل: {order.customer}")
        print(f"   أنواع الطلب: {order.get_selected_types_list()}")
        
        # اختبار دالة عرض الحالة
        display_info = order.get_display_status()
        print(f"   مصدر الحالة: {display_info['source']}")
        print(f"   حالة الطلب: {display_info['status']}")
        
        # اختبار النص المعروض
        display_text = order.get_display_status_text()
        print(f"   النص المعروض: {display_text}")
        
        # اختبار فئة البادج
        badge_class = order.get_display_status_badge_class()
        print(f"   فئة البادج: {badge_class}")
        
        # اختبار الأيقونة
        icon = order.get_display_status_icon()
        print(f"   الأيقونة: {icon}")
        
        # البحث عن المعاينة المرتبطة
        inspection = order.inspections.first()
        if inspection:
            print(f"   المعاينة المرتبطة: {inspection.id}")
            print(f"   حالة المعاينة: {inspection.status}")
            print(f"   نص حالة المعاينة: {inspection.get_status_display()}")
        else:
            print("   ⚠️ لا توجد معاينة مرتبطة")
        
        print()
        
        # اختبار خاص: إذا كانت المعاينة مكتملة، يجب أن يعرض "مكتمل"
        if inspection and inspection.status == 'completed':
            if display_text == 'مكتمل':
                print("   ✅ تم عرض 'مكتمل' بشكل صحيح للطلب المكتمل")
            else:
                print(f"   ❌ خطأ: يجب أن يعرض 'مكتمل' بدلاً من '{display_text}'")
        print("-" * 50)
        print()

def test_manufacturing_status_display():
    """اختبار عرض حالة المصنع للطلبات الأخرى"""
    
    print("🏭 اختبار عرض حالة المصنع للطلبات الأخرى")
    print("=" * 50)
    
    # البحث عن طلبات التركيب
    installation_orders = Order.objects.filter(selected_types__contains=['installation'])
    
    if not installation_orders.exists():
        print("❌ لا توجد طلبات تركيب في النظام")
        return
    
    print(f"✅ تم العثور على {installation_orders.count()} طلب تركيب")
    print()
    
    for order in installation_orders[:3]:  # اختبار أول 3 طلبات فقط
        print(f"📋 الطلب: {order.order_number}")
        print(f"   العميل: {order.customer}")
        print(f"   أنواع الطلب: {order.get_selected_types_list()}")
        
        # اختبار دالة عرض الحالة
        display_info = order.get_display_status()
        print(f"   مصدر الحالة: {display_info['source']}")
        print(f"   حالة الطلب: {display_info['status']}")
        
        # اختبار النص المعروض
        display_text = order.get_display_status_text()
        print(f"   النص المعروض: {display_text}")
        
        # اختبار فئة البادج
        badge_class = order.get_display_status_badge_class()
        print(f"   فئة البادج: {badge_class}")
        
        # اختبار الأيقونة
        icon = order.get_display_status_icon()
        print(f"   الأيقونة: {icon}")
        
        print("-" * 50)
        print()

if __name__ == "__main__":
    print("🚀 بدء اختبار عرض حالة الطلبات")
    print("=" * 60)
    
    try:
        test_inspection_status_display()
        test_manufacturing_status_display()
        
        print("✅ تم إكمال جميع الاختبارات بنجاح!")
        
    except Exception as e:
        print(f"❌ حدث خطأ أثناء الاختبار: {e}")
        import traceback
        traceback.print_exc() 