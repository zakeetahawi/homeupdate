#!/usr/bin/env python3
"""
تحقق بسيط من الإعدادات
"""

import os
import django
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def main():
    """التحقق البسيط"""
    print("🔍 التحقق من الإعدادات...")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        
        config = GoogleDriveConfig.get_active_config()
        if not config:
            print("❌ لا توجد إعدادات نشطة")
            return
            
        print(f"✅ الإعدادات النشطة:")
        print(f"   📁 مجلد المعاينات: {config.inspections_folder_id}")
        print(f"   📄 مجلد العقود: {config.contracts_folder_id}")
        
        # التحقق من أن المعرف صحيح
        if config.inspections_folder_id == "1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv":
            print("✅ مجلد المعاينات صحيح!")
        else:
            print(f"❌ مجلد المعاينات خاطئ")
            return
        
        print("\n🎉 النظام مُعد بشكل صحيح!")
        print("✅ جميع الرفعات الجديدة ستذهب للمجلد الصحيح")
        print("📁 الرابط: https://drive.google.com/drive/folders/1FiMh_6elODXGCrWOyTNr7IHrto2y0Skv")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    main()
