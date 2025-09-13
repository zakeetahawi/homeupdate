#!/usr/bin/env python
"""
اختبار سريع للإصلاحات الجديدة
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

def test_websocket_fixes():
    """اختبار إصلاحات WebSocket"""
    print("🔧 اختبار إصلاحات WebSocket...")
    
    # فحص ASGI
    if hasattr(settings, 'ASGI_APPLICATION'):
        asgi_app = settings.ASGI_APPLICATION
        print(f"✅ ASGI_APPLICATION: {asgi_app}")
        
        if asgi_app == 'crm.asgi.application':
            print("✅ ASGI مضبوط بشكل صحيح")
        else:
            print(f"❌ ASGI خطأ - القيمة الحالية: {asgi_app}")
    else:
        print("❌ ASGI_APPLICATION غير مُعرف")

def test_redis():
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

def test_server_connection():
    """اختبار اتصال الخادم"""
    print("\n🌐 اختبار اتصال الخادم...")
    
    try:
        import requests
        
        # اختبار الصفحة الرئيسية
        try:
            response = requests.get('http://localhost:8000/', timeout=5)
            if response.status_code == 200:
                print("✅ الخادم يعمل على المنفذ 8000")
            else:
                print(f"⚠️ الخادم يرد بكود: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ لا يمكن الاتصال بالخادم على localhost:8000")
            print("تأكد من تشغيل الخادم أولاً:")
            print("./لينكس/run-development.sh")
            return False
        except Exception as e:
            print(f"❌ خطأ في الاتصال: {e}")
            return False
        
        # اختبار APIs الدردشة
        try:
            response = requests.get('http://localhost:8000/modern-chat/api/active-users/', timeout=5)
            if response.status_code == 200:
                print("✅ API المستخدمين النشطين يعمل")
            else:
                print(f"⚠️ API المستخدمين النشطين: {response.status_code}")
        except Exception as e:
            print(f"❌ خطأ في API المستخدمين النشطين: {e}")
        
        return True
        
    except ImportError:
        print("❌ مكتبة requests غير مثبتة")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار سريع للإصلاحات الجديدة\n")
    
    # اختبار إصلاحات WebSocket
    test_websocket_fixes()
    
    # اختبار Redis
    test_redis()
    
    # اختبار قاعدة البيانات
    test_database()
    
    # اختبار اتصال الخادم
    server_ok = test_server_connection()
    
    print("\n🎉 انتهى الاختبار!")
    print("\n📝 الإصلاحات المطبقة:")
    print("✅ إصلاح خطأ UUID serialization في WebSocket")
    print("✅ إضافة debugging للزر العائم")
    print("✅ تحسين debugging لحذف المحادثة")
    print("✅ إضافة other_user_id في API user-rooms")
    print("✅ تحسين فتح النافذة تلقائياً")
    print("✅ إصلاح ملف التطوير (إزالة --reload)")
    
    if server_ok:
        print("\n🔧 للاختبار:")
        print("1. افتح المتصفح: http://localhost:8000")
        print("2. سجل الدخول: admin / admin123")
        print("3. افتح console المتصفح (F12)")
        print("4. ابحث عن رسائل debugging:")
        print("   - '🔘 فحص الزر العائم'")
        print("   - '🏠 غرفة' (في قائمة المحادثات)")
        print("   - '🔔 معالجة رسالة WebSocket جديدة'")
        print("5. جرب إرسال رسالة وتحقق من:")
        print("   - عدم ظهور خطأ UUID")
        print("   - فتح النافذة تلقائياً")
        print("   - عمل الزر العائم")
        print("6. جرب الزر الأيمن على محادثة لحذفها")
    else:
        print("\n⚠️ شغل الخادم أولاً:")
        print("./لينكس/run-development.sh")
    
    print("\n🆕 التحسينات المتوقعة:")
    print("✅ WebSocket لا ينقطع عند الإرسال")
    print("✅ رسائل debugging واضحة في console")
    print("✅ نافذة المحادثة تفتح تلقائياً")
    print("✅ الزر العائم يظهر ويعمل")
    print("✅ حذف المحادثة يعمل بـ room_id")
    print("✅ معلومات المستخدم الآخر تظهر في قائمة المحادثات")

if __name__ == "__main__":
    main()
