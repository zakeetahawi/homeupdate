from django.core.cache import cache

from .models import Notification
from .utils import get_user_notification_count

_NOTIF_CACHE_TTL = 30  # 30 ثانية


def notifications_context(request):
    """
    إضافة معلومات الإشعارات إلى السياق العام — Cached 30s per user
    """
    if not request.user.is_authenticated:
        return {}

    user = request.user
    cache_key = f"ctx_notif_{user.pk}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    unread_count = get_user_notification_count(user)

    recent_notifications = list(
        Notification.objects.recent_for_user(user, limit=10).select_related(
            "created_by", "content_type"
        )
    )

    result = {
        "notifications_unread_count": unread_count,
        "recent_notifications": recent_notifications,
    }
    cache.set(cache_key, result, _NOTIF_CACHE_TTL)
    return result
