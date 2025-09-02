#!/usr/bin/env python
"""
اختبار إشعارات المعاينة
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inspections.models import Inspection
from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

def test_inspection_notifications():
    """اختبار إشعارات المعاينة"""
    print("🧪 اختبار إشعارات المعاينة")
    print("=" * 50)
    
    # البحث عن معاينة للاختبار
    inspection = Inspection.objects.first()
    
    if not inspection:
        print("❌ لا توجد معاينات للاختبار")
        return False
    
    print(f"📋 المعاينة: {inspection.contract_number}")
    print(f"📊 الحالة الحالية: {inspection.status}")
    print(f"📊 خيارات الحالة: {inspection.STATUS_CHOICES}")
    
    # عد الإشعارات قبل التحديث
    notifications_before = Notification.objects.count()
    print(f"📢 عدد الإشعارات قبل التحديث: {notifications_before}")
    
    # تحديث حالة المعاينة
    old_status = inspection.status
    new_status = 'completed' if old_status != 'completed' else 'pending'
    
    print(f"\n🔄 تحديث حالة المعاينة من '{old_status}' إلى '{new_status}'")
    
    inspection.status = new_status
    inspection.save()
    
    # عد الإشعارات بعد التحديث
    notifications_after = Notification.objects.count()
    print(f"📢 عدد الإشعارات بعد التحديث: {notifications_after}")
    
    # التحقق من النتائج
    new_notifications_count = notifications_after - notifications_before
    print(f"📢 إشعارات جديدة: {new_notifications_count}")
    
    if new_notifications_count > 0:
        print("✅ تم إنشاء إشعار!")
        
        # عرض الإشعارات الجديدة
        new_notifications = Notification.objects.order_by('-created_at')[:new_notifications_count]
        for notif in new_notifications:
            print(f"  📢 {notif.title}")
            print(f"     {notif.message}")
            print(f"     نوع: {notif.notification_type}")
            print(f"     أولوية: {notif.priority}")
        
        return True
    else:
        print("❌ لم يتم إنشاء إشعار!")
        
        # فحص السبب
        print("\n🔍 فحص الأسباب المحتملة:")
        
        # 1. فحص إذا كان هناك تغيير فعلي
        inspection.refresh_from_db()
        print(f"  1. الحالة الجديدة في قاعدة البيانات: {inspection.status}")
        
        # 2. فحص إذا كان signal مفعل
        from django.db.models.signals import pre_save
        from notifications.signals import inspection_status_changed_notification
        
        receivers = pre_save._live_receivers(sender=Inspection)
        signal_found = any('inspection_status_changed_notification' in str(receiver) for receiver in receivers)
        print(f"  2. Signal مفعل: {signal_found}")
        
        # 3. فحص المستخدمين المستهدفين
        from notifications.utils import get_notification_recipients
        recipients = get_notification_recipients('inspection_status_changed', inspection, None)
        print(f"  3. عدد المستخدمين المستهدفين: {recipients.count()}")
        
        if recipients.exists():
            print(f"     المستخدمون: {[u.username for u in recipients[:5]]}")
        
        return False

def test_manual_notification():
    """اختبار إنشاء إشعار يدوي"""
    print("\n🧪 اختبار إنشاء إشعار يدوي")
    print("-" * 40)
    
    from notifications.signals import create_notification
    
    inspection = Inspection.objects.first()
    if not inspection:
        print("❌ لا توجد معاينات")
        return False
    
    try:
        notification = create_notification(
            title="اختبار إشعار المعاينة",
            message="هذا اختبار لإشعار المعاينة",
            notification_type='inspection_status_changed',
            related_object=inspection,
            priority='normal'
        )
        
        print(f"✅ تم إنشاء إشعار يدوي: {notification.title}")
        return True
        
    except Exception as e:
        print(f"❌ فشل في إنشاء الإشعار: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار نظام إشعارات المعاينة")
    print("=" * 60)
    
    # اختبار التحديث التلقائي
    auto_success = test_inspection_notifications()
    
    # اختبار الإنشاء اليدوي
    manual_success = test_manual_notification()
    
    print("\n" + "=" * 60)
    print("📊 النتائج:")
    print(f"  🔄 التحديث التلقائي: {'✅ نجح' if auto_success else '❌ فشل'}")
    print(f"  ✋ الإنشاء اليدوي: {'✅ نجح' if manual_success else '❌ فشل'}")
    
    return auto_success or manual_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
