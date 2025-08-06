#!/usr/bin/env python
"""
Script لتحديث جميع Templates لاستخدام الأكواد الموحدة
"""

import os
import re

def update_template_files():
    """تحديث جميع ملفات Templates"""
    
    template_patterns = [
        (r'{{ inspection\.id }}', '{{ inspection.inspection_code }}'),
        (r'#{{ inspection\.id }}', '{{ inspection.inspection_code }}'),
        (r'معاينة {{ order\.related_inspection\.id }}', '{{ order.related_inspection.inspection_code }}'),
        (r'{{ manufacturing_order\.id }}', '{{ manufacturing_order.manufacturing_code }}'),
        (r'#{{ manufacturing_order\.id }}', '{{ manufacturing_order.manufacturing_code }}'),
        (r'{{ installation\.id }}', '{{ installation.installation_code }}'),
        (r'#{{ installation\.id }}', '{{ installation.installation_code }}'),
    ]
    
    # البحث في جميع مجلدات Templates
    template_dirs = [
        'orders/templates',
        'inspections/templates', 
        'manufacturing/templates',
        'installations/templates',
        'customers/templates',
        'templates'
    ]
    
    updated_files = []
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            original_content = content
                            
                            # تطبيق جميع التحديثات
                            for pattern, replacement in template_patterns:
                                content = re.sub(pattern, replacement, content)
                            
                            # حفظ الملف إذا تم تعديله
                            if content != original_content:
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    f.write(content)
                                updated_files.append(file_path)
                                print(f"✅ تم تحديث: {file_path}")
                                
                        except Exception as e:
                            print(f"❌ خطأ في تحديث {file_path}: {str(e)}")
    
    print(f"\n📊 تقرير التحديث:")
    print(f"✅ تم تحديث {len(updated_files)} ملف")
    
    if updated_files:
        print("\n📝 الملفات المُحدثة:")
        for file_path in updated_files:
            print(f"   - {file_path}")


if __name__ == "__main__":
    print("🚀 بدء تحديث ملفات Templates...")
    print("=" * 50)
    
    update_template_files()
    
    print("=" * 50)
    print("✨ تم الانتهاء من تحديث Templates!")
