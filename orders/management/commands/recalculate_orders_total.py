from django.core.management.base import BaseCommand

from orders.models import Order


class Command(BaseCommand):
    help = "إعادة حساب المبلغ الإجمالي والسعر النهائي لكل الطلبات بناءً على عناصر الطلب"

    def handle(self, *args, **options):
        updated = 0
        for order in Order.objects.all():
            # حساب السعر النهائي من عناصر الطلب
            final_price = order.calculate_final_price()
            order.final_price = final_price
            order.total_amount = final_price
            order.save(update_fields=["final_price", "total_amount"])
            updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"تم تحديث وإعادة حساب المبلغ الإجمالي والسعر النهائي لـ {updated} طلب."
            )
        )
