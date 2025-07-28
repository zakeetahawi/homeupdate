#!/usr/bin/env python
"""
توحيد أرقام هواتف جميع العملاء حسب قواعد التنسيق المطلوبة.
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from customers.models import Customer

def main():
    updated = 0
    for customer in Customer.objects.all():
        old_phone = customer.phone or ''
        phone = old_phone.replace(' ', '')
        if '/' in phone:
            phone = phone.split('/')[0]
        if phone.startswith('20'):
            phone = '0' + phone[2:]
        elif phone.startswith('1'):
            phone = '0' + phone
        if phone != old_phone:
            customer.phone = phone
            customer.save()
            updated += 1
            print(f'تم تحديث رقم العميل {customer.name}: {old_phone} → {phone}')
    print(f'تم تحديث {updated} رقم هاتف.')

if __name__ == "__main__":
    main()
