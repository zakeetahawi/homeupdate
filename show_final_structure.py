#!/usr/bin/env python
"""عرض الهيكل النهائي للأقسام والوحدات"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from accounts.models import Department

print("\n" + "="*70)
print("🎯 الهيكل النهائي لأقسام ووحدات النظام")
print("="*70 + "\n")

departments = Department.objects.filter(parent=None).order_by('order')
total_units = 0

for dept in departments:
    children = Department.objects.filter(parent=dept).order_by('order')
    
    if children.exists():
        print(f"📁 {dept.name} ({dept.code})")
        total_units += children.count()
        
        for i, child in enumerate(children, 1):
            is_last = i == children.count()
            prefix = "└──" if is_last else "├──"
            
            # عرض حقول show_* المفعلة
            show_fields = []
            if child.show_customers:
                show_fields.append('عملاء')
            if child.show_orders:
                show_fields.append('طلبات')
            if child.show_inventory:
                show_fields.append('مخزون')
            if child.show_inspections:
                show_fields.append('معاينات')
            if child.show_installations:
                show_fields.append('تركيبات')
            if child.show_manufacturing:
                show_fields.append('مصنع')
            if child.show_complaints:
                show_fields.append('شكاوى')
            if child.show_reports:
                show_fields.append('تقارير')
            if child.show_accounting:
                show_fields.append('محاسبة')
            if child.show_database:
                show_fields.append('بيانات')
            
            show_text = f" [يظهر في: {', '.join(show_fields)}]" if show_fields else ""
            
            print(f"   {prefix} {child.name}{show_text}")
        print()

print("="*70)
print(f"📊 الإحصائيات:")
print(f"   • عدد الأقسام الرئيسية: {departments.count()}")
print(f"   • عدد الوحدات الفرعية: {total_units}")
print(f"   • المجموع الكلي: {departments.count() + total_units}")
print("="*70)
print(f"\n💡 الخطوات التالية:")
print(f"   1. افتح: http://localhost:8000/admin/accounts/department/")
print(f"   2. اختر أي وحدة وفعّل حقول 'عناصر القائمة الرئيسية'")
print(f"   3. بذلك ستظهر في القائمة الرئيسية للمستخدمين!")
print()
