#!/usr/bin/env python
"""
سكريبت لاختبار تحديث حالة المعاينة والتأكد من تحديث حالة الطلب المرتبط
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
from customers.models import Customer
from accounts.models import Branch, Salesperson
from django.utils import timezone

def test_inspection_status_update():
    """اختبار تحديث حالة المعاينة"""
    print("🔍 اختبار تحديث حالة المعاينة...")
    
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
        
        # إنشاء معاينة يدوياً إذا لم تكن موجودة
        if not inspection:
            print("⚠️ لم توجد معاينة مرتبطة، إنشاء معاينة يدوياً...")
            inspection = Inspection.objects.create(
                customer=inspection_order.customer,
                branch=inspection_order.branch,
                responsible_employee=inspection_order.salesperson,
                order=inspection_order,
                is_from_orders=True,
                request_date=timezone.now().date(),
                scheduled_date=timezone.now().date() + timedelta(days=1),
                status='pending',
                notes=f'معاينة تلقائية للطلب رقم {inspection_order.order_number}',
                order_notes=inspection_order.notes,
                created_by=inspection_order.created_by
            )
            print(f"✅ تم إنشاء المعاينة يدوياً: {inspection.id}")
        
        print(f"✅ تم العثور على طلب معاينة:")
        print(f"   رقم الطلب: {inspection_order.order_number}")
        print(f"   حالة الطلب الحالية: {inspection_order.order_status}")
        print(f"   حالة التتبع الحالية: {inspection_order.tracking_status}")
        print(f"   حالة المعاينة الحالية: {inspection.status}")
        
        # حفظ الحالات الحالية
        old_order_status = inspection_order.order_status
        old_tracking_status = inspection_order.tracking_status
        old_inspection_status = inspection.status
        
        # تغيير حالة المعاينة إلى مجدول
        print(f"\n🔄 تغيير حالة المعاينة إلى 'مجدول'...")
        inspection.status = 'scheduled'
        inspection.save()
        
        # إعادة تحميل البيانات
        inspection_order.refresh_from_db()
        inspection.refresh_from_db()
        
        print(f"✅ بعد التحديث:")
        print(f"   حالة الطلب الجديدة: {inspection_order.order_status}")
        print(f"   حالة التتبع الجديدة: {inspection_order.tracking_status}")
        print(f"   حالة المعاينة الجديدة: {inspection.status}")
        
        # التحقق من التحديث
        expected_order_status = 'in_progress'
        expected_tracking_status = 'factory'
        
        if (inspection_order.order_status == expected_order_status and 
            inspection_order.tracking_status == expected_tracking_status):
            print("✅ تم تحديث حالة الطلب بشكل صحيح!")
        else:
            print("❌ خطأ في تحديث حالة الطلب!")
            print(f"   المتوقع: order_status={expected_order_status}, tracking_status={expected_tracking_status}")
            print(f"   الفعلي: order_status={inspection_order.order_status}, tracking_status={inspection_order.tracking_status}")
        
        # إعادة الحالات إلى ما كانت عليه
        inspection.status = old_inspection_status
        inspection.save()
        
        inspection_order.refresh_from_db()
        print(f"\n✅ تم إعادة الحالات إلى ما كانت عليه")
        
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")

if __name__ == "__main__":
    test_inspection_status_update() 