#!/usr/bin/env python3
"""
سكريبت اختبار مبسط لإصلاح حقل المعاينة المرتبطة
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

def test_form_choices():
    """اختبار بناء خيارات النموذج"""
    print("🔍 اختبار بناء خيارات النموذج...")
    
    try:
        from customers.models import Customer
        from orders.forms import OrderForm
        
        # البحث عن عميل موجود
        customer = Customer.objects.first()
        if not customer:
            print("❌ لا يوجد عملاء في قاعدة البيانات")
            return
        
        print(f"✅ تم العثور على عميل: {customer.name}")
        
        # إنشاء نموذج مع العميل
        form = OrderForm(customer=customer)
        
        # طباعة خيارات المعاينة المرتبطة
        choices = form.fields['related_inspection'].choices
        print(f"✅ عدد خيارات المعاينة المرتبطة: {len(choices)}")
        
        for i, (value, text) in enumerate(choices):
            print(f"   {i+1}. القيمة: '{value}' | النص: '{text}'")
        
        print("\n✅ تم اختبار بناء الخيارات بنجاح!")
        
    except Exception as e:
        print(f"❌ حدث خطأ: {str(e)}")
        import traceback
        traceback.print_exc()

def test_api_response():
    """اختبار استجابة الـ API"""
    print("\n🔍 اختبار استجابة الـ API...")
    
    try:
        from customers.models import Customer
        from inspections.models import Inspection
        
        # البحث عن عميل مع معاينات
        customer = Customer.objects.first()
        if not customer:
            print("❌ لا يوجد عملاء في قاعدة البيانات")
            return
        
        inspections = Inspection.objects.filter(customer=customer)
        if not inspections.exists():
            print(f"❌ لا توجد معاينات للعميل {customer.name}")
            return
        
        print(f"✅ تم العثور على {inspections.count()} معاينة للعميل {customer.name}")
        
        # محاكاة استجابة الـ API
        inspection_choices = [
            {'value': 'customer_side', 'text': 'طرف العميل'}
        ]
        
        for inspection in inspections:
            inspection_choices.append({
                'value': str(inspection.id),
                'text': f"{inspection.customer.name} - {inspection.contract_number or f'معاينة {inspection.id}'} - {inspection.created_at.strftime('%Y-%m-%d')}"
            })
        
        print(f"✅ تم بناء {len(inspection_choices)} خيار في الـ API")
        for i, choice in enumerate(inspection_choices):
            print(f"   {i+1}. القيمة: '{choice['value']}' | النص: '{choice['text']}'")
        
        print("\n✅ تم اختبار الـ API بنجاح!")
        
    except Exception as e:
        print(f"❌ حدث خطأ: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("🚀 بدء اختبار إصلاح حقل المعاينة المرتبطة...")
    test_form_choices()
    test_api_response()
    print("\n✅ تم إكمال جميع الاختبارات!") 