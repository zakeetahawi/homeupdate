#!/usr/bin/env python3
"""
مشاركة مجلدات Google Drive مع المستخدم
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def share_folder_with_user(folder_id, user_email, folder_name):
    """مشاركة مجلد مع مستخدم محدد"""
    print(f"🔧 مشاركة مجلد {folder_name} مع {user_email}...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # إنشاء صلاحية جديدة
        permission = {
            'type': 'user',
            'role': 'writer',  # صلاحية كتابة
            'emailAddress': user_email
        }
        
        # تطبيق الصلاحية
        result = service.service.permissions().create(
            fileId=folder_id,
            body=permission,
            sendNotificationEmail=True,
            emailMessage=f'تم مشاركة مجلد {folder_name} معك من نظام CRM'
        ).execute()
        
        print(f"✅ تم مشاركة المجلد بنجاح!")
        print(f"🔗 ID الصلاحية: {result.get('id')}")
        print(f"📧 تم إرسال إشعار بالبريد الإلكتروني")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في المشاركة: {e}")
        return False

def share_folder_with_anyone(folder_id, folder_name):
    """مشاركة مجلد مع أي شخص لديه الرابط"""
    print(f"🌐 مشاركة مجلد {folder_name} مع أي شخص لديه الرابط...")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        # إنشاء صلاحية عامة
        permission = {
            'type': 'anyone',
            'role': 'reader'  # صلاحية قراءة فقط
        }
        
        # تطبيق الصلاحية
        result = service.service.permissions().create(
            fileId=folder_id,
            body=permission
        ).execute()
        
        print(f"✅ تم مشاركة المجلد مع الجميع!")
        print(f"🔗 ID الصلاحية: {result.get('id')}")
        
        # الحصول على الرابط
        folder_info = service.service.files().get(
            fileId=folder_id,
            fields='webViewLink'
        ).execute()
        
        print(f"🌐 رابط المجلد: {folder_info.get('webViewLink')}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في المشاركة: {e}")
        return False

def get_folder_permissions(folder_id, folder_name):
    """عرض صلاحيات المجلد الحالية"""
    print(f"👥 صلاحيات مجلد {folder_name}:")
    
    try:
        from inspections.services.google_drive_service import GoogleDriveService
        
        service = GoogleDriveService()
        
        permissions = service.service.permissions().list(fileId=folder_id).execute()
        
        for i, perm in enumerate(permissions.get('permissions', []), 1):
            print(f"   {i}. النوع: {perm.get('type')}")
            print(f"      الدور: {perm.get('role')}")
            if perm.get('emailAddress'):
                print(f"      البريد: {perm.get('emailAddress')}")
            print(f"      ID: {perm.get('id')}")
            print()
            
    except Exception as e:
        print(f"❌ خطأ في عرض الصلاحيات: {e}")

def main():
    """الدالة الرئيسية"""
    print("🔧 مشاركة مجلدات Google Drive")
    print("=" * 50)
    
    # الحصول على إعدادات المجلدات
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        config = GoogleDriveConfig.objects.first()
        
        if not config:
            print("❌ لا توجد إعدادات Google Drive")
            return
            
        inspections_folder_id = config.inspections_folder_id
        contracts_folder_id = config.contracts_folder_id
        
    except Exception as e:
        print(f"❌ خطأ في الحصول على الإعدادات: {e}")
        return
    
    # عرض الصلاحيات الحالية
    print("\n📋 الصلاحيات الحالية:")
    get_folder_permissions(inspections_folder_id, "المعاينات")
    get_folder_permissions(contracts_folder_id, "العقود")
    
    # طلب بريد المستخدم
    print("\n📧 أدخل بريدك الإلكتروني لمشاركة المجلدات معك:")
    user_email = input("البريد الإلكتروني: ").strip()
    
    if user_email:
        print(f"\n🔧 مشاركة المجلدات مع {user_email}...")
        
        # مشاركة مجلد المعاينات
        if inspections_folder_id:
            share_folder_with_user(inspections_folder_id, user_email, "المعاينات")
        
        # مشاركة مجلد العقود (إذا لم يكن مشترك بالفعل)
        if contracts_folder_id:
            share_folder_with_user(contracts_folder_id, user_email, "العقود")
    
    # خيار المشاركة العامة
    print("\n🌐 هل تريد مشاركة المجلدات مع أي شخص لديه الرابط؟ (y/n)")
    public_share = input("الاختيار: ").strip().lower()
    
    if public_share in ['y', 'yes', 'نعم']:
        print("\n🌐 مشاركة عامة للمجلدات...")
        
        if inspections_folder_id:
            share_folder_with_anyone(inspections_folder_id, "المعاينات")
        
        if contracts_folder_id:
            share_folder_with_anyone(contracts_folder_id, "العقود")
    
    # عرض الصلاحيات الجديدة
    print("\n📋 الصلاحيات بعد التحديث:")
    get_folder_permissions(inspections_folder_id, "المعاينات")
    get_folder_permissions(contracts_folder_id, "العقود")
    
    print("\n" + "=" * 50)
    print("🎯 انتهت عملية المشاركة")
    
    # عرض الروابط النهائية
    print("\n🔗 روابط المجلدات:")
    print(f"📁 المعاينات: https://drive.google.com/drive/folders/{inspections_folder_id}")
    print(f"📄 العقود: https://drive.google.com/drive/folders/{contracts_folder_id}")

if __name__ == "__main__":
    main()
