#!/usr/bin/env python
"""
سكريبت لإنشاء مستخدم مشرف افتراضي
"""
import os
import sys
import django

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# تكوين Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib.auth import get_user_model

def create_admin_user():
    User = get_user_model()
    
    # حذف المستخدم إذا كان موجوداً
    if User.objects.filter(username='admin').exists():
        User.objects.filter(username='admin').delete()
        print("تم حذف المستخدم admin الموجود مسبقاً")
    
    # إنشاء المستخدم الجديد
    user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )
    
    print(f"تم إنشاء المستخدم المشرف: {user.username}")
    print(f"البريد الإلكتروني: {user.email}")
    print("كلمة المرور: admin123")
    print("يمكنك الآن تسجيل الدخول باستخدام هذه البيانات")

if __name__ == "__main__":
    create_admin_user()
