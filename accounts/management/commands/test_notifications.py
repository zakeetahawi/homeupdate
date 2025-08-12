"""
أمر لاختبار نظام الإشعارات الجديد
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.services.simple_notifications import SimpleNotificationService
from orders.models import Order

User = get_user_model()


class Command(BaseCommand):
    help = 'اختبار نظام الإشعارات الجماعية الجديد'

    def add_arguments(self, parser):
        parser.add_argument(
            '--order-id',
            type=int,
            help='معرف الطلب لاختبار الإشعار'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 بدء اختبار نظام الإشعارات الجماعية...')
        )

        # الحصول على طلب للاختبار
        order_id = options.get('order_id')
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ الطلب رقم {order_id} غير موجود')
                )
                return
        else:
            # الحصول على أول طلب متاح
            order = Order.objects.first()
            if not order:
                self.stdout.write(
                    self.style.ERROR('❌ لا توجد طلبات في النظام')
                )
                return

        self.stdout.write(f'📋 اختبار الطلب: {order.order_number}')

        # اختبار إنشاء إشعار جماعي
        notification = SimpleNotificationService.create_unique_group_notification(
            title=f'اختبار إشعار جماعي للطلب {order.order_number}',
            message=f'هذا إشعار تجريبي لاختبار النظام الجديد للطلب {order.order_number}',
            notification_type='order_status_changed',
            order_number=order.order_number,
            customer_name=order.customer.name if order.customer else 'عميل تجريبي',
            priority='normal',
            target_users=User.objects.filter(is_active=True)[:5],  # أول 5 مستخدمين
            related_object=order
        )

        if notification:
            self.stdout.write(
                self.style.SUCCESS(f'✅ تم إنشاء الإشعار الجماعي بنجاح: {notification.id}')
            )
            self.stdout.write(f'📊 عدد المستخدمين المستهدفين: {notification.target_users.count()}')
            
            # اختبار محاولة إنشاء نفس الإشعار مرة أخرى
            duplicate_notification = SimpleNotificationService.create_unique_group_notification(
                title=f'اختبار إشعار جماعي للطلب {order.order_number}',
                message=f'هذا إشعار تجريبي لاختبار النظام الجديد للطلب {order.order_number}',
                notification_type='order_status_changed',
                order_number=order.order_number,
                customer_name=order.customer.name if order.customer else 'عميل تجريبي',
                priority='normal',
                target_users=User.objects.filter(is_active=True)[:5],
                related_object=order
            )
            
            if duplicate_notification.id == notification.id:
                self.stdout.write(
                    self.style.SUCCESS('✅ منع التكرار يعمل بشكل صحيح - تم إرجاع نفس الإشعار')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️ تم إنشاء إشعار مكرر - قد تحتاج لمراجعة منطق منع التكرار')
                )

            # عرض معلومات الإشعار
            self.stdout.write('\n📋 معلومات الإشعار:')
            self.stdout.write(f'   العنوان: {notification.title}')
            self.stdout.write(f'   النوع: {notification.get_notification_type_display()}')
            self.stdout.write(f'   الأولوية: {notification.get_priority_display()}')
            self.stdout.write(f'   تاريخ الإنشاء: {notification.created_at}')
            self.stdout.write(f'   عدد القراءات: {notification.get_read_count()}')
            self.stdout.write(f'   عدد غير المقروء: {notification.get_unread_count()}')

            # اختبار تحديد كمقروء
            first_user = notification.target_users.first()
            if first_user:
                notification.mark_as_read_by_user(first_user)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ تم تحديد الإشعار كمقروء للمستخدم: {first_user.username}')
                )
                self.stdout.write(f'📊 عدد القراءات الجديد: {notification.get_read_count()}')

        else:
            self.stdout.write(
                self.style.ERROR('❌ فشل في إنشاء الإشعار الجماعي')
            )

        # اختبار إشعار تغيير الحالة
        self.stdout.write('\n🔄 اختبار إشعار تغيير الحالة...')
        status_notification = SimpleNotificationService.notify_order_status_change_unique(
            order=order,
            old_status='pending',
            new_status='in_progress',
            changed_by=User.objects.first()
        )

        if status_notification:
            self.stdout.write(
                self.style.SUCCESS(f'✅ تم إنشاء إشعار تغيير الحالة: {status_notification.id}')
            )
        else:
            self.stdout.write(
                self.style.ERROR('❌ فشل في إنشاء إشعار تغيير الحالة')
            )

        self.stdout.write(
            self.style.SUCCESS('\n🎉 انتهى اختبار نظام الإشعارات الجماعية!')
        )
        self.stdout.write('💡 يمكنك الآن زيارة صفحة الإشعارات لرؤية النتائج')
