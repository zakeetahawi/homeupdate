from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .models import Notification, NotificationVisibility
from .utils import get_notification_recipients

User = get_user_model()


def clean_extra_data(data):
    """تنظيف البيانات الإضافية من النصوص المترجمة لتجنب مشاكل JSON"""
    if not isinstance(data, dict):
        return data

    cleaned_data = {}
    for key, value in data.items():
        if hasattr(value, '__str__'):
            cleaned_data[key] = str(value)
        else:
            cleaned_data[key] = value

    return cleaned_data


def create_notification(
    title, message, notification_type, related_object=None,
    created_by=None, priority='normal', extra_data=None, recipients=None
):
    """
    إنشاء إشعار جديد مع تحديد المستخدمين المصرح لهم برؤيته

    Args:
        title: عنوان الإشعار
        message: نص الإشعار
        notification_type: نوع الإشعار
        related_object: الكائن المرتبط (اختياري)
        created_by: المستخدم المنشئ (اختياري)
        priority: أولوية الإشعار (افتراضي: normal)
        extra_data: بيانات إضافية (اختياري)
        recipients: قائمة المستخدمين المستهدفين (اختياري)

    Returns:
        Notification: الإشعار المنشأ
    """
    from django.utils import timezone
    from datetime import timedelta

    # فحص الإشعارات المكررة (نفس النوع والكائن المرتبط في آخر دقيقة)
    if related_object:
        recent_time = timezone.now() - timedelta(minutes=1)
        existing_notification = Notification.objects.filter(
            notification_type=notification_type,
            content_type=ContentType.objects.get_for_model(related_object),
            object_id=related_object.pk,
            created_at__gte=recent_time
        ).first()

        # للإشعارات الحساسة، فحص أكثر دقة
        if existing_notification and notification_type in ['order_status_changed', 'manufacturing_status_changed']:
            # فحص إذا كان نفس التغيير بالضبط
            if (extra_data and existing_notification.extra_data and
                extra_data.get('old_status') == existing_notification.extra_data.get('old_status') and
                extra_data.get('new_status') == existing_notification.extra_data.get('new_status')):
                print(f"⚠️ تم تجاهل إشعار مكرر: {title}")
                return existing_notification
        elif existing_notification:
            print(f"⚠️ تم تجاهل إشعار مكرر: {title}")
            return existing_notification

    # إنشاء الإشعار
    notification = Notification.objects.create(
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        created_by=created_by,
        extra_data=clean_extra_data(extra_data or {}),
        content_type=ContentType.objects.get_for_model(related_object) if related_object else None,
        object_id=related_object.pk if related_object else None,
    )
    
    # تحديد المستخدمين المصرح لهم برؤية الإشعار
    if recipients is None:
        recipients = get_notification_recipients(
            notification_type, related_object, created_by
        )
    
    # إنشاء سجلات الرؤية
    visibility_records = []
    for user in recipients:
        visibility_records.append(
            NotificationVisibility(
                notification=notification,
                user=user,
                is_read=False
            )
        )
    
    if visibility_records:
        NotificationVisibility.objects.bulk_create(visibility_records)
    
    return notification


# ===== إشعارات العملاء =====

@receiver(post_save, sender='customers.Customer')
def customer_created_notification(sender, instance, created, **kwargs):
    """إشعار عند إنشاء عميل جديد"""
    if created:
        title = f"عميل جديد: {instance.name}"
        message = f"تم إنشاء عميل جديد باسم {instance.name} في فرع {instance.branch.name if instance.branch else 'غير محدد'}"
        
        if instance.created_by:
            message += f" بواسطة {instance.created_by.get_full_name() or instance.created_by.username}"
        
        create_notification(
            title=title,
            message=message,
            notification_type='customer_created',
            related_object=instance,
            created_by=instance.created_by,
            priority='normal',
            extra_data={
                'customer_code': instance.code,
                'branch_name': instance.branch.name if instance.branch else None,
            }
        )


# ===== إشعارات الطلبات =====

@receiver(post_save, sender='orders.Order')
def order_created_notification(sender, instance, created, **kwargs):
    """إشعار عند إنشاء طلب جديد"""
    if created:
        order_types = instance.get_selected_types_list() if hasattr(instance, 'get_selected_types_list') else []
        order_types_str = ', '.join([dict(instance.ORDER_TYPES).get(t, t) for t in order_types])
        
        title = f"طلب جديد: {instance.order_number}"
        message = f"تم إنشاء طلب جديد رقم {instance.order_number} من نوع ({order_types_str}) للعميل {instance.customer.name}"
        
        if instance.created_by:
            message += f" بواسطة {instance.created_by.get_full_name() or instance.created_by.username}"
        
        create_notification(
            title=title,
            message=message,
            notification_type='order_created',
            related_object=instance,
            created_by=instance.created_by,
            priority='normal',
            extra_data={
                'order_number': instance.order_number,
                'customer_code': instance.customer.code,
                'order_types': order_types,
                'total_amount': str(instance.total_amount) if hasattr(instance, 'total_amount') else None,
            }
        )


@receiver(pre_save, sender='orders.Order')
def order_status_changed_notification(sender, instance, **kwargs):
    """إشعار عند تغيير حالة الطلب"""
    if instance.pk:  # التأكد من أن الطلب موجود مسبقاً
        try:
            old_instance = sender.objects.get(pk=instance.pk)

            # التحقق من تغيير حالة الطلب
            if hasattr(instance, 'order_status') and hasattr(old_instance, 'order_status'):
                if old_instance.order_status != instance.order_status:
                    # تجاهل التغييرات التلقائية عند الإنشاء
                    if old_instance.order_status == 'pending_approval' and instance.order_status == 'pending':
                        return  # تجاهل هذا التغيير التلقائي
                    old_status_display = str(dict(instance.ORDER_STATUS_CHOICES).get(old_instance.order_status, old_instance.order_status))
                    new_status_display = str(dict(instance.ORDER_STATUS_CHOICES).get(instance.order_status, instance.order_status))
                    
                    title = f"تغيير حالة الطلب: {instance.order_number}"
                    message = f"تم تغيير حالة الطلب {instance.order_number} من '{old_status_display}' إلى '{new_status_display}'"
                    
                    # تحديد الأولوية حسب نوع التغيير
                    priority = 'normal'
                    if instance.order_status in ['delivered', 'completed']:
                        priority = 'high'
                    elif instance.order_status in ['cancelled', 'rejected']:
                        priority = 'urgent'
                    
                    create_notification(
                        title=title,
                        message=message,
                        notification_type='order_status_changed',
                        related_object=instance,
                        created_by=None,  # سيتم تحديده من السياق
                        priority=priority,
                        extra_data={
                            'order_number': instance.order_number,
                            'old_status': old_instance.order_status,
                            'new_status': instance.order_status,
                            'old_status_display': old_status_display,
                            'new_status_display': new_status_display,
                        }
                    )
            
            # التحقق من تغيير حالة التسليم
            if hasattr(instance, 'delivery_status') and hasattr(old_instance, 'delivery_status'):
                if (old_instance.delivery_status != instance.delivery_status and 
                    instance.delivery_status == 'delivered'):
                    
                    title = f"تم تسليم الطلب: {instance.order_number}"
                    message = f"تم تسليم الطلب {instance.order_number} للعميل {instance.customer.name}"
                    
                    if hasattr(instance, 'delivery_receipt_number') and instance.delivery_receipt_number:
                        message += f" برقم إذن التسليم: {instance.delivery_receipt_number}"
                    
                    create_notification(
                        title=title,
                        message=message,
                        notification_type='order_delivered',
                        related_object=instance,
                        created_by=None,
                        priority='high',
                        extra_data={
                            'order_number': instance.order_number,
                            'customer_name': instance.customer.name,
                            'delivery_receipt_number': getattr(instance, 'delivery_receipt_number', None),
                        }
                    )
                    
        except sender.DoesNotExist:
            pass


# ===== إشعارات المعاينات =====

@receiver(post_save, sender='inspections.Inspection')
def inspection_created_notification(sender, instance, created, **kwargs):
    """إشعار عند إنشاء معاينة جديدة"""
    if created:
        # استخدام كود الطلب فقط
        order_number = None
        if hasattr(instance, 'order') and instance.order:
            order_number = instance.order.order_number
        else:
            order_number = f"معاينة-{instance.pk}"

        title = f"معاينة جديدة: {order_number}"
        message = f"تم إنشاء معاينة جديدة للعميل {instance.customer.name if instance.customer else 'غير محدد'}"

        if hasattr(instance, 'order') and instance.order:
            message += f" للطلب {instance.order.order_number}"

        if instance.responsible_employee:
            message += f" بواسطة {instance.responsible_employee.name}"

        create_notification(
            title=title,
            message=message,
            notification_type='inspection_created',
            related_object=instance,
            created_by=getattr(instance, 'created_by', None),
            priority='normal',
            extra_data={
                'order_number': order_number,
                'customer_name': instance.customer.name if instance.customer else None,
                'branch_name': instance.branch.name if instance.branch else None,
                'responsible_employee': instance.responsible_employee.name if instance.responsible_employee else None,
            }
        )


@receiver(pre_save, sender='inspections.Inspection')
def inspection_status_changed_notification(sender, instance, **kwargs):
    """إشعار عند تغيير حالة المعاينة"""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            
            if old_instance.status != instance.status:
                old_status_display = str(dict(instance.STATUS_CHOICES).get(old_instance.status, old_instance.status))
                new_status_display = str(dict(instance.STATUS_CHOICES).get(instance.status, instance.status))

                # تحسين العنوان والرسالة
                contract_info = instance.contract_number or f"معاينة-{instance.pk}"
                if hasattr(instance, 'order') and instance.order:
                    contract_info = instance.order.order_number

                title = f"تغيير حالة المعاينة: {contract_info}"
                message = f"تم تغيير حالة المعاينة {contract_info} من '{old_status_display}' إلى '{new_status_display}'"

                # إضافة معلومات العميل إذا كانت متوفرة
                if hasattr(instance, 'customer') and instance.customer:
                    message += f" للعميل {instance.customer.name}"
                
                priority = 'high' if instance.status == 'completed' else 'normal'
                
                create_notification(
                    title=title,
                    message=message,
                    notification_type='inspection_status_changed',
                    related_object=instance,
                    created_by=None,
                    priority=priority,
                    extra_data={
                        'contract_number': instance.contract_number,
                        'old_status': old_instance.status,
                        'new_status': instance.status,
                        'old_status_display': old_status_display,
                        'new_status_display': new_status_display,
                    }
                )
                
        except sender.DoesNotExist:
            pass


# ===== إشعارات التركيبات =====

@receiver(post_save, sender='installations.InstallationSchedule')
def installation_scheduled_notification(sender, instance, created, **kwargs):
    """إشعار عند جدولة تركيب"""
    if created:
        title = f"جدولة تركيب: {instance.order.order_number}"
        message = f"تم جدولة تركيب للطلب {instance.order.order_number}"
        
        if instance.scheduled_date:
            message += f" في تاريخ {instance.scheduled_date.strftime('%Y-%m-%d')}"
        
        if instance.team:
            message += f" مع فريق {instance.team.name}"
        
        create_notification(
            title=title,
            message=message,
            notification_type='installation_scheduled',
            related_object=instance,
            created_by=getattr(instance, 'created_by', None),
            priority='normal',
            extra_data={
                'order_number': instance.order.order_number,
                'scheduled_date': instance.scheduled_date.isoformat() if instance.scheduled_date else None,
                'team_name': instance.team.name if instance.team else None,
            }
        )


@receiver(pre_save, sender='installations.InstallationSchedule')
def installation_completed_notification(sender, instance, **kwargs):
    """إشعار عند إكمال التركيب"""
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            
            if (old_instance.status != instance.status and 
                instance.status == 'completed'):
                
                title = f"تم إكمال التركيب: {instance.order.order_number}"
                message = f"تم إكمال تركيب الطلب {instance.order.order_number} بنجاح"
                
                if instance.completion_date:
                    message += f" في تاريخ {instance.completion_date.strftime('%Y-%m-%d')}"
                
                create_notification(
                    title=title,
                    message=message,
                    notification_type='installation_completed',
                    related_object=instance,
                    created_by=None,
                    priority='high',
                    extra_data={
                        'order_number': instance.order.order_number,
                        'completion_date': instance.completion_date.isoformat() if instance.completion_date else None,
                    }
                )
                
        except sender.DoesNotExist:
            pass


# ===== إشعارات أوامر التصنيع =====

@receiver(pre_save, sender='manufacturing.ManufacturingOrder')
def manufacturing_order_status_changed_notification(sender, instance, **kwargs):
    """إشعار عند تغيير حالة أمر التصنيع"""
    if instance.pk:  # التأكد من أن أمر التصنيع موجود مسبقاً
        try:
            old_instance = sender.objects.get(pk=instance.pk)

            if old_instance.status != instance.status:
                old_status_display = str(dict(instance.STATUS_CHOICES).get(old_instance.status, old_instance.status))
                new_status_display = str(dict(instance.STATUS_CHOICES).get(instance.status, instance.status))

                title = f"تغيير حالة أمر التصنيع: {instance.order.order_number}"
                message = f"تم تغيير حالة أمر التصنيع للطلب {instance.order.order_number} من '{old_status_display}' إلى '{new_status_display}'"

                # تحديد الأولوية حسب نوع التغيير
                priority = 'normal'
                if instance.status in ['completed', 'ready_install']:
                    priority = 'high'
                elif instance.status in ['rejected', 'cancelled']:
                    priority = 'urgent'

                create_notification(
                    title=title,
                    message=message,
                    notification_type='manufacturing_status_changed',
                    related_object=instance.order,  # ربط بالطلب الأصلي
                    created_by=None,  # سيتم تحديده من السياق
                    priority=priority,
                    extra_data={
                        'order_number': instance.order.order_number,
                        'manufacturing_order_id': instance.id,
                        'old_status': old_instance.status,
                        'new_status': instance.status,
                        'old_status_display': old_status_display,
                        'new_status_display': new_status_display,
                        'order_type': instance.order_type,
                    }
                )

        except sender.DoesNotExist:
            pass


# ===== إشعارات الشكاوى =====

@receiver(post_save, sender='complaints.Complaint')
def complaint_created_notification(sender, instance, created, **kwargs):
    """إشعار عند تسجيل شكوى جديدة"""
    if created:
        title = f"شكوى جديدة: {instance.complaint_number}"
        message = f"تم تسجيل شكوى جديدة من العميل {instance.customer.name} بعنوان '{instance.title}'"

        # تحديد الأولوية حسب نوع الشكوى
        priority = 'normal'
        if hasattr(instance, 'priority'):
            priority_map = {'urgent': 'urgent', 'high': 'high', 'medium': 'normal', 'low': 'low'}
            priority = priority_map.get(instance.priority, 'normal')

        create_notification(
            title=title,
            message=message,
            notification_type='complaint_created',
            related_object=instance,
            created_by=getattr(instance, 'created_by', None),
            priority=priority,
            extra_data={
                'complaint_number': instance.complaint_number,
                'customer_name': instance.customer.name,
                'complaint_title': instance.title,
                'complaint_type': instance.complaint_type.name if hasattr(instance, 'complaint_type') else None,
            }
        )
