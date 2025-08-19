#!/usr/bin/env python
"""
اختبار شامل لنظام الإشعارات
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from notifications.models import Notification, NotificationVisibility
from notifications.signals import create_notification
from notifications.utils import get_user_notification_count
from customers.models import Customer
from orders.models import Order

User = get_user_model()

def test_notification_creation():
    """اختبار إنشاء الإشعارات"""
    print("🧪 اختبار إنشاء الإشعارات...")
    
    user = User.objects.first()
    if not user:
        print("❌ لا يوجد مستخدمين للاختبار")
        return False
    
    # اختبار إنشاء إشعار أساسي
    notification = create_notification(
        title="اختبار إنشاء إشعار",
        message="هذا اختبار لإنشاء إشعار جديد",
        notification_type="customer_created",
        created_by=user,
        priority="normal",
        recipients=[user]
    )
    
    if notification:
        print("✅ تم إنشاء الإشعار بنجاح")
        
        # التحقق من إنشاء سجل الرؤية
        visibility = NotificationVisibility.objects.filter(
            notification=notification,
            user=user
        ).first()
        
        if visibility:
            print("✅ تم إنشاء سجل الرؤية بنجاح")
            return True
        else:
            print("❌ فشل في إنشاء سجل الرؤية")
            return False
    else:
        print("❌ فشل في إنشاء الإشعار")
        return False

def test_notification_permissions():
    """اختبار صلاحيات الإشعارات"""
    print("🔐 اختبار صلاحيات الإشعارات...")
    
    users = User.objects.all()[:2]
    if len(users) < 2:
        print("❌ نحتاج مستخدمين على الأقل للاختبار")
        return False
    
    user1, user2 = users[0], users[1]
    
    # إنشاء إشعار للمستخدم الأول فقط
    notification = create_notification(
        title="إشعار خاص",
        message="هذا إشعار خاص بمستخدم واحد",
        notification_type="order_created",
        created_by=user1,
        priority="normal",
        recipients=[user1]
    )
    
    # التحقق من أن المستخدم الأول يراه
    user1_notifications = Notification.objects.for_user(user1)
    if notification in user1_notifications:
        print("✅ المستخدم الأول يرى الإشعار")
    else:
        print("❌ المستخدم الأول لا يرى الإشعار")
        return False
    
    # التحقق من أن المستخدم الثاني لا يراه
    user2_notifications = Notification.objects.for_user(user2)
    if notification not in user2_notifications:
        print("✅ المستخدم الثاني لا يرى الإشعار (صحيح)")
        return True
    else:
        print("❌ المستخدم الثاني يرى الإشعار (خطأ)")
        return False

def test_notification_read_status():
    """اختبار حالة قراءة الإشعارات"""
    print("👁️ اختبار حالة قراءة الإشعارات...")
    
    user = User.objects.first()
    if not user:
        print("❌ لا يوجد مستخدمين للاختبار")
        return False
    
    # إنشاء إشعار جديد
    notification = create_notification(
        title="اختبار حالة القراءة",
        message="اختبار تحديد الإشعار كمقروء",
        notification_type="inspection_created",
        created_by=user,
        priority="normal",
        recipients=[user]
    )
    
    # التحقق من أنه غير مقروء في البداية
    unread_count_before = get_user_notification_count(user)
    print(f"📊 عدد الإشعارات غير المقروءة قبل القراءة: {unread_count_before}")
    
    # تحديد الإشعار كمقروء
    from notifications.utils import mark_notification_as_read
    success = mark_notification_as_read(notification, user)
    
    if success:
        print("✅ تم تحديد الإشعار كمقروء")
        
        # التحقق من تغيير العداد
        unread_count_after = get_user_notification_count(user)
        print(f"📊 عدد الإشعارات غير المقروءة بعد القراءة: {unread_count_after}")
        
        if unread_count_after < unread_count_before:
            print("✅ تم تحديث العداد بنجاح")
            return True
        else:
            print("❌ لم يتم تحديث العداد")
            return False
    else:
        print("❌ فشل في تحديد الإشعار كمقروء")
        return False

def test_notification_api():
    """اختبار API الإشعارات"""
    print("🌐 اختبار API الإشعارات...")
    
    user = User.objects.first()
    if not user:
        print("❌ لا يوجد مستخدمين للاختبار")
        return False
    
    client = Client()
    
    # تسجيل دخول المستخدم
    client.force_login(user)
    
    # اختبار endpoint عداد الإشعارات
    try:
        response = client.get('/notifications/ajax/count/')
        if response.status_code == 200:
            data = response.json()
            if 'count' in data:
                print(f"✅ API العداد يعمل: {data['count']} إشعار غير مقروء")
            else:
                print("❌ API العداد لا يحتوي على البيانات المطلوبة")
                return False
        else:
            print(f"❌ API العداد فشل: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ خطأ في API العداد: {e}")
        return False
    
    # اختبار endpoint الإشعارات الحديثة
    try:
        response = client.get('/notifications/ajax/recent/')
        if response.status_code == 200:
            data = response.json()
            if 'notifications' in data:
                print(f"✅ API الإشعارات الحديثة يعمل: {len(data['notifications'])} إشعار")
                return True
            else:
                print("❌ API الإشعارات الحديثة لا يحتوي على البيانات المطلوبة")
                return False
        else:
            print(f"❌ API الإشعارات الحديثة فشل: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ خطأ في API الإشعارات الحديثة: {e}")
        return False

def test_notification_signals():
    """اختبار إشارات الإشعارات"""
    print("📡 اختبار إشارات الإشعارات...")
    
    user = User.objects.first()
    if not user:
        print("❌ لا يوجد مستخدمين للاختبار")
        return False
    
    # عدد الإشعارات قبل الاختبار
    notifications_before = Notification.objects.count()
    
    # محاولة إنشاء عميل جديد (يجب أن ينشئ إشعار)
    try:
        from customers.models import Customer, CustomerCategory
        from accounts.models import Branch
        
        # الحصول على فرع أو إنشاء واحد
        branch = Branch.objects.first()
        if not branch:
            branch = Branch.objects.create(
                name="فرع تجريبي",
                code="TEST",
                address="عنوان تجريبي"
            )
        
        # إنشاء عميل جديد
        customer = Customer.objects.create(
            name="عميل تجريبي للإشعارات",
            phone="123456789",
            address="عنوان تجريبي",
            branch=branch,
            created_by=user
        )
        
        # التحقق من إنشاء إشعار
        notifications_after = Notification.objects.count()
        
        if notifications_after > notifications_before:
            print("✅ تم إنشاء إشعار عند إنشاء العميل")
            
            # البحث عن الإشعار المنشأ
            customer_notification = Notification.objects.filter(
                notification_type='customer_created',
                object_id=customer.id
            ).first()
            
            if customer_notification:
                print(f"✅ تم العثور على الإشعار: {customer_notification.title}")
                return True
            else:
                print("❌ لم يتم العثور على إشعار العميل")
                return False
        else:
            print("❌ لم يتم إنشاء إشعار عند إنشاء العميل")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار إشارات الإشعارات: {e}")
        return False

def run_all_tests():
    """تشغيل جميع الاختبارات"""
    print("🚀 بدء اختبار نظام الإشعارات الشامل...\n")
    
    tests = [
        ("إنشاء الإشعارات", test_notification_creation),
        ("صلاحيات الإشعارات", test_notification_permissions),
        ("حالة قراءة الإشعارات", test_notification_read_status),
        ("API الإشعارات", test_notification_api),
        ("إشارات الإشعارات", test_notification_signals),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 اختبار: {test_name}")
        print('='*50)
        
        try:
            if test_func():
                print(f"✅ نجح اختبار: {test_name}")
                passed += 1
            else:
                print(f"❌ فشل اختبار: {test_name}")
                failed += 1
        except Exception as e:
            print(f"💥 خطأ في اختبار {test_name}: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print("📊 نتائج الاختبارات:")
    print(f"✅ نجح: {passed}")
    print(f"❌ فشل: {failed}")
    print(f"📈 معدل النجاح: {(passed/(passed+failed)*100):.1f}%")
    print('='*50)
    
    if failed == 0:
        print("🎉 جميع الاختبارات نجحت! نظام الإشعارات يعمل بشكل مثالي.")
    else:
        print("⚠️ بعض الاختبارات فشلت. يرجى مراجعة الأخطاء أعلاه.")

if __name__ == "__main__":
    run_all_tests()
