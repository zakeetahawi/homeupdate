import os
import re
import sys

def fix_file_syntax(filepath):
    """تصحيح أخطاء بناء الجملة الشائعة في ملف"""
    print(f"Checking {filepath}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # إصلاح بعض المشاكل الشائعة
        # إصلاح المسافات المتعددة
        content = re.sub(r'\s+\n', '\n', content)
        
        # إصلاح أقواس غير مكتملة
        open_brackets = content.count('{') - content.count('}')
        open_parentheses = content.count('(') - content.count(')')
        open_squares = content.count('[') - content.count(']')
        
        for _ in range(open_brackets):
            content += '\n}'
        for _ in range(open_parentheses):
            content += '\n)'
        for _ in range(open_squares):
            content += '\n]'
        
        # إصلاح الأخطاء المحتملة في دالة get_customer_types
        if 'get_customer_types' in content:
            # تنظيف دالة get_customer_types
            get_types_pattern = r'def\s+get_customer_types\(\):\s*.*?(?=\n\s*class|\n\s*def|\Z)'
            get_types_match = re.search(get_types_pattern, content, re.DOTALL)
            
            if get_types_match:
                old_func = get_types_match.group(0)
                new_func = '''def get_customer_types():
    """استرجاع أنواع العملاء من قاعدة البيانات مع تخزين مؤقت"""
    cache_key = 'customer_types_choices'
    cached_types = cache.get(cache_key)
    
    if cached_types is None:
        try:
            from django.apps import apps
            CustomerType = apps.get_model('customers', 'CustomerType')
            
            if not CustomerType._meta.installed:
                return []
                
            types = [(t.code, t.name) for t in CustomerType.objects.filter(
                is_active=True).order_by('name')]
            cache.set(cache_key, types, timeout=3600)
            cached_types = types
        except Exception:
            cached_types = []
            
    return cached_types or []'''
                
                content = content.replace(old_func, new_func)
        
        # كتابة التغييرات
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(content)
        
        print(f"Fixed {filepath}")
        return True
    
    except Exception as e:
        print(f"Error fixing {filepath}: {str(e)}")
        return False

def main():
    """البحث عن ملفات models.py وإصلاحها"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    models_files = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file == 'models.py':
                models_files.append(os.path.join(root, file))
    
    for filepath in models_files:
        fix_file_syntax(filepath)

if __name__ == "__main__":
    main()