from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F, Q

from orders.models import Order
from manufacturing.models import ManufacturingOrder


class Command(BaseCommand):
    help = 'مزامنة حالات الطلبات مع حالات التصنيع (مُحسَّنة: تطبع تقدم وتحدّث فقط الاختلافات)'

    def handle(self, *args, **options):
        """مزامنة حالات الطلبات مع حالات التصنيع بشكل مُحسَّن"""

        self.stdout.write(self.style.SUCCESS('بدء مزامنة حالات الطلبات...'))

        updated_count = 0
        status_mapping = {
            'pending_approval': 'factory',
            'pending': 'factory',
            'in_progress': 'factory',
            'ready_install': 'ready',
            'completed': 'ready',
            'delivered': 'delivered',
            'rejected': 'factory',
            'cancelled': 'factory',
        }

        # تحديث فقط أوامر التصنيع التي تختلف عن حالة الطلب
        mismatch_qs = ManufacturingOrder.objects.filter(~Q(status=F('order__order_status'))).select_related('order')
        total_mismatch = mismatch_qs.count()
        self.stdout.write(f'عدد أوامر التصنيع التي تحتاج تحديث: {total_mismatch}')

        processed = 0
        batch = 500
        with transaction.atomic():
            for i, mfg_order in enumerate(mismatch_qs.iterator(), 1):
                try:
                    order = mfg_order.order
                    old_status = order.order_status
                    order.order_status = mfg_order.status
                    if mfg_order.status in status_mapping:
                        order.tracking_status = status_mapping[mfg_order.status]
                    order.save(update_fields=['order_status', 'tracking_status'])
                    updated_count += 1
                    processed += 1
                    if i % batch == 0 or i == total_mismatch:
                        self.stdout.write(f'المعالَجة: {i}/{total_mismatch} أوامر تصنيع (محدثة {processed})')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'خطأ في تحديث الطلب #{getattr(order, "order_number", order.pk)}: {e}'))

        # الآن معالجة الطلبات التي لا تحتوي على أوامر تصنيع
        # سنحدد الحالة المطلوبة لكل طلب: اذا كان من نوع معاينة ولديه معاينة مكتملة ناجحة -> مكتمل، وإلا -> انتظار
        orders_needing = Order.objects.filter(manufacturing_order__isnull=True)
        total_no_mfg = orders_needing.count()
        self.stdout.write(f'عدد الطلبات بدون تصنيع: {total_no_mfg}')

        processed_no_mfg = 0
        for j, order in enumerate(orders_needing.iterator(), 1):
            try:
                target_status = 'pending'
                try:
                    selected = order.get_selected_types_list()
                except Exception:
                    selected = []

                if 'inspection' in selected:
                    insp = order.inspections.first()
                    if insp and insp.status == 'completed' and insp.result == 'passed':
                        target_status = 'completed'

                if order.order_status != target_status:
                    order.order_status = target_status
                    order.save(update_fields=['order_status'])
                    updated_count += 1
                    processed_no_mfg += 1
                    if j % batch == 0:
                        self.stdout.write(f'المعالَجة بدون تصنيع: {j}/{total_no_mfg} (محدثة {processed_no_mfg})')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'خطأ عند مزامنة الطلب #{getattr(order, "order_number", order.pk)}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'تم الانتهاء من المزامنة. إجمالي الطلبات المحدثة: {updated_count}'))