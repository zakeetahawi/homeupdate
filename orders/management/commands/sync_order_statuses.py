from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import Order
from manufacturing.models import ManufacturingOrder


class Command(BaseCommand):
    help = 'مزامنة حالات الطلبات مع حالات التصنيع'

    def handle(self, *args, **options):
        """مزامنة حالات الطلبات مع حالات التصنيع"""
        
        self.stdout.write(
            self.style.SUCCESS('بدء مزامنة حالات الطلبات...')
        )
        
        updated_count = 0
        
        # الحصول على جميع أوامر التصنيع
        manufacturing_orders = ManufacturingOrder.objects.select_related('order').all()
        
        with transaction.atomic():
            for mfg_order in manufacturing_orders:
                try:
                    order = mfg_order.order
                    old_status = order.order_status
                    
                    # تحديث حالة الطلب لتتطابق مع حالة التصنيع
                    order.order_status = mfg_order.status
                    
                    # تحديث tracking_status بناءً على حالة التصنيع
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
                    
                    if mfg_order.status in status_mapping:
                        order.tracking_status = status_mapping[mfg_order.status]
                    
                    order.save(update_fields=['order_status', 'tracking_status'])
                    
                    if old_status != mfg_order.status:
                        updated_count += 1
                        self.stdout.write(
                            f'تم تحديث الطلب #{order.order_number}: '
                            f'{old_status} -> {mfg_order.status}'
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'خطأ في تحديث الطلب #{order.order_number}: {str(e)}'
                        )
                    )
        
        # تحديث الطلبات التي لا تحتوي على أوامر تصنيع
        orders_without_manufacturing = Order.objects.filter(
            manufacturing_order__isnull=True
        )
        
        for order in orders_without_manufacturing:
            if order.order_status != 'pending':
                order.order_status = 'pending'
                order.save(update_fields=['order_status'])
                updated_count += 1
                self.stdout.write(
                    f'تم تحديث الطلب #{order.order_number} إلى حالة الانتظار'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'تم الانتهاء من المزامنة. تم تحديث {updated_count} طلب.'
            )
        ) 