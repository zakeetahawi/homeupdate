#!/usr/bin/env python
"""
سكريبت لإصلاح جميع ملفات admin.py وإزالة الأخطاء النحوية
"""

import os
import re
import subprocess
import sys

def fix_admin_files():
    """إصلاح جميع ملفات admin.py"""
    
    # العثور على جميع ملفات admin.py
    admin_files = []
    for root, dirs, files in os.walk('.'):
        # تجاهل مجلدات venv
        if 'venv' in root or '__pycache__' in root:
            continue
        for file in files:
            if file == 'admin.py':
                admin_files.append(os.path.join(root, file))
    
    print(f"تم العثور على {len(admin_files)} ملف admin.py")
    
    for admin_file in admin_files:
        if 'venv' in admin_file:
            continue
            
        print(f"إصلاح {admin_file}...")
        
        try:
            # قراءة الملف
            with open(admin_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # إصلاح الأخطاء الشائعة
            fixes = [
                # إزالة استيراد BaseSortableModelAdmin
                (r'from crm\.admin_base import BaseSortableModelAdmin\n', ''),
                (r'# استيراد الفئة الأساسية المحسنة\n', ''),
                
                # استبدال BaseSortableModelAdmin بـ admin.ModelAdmin
                (r'BaseSortableModelAdmin', 'admin.ModelAdmin'),
                
                # إصلاح pattern المشكلة: @admin.register(Model)\n    list_per_page = 50\nclass Admin(...)
                (r'(@admin\.register\([^)]+\))\s*\n\s*(list_per_page\s*=\s*[^#\n]+(?:#[^\n]*)?)\s*\n\s*class\s+(\w+)\s*\(([^)]+)\)\s*:', 
                 r'\1\nclass \3(\4):\n    \2'),
                
                # إصلاح الأقواس المفتوحة
                (r'admin\.ModelAdmin\s*#[^)]*\):', 'admin.ModelAdmin):'),
                (r'admin\.ModelAdmin\s*#[^)]*:', 'admin.ModelAdmin:'),
                
                # إزالة التعليقات من تعريف الفئات
                (r'class\s+(\w+)\s*\(\s*admin\.ModelAdmin\s*#[^)]*\):', r'class \1(admin.ModelAdmin):'),
            ]
            
            # تطبيق الإصلاحات
            for pattern, replacement in fixes:
                content = re.sub(pattern, replacement, content)
            
            # إصلاح خاص للمشكلة الأكثر شيوعاً
            lines = content.split('\n')
            fixed_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # البحث عن pattern: @admin.register() متبوع بـ list_per_page متبوع بـ class
                if line.strip().startswith('@admin.register('):
                    fixed_lines.append(line)
                    i += 1
                    
                    # التحقق من السطر التالي
                    if i < len(lines):
                        next_line = lines[i]
                        if 'list_per_page' in next_line and next_line.strip().startswith('list_per_page'):
                            # هذا هو النمط المشكلة
                            # العثور على السطر الذي يحتوي على class
                            class_line_idx = i + 1
                            while class_line_idx < len(lines) and not lines[class_line_idx].strip().startswith('class'):
                                class_line_idx += 1
                            
                            if class_line_idx < len(lines):
                                class_line = lines[class_line_idx]
                                # إصلاح class line
                                class_line = re.sub(r'class\s+(\w+)\s*\(\s*admin\.ModelAdmin[^)]*\):', r'class \1(admin.ModelAdmin):', class_line)
                                
                                fixed_lines.append(class_line)
                                fixed_lines.append('    ' + next_line.strip())  # إضافة list_per_page مع مسافة بادئة صحيحة
                                i = class_line_idx + 1
                            else:
                                fixed_lines.append(next_line)
                                i += 1
                        else:
                            fixed_lines.append(line)
                            i += 1
                    else:
                        i += 1
                else:
                    fixed_lines.append(line)
                    i += 1
            
            content = '\n'.join(fixed_lines)
            
            # كتابة الملف المصحح
            with open(admin_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            # فحص الملف
            result = subprocess.run([sys.executable, '-m', 'py_compile', admin_file], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ تم إصلاح {admin_file} بنجاح")
            else:
                print(f"❌ لا يزال هناك خطأ في {admin_file}: {result.stderr}")
                
        except Exception as e:
            print(f"❌ خطأ في معالجة {admin_file}: {e}")

if __name__ == '__main__':
    fix_admin_files()
