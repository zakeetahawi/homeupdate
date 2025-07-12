#!/usr/bin/env python3
"""
اختبار روابط العميل المكرر
Test customer duplicate links
"""

import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from customers.models import Customer
from django.urls import reverse

def test_customer_links():
    """اختبار روابط العميل المكرر"""
    print("🔍 اختبار روابط العميل المكرر...")
    
    try:
        # البحث عن عميل موجود
        customer = Customer.objects.filter(status='active').first()
        if not customer:
            print("❌ لا يوجد عملاء للاختبار")
            return False
            
        print(f"✅ تم العثور على عميل: {customer.name}")
        print(f"📞 رقم الهاتف: {customer.phone}")
        
        # اختبار رابط إنشاء طلب
        order_url = f"{reverse('orders:order_create')}?customer_id={customer.pk}"
        print(f"🔗 رابط إنشاء طلب: {order_url}")
        
        # اختبار رابط إنشاء معاينة
        inspection_url = f"{reverse('inspections:inspection_create')}?customer_id={customer.pk}"
        print(f"🔗 رابط إنشاء معاينة: {inspection_url}")
        
        # اختبار رابط تفاصيل العميل
        customer_url = reverse('customers:customer_detail', kwargs={'pk': customer.pk})
        print(f"🔗 رابط تفاصيل العميل: {customer_url}")
        
        print("✅ جميع الروابط صحيحة")
        return True
        
    except Exception as e:
        print(f"❌ حدث خطأ: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 اختبار روابط العميل المكرر")
    print("=" * 50)
    
    if test_customer_links():
        print("✅ الاختبار نجح")
    else:
        print("❌ الاختبار فشل")
    
    print("=" * 50) 