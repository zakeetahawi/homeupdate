#!/usr/bin/env python
"""
فحص صلاحيات نقاط نهاية API
تشغيل: python scripts/security/check_api_permissions.py
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
import inspect
import importlib


def check_viewset_permissions(module_name, module):
    """فحص ViewSets في وحدة معينة"""
    issues = []
    checked = []
    
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, viewsets.ViewSet) and obj != viewsets.ViewSet:
            full_name = f"{module_name}.{name}"
            
            # فحص permission_classes
            if not hasattr(obj, 'permission_classes'):
                issues.append({
                    'viewset': full_name,
                    'issue': 'لا يوجد permission_classes',
                    'severity': 'critical'
                })
            elif not obj.permission_classes:
                issues.append({
                    'viewset': full_name,
                    'issue': 'permission_classes فارغ',
                    'severity': 'critical'
                })
            elif AllowAny in obj.permission_classes:
                issues.append({
                    'viewset': full_name,
                    'issue': 'يستخدم AllowAny - متاح للجميع!',
                    'severity': 'warning'
                })
            else:
                checked.append({
                    'viewset': full_name,
                    'permissions': [p.__name__ for p in obj.permission_classes]
                })
    
    return checked, issues


def main():
    """الدالة الرئيسية"""
    print('🔍 فحص صلاحيات API...\n')
    
    # الوحدات المطلوب فحصها
    modules_to_check = [
        'inventory.api_views',
        'orders.api_views',
        'manufacturing.api_views',
        'customers.api_views',
    ]
    
    all_checked = []
    all_issues = []
    
    for module_name in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            checked, issues = check_viewset_permissions(module_name, module)
            all_checked.extend(checked)
            all_issues.extend(issues)
        except ImportError:
            print(f'⚠️  الوحدة {module_name} غير موجودة')
        except Exception as e:
            print(f'❌ خطأ في فحص {module_name}: {e}')
    
    # عرض النتائج
    print('='*60)
    print('✅ ViewSets الآمنة:')
    print('='*60)
    for item in all_checked:
        perms = ', '.join(item['permissions'])
        print(f"  ✓ {item['viewset']}")
        print(f"    الصلاحيات: {perms}\n")
    
    if all_issues:
        print('\n' + '='*60)
        print('🔴 مشاكل الصلاحيات:')
        print('='*60)
        
        critical = [i for i in all_issues if i['severity'] == 'critical']
        warnings = [i for i in all_issues if i['severity'] == 'warning']
        
        if critical:
            print('\n🔴 حرج:')
            for issue in critical:
                print(f"  ❌ {issue['viewset']}")
                print(f"     {issue['issue']}\n")
        
        if warnings:
            print('\n⚠️  تحذيرات:')
            for issue in warnings:
                print(f"  ⚠️  {issue['viewset']}")
                print(f"     {issue['issue']}\n")
        
        print('='*60)
        print(f'\n📊 الملخص:')
        print(f'  ✅ آمن: {len(all_checked)}')
        print(f'  🔴 حرج: {len(critical)}')
        print(f'  ⚠️  تحذيرات: {len(warnings)}')
        print(f'  📈 الإجمالي: {len(all_checked) + len(all_issues)}')
        
        return False
    else:
        print('\n' + '='*60)
        print('✅ جميع ViewSets لديها صلاحيات مناسبة!')
        print('='*60)
        print(f'\n📊 تم فحص {len(all_checked)} ViewSet')
        return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
