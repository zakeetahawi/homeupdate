"""
Command لإنشاء إشعارات تجريبية للاختبار
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.services.simple_notifications import SimpleNotificationService

User = get_user_model()


class Command(BaseCommand):
    help = 'إنشاء إشعارات تجريبية للاختبار'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID المستخدم المراد إرسال الإشعارات إليه'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='عدد الإشعارات المراد إنشاؤها (افتراضي: 5)'
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        count = options.get('count', 5)

        # تحديد المستخدم
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'المستخدم بـ ID {user_id} غير موجود')
                )
                return
        else:
            # استخدام أول مستخدم superuser
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                self.stdout.write(
                    self.style.ERROR('لا يوجد مستخدم superuser في النظام')
                )
                return

        self.stdout.write(f'إنشاء {count} إشعارات تجريبية للمستخدم: {user.username}')

        # إنشاء إشعارات تجريبية متنوعة
        test_notifications = [
            {
                'customer_name': 'أحمد محمد',
                'order_number': 'ORD-2024-001',
                'status': 'تم إنشاء الطلب بنجاح',
                'notification_type': 'order_created',
                'priority': 'normal'
            },
            {
                'customer_name': 'فاطمة علي',
                'order_number': 'ORD-2024-002',
                'status': 'معاينة مجدولة غداً',
                'notification_type': 'inspection_scheduled',
                'priority': 'high'
            },
            {
                'customer_name': 'محمد حسن',
                'order_number': 'ORD-2024-003',
                'status': 'بدء عملية التصنيع',
                'notification_type': 'manufacturing_started',
                'priority': 'normal'
            },
            {
                'customer_name': 'سارة أحمد',
                'order_number': 'ORD-2024-004',
                'status': 'تم اكتمال الطلب',
                'notification_type': 'order_completed',
                'priority': 'low'
            },
            {
                'customer_name': 'خالد محمود',
                'order_number': 'ORD-2024-005',
                'status': 'طلب عاجل - يتطلب اهتمام فوري',
                'notification_type': 'order_updated',
                'priority': 'urgent'
            },
            {
                'customer_name': 'نور الدين',
                'order_number': 'ORD-2024-006',
                'status': 'تم إلغاء الطلب',
                'notification_type': 'order_cancelled',
                'priority': 'normal'
            },
            {
                'customer_name': 'ليلى عبدالله',
                'order_number': 'ORD-2024-007',
                'status': 'تم تركيب الطلب بنجاح',
                'notification_type': 'installation_completed',
                'priority': 'low'
            }
        ]

        created_count = 0
        for i in range(count):
            # اختيار إشعار من القائمة (مع التكرار إذا لزم الأمر)
            notification_data = test_notifications[i % len(test_notifications)]
            
            # تعديل رقم الطلب ليكون فريد
            notification_data['order_number'] = f"ORD-2024-{str(i+1).zfill(3)}"
            
            try:
                notification = SimpleNotificationService.create_order_notification(
                    customer_name=notification_data['customer_name'],
                    order_number=notification_data['order_number'],
                    status=notification_data['status'],
                    notification_type=notification_data['notification_type'],
                    priority=notification_data['priority'],
                    recipient=user
                )
                
                if notification:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ تم إنشاء إشعار: {notification.title}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠️ فشل في إنشاء إشعار: {notification_data["customer_name"]}'
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ خطأ في إنشاء إشعار: {str(e)}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 تم إنشاء {created_count} إشعار بنجاح من أصل {count} مطلوب'
            )
        )
        self.stdout.write(
            f'👤 المستخدم: {user.username} (ID: {user.id})'
        )
