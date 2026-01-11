from django.core.management.base import BaseCommand
from django.db import transaction

from inspections.models import Inspection
from orders.models import Order


class Command(BaseCommand):
    help = "إصلاح رقم الطلب للمعاينات المرتبطة بطلبات ليس لها رقم طلب (order_number)"

    def handle(self, *args, **options):
        fixed_count = 0
        with transaction.atomic():
            inspections = Inspection.objects.filter(
                order__isnull=False, is_from_orders=True
            )
            for inspection in inspections:
                order = inspection.order
                if order and (
                    not order.order_number or str(order.order_number).lower() == "none"
                ):
                    old_number = order.order_number
                    order.order_number = order.generate_unique_order_number()
                    order.save(update_fields=["order_number"])
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"تم إصلاح رقم الطلب للطلب المرتبط بالمعاينة {inspection.id}: القديم={old_number}, الجديد={order.order_number}"
                        )
                    )
        if fixed_count == 0:
            self.stdout.write(
                self.style.WARNING("لا توجد طلبات بحاجة لإصلاح رقم الطلب.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"تم إصلاح رقم الطلب في {fixed_count} طلب/معاينة بنجاح."
                )
            )
