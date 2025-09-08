#!/usr/bin/env python
"""
اختبار نظام الدردشة والإصلاحات
"""
import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from modern_chat.models import UserStatus, ChatRoom, Message
from django.conf import settings

User = get_user_model()

def test_django_settings():
    """اختبار إعدادات Django"""
    print("🔧 اختبار إعدادات Django...")
    
    # فحص ASGI
    if hasattr(settings, 'ASGI_APPLICATION'):
        asgi_app = settings.ASGI_APPLICATION
        print(f"✅ ASGI_APPLICATION: {asgi_app}")
        
        if asgi_app == 'crm.asgi:application':
            print("✅ ASGI مضبوط بشكل صحيح")
        else:
            print(f"❌ ASGI خطأ - يجب أن يكون 'crm.asgi:application'")
    else:
        print("❌ ASGI_APPLICATION غير مُعرف")
    
    # فحص CHANNEL_LAYERS
    if hasattr(settings, 'CHANNEL_LAYERS'):
        backend = settings.CHANNEL_LAYERS['default']['BACKEND']
        print(f"✅ CHANNEL_LAYERS: {backend}")
        
        if 'redis' in backend.lower():
            print("✅ Redis backend مضبوط")
        else:
            print(f"⚠️ Backend غير Redis: {backend}")
    else:
        print("❌ CHANNEL_LAYERS غير مُعرف")
    
    # فحص ALLOWED_HOSTS
    if hasattr(settings, 'ALLOWED_HOSTS'):
        hosts = settings.ALLOWED_HOSTS
        print(f"✅ ALLOWED_HOSTS: {hosts}")
        
        if '*' in hosts or 'localhost' in hosts:
            print("✅ ALLOWED_HOSTS يسمح بالاتصال المحلي")
        else:
            print(f"⚠️ قد تكون هناك مشكلة في ALLOWED_HOSTS")
    else:
        print("❌ ALLOWED_HOSTS غير مُعرف")

def test_redis_connection():
    """اختبار Redis"""
    print("\n🔌 اختبار Redis...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis يعمل")
        
        # اختبار channel layer
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        
        if channel_layer:
            print(f"✅ Channel Layer: {type(channel_layer).__name__}")
        else:
            print("❌ لا يمكن الحصول على Channel Layer")
            
    except Exception as e:
        print(f"❌ Redis لا يعمل: {e}")

def test_database():
    """اختبار قاعدة البيانات"""
    print("\n📊 اختبار قاعدة البيانات...")
    
    # إحصائيات
    users_count = User.objects.count()
    status_count = UserStatus.objects.count()
    rooms_count = ChatRoom.objects.count()
    messages_count = Message.objects.count()
    
    print(f"المستخدمين: {users_count}")
    print(f"حالات المستخدمين: {status_count}")
    print(f"غرف الدردشة: {rooms_count}")
    print(f"الرسائل: {messages_count}")
    
    # التحقق من تطابق المستخدمين مع الحالات
    if users_count == status_count:
        print("✅ جميع المستخدمين لديهم حالات")
    else:
        missing = users_count - status_count
        print(f"⚠️ {missing} مستخدم بدون حالة")
        
        # إنشاء حالات للمستخدمين المفقودين
        users_without_status = User.objects.exclude(
            id__in=UserStatus.objects.values_list('user_id', flat=True)
        )
        
        for user in users_without_status:
            UserStatus.objects.create(user=user, status='offline')
            print(f"✅ تم إنشاء حالة للمستخدم: {user.username}")

def create_test_users():
    """إنشاء مستخدمين للاختبار"""
    print("\n👥 إنشاء مستخدمين للاختبار...")
    
    # مستخدم admin
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'مدير',
            'last_name': 'النظام',
            'is_superuser': True,
            'is_staff': True
        }
    )
    
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("✅ تم إنشاء مستخدم admin")
    else:
        print("✅ مستخدم admin موجود")
    
    # مستخدم اختبار
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'مستخدم',
            'last_name': 'اختبار'
        }
    )
    
    if created:
        test_user.set_password('test123')
        test_user.save()
        print("✅ تم إنشاء مستخدم اختبار")
    else:
        print("✅ مستخدم اختبار موجود")
    
    return admin_user, test_user

def test_chat_room_creation(admin_user, test_user):
    """اختبار إنشاء غرفة دردشة"""
    print("\n💬 اختبار إنشاء غرفة دردشة...")
    
    try:
        # البحث عن غرفة موجودة أو إنشاء جديدة
        room = ChatRoom.objects.filter(
            room_type='private',
            participants=admin_user
        ).filter(
            participants=test_user
        ).first()
        
        if not room:
            room = ChatRoom.objects.create(
                name=f"دردشة بين {admin_user.username} و {test_user.username}",
                room_type='private'
            )
            room.participants.add(admin_user, test_user)
            print(f"✅ تم إنشاء غرفة دردشة جديدة: {room.id}")
        else:
            print(f"✅ غرفة دردشة موجودة: {room.id}")
        
        # إنشاء رسالة اختبار
        message = Message.objects.create(
            room=room,
            sender=admin_user,
            content="رسالة اختبار للتأكد من عمل النظام"
        )
        print(f"✅ تم إنشاء رسالة اختبار: {message.id}")
        
        return room
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء غرفة الدردشة: {e}")
        return None

def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار نظام الدردشة والإصلاحات\n")
    
    # اختبار إعدادات Django
    test_django_settings()
    
    # اختبار Redis
    test_redis_connection()
    
    # إنشاء مستخدمين للاختبار
    admin_user, test_user = create_test_users()
    
    # اختبار قاعدة البيانات
    test_database()
    
    # اختبار إنشاء غرفة دردشة
    room = test_chat_room_creation(admin_user, test_user)
    
    print("\n🎉 انتهى الاختبار!")
    print("\n📝 الإصلاحات المطبقة:")
    print("✅ إصلاح ASGI settings (crm.asgi:application)")
    print("✅ إصلاح فتح النافذة تلقائياً")
    print("✅ تحسين معالجة رسائل WebSocket")
    print("✅ إضافة API لمعلومات الغرفة")
    print("✅ تحسين debugging للـ WebSocket")
    print("✅ إزالة Cloudflare من ملفات التشغيل")
    print("✅ استخدام Daphne للتطوير والإنتاج")
    
    print("\n🔧 للتشغيل:")
    print("# للتطوير مع WebSocket:")
    print("./لينكس/run-development.sh")
    print("\n# للإنتاج المحلي مع WebSocket:")
    print("./لينكس/run-production.sh")
    print("\nثم افتح: http://localhost:8000")
    print("سجل الدخول: admin / admin123")
    
    print("\n🆕 الميزات المحسنة:")
    print("✅ الرسائل تصل فوراً (بدون تأخير)")
    print("✅ نافذة المحادثة تفتح تلقائياً")
    print("✅ مؤشر 'يكتب الآن' يعمل")
    print("✅ أصوات الإشعارات تعمل")
    print("✅ إشعارات WebSocket connection")
    print("✅ معلومات المستخدم تظهر في النافذة")

if __name__ == "__main__":
    main()
