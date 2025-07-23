#!/usr/bin/env python
"""
اختبار الاتصال بقاعدة البيانات PostgreSQL
"""

import os
import sys
import django

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')

# تحديث إعدادات قاعدة البيانات
os.environ['DATABASE_URL'] = 'postgres://postgres:5525@localhost:5432/crm_system'

django.setup()

# تحديث إعدادات Django
from django.conf import settings
settings.DATABASES['default'] = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'crm_system',
    'USER': 'postgres',
    'PASSWORD': '5525',
    'HOST': 'localhost',
    'PORT': '5432',
}

def test_connection():
    """اختبار الاتصال بقاعدة البيانات"""
    try:
        from django.db import connection
        print("محاولة الاتصال بقاعدة البيانات PostgreSQL...")
        print(f"قاعدة البيانات: {settings.DATABASES['default']['NAME']}")
        print(f"المضيف: {settings.DATABASES['default']['HOST']}:{settings.DATABASES['default']['PORT']}")
        print(f"المستخدم: {settings.DATABASES['default']['USER']}")
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"✅ تم الاتصال بنجاح!")
            print(f"إصدار PostgreSQL: {version}")
            
            # فحص الجداول
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            print(f"\nعدد الجداول الموجودة: {len(tables)}")
            
            # البحث عن جداول المعاينات
            inspection_tables = [table[0] for table in tables if 'inspection' in table[0].lower()]
            print(f"جداول المعاينات: {inspection_tables}")
            
            if inspection_tables:
                # فحص عدد المعاينات
                cursor.execute("SELECT COUNT(*) FROM inspections_inspection")
                count = cursor.fetchone()[0]
                print(f"عدد المعاينات في قاعدة البيانات: {count}")
                
                if count > 0:
                    # عرض عينة من المعاينات
                    cursor.execute("""
                        SELECT id, contract_number, request_date, scheduled_date, status
                        FROM inspections_inspection 
                        LIMIT 5
                    """)
                    inspections = cursor.fetchall()
                    print("\nعينة من المعاينات:")
                    for insp in inspections:
                        print(f"  ID: {insp[0]}, العقد: {insp[1]}, طلب: {insp[2]}, تنفيذ: {insp[3]}, حالة: {insp[4]}")
            
            return True
            
    except Exception as e:
        print(f"❌ فشل الاتصال: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_connection()