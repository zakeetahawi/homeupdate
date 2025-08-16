from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Complaint, ComplaintUpdate, ComplaintEscalation
from accounts.models import Department


User = get_user_model()


@receiver(post_save, sender=Complaint)
def complaint_post_save(sender, instance, created, **kwargs):
    """إشارة بعد حفظ الشكوى"""
    if created:
        # تم إزالة إنشاء إشعارات الشكوى الجديدة
        pass


@receiver(pre_save, sender=Complaint)
def complaint_status_change(sender, instance, **kwargs):
    """تتبع تغيير حالة الشكوى"""
    if instance.pk:
        try:
            old_instance = Complaint.objects.get(pk=instance.pk)

            # تسجيل تغيير الحالة
            if old_instance.status != instance.status:
                ComplaintUpdate.objects.create(
                    complaint=instance,
                    update_type='status_change',
                    title=f'تغيير الحالة من {old_instance.get_status_display()} إلى {instance.get_status_display()}',
                    description=f'تم تغيير حالة الشكوى من {old_instance.get_status_display()} إلى {instance.get_status_display()}',
                    old_status=old_instance.status,
                    new_status=instance.status,
                    is_visible_to_customer=True
                )

                # تم إزالة إنشاء إشعار تغيير الحالة
                pass

                # إشعار المدير في حالة التأخير
                if instance.status == 'overdue':
                    notify_managers_overdue(instance)

            # تسجيل تغيير المسؤول
            if old_instance.assigned_to != instance.assigned_to:
                ComplaintUpdate.objects.create(
                    complaint=instance,
                    update_type='assignment',
                    title='تغيير المسؤول',
                    description=f'تم تعيين {instance.assigned_to.get_full_name() if instance.assigned_to else "غير محدد"} كمسؤول عن الشكوى',
                    old_assignee=old_instance.assigned_to,
                    new_assignee=instance.assigned_to,
                    is_visible_to_customer=False
                )

        except Complaint.DoesNotExist:
            pass


def create_complaint_notification(complaint, notification_type, title, message, recipient):
    """إنشاء إشعار شكوى - تم تعطيلها"""
    pass


def notify_department_users(complaint, department, title, message):
    """إشعار مستخدمي قسم معين"""
    users = department.users.filter(is_active=True)
    for user in users:
        create_complaint_notification(
            complaint=complaint,
            notification_type='new_complaint',
            title=title,
            message=message,
            recipient=user
        )


def notify_managers_overdue(complaint):
    """إشعار المديرين في حالة تأخر الشكوى"""
    # إشعار مدير النظام
    managers = User.objects.filter(
        is_general_manager=True,
        is_active=True
    )
    
    for manager in managers:
        create_complaint_notification(
            complaint=complaint,
            notification_type='overdue',
            title=f'تأخر في حل الشكوى #{complaint.complaint_number}',
            message=f'تجاوزت الشكوى المقدمة من العميل {complaint.customer.name} الموعد النهائي للحل',
            recipient=manager
        )


@receiver(post_save, sender=ComplaintEscalation)
def escalation_notification(sender, instance, created, **kwargs):
    """إشعار التصعيد"""
    if created:
        # إشعار المصعد إليه
        if instance.escalated_to:
            create_complaint_notification(
                complaint=instance.complaint,
                notification_type='escalation',
                title=f'تصعيد الشكوى #{instance.complaint.complaint_number}',
                message=f'تم تصعيد الشكوى إليك - السبب: {instance.get_reason_display()}',
                recipient=instance.escalated_to
            )
        
        # إشعار المديرين
        managers = User.objects.filter(
            is_general_manager=True,
            is_active=True
        )
        
        for manager in managers:
            create_complaint_notification(
                complaint=instance.complaint,
                notification_type='escalation',
                title=f'تصعيد الشكوى #{instance.complaint.complaint_number}',
                message=f'تم تصعيد شكوى العميل {instance.complaint.customer.name} - السبب: {instance.get_reason_display()}',
                recipient=manager
            )
