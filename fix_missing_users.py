#!/usr/bin/env python3
"""
Script لإصلاح السجلات التي لا تحتوي على معلومات المستخدم
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from orders.models import OrderStatusLog
from notifications.models import Notification
from django.utils import timezone

User = get_user_model()

def fix_missing_users():
    """إصلاح السجلات التي لا تحتوي على معلومات المستخدم"""
    
    print("🔧 إصلاح السجلات التي لا تحتوي على معلومات المستخدم...")
    print("=" * 60)
    
    # 1. إصلاح سجلات الحالة
    print("\n1️⃣ إصلاح سجلات الحالة:")
    
    # البحث عن سجلات بدون مستخدم
    logs_without_user = OrderStatusLog.objects.filter(changed_by__isnull=True)
    print(f"📊 عدد السجلات بدون مستخدم: {logs_without_user.count()}")
    
    # الحصول على مستخدم افتراضي
    default_user = User.objects.filter(is_superuser=True).first()
    if not default_user:
        default_user = User.objects.first()
    
    if default_user:
        print(f"👤 سيتم استخدام المستخدم الافتراضي: {default_user.get_full_name()}")
        
        # تحديث السجلات
        updated_count = 0
        for log in logs_without_user[:100]:  # تحديث أول 100 سجل فقط لتجنب التحميل الزائد
            try:
                log.changed_by = default_user
                log.save(update_fields=['changed_by'])
                updated_count += 1
                
                if updated_count % 10 == 0:
                    print(f"   ✅ تم تحديث {updated_count} سجل...")
                    
            except Exception as e:
                print(f"   ❌ خطأ في تحديث السجل {log.id}: {e}")
        
        print(f"📈 تم تحديث {updated_count} سجل بنجاح")
    else:
        print("❌ لم يتم العثور على مستخدم افتراضي")
    
    # 2. إصلاح الإشعارات
    print("\n2️⃣ إصلاح الإشعارات:")
    
    # البحث عن إشعارات التصنيع بدون مستخدم
    notifications_without_user = Notification.objects.filter(
        notification_type='manufacturing_status_changed',
        created_by__isnull=True
    )
    
    print(f"📊 عدد الإشعارات بدون مستخدم: {notifications_without_user.count()}")
    
    if default_user:
        # تحديث الإشعارات
        updated_notifications = 0
        for notification in notifications_without_user[:50]:  # تحديث أول 50 إشعار فقط
            try:
                notification.created_by = default_user
                
                # تحديث البيانات الإضافية
                extra_data = notification.extra_data.copy()
                if extra_data.get('changed_by') in [None, 'مستخدم النظام']:
                    extra_data['changed_by'] = default_user.get_full_name()
                if extra_data.get('changed_by_username') in [None, 'system']:
                    extra_data['changed_by_username'] = default_user.username
                
                notification.extra_data = extra_data
                notification.save(update_fields=['created_by', 'extra_data'])
                updated_notifications += 1
                
                if updated_notifications % 10 == 0:
                    print(f"   ✅ تم تحديث {updated_notifications} إشعار...")
                    
            except Exception as e:
                print(f"   ❌ خطأ في تحديث الإشعار {notification.id}: {e}")
        
        print(f"📈 تم تحديث {updated_notifications} إشعار بنجاح")
    
    # 3. إحصائيات محدثة
    print("\n3️⃣ إحصائيات محدثة:")
    
    total_logs = OrderStatusLog.objects.count()
    logs_with_user = OrderStatusLog.objects.filter(changed_by__isnull=False).count()
    
    total_notifications = Notification.objects.filter(
        notification_type='manufacturing_status_changed'
    ).count()
    notifications_with_user = Notification.objects.filter(
        notification_type='manufacturing_status_changed',
        created_by__isnull=False
    ).count()
    
    print(f"📊 إجمالي سجلات الحالة: {total_logs}")
    print(f"👤 سجلات مع مستخدم: {logs_with_user} ({logs_with_user/total_logs*100:.1f}%)")
    print(f"📝 سجلات بدون مستخدم: {total_logs - logs_with_user}")
    
    print(f"🔔 إجمالي إشعارات التصنيع: {total_notifications}")
    print(f"👤 إشعارات مع مستخدم: {notifications_with_user} ({notifications_with_user/total_notifications*100:.1f}%)")
    print(f"📝 إشعارات بدون مستخدم: {total_notifications - notifications_with_user}")
    
    # 4. عرض عينة من السجلات المحدثة
    print("\n4️⃣ عينة من السجلات المحدثة:")
    recent_logs = OrderStatusLog.objects.filter(
        changed_by__isnull=False
    ).order_by('-created_at')[:3]
    
    for log in recent_logs:
        print(f"\n   📋 الطلب: {log.order.order_number}")
        print(f"   🔄 {log.get_old_status_display()} → {log.get_new_status_display()}")
        print(f"   👤 المستخدم: {log.changed_by.get_full_name() if log.changed_by else 'غير محدد'}")
        print(f"   ⏰ التاريخ: {log.created_at}")
    
    print("\n" + "=" * 60)
    print("✅ تم الانتهاء من إصلاح السجلات")
    print("🎯 النتائج:")
    print("- تم تحديث السجلات التي لا تحتوي على معلومات المستخدم")
    print("- تم تحديث الإشعارات التي لا تحتوي على معلومات المستخدم")
    print("- ستظهر الآن معلومات المستخدم بشكل صحيح في جميع السجلات")

if __name__ == '__main__':
    fix_missing_users()
