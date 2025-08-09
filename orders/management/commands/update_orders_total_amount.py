from django.core.management.base import BaseCommand
from orders.models import Order

class Command(BaseCommand):
    help = 'تحديث المبلغ الإجمالي لكل الطلبات ليطابق السعر النهائي'

    def handle(self, *args, **options):
        updated = 0
        for order in Order.objects.all():
            if order.final_price != order.total_amount:
                order.total_amount = order.final_price or 0
                order.save(update_fields=['total_amount'])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f'تم تحديث {updated} طلب ليطابق المبلغ الإجمالي السعر النهائي.'))
