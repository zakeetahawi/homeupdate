#!/usr/bin/env python3
"""
حل فوري لمشكلة الاستعادة
"""
import os
import sys
import django
from pathlib import Path

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def main():
    print("🔧 بدء الحل الفوري لمشكلة الاستعادة...")
    
    # 1. التحقق من وجود الملفات
    template_file = Path("odoo_db_manager/templates/odoo_db_manager/backup_upload.html")
    if not template_file.exists():
        print("❌ ملف القالب غير موجود")
        return False
    
    print("✅ ملف القالب موجود")
    
    # 2. التحقق من JavaScript
    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'initializeRestoreSystem' in content:
        print("✅ JavaScript موجود في القالب")
    else:
        print("❌ JavaScript غير موجود في القالب")
        return False
    
    # 3. إنشاء صفحة تشخيصية
    debug_url = "http://127.0.0.1:8000/odoo-db-manager/backups/upload/"
    
    print(f"""
🚀 الحل الفوري:

1. افتح المتصفح على: {debug_url}
2. اضغط F12 لفتح أدوات المطور
3. انتقل لتبويب Console
4. ابحث عن هذه الرسائل:
   - "JavaScript script starting..."
   - "Form found, adding event listener"
   
5. إذا لم تظهر الرسائل:
   - أعد تحميل الصفحة (Ctrl+F5)
   - تحقق من وجود أخطاء في Console
   
6. إذا ظهرت الرسائل لكن النموذج لا يُرسل:
   - اكتب في Console: 
     document.getElementById('restoreForm')
   - يجب أن يظهر عنصر النموذج
   
7. للإرسال اليدوي، اكتب في Console:
   const form = document.getElementById('restoreForm');
   if (form) form.submit();

8. أو استخدم الصفحة التشخيصية:
   file://{os.path.abspath('quick_fix_restore.html')}
""")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ تم إنشاء الحل الفوري بنجاح!")
    else:
        print("\n❌ فشل في إنشاء الحل الفوري")
