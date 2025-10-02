#!/usr/bin/env python
"""
اختبار مزامنة الحالات بين الطلبات وأوامر التصنيع
"""

import os
import sys

import django

# إعداد Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from manufacturing.models import ManufacturingOrder
from notifications.models import Notification
from orders.models import Order


def test_status_sync():
    """اختبار مزامنة الحالات"""
    print("🧪 اختبار مزامنة الحالات")
    print("=" * 50)

    # البحث عن طلب حديث مع أمر تصنيع
    order = Order.objects.filter(manufacturing_order__isnull=False).first()

    if not order:
        print("❌ لا توجد طلبات مع أوامر تصنيع للاختبار")
        return False

    manufacturing_order = order.manufacturing_order

    print(f"📋 الطلب: {order.order_number}")
    print(f"🏭 أمر التصنيع: {manufacturing_order.id}")
    print(f"📊 حالة الطلب الحالية: {order.order_status}")
    print(f"🔧 حالة التصنيع الحالية: {manufacturing_order.status}")

    # عد الإشعارات قبل التحديث
    notifications_before = Notification.objects.count()
    print(f"📢 عدد الإشعارات قبل التحديث: {notifications_before}")

    # تحديث حالة أمر التصنيع
    old_status = manufacturing_order.status
    new_status = "in_progress" if old_status != "in_progress" else "pending"

    print(f"\n🔄 تحديث حالة التصنيع من '{old_status}' إلى '{new_status}'")

    manufacturing_order.status = new_status
    manufacturing_order.save()

    # تحديث بيانات الطلب
    order.refresh_from_db()

    # عد الإشعارات بعد التحديث
    notifications_after = Notification.objects.count()
    print(f"📢 عدد الإشعارات بعد التحديث: {notifications_after}")

    # التحقق من النتائج
    print(f"\n📊 النتائج:")
    print(f"  🏭 حالة التصنيع الجديدة: {manufacturing_order.status}")
    print(f"  📋 حالة الطلب الجديدة: {order.order_status}")
    print(f"  📢 إشعارات جديدة: {notifications_after - notifications_before}")

    # التحقق من التطابق
    if order.order_status == manufacturing_order.status:
        print("✅ الحالات متطابقة!")
        success = True
    else:
        print("❌ الحالات غير متطابقة!")
        success = False

    # عرض الإشعارات الجديدة
    if notifications_after > notifications_before:
        new_notifications = Notification.objects.order_by("-created_at")[
            : notifications_after - notifications_before
        ]
        print(f"\n📢 الإشعارات الجديدة:")
        for notif in new_notifications:
            print(f"  - {notif.title}")
            print(f"    {notif.message}")
            print(f"    نوع: {notif.notification_type}")

    return success


def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار نظام مزامنة الحالات")
    print("=" * 60)

    success = test_status_sync()

    print("\n" + "=" * 60)
    if success:
        print("🎉 الاختبار نجح!")
    else:
        print("❌ الاختبار فشل!")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
