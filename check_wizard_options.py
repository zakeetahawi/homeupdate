#!/usr/bin/env python
"""فحص جميع خيارات الحقول في نظام تخصيص الويزارد"""

import os
import sys
import django

# إعداد Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.wizard_customization_models import WizardFieldOption

print('=' * 60)
print('جميع خيارات الحقول في نظام تخصيص الويزارد')
print('=' * 60)

field_types = [
    'tailoring_type',
    'installation_type', 
    'payment_method',
    'order_status',
    'service_type'
]

for ft in field_types:
    opts = WizardFieldOption.get_active_options(ft)
    ft_name = dict(WizardFieldOption.FIELD_TYPE_CHOICES)[ft]
    
    print(f'\n{ft_name}:')
    print(f'  عدد الخيارات: {opts.count()}')
    
    for opt in opts:
        default_mark = ' [افتراضي]' if opt.is_default else ''
        print(f'  - {opt.display_name} ({opt.value}){default_mark}')

print('\n' + '=' * 60)
total = WizardFieldOption.objects.filter(is_active=True).count()
print(f'إجمالي الخيارات النشطة: {total}')
print('=' * 60)
