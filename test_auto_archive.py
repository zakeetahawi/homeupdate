#!/usr/bin/env python
"""
سكريبت اختبار الأرشفة التلقائية للتركيبات
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from installations.models import InstallationSchedule, InstallationArchive, InstallationEventLog
from orders.models import Order
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

def test_auto_archive():
    """اختبار الأرشفة التلقائية"""
    print("🔍 بدء اختبار الأرشفة التلقائية...")

    # الحصول على تركيب غير مكتمل
    installation = InstallationSchedule.objects.filter(status__in=['scheduled', 'in_installation']).first()

    if not installation:
        print("❌ لم يتم العثور على تركيب غير مكتمل للاختبار")
        return

    print(f"📋 تم العثور على تركيب: {installation.installation_code}")
    print(f"📊 الحالة الحالية: {installation.get_status_display()}")

    # الحصول على مستخدم للاختبار
    user = User.objects.filter(is_active=True).first()
    if not user:
        print("❌ لم يتم العثور على مستخدم نشط")
        return

    print(f"👤 سيتم استخدام المستخدم: {user.get_full_name() or user.username}")

    # حفظ عدد الأرشيفات قبل الاختبار
    archives_before = InstallationArchive.objects.count()
    events_before = InstallationEventLog.objects.count()

    print(f"📊 عدد الأرشيفات قبل: {archives_before}")
    print(f"📊 عدد الأحداث قبل: {events_before}")

    # محاكاة تسجيل الدخول للمستخدم
    from accounts.middleware.current_user import _thread_locals
    _thread_locals.user = user
    _thread_locals.request = None

    try:
        # تغيير حالة التركيب إلى مكتملة
        print("🔄 جاري تغيير حالة التركيب إلى مكتملة...")
        installation.status = 'completed'
        installation.save()

        # التحقق من إنشاء الأرشيف
        archives_after = InstallationArchive.objects.count()
        events_after = InstallationEventLog.objects.count()

        print(f"📊 عدد الأرشيفات بعد: {archives_after}")
        print(f"📊 عدد الأحداث بعد: {events_after}")

        if archives_after > archives_before:
            print("✅ تم إنشاء الأرشيف تلقائياً!")

            # الحصول على الأرشيف الجديد
            archive = InstallationArchive.objects.filter(installation=installation).first()
            if archive:
                print(f"📁 الأرشيف: {archive}")
                print(f"👤 أرشف بواسطة: {archive.archived_by.get_full_name() if archive.archived_by else 'غير محدد'}")
                print(f"📝 ملاحظات: {archive.archive_notes}")
        else:
            print("❌ لم يتم إنشاء الأرشيف")

        if events_after > events_before:
            print("✅ تم تسجيل الحدث!")

            # الحصول على الحدث الجديد
            event = InstallationEventLog.objects.filter(installation=installation).order_by('-created_at').first()
            if event:
                print(f"📋 الحدث: {event.get_event_type_display()}")
                print(f"👤 المستخدم: {event.user.get_full_name() if event.user else 'غير محدد'}")
                print(f"📝 الوصف: {event.description}")
        else:
            print("❌ لم يتم تسجيل الحدث")

    except Exception as e:
        print(f"❌ خطأ أثناء الاختبار: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # تنظيف thread local storage
        if hasattr(_thread_locals, 'user'):
            delattr(_thread_locals, 'user')
        if hasattr(_thread_locals, 'request'):
            delattr(_thread_locals, 'request')

    print("🏁 انتهى الاختبار")

if __name__ == '__main__':
    test_auto_archive()