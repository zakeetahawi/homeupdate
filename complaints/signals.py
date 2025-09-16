from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q
from .models import Complaint, ComplaintUpdate, ComplaintEscalation, ComplaintNotification
from .services.notification_service import notification_service

@receiver(post_save, sender=Complaint)
def handle_complaint_notifications(sender, instance, created, **kwargs):
    """معالجة إشعارات الشكوى باستخدام خدمة الإشعارات المحسنة"""
    if created:
        # استخدام خدمة الإشعارات المحسنة
        notification_service.notify_new_complaint(instance)

@receiver(pre_save, sender=Complaint)
def handle_status_change_notifications(sender, instance, **kwargs):
    """معالجة إشعارات تغيير الحالة باستخدام خدمة الإشعارات المحسنة"""
    if instance.pk:  # للتأكد من أن الشكوى موجودة مسبقاً
        try:
            old_instance = Complaint.objects.get(pk=instance.pk)

            # تغيير الحالة
            if old_instance.status != instance.status:
                # تخزين البيانات للمعالجة بعد الحفظ
                instance._old_status = old_instance.status
                instance._status_changed = True

            # تغيير المسؤول
            if old_instance.assigned_to != instance.assigned_to:
                instance._old_assignee = old_instance.assigned_to
                instance._assignee_changed = True

        except Complaint.DoesNotExist:
            pass


@receiver(post_save, sender=Complaint)
def handle_post_save_notifications(sender, instance, created, **kwargs):
    """معالجة الإشعارات بعد حفظ الشكوى"""
    if not created:
        # معالجة تغيير الحالة
        if hasattr(instance, '_status_changed') and instance._status_changed:
            notification_service.notify_status_change(
                complaint=instance,
                old_status=instance._old_status,
                new_status=instance.status,
                changed_by=getattr(instance, '_changed_by', None)
            )
            # تنظيف البيانات المؤقتة
            delattr(instance, '_old_status')
            delattr(instance, '_status_changed')

        # معالجة تغيير المسؤول
        if hasattr(instance, '_assignee_changed') and instance._assignee_changed:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🔄 تغيير المسؤول للشكوى {instance.complaint_number}: من {instance._old_assignee} إلى {instance.assigned_to}")

            notification_service.notify_assignment_change(
                complaint=instance,
                old_assignee=instance._old_assignee,
                new_assignee=instance.assigned_to,
                changed_by=getattr(instance, '_changed_by', None)
            )
            # تنظيف البيانات المؤقتة
            delattr(instance, '_old_assignee')
            delattr(instance, '_assignee_changed')

@receiver(post_save, sender=ComplaintUpdate)
def handle_update_notifications(sender, instance, created, **kwargs):
    """معالجة إشعارات التحديثات"""
    if created:
        recipients = set()
        if instance.complaint.assigned_to:
            recipients.add(instance.complaint.assigned_to)
        if instance.complaint.created_by:
            recipients.add(instance.complaint.created_by)
        if instance.complaint.assigned_department and instance.complaint.assigned_department.manager:
            recipients.add(instance.complaint.assigned_department.manager)

        for recipient in recipients:
            if recipient != instance.created_by:  # لا نرسل إشعاراً لمنشئ التحديث
                ComplaintNotification.create_notification(
                    complaint=instance.complaint,
                    notification_type='comment',
                    recipient=recipient,
                    title=f'تحديث جديد على الشكوى {instance.complaint.complaint_number}',
                    message=instance.description[:100] + '...' if len(instance.description) > 100 else instance.description
                )

@receiver(post_save, sender=ComplaintEscalation)
def handle_escalation_notifications(sender, instance, created, **kwargs):
    """معالجة إشعارات التصعيد"""
    if created:
        # إشعار للمسؤول الجديد
        if instance.escalated_to:
            ComplaintNotification.create_notification(
                complaint=instance.complaint,
                notification_type='escalation',
                recipient=instance.escalated_to,
                title=f'تم تصعيد الشكوى {instance.complaint.complaint_number} إليك',
                message=f'تم تصعيد الشكوى من {instance.escalated_from.get_full_name() if instance.escalated_from else "النظام"}'
            )

        # إشعار للمدراء
        if instance.complaint.assigned_department and instance.complaint.assigned_department.manager:
            manager = instance.complaint.assigned_department.manager
            if manager != instance.escalated_to:
                    ComplaintNotification.create_notification(
                        complaint=instance.complaint,
                        notification_type='escalation',
                        recipient=manager,
                        title=f'تم تصعيد الشكوى {instance.complaint.complaint_number}',
                        message=f'تم تصعيد الشكوى إلى {instance.escalated_to.get_full_name()}'
                    )

def check_complaint_deadlines():
    """فحص المواعيد النهائية للشكاوى وإرسال إشعارات"""
    # الشكاوى التي يقترب موعدها النهائي (خلال 24 ساعة)
    deadline_approaching = Complaint.objects.filter(
        Q(status__in=['new', 'in_progress']) &
        Q(deadline__lte=timezone.now() + timezone.timedelta(hours=24)) &
        Q(deadline__gt=timezone.now())
    )

    for complaint in deadline_approaching:
        if complaint.assigned_to:
            ComplaintNotification.create_notification(
                complaint=complaint,
                notification_type='deadline',
                recipient=complaint.assigned_to,
                title=f'اقتراب الموعد النهائي للشكوى {complaint.complaint_number}',
                message=f'يتبقى أقل من 24 ساعة على الموعد النهائي لحل الشكوى'
            )

    # الشكاوى المتأخرة
    overdue = Complaint.objects.filter(
        status__in=['new', 'in_progress'],
        deadline__lt=timezone.now()
    )

    # إرسال تنبيهات للشكاوى المتأخرة
    from complaints.services.notification_service import ComplaintNotificationService
    notification_service = ComplaintNotificationService()

    for complaint in overdue:
        # تحديث حالة الشكوى إلى متأخرة
        if complaint.status != 'overdue':
            complaint.status = 'overdue'
            complaint.save()

        # إرسال تنبيهات للمستخدمين الذين يمكن التصعيد إليهم
        notification_service.notify_overdue_to_escalation_users(complaint)

    for complaint in overdue:
        recipients = set()
        if complaint.assigned_to:
            recipients.add(complaint.assigned_to)
        if complaint.assigned_department and complaint.assigned_department.manager:
            recipients.add(complaint.assigned_department.manager)

        for recipient in recipients:
            ComplaintNotification.create_notification(
                complaint=complaint,
                notification_type='overdue',
                recipient=recipient,
                title=f'تجاوز الموعد النهائي للشكوى {complaint.complaint_number}',
                message=f'تم تجاوز الموعد النهائي لحل الشكوى. يرجى اتخاذ الإجراء المناسب.'
            )
