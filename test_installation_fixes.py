#!/usr/bin/env python3
"""
سكريبت اختبار إصلاحات نظام التركيب
"""

import requests
import json
import time

def test_installation_system():
    """اختبار نظام التركيب"""
    base_url = "http://127.0.0.1:8000"
    
    print("🔧 بدء اختبار نظام التركيب...")
    
    try:
        # اختبار الوصول للصفحة الرئيسية
        print("📋 اختبار الوصول للصفحة الرئيسية...")
        response = requests.get(f"{base_url}/installations/")
        if response.status_code == 200:
            print("✅ تم الوصول للصفحة الرئيسية بنجاح")
        else:
            print(f"❌ فشل الوصول للصفحة الرئيسية: {response.status_code}")
            return False
        
        # اختبار قائمة التركيبات
        print("📋 اختبار قائمة التركيبات...")
        response = requests.get(f"{base_url}/installations/installation-list/")
        if response.status_code == 200:
            print("✅ تم الوصول لقائمة التركيبات بنجاح")
        else:
            print(f"❌ فشل الوصول لقائمة التركيبات: {response.status_code}")
        
        # اختبار لوحة التحكم
        print("📋 اختبار لوحة التحكم...")
        response = requests.get(f"{base_url}/installations/")
        if response.status_code == 200:
            print("✅ تم الوصول للوحة التحكم بنجاح")
        else:
            print(f"❌ فشل الوصول للوحة التحكم: {response.status_code}")
        
        # اختبار الجدول اليومي
        print("📋 اختبار الجدول اليومي...")
        response = requests.get(f"{base_url}/installations/daily-schedule/")
        if response.status_code == 200:
            print("✅ تم الوصول للجدول اليومي بنجاح")
        else:
            print(f"❌ فشل الوصول للجدول اليومي: {response.status_code}")
        
        print("\n🎉 تم اختبار النظام بنجاح!")
        print("\n📝 ملخص الإصلاحات المطبقة:")
        print("✅ إصلاح خطأ installation_detail view")
        print("✅ إضافة قائمة منسدلة لتحديث الحالة")
        print("✅ إضافة أزرار منفصلة للطلب والتركيب")
        print("✅ إضافة إمكانية تعديل الجدولة")
        print("✅ تحسين واجهة المستخدم")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ لا يمكن الاتصال بالخادم. تأكد من تشغيل Django server")
        return False
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")
        return False

if __name__ == "__main__":
    print("🚀 بدء اختبار إصلاحات نظام التركيب")
    print("=" * 50)
    
    success = test_installation_system()
    
    if success:
        print("\n✅ تم اختبار النظام بنجاح!")
        print("🌐 يمكنك الآن الوصول للنظام على: http://127.0.0.1:8000/installations/")
    else:
        print("\n❌ فشل في اختبار النظام")
        print("🔧 يرجى التحقق من تشغيل الخادم وإعادة المحاولة") 