from django import template

register = template.Library()


@register.filter(name="getattribute")
def getattribute(obj, attr):
    """
    Template filter للحصول على خاصية من كائن باستخدام اسم الخاصية كنص
    الاستخدام: {{ form|getattribute:field_name }}
    """
    try:
        return getattr(obj, attr)
    except (AttributeError, TypeError):
        return None


@register.filter
def notification_icon(notification_type):
    """
    إرجاع أيقونة مناسبة لنوع الإشعار
    """
    icons = {
        "customer_created": "fas fa-user-plus",
        "order_created": "fas fa-shopping-cart",
        "order_updated": "fas fa-edit",
        "order_status_changed": "fas fa-exchange-alt",
        "order_delivered": "fas fa-truck",
        "installation_scheduled": "fas fa-calendar-plus",
        "installation_completed": "fas fa-check-circle",
        "inspection_created": "fas fa-search-plus",
        "inspection_status_changed": "fas fa-clipboard-check",
        "manufacturing_status_changed": "fas fa-industry",
        "complaint_created": "fas fa-exclamation-triangle",
        # إشعارات التقطيع الجديدة
        "cutting_order_created": "fas fa-cut",
        "cutting_completed": "fas fa-check-circle",
        "cutting_item_rejected": "fas fa-times-circle",
        "stock_shortage": "fas fa-exclamation-triangle",
        "fabric_received": "fas fa-industry",
        "cutting_ready_for_pickup": "fas fa-hand-holding",
    }
    return icons.get(notification_type, "fas fa-bell")


@register.filter
def notification_color(notification_type):
    """
    إرجاع لون مناسب لنوع الإشعار
    """
    colors = {
        "customer_created": "success",
        "order_created": "primary",
        "order_updated": "info",
        "order_status_changed": "warning",
        "order_delivered": "success",
        "installation_scheduled": "info",
        "installation_completed": "success",
        "inspection_created": "primary",
        "inspection_status_changed": "warning",
        "manufacturing_status_changed": "secondary",
        "complaint_created": "danger",
        # إشعارات التقطيع الجديدة
        "cutting_order_created": "primary",
        "cutting_completed": "success",
        "cutting_item_rejected": "danger",
        "stock_shortage": "warning",
        "fabric_received": "info",
        "cutting_ready_for_pickup": "info",
    }
    return colors.get(notification_type, "secondary")


@register.filter
def priority_badge_class(priority):
    """
    إرجاع class مناسب لأولوية الإشعار
    """
    classes = {
        "low": "badge-secondary",
        "normal": "badge-primary",
        "high": "badge-warning",
        "urgent": "badge-danger",
    }
    return classes.get(priority, "badge-secondary")


@register.inclusion_tag("notifications/notification_badge.html")
def notification_badge(notification):
    """
    عرض شارة الإشعار مع الأيقونة واللون المناسب
    """
    return {
        "notification": notification,
        "icon_class": notification_icon(notification.notification_type),
        "color_class": notification_color(notification.notification_type),
        "priority_class": priority_badge_class(notification.priority),
    }


@register.simple_tag
def notification_settings_summary(user):
    """
    إرجاع ملخص إعدادات الإشعارات للمستخدم
    """
    from ..models import NotificationSettings

    try:
        settings = NotificationSettings.objects.get(user=user)
        enabled_types = settings.get_notification_types_display()

        return {
            "enabled": settings.notifications_enabled,
            "enabled_types_count": len(enabled_types),
            "min_priority": settings.get_min_priority_level_display(),
            "enabled_types": enabled_types,
        }
    except NotificationSettings.DoesNotExist:
        return {
            "enabled": True,
            "enabled_types_count": 11,  # العدد الافتراضي
            "min_priority": "منخفض",
            "enabled_types": [],
        }


@register.filter
def is_notification_enabled(user, notification_type):
    """
    فحص ما إذا كان نوع إشعار معين مفعل للمستخدم
    """
    from ..models import NotificationSettings

    try:
        settings = NotificationSettings.objects.get(user=user)
        return settings.is_notification_type_enabled(notification_type)
    except NotificationSettings.DoesNotExist:
        return True  # افتراضياً مفعل


@register.filter
def notifications_enabled_for_user(user):
    """
    فحص ما إذا كانت الإشعارات مفعلة للمستخدم
    """
    from ..models import NotificationSettings

    try:
        settings = NotificationSettings.objects.get(user=user)
        return settings.notifications_enabled
    except NotificationSettings.DoesNotExist:
        return True  # افتراضياً مفعل
