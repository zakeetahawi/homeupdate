#!/usr/bin/env python
"""
توحيد أرقام هواتف جميع العملاء حسب قواعد التنسيق المطلوبة.
"""
import os
import sys

import django

# إعداد Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
# إضافة مجلد المشروع الرئيسي إلى sys.path ليعمل السكريبت من أي موقع
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
django.setup()

from customers.models import Customer


def main():
    updated = 0
    for customer in Customer.objects.all():
        old_phone = customer.phone or ""
        phone = old_phone.replace(" ", "")
        if "/" in phone:
            phone = phone.split("/")[0]
        if phone.startswith("20"):
            phone = "0" + phone[2:]
        elif phone.startswith("1"):
            phone = "0" + phone
        if phone != old_phone:
            customer.phone = phone
            customer.save()
            updated += 1
            print(f"تم تحديث رقم العميل {customer.name}: {old_phone} → {phone}")
    print(f"تم تحديث {updated} رقم هاتف.")


if __name__ == "__main__":
    main()
