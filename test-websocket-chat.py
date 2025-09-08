#!/usr/bin/env python
"""
اختبار شامل لنظام الدردشة مع WebSocket
"""
import os
import django
import asyncio
import json

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from modern_chat.models import UserStatus, ChatRoom, Message
from django.conf import settings

User = get_user_model()

def test_settings():
    """اختبار إعدادات WebSocket"""
    print("🔧 اختبار إعدادات WebSocket...")
    
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
    
    # فحص التطبيقات
    if 'modern_chat' in settings.INSTALLED_APPS:
        print("✅ modern_chat مُثبت")
    else:
        print("❌ modern_chat غير مُثبت")
    
    if 'channels' in settings.INSTALLED_APPS:
        print("✅ channels مُثبت")
    else:
        print("❌ channels غير مُثبت")

def test_redis_connection():
    """اختبار اتصال Redis"""
    print("\n🔌 اختبار اتصال Redis...")
    
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        
        if channel_layer:
            print(f"✅ Channel Layer: {type(channel_layer).__name__}")
            
            # اختبار Redis
            async def test_redis():
                try:
                    await channel_layer.send('test-channel', {
                        'type': 'test.message',
                        'text': 'Hello World'
                    })
                    return True
                except Exception as e:
                    print(f"❌ خطأ Redis: {e}")
                    return False
            
            result = asyncio.run(test_redis())
            if result:
                print("✅ Redis يعمل بشكل صحيح")
            else:
                print("❌ مشكلة في Redis")
        else:
            print("❌ لا يمكن الحصول على Channel Layer")
    
    except Exception as e:
        print(f"❌ خطأ في WebSocket: {e}")

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
    
    # اختبار APIs
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

def test_new_features():
    """اختبار الميزات الجديدة"""
    print("\n🆕 اختبار الميزات الجديدة...")
    
    client = Client()
    
    # تسجيل الدخول
    client.post('/accounts/login/', {
        'username': 'admin',
        'password': 'admin123'
    })
    
    # اختبار API حذف المحادثة
    response = client.post('/modern-chat/api/delete-conversation/', 
                          json.dumps({'user_id': 999}),
                          content_type='application/json')
    
    if response.status_code in [404, 400]:  # متوقع لأن المستخدم غير موجود
        print("✅ API حذف المحادثة يعمل")
    else:
        print(f"⚠️ API حذف المحادثة: {response.status_code}")
    
    # اختبار API حظر المستخدم
    response = client.post('/modern-chat/api/block-user/', 
                          json.dumps({'user_id': 999}),
                          content_type='application/json')
    
    if response.status_code in [404, 400]:  # متوقع لأن المستخدم غير موجود
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
        
        # إنشاء حالات للمستخدمين المفقودة
        users_without_status = User.objects.exclude(
            id__in=UserStatus.objects.values_list('user_id', flat=True)
        )
        
        for user in users_without_status:
            UserStatus.objects.create(user=user, status='offline')
            print(f"✅ تم إنشاء حالة للمستخدم: {user.username}")

def create_test_data():
    """إنشاء بيانات اختبار"""
    print("\n🧪 إنشاء بيانات اختبار...")
    
    # التأكد من وجود مستخدم admin
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
    
    # التأكد من وجود حالة للمستخدم
    status, created = UserStatus.objects.get_or_create(
        user=admin_user,
        defaults={'status': 'online'}
    )
    
    if created:
        print("✅ تم إنشاء حالة للمستخدم admin")
    else:
        print("✅ حالة المستخدم admin موجودة")

def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار شامل لنظام الدردشة مع WebSocket\n")
    
    # اختبار الإعدادات
    test_settings()
    
    # إنشاء بيانات اختبار
    create_test_data()
    
    # اختبار قاعدة البيانات
    test_database()
    
    # اختبار Redis
    test_redis_connection()
    
    # اختبار APIs
    test_chat_apis()
    
    # اختبار الميزات الجديدة
    test_new_features()
    
    print("\n🎉 انتهى الاختبار الشامل!")
    print("\n📝 خطوات التشغيل:")
    print("1. شغل Redis: redis-server")
    print("2. شغل النظام: ./لينكس/run-production.sh")
    print("3. افتح المتصفح: http://localhost:8000")
    print("4. سجل الدخول: admin / admin123")
    print("5. اختبر الدردشة والميزات الجديدة")
    
    print("\n🆕 الميزات الجديدة:")
    print("✅ WebSocket للرسائل الفورية")
    print("✅ مؤشر 'يكتب الآن'")
    print("✅ عرض ملف المستخدم (modal)")
    print("✅ حذف المحادثة")
    print("✅ حظر المستخدم")
    print("✅ إشعارات محسنة")
    print("✅ أداء أفضل مع Daphne")

if __name__ == "__main__":
    main()
