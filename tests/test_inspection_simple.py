#!/usr/bin/env python
"""
اختبار بسيط لإنشاء المعاينات التلقائية
"""

import os
import sys

import django

# إعداد Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

import json

from accounts.models import Branch, Salesperson, User
from customers.models import Customer
from inspections.models import Inspection
from orders.models import Order


def test_inspection_creation_from_form():
    """اختبار إنشاء معاينة من النموذج"""
    print("🧪 اختبار إنشاء معاينة من النموذج")
    print("=" * 50)

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
    print()

    # عدد المعاينات قبل الاختبار
    inspections_before = Inspection.objects.count()
    print(f"📊 عدد المعاينات قبل الاختبار: {inspections_before}")

    # اختبار إنشاء طلب معاينة باستخدام النموذج
    from orders.forms import OrderForm

    form_data = {
        "customer": customer.id,
        "branch": branch.id,
        "salesperson": salesperson.id,
        "selected_types": "inspection",  # نوع واحد فقط
        "notes": "اختبار إنشاء معاينة من النموذج",
        "status": "normal",
        "delivery_type": "branch",
        "delivery_address": "",
        "order_status": "pending",
        # لا نحتاج invoice_number للمعاينة
    }

    print(f"📋 بيانات النموذج:")
    for key, value in form_data.items():
        print(f"  - {key}: {value}")
    print()

    # إنشاء وتحقق من النموذج
    form = OrderForm(data=form_data, user=user)

    if form.is_valid():
        print("✅ النموذج صالح")

        # حفظ الطلب
        order = form.save()
        print(f"✅ تم حفظ الطلب: {order.order_number}")
        print(f"📋 selected_types بعد الحفظ: {order.selected_types}")
        print(f"📋 الأنواع المستخرجة: {order.get_selected_types_list()}")

        # انتظار قليل للإشارة
        import time

        time.sleep(1)

        # فحص المعاينات المرتبطة
        related_inspections = Inspection.objects.filter(order=order)
        print(f"🔍 عدد المعاينات المرتبطة: {related_inspections.count()}")

        if related_inspections.exists():
            inspection = related_inspections.first()
            print(f"✅ تم إنشاء المعاينة: {inspection.inspection_code}")
            print(f"📅 تاريخ الطلب: {inspection.request_date}")
            print(f"📅 تاريخ الجدولة: {inspection.scheduled_date}")
            print(f"📊 الحالة: {inspection.status}")
            print(f"👤 المعاين: {inspection.inspector}")
            print(f"💼 الموظف المسؤول: {inspection.responsible_employee}")

            # التحقق من عدد المعاينات الجديدة
            inspections_after = Inspection.objects.count()
            new_inspections = inspections_after - inspections_before
            print(f"\n📊 المعاينات الجديدة: {new_inspections}")

            if new_inspections == 1:
                print("✅ النتيجة: تم إنشاء معاينة واحدة بنجاح!")
                return True
            else:
                print(f"⚠️ النتيجة: تم إنشاء {new_inspections} معاينة")
                return False
        else:
            print("❌ لم يتم إنشاء معاينة تلقائية!")
            return False
    else:
        print("❌ النموذج غير صالح:")
        for field, errors in form.errors.items():
            print(f"  - {field}: {errors}")
        return False


def test_non_inspection_order():
    """اختبار طلب غير معاينة"""
    print("\n🧪 اختبار طلب تركيب (لا يجب إنشاء معاينة)")
    print("=" * 50)

    # البحث عن بيانات للاختبار
    customer = Customer.objects.first()
    branch = Branch.objects.first()
    user = User.objects.filter(is_active=True).first()
    salesperson = Salesperson.objects.filter(is_active=True).first()

    if not all([customer, branch, user, salesperson]):
        print("❌ لا توجد بيانات كافية للاختبار")
        return False

    # عدد المعاينات قبل الاختبار
    inspections_before = Inspection.objects.count()

    # اختبار إنشاء طلب تركيب
    from orders.forms import OrderForm

    form_data = {
        "customer": customer.id,
        "branch": branch.id,
        "salesperson": salesperson.id,
        "selected_types": "installation",  # تركيب
        "notes": "اختبار طلب تركيب - لا يجب إنشاء معاينة",
        "status": "normal",
        "invoice_number": "TEST-INSTALL-001",  # مطلوب للتركيب
        "contract_number": "CONTRACT-001",  # مطلوب للتركيب
        "delivery_type": "branch",
        "delivery_address": "",
        "order_status": "pending",
    }

    print(f"📋 بيانات طلب التركيب:")
    for key, value in form_data.items():
        print(f"  - {key}: {value}")
    print()

    # إنشاء وتحقق من النموذج
    form = OrderForm(data=form_data, user=user)

    if form.is_valid():
        print("✅ النموذج صالح")

        # حفظ الطلب
        order = form.save()
        print(f"✅ تم حفظ الطلب: {order.order_number}")
        print(f"📋 الأنواع المستخرجة: {order.get_selected_types_list()}")

        # انتظار قليل للإشارة
        import time

        time.sleep(1)

        # فحص المعاينات المرتبطة
        related_inspections = Inspection.objects.filter(order=order)
        print(f"🔍 عدد المعاينات المرتبطة: {related_inspections.count()}")

        if related_inspections.exists():
            print("❌ تم إنشاء معاينة بالخطأ لطلب تركيب!")
            return False
        else:
            print("✅ لم يتم إنشاء معاينة (صحيح)")

            # التحقق من عدم إنشاء معاينات جديدة
            inspections_after = Inspection.objects.count()
            new_inspections = inspections_after - inspections_before

            if new_inspections == 0:
                print("✅ النتيجة: لم يتم إنشاء أي معاينة (صحيح)")
                return True
            else:
                print(f"❌ النتيجة: تم إنشاء {new_inspections} معاينة بالخطأ!")
                return False
    else:
        print("❌ النموذج غير صالح:")
        for field, errors in form.errors.items():
            print(f"  - {field}: {errors}")
        return False


def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار نظام إنشاء المعاينات التلقائية")
    print("=" * 80)

    # اختبار 1: طلب معاينة
    test1_result = test_inspection_creation_from_form()

    # اختبار 2: طلب تركيب
    test2_result = test_non_inspection_order()

    print("\n🎯 النتيجة النهائية:")
    print("=" * 40)

    if test1_result and test2_result:
        print("✅ جميع الاختبارات نجحت!")
        print("✅ نظام إنشاء المعاينات التلقائية يعمل بشكل صحيح")
        print("\n📋 الخلاصة:")
        print("  ✅ طلبات المعاينة تنشئ معاينات تلقائية")
        print("  ✅ طلبات التركيب لا تنشئ معاينات")
        print("  ✅ النظام يعمل كما هو مطلوب")
        return True
    else:
        print("❌ بعض الاختبارات فشلت")
        print("❌ يحتاج النظام إلى مراجعة")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
