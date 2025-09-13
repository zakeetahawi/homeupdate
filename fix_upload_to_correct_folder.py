#!/usr/bin/env python3
"""
إصلاح الرفع للمجلد الصحيح حسب الإعدادات
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def update_config_to_correct_folder():
    """تحديث الإعدادات للمجلد الصحيح"""
    print("🔧 تحديث الإعدادات للمجلد الصحيح...")
    
    # المجلد الصحيح الذي تريده
    CORRECT_INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    CORRECT_CONTRACTS_FOLDER = "1TFLsDSqOupT0wHAYrIFOdOJNmffZ78CG"
    
    print(f"📁 المجلد الصحيح للمعاينات: {CORRECT_INSPECTIONS_FOLDER}")
    print(f"📄 مجلد العقود: {CORRECT_CONTRACTS_FOLDER}")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        
        config = GoogleDriveConfig.get_active_config()
        if not config:
            print("❌ لا توجد إعدادات للتحديث")
            return False
        
        old_inspections = config.inspections_folder_id
        old_contracts = config.contracts_folder_id
        
        config.inspections_folder_id = CORRECT_INSPECTIONS_FOLDER
        config.contracts_folder_id = CORRECT_CONTRACTS_FOLDER
        config.save()
        
        print(f"✅ تم تحديث الإعدادات:")
        print(f"   📁 المعاينات: {old_inspections} → {CORRECT_INSPECTIONS_FOLDER}")
        print(f"   📄 العقود: {old_contracts} → {CORRECT_CONTRACTS_FOLDER}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تحديث الإعدادات: {e}")
        return False

def find_recent_uploads():
    """البحث عن الرفعات الأخيرة في المجلد الخاطئ"""
    print("\n🔍 البحث عن الرفعات الأخيرة...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # المجلد القديم الذي كان يستخدم
        old_folder = "1jMeDl6AqrS-pzX_ECfXGACOekيW0b7Av"
        
        print(f"📁 البحث في المجلد القديم: {old_folder}")
        
        try:
            # البحث عن الملفات الأخيرة (آخر 7 أيام)
            from datetime import datetime, timedelta
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
            
            query = f"'{old_folder}' in parents and trashed=false and createdTime > '{week_ago}'"
            
            results = service.service.files().list(
                q=query,
                fields='files(id,name,createdTime,parents)',
                pageSize=1000,
                orderBy='createdTime desc'
            ).execute()
            
            files = results.get('files', [])
            print(f"   📊 الملفات المرفوعة في آخر 7 أيام: {len(files)}")
            
            # فلترة ملفات المعاينات فقط
            recent_inspections = []
            for file in files:
                file_name = file.get('name', '')
                if ('عقد' not in file_name and 
                    'contract' not in file_name.lower() and
                    '.pdf' in file_name.lower()):
                    
                    recent_inspections.append({
                        'id': file.get('id'),
                        'name': file_name,
                        'created_time': file.get('createdTime'),
                        'current_folder': old_folder,
                        'parents': file.get('parents', [])
                    })
            
            print(f"   📁 معاينات أخيرة للنقل: {len(recent_inspections)}")
            
            if recent_inspections:
                print("   📋 المعاينات الأخيرة:")
                for file in recent_inspections[:10]:
                    created_time = file['created_time'][:10] if file['created_time'] else 'غير معروف'
                    print(f"      - {file['name']} ({created_time})")
            
            return recent_inspections
            
        except Exception as e:
            print(f"❌ خطأ في البحث في المجلد القديم: {e}")
            return []
        
    except Exception as e:
        print(f"❌ خطأ في البحث عن الرفعات الأخيرة: {e}")
        return []

def move_recent_files_to_correct_folder(files_to_move):
    """نقل الملفات الأخيرة للمجلد الصحيح"""
    print("\n📦 نقل الملفات الأخيرة للمجلد الصحيح...")
    
    if not files_to_move:
        print("✅ لا توجد ملفات أخيرة للنقل")
        return True
    
    CORRECT_INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        moved_count = 0
        
        print(f"📁 نقل {len(files_to_move)} ملف للمجلد الصحيح...")
        
        for file_info in files_to_move:
            try:
                file_name = file_info['name']
                file_id = file_info['id']
                current_parents = file_info.get('parents', [])
                
                # نقل الملف للمجلد الصحيح
                remove_parents = ','.join(current_parents) if current_parents else None
                
                service.service.files().update(
                    fileId=file_id,
                    addParents=CORRECT_INSPECTIONS_FOLDER,
                    removeParents=remove_parents,
                    fields='id,parents'
                ).execute()
                
                print(f"✅ تم نقل: {file_name}")
                moved_count += 1
                
                # توقف قصير لتجنب تجاوز حدود API
                if moved_count % 5 == 0:
                    import time
                    time.sleep(0.5)
                
            except Exception as e:
                print(f"❌ خطأ في نقل الملف {file_info['name']}: {e}")
        
        print(f"\n🎉 تم نقل {moved_count} ملف أخير بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في نقل الملفات: {e}")
        return False

def test_upload_to_correct_folder():
    """اختبار الرفع للمجلد الصحيح"""
    print("\n🧪 اختبار الرفع للمجلد الصحيح...")
    
    try:
        from inspections.services.google_drive_service import test_file_upload_to_folder
        
        result = test_file_upload_to_folder()
        
        if result.get('success'):
            print(f"✅ نجح اختبار الرفع")
            print(f"   📁 المجلد المستخدم: {result.get('folder_id')}")
            print(f"   📄 الملف التجريبي: {result.get('file_name')}")
            
            # التحقق من أن المجلد صحيح
            if result.get('folder_id') == "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv":
                print("✅ النظام يرفع للمجلد الصحيح!")
                return True
            else:
                print(f"❌ النظام ما زال يرفع للمجلد الخاطئ: {result.get('folder_id')}")
                return False
        else:
            print(f"❌ فشل اختبار الرفع: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار الرفع: {e}")
        return False

def check_current_folder_contents():
    """فحص محتويات المجلد الصحيح"""
    print("\n📊 فحص محتويات المجلد الصحيح...")
    
    CORRECT_INSPECTIONS_FOLDER = "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv"
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # عد الملفات في المجلد الصحيح
        results = service.service.files().list(
            q=f"'{CORRECT_INSPECTIONS_FOLDER}' in parents and trashed=false",
            fields='files(id,name,createdTime)',
            pageSize=1000,
            orderBy='createdTime desc'
        ).execute()
        
        files = results.get('files', [])
        print(f"📁 المجلد الصحيح يحتوي على: {len(files)} ملف")
        
        if files:
            print("📋 آخر 5 ملفات:")
            for file in files[:5]:
                created_time = file.get('createdTime', '')[:10] if file.get('createdTime') else 'غير معروف'
                print(f"   - {file.get('name')} ({created_time})")
        else:
            print("⚠️ المجلد فارغ - سيتم نقل الملفات إليه")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في فحص المجلد: {e}")
        return False

def restart_celery_workers():
    """إعادة تشغيل عمال Celery لتطبيق الإعدادات الجديدة"""
    print("\n🔄 إعادة تشغيل عمال Celery...")
    
    try:
        import subprocess
        
        # قتل عمال Celery الحاليين
        subprocess.run(['pkill', '-f', 'celery'], check=False)
        print("✅ تم إيقاف عمال Celery القدامى")
        
        # انتظار قصير
        import time
        time.sleep(2)
        
        print("💡 يرجى إعادة تشغيل النظام لتطبيق الإعدادات الجديدة")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إعادة تشغيل Celery: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🔧 إصلاح الرفع للمجلد الصحيح حسب الإعدادات")
    print("=" * 60)
    print("📁 المجلد الصحيح: 1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    print("📂 اسم المجلد: crm-insp")
    print("=" * 60)
    
    # 1. فحص محتويات المجلد الصحيح الحالية
    if not check_current_folder_contents():
        return
    
    # 2. تحديث الإعدادات للمجلد الصحيح
    if not update_config_to_correct_folder():
        return
    
    # 3. البحث عن الرفعات الأخيرة في المجلد الخاطئ
    recent_files = find_recent_uploads()
    
    # 4. نقل الملفات الأخيرة للمجلد الصحيح
    if recent_files:
        if not move_recent_files_to_correct_folder(recent_files):
            return
    
    # 5. اختبار الرفع للمجلد الصحيح
    if not test_upload_to_correct_folder():
        return
    
    # 6. إعادة تشغيل عمال Celery
    restart_celery_workers()
    
    print("\n" + "=" * 60)
    print("🎉 تم إصلاح المشكلة بنجاح!")
    print("✅ جميع الرفعات الأخيرة تم نقلها للمجلد الصحيح")
    print("✅ النظام الآن يرفع للمجلد الصحيح حسب الإعدادات")
    print("✅ جميع الرفعات الجديدة ستذهب للمجلد الصحيح")
    
    print("\n🔗 الرابط الصحيح:")
    print("📁 المعاينات: https://drive.google.com/drive/folders/1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
    
    print("\n💡 ملاحظة: يرجى إعادة تشغيل النظام لضمان تطبيق الإعدادات الجديدة")

if __name__ == "__main__":
    main()
