from django.core.management.base import BaseCommand
from accounts.models import Department

class Command(BaseCommand):
    help = 'إنشاء الأقسام الافتراضية إذا لم تكن موجودة'

    def handle(self, *args, **kwargs):
        # قائمة الأقسام الافتراضية
        default_departments = [
            {'name': 'العملاء', 'url': '/customers/', 'icon': 'fa fa-users', 'order': 1},
            {'name': 'الطلبات', 'url': '/orders/', 'icon': 'fa fa-shopping-cart', 'order': 2},
            {'name': 'الفحوصات', 'url': '/inspections/', 'icon': 'fa fa-clipboard-check', 'order': 3},
            {'name': 'المخزون', 'url': '/inventory/', 'icon': 'fa fa-boxes', 'order': 4},
            {'name': 'التركيبات', 'url': '/installations/', 'icon': 'fa fa-tools', 'order': 5},
            {'name': 'المصنع', 'url': '/factory/', 'icon': 'fa fa-industry', 'order': 6},
            {'name': 'التقارير', 'url': '/reports/', 'icon': 'fa fa-chart-bar', 'order': 7},
            {'name': 'إدارة البيانات', 'url': '/data-management/', 'icon': 'fa fa-database', 'order': 8},
        ]
        
        # التحقق من وجود كل قسم وإنشائه إذا لم يكن موجودًا
        created_count = 0
        for dept in default_departments:
            department, created = Department.objects.get_or_create(
                name=dept['name'],
                defaults={
                    'url': dept['url'],
                    'icon': dept['icon'],
                    'order': dept['order']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'تم إنشاء قسم "{dept["name"]}" بنجاح'))
            else:
                # تحديث الحقول الأخرى إذا تغيرت
                updated = False
                for field in ['url', 'icon', 'order']:
                    if getattr(department, field) != dept[field]:
                        setattr(department, field, dept[field])
                        updated = True
                
                if updated:
                    department.save()
                    self.stdout.write(self.style.WARNING(f'تم تحديث قسم "{dept["name"]}"'))
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f'تم إنشاء {created_count} قسم جديد'))
        else:
            self.stdout.write(self.style.SUCCESS('جميع الأقسام موجودة بالفعل'))
