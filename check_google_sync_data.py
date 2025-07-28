#!/usr/bin/env python
"""
سكريبت فحص بيانات Google Sync الموجودة
Quick check for existing Google Sync data
"""

import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

def check_google_sync_data():
    """فحص بيانات Google Sync الموجودة"""
    
    print("🔍 فحص بيانات Google Sync الموجودة")
    print("=" * 50)
    
    try:
        # فحص تعيينات Google Sheets
        from odoo_db_manager.google_sync_advanced import GoogleSheetMapping, GoogleSyncTask
        
        mappings = GoogleSheetMapping.objects.all()
        print(f"\n📋 تعيينات Google Sheets: {mappings.count()}")
        
        if mappings.exists():
            print("  التعيينات الموجودة:")
            for mapping in mappings:
                status = "نشط" if mapping.is_active else "غير نشط"
                print(f"    - {mapping.name} ({status})")
                print(f"      معرف الجدول: {mapping.spreadsheet_id}")
                print(f"      اسم الورقة: {mapping.sheet_name}")
                print(f"      آخر مزامنة: {mapping.last_sync or 'لم تتم مزامنة'}")
                
                # فحص تعيينات الأعمدة
                column_mappings = mapping.get_column_mappings()
                if column_mappings:
                    print(f"      تعيينات الأعمدة: {len(column_mappings)} عمود")
                    for col, field in list(column_mappings.items())[:3]:  # أول 3 فقط
                        print(f"        {col} -> {field}")
                    if len(column_mappings) > 3:
                        print(f"        ... و {len(column_mappings) - 3} تعيين آخر")
                else:
                    print("      تعيينات الأعمدة: غير محددة")
                print()
        else:
            print("  ⚠️ لا توجد تعيينات Google Sheets")
        
        # فحص مهام المزامنة
        tasks = GoogleSyncTask.objects.all().order_by('-created_at')[:5]
        print(f"\n📝 مهام المزامنة: {GoogleSyncTask.objects.count()} (آخر 5)")
        
        if tasks.exists():
            for task in tasks:
                print(f"    - {task.get_task_type_display()}: {task.status}")
                print(f"      التعيين: {task.mapping.name}")
                print(f"      تاريخ الإنشاء: {task.created_at}")
                if task.rows_processed > 0:
                    print(f"      الصفوف المعالجة: {task.rows_processed}")
                print()
        else:
            print("  ⚠️ لا توجد مهام مزامنة")
            
    except ImportError as e:
        print(f"❌ خطأ في استيراد نماذج Google Sync: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ خطأ في فحص تعيينات Google Sheets: {str(e)}")
    
    try:
        # فحص إعدادات Google Drive
        from odoo_db_manager.models import GoogleDriveConfig
        
        drive_config = GoogleDriveConfig.get_active_config()
        print(f"\n🗂️ إعدادات Google Drive:")
        
        if drive_config:
            print(f"    الاسم: {drive_config.name}")
            print(f"    نشط: {'نعم' if drive_config.is_active else 'لا'}")
            print(f"    ملف الاعتماد: {'موجود' if drive_config.credentials_file else 'غير موجود'}")
            print(f"    مجلد الجذر: {drive_config.root_folder_id or 'غير محدد'}")
        else:
            print("  ⚠️ لا توجد إعدادات Google Drive نشطة")
            
    except ImportError as e:
        print(f"❌ خطأ في استيراد نماذج Google Drive: {str(e)}")
    except Exception as e:
        print(f"❌ خطأ في فحص إعدادات Google Drive: {str(e)}")
    
    try:
        # فحص إعدادات Google Sheets القديمة
        from odoo_db_manager.models import GoogleSheetsConfig
        
        sheets_configs = GoogleSheetsConfig.objects.all()
        print(f"\n📊 إعدادات Google Sheets القديمة: {sheets_configs.count()}")
        
        if sheets_configs.exists():
            for config in sheets_configs:
                print(f"    - {config.name}")
                print(f"      معرف الجدول: {config.spreadsheet_id}")
                print(f"      نشط: {'نعم' if config.is_active else 'لا'}")
        else:
            print("  ⚠️ لا توجد إعدادات Google Sheets قديمة")
            
    except ImportError as e:
        print(f"❌ خطأ في استيراد نماذج Google Sheets: {str(e)}")
    except Exception as e:
        print(f"❌ خطأ في فحص إعدادات Google Sheets: {str(e)}")
    
    # فحص التطبيقات المُثبتة
    print(f"\n🔧 فحص التطبيقات:")
    
    from django.apps import apps
    
    try:
        app_config = apps.get_app_config('odoo_db_manager')
        print(f"    ✅ تطبيق odoo_db_manager مُثبت")
        print(f"       المسار: {app_config.path}")
        
        # فحص النماذج المتاحة
        models = app_config.get_models()
        model_names = [model._meta.model_name for model in models]
        print(f"       النماذج المتاحة: {len(model_names)}")
        
        google_models = [name for name in model_names if 'google' in name.lower()]
        if google_models:
            print(f"       نماذج Google: {', '.join(google_models)}")
        else:
            print(f"       نماذج Google: غير موجودة")
            
    except Exception as e:
        print(f"    ❌ مشكلة في تطبيق odoo_db_manager: {str(e)}")
    
    print("\n" + "=" * 50)
    print("✅ انتهى فحص بيانات Google Sync")

if __name__ == "__main__":
    check_google_sync_data()