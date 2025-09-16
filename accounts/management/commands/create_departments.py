from django.core.management.base import BaseCommand
from accounts.models import Department, User
from django.db import transaction

class Command(BaseCommand):
    help = 'Create organizational structure with administrations, departments and units'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            # المستويات التنظيمية الرئيسية
            self.stdout.write(self.style.SUCCESS('إنشاء الهيكل التنظيمي...'))

            # إنشاء الإدارات الرئيسية
            main_departments = {
                # الإدارة العامة
                'management': {
                    'name': 'الإدارة العامة',
                    'code': 'management',
                    'department_type': 'administration',
                    'icon': 'fas fa-building',
                    'order': 1,
                    'description': 'تشمل الإدارة التنفيذية والشؤون الإدارية العامة',
                },
                # إدارة المبيعات والتسويق
                'sales': {
                    'name': 'إدارة المبيعات والتسويق',
                    'code': 'sales',
                    'department_type': 'administration',
                    'icon': 'fas fa-chart-line',
                    'order': 2,
                    'description': 'تشمل فرق المبيعات والتسويق وخدمة العملاء',
                },
                # إدارة العمليات
                'operations': {
                    'name': 'إدارة العمليات',
                    'code': 'operations',
                    'department_type': 'administration',
                    'icon': 'fas fa-cogs',
                    'order': 3,
                    'description': 'تشمل المصنع والمعاينات والتركيبات',
                },
                # إدارة الخدمات المساندة
                'support': {
                    'name': 'الخدمات المساندة',
                    'code': 'support',
                    'department_type': 'administration',
                    'icon': 'fas fa-hands-helping',
                    'order': 4,
                    'description': 'تشمل الموارد البشرية والشؤون المالية وتقنية المعلومات',
                },
            }

            admin_departments = {}
            # إنشاء الإدارات الرئيسية
            for code, data in main_departments.items():
                dept, created = Department.objects.update_or_create(
                    code=code,
                    defaults={
                        'name': data['name'],
                        'department_type': data['department_type'],
                        'icon': data['icon'],
                        'order': data['order'],
                        'description': data['description'],
                    }
                )
                admin_departments[code] = dept
                status = 'Created' if created else 'Updated'
                self.stdout.write(self.style.SUCCESS(f'{status} administration: {dept.name}'))

            # قائمة الأقسام مع روابطها بالإدارات الرئيسية
            departments_data = {
                # أقسام الإدارة العامة
                'exec_office': {
                    'name': 'مكتب المدير التنفيذي',
                    'code': 'exec_office',
                    'department_type': 'department',
                    'icon': 'fas fa-user-tie',
                    'order': 1,
                    'description': 'مكتب المدير التنفيذي والشؤون الإدارية العليا',
                    'parent': admin_departments['management'],
                },
                'admin_affairs': {
                    'name': 'الشؤون الإدارية',
                    'code': 'admin_affairs',
                    'department_type': 'department',
                    'icon': 'fas fa-clipboard-list',
                    'order': 2,
                    'description': 'إدارة الشؤون الإدارية والتنظيمية',
                    'parent': admin_departments['management'],
                },
                'quality': {
                    'name': 'قسم الجودة',
                    'code': 'quality',
                    'department_type': 'department',
                    'icon': 'fas fa-award',
                    'order': 3,
                    'description': 'مراقبة وضمان الجودة',
                    'parent': admin_departments['management'],
                },
                
                # أقسام المبيعات والتسويق
                'customers': {
                    'name': 'العملاء',
                    'code': 'customers',
                    'department_type': 'department',
                    'url_name': 'customers:customer_list',  # تحديث
                    'icon': 'fas fa-users',
                    'order': 1,
                    'description': 'إدارة بيانات وعلاقات العملاء',
                    'parent': admin_departments['sales'],
                },
                'orders': {
                    'name': 'الطلبات',
                    'code': 'orders',
                    'department_type': 'department',
                    'url_name': 'orders:order_list',  # تحديث
                    'icon': 'fas fa-shopping-cart',
                    'order': 2,
                    'description': 'إدارة طلبات العملاء',
                    'parent': admin_departments['sales'],
                },
                'marketing': {
                    'name': 'التسويق',
                    'code': 'marketing',
                    'department_type': 'department',
                    'icon': 'fas fa-bullhorn',
                    'order': 3,
                    'description': 'الأنشطة التسويقية والترويجية',
                    'parent': admin_departments['sales'],
                },
                
                # أقسام العمليات
                'inventory': {
                    'name': 'المخزون',
                    'code': 'inventory',
                    'department_type': 'department',
                    'url_name': 'inventory:dashboard',  # تحديث
                    'icon': 'fas fa-boxes',
                    'order': 1,
                    'description': 'إدارة المخزون والمستودعات',
                    'parent': admin_departments['operations'],
                },
                'factory': {
                    'name': 'المصنع',
                    'code': 'factory',
                    'department_type': 'department',
                    'url_name': 'factory:factory_list',  # تحديث
                    'icon': 'fas fa-industry',
                    'order': 2,
                    'description': 'إدارة عمليات التصنيع والإنتاج',
                    'parent': admin_departments['operations'],
                },
                'inspections': {
                    'name': 'المعاينات',
                    'code': 'inspections',
                    'department_type': 'department',
                    'url_name': 'inspections:inspection_list',  # تحديث
                    'icon': 'fas fa-clipboard-check',
                    'order': 3,
                    'description': 'إدارة عمليات المعاينة',
                    'parent': admin_departments['operations'],
                },
                'installations': {
                    'name': 'التركيبات',
                    'code': 'installations',
                    'department_type': 'department',
                    'url_name': 'installations:dashboard',  # تحديث
                    'icon': 'fas fa-tools',
                    'order': 4,
                    'description': 'إدارة عمليات التركيب',
                    'parent': admin_departments['operations'],
                },
                
                # أقسام الخدمات المساندة
                'hr': {
                    'name': 'الموارد البشرية',
                    'code': 'hr',
                    'department_type': 'department',
                    'icon': 'fas fa-user-friends',
                    'order': 1,
                    'description': 'إدارة شؤون الموظفين والتوظيف',
                    'parent': admin_departments['support'],
                },
                'finance': {
                    'name': 'الشؤون المالية',
                    'code': 'finance',
                    'department_type': 'department',
                    'icon': 'fas fa-money-bill-wave',
                    'order': 2,
                    'description': 'إدارة الشؤون المالية والمحاسبية',
                    'parent': admin_departments['support'],
                },
                'it': {
                    'name': 'تقنية المعلومات',
                    'code': 'it',
                    'department_type': 'department',
                    'icon': 'fas fa-laptop-code',
                    'order': 3,
                    'description': 'الدعم التقني وتطوير الأنظمة',
                    'parent': admin_departments['support'],
                },
                'reports': {
                    'name': 'التقارير',
                    'code': 'reports',
                    'department_type': 'department',
                    'url_name': 'reports:report_list',
                    'icon': 'fas fa-chart-bar',
                    'order': 4,
                    'description': 'إدارة وإعداد التقارير',
                    'parent': admin_departments['support'],
                },
            }
            
            # إنشاء الأقسام
            dept_objects = {}
            for code, data in departments_data.items():
                dept, created = Department.objects.update_or_create(
                    code=code,
                    defaults={
                        'name': data['name'],
                        'department_type': data['department_type'],
                        'icon': data.get('icon'),
                        'url_name': data.get('url_name'),
                        'parent': data.get('parent'),
                        'order': data.get('order', 0),
                        'description': data.get('description', ''),
                    }
                )
                dept_objects[code] = dept
                status = 'Created' if created else 'Updated'
                self.stdout.write(self.style.SUCCESS(f'{status} department: {dept.name}'))
                
            # إنشاء الوحدات (المستوى الثالث)
            units_data = {
                # وحدات قسم العملاء
                'vip_customers': {
                    'name': 'العملاء المميزين',
                    'code': 'vip_customers',
                    'department_type': 'unit',
                    'icon': 'fas fa-crown',
                    'order': 1,
                    'description': 'إدارة كبار العملاء والعملاء المميزين',
                    'parent': dept_objects['customers'],
                },
                'customer_service': {
                    'name': 'خدمة العملاء',
                    'code': 'customer_service',
                    'department_type': 'unit',
                    'icon': 'fas fa-headset',
                    'order': 2,
                    'description': 'دعم العملاء ومتابعة الشكاوى',
                    'parent': dept_objects['customers'],
                },
                
                # وحدات قسم المعاينات
                'inspection_scheduling': {
                    'name': 'جدولة المعاينات',
                    'code': 'inspection_scheduling',
                    'department_type': 'unit',
                    'icon': 'fas fa-calendar-alt',
                    'order': 1,
                    'description': 'تنظيم جداول المعاينات',
                    'parent': dept_objects['inspections'],
                },
                'technical_inspection': {
                    'name': 'المعاينة الفنية',
                    'code': 'technical_inspection',
                    'department_type': 'unit',
                    'icon': 'fas fa-hard-hat',
                    'order': 2,
                    'description': 'الفريق الفني للمعاينات',
                    'parent': dept_objects['inspections'],
                },
                
                # وحدات قسم المخزون
                'warehouse': {
                    'name': 'المستودعات',
                    'code': 'warehouse',
                    'department_type': 'unit',
                    'icon': 'fas fa-warehouse',
                    'order': 1,
                    'description': 'إدارة المستودعات',
                    'parent': dept_objects['inventory'],
                },
                'procurement': {
                    'name': 'المشتريات',
                    'code': 'procurement',
                    'department_type': 'unit',
                    'icon': 'fas fa-shopping-basket',
                    'order': 2,
                    'description': 'إدارة المشتريات والتوريدات',
                    'parent': dept_objects['inventory'],
                },
                
                # وحدات قسم الموارد البشرية
                'recruitment': {
                    'name': 'التوظيف',
                    'code': 'recruitment',
                    'department_type': 'unit',
                    'icon': 'fas fa-user-plus',
                    'order': 1,
                    'description': 'استقطاب وتوظيف الكفاءات',
                    'parent': dept_objects['hr'],
                },
                'training': {
                    'name': 'التدريب والتطوير',
                    'code': 'training',
                    'department_type': 'unit',
                    'icon': 'fas fa-graduation-cap',
                    'order': 2,
                    'description': 'تدريب وتطوير الموظفين',
                    'parent': dept_objects['hr'],
                },
                
                # وحدات قسم تقنية المعلومات
                'tech_support': {
                    'name': 'الدعم الفني',
                    'code': 'tech_support',
                    'department_type': 'unit',
                    'icon': 'fas fa-life-ring',
                    'order': 1,
                    'description': 'دعم المستخدمين وحل المشكلات التقنية',
                    'parent': dept_objects['it'],
                },
                'system_dev': {
                    'name': 'تطوير الأنظمة',
                    'code': 'system_dev',
                    'department_type': 'unit',
                    'icon': 'fas fa-code',
                    'order': 2,
                    'description': 'تطوير وتحسين أنظمة الشركة',
                    'parent': dept_objects['it'],
                },
            }
            
            # إنشاء الوحدات
            for code, data in units_data.items():
                unit, created = Department.objects.update_or_create(
                    code=code,
                    defaults={
                        'name': data['name'],
                        'department_type': data['department_type'],
                        'icon': data.get('icon'),
                        'url_name': data.get('url_name'),
                        'parent': data.get('parent'),
                        'order': data.get('order', 0),
                        'description': data.get('description', ''),
                    }
                )
                status = 'Created' if created else 'Updated'
                self.stdout.write(self.style.SUCCESS(f'{status} unit: {unit.name}'))
