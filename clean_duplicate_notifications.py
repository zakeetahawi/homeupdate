#!/usr/bin/env python
"""
حذف الإشعارات المكررة
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from notifications.models import Notification
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

def clean_duplicate_notifications():
    """حذف الإشعارات المكررة"""
    print("🧹 تنظيف الإشعارات المكررة")
    print("=" * 50)
    
    # البحث عن الإشعارات المكررة
    duplicates = Notification.objects.values(
        'notification_type', 'content_type', 'object_id'
    ).annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    total_deleted = 0
    
    for duplicate in duplicates:
        # الحصول على جميع الإشعارات المكررة
        notifications = Notification.objects.filter(
            notification_type=duplicate['notification_type'],
            content_type=duplicate['content_type'],
            object_id=duplicate['object_id']
        ).order_by('created_at')
        
        if notifications.count() > 1:
            # الاحتفاظ بأول إشعار وحذف الباقي
            first_notification = notifications.first()
            duplicates_to_delete = notifications.exclude(id=first_notification.id)
            
            count = duplicates_to_delete.count()
            print(f"🗑️ حذف {count} إشعار مكرر من نوع: {duplicate['notification_type']}")
            
            duplicates_to_delete.delete()
            total_deleted += count
    
    print(f"\n✅ تم حذف {total_deleted} إشعار مكرر")
    
    # إحصائيات نهائية
    total_notifications = Notification.objects.count()
    print(f"📊 إجمالي الإشعارات المتبقية: {total_notifications}")
    
    return total_deleted

def clean_old_notifications(days=30):
    """حذف الإشعارات القديمة"""
    print(f"\n🧹 حذف الإشعارات الأقدم من {days} يوم")
    print("-" * 40)
    
    cutoff_date = timezone.now() - timedelta(days=days)
    old_notifications = Notification.objects.filter(created_at__lt=cutoff_date)
    
    count = old_notifications.count()
    if count > 0:
        old_notifications.delete()
        print(f"✅ تم حذف {count} إشعار قديم")
    else:
        print("✅ لا توجد إشعارات قديمة للحذف")
    
    return count

def main():
    """الدالة الرئيسية"""
    print("🚀 تنظيف الإشعارات")
    print("=" * 60)
    
    # تنظيف الإشعارات المكررة
    duplicates_deleted = clean_duplicate_notifications()
    
    # تنظيف الإشعارات القديمة (اختياري)
    # old_deleted = clean_old_notifications(30)
    
    print("\n" + "=" * 60)
    print("🎉 تم تنظيف الإشعارات بنجاح!")
    print(f"📊 الإحصائيات:")
    print(f"  🗑️ إشعارات مكررة محذوفة: {duplicates_deleted}")
    # print(f"  📅 إشعارات قديمة محذوفة: {old_deleted}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
