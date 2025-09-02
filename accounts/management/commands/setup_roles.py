from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import Role, User, Department
from django.db.models import Q

class Command(BaseCommand):
    help = 'إعداد الأدوار والصلاحيات الافتراضية للنظام'

    def handle(self, *args, **options):
        self.stdout.write('بدء إعداد أدوار النظام والصلاحيات...')
        
        # إنشاء دور المدير الأعلى (Super Admin)
        superadmin_role, created = Role.objects.get_or_create(
            name='مدير النظام',
            defaults={
                'description': 'الصلاحيات الكاملة على النظام',
                'is_system_role': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('تم إنشاء دور مدير النظام'))
        
        # إنشاء دور المدير (Admin)
        admin_role, created = Role.objects.get_or_create(
            name='مدير',
            defaults={
                'description': 'صلاحيات إدارية على معظم الميزات',
                'is_system_role': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('تم إنشاء دور المدير'))
        
        # إنشاء دور مدير المبيعات
        sales_manager_role, created = Role.objects.get_or_create(
            name='مدير مبيعات',
            defaults={
                'description': 'صلاحيات على المبيعات والعملاء',
                'is_system_role': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('تم إنشاء دور مدير المبيعات'))
        
        # إنشاء دور فني المعاينة
        inspection_tech_role, created = Role.objects.get_or_create(
            name='فني معاينة',
            defaults={
                'description': 'صلاحيات تتعلق بالمعاينات',
                'is_system_role': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('تم إنشاء دور فني المعاينة'))
        
        # إنشاء دور فني التركيب
        installation_tech_role, created = Role.objects.get_or_create(
            name='فني تركيب',
            defaults={
                'description': 'صلاحيات تتعلق بالتركيبات',
                'is_system_role': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('تم إنشاء دور فني التركيب'))
            
        # إنشاء دور مسؤول المخزون
        inventory_manager_role, created = Role.objects.get_or_create(
            name='مسؤول المخزون',
            defaults={
                'description': 'صلاحيات على المخزون والمنتجات',
                'is_system_role': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('تم إنشاء دور مسؤول المخزون'))
        
        # إنشاء دور مسؤول المصنع
        factory_manager_role, created = Role.objects.get_or_create(
            name='مسؤول المصنع',
            defaults={
                'description': 'صلاحيات على المصنع والإنتاج',
                'is_system_role': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('تم إنشاء دور مسؤول المصنع'))
        
        # إنشاء دور موظف مبيعات
        sales_employee_role, created = Role.objects.get_or_create(
            name='موظف مبيعات',
            defaults={
                'description': 'صلاحيات محدودة للعمل على المبيعات',
                'is_system_role': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('تم إنشاء دور موظف مبيعات'))
        
        # إضافة الصلاحيات لدور المدير الأعلى (جميع الصلاحيات)
        all_permissions = Permission.objects.all()
        superadmin_role.permissions.set(all_permissions)
        self.stdout.write(self.style.SUCCESS(f'تم إضافة {all_permissions.count()} صلاحية لدور مدير النظام'))
        
        # إضافة صلاحيات دور المدير
        admin_permissions = Permission.objects.exclude(
            Q(content_type__app_label='contenttypes') | 
            Q(content_type__app_label='sessions') | 
            Q(content_type__app_label='admin') |
            Q(codename__startswith='delete')
        )
        admin_role.permissions.set(admin_permissions)
        self.stdout.write(self.style.SUCCESS(f'تم إضافة {admin_permissions.count()} صلاحية لدور المدير'))
        
        # إضافة صلاحيات مدير المبيعات
        sales_apps = ['customers', 'orders']
        customer_ct = ContentType.objects.get_for_model(Department)
        sales_permissions = Permission.objects.filter(
            Q(content_type__app_label__in=sales_apps) |
            Q(content_type=customer_ct)
        )
        sales_manager_role.permissions.set(sales_permissions)
        self.stdout.write(self.style.SUCCESS(f'تم إضافة {sales_permissions.count()} صلاحية لدور مدير المبيعات'))
        
        # إضافة صلاحيات فني المعاينة
        inspection_apps = ['inspections']
        inspection_permissions = Permission.objects.filter(
            content_type__app_label__in=inspection_apps
        ).exclude(
            codename__startswith='delete'
        )
        inspection_tech_role.permissions.set(inspection_permissions)
        self.stdout.write(self.style.SUCCESS(f'تم إضافة {inspection_permissions.count()} صلاحية لدور فني المعاينة'))
        
        # إضافة صلاحيات فني التركيب
        installation_apps = ['installations']
        installation_permissions = Permission.objects.filter(
            content_type__app_label__in=installation_apps
        ).exclude(
            codename__startswith='delete'
        )
        installation_tech_role.permissions.set(installation_permissions)
        self.stdout.write(self.style.SUCCESS(f'تم إضافة {installation_permissions.count()} صلاحية لدور فني التركيب'))
        
        # إضافة صلاحيات مسؤول المخزون
        inventory_apps = ['inventory']
        inventory_permissions = Permission.objects.filter(
            content_type__app_label__in=inventory_apps
        )
        inventory_manager_role.permissions.set(inventory_permissions)
        self.stdout.write(self.style.SUCCESS(f'تم إضافة {inventory_permissions.count()} صلاحية لدور مسؤول المخزون'))
        
        # إضافة صلاحيات مسؤول المصنع
        factory_apps = ['factory']
        factory_permissions = Permission.objects.filter(
            content_type__app_label__in=factory_apps
        )
        factory_manager_role.permissions.set(factory_permissions)
        self.stdout.write(self.style.SUCCESS(f'تم إضافة {factory_permissions.count()} صلاحية لدور مسؤول المصنع'))
        
        # إضافة صلاحيات موظف المبيعات (قراءة وإنشاء فقط)
        sales_employee_permissions = Permission.objects.filter(
            Q(content_type__app_label__in=sales_apps) &
            (Q(codename__startswith='view') | Q(codename__startswith='add'))
        )
        sales_employee_role.permissions.set(sales_employee_permissions)
        self.stdout.write(self.style.SUCCESS(f'تم إضافة {sales_employee_permissions.count()} صلاحية لدور موظف المبيعات'))
        
        # إسناد دور المدير الأعلى للمستخدمين المشرفين الحاليين إذا وجد
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            superadmin_role.assign_to_user(user)
            self.stdout.write(self.style.SUCCESS(f'تم إسناد دور مدير النظام للمستخدم {user.username}'))
        
        self.stdout.write(self.style.SUCCESS('اكتمل إعداد الأدوار والصلاحيات بنجاح!'))