from django.core.management.base import BaseCommand
from django.db import transaction
from complaints.models import ComplaintType


class Command(BaseCommand):
    help = 'إعداد أنواع الشكاوى الأولية في النظام'

    def handle(self, *args, **options):
        complaint_types = [
            {
                'name': 'مشكلة في المنتج',
                'description': 'شكاوى متعلقة بجودة أو عيوب في المنتجات',
                'is_active': True,
            },
            {
                'name': 'مشكلة في التسليم',
                'description': 'شكاوى متعلقة بتأخير أو مشاكل في التسليم',
                'is_active': True,
            },
            {
                'name': 'مشكلة في التركيب',
                'description': 'شكاوى متعلقة بعملية التركيب أو المُركبين',
                'is_active': True,
            },
            {
                'name': 'مشكلة في المعاينة',
                'description': 'شكاوى متعلقة بعملية المعاينة أو المُعاينين',
                'is_active': True,
            },
            {
                'name': 'مشكلة في الخدمة',
                'description': 'شكاوى متعلقة بجودة الخدمة المقدمة',
                'is_active': True,
            },
            {
                'name': 'مشكلة مالية',
                'description': 'شكاوى متعلقة بالفواتير أو الدفعات',
                'is_active': True,
            },
            {
                'name': 'طلب إرجاع',
                'description': 'طلبات إرجاع المنتجات أو إلغاء الطلبات',
                'is_active': True,
            },
            {
                'name': 'شكوى عامة',
                'description': 'شكاوى عامة أخرى',
                'is_active': True,
            },
        ]

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for complaint_type_data in complaint_types:
                complaint_type, created = ComplaintType.objects.get_or_create(
                    name=complaint_type_data['name'],
                    defaults=complaint_type_data
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Created complaint type: {complaint_type.name}')
                    )
                else:
                    # تحديث البيانات الموجودة
                    for key, value in complaint_type_data.items():
                        if key != 'name':  # لا نُحدث الاسم
                            setattr(complaint_type, key, value)
                    complaint_type.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'Updated complaint type: {complaint_type.name}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up complaint types. '
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )
