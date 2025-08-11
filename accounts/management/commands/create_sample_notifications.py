"""
أمر إنشاء إشعارات تجريبية لاختبار النظام 🎨
Create Sample Notifications Command
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import SimpleNotification, ComplaintNotification
from accounts.services.simple_notifications import SimpleNotificationService
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'إنشاء إشعارات تجريبية لاختبار النظام الجديد'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='عدد الإشعارات المراد إنشاؤها (افتراضي: 10)'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='اسم المستخدم المحدد (افتراضي: جميع المستخدمين النشطين)'
        )

    def handle(self, *args, **options):
        count = options['count']
        username = options.get('user')
        
        self.stdout.write(
            self.style.SUCCESS(f'🎨 إنشاء {count} إشعار تجريبي...')
        )
        
        # الحصول على المستخدمين
        if username:
            try:
                users = [User.objects.get(username=username)]
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'المستخدم {username} غير موجود')
                )
                return
        else:
            users = User.objects.filter(is_active=True, is_superuser=False)[:5]
        
        if not users:
            self.stdout.write(
                self.style.ERROR('لا توجد مستخدمين نشطين')
            )
            return
        
        # بيانات تجريبية
        customers = [
            'أحمد محمد علي',
            'فاطمة أحمد',
            'محمد عبدالله',
            'سارة محمود',
            'خالد أحمد',
            'نور الدين',
            'عائشة حسن',
            'يوسف إبراهيم',
            'زينب علي',
            'عمر محمد'
        ]
        
        order_statuses = [
            'في قائمة الانتظار',
            'قيد المعالجة',
            'قيد التصنيع',
            'جاهز للتسليم',
            'تم التسليم',
            'قيد المراجعة'
        ]
        
        notification_types = [
            'order_created',
            'order_updated',
            'order_completed',
            'inspection_scheduled',
            'manufacturing_started',
            'installation_completed'
        ]
        
        priorities = ['low', 'normal', 'high', 'urgent']
        
        complaint_types = ['new', 'assigned', 'in_progress', 'resolved', 'escalated']
        complaint_priorities = ['low', 'medium', 'high', 'critical']
        
        created_notifications = 0
        created_complaints = 0
        
        # إنشاء إشعارات الطلبات
        for i in range(count):
            user = random.choice(users)
            customer = random.choice(customers)
            order_number = f"#1-0001-{1000 + i:04d}"
            status = random.choice(order_statuses)
            notification_type = random.choice(notification_types)
            priority = random.choice(priorities)
            
            notification = SimpleNotificationService.create_order_notification(
                customer_name=customer,
                order_number=order_number,
                status=status,
                notification_type=notification_type,
                priority=priority,
                recipient=user
            )
            
            if notification:
                created_notifications += 1
                
                # جعل بعض الإشعارات مقروءة
                if random.choice([True, False, False]):  # 33% مقروءة
                    notification.mark_as_read()
        
        # إنشاء إشعارات الشكاوى
        complaint_count = max(1, count // 3)  # ثلث العدد للشكاوى
        
        for i in range(complaint_count):
            user = random.choice(users)
            customer = random.choice(customers)
            complaint_number = f"#C-2025-{100 + i:03d}"
            complaint_type = random.choice(complaint_types)
            priority = random.choice(complaint_priorities)
            
            titles = {
                'new': f'شكوى جديدة من {customer}',
                'assigned': f'تم تعيين شكوى {customer}',
                'in_progress': f'شكوى {customer} قيد المعالجة',
                'resolved': f'تم حل شكوى {customer}',
                'escalated': f'تم تصعيد شكوى {customer}'
            }
            
            title = titles.get(complaint_type, f'شكوى من {customer}')
            
            notification = SimpleNotificationService.create_complaint_notification(
                customer_name=customer,
                complaint_number=complaint_number,
                title=title,
                complaint_type=complaint_type,
                priority=priority,
                recipient=user
            )
            
            if notification:
                created_complaints += 1
                
                # جعل بعض الشكاوى مقروءة
                if random.choice([True, False]):  # 50% مقروءة
                    notification.mark_as_read()
        
        # تقرير النتائج
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ تم إنشاء {created_notifications} إشعار طلب بنجاح'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ تم إنشاء {created_complaints} إشعار شكوى بنجاح'
            )
        )
        
        # إحصائيات
        total_order_notifications = SimpleNotification.objects.count()
        total_complaint_notifications = ComplaintNotification.objects.count()
        unread_orders = SimpleNotification.objects.filter(is_read=False).count()
        unread_complaints = ComplaintNotification.objects.filter(is_read=False).count()
        
        self.stdout.write(
            self.style.WARNING(
                f'📊 إجمالي إشعارات الطلبات: {total_order_notifications} '
                f'(غير مقروءة: {unread_orders})'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f'📊 إجمالي إشعارات الشكاوى: {total_complaint_notifications} '
                f'(غير مقروءة: {unread_complaints})'
            )
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                '🎉 تم إنشاء الإشعارات التجريبية بنجاح! '
                'يمكنك الآن اختبار النظام الجديد.'
            )
        )
