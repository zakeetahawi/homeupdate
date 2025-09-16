#!/usr/bin/env python3
"""
فحص المعاينة 5059 التي تسبب مشاكل timeout
"""

import os
import sys
import django

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inspections.models import Inspection

def check_inspection_5059():
    """فحص المعاينة المشكلة"""
    print("🔍 فحص المعاينة 5059...")
    
    try:
        inspection = Inspection.objects.get(id=5059)
        
        print(f"📋 معلومات المعاينة:")
        print(f"   - المعرف: {inspection.id}")
        print(f"   - التاريخ: {inspection.created_at}")
        print(f"   - الملف: {inspection.inspection_file}")
        print(f"   - Google Drive ID: {inspection.google_drive_file_id}")
        
        if inspection.inspection_file:
            file_path = inspection.inspection_file.path
            print(f"   - مسار الملف: {file_path}")
            print(f"   - الملف موجود: {os.path.exists(file_path)}")
            
            if not os.path.exists(file_path):
                print("🗑️ إزالة مسار الملف المفقود...")
                inspection.inspection_file = None
                inspection.save()
                print("✅ تم إزالة مسار الملف المفقود")
            else:
                print(f"   - حجم الملف: {os.path.getsize(file_path)} bytes")
        else:
            print("   - لا يوجد ملف مرتبط")
            
        if inspection.google_drive_file_id:
            print("✅ المعاينة مرفوعة على Google Drive بالفعل")
        else:
            print("⚠️ المعاينة لم ترفع على Google Drive بعد")
            
    except Inspection.DoesNotExist:
        print("❌ المعاينة 5059 غير موجودة")
    except Exception as e:
        print(f"❌ خطأ في فحص المعاينة: {e}")

if __name__ == "__main__":
    check_inspection_5059()
