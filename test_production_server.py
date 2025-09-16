#!/usr/bin/env python3
"""
اختبار شامل لخادم الإنتاج والتأكد من عمل جميع الوظائف
"""

import os
import django
import requests
import time
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

def test_server_response():
    """اختبار استجابة الخادم"""
    print("🌐 اختبار استجابة الخادم...")
    
    try:
        response = requests.get('http://localhost:8000', timeout=10)
        if response.status_code == 200:
            print("✅ الخادم يستجيب بشكل طبيعي")
            return True
        else:
            print(f"❌ الخادم يستجيب بكود خطأ: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ لا يمكن الاتصال بالخادم")
        return False
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return False

def test_google_drive_upload():
    """اختبار رفع الملفات إلى Google Drive"""
    print("\n📤 اختبار رفع الملفات إلى Google Drive...")
    
    try:
        from orders.tasks import upload_inspection_to_drive_async
        from inspections.models import Inspection
        
        # البحث عن معاينة للاختبار
        inspection = Inspection.objects.filter(
            google_drive_file_id__isnull=True
        ).first()
        
        if inspection:
            print(f"📋 اختبار رفع المعاينة {inspection.id}...")
            
            # محاولة رفع الملف
            result = upload_inspection_to_drive_async.delay(inspection.id)
            
            # انتظار النتيجة لمدة 30 ثانية
            try:
                task_result = result.get(timeout=30)
                if task_result.get('success'):
                    print("✅ تم رفع الملف بنجاح إلى Google Drive")
                    return True
                else:
                    print(f"❌ فشل في رفع الملف: {task_result.get('error')}")
                    return False
            except Exception as e:
                print(f"❌ خطأ في مهمة الرفع: {e}")
                return False
        else:
            print("⚠️ لا توجد معاينات للاختبار")
            return True
            
    except Exception as e:
        print(f"❌ خطأ في اختبار Google Drive: {e}")
        return False

def test_celery_tasks():
    """اختبار مهام Celery"""
    print("\n⚙️ اختبار مهام Celery...")
    
    try:
        from orders.tasks import calculate_order_totals_async
        from orders.models import Order
        
        # البحث عن طلب للاختبار
        order = Order.objects.first()
        
        if order:
            print(f"📊 اختبار حساب إجماليات الطلب {order.order_number}...")
            
            # تشغيل مهمة حساب الإجماليات
            result = calculate_order_totals_async.delay(order.id)
            
            # انتظار النتيجة لمدة 10 ثوان
            try:
                task_result = result.get(timeout=10)
                if task_result.get('success'):
                    print("✅ تم حساب الإجماليات بنجاح")
                    return True
                else:
                    print(f"❌ فشل في حساب الإجماليات: {task_result.get('error')}")
                    return False
            except Exception as e:
                print(f"❌ خطأ في مهمة الحساب: {e}")
                return False
        else:
            print("⚠️ لا توجد طلبات للاختبار")
            return True
            
    except Exception as e:
        print(f"❌ خطأ في اختبار Celery: {e}")
        return False

def test_database_connection():
    """اختبار اتصال قاعدة البيانات"""
    print("\n🗄️ اختبار اتصال قاعدة البيانات...")
    
    try:
        from django.db import connection
        
        # اختبار الاتصال
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
        if result and result[0] == 1:
            print("✅ اتصال قاعدة البيانات يعمل بشكل طبيعي")
            return True
        else:
            print("❌ مشكلة في اتصال قاعدة البيانات")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اتصال قاعدة البيانات: {e}")
        return False

def test_google_drive_config():
    """اختبار إعدادات Google Drive"""
    print("\n⚙️ اختبار إعدادات Google Drive...")
    
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        
        config = GoogleDriveConfig.get_active_config()
        if config:
            print(f"✅ الإعدادات النشطة:")
            print(f"   📁 مجلد المعاينات: {config.inspections_folder_id}")
            print(f"   📄 مجلد العقود: {config.contracts_folder_id}")
            print(f"   ✅ نشط: {config.is_active}")
            return True
        else:
            print("❌ لا توجد إعدادات Google Drive نشطة")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في فحص إعدادات Google Drive: {e}")
        return False

def test_redis_connection():
    """اختبار اتصال Redis"""
    print("\n🔴 اختبار اتصال Redis...")
    
    try:
        import redis
        
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        
        print("✅ اتصال Redis يعمل بشكل طبيعي")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اتصال Redis: {e}")
        return False

def test_file_upload_endpoints():
    """اختبار نقاط رفع الملفات"""
    print("\n📁 اختبار نقاط رفع الملفات...")
    
    try:
        # اختبار الوصول لصفحة الإعدادات المركزية
        response = requests.get('http://localhost:8000/odoo-db-manager/google-drive/settings/', timeout=10)
        
        if response.status_code in [200, 302]:  # 302 للتوجيه لتسجيل الدخول
            print("✅ صفحة الإعدادات المركزية متاحة")
            return True
        else:
            print(f"❌ مشكلة في الوصول لصفحة الإعدادات: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في اختبار نقاط الرفع: {e}")
        return False

def generate_report(results):
    """إنشاء تقرير شامل"""
    print("\n" + "="*60)
    print("📋 تقرير اختبار خادم الإنتاج")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    failed_tests = total_tests - passed_tests
    
    print(f"📊 إجمالي الاختبارات: {total_tests}")
    print(f"✅ نجح: {passed_tests}")
    print(f"❌ فشل: {failed_tests}")
    print(f"📈 نسبة النجاح: {(passed_tests/total_tests*100):.1f}%")
    
    print(f"\n📝 تفاصيل الاختبارات:")
    for test_name, result in results.items():
        status = "✅ نجح" if result else "❌ فشل"
        print(f"   {test_name}: {status}")
    
    if failed_tests == 0:
        print(f"\n🎉 جميع الاختبارات نجحت! النظام جاهز للعمل.")
    else:
        print(f"\n⚠️ يوجد {failed_tests} اختبار فاشل. يرجى مراجعة الأخطاء أعلاه.")
    
    print("="*60)

def main():
    """الدالة الرئيسية"""
    print("🧪 بدء اختبار شامل لخادم الإنتاج")
    print("="*60)
    
    results = {}
    
    # تشغيل جميع الاختبارات
    results["استجابة الخادم"] = test_server_response()
    results["اتصال قاعدة البيانات"] = test_database_connection()
    results["اتصال Redis"] = test_redis_connection()
    results["إعدادات Google Drive"] = test_google_drive_config()
    results["نقاط رفع الملفات"] = test_file_upload_endpoints()
    results["مهام Celery"] = test_celery_tasks()
    results["رفع Google Drive"] = test_google_drive_upload()
    
    # إنشاء التقرير
    generate_report(results)

if __name__ == "__main__":
    main()
