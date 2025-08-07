#!/usr/bin/env python3
"""
سكريبت لإنشاء مستودع تجريبي مع معلومات كاملة
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from inventory.models import Warehouse
from accounts.models import Branch
from django.contrib.auth.models import User

def create_test_warehouse():
    """إنشاء مستودع تجريبي"""
    print("🏗️ إنشاء مستودع تجريبي")
    print("=" * 50)
    
    # الحصول على أول فرع ومستخدم
    branch = Branch.objects.first()
    user = User.objects.first()
    
    if not branch:
        print("❌ لا توجد فروع في النظام")
        return
    
    if not user:
        print("❌ لا توجد مستخدمين في النظام")
        return
    
    # إنشاء مستودع جديد
    warehouse_data = {
        'name': 'مستودع تجريبي',
        'code': 'TEST001',
        'branch': branch,
        'manager': user,
        'address': 'شارع التجربة، مدينة الاختبار',
        'notes': 'مستودع تم إنشاؤه للاختبار',
        'is_active': True,
        'created_by': user
    }
    
    # التحقق من عدم وجود رمز مكرر
    if Warehouse.objects.filter(code=warehouse_data['code']).exists():
        print("⚠️ رمز المستودع موجود بالفعل، سيتم استخدام رمز مختلف")
        warehouse_data['code'] = 'TEST002'
    
    try:
        warehouse = Warehouse.objects.create(**warehouse_data)
        print(f"✅ تم إنشاء المستودع بنجاح: {warehouse.name}")
        print(f"📦 المستودع: {warehouse.name}")
        print(f"🔢 الرمز: {warehouse.code}")
        print(f"🏢 الفرع: {warehouse.branch.name}")
        print(f"👤 المدير: {warehouse.manager.get_full_name()}")
        print(f"📍 العنوان: {warehouse.address}")
        print(f"📅 تاريخ الإنشاء: {warehouse.created_date_display}")
        print(f"🔄 آخر تعديل: {warehouse.updated_date_display}")
        print(f"👨‍💼 تم إنشاؤه بواسطة: {warehouse.created_by_name}")
        print(f"✅ الحالة: {'نشط' if warehouse.is_active else 'غير نشط'}")
        
        print("\n" + "=" * 50)
        print("✅ تم إنشاء المستودع التجريبي بنجاح")
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء المستودع: {str(e)}")

if __name__ == "__main__":
    create_test_warehouse() 