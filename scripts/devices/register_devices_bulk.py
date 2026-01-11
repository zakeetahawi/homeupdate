#!/usr/bin/env python
"""
سكريبت لتسجيل أجهزة متعددة دفعة واحدة من ملف CSV

الاستخدام:
    python register_devices_bulk.py devices.csv

تنسيق ملف CSV:
    branch_name,device_name,notes
    فرع الرياض,كمبيوتر الاستقبال 1,الطابق الأول
    فرع جدة,كمبيوتر المدير,مكتب المدير
"""

import csv
import os
import sys

import django

# إعداد Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from accounts.models import Branch, BranchDevice


def register_devices_from_csv(csv_file_path):
    """
    تسجيل أجهزة من ملف CSV

    ملاحظة: هذا السكريبت يقوم بإنشاء سجلات في قاعدة البيانات
    لكن سيحتاج المدير إلى تحديث البصمة الفعلية من كل جهاز
    """

    if not os.path.exists(csv_file_path):
        print(f"❌ الملف غير موجود: {csv_file_path}")
        return

    devices_created = 0
    devices_failed = 0

    print("📋 بدء تسجيل الأجهزة من ملف CSV...")
    print("-" * 60)

    with open(csv_file_path, "r", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)

        for row_num, row in enumerate(reader, start=1):
            branch_name = row.get("branch_name", "").strip()
            device_name = row.get("device_name", "").strip()
            notes = row.get("notes", "").strip()

            if not branch_name or not device_name:
                print(f"⚠️  سطر {row_num}: بيانات ناقصة (اسم الفرع أو اسم الجهاز)")
                devices_failed += 1
                continue

            # البحث عن الفرع
            try:
                branch = Branch.objects.get(name=branch_name)
            except Branch.DoesNotExist:
                print(f"❌ سطر {row_num}: الفرع '{branch_name}' غير موجود")
                devices_failed += 1
                continue
            except Branch.MultipleObjectsReturned:
                print(f"❌ سطر {row_num}: يوجد أكثر من فرع بنفس الاسم '{branch_name}'")
                devices_failed += 1
                continue

            # إنشاء بصمة مؤقتة (سيتم تحديثها لاحقاً)
            temp_fingerprint = f"TEMP_{branch.code}_{device_name}_{row_num}".replace(
                " ", "_"
            )

            # التحقق من عدم وجود جهاز بنفس الاسم في نفس الفرع
            if BranchDevice.objects.filter(
                branch=branch, device_name=device_name
            ).exists():
                print(
                    f"⚠️  سطر {row_num}: الجهاز '{device_name}' موجود بالفعل في فرع '{branch_name}'"
                )
                devices_failed += 1
                continue

            # إنشاء الجهاز
            try:
                device = BranchDevice.objects.create(
                    branch=branch,
                    device_name=device_name,
                    device_fingerprint=temp_fingerprint,
                    notes=notes
                    + "\n⚠️ تنبيه: البصمة مؤقتة - يجب تحديثها من الجهاز الفعلي",
                    is_active=False,  # غير نشط حتى يتم تحديث البصمة
                )

                print(
                    f"✅ سطر {row_num}: تم إنشاء '{device_name}' للفرع '{branch_name}'"
                )
                print(f"   🔑 البصمة المؤقتة: {temp_fingerprint}")
                print(f"   ⚠️  يجب تحديث البصمة من صفحة التسجيل!")
                devices_created += 1

            except Exception as e:
                print(f"❌ سطر {row_num}: خطأ في إنشاء الجهاز: {str(e)}")
                devices_failed += 1

    print("-" * 60)
    print(f"\n📊 النتائج:")
    print(f"   ✅ تم إنشاء: {devices_created} جهاز")
    print(f"   ❌ فشل: {devices_failed} جهاز")
    print(f"\n⚠️  تنبيه مهم:")
    print(f"   جميع الأجهزة المُنشأة غير نشطة وتحتوي على بصمات مؤقتة")
    print(f"   يجب على المدير:")
    print(f"   1. الذهاب إلى كل جهاز")
    print(f"   2. فتح صفحة التسجيل: /accounts/register-device/")
    print(f"   3. تسجيل الجهاز لتحديث البصمة الفعلية")
    print(f"   4. أو: تحديث البصمة يدوياً من لوحة الإدارة")


def create_sample_csv(output_file="devices_sample.csv"):
    """إنشاء ملف CSV نموذجي"""

    sample_data = [
        ["branch_name", "device_name", "notes"],
        ["فرع الرياض", "كمبيوتر الاستقبال 1", "الطابق الأول - مكتب الاستقبال"],
        ["فرع الرياض", "كمبيوتر الاستقبال 2", "الطابق الأول - مكتب الاستقبال"],
        ["فرع الرياض", "كمبيوتر المدير", "الطابق الثاني - مكتب المدير"],
        ["فرع جدة", "كمبيوتر الاستقبال", "منطقة الاستقبال الرئيسية"],
        ["فرع جدة", "كمبيوتر المحاسبة", "قسم المحاسبة"],
    ]

    with open(output_file, "w", encoding="utf-8-sig", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(sample_data)

    print(f"✅ تم إنشاء ملف CSV نموذجي: {output_file}")
    print(f"\nمحتوى الملف:")
    print("-" * 60)
    for row in sample_data:
        print(",".join(row))
    print("-" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("📝 الاستخدام:")
        print(f"   python {sys.argv[0]} <csv_file>")
        print(f"\nلإنشاء ملف CSV نموذجي:")
        print(f"   python {sys.argv[0]} --sample")
        print(f"\nتنسيق ملف CSV:")
        print(f"   branch_name,device_name,notes")
        print(f"   فرع الرياض,كمبيوتر الاستقبال 1,الطابق الأول")
        sys.exit(1)

    if sys.argv[1] == "--sample":
        create_sample_csv()
    else:
        csv_file = sys.argv[1]
        register_devices_from_csv(csv_file)
