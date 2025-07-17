#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت سريع لاختبار منطق الحالات الجديد لأوامر التصنيع
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from manufacturing.models import ManufacturingOrder
from manufacturing.views import ManufacturingOrderListView

def test_status_logic():
    """اختبار منطق الحالات الجديد"""
    
    print("🧪 اختبار منطق الحالات الجديد لأوامر التصنيع")
    print("=" * 50)
    
    # إنشاء instance من الـ view
    view = ManufacturingOrderListView()
    
    # اختبار الحالات المختلفة
    test_cases = [
        # (نوع الطلب, الحالة الحالية, الحالات المتوقعة)
        ('installation', 'in_progress', ['ready_install']),
        ('installation', 'ready_install', ['delivered']),
        ('tailoring', 'in_progress', ['completed']),
        ('tailoring', 'completed', ['delivered']),
        ('accessory', 'in_progress', ['completed']),
        ('accessory', 'completed', ['delivered']),
    ]
    
    for order_type, current_status, expected_statuses in test_cases:
        print(f"\n📋 اختبار: {order_type} - {current_status}")
        print(f"الحالات المتوقعة: {expected_statuses}")
        
        # محاكاة استدعاء الدالة
        try:
            # إنشاء user وهمي للاختبار
            from django.contrib.auth.models import User
            test_user = User.objects.filter(is_superuser=True).first()
            
            if test_user:
                available_statuses = view._get_available_statuses(
                    test_user, current_status, order_type
                )
                
                print(f"✅ الحالات المتاحة: {available_statuses}")
                
                # التحقق من النتائج
                if set(available_statuses) == set(expected_statuses):
                    print("✅ النتيجة صحيحة!")
                else:
                    print("❌ النتيجة خاطئة!")
                    print(f"متوقع: {expected_statuses}")
                    print(f"فعلي: {available_statuses}")
            else:
                print("⚠️ لم يتم العثور على مدير للاختبار")
                
        except Exception as e:
            print(f"❌ خطأ في الاختبار: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 انتهى الاختبار")

def test_order_types():
    """اختبار أنواع الطلبات في قاعدة البيانات"""
    
    print("\n📊 فحص أنواع الطلبات في قاعدة البيانات")
    print("=" * 50)
    
    try:
        orders = ManufacturingOrder.objects.all()[:10]  # أول 10 طلبات
        
        type_counts = {}
        status_counts = {}
        
        for order in orders:
            # الحصول على نوع الطلب
            order_types = order.order.get_selected_types_list() if hasattr(order.order, 'get_selected_types_list') else []
            
            for order_type in order_types:
                type_counts[order_type] = type_counts.get(order_type, 0) + 1
            
            # الحصول على الحالة
            status = order.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("📈 إحصائيات أنواع الطلبات:")
        for order_type, count in type_counts.items():
            print(f"  {order_type}: {count}")
        
        print("\n📈 إحصائيات الحالات:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
            
    except Exception as e:
        print(f"❌ خطأ في فحص قاعدة البيانات: {e}")

if __name__ == "__main__":
    print("🚀 بدء اختبار منطق الحالات الجديد...")
    
    # اختبار المنطق
    test_status_logic()
    
    # فحص قاعدة البيانات
    test_order_types()
    
    print("\n✨ انتهى جميع الاختبارات!") 