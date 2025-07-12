#!/usr/bin/env python
"""
سكريبت لاختبار تحديث تاريخ التسليم عند اكتمال المعاينة
"""

import os
import sys
import django
from datetime import datetime, timedelta

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from inspections.models import Inspection
from django.utils import timezone

def test_completion_date_update():
    """اختبار تحديث تاريخ التسليم عند اكتمال المعاينة"""
    print("🔍 اختبار تحديث تاريخ التسليم عند اكتمال المعاينة...")
    
    try:
        # البحث عن طلب معاينة موجود
        inspection_order = Order.objects.filter(
            selected_types__contains='inspection'
        ).first()
        
        if not inspection_order:
            print("❌ لا يوجد طلب معاينة للاختبار")
            return
        
        # البحث عن المعاينة المرتبطة
        inspection = Inspection.objects.filter(order=inspection_order).first()
        
        if not inspection:
            print("❌ لا توجد معاينة مرتبطة بالطلب")
            return
        
        print(f"✅ تم العثور على طلب معاينة:")
        print(f"   رقم الطلب: {inspection_order.order_number}")
        print(f"   حالة الطلب الحالية: {inspection_order.order_status}")
        print(f"   حالة المعاينة الحالية: {inspection.status}")
        print(f"   تاريخ التسليم الحالي: {inspection_order.expected_delivery_date}")
        
        # حفظ التاريخ الحالي
        old_delivery_date = inspection_order.expected_delivery_date
        
        # تغيير حالة المعاينة إلى مكتملة
        print(f"\n🔄 تغيير حالة المعاينة إلى 'مكتملة'...")
        inspection.status = 'completed'
        inspection.save()
        
        # إعادة تحميل البيانات
        inspection_order.refresh_from_db()
        inspection.refresh_from_db()
        
        print(f"✅ بعد التحديث:")
        print(f"   حالة الطلب الجديدة: {inspection_order.order_status}")
        print(f"   حالة المعاينة الجديدة: {inspection.status}")
        print(f"   تاريخ التسليم الجديد: {inspection_order.expected_delivery_date}")
        
        # التحقق من التحديث
        if inspection_order.expected_delivery_date != old_delivery_date:
            print("✅ تم تحديث تاريخ التسليم بنجاح!")
        else:
            print("❌ لم يتم تحديث تاريخ التسليم!")
        
        # إعادة الحالة إلى ما كانت عليه
        inspection.status = 'pending'
        inspection.save()
        
        inspection_order.refresh_from_db()
        print(f"\n✅ تم إعادة الحالات إلى ما كانت عليه")
        
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")

if __name__ == "__main__":
    test_completion_date_update() 