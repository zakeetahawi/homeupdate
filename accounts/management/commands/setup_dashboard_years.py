"""
أمر لإعداد السنوات الافتراضية للداش بورد
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import DashboardYearSettings


class Command(BaseCommand):
    help = 'إعداد السنوات الافتراضية للداش بورد'

    def add_arguments(self, parser):
        parser.add_argument(
            '--years',
            type=str,
            help='السنوات المراد إضافتها (مفصولة بفواصل)',
            default='2023,2024,2025,2026'
        )
        parser.add_argument(
            '--default-year',
            type=int,
            help='السنة الافتراضية',
            default=None
        )

    def handle(self, *args, **options):
        years_str = options['years']
        default_year = options['default_year']
        
        # تحويل السلسلة إلى قائمة سنوات
        years_list = [int(year.strip()) for year in years_str.split(',')]
        
        self.stdout.write(
            self.style.SUCCESS(f'بدء إعداد السنوات: {years_list}')
        )
        
        created_count = 0
        updated_count = 0
        
        for year in years_list:
            year_obj, created = DashboardYearSettings.objects.get_or_create(
                year=year,
                defaults={
                    'is_active': True,
                    'is_default': False,
                    'description': f'سنة {year}'
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'تم إنشاء سنة {year}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'سنة {year} موجودة بالفعل')
                )
        
        # تعيين السنة الافتراضية
        if default_year:
            try:
                default_obj = DashboardYearSettings.objects.get(year=default_year)
                default_obj.is_default = True
                default_obj.save()
                self.stdout.write(
                    self.style.SUCCESS(f'تم تعيين سنة {default_year} كافتراضية')
                )
            except DashboardYearSettings.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'سنة {default_year} غير موجودة')
                )
        else:
            # تعيين السنة الحالية كافتراضية إذا لم يتم تحديد سنة
            current_year = timezone.now().year
            try:
                current_obj = DashboardYearSettings.objects.get(year=current_year)
                current_obj.is_default = True
                current_obj.save()
                self.stdout.write(
                    self.style.SUCCESS(f'تم تعيين سنة {current_year} كافتراضية')
                )
            except DashboardYearSettings.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'سنة {current_year} غير موجودة في القائمة')
                )
        
        # عرض الإحصائيات النهائية
        total_years = DashboardYearSettings.objects.count()
        active_years = DashboardYearSettings.objects.filter(is_active=True).count()
        default_year_obj = DashboardYearSettings.objects.filter(is_default=True).first()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ تم إكمال الإعداد بنجاح!\n'
                f'📊 إحصائيات السنوات:\n'
                f'   - إجمالي السنوات: {total_years}\n'
                f'   - السنوات النشطة: {active_years}\n'
                f'   - السنة الافتراضية: {default_year_obj.year if default_year_obj else "غير محدد"}\n'
                f'   - السنوات الجديدة: {created_count}\n'
                f'   - السنوات المحدثة: {updated_count}'
            )
        ) 