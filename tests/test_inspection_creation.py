#!/usr/bin/env python
"""
اختبار إنشاء المعاينات التلقائية من الطلبات
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from inspections.models import Inspection
from customers.models import Customer
from accounts.models import Branch, User
import json


def test_inspection_creation():
    """اختبار إنشاء معاينة تلقائية"""
    print("🧪 اختبار إنشاء المعاينات التلقائية")
    print("=" * 60)
    
    # البحث عن بيانات للاختبار
    customer = Customer.objects.first()
    branch = Branch.objects.first()
    user = User.objects.filter(is_active=True).first()
    
    if not all([customer, branch, user]):
        print("❌ لا توجد بيانات كافية للاختبار")
        return False
    
    print(f"📋 العميل: {customer}")
    print(f"🏢 الفرع: {branch}")
    print(f"👤 المستخدم: {user}")
    print()
    
    # عدد المعاينات قبل الاختبار
    inspections_before = Inspection.objects.count()
    print(f"📊 عدد المعاينات قبل الاختبار: {inspections_before}")
    
    # اختبار 1: إنشاء طلب معاينة بالطريقة الصحيحة
    print("\n🔬 اختبار 1: إنشاء طلب معاينة")
    print("-" * 40)
    
    try:
        order1 = Order.objects.create(
            customer=customer,
            branch=branch,
            created_by=user,
            selected_types=json.dumps(['inspection']),  # الطريقة الصحيحة
            notes='اختبار إنشاء معاينة تلقائية - الطريقة الصحيحة',
            order_type='service'
        )
        
        print(f"✅ تم إنشاء الطلب: {order1.order_number}")
        print(f"📋 selected_types: {order1.selected_types}")
        print(f"📋 الأنواع المستخرجة: {order1.get_selected_types_list()}")
        
        # فحص المعاينات المرتبطة
        related_inspections = Inspection.objects.filter(order=order1)
        print(f"🔍 عدد المعاينات المرتبطة: {related_inspections.count()}")
        
        if related_inspections.exists():
            inspection = related_inspections.first()
            print(f"✅ تم إنشاء المعاينة: {inspection.inspection_code}")
            print(f"📅 تاريخ الطلب: {inspection.request_date}")
            print(f"📅 تاريخ الجدولة: {inspection.scheduled_date}")
            print(f"📊 الحالة: {inspection.status}")
        else:
            print("❌ لم يتم إنشاء معاينة تلقائية!")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار 1: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # اختبار 2: إنشاء طلب غير معاينة
    print("\n🔬 اختبار 2: إنشاء طلب تركيب (لا يجب إنشاء معاينة)")
    print("-" * 40)
    
    try:
        order2 = Order.objects.create(
            customer=customer,
            branch=branch,
            created_by=user,
            selected_types=json.dumps(['installation']),
            notes='اختبار طلب تركيب - لا يجب إنشاء معاينة',
            order_type='service'
        )
        
        print(f"✅ تم إنشاء الطلب: {order2.order_number}")
        print(f"📋 الأنواع المستخرجة: {order2.get_selected_types_list()}")
        
        # فحص المعاينات المرتبطة
        related_inspections = Inspection.objects.filter(order=order2)
        print(f"🔍 عدد المعاينات المرتبطة: {related_inspections.count()}")
        
        if related_inspections.exists():
            print("❌ تم إنشاء معاينة بالخطأ لطلب تركيب!")
        else:
            print("✅ لم يتم إنشاء معاينة (صحيح)")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار 2: {str(e)}")
    
    # اختبار 3: إنشاء طلب بـ selected_types فارغ
    print("\n🔬 اختبار 3: إنشاء طلب بدون نوع محدد")
    print("-" * 40)
    
    try:
        order3 = Order.objects.create(
            customer=customer,
            branch=branch,
            created_by=user,
            selected_types='',  # فارغ
            notes='اختبار طلب بدون نوع محدد',
            order_type='service'
        )
        
        print(f"✅ تم إنشاء الطلب: {order3.order_number}")
        print(f"📋 selected_types: '{order3.selected_types}'")
        print(f"📋 الأنواع المستخرجة: {order3.get_selected_types_list()}")
        
        # فحص المعاينات المرتبطة
        related_inspections = Inspection.objects.filter(order=order3)
        print(f"🔍 عدد المعاينات المرتبطة: {related_inspections.count()}")
        
        if related_inspections.exists():
            print("❌ تم إنشاء معاينة بالخطأ لطلب فارغ!")
        else:
            print("✅ لم يتم إنشاء معاينة (صحيح)")
            
    except Exception as e:
        print(f"❌ خطأ في اختبار 3: {str(e)}")
    
    # النتائج النهائية
    print("\n📊 النتائج النهائية:")
    print("=" * 40)
    
    inspections_after = Inspection.objects.count()
    new_inspections = inspections_after - inspections_before
    
    print(f"📊 عدد المعاينات قبل الاختبار: {inspections_before}")
    print(f"📊 عدد المعاينات بعد الاختبار: {inspections_after}")
    print(f"📊 المعاينات الجديدة: {new_inspections}")
    
    if new_inspections == 1:
        print("✅ النتيجة: تم إنشاء معاينة واحدة فقط (صحيح)")
        return True
    elif new_inspections == 0:
        print("❌ النتيجة: لم يتم إنشاء أي معاينة (خطأ)")
        return False
    else:
        print(f"⚠️ النتيجة: تم إنشاء {new_inspections} معاينة (غير متوقع)")
        return False


def test_order_form_simulation():
    """محاكاة إنشاء طلب من النموذج"""
    print("\n🌐 اختبار محاكاة النموذج")
    print("=" * 40)
    
    from orders.forms import OrderForm
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = User.objects.filter(is_active=True).first()
    customer = Customer.objects.first()
    branch = Branch.objects.first()
    
    if not all([user, customer, branch]):
        print("❌ لا توجد بيانات كافية لاختبار النموذج")
        return False
    
    # بيانات النموذج
    form_data = {
        'customer': customer.id,
        'branch': branch.id,
        'selected_types': 'inspection',  # كما يأتي من النموذج
        'notes': 'اختبار من النموذج المحاكي',
        'status': 'normal',
        'invoice_number': 'TEST-001',
        'delivery_type': 'branch',
        'delivery_address': '',
    }
    
    print(f"📋 بيانات النموذج: {form_data}")
    
    # إنشاء النموذج
    form = OrderForm(data=form_data, user=user)
    
    if form.is_valid():
        print("✅ النموذج صالح")
        
        # حفظ الطلب
        order = form.save()
        print(f"✅ تم حفظ الطلب: {order.order_number}")
        print(f"📋 selected_types بعد الحفظ: {order.selected_types}")
        print(f"📋 الأنواع المستخرجة: {order.get_selected_types_list()}")
        
        # فحص المعاينات
        related_inspections = Inspection.objects.filter(order=order)
        print(f"🔍 عدد المعاينات المرتبطة: {related_inspections.count()}")
        
        if related_inspections.exists():
            inspection = related_inspections.first()
            print(f"✅ تم إنشاء المعاينة: {inspection.inspection_code}")
            return True
        else:
            print("❌ لم يتم إنشاء معاينة من النموذج!")
            return False
    else:
        print("❌ النموذج غير صالح:")
        for field, errors in form.errors.items():
            print(f"  - {field}: {errors}")
        return False


def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار إنشاء المعاينات التلقائية")
    print("=" * 80)
    
    # اختبار إنشاء المعاينات
    test1_result = test_inspection_creation()
    
    # اختبار النموذج
    test2_result = test_order_form_simulation()
    
    print("\n🎯 النتيجة النهائية:")
    print("=" * 40)
    
    if test1_result and test2_result:
        print("✅ جميع الاختبارات نجحت!")
        print("✅ نظام إنشاء المعاينات التلقائية يعمل بشكل صحيح")
        return True
    else:
        print("❌ بعض الاختبارات فشلت")
        print("❌ يحتاج النظام إلى مراجعة")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
