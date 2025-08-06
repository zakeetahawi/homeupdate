"""
سكريبت لتطبيق تحسينات الترتيب على جميع admin classes في المشروع
"""

import os
import re
from pathlib import Path

# تحديد مجلدات التطبيقات
APPS = [
    'accounts', 'backup_system', 'complaints', 'customers', 
    'installations', 'inventory', 'manufacturing', 'orders', 'reports'
]

def update_admin_file(app_name):
    """تحديث ملف admin.py للتطبيق المحدد"""
    admin_file_path = f"/home/zakee/homeupdate/{app_name}/admin.py"
    
    if not os.path.exists(admin_file_path):
        print(f"❌ ملف {admin_file_path} غير موجود")
        return False
    
    try:
        with open(admin_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # التحقق من وجود استيراد BaseSortableModelAdmin
        if 'from crm.admin_base import BaseSortableModelAdmin' not in content:
            # إضافة الاستيراد
            import_pattern = r'(from django\.contrib import admin.*?\n)'
            replacement = r'\1from crm.admin_base import BaseSortableModelAdmin\n'
            content = re.sub(import_pattern, replacement, content, flags=re.DOTALL)
        
        # البحث عن جميع admin classes
        admin_class_pattern = r'@admin\.register\([^)]+\)\s*\nclass\s+(\w+)\(admin\.ModelAdmin\):'
        
        def replace_admin_class(match):
            class_name = match.group(1)
            return match.group(0).replace('admin.ModelAdmin', 'BaseSortableModelAdmin  # استخدام الفئة المحسنة')
        
        content = re.sub(admin_class_pattern, replace_admin_class, content)
        
        # إضافة list_per_page = 50 للفئات التي لا تحتوي عليها
        def add_list_per_page(match):
            class_content = match.group(0)
            if 'list_per_page' not in class_content:
                # إضافة list_per_page بعد تعريف الفئة
                lines = class_content.split('\n')
                lines.insert(1, '    list_per_page = 50  # عرض 50 صف كافتراضي')
                class_content = '\n'.join(lines)
            return class_content
        
        # البحث عن جميع admin classes مع محتواها
        full_class_pattern = r'(@admin\.register\([^)]+\)\s*\nclass\s+\w+\([^)]+\):[^@]*?)(?=@|\Z)'
        content = re.sub(full_class_pattern, add_list_per_page, content, flags=re.DOTALL)
        
        # كتابة الملف المحدث
        with open(admin_file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        print(f"✅ تم تحديث {admin_file_path} بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في تحديث {admin_file_path}: {str(e)}")
        return False

def main():
    """تنفيذ التحديث على جميع التطبيقات"""
    print("🚀 بدء تطبيق تحسينات الترتيب على جميع admin classes...")
    
    success_count = 0
    total_count = 0
    
    for app in APPS:
        total_count += 1
        if update_admin_file(app):
            success_count += 1
    
    print(f"\n📊 النتائج:")
    print(f"✅ تم تحديث {success_count} من {total_count} ملف")
    print(f"❌ فشل في تحديث {total_count - success_count} ملف")
    
    if success_count == total_count:
        print("\n🎉 تم تطبيق جميع التحسينات بنجاح!")
        print("الآن جميع الجداول تدعم:")
        print("• ترتيب جميع الأعمدة بالنقر على رأس العمود")
        print("• عرض 50 صف في الصفحة الواحدة")
        print("• تحسينات الأداء والواجهة")
    else:
        print("\n⚠️ يرجى مراجعة الملفات التي فشل تحديثها")

if __name__ == "__main__":
    main()
