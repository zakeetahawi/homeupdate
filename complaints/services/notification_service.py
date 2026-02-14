"""
Enhanced notification service for complaints system integration
يستخدم نظام الإشعارات الرئيسي الموحد (Notification model)
بدلاً من نظام ComplaintNotification المنفصل
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)


def _create_main_notification(complaint, recipient, notification_type, title, message, priority="normal"):
    """
    إنشاء إشعار في النظام الرئيسي الموحد مع تحديد المستلم
    """
    from notifications.models import Notification, NotificationVisibility
    from django.contrib.contenttypes.models import ContentType

    # تحويل أنواع الإشعارات القديمة إلى الأنواع الرئيسية
    type_map = {
        "new_complaint": "complaint_created",
        "status_change": "complaint_status_changed",
        "assignment": "complaint_assigned",
        "escalation": "complaint_escalated",
        "escalation_alert": "complaint_escalated",
        "overdue": "complaint_overdue",
        "overdue_reminder": "complaint_overdue",
        "deadline": "complaint_overdue",
        "comment": "complaint_comment",
    }
    mapped_type = type_map.get(notification_type, "complaint_status_changed")

    # فحص التكرار - نفس النوع ونفس الشكوى في آخر 5 دقائق
    from datetime import timedelta
    recent_time = timezone.now() - timedelta(minutes=5)
    ct = ContentType.objects.get_for_model(complaint)
    existing = Notification.objects.filter(
        notification_type=mapped_type,
        content_type=ct,
        object_id=complaint.pk,
        created_at__gte=recent_time,
    ).first()
    if existing:
        # تأكد من أن المستلم لديه visibility record
        NotificationVisibility.objects.get_or_create(
            notification=existing,
            user=recipient,
            defaults={"is_read": False},
        )
        return existing

    notification = Notification.objects.create(
        title=title,
        message=message,
        notification_type=mapped_type,
        priority=priority,
        content_type=ct,
        object_id=complaint.pk,
        extra_data={
            "complaint_number": complaint.complaint_number,
            "customer_name": complaint.customer.name if complaint.customer else "",
        },
    )

    NotificationVisibility.objects.create(
        notification=notification,
        user=recipient,
        is_read=False,
    )

    return notification


class ComplaintNotificationService:
    """
    Centralized service for handling all complaint notifications
    """

    def __init__(self):
        self.channel_layer = get_channel_layer()

    def notify_new_complaint(self, complaint):
        """
        Send notifications when a new complaint is created
        """
        try:
            # Notify assigned user
            if complaint.assigned_to:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.assigned_to,
                    notification_type="new_complaint",
                    title=f"شكوى جديدة مسندة إليك: {complaint.complaint_number}",
                    message=f"تم إسناد شكوى جديدة من العميل {complaint.customer.name} إليك",
                    send_email=True,
                )

            # Notify department manager
            if complaint.assigned_department and complaint.assigned_department.manager:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.assigned_department.manager,
                    notification_type="new_complaint",
                    title=f"شكوى جديدة في قسم {complaint.assigned_department.name}",
                    message=f"تم تسجيل شكوى جديدة من العميل {complaint.customer.name}",
                    send_email=False,
                )

            # Notify supervisors
            supervisors = User.objects.filter(
                groups__name="Complaints_Supervisors", is_active=True
            )
            for supervisor in supervisors:
                self._send_notification(
                    complaint=complaint,
                    recipient=supervisor,
                    notification_type="new_complaint",
                    title=f"شكوى جديدة: {complaint.complaint_number}",
                    message=f"تم تسجيل شكوى جديدة من العميل {complaint.customer.name}",
                    send_email=False,
                )

        except Exception as e:
            logger.error(f"Error sending new complaint notifications: {str(e)}")

    def notify_status_change(self, complaint, old_status, new_status, changed_by):
        """
        Send notifications when complaint status changes
        """
        try:
            status_messages = {
                "new": "جديدة",
                "in_progress": "قيد الحل",
                "resolved": "محلولة",
                "closed": "مغلقة",
                "overdue": "متأخرة",
                "escalated": "مصعدة",
            }

            message = f'تم تغيير حالة الشكوى من "{status_messages.get(old_status, old_status)}" إلى "{status_messages.get(new_status, new_status)}"'

            # إخفاء الإشعارات القديمة عند حل الشكوى أو إغلاقها
            if new_status in ["resolved", "closed"]:
                self._hide_old_notifications_for_resolved_complaint(complaint)

            # Notify customer (if resolved or closed)
            if new_status in ["resolved", "closed"] and hasattr(
                complaint.customer, "user"
            ):
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.customer.user,
                    notification_type="status_change",
                    title=f"تحديث حالة شكواك: {complaint.complaint_number}",
                    message=message,
                    send_email=True,
                )

            # Notify assigned user (if not the one who changed it)
            if complaint.assigned_to and complaint.assigned_to != changed_by:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.assigned_to,
                    notification_type="status_change",
                    title=f"تحديث حالة الشكوى: {complaint.complaint_number}",
                    message=message,
                    send_email=False,
                )

            # Notify creator (if not the one who changed it)
            if complaint.created_by and complaint.created_by != changed_by:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.created_by,
                    notification_type="status_change",
                    title=f"تحديث حالة الشكوى: {complaint.complaint_number}",
                    message=message,
                    send_email=False,
                )

        except Exception as e:
            logger.error(f"Error sending status change notifications: {str(e)}")

    def notify_assignment_change(
        self, complaint, old_assignee, new_assignee, changed_by
    ):
        """
        Send notifications when complaint assignment changes
        """
        try:
            # إخفاء الإشعارات القديمة للمسؤول السابق
            if old_assignee:
                self._hide_old_assignment_notifications(complaint, old_assignee)

            # Notify new assignee
            if new_assignee:
                self._send_notification(
                    complaint=complaint,
                    recipient=new_assignee,
                    notification_type="assignment",
                    title=f"تم إسناد شكوى إليك: {complaint.complaint_number}",
                    message=f"تم إسناد شكوى من العميل {complaint.customer.name} إليك",
                    send_email=True,
                )

            # Notify old assignee
            if old_assignee and old_assignee != changed_by:
                self._send_notification(
                    complaint=complaint,
                    recipient=old_assignee,
                    notification_type="assignment",
                    title=f"تم نقل الشكوى: {complaint.complaint_number}",
                    message=f'تم نقل الشكوى إلى {new_assignee.get_full_name() if new_assignee else "مستخدم آخر"}',
                    send_email=False,
                )

        except Exception as e:
            logger.error(f"Error sending assignment change notifications: {str(e)}")

    def notify_deadline_approaching(self, complaint, hours_remaining):
        """
        Send notifications when deadline is approaching
        """
        try:
            if complaint.assigned_to:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.assigned_to,
                    notification_type="deadline",
                    title=f"اقتراب الموعد النهائي: {complaint.complaint_number}",
                    message=f"يتبقى {hours_remaining} ساعة على الموعد النهائي لحل الشكوى",
                    send_email=True,
                )

        except Exception as e:
            logger.error(f"Error sending deadline notifications: {str(e)}")

    def notify_overdue_to_escalation_users(self, complaint):
        """
        إرسال تنبيهات للمستخدمين الذين يمكن التصعيد إليهم عند تجاوز الشكوى للموعد النهائي
        """
        try:
            from django.contrib.auth.models import Group

            from accounts.models import User
            from complaints.models import ComplaintUserPermissions

            # البحث عن المستخدمين الذين يمكن التصعيد إليهم
            escalation_users = []

            # 1. المستخدمون مع صلاحية استقبال التصعيد
            users_with_escalation_permission = User.objects.filter(
                complaint_permissions__can_receive_escalations=True,
                complaint_permissions__is_active=True,
            )
            escalation_users.extend(users_with_escalation_permission)

            # 2. مدراء الأقسام
            if complaint.assigned_department and hasattr(
                complaint.assigned_department, "manager"
            ):
                if complaint.assigned_department.manager:
                    escalation_users.append(complaint.assigned_department.manager)

            # 3. المستخدمون في المجموعات الإدارية
            admin_groups = Group.objects.filter(
                name__in=["Complaints_Managers", "Complaints_Supervisors", "Managers"]
            )
            for group in admin_groups:
                escalation_users.extend(group.user_set.all())

            # إزالة التكرار والمستخدم المسؤول الحالي
            escalation_users = list(set(escalation_users))
            if complaint.assigned_to in escalation_users:
                escalation_users.remove(complaint.assigned_to)

            # إرسال التنبيهات
            for user in escalation_users:
                self._send_notification(
                    complaint=complaint,
                    recipient=user,
                    notification_type="escalation_alert",
                    title=f"شكوى متأخرة تحتاج تصعيد: {complaint.complaint_number}",
                    message=f"الشكوى {complaint.complaint_number} تجاوزت الموعد النهائي وتحتاج إلى تصعيد أو تدخل إداري",
                    send_email=True,
                )

            logger.info(
                f"تم إرسال تنبيهات التصعيد لـ {len(escalation_users)} مستخدم للشكوى {complaint.complaint_number}"
            )

        except Exception as e:
            logger.error(f"Error sending escalation notifications: {str(e)}")

    def notify_overdue_complaints_daily(self):
        """
        إرسال تنبيهات يومية للشكاوى المتأخرة
        """
        try:
            from django.utils import timezone

            from complaints.models import Complaint

            # البحث عن الشكاوى المتأخرة
            overdue_complaints = Complaint.objects.filter(
                deadline__lt=timezone.now(),
                status__in=["new", "in_progress", "overdue"],
            ).select_related(
                "customer", "complaint_type", "assigned_to", "assigned_department"
            )

            if not overdue_complaints.exists():
                logger.info("لا توجد شكاوى متأخرة")
                return

            # إرسال تنبيه لكل شكوى متأخرة
            for complaint in overdue_complaints:
                # تحديث حالة الشكوى إلى متأخرة إذا لم تكن كذلك
                if complaint.status != "overdue":
                    complaint.status = "overdue"
                    complaint.save()

                # إرسال تنبيه للمسؤول الحالي
                if complaint.assigned_to:
                    self._send_notification(
                        complaint=complaint,
                        recipient=complaint.assigned_to,
                        notification_type="overdue_reminder",
                        title=f"تذكير: شكوى متأخرة {complaint.complaint_number}",
                        message=f"الشكوى متأخرة منذ {(timezone.now() - complaint.deadline).days} يوم",
                        send_email=True,
                    )

                # إرسال تنبيه للمستخدمين الذين يمكن التصعيد إليهم
                self.notify_overdue_to_escalation_users(complaint)

            logger.info(
                f"تم إرسال تنبيهات يومية لـ {overdue_complaints.count()} شكوى متأخرة"
            )

        except Exception as e:
            logger.error(f"Error sending daily overdue notifications: {str(e)}")

    def notify_overdue(self, complaint):
        """
        Send notifications when complaint becomes overdue
        """
        try:
            # Notify assigned user
            if complaint.assigned_to:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.assigned_to,
                    notification_type="overdue",
                    title=f"شكوى متأخرة: {complaint.complaint_number}",
                    message=f"تجاوزت الشكوى الموعد النهائي المحدد لها",
                    send_email=True,
                )

            # Notify department manager
            if complaint.assigned_department and complaint.assigned_department.manager:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.assigned_department.manager,
                    notification_type="overdue",
                    title=f"شكوى متأخرة في القسم: {complaint.complaint_number}",
                    message=f"تجاوزت شكوى في قسم {complaint.assigned_department.name} الموعد النهائي",
                    send_email=True,
                )

        except Exception as e:
            logger.error(f"Error sending overdue notifications: {str(e)}")

    def notify_escalation(self, complaint, escalation):
        """
        Send notifications when complaint is escalated
        """
        try:
            # Notify escalated_to user
            if escalation.escalated_to:
                self._send_notification(
                    complaint=complaint,
                    recipient=escalation.escalated_to,
                    notification_type="escalation",
                    title=f"تصعيد شكوى إليك: {complaint.complaint_number}",
                    message=f"تم تصعيد شكوى من العميل {complaint.customer.name} إليك. السبب: {escalation.get_reason_display()}",
                    send_email=True,
                )

            # Notify escalated_from user
            if escalation.escalated_from:
                self._send_notification(
                    complaint=complaint,
                    recipient=escalation.escalated_from,
                    notification_type="escalation",
                    title=f"تم تصعيد الشكوى: {complaint.complaint_number}",
                    message=f'تم تصعيد الشكوى إلى {escalation.escalated_to.get_full_name() if escalation.escalated_to else "مستوى أعلى"}',
                    send_email=False,
                )

        except Exception as e:
            logger.error(f"Error sending escalation notifications: {str(e)}")

    def _send_notification(
        self, complaint, recipient, notification_type, title, message, send_email=False
    ):
        """
        Internal method to send notification via main unified system
        """
        try:
            # إنشاء إشعار في النظام الرئيسي الموحد
            _create_main_notification(
                complaint=complaint,
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
            )

            # Send email if requested
            if send_email and hasattr(recipient, "email") and recipient.email:
                self._send_email_notification(recipient, complaint, title, message)

        except Exception as e:
            logger.error(f"Error sending notification to {recipient}: {str(e)}")

    def _send_websocket_notification(self, recipient, notification):
        """
        WebSocket notifications disabled - chat system removed
        """
        # Chat system has been completely removed
        # This method is kept for compatibility but does nothing
        pass

    def _send_email_notification(self, recipient, complaint, title, message):
        """
        Send email notification
        """
        try:
            if not recipient.email:
                return

            # بناء رابط الشكوى ديناميكياً
            site_url = getattr(settings, 'SITE_URL', None)
            if not site_url:
                allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
                host = next((h for h in allowed_hosts if h not in ('*', 'localhost', '127.0.0.1')), 'localhost:8000')
                scheme = 'https' if not host.startswith('localhost') else 'http'
                site_url = f"{scheme}://{host}"

            context = {
                "recipient": recipient,
                "complaint": complaint,
                "title": title,
                "message": message,
                "complaint_url": f"{site_url}{reverse('complaints:complaint_detail', kwargs={'pk': complaint.pk})}",
            }

            html_message = render_to_string(
                "complaints/emails/notification.html", context
            )
            plain_message = render_to_string(
                "complaints/emails/notification.txt", context
            )

            send_mail(
                subject=title,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                html_message=html_message,
                fail_silently=True,
            )

        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")

    def _hide_old_assignment_notifications(self, complaint, old_assignee):
        """
        إخفاء الإشعارات القديمة للمسؤول السابق عند تغيير التعيين
        يعمل مع النظام الرئيسي الموحد (NotificationVisibility)
        """
        try:
            from django.contrib.contenttypes.models import ContentType
            from notifications.models import Notification, NotificationVisibility

            ct = ContentType.objects.get_for_model(complaint)

            # البحث عن إشعارات الشكوى القديمة للمسؤول السابق
            old_visibility = NotificationVisibility.objects.filter(
                user=old_assignee,
                is_read=False,
                notification__content_type=ct,
                notification__object_id=complaint.pk,
                notification__notification_type__in=[
                    "complaint_assigned", "complaint_created",
                ],
            )

            updated_count = old_visibility.update(is_read=True)

            if updated_count > 0:
                logger.info(
                    f"✅ تم إخفاء {updated_count} إشعار قديم للمسؤول السابق {old_assignee.username} للشكوى {complaint.complaint_number}"
                )

        except Exception as e:
            logger.error(f"Error hiding old assignment notifications: {str(e)}")

    def _hide_old_notifications_for_resolved_complaint(self, complaint):
        """
        إخفاء جميع الإشعارات القديمة عند حل الشكوى أو إغلاقها
        يعمل مع النظام الرئيسي الموحد
        """
        try:
            from django.contrib.contenttypes.models import ContentType
            from notifications.models import NotificationVisibility

            ct = ContentType.objects.get_for_model(complaint)

            updated_count = NotificationVisibility.objects.filter(
                is_read=False,
                notification__content_type=ct,
                notification__object_id=complaint.pk,
            ).update(is_read=True)

            if updated_count > 0:
                logger.info(
                    f"تم إخفاء {updated_count} إشعار قديم للشكوى المحلولة {complaint.complaint_number}"
                )

        except Exception as e:
            logger.error(
                f"Error hiding old notifications for resolved complaint: {str(e)}"
            )

    def cleanup_old_notifications(self, days=30):
        """
        تنظيف شامل للإشعارات القديمة في النظام الرئيسي الموحد
        """
        try:
            from django.contrib.contenttypes.models import ContentType
            from complaints.models import Complaint
            from notifications.models import Notification, NotificationVisibility

            ct = ContentType.objects.get_for_model(Complaint)
            total_hidden = 0

            # 1. إخفاء إشعارات الشكاوى المحلولة/المغلقة
            resolved_ids = list(Complaint.objects.filter(
                status__in=["resolved", "closed"]
            ).values_list("pk", flat=True))

            if resolved_ids:
                hidden_count = NotificationVisibility.objects.filter(
                    is_read=False,
                    notification__content_type=ct,
                    notification__object_id__in=resolved_ids,
                ).update(is_read=True)
                total_hidden += hidden_count

            # 2. حذف الإشعارات القديمة جداً (أكثر من days يوم)
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(days=days)
            old_notifications = Notification.objects.filter(
                content_type=ct,
                created_at__lt=cutoff,
                notification_type__startswith="complaint_",
            )
            old_count = old_notifications.count()
            if old_count > 0:
                # حذف visibility records أولاً ثم الإشعارات
                NotificationVisibility.objects.filter(
                    notification__in=old_notifications
                ).delete()
                old_notifications.delete()
                logger.info(f"تم حذف {old_count} إشعار شكوى قديم (أكثر من {days} يوم)")

            logger.info(f"✅ تم تنظيف {total_hidden} إشعار قديم إجمالي")
            return total_hidden

        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {str(e)}")
            return 0


# Global instance
notification_service = ComplaintNotificationService()
