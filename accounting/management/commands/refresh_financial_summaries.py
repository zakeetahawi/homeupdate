"""
أمر إدارة لتحديث الملخصات المالية لجميع العملاء
Management command to refresh all customer financial summaries
"""
from django.core.management.base import BaseCommand
from accounting.models import CustomerFinancialSummary
from customers.models import Customer


class Command(BaseCommand):
    help = 'تحديث الملخصات المالية لجميع العملاء'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='تحديث جميع العملاء حتى الذين ليس لديهم طلبات'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='الحد الأقصى لعدد العملاء المراد تحديثهم (0 = بدون حد)'
        )
    
    def handle(self, *args, **options):
        self.stdout.write('بدء تحديث الملخصات المالية...')
        
        if options['all']:
            customers = Customer.objects.all()
        else:
            customers = Customer.objects.filter(customer_orders__isnull=False).distinct()
        
        total = customers.count()
        
        if options['limit'] > 0:
            customers = customers[:options['limit']]
            self.stdout.write(f'تحديث {options["limit"]} عميل من أصل {total}')
        else:
            self.stdout.write(f'تحديث {total} عميل')
        
        count = 0
        errors = 0
        
        for customer in customers:
            try:
                summary, created = CustomerFinancialSummary.objects.get_or_create(
                    customer=customer
                )
                summary.refresh()
                count += 1
                
                if count % 100 == 0:
                    self.stdout.write(f'تم معالجة {count}...')
            except Exception as e:
                errors += 1
                self.stderr.write(f'خطأ في العميل {customer.pk}: {str(e)}')
        
        self.stdout.write(
            self.style.SUCCESS(f'تم تحديث {count} ملخص مالي بنجاح ({errors} أخطاء)')
        )
        
        # إحصائيات
        summaries = CustomerFinancialSummary.objects.all()
        self.stdout.write(f'إجمالي الملخصات: {summaries.count()}')
        self.stdout.write(f'عملاء مدينون: {summaries.filter(total_debt__gt=0).count()}')
        self.stdout.write(f'عملاء دائنون: {summaries.filter(total_debt__lt=0).count()}')
        self.stdout.write(f'عملاء صافي: {summaries.filter(total_debt=0).count()}')
