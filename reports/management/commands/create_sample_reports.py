from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from reports.models import Report

class Command(BaseCommand):
    help = 'Creates sample reports for testing'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        user = User.objects.first()

        if not user:
            self.stdout.write(self.style.ERROR('No user found in the system. Please create a user first.'))
            return

        reports_data = [
            {
                'title': 'تقرير المبيعات الشهري',
                'report_type': 'sales',
                'description': 'تقرير شامل عن المبيعات خلال الشهر الماضي',
                'parameters': {'date_range': 30},
                'created_by': user
            },
            {
                'title': 'تقرير الإنتاج الأسبوعي',
                'report_type': 'production',
                'description': 'تقرير عن حالة الإنتاج الأسبوعي',
                'parameters': {'date_range': 7},
                'created_by': user
            },
            {
                'title': 'تقرير المخزون',
                'report_type': 'inventory',
                'description': 'تقرير عن حالة المخزون الحالية',
                'parameters': {},
                'created_by': user
            },
            {
                'title': 'التقرير المالي الشهري',
                'report_type': 'financial',
                'description': 'تقرير مالي شامل للشهر الماضي',
                'parameters': {'date_range': 30},
                'created_by': user
            }
        ]

        for data in reports_data:
            Report.objects.create(**data)
        
        self.stdout.write(self.style.SUCCESS('تم إنشاء التقارير بنجاح'))
