#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت لاختبار استبدال Bootstrap Modal بـ SweetAlert2
"""

import os
import re
from pathlib import Path


def check_file_for_bootstrap_modal(file_path):
    """فحص ملف للبحث عن استخدامات Bootstrap Modal"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        issues = []

        # البحث عن استخدامات Bootstrap Modal
        modal_patterns = [
            r'data-bs-toggle="modal"',
            r'data-bs-target="#',
            r"bootstrap\.Modal",
            r"new bootstrap\.Modal",
            r"bootstrap\.Modal\.getInstance",
            r'class="modal fade"',
            r'class="modal-dialog"',
            r'class="modal-content"',
            r'class="modal-header"',
            r'class="modal-body"',
            r'class="modal-footer"',
            r'data-bs-dismiss="modal"',
        ]

        for pattern in modal_patterns:
            matches = re.findall(pattern, content)
            if matches:
                issues.append(f"  - وجد {len(matches)} استخدام لـ: {pattern}")

        return issues
    except Exception as e:
        return [f"  - خطأ في قراءة الملف: {e}"]


def check_file_for_sweetalert2(file_path):
    """فحص ملف للبحث عن استخدامات SweetAlert2"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        positives = []

        # البحث عن استخدامات SweetAlert2
        swal_patterns = [
            r"Swal\.fire",
            r"sweetalert2",
            r"openAdd.*Modal",
            r"confirmDelete",
            r"swal2-rtl",
            r"include.*sweetalert2_utils",
        ]

        for pattern in swal_patterns:
            matches = re.findall(pattern, content)
            if matches:
                positives.append(f"  + وجد {len(matches)} استخدام لـ: {pattern}")

        return positives
    except Exception as e:
        return [f"  - خطأ في قراءة الملف: {e}"]


def main():
    """الدالة الرئيسية"""
    print("🔍 فحص استبدال Bootstrap Modal بـ SweetAlert2")
    print("=" * 60)

    # مجلد المخزون
    inventory_dir = Path("inventory/templates/inventory")

    if not inventory_dir.exists():
        print("❌ لم يتم العثور على مجلد templates/inventory")
        return

    # الملفات المحدثة
    updated_files = [
        "category_list_new.html",
        "warehouse_list_new.html",
        "supplier_list_new.html",
        "warehouse_location_list.html",
        "purchase_order_list_new.html",
        "warehouse_detail.html",
    ]

    # الملفات الجديدة
    new_files = ["sweetalert2_utils.html", "sweetalert2_custom.css"]

    print("\n📁 فحص الملفات المحدثة:")
    print("-" * 40)

    all_issues = []
    all_positives = []

    for file_name in updated_files:
        file_path = inventory_dir / file_name
        if file_path.exists():
            print(f"\n📄 {file_name}:")

            # فحص Bootstrap Modal
            issues = check_file_for_bootstrap_modal(file_path)
            if issues:
                print("  ❌ مشاكل محتملة:")
                all_issues.extend(issues)
                for issue in issues:
                    print(issue)
            else:
                print("  ✅ لا توجد استخدامات لـ Bootstrap Modal")

            # فحص SweetAlert2
            positives = check_file_for_sweetalert2(file_path)
            if positives:
                print("  ✅ استخدامات SweetAlert2:")
                all_positives.extend(positives)
                for positive in positives:
                    print(positive)
            else:
                print("  ⚠️  لم يتم العثور على استخدامات SweetAlert2")
        else:
            print(f"\n❌ {file_name}: الملف غير موجود")

    print("\n📁 فحص الملفات الجديدة:")
    print("-" * 40)

    for file_name in new_files:
        file_path = inventory_dir / file_name
        if file_path.exists():
            print(f"  ✅ {file_name}: موجود")

            # فحص محتوى الملفات الجديدة
            positives = check_file_for_sweetalert2(file_path)
            if positives:
                print("    استخدامات SweetAlert2:")
                all_positives.extend(positives)
                for positive in positives:
                    print(positive)
        else:
            print(f"  ❌ {file_name}: الملف غير موجود")

    print("\n📊 ملخص النتائج:")
    print("-" * 40)

    if all_issues:
        print(f"❌ تم العثور على {len(all_issues)} مشكلة محتملة:")
        for issue in all_issues:
            print(issue)
    else:
        print("✅ لم يتم العثور على مشاكل محتملة")

    if all_positives:
        print(f"✅ تم العثور على {len(all_positives)} استخدام لـ SweetAlert2:")
        for positive in all_positives:
            print(positive)
    else:
        print("⚠️  لم يتم العثور على استخدامات SweetAlert2")

    print("\n🎯 التوصيات:")
    print("-" * 40)

    if all_issues:
        print("1. راجع الملفات التي تحتوي على استخدامات Bootstrap Modal")
        print("2. تأكد من استبدال جميع استخدامات Modal بـ SweetAlert2")
        print("3. اختبر الوظائف بعد التحديث")
    else:
        print("1. ✅ تم استبدال جميع استخدامات Bootstrap Modal بنجاح")
        print("2. ✅ تم إضافة SweetAlert2 بشكل صحيح")
        print("3. 🧪 اختبر الوظائف للتأكد من عملها بشكل صحيح")

    if all_positives:
        print("4. ✅ تم العثور على استخدامات SweetAlert2 في الملفات")
        print("5. ✅ الملفات الجديدة موجودة ومحتواها صحيح")

    print("\n📝 ملاحظات إضافية:")
    print("-" * 40)
    print("• تأكد من تحميل SweetAlert2 في جميع الصفحات")
    print("• تأكد من إضافة include لملف sweetalert2_utils.html")
    print("• تأكد من تحميل ملف CSS المخصص")
    print("• اختبر جميع النوافذ والوظائف")
    print("• راجع ملف README للحصول على مزيد من المعلومات")


if __name__ == "__main__":
    main()
