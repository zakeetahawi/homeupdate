"""
تعريف الأقسام الأساسية للنظام
"""
from django.utils.translation import gettext_lazy as _

# قائمة الأقسام الرئيسية
CORE_DEPARTMENTS = [
    {
        'name': 'العملاء',
        'code': 'customers',
        'url_name': 'customers:customer_list',
        'department_type': 'department',
        'icon': 'fas fa-users',
        'order': 10,
        'has_pages': False,
        'is_core': True,
        'children': []
    },
    {
        'name': 'الطلبات',
        'code': 'orders',
        'url_name': 'orders:order_list',
        'department_type': 'department',
        'icon': 'fas fa-shopping-cart',
        'order': 20,
        'has_pages': False,
        'is_core': True,
        'children': []
    },
    {
        'name': 'المخزون',
        'code': 'inventory',
        'url_name': 'inventory:dashboard',
        'department_type': 'department',
        'icon': 'fas fa-boxes',
        'order': 30,
        'has_pages': False,
        'is_core': True,
        'children': []
    },
    {
        'name': 'المعاينات',
        'code': 'inspections',
        'url_name': 'inspections:inspection_list',
        'department_type': 'department',
        'icon': 'fas fa-clipboard-check',
        'order': 40,
        'has_pages': False,
        'is_core': True,
        'children': []
    },
    {
        'name': 'التركيبات',
        'code': 'installations',
        'url_name': 'installations:dashboard',
        'department_type': 'department',
        'icon': 'fas fa-tools',
        'order': 50,
        'has_pages': False,
        'is_core': True,
        'children': []
    },
    {
        'name': 'المصنع',
        'code': 'factory',
        'url_name': 'factory:factory_list',
        'department_type': 'department',
        'icon': 'fas fa-industry',
        'order': 60,
        'has_pages': False,
        'is_core': True,
        'children': []
    },
    {
        'name': 'الشكاوى',
        'code': 'complaints',
        'url_name': 'complaints:dashboard',
        'department_type': 'department',
        'icon': 'fas fa-headset',
        'order': 65,
        'has_pages': False,
        'is_core': True,
        'children': []
    },
    {
        'name': 'التقارير',
        'code': 'reports',
        'url_name': 'reports:dashboard',
        'department_type': 'department',
        'icon': 'fas fa-chart-bar',
        'order': 70,
        'has_pages': False,
        'is_core': True,
        'children': []
    },
    {
        'name': 'إدارة البيانات',
        'code': 'data_management',
        'url_name': 'odoo_db_manager:dashboard',
        'department_type': 'department',
        'icon': 'fas fa-database',
        'order': 80,
        'has_pages': True,
        'is_core': True,
        'children': []
    }
]

def create_core_departments():
    """
    إنشاء الأقسام الأساسية للنظام إذا لم تكن موجودة وتعطيل الأقسام غير الأساسية
    """
    from accounts.models import Department

    # الحصول على قائمة بأكواد الأقسام الأساسية
    core_dept_codes = [dept['code'] for dept in CORE_DEPARTMENTS]
    core_child_codes = []

    for dept in CORE_DEPARTMENTS:
        for child in dept.get('children', []):
            core_child_codes.append(child['code'])

    # إنشاء الأقسام الرئيسية مع الحفاظ على حالة التفعيل
    for dept_data in CORE_DEPARTMENTS:
        children = dept_data.get('children', [])
        dept_data_clean = {k: v for k, v in dept_data.items() if k != 'children'}

        # التحقق من وجود القسم أولاً
        existing_dept = Department.objects.filter(code=dept_data_clean['code']).first()
        dept = None  # تهيئة المتغير

        if existing_dept:
            # إذا كان القسم موجود، نحدث البيانات فقط بدون تغيير is_active
            current_is_active = existing_dept.is_active
            dept_data_copy = dept_data_clean.copy()
            dept_data_copy['is_active'] = current_is_active  # الحفاظ على الحالة الحالية

            for key, value in dept_data_copy.items():
                setattr(existing_dept, key, value)
            existing_dept.save()
            dept = existing_dept
        else:
            # إنشاء قسم جديد - جميع الأقسام في CORE_DEPARTMENTS أساسية
            dept = Department.objects.create(**dept_data_clean)

        # إنشاء الأقسام الفرعية مع نفس المنطق
        if dept:  # التأكد من أن القسم الرئيسي موجود
            for child_data in children:
                child_data['parent'] = dept
                existing_child = Department.objects.filter(code=child_data['code']).first()

                if existing_child:
                    # الحفاظ على حالة التفعيل للقسم الفرعي
                    current_is_active = existing_child.is_active
                    child_data['is_active'] = current_is_active

                    for key, value in child_data.items():
                        setattr(existing_child, key, value)
                    existing_child.save()
                else:
                    # إنشاء قسم فرعي جديد فقط إذا كان أساسي
                    if child_data.get('is_core', False):
                        Department.objects.create(**child_data)
                    # لا ننشئ الأقسام الفرعية غير الأساسية إذا تم حذفها

    # تحديث الأقسام الأساسية لتكون is_core=True فقط (بدون تغيير is_active)
    Department.objects.filter(code__in=core_dept_codes).update(is_core=True)
    Department.objects.filter(code__in=core_child_codes).update(is_core=True)

    # ⚠️ تم تعطيل حذف الأقسام الإضافية للحفاظ على الأقسام المخصصة
    # إذا كنت تريد حذف الأقسام الإضافية، استخدم الأمر: python manage.py cleanup_departments
    
    # # حذف الأقسام الوهمية والإدارات والوحدات الإضافية
    # real_departments = [
    #     'customers', 'orders', 'inventory', 'inspections',
    #     'installations', 'factory', 'complaints', 'reports', 'data_management'
    # ]
    # 
    # # حذف جميع الأقسام التي ليست في القائمة الحقيقية
    # fake_departments = Department.objects.exclude(code__in=real_departments)
    # deleted_count = fake_departments.count()
    # fake_departments.delete()
    # 
    # if deleted_count > 0:
    #     print(f"تم حذف {deleted_count} قسم/إدارة/وحدة إضافية")

    print(f"✅ تم التأكد من وجود {len(core_dept_codes)} قسم أساسي و {len(core_child_codes)} قسم فرعي أساسي")
    print(f"ℹ️  إيقاف العمليات...")
