#!/usr/bin/env python
import os
import sys
import django

# إعداد Django
sys.path.append('/home/xhunterx/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from complaints.models import ResolutionMethod

# إنشاء طرق حل افتراضية
methods = [
    {'name': 'استبدال المنتج', 'description': 'استبدال المنتج المعيب بآخر جديد'},
    {'name': 'إصلاح المنتج', 'description': 'إصلاح العيب في المنتج الحالي'},
    {'name': 'استرداد المبلغ', 'description': 'استرداد كامل أو جزئي للمبلغ المدفوع'},
    {'name': 'خصم على الطلب التالي', 'description': 'تقديم خصم للعميل على الطلب القادم'},
    {'name': 'تعويض مالي', 'description': 'تقديم تعويض مالي للعميل'},
    {'name': 'إعادة التركيب', 'description': 'إعادة تركيب المنتج بشكل صحيح'},
    {'name': 'تدريب الفريق', 'description': 'تدريب الفريق لتجنب تكرار المشكلة'},
    {'name': 'تحسين العملية', 'description': 'تحسين العملية الداخلية لمنع تكرار المشكلة'},
]

print("إنشاء طرق الحل...")
for i, method_data in enumerate(methods, 1):
    method, created = ResolutionMethod.objects.get_or_create(
        name=method_data['name'],
        defaults={
            'description': method_data['description'],
            'order': i * 10,
            'is_active': True
        }
    )
    if created:
        print(f"✅ تم إنشاء طريقة الحل: {method.name}")
    else:
        print(f"⚠️ طريقة الحل موجودة بالفعل: {method.name}")

print(f"\n🎉 إجمالي طرق الحل: {ResolutionMethod.objects.count()}")
