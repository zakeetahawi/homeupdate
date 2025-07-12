"""
أمر إنشاء إشعارات تجريبية لاختبار النظام
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from accounts.models import Notification, Department, Branch
from accounts.services import NotificationService
from customers.models import Customer
from orders.models import Order
from manufacturing.models import ManufacturingOrder
from inspections.models import Inspection
from inventory.models import Product
import random
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'إنشاء إشعارات تجريبية لاختبار نظام الإشعارات'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='عدد الإشعارات المراد إنشاؤها'
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['all', 'orders', 'inspections', 'manufacturing', 'inventory', 'system'],
            default='all',
            help='نوع الإشعارات المراد إنشاؤها'
        )
        parser.add_argument(
            '--priority',
            type=str,
            choices=['low', 'medium', 'high', 'urgent'],
            default='medium',
            help='أولوية الإشعارات'
        )

    def handle(self, *args, **options):
        count = options['count']
        notification_type = options['type']
        priority = options['priority']

        self.stdout.write(
            self.style.SUCCESS(f'بدء إنشاء {count} إشعار تجريبي من نوع {notification_type}')
        )

        # الحصول على المستخدمين والأقسام
        users = list(User.objects.filter(is_active=True))
        departments = list(Department.objects.filter(is_active=True))
        branches = list(Branch.objects.filter(is_active=True))

        if not users:
            self.stdout.write(
                self.style.ERROR('لا يوجد مستخدمين نشطين في النظام')
            )
            return

        notifications_created = 0

        for i in range(count):
            try:
                if notification_type == 'all':
                    notification_type = random.choice(['orders', 'inspections', 'manufacturing', 'inventory', 'system'])
                
                notification = self.create_test_notification(
                    notification_type, priority, users, departments, branches
                )
                
                if notification:
                    notifications_created += 1
                    self.stdout.write(
                        f'تم إنشاء إشعار: {notification.title}'
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'خطأ في إنشاء الإشعار {i+1}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'تم إنشاء {notifications_created} إشعار بنجاح من أصل {count}'
            )
        )

    def create_test_notification(self, notification_type, priority, users, departments, branches):
        """إنشاء إشعار تجريبي"""
        
        # تحديد المرسل والمستلمين
        sender = random.choice(users)
        recipients = random.sample(users, min(3, len(users)))
        
        # تحديد الأقسام والفروع المستهدفة
        target_departments = random.sample(departments, min(2, len(departments))) if departments else []
        target_branches = random.sample(branches, min(2, len(branches))) if branches else []
        
        # إنشاء الإشعار حسب النوع
        if notification_type == 'orders':
            return self.create_order_notification(sender, recipients, target_departments, target_branches, priority)
        elif notification_type == 'inspections':
            return self.create_inspection_notification(sender, recipients, target_departments, target_branches, priority)
        elif notification_type == 'manufacturing':
            return self.create_manufacturing_notification(sender, recipients, target_departments, target_branches, priority)
        elif notification_type == 'inventory':
            return self.create_inventory_notification(sender, recipients, target_departments, target_branches, priority)
        elif notification_type == 'system':
            return self.create_system_notification(sender, recipients, target_departments, target_branches, priority)
        
        return None

    def create_order_notification(self, sender, recipients, target_departments, target_branches, priority):
        """إنشاء إشعار طلب تجريبي"""
        titles = [
            'طلب جديد من عميل VIP',
            'طلب عاجل يحتاج موافقة',
            'طلب كبير من عميل جديد',
            'طلب يحتاج متابعة خاصة',
            'طلب من فرع جديد'
        ]
        
        messages = [
            'تم استلام طلب جديد من عميل مهم ويحتاج متابعة فورية',
            'طلب عاجل من عميل VIP يحتاج موافقة المدير',
            'طلب كبير من عميل جديد يتطلب اهتمام خاص',
            'طلب يحتاج متابعة من قسم المبيعات',
            'طلب من فرع جديد يحتاج مراجعة'
        ]
        
        title = random.choice(titles)
        message = random.choice(messages)
        
        # محاولة ربط الإشعار بطلب حقيقي
        content_type = None
        object_id = None
        action_url = ''
        
        try:
            order = Order.objects.first()
            if order:
                content_type = ContentType.objects.get_for_model(Order)
                object_id = order.id
                action_url = f'/admin/orders/order/{order.id}/change/'
        except:
            pass
        
        notification = Notification.objects.create(
            title=title,
            message=message,
            notification_type='order',
            priority=priority,
            sender=sender,
            content_type=content_type,
            object_id=object_id,
            action_url=action_url,
            requires_action=random.choice([True, False])
        )
        
        notification.recipients.set(recipients)
        if target_departments:
            notification.target_departments.set(target_departments)
        if target_branches:
            notification.target_branches.set(target_branches)
        
        return notification

    def create_inspection_notification(self, sender, recipients, target_departments, target_branches, priority):
        """إنشاء إشعار معاينة تجريبي"""
        titles = [
            'معاينة جديدة مطلوبة',
            'معاينة عاجلة للعميل',
            'معاينة فنية مطلوبة',
            'معاينة جودة جديدة',
            'معاينة موقع جديد'
        ]
        
        messages = [
            'تم طلب معاينة جديدة من عميل ويحتاج متابعة فورية',
            'معاينة عاجلة مطلوبة من عميل VIP',
            'معاينة فنية مطلوبة للموقع الجديد',
            'معاينة جودة جديدة تحتاج مراجعة',
            'معاينة موقع جديد مطلوبة'
        ]
        
        title = random.choice(titles)
        message = random.choice(messages)
        
        content_type = None
        object_id = None
        action_url = ''
        
        try:
            inspection = Inspection.objects.first()
            if inspection:
                content_type = ContentType.objects.get_for_model(Inspection)
                object_id = inspection.id
                action_url = f'/admin/inspections/inspection/{inspection.id}/change/'
        except:
            pass
        
        notification = Notification.objects.create(
            title=title,
            message=message,
            notification_type='inspection',
            priority=priority,
            sender=sender,
            content_type=content_type,
            object_id=object_id,
            action_url=action_url,
            requires_action=True
        )
        
        notification.recipients.set(recipients)
        if target_departments:
            notification.target_departments.set(target_departments)
        if target_branches:
            notification.target_branches.set(target_branches)
        
        return notification

    def create_manufacturing_notification(self, sender, recipients, target_departments, target_branches, priority):
        """إنشاء إشعار تصنيع تجريبي"""
        titles = [
            'أمر تصنيع جديد',
            'تصنيع عاجل مطلوب',
            'أمر تصنيع كبير',
            'تصنيع مخصص مطلوب',
            'أمر تصنيع من فرع جديد'
        ]
        
        messages = [
            'تم إنشاء أمر تصنيع جديد ويحتاج متابعة',
            'تصنيع عاجل مطلوب من قسم الإنتاج',
            'أمر تصنيع كبير يحتاج مراجعة',
            'تصنيع مخصص مطلوب من قسم التصميم',
            'أمر تصنيع من فرع جديد يحتاج موافقة'
        ]
        
        title = random.choice(titles)
        message = random.choice(messages)
        
        content_type = None
        object_id = None
        action_url = ''
        
        try:
            manufacturing_order = ManufacturingOrder.objects.first()
            if manufacturing_order:
                content_type = ContentType.objects.get_for_model(ManufacturingOrder)
                object_id = manufacturing_order.id
                action_url = f'/admin/manufacturing/manufacturingorder/{manufacturing_order.id}/change/'
        except:
            pass
        
        notification = Notification.objects.create(
            title=title,
            message=message,
            notification_type='manufacturing',
            priority=priority,
            sender=sender,
            content_type=content_type,
            object_id=object_id,
            action_url=action_url,
            requires_action=True
        )
        
        notification.recipients.set(recipients)
        if target_departments:
            notification.target_departments.set(target_departments)
        if target_branches:
            notification.target_branches.set(target_branches)
        
        return notification

    def create_inventory_notification(self, sender, recipients, target_departments, target_branches, priority):
        """إنشاء إشعار مخزون تجريبي"""
        titles = [
            'تنبيه مخزون منخفض',
            'نفاد مخزون عاجل',
            'طلب شراء مطلوب',
            'مخزون جديد وصل',
            'تحديث مخزون مطلوب'
        ]
        
        messages = [
            'المخزون منخفض لمنتج مهم ويحتاج طلب شراء',
            'نفد مخزون منتج عاجل ويحتاج طلب فوري',
            'طلب شراء مطلوب لتجديد المخزون',
            'وصل مخزون جديد ويحتاج تحديث',
            'تحديث مخزون مطلوب من قسم المشتريات'
        ]
        
        title = random.choice(titles)
        message = random.choice(messages)
        
        content_type = None
        object_id = None
        action_url = ''
        
        try:
            product = Product.objects.first()
            if product:
                content_type = ContentType.objects.get_for_model(Product)
                object_id = product.id
                action_url = f'/admin/inventory/product/{product.id}/change/'
        except:
            pass
        
        notification = Notification.objects.create(
            title=title,
            message=message,
            notification_type='inventory',
            priority=priority,
            sender=sender,
            content_type=content_type,
            object_id=object_id,
            action_url=action_url,
            requires_action=random.choice([True, False])
        )
        
        notification.recipients.set(recipients)
        if target_departments:
            notification.target_departments.set(target_departments)
        if target_branches:
            notification.target_branches.set(target_branches)
        
        return notification

    def create_system_notification(self, sender, recipients, target_departments, target_branches, priority):
        """إنشاء إشعار نظام تجريبي"""
        titles = [
            'تحديث النظام',
            'صيانة مجدولة',
            'نسخة احتياطية مكتملة',
            'تقرير شهري جاهز',
            'تحديث أمان النظام'
        ]
        
        messages = [
            'تم تحديث النظام بنجاح وجاهز للاستخدام',
            'صيانة مجدولة للنظام غداً من الساعة 2-4 صباحاً',
            'تم إكمال النسخة الاحتياطية الأسبوعية بنجاح',
            'التقرير الشهري جاهز للعرض والتحميل',
            'تم تحديث إعدادات الأمان في النظام'
        ]
        
        title = random.choice(titles)
        message = random.choice(messages)
        
        notification = Notification.objects.create(
            title=title,
            message=message,
            notification_type='system',
            priority=priority,
            sender=sender,
            requires_action=False
        )
        
        notification.recipients.set(recipients)
        if target_departments:
            notification.target_departments.set(target_departments)
        if target_branches:
            notification.target_branches.set(target_branches)
        
        return notification 