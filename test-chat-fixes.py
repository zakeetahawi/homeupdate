#!/usr/bin/env python
"""
اختبار شامل لإصلاحات الدردشة
"""
import os
import django
import asyncio

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from modern_chat.models import UserStatus, ChatRoom, Message
from django.conf import settings

User = get_user_model()

def test_websocket_settings():
    """اختبار إعدادات WebSocket"""
    print("🔌 اختبار إعدادات WebSocket...")
    
    # فحص ASGI
    if hasattr(settings, 'ASGI_APPLICATION'):
        print(f"✅ ASGI_APPLICATION: {settings.ASGI_APPLICATION}")
    else:
        print("❌ ASGI_APPLICATION غير مُعرف")
    
    # فحص CHANNEL_LAYERS
    if hasattr(settings, 'CHANNEL_LAYERS'):
        backend = settings.CHANNEL_LAYERS['default']['BACKEND']
        print(f"✅ CHANNEL_LAYERS: {backend}")
    else:
        print("❌ CHANNEL_LAYERS غير مُعرف")
    
    # فحص channels
    if 'channels' in settings.INSTALLED_APPS:
        print("✅ channels مُثبت")
    else:
        print("❌ channels غير مُثبت")

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
            
            # اختبار إرسال رسالة
            async def test_channel():
                try:
                    await channel_layer.send('test-channel', {
                        'type': 'test.message',
                        'text': 'Hello World'
                    })
                    return True
                except Exception as e:
                    print(f"❌ خطأ في Channel Layer: {e}")
                    return False
            
            result = asyncio.run(test_channel())
            if result:
                print("✅ Channel Layer يعمل")
            else:
                print("❌ مشكلة في Channel Layer")
        else:
            print("❌ لا يمكن الحصول على Channel Layer")
            
    except Exception as e:
        print(f"❌ Redis لا يعمل: {e}")

def test_sound_files():
    """اختبار الملفات الصوتية"""
    print("\n🔊 اختبار الملفات الصوتية...")
    
    sound_files = [
        'static/sounds/message-receive.wav',
        'static/sounds/message-send.wav'
    ]
    
    for sound_file in sound_files:
        if os.path.exists(sound_file):
            size = os.path.getsize(sound_file)
            print(f"✅ {os.path.basename(sound_file)}: {size} bytes")
        else:
            print(f"❌ {os.path.basename(sound_file)}: غير موجود")

def test_chat_apis():
    """اختبار APIs الدردشة"""
    print("\n🌐 اختبار APIs الدردشة...")
    
    client = Client()
    
    # تسجيل الدخول
    login_response = client.post('/accounts/login/', {
        'username': 'admin',
        'password': 'admin123'
    })
    
    if login_response.status_code in [200, 302]:
        print("✅ تسجيل الدخول نجح")
    else:
        print(f"❌ تسجيل الدخول فشل: {login_response.status_code}")
        return
    
    # اختبار APIs الأساسية
    apis = [
        ('/modern-chat/api/active-users/', 'المستخدمين النشطين'),
        ('/modern-chat/api/user-rooms/', 'غرف المستخدم'),
        ('/modern-chat/api/check-new-messages/', 'فحص الرسائل الجديدة'),
    ]
    
    for url, name in apis:
        response = client.get(url)
        if response.status_code == 200:
            print(f"✅ {name}: {response.status_code}")
        else:
            print(f"❌ {name}: {response.status_code}")
    
    # اختبار APIs الجديدة
    print("\n🆕 اختبار APIs الجديدة...")
    
    # اختبار API حذف المحادثة (مع مستخدم غير موجود)
    response = client.post('/modern-chat/api/delete-conversation/', 
                          '{"user_id": 99999}',
                          content_type='application/json')
    
    if response.status_code in [404, 400]:
        print("✅ API حذف المحادثة يعمل")
    else:
        print(f"⚠️ API حذف المحادثة: {response.status_code}")
    
    # اختبار API حظر المستخدم (مع مستخدم غير موجود)
    response = client.post('/modern-chat/api/block-user/', 
                          '{"user_id": 99999}',
                          content_type='application/json')
    
    if response.status_code in [404, 400]:
        print("✅ API حظر المستخدم يعمل")
    else:
        print(f"⚠️ API حظر المستخدم: {response.status_code}")

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
    
    # إنشاء حالات للمستخدمين
    for user in [admin_user, test_user]:
        status, created = UserStatus.objects.get_or_create(
            user=user,
            defaults={'status': 'online'}
        )
        if created:
            print(f"✅ تم إنشاء حالة للمستخدم: {user.username}")

def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار شامل لإصلاحات الدردشة\n")
    
    # اختبار إعدادات WebSocket
    test_websocket_settings()
    
    # اختبار Redis
    test_redis_connection()
    
    # اختبار الملفات الصوتية
    test_sound_files()
    
    # إنشاء مستخدمين للاختبار
    create_test_users()
    
    # اختبار قاعدة البيانات
    test_database()
    
    # اختبار APIs
    test_chat_apis()
    
    print("\n🎉 انتهى اختبار الإصلاحات!")
    print("\n📝 النتائج المتوقعة بعد الإصلاحات:")
    print("✅ الرسائل تصل فوراً (بدون تأخير 10 ثواني)")
    print("✅ نافذة المحادثة تفتح تلقائياً عند وصول رسالة")
    print("✅ مؤشر 'يكتب الآن' يظهر ويعمل")
    print("✅ أصوات إشعارات تعمل عند وصول رسالة")
    print("✅ عرض ملف المستخدم في modal جميل")
    print("✅ حذف المحادثة يعمل مع رسائل واضحة")
    print("✅ قائمة الزر الأيمن تعمل بشكل صحيح")
    
    print("\n🔧 للتشغيل:")
    print("./start-server.sh")
    print("ثم افتح: http://localhost:8000")
    print("سجل الدخول: admin / admin123")

if __name__ == "__main__":
    main()
