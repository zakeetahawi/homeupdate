"""
إنشاء بروفايلات مهندسي الديكور تلقائياً لجميع العملاء من نوع 'designer'
الذين ليس لديهم بروفايل بعد.
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from customers.models import Customer
from external_sales.models import DecoratorEngineerProfile


class Command(BaseCommand):
    help = "إنشاء DecoratorEngineerProfile لجميع العملاء من نوع designer بدون بروفايل"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض ما سيتم إنشاؤه بدون تنفيذ فعلي",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # العملاء من نوع designer بدون بروفايل
        designers_without_profile = Customer.objects.filter(
            customer_type="designer"
        ).exclude(
            pk__in=DecoratorEngineerProfile.objects.values_list("customer_id", flat=True)
        ).select_related("branch")

        count = designers_without_profile.count()
        self.stdout.write(f"عملاء نوع designer بدون بروفايل: {count}")

        if count == 0:
            self.stdout.write(self.style.SUCCESS("لا يوجد عملاء بحاجة لبروفايل."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("-- وضع المعاينة (dry-run) --"))
            for c in designers_without_profile:
                self.stdout.write(f"  سيُنشأ: {c.name} (pk={c.pk}, branch={c.branch})")
            return

        created = 0
        for customer in designers_without_profile:
            DecoratorEngineerProfile.objects.create(
                customer=customer,
                city=customer.branch.name if customer.branch else "",
                priority="regular",
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"تم إنشاء {created} بروفايل مهندس ديكور بنجاح.")
        )
