#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت سريع لاختبار إصلاح مشاكل الحالات
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from manufacturing.views import ManufacturingOrderListView

def test_status_fixes():
    """اختبار إصلاحات الحالات"""
    
    print("🔧 اختبار إصلاحات مشاكل الحالات")
    print("=" * 50)
    
    # إنشاء instance من الـ view
    view = ManufacturingOrderListView()
    
    # اختبار الحالات المختلفة
    test_cases = [
        # (نوع الطلب, الحالة الحالية, الحالات المتوقعة)
        ('installation', 'in_progress', ['ready_install']),
        ('installation', 'ready_install', ['delivered']),
        ('custom', 'in_progress', ['completed']),
        ('custom', 'completed', ['delivered']),
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
                
                # استخراج أسماء الحالات فقط
                status_names = [status[0] for status in available_statuses]
                
                print(f"✅ الحالات المتاحة: {status_names}")
                
                # التحقق من النتائج
                if set(status_names) == set(expected_statuses):
                    print("✅ النتيجة صحيحة!")
                else:
                    print("❌ النتيجة خاطئة!")
                    print(f"متوقع: {expected_statuses}")
                    print(f"فعلي: {status_names}")
            else:
                print("⚠️ لم يتم العثور على مدير للاختبار")
                
        except Exception as e:
            print(f"❌ خطأ في الاختبار: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 انتهى اختبار الإصلاحات")

def test_admin_status_access():
    """اختبار وصول المديرين للحالات"""
    
    print("\n👑 اختبار وصول المديرين للحالات")
    print("=" * 50)
    
    view = ManufacturingOrderListView()
    
    # اختبار حالات المديرين
    admin_test_cases = [
        ('installation', 'in_progress', ['ready_install']),
        ('custom', 'in_progress', ['completed']),
        ('accessory', 'in_progress', ['completed']),
    ]
    
    for order_type, current_status, expected_statuses in admin_test_cases:
        print(f"\n📋 اختبار المدير: {order_type} - {current_status}")
        
        try:
            from django.contrib.auth.models import User
            test_user = User.objects.filter(is_superuser=True).first()
            
            if test_user:
                available_statuses = view._get_available_statuses(
                    test_user, current_status, order_type
                )
                
                status_names = [status[0] for status in available_statuses]
                
                print(f"✅ الحالات المتاحة للمدير: {status_names}")
                
                # التحقق من أن المدير لا يمكنه الوصول لجميع الحالات بعد "قيد التنفيذ"
                if current_status == 'in_progress':
                    if 'rejected' in status_names or 'cancelled' in status_names:
                        print("❌ المدير يمكنه الوصول لحالات مرفوض/ملغي بعد قيد التنفيذ!")
                    else:
                        print("✅ المدير لا يمكنه الوصول لحالات مرفوض/ملغي بعد قيد التنفيذ")
                        
            else:
                print("⚠️ لم يتم العثور على مدير للاختبار")
                
        except Exception as e:
            print(f"❌ خطأ في الاختبار: {e}")

if __name__ == "__main__":
    print("🚀 بدء اختبار إصلاحات مشاكل الحالات...")
    
    # اختبار الإصلاحات الأساسية
    test_status_fixes()
    
    # اختبار وصول المديرين
    test_admin_status_access()
    
    print("\n✨ انتهى جميع الاختبارات!") 