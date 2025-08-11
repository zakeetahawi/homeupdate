"""
أمر إنشاء إشعارات للطلب الأخير
Create Order Notifications Command
"""

from django.core.management.base import BaseCommand
from orders.models import Order
from accounts.services.simple_notifications import SimpleNotificationService


class Command(BaseCommand):
    help = 'إنشاء إشعارات للطلب الأخير'

    def add_arguments(self, parser):
        parser.add_argument(
            '--order-id',
            type=int,
            help='معرف الطلب المحدد'
        )

    def handle(self, *args, **options):
        order_id = options.get('order_id')
        
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'الطلب {order_id} غير موجود')
                )
                return
        else:
            # الحصول على آخر طلب
            order = Order.objects.last()
            if not order:
                self.stdout.write(
                    self.style.ERROR('لا توجد طلبات في النظام')
                )
                return
        
        self.stdout.write(
            self.style.SUCCESS(f'إنشاء إشعارات للطلب: {order.order_number}')
        )
        
        # إنشاء إشعارات للطلب
        notifications = SimpleNotificationService.notify_new_order(order)
        
        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء {len(notifications)} إشعار')
        )
        
        # عرض الإشعارات
        for notification in notifications:
            self.stdout.write(
                f'- {notification.title} للمستخدم {notification.recipient.username}'
            )
