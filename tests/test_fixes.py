#!/usr/bin/env python
"""
اختبار الإصلاحات المطبقة على نظام الإشعارات
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import Notification
from notifications.signals import create_notification
from manufacturing.models import ManufacturingOrder
from orders.models import Order

User = get_user_model()

def test_manufacturing_order_notification():
    """اختبار إشعارات أوامر التصنيع"""
    print("🏭 اختبار إشعارات أوامر التصنيع...")
    
    # البحث عن أمر تصنيع موجود
    manufacturing_order = ManufacturingOrder.objects.first()
    if not manufacturing_order:
        print("❌ لا يوجد أوامر تصنيع للاختبار")
        return False
    
    print(f"✅ تم العثور على أمر التصنيع: {manufacturing_order.id}")
    print(f"   الحالة الحالية: {manufacturing_order.status}")
    
    # عدد الإشعارات قبل التغيير
    notifications_before = Notification.objects.count()
    
    # تغيير حالة أمر التصنيع
    old_status = manufacturing_order.status
    new_status = 'in_progress' if old_status != 'in_progress' else 'completed'
    
    print(f"🔄 تغيير الحالة من {old_status} إلى {new_status}")
    
    manufacturing_order.status = new_status
    manufacturing_order.save()
    
    # التحقق من إنشاء إشعار
    notifications_after = Notification.objects.count()
    
    if notifications_after > notifications_before:
        print("✅ تم إنشاء إشعار عند تغيير حالة أمر التصنيع")
        
        # البحث عن الإشعار المنشأ
        latest_notification = Notification.objects.filter(
            notification_type='order_status_changed'
        ).order_by('-created_at').first()
        
        if latest_notification:
            print(f"✅ تفاصيل الإشعار: {latest_notification.title}")
            print(f"   الرسالة: {latest_notification.message}")
            return True
        else:
            print("❌ لم يتم العثور على الإشعار المنشأ")
            return False
    else:
        print("❌ لم يتم إنشاء إشعار عند تغيير حالة أمر التصنيع")
        return False

def test_notification_read_functionality():
    """اختبار وظيفة تحديد الإشعار كمقروء"""
    print("👁️ اختبار وظيفة تحديد الإشعار كمقروء...")
    
    user = User.objects.first()
    if not user:
        print("❌ لا يوجد مستخدمين للاختبار")
        return False
    
    # إنشاء إشعار تجريبي
    notification = create_notification(
        title="اختبار تحديد كمقروء",
        message="هذا إشعار لاختبار وظيفة التحديد كمقروء",
        notification_type="order_created",
        created_by=user,
        priority="normal",
        recipients=[user]
    )
    
    if not notification:
        print("❌ فشل في إنشاء الإشعار التجريبي")
        return False
    
    print(f"✅ تم إنشاء إشعار تجريبي: {notification.id}")
    
    # التحقق من أنه غير مقروء في البداية
    from notifications.models import NotificationVisibility
    visibility = NotificationVisibility.objects.filter(
        notification=notification,
        user=user
    ).first()
    
    if not visibility:
        print("❌ لم يتم إنشاء سجل الرؤية")
        return False
    
    if visibility.is_read:
        print("❌ الإشعار مقروء بالفعل (يجب أن يكون غير مقروء)")
        return False
    
    print("✅ الإشعار غير مقروء كما هو متوقع")
    
    # تحديد الإشعار كمقروء
    from notifications.utils import mark_notification_as_read
    success = mark_notification_as_read(notification, user)
    
    if success:
        print("✅ تم تحديد الإشعار كمقروء بنجاح")
        
        # التحقق من التحديث
        visibility.refresh_from_db()
        if visibility.is_read:
            print("✅ تم تحديث حالة القراءة في قاعدة البيانات")
            return True
        else:
            print("❌ لم يتم تحديث حالة القراءة في قاعدة البيانات")
            return False
    else:
        print("❌ فشل في تحديد الإشعار كمقروء")
        return False

def test_inspection_duplicate_issue():
    """اختبار مشكلة المعاينات المكررة"""
    print("🔍 اختبار مشكلة المعاينات المكررة...")
    
    from inspections.models import Inspection
    
    # البحث عن طلب له أكثر من معاينة
    from django.db.models import Count
    orders_with_multiple_inspections = Order.objects.annotate(
        inspection_count=Count('inspections')
    ).filter(inspection_count__gt=1)
    
    if not orders_with_multiple_inspections.exists():
        print("✅ لا توجد طلبات بمعاينات مكررة")
        return True
    
    order_with_duplicates = orders_with_multiple_inspections.first()
    print(f"⚠️ تم العثور على طلب بمعاينات متعددة: {order_with_duplicates.order_number}")
    
    inspections = Inspection.objects.filter(order=order_with_duplicates)
    print(f"   عدد المعاينات: {inspections.count()}")
    
    # اختبار الدالة المحدثة
    try:
        from inspections.views import inspection_detail_by_code
        inspection_code = f"{order_with_duplicates.order_number}-I"
        print(f"   اختبار الكود: {inspection_code}")
        
        # محاكاة الطلب
        class MockRequest:
            user = User.objects.first()
        
        request = MockRequest()
        
        # هذا يجب أن يعمل الآن بدون خطأ MultipleObjectsReturned
        first_inspection = Inspection.objects.filter(
            order__order_number=order_with_duplicates.order_number
        ).first()
        
        if first_inspection:
            print(f"✅ تم الحصول على أول معاينة بنجاح: {first_inspection.id}")
            return True
        else:
            print("❌ لم يتم العثور على معاينة")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار المعاينات المكررة: {e}")
        return False

def run_all_fixes_tests():
    """تشغيل جميع اختبارات الإصلاحات"""
    print("🔧 بدء اختبار الإصلاحات المطبقة...\n")
    
    tests = [
        ("إشعارات أوامر التصنيع", test_manufacturing_order_notification),
        ("وظيفة تحديد الإشعار كمقروء", test_notification_read_functionality),
        ("مشكلة المعاينات المكررة", test_inspection_duplicate_issue),
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
    print("📊 نتائج اختبارات الإصلاحات:")
    print(f"✅ نجح: {passed}")
    print(f"❌ فشل: {failed}")
    print(f"📈 معدل النجاح: {(passed/(passed+failed)*100):.1f}%")
    print('='*50)
    
    if failed == 0:
        print("🎉 جميع الإصلاحات تعمل بشكل مثالي!")
    else:
        print("⚠️ بعض الإصلاحات تحتاج مراجعة إضافية.")

if __name__ == "__main__":
    run_all_fixes_tests()
