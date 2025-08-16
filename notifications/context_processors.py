from .utils import get_user_notification_count
from .models import Notification


def notifications_context(request):
    """
    إضافة معلومات الإشعارات إلى السياق العام
    """
    context = {}
    
    if request.user.is_authenticated:
        # عدد الإشعارات غير المقروءة
        unread_count = get_user_notification_count(request.user)
        
        # آخر الإشعارات (للعرض في القائمة المنسدلة)
        recent_notifications = Notification.objects.recent_for_user(
            request.user, limit=5
        ).select_related('created_by', 'content_type')
        
        context.update({
            'notifications_unread_count': unread_count,
            'recent_notifications': recent_notifications,
        })
    
    return context
