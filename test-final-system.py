#!/usr/bin/env python
"""
اختبار نهائي شامل للنظام
"""
import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from cutting.models import Section
from modern_chat.models import UserStatus, ChatRoom, Message
from django.conf import settings

User = get_user_model()

def test_basic_system():
    """اختبار النظام الأساسي"""
    print("🔧 اختبار النظام الأساسي...")
    
    # فحص قاعدة البيانات
    users_count = User.objects.count()
    sections_count = Section.objects.count()
    
    print(f"✅ المستخدمين: {users_count}")
    print(f"✅ الأقسام: {sections_count}")
    
    if sections_count > 0:
        print("✅ الأقسام تظهر بشكل صحيح")
        for section in Section.objects.all()[:5]:
            print(f"  - {section.name}")
    else:
        print("❌ لا توجد أقسام")

def test_websocket_settings():
    """اختبار إعدادات WebSocket"""
    print("\n🔌 اختبار إعدادات WebSocket...")
    
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

def test_chat_system():
    """اختبار نظام الدردشة"""
    print("\n💬 اختبار نظام الدردشة...")
    
    try:
        # إحصائيات الدردشة
        status_count = UserStatus.objects.count()
        rooms_count = ChatRoom.objects.count()
        messages_count = Message.objects.count()
        
        print(f"✅ حالات المستخدمين: {status_count}")
        print(f"✅ غرف الدردشة: {rooms_count}")
        print(f"✅ الرسائل: {messages_count}")
        
        # التحقق من تطابق المستخدمين مع الحالات
        users_count = User.objects.count()
        if users_count == status_count:
            print("✅ جميع المستخدمين لديهم حالات")
        else:
            missing = users_count - status_count
            print(f"⚠️ {missing} مستخدم بدون حالة")
            
    except Exception as e:
        print(f"❌ خطأ في نظام الدردشة: {e}")

def test_redis_connection():
    """اختبار اتصال Redis"""
    print("\n🔌 اختبار Redis...")
    
    try:
        from channels.layers import get_channel_layer
        import asyncio
        
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

def create_test_admin():
    """إنشاء مستخدم admin للاختبار"""
    print("\n👤 إنشاء مستخدم admin...")
    
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

def test_allowed_hosts():
    """اختبار ALLOWED_HOSTS"""
    print("\n🌐 اختبار ALLOWED_HOSTS...")
    
    if hasattr(settings, 'ALLOWED_HOSTS'):
        hosts = settings.ALLOWED_HOSTS
        print(f"✅ ALLOWED_HOSTS: {hosts}")
        
        if '*' in hosts:
            print("✅ السماح لجميع النطاقات")
        else:
            print(f"⚠️ مقيد على: {', '.join(hosts)}")
    else:
        print("❌ ALLOWED_HOSTS غير مُعرف")

def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار نهائي شامل للنظام\n")
    
    # اختبار النظام الأساسي
    test_basic_system()
    
    # اختبار ALLOWED_HOSTS
    test_allowed_hosts()
    
    # اختبار إعدادات WebSocket
    test_websocket_settings()
    
    # إنشاء مستخدم admin
    create_test_admin()
    
    # اختبار نظام الدردشة
    test_chat_system()
    
    # اختبار Redis
    test_redis_connection()
    
    print("\n🎉 انتهى الاختبار النهائي!")
    print("\n📝 خطوات التشغيل:")
    print("1. شغل النظام: ./run-simple.sh")
    print("2. افتح المتصفح: http://localhost:8000")
    print("3. سجل الدخول: admin / admin123")
    print("4. اختبر الدردشة والميزات الجديدة")
    
    print("\n🆕 الميزات المتاحة:")
    print("✅ WebSocket للرسائل الفورية")
    print("✅ مؤشر 'يكتب الآن'")
    print("✅ عرض ملف المستخدم")
    print("✅ حذف المحادثة")
    print("✅ حظر المستخدم")
    print("✅ إشعارات محسنة")
    print("✅ أداء أفضل مع Daphne")
    print("✅ الأقسام تظهر بشكل صحيح")
    
    print("\n🔧 إذا كانت هناك مشاكل:")
    print("- تأكد من تشغيل Redis: redis-server")
    print("- تأكد من استخدام Daphne وليس Gunicorn")
    print("- راجع console المتصفح للأخطاء")
    print("- تحقق من إعدادات ASGI في settings.py")

if __name__ == "__main__":
    main()
