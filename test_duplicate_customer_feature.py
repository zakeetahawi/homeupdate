#!/usr/bin/env python3
"""
سكريبت اختبار ميزة بطاقة العميل المكرر
Test script for duplicate customer card feature
"""

import os
import sys
import django
from django.conf import settings

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from customers.models import Customer
from accounts.models import Branch, User
from django.contrib.auth import get_user_model

def test_duplicate_customer_feature():
    """اختبار ميزة بطاقة العميل المكرر"""
    print("🔍 بدء اختبار ميزة بطاقة العميل المكرر...")
    print("Starting duplicate customer card feature test...")
    
    try:
        # البحث عن فرع موجود
        branch = Branch.objects.filter(is_active=True).first()
        if not branch:
            print("❌ لا يوجد فروع نشطة في النظام")
            return False
            
        # البحث عن مستخدم موجود
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ لا يوجد مستخدمين نشطين في النظام")
            return False
            
        # البحث عن عميل موجود
        existing_customer = Customer.objects.filter(status='active').first()
        if not existing_customer:
            print("❌ لا يوجد عملاء في النظام")
            return False
            
        print(f"✅ تم العثور على عميل موجود: {existing_customer.name}")
        print(f"📞 رقم الهاتف: {existing_customer.phone}")
        print(f"🏢 الفرع: {existing_customer.branch.name if existing_customer.branch else 'غير محدد'}")
        
        # محاكاة محاولة إنشاء عميل بنفس رقم الهاتف
        from customers.forms import CustomerForm
        
        # إنشاء بيانات نموذج مع رقم هاتف مكرر
        form_data = {
            'name': 'عميل تجريبي جديد',
            'phone': existing_customer.phone,  # نفس رقم الهاتف
            'phone2': '',
            'email': 'test@example.com',
            'address': 'عنوان تجريبي',
            'customer_type': 'retail',
            'status': 'active',
            'interests': '',
            'notes': ''
        }
        
        # إنشاء النموذج
        form = CustomerForm(data=form_data, user=user)
        
        # اختبار التحقق من صحة النموذج
        if not form.is_valid():
            print("✅ تم اكتشاف الخطأ المتوقع عند تكرار رقم الهاتف")
            
            # التحقق من وجود معلومات العميل الموجود
            if hasattr(form, 'existing_customer'):
                print("✅ تم حفظ معلومات العميل الموجود في النموذج")
                print(f"📋 معلومات العميل الموجود: {form.existing_customer.name}")
                
                # التحقق من رسالة الخطأ
                if 'phone' in form.errors:
                    error_message = form.errors['phone'][0]
                    print(f"📝 رسالة الخطأ: {error_message}")
                    
                    # التحقق من وجود كود الخطأ
                    if hasattr(form.errors['phone'][0], 'code') and form.errors['phone'][0].code == 'duplicate_phone':
                        print("✅ تم تحديد كود الخطأ الصحيح: duplicate_phone")
                    else:
                        print("⚠️ لم يتم تحديد كود الخطأ")
                        
                return True
            else:
                print("❌ لم يتم حفظ معلومات العميل الموجود")
                return False
        else:
            print("❌ لم يتم اكتشاف الخطأ المتوقع")
            return False
            
    except Exception as e:
        print(f"❌ حدث خطأ أثناء الاختبار: {str(e)}")
        return False

def test_customer_model_methods():
    """اختبار دوال نموذج العميل"""
    print("\n🔍 اختبار دوال نموذج العميل...")
    
    try:
        customer = Customer.objects.filter(status='active').first()
        if not customer:
            print("❌ لا يوجد عملاء للاختبار")
            return False
            
        # اختبار دالة get_absolute_url
        try:
            url = customer.get_absolute_url()
            print(f"✅ دالة get_absolute_url تعمل: {url}")
        except Exception as e:
            print(f"❌ خطأ في دالة get_absolute_url: {str(e)}")
            return False
            
        # اختبار دالة get_customer_type_display
        try:
            display = customer.get_customer_type_display()
            print(f"✅ دالة get_customer_type_display تعمل: {display}")
        except Exception as e:
            print(f"❌ خطأ في دالة get_customer_type_display: {str(e)}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ حدث خطأ أثناء اختبار دوال النموذج: {str(e)}")
        return False

def main():
    """الدالة الرئيسية"""
    print("=" * 60)
    print("🧪 اختبار ميزة بطاقة العميل المكرر")
    print("Testing Duplicate Customer Card Feature")
    print("=" * 60)
    
    # اختبار الميزة الرئيسية
    feature_test = test_duplicate_customer_feature()
    
    # اختبار دوال النموذج
    model_test = test_customer_model_methods()
    
    print("\n" + "=" * 60)
    print("📊 نتائج الاختبار:")
    print("Test Results:")
    print("=" * 60)
    
    if feature_test and model_test:
        print("✅ جميع الاختبارات نجحت")
        print("✅ الميزة جاهزة للاستخدام")
        print("✅ يمكن الآن عرض بطاقة العميل المكرر عند تكرار رقم الهاتف")
    else:
        print("❌ بعض الاختبارات فشلت")
        print("❌ يرجى مراجعة الكود وإصلاح المشاكل")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 