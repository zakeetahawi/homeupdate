from django.core.management.base import BaseCommand
from django.db.models import F
from inspections.models import Inspection


class Command(BaseCommand):
    help = 'نسخ ملاحظات الطلبات إلى حقل order_notes في نموذج المعاينة'

    def handle(self, *args, **options):
        # الحصول على المعاينات التي لها طلبات مرتبطة وملاحظات
        inspections_with_orders = Inspection.objects.filter(
            order__isnull=False,
            order__notes__isnull=False,
            order_notes=''  # فقط المعاينات التي لم يتم ملء حقل order_notes بها بعد
        )
        
        count = 0
        for inspection in inspections_with_orders:
            if inspection.order and inspection.order.notes:
                inspection.order_notes = inspection.order.notes
                inspection.save(update_fields=['order_notes'])
                count += 1
        
        # طباعة النتائج
        self.stdout.write(
            self.style.SUCCESS(
                f'تم نسخ ملاحظات الطلبات بنجاح إلى {count} معاينة'
            )
        )