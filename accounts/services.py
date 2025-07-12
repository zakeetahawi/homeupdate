"""
خدمات الإشعارات المحسنة
"""
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models import Q
from .models import Notification, Department, Branch

User = get_user_model()


class NotificationService:
    """خدمة إدارة الإشعارات"""
    
    @staticmethod
    def create_order_notification(order, notification_type='order', priority='medium'):
        """إنشاء إشعار لطلب جديد"""
        title = f"طلب جديد #{order.order_number}"
        message = f"تم إنشاء طلب جديد من العميل {order.customer.name}"
        
        # تحديد المستلمين
        recipients = NotificationService._get_order_recipients(order)
        
        notification = Notification.create_notification(
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            recipients=recipients,
            content_type=ContentType.objects.get_for_model(order),
            object_id=order.id,
            action_url=f"/admin/orders/order/{order.id}/change/"
        )
        
        return notification
    
    @staticmethod
    def create_inspection_notification(inspection, notification_type='inspection', priority='medium'):
        """إنشاء إشعار لمعاينة جديدة"""
        title = f"معاينة جديدة #{inspection.contract_number}"
        message = f"تم إنشاء معاينة جديدة للعميل {inspection.customer.name}"
        
        recipients = NotificationService._get_inspection_recipients(inspection)
        
        notification = Notification.create_notification(
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            recipients=recipients,
            content_type=ContentType.objects.get_for_model(inspection),
            object_id=inspection.id,
            action_url=f"/admin/inspections/inspection/{inspection.id}/change/"
        )
        
        return notification
    
    @staticmethod
    def create_manufacturing_notification(manufacturing_order, notification_type='manufacturing', priority='medium'):
        """إنشاء إشعار لأمر تصنيع جديد"""
        title = f"أمر تصنيع جديد #{manufacturing_order.id}"
        message = f"تم إنشاء أمر تصنيع جديد للطلب #{manufacturing_order.order.id}"
        
        recipients = NotificationService._get_manufacturing_recipients(manufacturing_order)
        
        notification = Notification.create_notification(
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            recipients=recipients,
            content_type=ContentType.objects.get_for_model(manufacturing_order),
            object_id=manufacturing_order.id,
            action_url=f"/admin/manufacturing/manufacturingorder/{manufacturing_order.id}/change/"
        )
        
        return notification
    
    @staticmethod
    def create_inventory_alert(product, alert_type='low_stock', priority='high'):
        """إنشاء تنبيه مخزون"""
        if alert_type == 'low_stock':
            title = f"تنبيه مخزون منخفض - {product.name}"
            message = f"المخزون الحالي للمنتج {product.name} منخفض"
        elif alert_type == 'out_of_stock':
            title = f"تنبيه نفاد المخزون - {product.name}"
            message = f"نفد المخزون للمنتج {product.name}"
            priority = 'urgent'
        
        recipients = NotificationService._get_inventory_recipients()
        
        notification = Notification.create_notification(
            title=title,
            message=message,
            notification_type='inventory',
            priority=priority,
            recipients=recipients,
            content_type=ContentType.objects.get_for_model(product),
            object_id=product.id,
            action_url=f"/admin/inventory/product/{product.id}/change/"
        )
        
        return notification
    
    @staticmethod
    def create_system_notification(title, message, priority='medium', recipients=None):
        """إنشاء إشعار نظام عام"""
        if not recipients:
            recipients = User.objects.filter(is_staff=True)
        
        notification = Notification.create_notification(
            title=title,
            message=message,
            notification_type='system',
            priority=priority,
            recipients=recipients
        )
        
        return notification
    
    @staticmethod
    def _get_order_recipients(order):
        """الحصول على مستلمي إشعارات الطلبات"""
        recipients = set()
        
        # إضافة مديري المبيعات
        sales_department = Department.objects.filter(name__icontains='مبيعات').first()
        if sales_department:
            recipients.update(sales_department.users.filter(is_active=True))
        
        # إضافة مديري الفرع
        if order.customer.branch:
            recipients.update(User.objects.filter(
                branch=order.customer.branch,
                is_staff=True
            ))
        
        # إضافة المشرفين
        recipients.update(User.objects.filter(is_superuser=True))
        
        return list(recipients)
    
    @staticmethod
    def _get_inspection_recipients(inspection):
        """الحصول على مستلمي إشعارات المعاينات"""
        recipients = set()
        
        # إضافة قسم المعاينات
        inspection_department = Department.objects.filter(name__icontains='معاينة').first()
        if inspection_department:
            recipients.update(inspection_department.users.filter(is_active=True))
        
        # إضافة مديري الفرع
        if inspection.branch:
            recipients.update(User.objects.filter(
                branch=inspection.branch,
                is_staff=True
            ))
        
        # إضافة المشرفين
        recipients.update(User.objects.filter(is_superuser=True))
        
        return list(recipients)
    
    @staticmethod
    def _get_manufacturing_recipients(manufacturing_order):
        """الحصول على مستلمي إشعارات التصنيع"""
        recipients = set()
        
        # إضافة قسم التصنيع
        manufacturing_department = Department.objects.filter(name__icontains='تصنيع').first()
        if manufacturing_department:
            recipients.update(manufacturing_department.users.filter(is_active=True))
        
        # إضافة المشرفين
        recipients.update(User.objects.filter(is_superuser=True))
        
        return list(recipients)
    
    @staticmethod
    def _get_inventory_recipients():
        """الحصول على مستلمي تنبيهات المخزون"""
        recipients = set()
        
        # إضافة قسم المخزون
        inventory_department = Department.objects.filter(name__icontains='مخزون').first()
        if inventory_department:
            recipients.update(inventory_department.users.filter(is_active=True))
        
        # إضافة المشرفين
        recipients.update(User.objects.filter(is_superuser=True))
        
        return list(recipients)
    
    @staticmethod
    def mark_notification_as_read(notification_id, user):
        """تحديد إشعار كمقروء"""
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.mark_as_read(user)
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def get_user_notifications(user, unread_only=False, limit=None):
        """الحصول على إشعارات المستخدم"""
        queryset = Notification.objects.filter(recipients=user)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        queryset = queryset.select_related('sender', 'content_type').order_by('-created_at')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    @staticmethod
    def cleanup_old_notifications(days=30):
        """تنظيف الإشعارات القديمة"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count = Notification.objects.filter(
            created_at__lt=cutoff_date,
            is_archived=True
        ).delete()[0]
        
        return deleted_count 