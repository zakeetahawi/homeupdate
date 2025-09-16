#!/usr/bin/env python3
"""
مشاركة سريعة لمجلدات Google Drive
"""

import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def quick_share_inspections_folder():
    """مشاركة سريعة لمجلد المعاينات مع الجميع"""
    print("🌐 مشاركة مجلد المعاينات مع الجميع...")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        from inspections.services.google_drive_service import GoogleDriveService
        
        # الحصول على ID المجلد
        config = GoogleDriveConfig.objects.first()
        if not config or not config.inspections_folder_id:
            print("❌ لا يوجد مجلد معاينات محدد")
            return False
        
        folder_id = config.inspections_folder_id
        service = GoogleDriveService()
        
        # إنشاء صلاحية عامة للقراءة
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        
        result = service.service.permissions().create(
            fileId=folder_id,
            body=permission
        ).execute()
        
        print(f"✅ تم مشاركة مجلد المعاينات بنجاح!")
        print(f"🔗 رابط المجلد: https://drive.google.com/drive/folders/{folder_id}")
        
        return True
        
    except Exception as e:
        if "Permission already exists" in str(e):
            print("✅ المجلد مشترك بالفعل!")
            print(f"🔗 رابط المجلد: https://drive.google.com/drive/folders/{folder_id}")
            return True
        else:
            print(f"❌ خطأ في المشاركة: {e}")
            return False

def show_folder_links():
    """عرض روابط المجلدات"""
    print("\n🔗 روابط مجلدات Google Drive:")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        
        config = GoogleDriveConfig.objects.first()
        if not config:
            print("❌ لا توجد إعدادات")
            return
        
        if config.inspections_folder_id:
            print(f"📁 المعاينات: https://drive.google.com/drive/folders/{config.inspections_folder_id}")
        
        if config.contracts_folder_id:
            print(f"📄 العقود: https://drive.google.com/drive/folders/{config.contracts_folder_id}")
            
    except Exception as e:
        print(f"❌ خطأ: {e}")

def main():
    """الدالة الرئيسية"""
    print("🚀 مشاركة سريعة لمجلدات Google Drive")
    print("=" * 50)
    
    # مشاركة مجلد المعاينات
    success = quick_share_inspections_folder()
    
    # عرض الروابط
    show_folder_links()
    
    if success:
        print("\n🎉 تم! يمكنك الآن الوصول لمجلد المعاينات")
        print("💡 انسخ الرابط أعلاه وافتحه في المتصفح")
    else:
        print("\n❌ فشلت المشاركة - قد تحتاج لمشاركة يدوية")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
