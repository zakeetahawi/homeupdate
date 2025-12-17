# Generated manually

from django.db import migrations


def create_departments_structure(apps, schema_editor):
    """إنشاء هيكل الأقسام والوحدات الافتراضي"""
    Department = apps.get_model('accounts', 'Department')
    
    # حذف الأقسام القديمة إذا وجدت
    Department.objects.filter(code__startswith='navbar_').delete()
    Department.objects.filter(code='main_navbar').delete()
    
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
    
    # إنشاء أو تحديث الأقسام الرئيسية
    created_parents = {}
    for code, data in main_departments.items():
        defaults = {
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
        
        dept, created = Department.objects.update_or_create(
            code=code,
            defaults=defaults
        )
        created_parents[code] = dept
    
    # تعريف الوحدات الفرعية
    navbar_units = [
        # العملاء
        {
            'parent_code': 'customers',
            'code': 'customers_list',
            'name': 'قائمة العملاء',
            'url_name': 'customers:customer_list',
            'icon': 'fa-list',
            'order': 1,
            'show_customers': True,
        },
        # الطلبات
        {
            'parent_code': 'orders',
            'code': 'orders_list',
            'name': 'قائمة الطلبات',
            'url_name': 'orders:order_list',
            'icon': 'fa-list',
            'order': 1,
            'show_orders': True,
        },
        # المخزون
        {
            'parent_code': 'inventory',
            'code': 'inventory_management',
            'name': 'إدارة المخزون',
            'url_name': 'inventory:inventory_list',
            'icon': 'fa-warehouse',
            'order': 1,
            'show_inventory': True,
        },
        {
            'parent_code': 'inventory',
            'code': 'warehouse_management',
            'name': 'إدارة المستودعات',
            'url_name': 'inventory:warehouse_list',
            'icon': 'fa-building',
            'order': 2,
            'show_inventory': True,
        },
        {
            'parent_code': 'inventory',
            'code': 'products_colors',
            'name': 'المنتجات والألوان',
            'url_name': 'inventory:product_list',
            'icon': 'fa-box',
            'order': 3,
            'show_inventory': True,
        },
        {
            'parent_code': 'inventory',
            'code': 'color_management',
            'name': 'إدارة الألوان',
            'url_name': 'inventory:color_attribute_list',
            'icon': 'fa-palette',
            'order': 4,
            'show_inventory': True,
        },
        {
            'parent_code': 'inventory',
            'code': 'inventory_transfers',
            'name': 'تحويلات مخزنية',
            'url_name': 'inventory:transfer_list',
            'icon': 'fa-exchange-alt',
            'order': 5,
            'show_inventory': True,
        },
        # التقطيع (تحت المخزون)
        {
            'parent_code': 'cutting',
            'code': 'cutting_system',
            'name': 'نظام التقطيع',
            'url_name': 'cutting:cutting_order_list',
            'icon': 'fa-cut',
            'order': 1,
            'show_inventory': True,
        },
        {
            'parent_code': 'cutting',
            'code': 'batch_cutting_orders',
            'name': 'أوامر التقطيع المجمعة',
            'url_name': 'cutting:batch_cutting_order_list',
            'icon': 'fa-layer-group',
            'order': 2,
            'show_inventory': True,
        },
        {
            'parent_code': 'cutting',
            'code': 'cutting_reports',
            'name': 'تقارير التقطيع',
            'url_name': 'cutting:cutting_reports',
            'icon': 'fa-chart-line',
            'order': 3,
            'show_inventory': True,
        },
        # المعاينات
        {
            'parent_code': 'inspections',
            'code': 'inspections_list',
            'name': 'قائمة المعاينات',
            'url_name': 'inspections:inspection_list',
            'icon': 'fa-list',
            'order': 1,
            'show_inspections': True,
        },
        # التركيبات
        {
            'parent_code': 'installations',
            'code': 'installations_dashboard',
            'name': 'لوحة التركيبات',
            'url_name': 'installations:installation_dashboard',
            'icon': 'fa-tachometer-alt',
            'order': 1,
            'show_installations': True,
        },
        # المصنع
        {
            'parent_code': 'manufacturing',
            'code': 'product_receipt',
            'name': 'استلام المنتجات',
            'url_name': 'manufacturing:product_receipt_list',
            'icon': 'fa-inbox',
            'order': 1,
            'show_manufacturing': True,
        },
        {
            'parent_code': 'manufacturing',
            'code': 'manufacturing_orders',
            'name': 'أوامر التصنيع',
            'url_name': 'manufacturing:manufacturing_order_list',
            'icon': 'fa-cogs',
            'order': 2,
            'show_manufacturing': True,
        },
        {
            'parent_code': 'manufacturing',
            'code': 'factory_receipt',
            'name': 'استلام من المصنع',
            'url_name': 'manufacturing:fabric_receipt_list',
            'icon': 'fa-truck-loading',
            'order': 3,
            'show_manufacturing': True,
        },
        # الشكاوى
        {
            'parent_code': 'complaints',
            'code': 'complaints_dashboard',
            'name': 'لوحة الشكاوى',
            'url_name': 'complaints:dashboard',
            'icon': 'fa-tachometer-alt',
            'order': 1,
            'show_complaints': True,
        },
        {
            'parent_code': 'complaints',
            'code': 'complaints_list',
            'name': 'قائمة الشكاوى',
            'url_name': 'complaints:complaint_list',
            'icon': 'fa-list',
            'order': 2,
            'show_complaints': True,
        },
        {
            'parent_code': 'complaints',
            'code': 'unresolved_complaints',
            'name': 'الشكاوى غير المحلولة',
            'url_name': 'complaints:unresolved_complaints',
            'icon': 'fa-exclamation-circle',
            'order': 3,
            'show_complaints': True,
        },
        # التقارير
        {
            'parent_code': 'reports',
            'code': 'reports_dashboard',
            'name': 'لوحة التقارير',
            'url_name': 'reports:dashboard',
            'icon': 'fa-tachometer-alt',
            'order': 1,
            'show_reports': True,
        },
        {
            'parent_code': 'reports',
            'code': 'orders_report',
            'name': 'تقرير الطلبات',
            'url_name': 'reports:orders_report',
            'icon': 'fa-file-alt',
            'order': 2,
            'show_reports': True,
        },
        {
            'parent_code': 'reports',
            'code': 'production_reports',
            'name': 'تقارير الإنتاج',
            'url_name': 'reports:production_report',
            'icon': 'fa-industry',
            'order': 3,
            'show_reports': True,
        },
        # المحاسبة
        {
            'parent_code': 'accounting',
            'code': 'accounting_dashboard',
            'name': 'لوحة المحاسبة',
            'url_name': 'accounting:dashboard',
            'icon': 'fa-tachometer-alt',
            'order': 1,
            'show_accounting': True,
        },
        {
            'parent_code': 'accounting',
            'code': 'chart_of_accounts',
            'name': 'شجرة الحسابات',
            'url_name': 'accounting:account_list',
            'icon': 'fa-sitemap',
            'order': 2,
            'show_accounting': True,
        },
        {
            'parent_code': 'accounting',
            'code': 'journal_entries',
            'name': 'القيود المحاسبية',
            'url_name': 'accounting:transaction_list',
            'icon': 'fa-book',
            'order': 3,
            'show_accounting': True,
        },
        {
            'parent_code': 'accounting',
            'code': 'customer_advances',
            'name': 'سلف العملاء',
            'url_name': 'accounting:customer_advance_list',
            'icon': 'fa-money-bill-wave',
            'order': 4,
            'show_accounting': True,
        },
        # إدارة البيانات
        {
            'parent_code': 'database',
            'code': 'database_management',
            'name': 'إدارة قاعدة البيانات',
            'url_name': 'odoo_db_manager:database_list',
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
            
            code = unit_data.pop('code')
            Department.objects.update_or_create(
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
