#!/usr/bin/env python3
"""
سكريبت لاختبار عرض معلومات المستودع
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from inventory.models import Warehouse
from django.contrib.auth.models import User

def test_warehouse_info():
    """اختبار عرض معلومات المستودع"""
    print("🔍 اختبار عرض معلومات المستودع")
    print("=" * 50)
    
    # الحصول على أول مستودع
    warehouse = Warehouse.objects.first()
    if not warehouse:
        print("❌ لا توجد مستودعات في النظام")
        return
    
    print(f"📦 المستودع: {warehouse.name}")
    print(f"🔢 الرمز: {warehouse.code}")
    print(f"🏢 الفرع: {warehouse.branch.name if warehouse.branch else 'جميع الفروع'}")
    print(f"👤 المدير: {warehouse.manager.get_full_name() if warehouse.manager else 'غير محدد'}")
    print(f"📍 العنوان: {warehouse.address or 'غير محدد'}")
    print(f"📅 تاريخ الإنشاء: {warehouse.created_date_display}")
    print(f"🔄 آخر تعديل: {warehouse.updated_date_display}")
    print(f"👨‍💼 تم إنشاؤه بواسطة: {warehouse.created_by_name}")
    print(f"✅ الحالة: {'نشط' if warehouse.is_active else 'غير نشط'}")
    
    print("\n" + "=" * 50)
    print("✅ تم اختبار عرض معلومات المستودع بنجاح")

if __name__ == "__main__":
    test_warehouse_info() 