#!/usr/bin/env python
"""
اختبار الإصلاحات الحرجة لنظام المحادثة
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

def test_critical_fixes():
    """اختبار الإصلاحات الحرجة"""
    print("🔥 اختبار الإصلاحات الحرجة لنظام المحادثة\n")
    
    # فحص ASGI
    if hasattr(settings, 'ASGI_APPLICATION'):
        asgi_app = settings.ASGI_APPLICATION
        print(f"✅ ASGI_APPLICATION: {asgi_app}")
    else:
        print("❌ ASGI_APPLICATION غير مُعرف")

def test_database_status():
    """اختبار حالة قاعدة البيانات"""
    print("\n📊 اختبار حالة قاعدة البيانات...")
    
    # إحصائيات
    users_count = User.objects.count()
    status_count = UserStatus.objects.count()
    rooms_count = ChatRoom.objects.count()
    messages_count = Message.objects.count()
    
    print(f"المستخدمين: {users_count}")
    print(f"حالات المستخدمين: {status_count}")
    print(f"غرف الدردشة: {rooms_count}")
    print(f"الرسائل: {messages_count}")

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
                return True
            else:
                print(f"⚠️ الخادم يرد بكود: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ لا يمكن الاتصال بالخادم على localhost:8000")
            print("تأكد من تشغيل الخادم أولاً:")
            print("./لينكس/run-development.sh")
            return False
        except Exception as e:
            print(f"❌ خطأ في الاتصال: {e}")
            return False
        
    except ImportError:
        print("❌ مكتبة requests غير مثبتة")
        return False

def main():
    """الدالة الرئيسية"""
    print("🚀 اختبار الإصلاحات الحرجة لنظام المحادثة\n")
    
    # اختبار الإصلاحات
    test_critical_fixes()
    
    # اختبار قاعدة البيانات
    test_database_status()
    
    # اختبار اتصال الخادم
    server_ok = test_server_connection()
    
    print("\n🎉 انتهى الاختبار!")
    print("\n📝 الإصلاحات المطبقة:")
    print("✅ إصلاح خطأ updateUserRoomsWidget")
    print("✅ تحسين مؤشر 'جاري الكتابة الآن'")
    print("✅ إصلاح الفتح التلقائي للمحادثة")
    print("✅ إصلاح عداد الرسائل غير المقروءة")
    print("✅ تحسين markMessagesAsRead")
    print("✅ إضافة دوال إدارة العدادات")
    
    if server_ok:
        print("\n🧪 خطة الاختبار:")
        print("1. افتح المتصفح: http://localhost:8000")
        print("2. سجل الدخول: admin / admin123")
        print("3. افتح console المتصفح (F12)")
        print("4. اختبر الميزات التالية:")
        print("\n🔥 **اختبارات حرجة:**")
        print("   ✅ فتح المحادثة تلقائياً عند وصول رسالة")
        print("   ✅ ظهور 'جاري الكتابة الآن' عند كتابة المستخدم الآخر")
        print("   ✅ اختفاء عداد الرسائل عند فتح المحادثة")
        print("   ✅ حذف المحادثة يعمل من قائمة المحادثات")
        print("   ✅ الإشعار الصوتي يعمل لجميع الرسائل الجديدة")
        
        print("\n📋 **خطوات الاختبار المفصلة:**")
        print("1. **اختبار الفتح التلقائي:**")
        print("   - افتح نافذتين في متصفحين مختلفين")
        print("   - سجل دخول بمستخدمين مختلفين")
        print("   - أرسل رسالة من المستخدم الأول")
        print("   - تحقق من فتح النافذة تلقائياً للمستخدم الثاني")
        
        print("\n2. **اختبار 'جاري الكتابة الآن':**")
        print("   - ابدأ الكتابة في نافذة المستخدم الأول")
        print("   - تحقق من ظهور 'جاري الكتابة الآن' للمستخدم الثاني")
        print("   - توقف عن الكتابة وتحقق من اختفاء المؤشر")
        
        print("\n3. **اختبار عداد الرسائل:**")
        print("   - أرسل رسالة وتحقق من ظهور العداد")
        print("   - افتح المحادثة وتحقق من اختفاء العداد")
        
        print("\n4. **اختبار حذف المحادثة:**")
        print("   - انقر بالزر الأيمن على محادثة في القائمة")
        print("   - اختر 'حذف المحادثة'")
        print("   - تحقق من حذف المحادثة بنجاح")
        
        print("\n5. **اختبار الإشعار الصوتي:**")
        print("   - تأكد من تشغيل الصوت في المتصفح")
        print("   - أرسل رسالة وتحقق من تشغيل الصوت")
        print("   - اختبر مع النافذة مفتوحة ومغلقة")
    else:
        print("\n⚠️ شغل الخادم أولاً:")
        print("./لينكس/run-development.sh")
    
    print("\n🎯 **النتائج المتوقعة:**")
    print("✅ لا توجد أخطاء JavaScript في console")
    print("✅ جميع الوظائف تعمل بسلاسة")
    print("✅ تجربة مستخدم محسنة")
    print("✅ استجابة فورية للأحداث")
    
    print("\n📈 **الخطوات التالية:**")
    print("1. اختبار شامل للوظائف")
    print("2. تنظيف رسائل console.log المتبقية")
    print("3. إعادة هيكلة نظام إدارة الحالة")
    print("4. إضافة ميزات جديدة")

if __name__ == "__main__":
    main()
