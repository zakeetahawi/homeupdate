#!/usr/bin/env python
"""
سكريبت لفحص كيفية عرض نتائج المعاينة في النظام
"""
import os
import sys
import django
from django.utils import timezone

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from inspections.models import Inspection

def debug_inspection_results():
    """فحص كيفية عرض نتائج المعاينة"""
    print("🔍 فحص نتائج المعاينة...")
    
    # الحصول على بعض المعاينات المكتملة
    completed_inspections = Inspection.objects.filter(status='completed')[:5]
    
    print(f"📊 عدد المعاينات المكتملة: {completed_inspections.count()}")
    print("\n" + "="*50)
    
    for inspection in completed_inspections:
        print(f"\n🔸 معاينة رقم: {inspection.id}")
        print(f"   رقم العقد: {inspection.contract_number}")
        print(f"   الحالة: {inspection.status}")
        print(f"   النتيجة (القيمة الخام): {inspection.result}")
        print(f"   النتيجة (المعروضة): {inspection.get_result_display()}")
        print(f"   العميل: {inspection.customer}")
        print(f"   تاريخ الإكمال: {inspection.completed_at}")
        print("-" * 30)
    
    # فحص خيارات النتيجة المتاحة
    print("\n📋 خيارات النتيجة المتاحة:")
    for choice in Inspection.RESULT_CHOICES:
        print(f"   {choice[0]} -> {choice[1]}")
    
    # فحص إعدادات اللغة
    from django.conf import settings
    print(f"\n🌐 إعدادات اللغة:")
    print(f"   LANGUAGE_CODE: {settings.LANGUAGE_CODE}")
    print(f"   USE_I18N: {settings.USE_I18N}")
    
    # اختبار الترجمة مباشرة
    from django.utils.translation import gettext_lazy as _
    print(f"\n🔤 اختبار الترجمة:")
    print(f"   _('ناجحة'): {_('ناجحة')}")
    print(f"   _('غير مجدية'): {_('غير مجدية')}")

if __name__ == "__main__":
    debug_inspection_results()