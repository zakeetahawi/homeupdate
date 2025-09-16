from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from accounts.models import Department

class Command(BaseCommand):
    help = 'Set up initial departments for the system'

    def handle(self, *args, **options):
        # Define departments
        departments = [
            {
                'name': 'العملاء',
                'code': 'customers',
                'icon': 'fas fa-users',
                'url_name': 'customers:customer_list',
                'order': 1,
                'description': 'إدارة العملاء وبياناتهم'
            },
            {
                'name': 'الطلبات',
                'code': 'orders',
                'icon': 'fas fa-shopping-cart',
                'url_name': 'orders:order_list',
                'order': 2,
                'description': 'إدارة طلبات العملاء'
            },
            {
                'name': 'المصنع',
                'code': 'factory',
                'icon': 'fas fa-industry',
                'url_name': 'factory:factory_list',
                'order': 3,
                'description': 'إدارة عمليات الإنتاج في المصنع'
            },
            {
                'name': 'المخزون',
                'code': 'inventory',
                'icon': 'fas fa-boxes',
                'url_name': 'inventory:inventory_list',
                'order': 4,
                'description': 'إدارة المخزون والمنتجات'
            },
            {
                'name': 'المعاينات',
                'code': 'inspections',
                'icon': 'fas fa-clipboard-check',
                'url_name': 'inspections:dashboard',
                'order': 5,
                'description': 'إدارة عمليات المعاينة'
            },
            {
                'name': 'التركيبات',
                'code': 'installations',
                'icon': 'fas fa-tools',
                'url_name': 'installations:dashboard',
                'order': 6,
                'description': 'إدارة عمليات التركيب'
            },
            {
                'name': 'الشكاوى',
                'code': 'complaints',
                'icon': 'fas fa-exclamation-triangle',
                'url_name': 'complaints:dashboard',
                'order': 7,
                'description': 'إدارة الشكاوى وخدمة العملاء'
            },
            {
                'name': 'التقارير',
                'code': 'reports',
                'icon': 'fas fa-chart-bar',
                'url_name': 'reports:report_list',
                'order': 8,
                'description': 'عرض وإنشاء التقارير'
            },
        ]
        
        # Create departments
        created_count = 0
        updated_count = 0
        
        for dept_data in departments:
            dept, created = Department.objects.update_or_create(
                code=dept_data['code'],
                defaults={
                    'name': dept_data['name'],
                    'icon': dept_data['icon'],
                    'url_name': dept_data['url_name'],
                    'order': dept_data['order'],
                    'description': dept_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created department: {dept.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated department: {dept.name}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully set up departments. Created: {created_count}, Updated: {updated_count}'
        ))
