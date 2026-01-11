#!/usr/bin/env python
"""
اختبار إصلاح حقل حالة المديونية في المعاينات
"""
import os
import sys

import django

# إعداد Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from inspections.models import Inspection
from orders.models import Order


def test_payment_status_logic():
    """اختبار منطق حالة المديونية"""
    print("🧪 اختبار منطق حالة المديونية...")

    # البحث عن معاينة موجودة
    inspection = Inspection.objects.first()
    if not inspection:
        print("❌ لا توجد معاينات للاختبار")
        return False

    print(f"✅ تم العثور على معاينة: {inspection.contract_number}")

    # عرض حالة المديونية الحالية
    print(f"   حالة المديونية الحالية: {inspection.get_payment_status_display()}")

    # التحقق من الطلب المرتبط
    if inspection.order:
        print(f"   الطلب المرتبط: {inspection.order.order_number}")
        print(
            f"   حالة الدفع في الطلب: {'مدفوع بالكامل' if inspection.order.is_fully_paid else 'غير مدفوع بالكامل'}"
        )

        # محاكاة حفظ المعاينة لاختبار التحديث التلقائي
        old_payment_status = inspection.payment_status
        inspection.save()

        print(f"   حالة المديونية بعد الحفظ: {inspection.get_payment_status_display()}")

        # التحقق من التحديث الصحيح
        expected_status = (
            "paid" if inspection.order.is_fully_paid else "collect_on_visit"
        )
        if inspection.payment_status == expected_status:
            print("✅ تم تحديث حالة المديونية بشكل صحيح")
            return True
        else:
            print(
                f"❌ خطأ في تحديث حالة المديونية. متوقع: {expected_status}, فعلي: {inspection.payment_status}"
            )
            return False
    else:
        print("⚠️ المعاينة غير مرتبطة بطلب")
        return False


def test_form_fields():
    """اختبار حقول النموذج"""
    print("📝 اختبار حقول النموذج...")

    from inspections.forms import InspectionForm

    # إنشاء نموذج فارغ
    form = InspectionForm()

    # التحقق من عدم وجود حقل payment_status في الحقول
    if "payment_status" not in form.fields:
        print("✅ تم إزالة حقل payment_status من النموذج بنجاح")
        return True
    else:
        print("❌ حقل payment_status لا يزال موجوداً في النموذج")
        return False


def test_template_display():
    """اختبار عرض القالب"""
    print("🎨 اختبار عرض القالب...")

    # قراءة محتوى القالب
    template_path = "inspections/templates/inspections/inspection_form.html"

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # التحقق من وجود العرض الجديد لحالة المديونية
        if (
            "form-control-plaintext" in template_content
            and "badge bg-success" in template_content
        ):
            print("✅ تم تحديث القالب لعرض حالة المديونية كنص فقط")
            return True
        else:
            print("❌ لم يتم تحديث القالب بشكل صحيح")
            return False

    except FileNotFoundError:
        print(f"❌ لم يتم العثور على القالب: {template_path}")
        return False


def run_all_tests():
    """تشغيل جميع الاختبارات"""
    print("🚀 بدء اختبار إصلاح حقل حالة المديونية...\n")

    tests = [
        ("منطق حالة المديونية", test_payment_status_logic),
        ("حقول النموذج", test_form_fields),
        ("عرض القالب", test_template_display),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 اختبار: {test_name}")
        print("=" * 50)

        try:
            if test_func():
                print(f"✅ نجح اختبار: {test_name}")
                passed += 1
            else:
                print(f"❌ فشل اختبار: {test_name}")
                failed += 1
        except Exception as e:
            print(f"💥 خطأ في اختبار {test_name}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print("📊 نتائج اختبار إصلاح حالة المديونية:")
    print(f"✅ نجح: {passed}")
    print(f"❌ فشل: {failed}")
    print(f"📈 معدل النجاح: {(passed/(passed+failed)*100):.1f}%")
    print("=" * 50)

    if failed == 0:
        print("🎉 جميع الاختبارات نجحت! حقل حالة المديونية يعمل بشكل صحيح.")
    else:
        print("⚠️ بعض الاختبارات فشلت. يرجى مراجعة الأخطاء أعلاه.")


if __name__ == "__main__":
    run_all_tests()
