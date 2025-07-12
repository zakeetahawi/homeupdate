#!/usr/bin/env python
"""
سكريبت لإنشاء طلب معاينة للاختبار
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

def create_test_inspection_order():
    """إنشاء طلب معاينة للاختبار"""
    print("🔍 إنشاء طلب معاينة للاختبار...")
    
    try:
        # الحصول على عميل وفرع وبائع للاختبار
        customer = Customer.objects.first()
        branch = Branch.objects.first()
        salesperson = Salesperson.objects.first()
        
        if not customer or not branch or not salesperson:
            print("❌ لا يمكن العثور على بيانات الاختبار المطلوبة")
            return
        
        print(f"✅ تم العثور على بيانات الاختبار:")
        print(f"   العميل: {customer.name}")
        print(f"   الفرع: {branch.name}")
        print(f"   البائع: {salesperson.name}")
        
        # إنشاء طلب معاينة جديد
        order = Order.objects.create(
            customer=customer,
            branch=branch,
            salesperson=salesperson,
            status='normal',
            selected_types=['inspection'],
            delivery_type='branch',
            delivery_address='',
            notes='طلب معاينة للاختبار'
        )
        
        print(f"✅ تم إنشاء طلب معاينة جديد:")
        print(f"   رقم الطلب: {order.order_number}")
        print(f"   حالة الطلب: {order.order_status}")
        print(f"   حالة التتبع: {order.tracking_status}")
        
        # التحقق من وجود المعاينة المرتبطة
        inspection = Inspection.objects.filter(order=order).first()
        if inspection:
            print(f"✅ تم إنشاء المعاينة المرتبطة:")
            print(f"   معرف المعاينة: {inspection.id}")
            print(f"   حالة المعاينة: {inspection.status}")
        else:
            print("❌ لم يتم إنشاء المعاينة المرتبطة")
        
        return order, inspection
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء طلب الاختبار: {e}")
        return None, None

if __name__ == "__main__":
    create_test_inspection_order() 