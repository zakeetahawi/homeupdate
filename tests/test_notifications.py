#!/usr/bin/env python
"""
سكريبت لاختبار نظام الإشعارات
"""
import os
import sys

import django

# إعداد Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model

from customers.models import Customer
from notifications.signals import create_notification
from orders.models import Order

User = get_user_model()


def test_notifications():
    """اختبار إنشاء الإشعارات"""
    print("🔔 اختبار نظام الإشعارات...")

    # الحصول على أول مستخدم
    user = User.objects.first()
    if not user:
        print("❌ لا يوجد مستخدمين في النظام")
        return

    print(f"✅ تم العثور على المستخدم: {user.username}")

    # إنشاء إشعارات تجريبية
    notifications_data = [
        {
            "title": "مرحباً بك في نظام الإشعارات",
            "message": "تم تفعيل نظام الإشعارات الجديد بنجاح. ستتلقى الآن إشعارات فورية عن جميع الأحداث المهمة في النظام.",
            "notification_type": "customer_created",
            "priority": "high",
        },
        {
            "title": "إشعار تجريبي - طلب جديد",
            "message": "هذا إشعار تجريبي يحاكي إنشاء طلب جديد في النظام.",
            "notification_type": "order_created",
            "priority": "normal",
        },
        {
            "title": "إشعار تجريبي - معاينة مكتملة",
            "message": "تم إكمال معاينة تجريبية بنجاح.",
            "notification_type": "inspection_status_changed",
            "priority": "high",
        },
        {
            "title": "إشعار عاجل - شكوى جديدة",
            "message": "تم تسجيل شكوى جديدة تتطلب اهتماماً فورياً.",
            "notification_type": "complaint_created",
            "priority": "urgent",
        },
        {
            "title": "إشعار منخفض الأولوية",
            "message": "هذا إشعار تجريبي منخفض الأولوية.",
            "notification_type": "installation_scheduled",
            "priority": "low",
        },
    ]

    created_count = 0
    for data in notifications_data:
        try:
            notification = create_notification(
                title=data["title"],
                message=data["message"],
                notification_type=data["notification_type"],
                created_by=user,
                priority=data["priority"],
                recipients=[user],
            )
            print(f"✅ تم إنشاء الإشعار: {notification.title}")
            created_count += 1
        except Exception as e:
            print(f"❌ خطأ في إنشاء الإشعار: {e}")

    print(f"\n🎉 تم إنشاء {created_count} إشعار بنجاح!")

    # عرض إحصائيات
    from notifications.models import Notification, NotificationVisibility
    from notifications.utils import get_user_notification_count

    total_notifications = Notification.objects.count()
    user_notifications = Notification.objects.for_user(user).count()
    unread_count = get_user_notification_count(user)

    print(f"\n📊 إحصائيات الإشعارات:")
    print(f"   - إجمالي الإشعارات: {total_notifications}")
    print(f"   - إشعارات المستخدم: {user_notifications}")
    print(f"   - غير مقروءة: {unread_count}")


if __name__ == "__main__":
    test_notifications()
