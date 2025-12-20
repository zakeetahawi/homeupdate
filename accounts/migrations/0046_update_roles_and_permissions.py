from django.db import migrations

def apply_roles(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    
    # تعريف التدرج الهرمي للأدوار مع الصلاحيات المحدثة
    ROLE_HIERARCHY = {
        'sales_manager': {
            'level': 1,
            'display': 'مدير مبيعات',
            'inherits_from': ['region_manager'],
            'permissions': ['view_all_customers', 'view_all_orders', 'view_all_manufacturing', 'view_all_installations']
        },
        'region_manager': {
            'level': 2,
            'display': 'مدير منطقة',
            'inherits_from': ['branch_manager'],
            'permissions': ['view_all_region_orders', 'manage_branches', 'manage_users']
        },
        'branch_manager': {
            'level': 3,
            'display': 'مدير فرع',
            'inherits_from': ['salesperson'],
            'permissions': ['view_branch_orders', 'manage_branch_users', 'approve_orders']
        },
        'factory_manager': {
            'level': 2,
            'display': 'مسؤول مصنع',
            'inherits_from': ['factory_receiver'],
            'permissions': ['view_all_orders', 'search_orders', 'manage_manufacturing', 'manage_inventory', 'approve_manufacturing_orders', 'start_manufacturing']
        },
        'factory_accountant': {
            'level': 3,
            'display': 'محاسب مصنع',
            'inherits_from': ['factory_receiver'],
            'permissions': ['complete_manufacturing', 'view_manufacturing_financials']
        },
        'factory_receiver': {
            'level': 4,
            'display': 'مسؤول استلام مصنع',
            'inherits_from': [],
            'permissions': ['receive_fabric', 'deliver_to_production_line', 'view_fabric_receipts']
        },
        'inspection_manager': {
            'level': 3,
            'display': 'مسؤول معاينات',
            'inherits_from': ['inspection_technician'],
            'permissions': ['view_all_inspections', 'manage_all_inspections', 'assign_inspections', 'view_all_customers', 'manage_all_customers']
        },
        'installation_manager': {
            'level': 3,
            'display': 'مسؤول تركيبات',
            'inherits_from': [],
            'permissions': ['view_all_installations', 'manage_installations', 'view_all_manufacturing']
        },
        'warehouse_staff': {
            'level': 4,
            'display': 'موظف مستودع',
            'inherits_from': [],
            'permissions': ['manage_warehouse_inventory', 'transfer_products']
        },
        'salesperson': {
            'level': 4,
            'display': 'بائع',
            'inherits_from': [],
            'permissions': ['create_orders', 'view_own_orders', 'edit_own_orders']
        },
        'inspection_technician': {
            'level': 5,
            'display': 'فني معاينة',
            'inherits_from': [],
            'permissions': ['view_assigned_inspections', 'update_inspection_status']
        },
        'user': {
            'level': 6,
            'display': 'مستخدم عادي',
            'inherits_from': [],
            'permissions': ['view_dashboard']
        }
    }

    # دالة تعيين الصلاحيات (محلياً داخل الدالة)
    def map_permission(perm_code):
        mapping = {
            # Sales Manager Permissions
            'view_all_customers': [('customers', 'view_customer')],
            'view_all_orders': [('orders', 'view_order')],
            'view_all_manufacturing': [('manufacturing', 'view_manufacturingorder')],
            'view_all_installations': [('installations', 'view_installationschedule')],
            
            # Factory Manager Permissions
            'search_orders': [], 
            'manage_manufacturing': [
                ('manufacturing', 'add_manufacturingorder'), 
                ('manufacturing', 'change_manufacturingorder'),
                ('manufacturing', 'delete_manufacturingorder'),
                ('manufacturing', 'view_manufacturingorder')
            ],
            'manage_inventory': [
                ('inventory', 'view_product'), 
                ('inventory', 'change_product')
            ],
            'approve_manufacturing_orders': [('manufacturing', 'can_approve_orders')],
            'start_manufacturing': [], 
            
            # Factory Accountant Permissions
            'complete_manufacturing': [('manufacturing', 'change_manufacturingorder')], 
            'view_manufacturing_financials': [('manufacturing', 'view_manufacturingorder')],
            
            # Factory Receiver Permissions
            'receive_fabric': [('manufacturing', 'can_receive_fabric')],
            'deliver_to_production_line': [('manufacturing', 'can_deliver_to_production_line')],
            'view_fabric_receipts': [('manufacturing', 'can_view_fabric_receipts')],

            # Installation Manager Permissions
            'manage_installations': [
                ('installations', 'add_installationschedule'),
                ('installations', 'change_installationschedule'),
                ('installations', 'delete_installationschedule')
            ],
            'edit_manufacturing_orders': [('manufacturing', 'change_manufacturingorder')],

            # Inspection Manager Permissions
            'view_all_inspections': [('inspections', 'view_inspection')],
            'manage_all_inspections': [
                ('inspections', 'add_inspection'),
                ('inspections', 'change_inspection')
            ],
            'assign_inspections': [('inspections', 'change_inspection')], 

            # Customer Management
            'manage_all_customers': [
                ('customers', 'add_customer'),
                ('customers', 'change_customer'),
                ('customers', 'delete_customer')
            ]
        }
        
        if '.' in perm_code:
            try:
                app, code = perm_code.split('.')
                return [(app, code)]
            except ValueError:
                return []
            
        return mapping.get(perm_code, [])

    # تنفيذ التحديث
    # نركز على الأدوار المهمة التي تم تحديثها
    target_roles = ['sales_manager', 'factory_manager', 'factory_accountant', 'factory_receiver', 'installation_manager', 'inspection_manager']

    for role_key in target_roles:
        role_data = ROLE_HIERARCHY.get(role_key)
        if not role_data:
            continue
            
        group_name = role_data['display']
        group, created = Group.objects.get_or_create(name=group_name)
        
        # مسح الصلاحيات لإعادة تعيينها
        group.permissions.clear()
        
        perms_list = role_data['permissions']
        
        for perm_code in perms_list:
            if perm_code == 'all':
                continue
                
            real_perms = map_permission(perm_code)
            
            for app_label, codename in real_perms:
                try:
                    permission = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    print(f"Warning: Permission {app_label}.{codename} not found.")

def reverse_func(apps, schema_editor):
    # لا نقوم بحذف المجموعات عند التراجع لتجنب فقدان البيانات
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0045_remove_user_is_general_manager_and_more'),
        # نعتمد أيضاً على التطبيقات الأخرى لضمان وجود الصلاحيات
        ('customers', '0001_initial'), # Assuming exists
        ('inspections', '0001_initial'), # Assuming exists
        ('manufacturing', '0001_initial'), # Assuming exists
        ('installations', '0001_initial'), # Assuming exists
    ]

    operations = [
        migrations.RunPython(apply_roles, reverse_func),
    ]
