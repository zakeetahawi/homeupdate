#!/usr/bin/env python
"""
اختبار أيقونات الإشعارات
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from notifications.models import Notification

def test_notification_icons():
    """اختبار أيقونات الإشعارات"""
    print("🎨 اختبار أيقونات الإشعارات")
    print("=" * 50)
    
    # الحصول على بعض الإشعارات
    notifications = Notification.objects.all()[:10]
    
    if not notifications:
        print("❌ لا توجد إشعارات للاختبار")
        return False
    
    print(f"📢 عدد الإشعارات للاختبار: {notifications.count()}")
    print()
    
    for notification in notifications:
        icon_data = notification.get_icon_and_color()
        
        print(f"📋 الإشعار: {notification.title[:50]}...")
        print(f"   🔖 النوع: {notification.notification_type}")
        print(f"   🎨 الأيقونة: {icon_data['icon']}")
        print(f"   🎨 اللون: {icon_data['color']}")
        print(f"   🎨 الخلفية: {icon_data['bg']}")
        print(f"   🔗 الرابط: {notification.get_absolute_url()}")
        print("-" * 40)
    
    return True

def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار نظام أيقونات الإشعارات")
    print("=" * 60)
    
    success = test_notification_icons()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ تم اختبار الأيقونات بنجاح!")
        print("🎨 الأيقونات والألوان جاهزة للاستخدام")
    else:
        print("❌ فشل في اختبار الأيقونات")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
