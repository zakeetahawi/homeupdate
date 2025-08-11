#!/usr/bin/env python
"""
اختبار نظام الإشعارات
"""

import os
import sys
import django

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from accounts.services.simple_notifications import SimpleNotificationService
from accounts.models import SimpleNotification, ComplaintNotification

def test_notifications():
    print("🎨 اختبار نظام الإشعارات البسيط والمتقدم")
    print("=" * 50)
    
    # الحصول على آخر طلب
    order = Order.objects.last()
    if not order:
        print("❌ لا توجد طلبات في النظام")
        return
    
    print(f"📋 آخر طلب: {order.order_number}")
    print(f"👤 العميل: {order.customer.name}")
    
    # إنشاء إشعارات للطلب
    print("\n🔔 إنشاء إشعارات للطلب...")
    notifications = SimpleNotificationService.notify_new_order(order)
    
    print(f"✅ تم إنشاء {len(notifications)} إشعار")
    
    # عرض الإشعارات
    print("\n📋 قائمة الإشعارات:")
    for i, notification in enumerate(notifications, 1):
        print(f"{i}. {notification.get_icon()} {notification.title}")
        print(f"   👤 المستلم: {notification.recipient.username}")
        print(f"   🎯 النوع: {notification.get_notification_type_display()}")
        print(f"   ⚡ الأولوية: {notification.get_priority_display()}")
        print()
    
    # إحصائيات
    total_order_notifications = SimpleNotification.objects.count()
    total_complaint_notifications = ComplaintNotification.objects.count()
    unread_orders = SimpleNotification.objects.filter(is_read=False).count()
    unread_complaints = ComplaintNotification.objects.filter(is_read=False).count()
    
    print("📊 إحصائيات النظام:")
    print(f"🔔 إجمالي إشعارات الطلبات: {total_order_notifications}")
    print(f"📢 إجمالي إشعارات الشكاوى: {total_complaint_notifications}")
    print(f"🔴 إشعارات طلبات غير مقروءة: {unread_orders}")
    print(f"🟠 إشعارات شكاوى غير مقروءة: {unread_complaints}")
    
    print("\n🎉 تم اختبار النظام بنجاح!")

if __name__ == "__main__":
    test_notifications()
