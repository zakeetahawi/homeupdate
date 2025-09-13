"""
Enhanced notification service for complaints system integration
"""
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

from ..models import ComplaintNotification

User = get_user_model()
logger = logging.getLogger(__name__)


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
                    notification_type='new_complaint',
                    title=f'شكوى جديدة مسندة إليك: {complaint.complaint_number}',
                    message=f'تم إسناد شكوى جديدة من العميل {complaint.customer.name} إليك',
                    send_email=True
                )
            
            # Notify department manager
            if complaint.assigned_department and complaint.assigned_department.manager:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.assigned_department.manager,
                    notification_type='new_complaint',
                    title=f'شكوى جديدة في قسم {complaint.assigned_department.name}',
                    message=f'تم تسجيل شكوى جديدة من العميل {complaint.customer.name}',
                    send_email=False
                )
            
            # Notify supervisors
            supervisors = User.objects.filter(
                groups__name='Complaints_Supervisors',
                is_active=True
            )
            for supervisor in supervisors:
                self._send_notification(
                    complaint=complaint,
                    recipient=supervisor,
                    notification_type='new_complaint',
                    title=f'شكوى جديدة: {complaint.complaint_number}',
                    message=f'تم تسجيل شكوى جديدة من العميل {complaint.customer.name}',
                    send_email=False
                )
                
        except Exception as e:
            logger.error(f"Error sending new complaint notifications: {str(e)}")
    
    def notify_status_change(self, complaint, old_status, new_status, changed_by):
        """
        Send notifications when complaint status changes
        """
        try:
            status_messages = {
                'new': 'جديدة',
                'in_progress': 'قيد الحل',
                'resolved': 'محلولة',
                'closed': 'مغلقة',
                'overdue': 'متأخرة',
                'escalated': 'مصعدة'
            }

            message = f'تم تغيير حالة الشكوى من "{status_messages.get(old_status, old_status)}" إلى "{status_messages.get(new_status, new_status)}"'

            # إخفاء الإشعارات القديمة عند حل الشكوى أو إغلاقها
            if new_status in ['resolved', 'closed']:
                self._hide_old_notifications_for_resolved_complaint(complaint)

            # Notify customer (if resolved or closed)
            if new_status in ['resolved', 'closed'] and hasattr(complaint.customer, 'user'):
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.customer.user,
                    notification_type='status_change',
                    title=f'تحديث حالة شكواك: {complaint.complaint_number}',
                    message=message,
                    send_email=True
                )
            
            # Notify assigned user (if not the one who changed it)
            if complaint.assigned_to and complaint.assigned_to != changed_by:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.assigned_to,
                    notification_type='status_change',
                    title=f'تحديث حالة الشكوى: {complaint.complaint_number}',
                    message=message,
                    send_email=False
                )
            
            # Notify creator (if not the one who changed it)
            if complaint.created_by and complaint.created_by != changed_by:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.created_by,
                    notification_type='status_change',
                    title=f'تحديث حالة الشكوى: {complaint.complaint_number}',
                    message=message,
                    send_email=False
                )
                
        except Exception as e:
            logger.error(f"Error sending status change notifications: {str(e)}")
    
    def notify_assignment_change(self, complaint, old_assignee, new_assignee, changed_by):
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
                    notification_type='assignment',
                    title=f'تم إسناد شكوى إليك: {complaint.complaint_number}',
                    message=f'تم إسناد شكوى من العميل {complaint.customer.name} إليك',
                    send_email=True
                )
            
            # Notify old assignee
            if old_assignee and old_assignee != changed_by:
                self._send_notification(
                    complaint=complaint,
                    recipient=old_assignee,
                    notification_type='assignment',
                    title=f'تم نقل الشكوى: {complaint.complaint_number}',
                    message=f'تم نقل الشكوى إلى {new_assignee.get_full_name() if new_assignee else "مستخدم آخر"}',
                    send_email=False
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
                    notification_type='deadline',
                    title=f'اقتراب الموعد النهائي: {complaint.complaint_number}',
                    message=f'يتبقى {hours_remaining} ساعة على الموعد النهائي لحل الشكوى',
                    send_email=True
                )
                
        except Exception as e:
            logger.error(f"Error sending deadline notifications: {str(e)}")
    
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
                    notification_type='overdue',
                    title=f'شكوى متأخرة: {complaint.complaint_number}',
                    message=f'تجاوزت الشكوى الموعد النهائي المحدد لها',
                    send_email=True
                )
            
            # Notify department manager
            if complaint.assigned_department and complaint.assigned_department.manager:
                self._send_notification(
                    complaint=complaint,
                    recipient=complaint.assigned_department.manager,
                    notification_type='overdue',
                    title=f'شكوى متأخرة في القسم: {complaint.complaint_number}',
                    message=f'تجاوزت شكوى في قسم {complaint.assigned_department.name} الموعد النهائي',
                    send_email=True
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
                    notification_type='escalation',
                    title=f'تصعيد شكوى إليك: {complaint.complaint_number}',
                    message=f'تم تصعيد شكوى من العميل {complaint.customer.name} إليك. السبب: {escalation.get_reason_display()}',
                    send_email=True
                )
            
            # Notify escalated_from user
            if escalation.escalated_from:
                self._send_notification(
                    complaint=complaint,
                    recipient=escalation.escalated_from,
                    notification_type='escalation',
                    title=f'تم تصعيد الشكوى: {complaint.complaint_number}',
                    message=f'تم تصعيد الشكوى إلى {escalation.escalated_to.get_full_name() if escalation.escalated_to else "مستوى أعلى"}',
                    send_email=False
                )
                
        except Exception as e:
            logger.error(f"Error sending escalation notifications: {str(e)}")
    
    def _send_notification(self, complaint, recipient, notification_type, title, message, send_email=False):
        """
        Internal method to send notification
        """
        try:
            # Create database notification
            notification = ComplaintNotification.create_notification(
                complaint=complaint,
                notification_type=notification_type,
                recipient=recipient,
                title=title,
                message=message
            )
            
            # WebSocket notifications disabled - chat system removed
            # self._send_websocket_notification(recipient, notification)
            
            # Send email if requested
            if send_email and hasattr(recipient, 'email') and recipient.email:
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
            
            context = {
                'recipient': recipient,
                'complaint': complaint,
                'title': title,
                'message': message,
                'complaint_url': f"http://localhost:8000{reverse('complaints:complaint_detail', kwargs={'pk': complaint.pk})}"
            }
            
            html_message = render_to_string('complaints/emails/notification.html', context)
            plain_message = render_to_string('complaints/emails/notification.txt', context)
            
            send_mail(
                subject=title,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                html_message=html_message,
                fail_silently=True
            )
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")

    def _hide_old_assignment_notifications(self, complaint, old_assignee):
        """
        إخفاء الإشعارات القديمة للمسؤول السابق عند تغيير التعيين
        """
        try:
            from complaints.models import ComplaintNotification

            # تحديد الإشعارات القديمة للمسؤول السابق كمقروءة
            old_notifications = ComplaintNotification.objects.filter(
                complaint=complaint,
                recipient=old_assignee,
                notification_type__in=['assignment', 'new_complaint'],
                is_read=False
            )

            # طباعة تفاصيل للتشخيص
            logger.info(f"🔍 البحث عن إشعارات قديمة للمسؤول {old_assignee.username} للشكوى {complaint.complaint_number}")
            logger.info(f"🔍 عدد الإشعارات الموجودة قبل الإخفاء: {old_notifications.count()}")

            updated_count = old_notifications.update(is_read=True)

            if updated_count > 0:
                logger.info(f"✅ تم إخفاء {updated_count} إشعار قديم للمسؤول السابق {old_assignee.username} للشكوى {complaint.complaint_number}")
            else:
                logger.info(f"ℹ️ لا توجد إشعارات قديمة لإخفائها للمسؤول {old_assignee.username} للشكوى {complaint.complaint_number}")

            # إضافة تنظيف شامل للإشعارات غير المتطابقة
            self._cleanup_mismatched_assignment_notifications()

        except Exception as e:
            logger.error(f"Error hiding old assignment notifications: {str(e)}")

    def _cleanup_mismatched_assignment_notifications(self):
        """
        تنظيف شامل للإشعارات غير المتطابقة - إخفاء الإشعارات للمستخدمين الذين لم يعودوا مسؤولين
        """
        try:
            from complaints.models import ComplaintNotification, Complaint

            # البحث عن الإشعارات غير المقروءة للتعيين
            assignment_notifications = ComplaintNotification.objects.filter(
                notification_type__in=['assignment', 'new_complaint'],
                is_read=False,
                complaint__status__in=['new', 'in_progress', 'escalated']
            ).select_related('complaint')

            cleaned_count = 0
            for notification in assignment_notifications:
                # إذا كان المستلم للإشعار ليس هو المسؤول الحالي عن الشكوى
                if notification.complaint.assigned_to != notification.recipient:
                    notification.is_read = True
                    notification.save()
                    cleaned_count += 1
                    logger.info(f"🧹 تم إخفاء إشعار غير متطابق: الشكوى {notification.complaint.complaint_number} للمستخدم {notification.recipient.username}")

            if cleaned_count > 0:
                logger.info(f"✅ تم تنظيف {cleaned_count} إشعار غير متطابق")

        except Exception as e:
            logger.error(f"Error cleaning up mismatched assignment notifications: {str(e)}")

    def _hide_old_notifications_for_resolved_complaint(self, complaint):
        """
        إخفاء جميع الإشعارات القديمة عند حل الشكوى أو إغلاقها
        """
        try:
            from complaints.models import ComplaintNotification

            # تحديد جميع الإشعارات غير المقروءة للشكوى كمقروءة
            old_notifications = ComplaintNotification.objects.filter(
                complaint=complaint,
                is_read=False
            )

            updated_count = old_notifications.update(is_read=True)

            if updated_count > 0:
                logger.info(f"تم إخفاء {updated_count} إشعار قديم للشكوى المحلولة {complaint.complaint_number}")

        except Exception as e:
            logger.error(f"Error hiding old notifications for resolved complaint: {str(e)}")

    def cleanup_old_notifications(self):
        """
        تنظيف شامل للإشعارات القديمة
        """
        try:
            from complaints.models import ComplaintNotification, Complaint

            # إخفاء إشعارات الشكاوى المحلولة/المغلقة
            resolved_complaints = Complaint.objects.filter(status__in=['resolved', 'closed'])
            total_hidden = 0

            for complaint in resolved_complaints:
                hidden_count = ComplaintNotification.objects.filter(
                    complaint=complaint,
                    is_read=False
                ).update(is_read=True)
                total_hidden += hidden_count

                if hidden_count > 0:
                    logger.info(f"تم إخفاء {hidden_count} إشعار للشكوى المحلولة {complaint.complaint_number}")

            # إخفاء إشعارات التعيين للمستخدمين الذين لم يعودوا مسؤولين
            active_complaints = Complaint.objects.filter(status__in=['new', 'in_progress', 'escalated'])

            for complaint in active_complaints:
                if complaint.assigned_to:
                    # إخفاء إشعارات التعيين للمستخدمين الآخرين (عدا المسؤول الحالي)
                    old_notifications = ComplaintNotification.objects.filter(
                        complaint=complaint,
                        notification_type__in=['assignment', 'new_complaint'],
                        is_read=False
                    ).exclude(recipient=complaint.assigned_to)

                    hidden_count = old_notifications.update(is_read=True)
                    total_hidden += hidden_count

                    if hidden_count > 0:
                        logger.info(f"تم إخفاء {hidden_count} إشعار قديم للشكوى {complaint.complaint_number}")

            logger.info(f"✅ تم تنظيف {total_hidden} إشعار قديم إجمالي")
            return total_hidden

        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {str(e)}")
            return 0


# Global instance
notification_service = ComplaintNotificationService()
