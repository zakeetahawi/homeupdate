#!/usr/bin/env python
"""
حذف الهيكل القديم وإنشاء وحدات navbar كوحدات رئيسية تابعة للأقسام الموجودة
"""
import os
import sys
import django

# إضافة المسار الصحيح للمشروع
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from accounts.models import Department

def cleanup_and_create_navbar_units():
    """حذف الهيكل القديم وإنشاء وحدات navbar"""
    
    # 1. حذف الوحدات القديمة
    print("🗑️  حذف الوحدات القديمة...")
    old_navbar = Department.objects.filter(code__startswith='navbar_')
    old_main = Department.objects.filter(code='main_navbar')
    
    deleted_count = old_navbar.count() + old_main.count()
    old_navbar.delete()
    old_main.delete()
    
    if deleted_count > 0:
        print(f"   ✓ تم حذف {deleted_count} قسم قديم")
    else:
        print(f"   • لا توجد أقسام قديمة للحذف")
    
    print("\n" + "="*70 + "\n")
    
    # 2. التحقق من الأقسام الرئيسية الموجودة أو إنشاؤها
    print("📋 التحقق من الأقسام الرئيسية...")
    
    main_departments = {
        'customers': {'name': 'إدارة العملاء', 'icon': 'fa-users', 'order': 1},
        'orders': {'name': 'إدارة الطلبات', 'icon': 'fa-shopping-cart', 'order': 2},
        'inventory': {'name': 'إدارة المخزون', 'icon': 'fa-warehouse', 'order': 3},
        'inspections': {'name': 'إدارة المعاينات', 'icon': 'fa-search', 'order': 4},
        'installations': {'name': 'إدارة التركيبات', 'icon': 'fa-tools', 'order': 5},
        'manufacturing': {'name': 'إدارة التصنيع', 'icon': 'fa-industry', 'order': 6},
        'complaints': {'name': 'إدارة الشكاوى', 'icon': 'fa-exclamation-triangle', 'order': 7},
        'reports': {'name': 'التقارير', 'icon': 'fa-chart-bar', 'order': 8},
        'accounting': {'name': 'المحاسبة', 'icon': 'fa-calculator', 'order': 9},
        'database': {'name': 'إدارة البيانات', 'icon': 'fa-database', 'order': 10},
        'cutting': {'name': 'إدارة التقطيع', 'icon': 'fa-cut', 'order': 11},
    }
    
    created_depts = 0
    existing_depts = 0
    
    for code, data in main_departments.items():
        dept, created = Department.objects.get_or_create(
            code=code,
            defaults={
                'name': data['name'],
                'department_type': 'department',
                'icon': data['icon'],
                'order': data['order'],
                'is_active': True,
                'parent': None,
                'description': f'قسم {data["name"]}',
                # تعيين جميع حقول show_* بقيم افتراضية
                'show_customers': False,
                'show_orders': False,
                'show_inventory': False,
                'show_inspections': False,
                'show_installations': False,
                'show_manufacturing': False,
                'show_complaints': False,
                'show_reports': False,
                'show_accounting': False,
                'show_database': False,
            }
        )
        
        if created:
            created_depts += 1
            print(f"   ✓ تم إنشاء: {data['name']} ({code})")
        else:
            existing_depts += 1
            # تحديث الترتيب والأيقونة
            dept.order = data['order']
            dept.icon = data['icon']
            dept.save(update_fields=['order', 'icon'])
            print(f"   ⟳ موجود: {data['name']} ({code})")
    
    print(f"\n   📊 تم إنشاء {created_depts} قسم | {existing_depts} قسم موجود")
    print("\n" + "="*70 + "\n")
    
    # 3. إنشاء الوحدات الفرعية لكل قسم
    print("🎯 إنشاء وحدات Navbar كوحدات فرعية...")
    
    navbar_units = [
        # العملاء
        {
            'parent_code': 'customers',
            'code': 'customers_list',
            'name': 'قائمة العملاء',
            'url_name': '/customers/',
            'icon': 'fa-list',
            'order': 1,
            'show_customers': True
        },
        
        # الطلبات
        {
            'parent_code': 'orders',
            'code': 'orders_list',
            'name': 'قائمة الطلبات',
            'url_name': '/orders/',
            'icon': 'fa-list',
            'order': 1,
            'show_orders': True
        },
        
        # المخزون - وحدات متعددة
        {
            'parent_code': 'inventory',
            'code': 'inventory_dashboard',
            'name': 'إدارة المخزون',
            'url_name': '/inventory/',
            'icon': 'fa-warehouse',
            'order': 1,
            'show_inventory': True
        },
        {
            'parent_code': 'inventory',
            'code': 'inventory_warehouses',
            'name': 'إدارة المستودعات',
            'url_name': '/inventory/warehouses/',
            'icon': 'fa-warehouse',
            'order': 2,
            'show_inventory': True
        },
        {
            'parent_code': 'inventory',
            'code': 'inventory_products',
            'name': 'المنتجات والألوان',
            'url_name': '/inventory/base-products/',
            'icon': 'fa-palette',
            'order': 3,
            'show_inventory': True
        },
        {
            'parent_code': 'inventory',
            'code': 'inventory_colors',
            'name': 'إدارة الألوان',
            'url_name': '/inventory/colors/',
            'icon': 'fa-fill-drip',
            'order': 4,
            'show_inventory': True
        },
        {
            'parent_code': 'inventory',
            'code': 'inventory_transfers',
            'name': 'تحويلات مخزنية',
            'url_name': '/inventory/transfers/',
            'icon': 'fa-exchange-alt',
            'order': 5,
            'show_inventory': True
        },
        
        # التقطيع
        {
            'parent_code': 'cutting',
            'code': 'cutting_system',
            'name': 'نظام التقطيع',
            'url_name': '/cutting/',
            'icon': 'fa-cut',
            'order': 1,
            'show_inventory': True
        },
        {
            'parent_code': 'cutting',
            'code': 'cutting_batch_orders',
            'name': 'أوامر التقطيع المجمعة',
            'url_name': '/cutting/orders/completed/',
            'icon': 'fa-list-check',
            'order': 2,
            'show_inventory': True
        },
        {
            'parent_code': 'cutting',
            'code': 'cutting_reports',
            'name': 'تقارير التقطيع',
            'url_name': '/cutting/reports/',
            'icon': 'fa-chart-bar',
            'order': 3,
            'show_inventory': True
        },
        
        # استلام المنتجات
        {
            'parent_code': 'manufacturing',
            'code': 'product_receipt',
            'name': 'استلام المنتجات',
            'url_name': '/manufacturing/product-receipt/',
            'icon': 'fa-box-open',
            'order': 1,
            'show_inventory': True
        },
        
        # المعاينات
        {
            'parent_code': 'inspections',
            'code': 'inspections_list',
            'name': 'قائمة المعاينات',
            'url_name': '/inspections/',
            'icon': 'fa-clipboard-check',
            'order': 1,
            'show_inspections': True
        },
        
        # التركيبات
        {
            'parent_code': 'installations',
            'code': 'installations_dashboard',
            'name': 'لوحة التركيبات',
            'url_name': '/installations/',
            'icon': 'fa-tools',
            'order': 1,
            'show_installations': True
        },
        
        # المصنع
        {
            'parent_code': 'manufacturing',
            'code': 'manufacturing_orders',
            'name': 'أوامر التصنيع',
            'url_name': '/manufacturing/',
            'icon': 'fa-list',
            'order': 2,
            'show_manufacturing': True
        },
        {
            'parent_code': 'manufacturing',
            'code': 'factory_receiver',
            'name': 'استلام من المصنع',
            'url_name': '/manufacturing/fabric-receipt/',
            'icon': 'fa-industry',
            'order': 3,
            'show_manufacturing': True
        },
        
        # الشكاوى
        {
            'parent_code': 'complaints',
            'code': 'complaints_dashboard',
            'name': 'لوحة الشكاوى',
            'url_name': '/complaints/',
            'icon': 'fa-tachometer-alt',
            'order': 1,
            'show_complaints': True
        },
        {
            'parent_code': 'complaints',
            'code': 'complaints_list',
            'name': 'قائمة الشكاوى',
            'url_name': '/complaints/list/',
            'icon': 'fa-list',
            'order': 2,
            'show_complaints': True
        },
        {
            'parent_code': 'complaints',
            'code': 'complaints_unsolved',
            'name': 'الشكاوى غير المحلولة',
            'url_name': '/complaints/admin/',
            'icon': 'fa-shield-alt',
            'order': 3,
            'show_complaints': True
        },
        
        # التقارير
        {
            'parent_code': 'reports',
            'code': 'reports_dashboard',
            'name': 'لوحة التقارير',
            'url_name': '/reports/',
            'icon': 'fa-tachometer-alt',
            'order': 1,
            'show_reports': True
        },
        {
            'parent_code': 'reports',
            'code': 'reports_orders',
            'name': 'تقرير الطلبات',
            'url_name': '/reports/orders/',
            'icon': 'fa-shopping-cart',
            'order': 2,
            'show_reports': True
        },
        {
            'parent_code': 'reports',
            'code': 'reports_production',
            'name': 'تقارير الإنتاج',
            'url_name': '/reports/production/',
            'icon': 'fa-industry',
            'order': 3,
            'show_reports': True
        },
        
        # المحاسبة
        {
            'parent_code': 'accounting',
            'code': 'accounting_dashboard',
            'name': 'لوحة المحاسبة',
            'url_name': '/accounting/',
            'icon': 'fa-tachometer-alt',
            'order': 1,
            'show_accounting': True
        },
        {
            'parent_code': 'accounting',
            'code': 'accounting_accounts_tree',
            'name': 'شجرة الحسابات',
            'url_name': '/accounting/accounts/',
            'icon': 'fa-sitemap',
            'order': 2,
            'show_accounting': True
        },
        {
            'parent_code': 'accounting',
            'code': 'accounting_transactions',
            'name': 'القيود المحاسبية',
            'url_name': '/accounting/transactions/',
            'icon': 'fa-file-invoice',
            'order': 3,
            'show_accounting': True
        },
        {
            'parent_code': 'accounting',
            'code': 'accounting_advances',
            'name': 'عربونات العملاء',
            'url_name': '/accounting/advances/',
            'icon': 'fa-hand-holding-usd',
            'order': 4,
            'show_accounting': True
        },
        
        # إدارة البيانات
        {
            'parent_code': 'database',
            'code': 'database_management',
            'name': 'إدارة قاعدة البيانات',
            'url_name': '/database/',
            'icon': 'fa-database',
            'order': 1,
            'show_database': True
        },
    ]
    
    created_units = 0
    updated_units = 0
    parent_dict = {}
    
    for unit_data in navbar_units:
        parent_code = unit_data.pop('parent_code')
        
        # الحصول على القسم الرئيسي
        if parent_code not in parent_dict:
            parent_dict[parent_code] = Department.objects.get(code=parent_code)
        
        parent_dept = parent_dict[parent_code]
        
        # استخراج حقول show_*
        show_fields = {}
        for key in list(unit_data.keys()):
            if key.startswith('show_'):
                show_fields[key] = unit_data.pop(key)
        
        # إنشاء أو تحديث الوحدة
        unit, created = Department.objects.update_or_create(
            code=unit_data['code'],
            defaults={
                'name': unit_data['name'],
                'url_name': unit_data['url_name'],
                'icon': unit_data['icon'],
                'order': unit_data['order'],
                'department_type': 'unit',
                'is_active': True,
                'parent': parent_dept,
                'description': f'وحدة {unit_data["name"]} ضمن {parent_dept.name}',
                **show_fields
            }
        )
        
        if created:
            created_units += 1
            print(f"   ✓ {parent_dept.name} → {unit_data['name']}")
        else:
            updated_units += 1
            print(f"   ⟳ {parent_dept.name} → {unit_data['name']}")
    
    print(f"\n   📊 تم إنشاء {created_units} وحدة | تم تحديث {updated_units} وحدة")
    print("\n" + "="*70 + "\n")
    
    # 4. عرض الهيكل النهائي
    print("🎯 الهيكل النهائي:")
    print("="*70)
    
    departments = Department.objects.filter(parent=None).order_by('order')
    for dept in departments:
        children = Department.objects.filter(parent=dept).order_by('order')
        if children.exists():
            print(f"\n├── {dept.name} ({dept.code})")
            for i, child in enumerate(children, 1):
                is_last = i == children.count()
                prefix = "└──" if is_last else "├──"
                print(f"│   {prefix} {child.name}")
    
    print("\n" + "="*70)
    print(f"\n✅ تم بنجاح!")
    print(f"💡 افتح: http://localhost:8000/admin/accounts/department/")

if __name__ == '__main__':
    cleanup_and_create_navbar_units()
