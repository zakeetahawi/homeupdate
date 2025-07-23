#!/usr/bin/env python
"""
سكريبت لضبط تواريخ المعاينات - PostgreSQL
"""

import os
import sys
import django
from datetime import timedelta

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')

# تحديث إعدادات قاعدة البيانات لاستخدام PostgreSQL
os.environ['DATABASE_URL'] = 'postgres://postgres:5525@localhost:5432/crm_system'

# إعداد Django مع قاعدة البيانات الصحيحة
django.setup()

# تحديث إعدادات Django لاستخدام PostgreSQL
from django.conf import settings
settings.DATABASES['default'] = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'crm_system',
    'USER': 'postgres',
    'PASSWORD': '5525',
    'HOST': 'localhost',
    'PORT': '5432',
}

from inspections.models import Inspection
from django.utils import timezone
from django.db import transaction

def check_database_connection():
    """التحقق من الاتصال بقاعدة البيانات"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                print("✅ تم الاتصال بقاعدة البيانات PostgreSQL بنجاح")
                return True
    except Exception as e:
        print(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        return False

def check_tables():
    """التحقق من وجود الجداول"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%inspection%'
            """)
            tables = cursor.fetchall()
            print(f"الجداول الموجودة المتعلقة بالمعاينات: {[table[0] for table in tables]}")
            return len(tables) > 0
    except Exception as e:
        print(f"خطأ في فحص الجداول: {e}")
        return False

def quick_fix():
    """تصحيح سريع لل��واريخ"""
    
    print("فحص الاتصال بقاعدة البيانات...")
    if not check_database_connection():
        return
    
    print("فحص وجود الجداول...")
    if not check_tables():
        print("❌ جداول المعاينات غير موجودة")
        return
    
    print("البحث عن المعاينات التي تحتاج تصحيح...")
    
    try:
        # البحث عن المعاينات التي تاريخ تنفيذها = تاريخ الطلب + يوم واحد
        inspections_to_fix = []
        
        total_inspections = Inspection.objects.count()
        print(f"إجمالي المعاينات في قاعدة البيانات: {total_inspections}")
        
        for inspection in Inspection.objects.filter(
            scheduled_date__isnull=False,
            request_date__isnull=False
        ):
            # التحقق من أن تاريخ التنفيذ = تاريخ الطلب + يوم واحد
            expected_wrong_date = inspection.request_date + timedelta(days=1)
            if inspection.scheduled_date == expected_wrong_date:
                inspections_to_fix.append(inspection)
        
        print(f"تم العثور على {len(inspections_to_fix)} معاينة تحتاج تصحيح")
        
        if inspections_to_fix:
            print("\nالمعاينات التي ستتم تصحيحها:")
            for i, inspection in enumerate(inspections_to_fix[:5], 1):
                print(f"{i}. معاينة {inspection.contract_number or inspection.id}: "
                      f"{inspection.scheduled_date} → {inspection.request_date + timedelta(days=2)}")
            
            if len(inspections_to_fix) > 5:
                print(f"... و {len(inspections_to_fix) - 5} معاينة أخرى")
            
            response = input("\nهل تريد المتابعة؟ (y/n): ")
            if response.lower() in ['y', 'yes', 'نعم']:
                with transaction.atomic():
                    for inspection in inspections_to_fix:
                        old_date = inspection.scheduled_date
                        new_date = inspection.request_date + timedelta(days=2)
                        
                        inspection.scheduled_date = new_date
                        inspection.save(update_fields=['scheduled_date'])
                        
                        print(f"✓ معاينة {inspection.contract_number or inspection.id}: {old_date} → {new_date}")
                
                print(f"\n✅ تم تصحيح {len(inspections_to_fix)} معاينة بنجاح!")
            else:
                print("تم إلغاء العملية")
        else:
            print("✅ جميع التواريخ صحيحة!")
            
    except Exception as e:
        print(f"❌ خطأ أثناء معالجة المعاينات: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("سكريبت ضبط تواريخ المعاينات - PostgreSQL")
    print("="*50)
    quick_fix()