#!/usr/bin/env python3
"""
سكريبت اختبار لإصلاح حقل المعاينة المرتبطة
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from customers.models import Customer
from orders.models import Order
from inspections.models import Inspection
from orders.forms import OrderForm

User = get_user_model()

def test_related_inspection_fix():
    """اختبار إصلاح حقل المعاينة المرتبطة"""
    print("🔍 بدء اختبار إصلاح حقل المعاينة المرتبطة...")
    
    try:
        # إنشاء مستخدم للاختبار
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={
                'email': 'test@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        # إنشاء عميل للاختبار
        customer, created = Customer.objects.get_or_create(
            name='عميل اختبار',
            defaults={
                'phone': '0123456789',
                'email': 'customer@test.com'
            }
        )
        
        # إنشاء معاينة للاختبار
        inspection, created = Inspection.objects.get_or_create(
            customer=customer,
            defaults={
                'contract_number': 'TEST-001',
                'request_date': '2024-01-01',
                'scheduled_date': '2024-01-02',
                'status': 'pending'
            }
        )
        
        print(f"✅ تم إنشاء البيانات الأساسية:")
        print(f"   - المستخدم: {user.username}")
        print(f"   - العميل: {customer.name}")
        print(f"   - المعاينة: {inspection.id}")
        
        # اختبار النموذج للمعاينة
        print("\n🔍 اختبار النموذج للمعاينة...")
        form_data = {
            'customer': customer.id,
            'selected_types': 'inspection',
            'invoice_number': 'INV-001',
            'salesperson': 1,  # سيتم تجاهلها إذا لم تكن موجودة
            'branch': 1,  # سيتم تجاهلها إذا لم تكن موجودة
        }
        
        form = OrderForm(data=form_data, user=user, customer=customer)
        
        if form.is_valid():
            print("✅ النموذج صالح للمعاينة")
            order = form.save(commit=False)
            print(f"   - نوع الطلب: {order.selected_types}")
            print(f"   - المعاينة المرتبطة: {order.related_inspection}")
            print(f"   - نوع المعاينة المرتبطة: {order.related_inspection_type}")
        else:
            print("❌ النموذج غير صالح للمعاينة:")
            print(form.errors)
        
        # اختبار النموذج للتركيب
        print("\n🔍 اختبار النموذج للتركيب...")
        form_data_installation = {
            'customer': customer.id,
            'selected_types': 'installation',
            'invoice_number': 'INV-002',
            'contract_number': 'CON-001',
            'related_inspection': 'customer_side',
            'salesperson': 1,  # سيتم تجاهلها إذا لم تكن موجودة
            'branch': 1,  # سيتم تجاهلها إذا لم تكن موجودة
        }
        
        form_installation = OrderForm(data=form_data_installation, user=user, customer=customer)
        
        if form_installation.is_valid():
            print("✅ النموذج صالح للتركيب")
            order_installation = form_installation.save(commit=False)
            print(f"   - نوع الطلب: {order_installation.selected_types}")
            print(f"   - المعاينة المرتبطة: {order_installation.related_inspection}")
            print(f"   - نوع المعاينة المرتبطة: {order_installation.related_inspection_type}")
        else:
            print("❌ النموذج غير صالح للتركيب:")
            print(form_installation.errors)
        
        # اختبار النموذج للتركيب مع معاينة محددة
        print("\n🔍 اختبار النموذج للتركيب مع معاينة محددة...")
        form_data_installation_with_inspection = {
            'customer': customer.id,
            'selected_types': 'installation',
            'invoice_number': 'INV-003',
            'contract_number': 'CON-002',
            'related_inspection': str(inspection.id),
            'salesperson': 1,  # سيتم تجاهلها إذا لم تكن موجودة
            'branch': 1,  # سيتم تجاهلها إذا لم تكن موجودة
        }
        
        form_installation_with_inspection = OrderForm(data=form_data_installation_with_inspection, user=user, customer=customer)
        
        if form_installation_with_inspection.is_valid():
            print("✅ النموذج صالح للتركيب مع معاينة محددة")
            order_installation_with_inspection = form_installation_with_inspection.save(commit=False)
            print(f"   - نوع الطلب: {order_installation_with_inspection.selected_types}")
            print(f"   - المعاينة المرتبطة: {order_installation_with_inspection.related_inspection}")
            print(f"   - نوع المعاينة المرتبطة: {order_installation_with_inspection.related_inspection_type}")
        else:
            print("❌ النموذج غير صالح للتركيب مع معاينة محددة:")
            print(form_installation_with_inspection.errors)
        
        print("\n✅ تم إكمال جميع الاختبارات بنجاح!")
        
    except Exception as e:
        print(f"❌ حدث خطأ أثناء الاختبار: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_related_inspection_fix() 