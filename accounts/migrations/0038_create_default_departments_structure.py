# Generated manually

from django.db import migrations


def create_departments_structure(apps, schema_editor):
    """إنشاء هيكل الأقسام والوحدات الافتراضي"""
    Department = apps.get_model('accounts', 'Department')
    
    # لا نحذف الأقسام الموجودة - نحدثها فقط أو ننشئها إذا لم تكن موجودة
    # هذا يحافظ على الإعدادات المخصصة للمستخدم
    
    # تعريف الأقسام الرئيسية
    main_departments = {
        'customers': {
            'name': 'العملاء',
            'icon': 'fa-users',
            'order': 1,
            'url_name': 'customers:customer_list',
            'show_customers': True,
        },
        'orders': {
            'name': 'الطلبات',
            'icon': 'fa-shopping-cart',
            'order': 2,
            'url_name': 'orders:order_list',
            'show_orders': True,
        },
        'inventory': {
            'name': 'المخزون',
            'icon': 'fa-boxes',
            'order': 3,
            'url_name': None,
            'show_inventory': True,
        },
        'inspections': {
            'name': 'المعاينات',
            'icon': 'fa-clipboard-check',
            'order': 4,
            'url_name': 'inspections:inspection_list',
            'show_inspections': True,
        },
        'installations': {
            'name': 'التركيبات',
            'icon': 'fa-tools',
            'order': 5,
            'url_name': 'installations:installation_dashboard',
            'show_installations': True,
        },
        'manufacturing': {
            'name': 'إدارة التصنيع',
            'icon': 'fa-industry',
            'order': 6,
            'url_name': None,
            'show_manufacturing': True,
        },
        'complaints': {
            'name': 'الشكاوى',
            'icon': 'fa-exclamation-triangle',
            'order': 7,
            'url_name': None,
            'show_complaints': True,
        },
        'reports': {
            'name': 'التقارير',
            'icon': 'fa-chart-bar',
            'order': 8,
            'url_name': None,
            'show_reports': True,
        },
        'accounting': {
            'name': 'المحاسبة',
            'icon': 'fa-calculator',
            'order': 9,
            'url_name': None,
            'show_accounting': True,
        },
        'database': {
            'name': 'إدارة البيانات',
            'icon': 'fa-database',
            'order': 10,
            'url_name': 'odoo_db_manager:database_list',
            'show_database': True,
        },
        'cutting': {
            'name': 'إدارة التقطيع',
            'icon': 'fa-cut',
            'order': 11,
            'url_name': None,
            'show_inventory': True,  # التقطيع يظهر في المخزون
        },
    }
    
    # إنشاء أو الحصول على الأقسام الرئيسية (get_or_create)
    created_parents = {}
    for code, data in main_departments.items():
        dept, created = Department.objects.get_or_create(
            code=code,
            defaults={
                'name': data['name'],
                'department_type': 'department',
                'icon': data['icon'],
                'order': data['order'],
                'url_name': data['url_name'],
                'is_active': True,
                'is_core': True,
                'parent': None,
                'description': f'قسم {data["name"]}',
                'show_customers': data.get('show_customers', False),
                'show_orders': data.get('show_orders', False),
                'show_inventory': data.get('show_inventory', False),
                'show_inspections': data.get('show_inspections', False),
                'show_installations': data.get('show_installations', False),
                'show_manufacturing': data.get('show_manufacturing', False),
                'show_complaints': data.get('show_complaints', False),
                'show_reports': data.get('show_reports', False),
                'show_accounting': data.get('show_accounting', False),
                'show_database': data.get('show_database', False),
            }
        )
        created_parents[code] = dept
    
    # تعريف الوحدات الفرعية (نسخة من السكريبت العامل)
    navbar_units = [
        # العملاء
        {
            'parent_code': 'customers',
            'code': 'customers_list',
            'name': 'قائمة العملاء',
            'url_name': '/customers/',
            'icon': 'fa-list',
            'order': 1,
            'show_customers': True,
        },
        # الطلبات
        {
            'parent_code': 'orders',
            'code': 'orders_list',
            'name': 'قائمة الطلبات',
            'url_name': '/orders/',
            'icon': 'fa-list',
            'order': 1,
            'show_orders': True,
        },
        # المخزون - وحدات متعددة
        {
            'parent_code': 'inventory',
            'code': 'inventory_dashboard',
            'name': 'إدارة المخزون',
            'url_name': '/inventory/',
            'icon': 'fa-warehouse',
            'order': 1,
            'show_inventory': True,
        },
        {
            'parent_code': 'inventory',
            'code': 'inventory_warehouses',
            'name': 'إدارة المستودعات',
            'url_name': '/inventory/warehouses/',
            'icon': 'fa-warehouse',
            'order': 2,
            'show_inventory': True,
        },
        {
            'parent_code': 'inventory',
            'code': 'inventory_products',
            'name': 'المنتجات والألوان',
            'url_name': '/inventory/base-products/',
            'icon': 'fa-palette',
            'order': 3,
            'show_inventory': True,
        },
        {
            'parent_code': 'inventory',
            'code': 'inventory_colors',
            'name': 'إدارة الألوان',
            'url_name': '/inventory/colors/',
            'icon': 'fa-fill-drip',
            'order': 4,
            'show_inventory': True,
        },
        {
            'parent_code': 'inventory',
            'code': 'inventory_transfers',
            'name': 'تحويلات مخزنية',
            'url_name': '/inventory/transfers/',
            'icon': 'fa-exchange-alt',
            'order': 5,
            'show_inventory': True,
        },
        # التقطيع
        {
            'parent_code': 'cutting',
            'code': 'cutting_system',
            'name': 'نظام التقطيع',
            'url_name': '/cutting/',
            'icon': 'fa-cut',
            'order': 1,
            'show_inventory': True,
        },
        {
            'parent_code': 'cutting',
            'code': 'cutting_batch_orders',
            'name': 'أوامر التقطيع المجمعة',
            'url_name': '/cutting/orders/completed/',
            'icon': 'fa-list-check',
            'order': 2,
            'show_inventory': True,
        },
        {
            'parent_code': 'cutting',
            'code': 'cutting_reports',
            'name': 'تقارير التقطيع',
            'url_name': '/cutting/reports/',
            'icon': 'fa-chart-bar',
            'order': 3,
            'show_inventory': True,
        },
        # استلام المنتجات
        {
            'parent_code': 'manufacturing',
            'code': 'product_receipt',
            'name': 'استلام المنتجات',
            'url_name': '/manufacturing/product-receipt/',
            'icon': 'fa-box-open',
            'order': 1,
            'show_inventory': True,
        },
        # المعاينات
        {
            'parent_code': 'inspections',
            'code': 'inspections_list',
            'name': 'قائمة المعاينات',
            'url_name': '/inspections/',
            'icon': 'fa-clipboard-check',
            'order': 1,
            'show_inspections': True,
        },
        # التركيبات
        {
            'parent_code': 'installations',
            'code': 'installations_dashboard',
            'name': 'لوحة التركيبات',
            'url_name': '/installations/',
            'icon': 'fa-tools',
            'order': 1,
            'show_installations': True,
        },
        # المصنع
        {
            'parent_code': 'manufacturing',
            'code': 'manufacturing_orders',
            'name': 'أوامر التصنيع',
            'url_name': '/manufacturing/',
            'icon': 'fa-list',
            'order': 2,
            'show_manufacturing': True,
        },
        {
            'parent_code': 'manufacturing',
            'code': 'factory_receiver',
            'name': 'استلام من المصنع',
            'url_name': '/manufacturing/fabric-receipt/',
            'icon': 'fa-industry',
            'order': 3,
            'show_manufacturing': True,
        },
        # الشكاوى
        {
            'parent_code': 'complaints',
            'code': 'complaints_dashboard',
            'name': 'لوحة الشكاوى',
            'url_name': '/complaints/',
            'icon': 'fa-tachometer-alt',
            'order': 1,
            'show_complaints': True,
        },
        {
            'parent_code': 'complaints',
            'code': 'complaints_list',
            'name': 'قائمة الشكاوى',
            'url_name': '/complaints/list/',
            'icon': 'fa-list',
            'order': 2,
            'show_complaints': True,
        },
        {
            'parent_code': 'complaints',
            'code': 'complaints_unsolved',
            'name': 'الشكاوى غير المحلولة',
            'url_name': '/complaints/admin/',
            'icon': 'fa-shield-alt',
            'order': 3,
            'show_complaints': True,
        },
        # التقارير
        {
            'parent_code': 'reports',
            'code': 'reports_dashboard',
            'name': 'لوحة التقارير',
            'url_name': '/reports/',
            'icon': 'fa-tachometer-alt',
            'order': 1,
            'show_reports': True,
        },
        {
            'parent_code': 'reports',
            'code': 'reports_orders',
            'name': 'تقرير الطلبات',
            'url_name': '/reports/orders/',
            'icon': 'fa-shopping-cart',
            'order': 2,
            'show_reports': True,
        },
        {
            'parent_code': 'reports',
            'code': 'reports_production',
            'name': 'تقارير الإنتاج',
            'url_name': '/reports/production/',
            'icon': 'fa-industry',
            'order': 3,
            'show_reports': True,
        },
        # المحاسبة
        {
            'parent_code': 'accounting',
            'code': 'accounting_dashboard',
            'name': 'لوحة المحاسبة',
            'url_name': '/accounting/',
            'icon': 'fa-tachometer-alt',
            'order': 1,
            'show_accounting': True,
        },
        {
            'parent_code': 'accounting',
            'code': 'accounting_accounts_tree',
            'name': 'شجرة الحسابات',
            'url_name': '/accounting/accounts/',
            'icon': 'fa-sitemap',
            'order': 2,
            'show_accounting': True,
        },
        {
            'parent_code': 'accounting',
            'code': 'accounting_transactions',
            'name': 'القيود المحاسبية',
            'url_name': '/accounting/transactions/',
            'icon': 'fa-file-invoice',
            'order': 3,
            'show_accounting': True,
        },
        {
            'parent_code': 'accounting',
            'code': 'accounting_advances',
            'name': 'سلف العملاء',
            'url_name': '/accounting/advances/',
            'icon': 'fa-hand-holding-usd',
            'order': 4,
            'show_accounting': True,
        },
        # إدارة البيانات
        {
            'parent_code': 'database',
            'code': 'database_management',
            'name': 'إدارة قاعدة البيانات',
            'url_name': '/database/',
            'icon': 'fa-database',
            'order': 1,
            'show_database': True,
        },
    ]
    
    # إنشاء الوحدات الفرعية
    for unit_data in navbar_units:
        parent_code = unit_data.pop('parent_code')
        parent = created_parents.get(parent_code)
        
        if parent:
            code = unit_data.pop('code')
            unit_data['parent_id'] = parent.id
            unit_data['department_type'] = 'unit'
            unit_data['is_active'] = True
            unit_data['is_core'] = True
            unit_data['description'] = f'وحدة {unit_data["name"]}'
            
            # إضافة جميع حقول show_* كـ False ما عدا المحدد
            for field in ['show_customers', 'show_orders', 'show_inventory', 'show_inspections',
                         'show_installations', 'show_manufacturing', 'show_complaints', 
                         'show_reports', 'show_accounting', 'show_database']:
                if field not in unit_data:
                    unit_data[field] = False
            
            Department.objects.get_or_create(
                code=code,
                defaults=unit_data
            )


def reverse_departments_structure(apps, schema_editor):
    """حذف الأقسام والوحدات المُنشأة"""
    Department = apps.get_model('accounts', 'Department')
    Department.objects.filter(is_core=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0037_department_show_accounting_and_more'),
    ]

    operations = [
        migrations.RunPython(
            create_departments_structure,
            reverse_departments_structure
        ),
    ]
