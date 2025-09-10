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
            
            # Send real-time notification via WebSocket
            self._send_websocket_notification(recipient, notification)
            
            # Send email if requested
            if send_email and hasattr(recipient, 'email') and recipient.email:
                self._send_email_notification(recipient, complaint, title, message)
                
        except Exception as e:
            logger.error(f"Error sending notification to {recipient}: {str(e)}")
    
    def _send_websocket_notification(self, recipient, notification):
        """
        Send real-time notification via WebSocket
        """
        try:
            if self.channel_layer:
                async_to_sync(self.channel_layer.group_send)(
                    f"user_{recipient.id}_notifications",
                    {
                        "type": "notification.message",
                        "notification": {
                            "id": notification.id,
                            "type": notification.notification_type,
                            "title": notification.title,
                            "message": notification.message,
                            "url": notification.url,
                            "created_at": notification.created_at.isoformat()
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {str(e)}")
    
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
                'complaint_url': f"{settings.SITE_URL}{reverse('complaints:complaint_detail', kwargs={'pk': complaint.pk})}"
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


# Global instance
notification_service = ComplaintNotificationService()
