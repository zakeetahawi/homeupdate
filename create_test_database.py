#!/usr/bin/env python3
"""
سكريبت لإنشاء قاعدة بيانات تجريبية للاختبار
"""

import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from odoo_db_manager.models import Database

User = get_user_model()

def create_test_database():
    """إنشاء قاعدة بيانات تجريبية"""
    
    print("🔍 إنشاء قاعدة بيانات تجريبية...")
    
    # إنشاء قاعدة بيانات تجريبية
    database, created = Database.objects.get_or_create(
        name='test_restore_db',
        defaults={
            'db_type': 'postgresql',
            'connection_info': {
                'HOST': 'localhost',
                'PORT': '5432',
                'NAME': 'test_restore_db',
                'USER': 'postgres',
                'PASSWORD': 'password'
            },
            'is_active': True,
            'status': True
        }
    )
    
    if created:
        print(f"✅ تم إنشاء قاعدة البيانات: {database.name}")
    else:
        print(f"✅ قاعدة البيانات موجودة: {database.name}")
    
    print(f"📊 معرف قاعدة البيانات: {database.id}")
    print(f"🌐 يمكنك الآن اختبار الاستعادة على: http://localhost:8000/odoo-db-manager/backups/upload/{database.id}/")
    
    return database

if __name__ == '__main__':
    create_test_database() 