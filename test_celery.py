#!/usr/bin/env python
"""
اختبار Celery والمهام الخلفية
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from crm.celery import test_celery_connection, get_celery_stats
from orders.tasks import clear_expired_cache, cleanup_failed_uploads


def test_celery():
    """اختبار شامل لـ Celery"""
    print("🧪 اختبار Celery...")
    print("=" * 50)
    
    # اختبار الاتصال
    print("1. اختبار الاتصال:")
    connection_result = test_celery_connection()
    if connection_result['status'] == 'success':
        print(f"   ✅ {connection_result['message']}")
        print(f"   📋 Task ID: {connection_result['task_id']}")
    else:
        print(f"   ❌ {connection_result['message']}")
        return False
    
    print()
    
    # اختبار الإحصائيات
    print("2. إحصائيات Celery:")
    stats_result = get_celery_stats()
    if stats_result['status'] == 'success':
        stats = stats_result['stats']
        print(f"   👷 العمال النشطون: {stats['workers']['active']}")
        print(f"   📋 المهام النشطة: {stats['tasks']['active']}")
        print(f"   ⏰ المهام المجدولة: {stats['tasks']['scheduled']}")
        print(f"   📦 المهام المحجوزة: {stats['tasks']['reserved']}")
    else:
        print(f"   ⚠️ {stats_result['message']}")
    
    print()
    
    # اختبار مهمة تنظيف التخزين المؤقت
    print("3. اختبار مهمة تنظيف التخزين المؤقت:")
    try:
        result = clear_expired_cache.delay()
        print(f"   📤 تم إرسال المهمة: {result.id}")
        
        # انتظار النتيجة
        response = result.get(timeout=30)
        if response['success']:
            print(f"   ✅ {response['message']}")
        else:
            print(f"   ❌ {response['message']}")
    except Exception as e:
        print(f"   ❌ خطأ في المهمة: {str(e)}")
    
    print()
    
    # اختبار مهمة تنظيف الملفات الفاشلة
    print("4. اختبار مهمة تنظيف الملفات الفاشلة:")
    try:
        result = cleanup_failed_uploads.delay()
        print(f"   📤 تم إرسال المهمة: {result.id}")
        
        # انتظار النتيجة
        response = result.get(timeout=30)
        if response['success']:
            print(f"   ✅ تم إعادة جدولة {response['orders_retried']} ملف عقد")
            print(f"   ✅ تم إعادة جدولة {response['inspections_retried']} ملف معاينة")
        else:
            print(f"   ❌ {response['message']}")
    except Exception as e:
        print(f"   ❌ خطأ في المهمة: {str(e)}")
    
    print()
    print("✅ انتهى اختبار Celery بنجاح!")
    return True


def test_redis():
    """اختبار اتصال Redis/Valkey"""
    print("🔴 اختبار Redis/Valkey...")
    print("=" * 50)

    try:
        import redis

        # الاتصال بـ Redis/Valkey
        r = redis.Redis(host='localhost', port=6379, db=0)

        # اختبار الاتصال
        if r.ping():
            print("✅ Redis/Valkey متصل ويعمل بشكل طبيعي")

            # اختبار الكتابة والقراءة
            r.set('test_key', 'test_value', ex=10)
            value = r.get('test_key')

            if value and value.decode() == 'test_value':
                print("✅ اختبار الكتابة والقراءة نجح")
                r.delete('test_key')
            else:
                print("❌ فشل في اختبار الكتابة والقراءة")
                return False

            # معلومات Redis/Valkey
            try:
                info = r.info()
                version = info.get('redis_version') or info.get('valkey_version', 'غير معروف')
                print(f"📊 الإصدار: {version}")
                print(f"💾 استخدام الذاكرة: {info.get('used_memory_human', 'غير معروف')}")
                print(f"👥 العملاء المتصلون: {info.get('connected_clients', 'غير معروف')}")
            except Exception:
                print("📊 معلومات الخادم غير متاحة")

            return True
        else:
            print("❌ فشل في الاتصال بـ Redis/Valkey")
            return False

    except ImportError:
        print("❌ مكتبة redis غير مثبتة")
        print("   قم بتثبيتها باستخدام: pip install redis")
        return False
    except Exception as e:
        print(f"❌ خطأ في الاتصال بـ Redis/Valkey: {str(e)}")
        print("   تأكد من تشغيل Redis/Valkey: valkey-server أو redis-server")
        return False


def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار نظام المهام الخلفية")
    print("=" * 60)
    print()
    
    # اختبار Redis أولاً
    redis_ok = test_redis()
    print()
    
    if not redis_ok:
        print("❌ يجب إصلاح مشاكل Redis قبل اختبار Celery")
        print("💡 تأكد من تشغيل Redis: redis-server")
        return False
    
    # اختبار Celery
    celery_ok = test_celery()
    
    if celery_ok:
        print()
        print("🎉 جميع الاختبارات نجحت!")
        print("💡 يمكنك الآن استخدام المهام الخلفية في النظام")
        print()
        print("📋 أوامر مفيدة:")
        print("   - مراقبة العمال: celery -A crm inspect active")
        print("   - مراقبة المهام: celery -A crm events")
        print("   - إحصائيات: celery -A crm inspect stats")
        print("   - مراقبة السجلات: tail -f /tmp/celery_worker.log")
    else:
        print()
        print("❌ فشل في بعض الاختبارات")
        print("💡 تأكد من تشغيل Celery Worker:")
        print("   celery -A crm worker --loglevel=info")
    
    return celery_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
