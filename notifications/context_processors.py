from .utils import get_user_notification_count
from .models import Notification
from django.core.cache import cache


def notifications_context(request):
    """
    إضافة معلومات الإشعارات إلى السياق العام
    مُحسّن مع التخزين المؤقت
    """
    context = {}
    
    if request.user.is_authenticated:
        user_id = request.user.id
        
        # التخزين المؤقت لعدد الإشعارات (30 ثانية فقط - تتغير كثيراً)
        count_cache_key = f'ctx_notif_count_{user_id}'
        unread_count = cache.get(count_cache_key)
        
        if unread_count is None:
            unread_count = get_user_notification_count(request.user)
            cache.set(count_cache_key, unread_count, 30)
        
        # التخزين المؤقت للإشعارات الأخيرة (30 ثانية)
        notif_cache_key = f'ctx_notif_recent_{user_id}'
        recent_notifications = cache.get(notif_cache_key)
        
        if recent_notifications is None:
            recent_notifications = list(
                Notification.objects.recent_for_user(
                    request.user, limit=10
                ).select_related('created_by', 'content_type')
            )
            cache.set(notif_cache_key, recent_notifications, 30)
        
        context.update({
            'notifications_unread_count': unread_count,
            'recent_notifications': recent_notifications,
        })
    
    return context
