#!/usr/bin/env python
"""
اختبار نهائي لإنشاء المعاينات التلقائية من الواجهة
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
from accounts.models import Branch, User, Salesperson
import json


def test_inspection_creation_final():
    """اختبار نهائي لإنشاء معاينة"""
    print("🎯 الاختبار النهائي لإنشاء المعاينات التلقائية")
    print("=" * 60)
    
    # البحث عن بيانات للاختبار
    customer = Customer.objects.first()
    branch = Branch.objects.first()
    user = User.objects.filter(is_active=True).first()
    salesperson = Salesperson.objects.filter(is_active=True).first()
    
    if not all([customer, branch, user, salesperson]):
        print("❌ لا توجد بيانات كافية للاختبار")
        return False
    
    print(f"📋 العميل: {customer}")
    print(f"🏢 الفرع: {branch}")
    print(f"👤 المستخدم: {user}")
    print(f"💼 البائع: {salesperson}")
    print(f"🔗 البائع له حساب مستخدم: {'نعم' if salesperson.user else 'لا'}")
    print()
    
    # عدد المعاينات قبل الاختبار
    inspections_before = Inspection.objects.count()
    print(f"📊 عدد المعاينات قبل الاختبار: {inspections_before}")
    
    # محاكاة بيانات الواجهة
    from orders.forms import OrderForm
    
    # بيانات كما تأتي من الواجهة
    form_data = {
        'customer': customer.id,
        'branch': branch.id,
        'salesperson': salesperson.id,
        'selected_types': 'inspection',  # هذا ما يأتي من الراديو
        'notes': 'طلب معاينة من الواجهة - اختبار نهائي',
        'status': 'normal',
        'delivery_type': 'branch',
        'delivery_address': '',
        'tracking_status': 'pending',
    }
    
    print(f"📋 بيانات الواجهة:")
    for key, value in form_data.items():
        print(f"  - {key}: {value}")
    print()
    
    # إنشاء النموذج كما يحدث في الواجهة
    form = OrderForm(data=form_data, user=user)
    
    print("🔍 فحص صحة النموذج...")
    if form.is_valid():
        print("✅ النموذج صالح - سيتم حفظ الطلب")
        
        # حفظ الطلب
        order = form.save()
        print(f"✅ تم حفظ الطلب: {order.order_number}")
        print(f"📋 selected_types النهائي: {order.selected_types}")
        print(f"📋 الأنواع المستخرجة: {order.get_selected_types_list()}")
        
        # انتظار قليل للإشارة
        import time
        time.sleep(2)
        
        # فحص المعاينات المرتبطة
        related_inspections = Inspection.objects.filter(order=order)
        print(f"\n🔍 فحص المعاينات المرتبطة...")
        print(f"🔍 عدد المعاينات المرتبطة: {related_inspections.count()}")
        
        if related_inspections.exists():
            inspection = related_inspections.first()
            print(f"\n✅ تم إنشاء المعاينة بنجاح!")
            print(f"📋 رقم المعاينة: {inspection.inspection_code}")
            print(f"📅 تاريخ الطلب: {inspection.request_date}")
            print(f"📅 تاريخ الجدولة: {inspection.scheduled_date}")
            print(f"📊 الحالة: {inspection.status}")
            print(f"👤 المعاين: {inspection.inspector or 'غير محدد'}")
            print(f"💼 الموظف المسؤول: {inspection.responsible_employee}")
            print(f"🏢 الفرع: {inspection.branch}")
            print(f"👥 العميل: {inspection.customer}")
            print(f"📝 الملاحظات: {inspection.notes}")
            
            # التحقق من الربط
            print(f"\n🔗 فحص الربط:")
            print(f"  - المعاينة مرتبطة بالطلب: {'نعم' if inspection.order == order else 'لا'}")
            print(f"  - الطلب له معاينات: {order.inspections.count()}")
            print(f"  - من قسم الطلبات: {'نعم' if inspection.is_from_orders else 'لا'}")
            
            # فحص العدد الإجمالي
            inspections_after = Inspection.objects.count()
            new_inspections = inspections_after - inspections_before
            print(f"\n📊 الإحصائيات:")
            print(f"  - المعاينات قبل: {inspections_before}")
            print(f"  - المعاينات بعد: {inspections_after}")
            print(f"  - المعاينات الجديدة: {new_inspections}")
            
            if new_inspections == 1:
                print("\n🎉 النتيجة النهائية: نجح الاختبار!")
                print("✅ تم إنشاء معاينة واحدة فقط كما هو مطلوب")
                print("✅ النظام يعمل بشكل صحيح من الواجهة")
                return True
            else:
                print(f"\n⚠️ تم إنشاء {new_inspections} معاينة (غير متوقع)")
                return False
        else:
            print("\n❌ لم يتم إنشاء معاينة تلقائية!")
            print("❌ هناك مشكلة في النظام")
            return False
    else:
        print("❌ النموذج غير صالح:")
        for field, errors in form.errors.items():
            print(f"  - {field}: {errors}")
        return False


def main():
    """الدالة الرئيسية"""
    print("🚀 الاختبار النهائي لنظام إنشاء المعاينات التلقائية")
    print("=" * 80)
    
    success = test_inspection_creation_final()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 تهانينا! النظام يعمل بشكل مثالي!")
        print("✅ المعاينات التلقائية تُنشأ عند طلب نوع 'معاينة' من الواجهة")
        print("✅ يمكن للمستخدمين الآن إنشاء طلبات معاينة بنجاح")
        print("\n📋 ما يحدث عند إنشاء طلب معاينة:")
        print("  1. المستخدم يختار نوع 'معاينة' من الواجهة")
        print("  2. يملأ بيانات الطلب (بدون رقم فاتورة)")
        print("  3. عند الحفظ، يتم إنشاء الطلب")
        print("  4. تلقائياً يتم إنشاء معاينة مرتبطة بالطلب")
        print("  5. المعاينة تظهر في قسم المعاينات")
        print("\n🎯 المشكلة محلولة تماماً!")
    else:
        print("❌ لا يزال هناك مشاكل في النظام")
        print("❌ يحتاج إلى مراجعة إضافية")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
