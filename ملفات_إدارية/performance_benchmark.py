#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🚀 أداة قياس الأداء - Performance Benchmark
قياس سرعة التطبيق قبل وبعد التحسينات
"""

import os
import sys
import time
import statistics
from pathlib import Path

# إضافة المشروع للـ path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

import django
django.setup()


def benchmark_database():
    """قياس أداء قاعدة البيانات"""
    from django.db import connection, reset_queries
    from django.conf import settings
    
    print("\n📊 قياس أداء قاعدة البيانات")
    print("-" * 50)
    
    # تفعيل تتبع الاستعلامات
    settings.DEBUG = True
    
    times = []
    
    # اختبار 1: استعلام بسيط
    for _ in range(10):
        reset_queries()
        start = time.time()
        
        from customers.models import Customer
        list(Customer.objects.all()[:100])
        
        times.append((time.time() - start) * 1000)
    
    avg_time = statistics.mean(times)
    print(f"  ✅ استعلام العملاء (100): {avg_time:.2f}ms متوسط")
    
    # اختبار 2: استعلام مع select_related
    times = []
    for _ in range(10):
        reset_queries()
        start = time.time()
        
        from orders.models import Order
        list(Order.objects.select_related('customer', 'branch').all()[:100])
        
        times.append((time.time() - start) * 1000)
    
    avg_time = statistics.mean(times)
    print(f"  ✅ استعلام الطلبات مع العلاقات (100): {avg_time:.2f}ms متوسط")
    
    # اختبار 3: عدّ السجلات
    times = []
    for _ in range(10):
        start = time.time()
        
        Customer.objects.count()
        Order.objects.count()
        
        times.append((time.time() - start) * 1000)
    
    avg_time = statistics.mean(times)
    print(f"  ✅ عدّ السجلات: {avg_time:.2f}ms متوسط")
    
    return avg_time


def benchmark_cache():
    """قياس أداء Cache"""
    from django.core.cache import cache
    
    print("\n📊 قياس أداء Cache (Redis)")
    print("-" * 50)
    
    # اختبار الكتابة
    times = []
    for i in range(100):
        start = time.time()
        cache.set(f'benchmark_key_{i}', {'data': 'test' * 100}, 60)
        times.append((time.time() - start) * 1000)
    
    avg_write = statistics.mean(times)
    print(f"  ✅ كتابة Cache: {avg_write:.3f}ms متوسط")
    
    # اختبار القراءة
    times = []
    for i in range(100):
        start = time.time()
        cache.get(f'benchmark_key_{i}')
        times.append((time.time() - start) * 1000)
    
    avg_read = statistics.mean(times)
    print(f"  ✅ قراءة Cache: {avg_read:.3f}ms متوسط")
    
    # تنظيف
    for i in range(100):
        cache.delete(f'benchmark_key_{i}')
    
    return avg_read


def benchmark_context_processors():
    """قياس أداء Context Processors"""
    from django.test import RequestFactory
    from django.contrib.auth import get_user_model
    
    print("\n📊 قياس أداء Context Processors")
    print("-" * 50)
    
    User = get_user_model()
    factory = RequestFactory()
    
    # الحصول على مستخدم للاختبار
    try:
        user = User.objects.first()
        if not user:
            print("  ⚠️ لا يوجد مستخدمين للاختبار")
            return 0
    except:
        print("  ⚠️ خطأ في الحصول على المستخدم")
        return 0
    
    request = factory.get('/')
    request.user = user
    
    # اختبار كل context processor
    from accounts.context_processors import departments, company_info, footer_settings
    from crm.context_processors import admin_stats
    
    processors = [
        ('departments', departments),
        ('company_info', company_info),
        ('footer_settings', footer_settings),
        ('admin_stats', admin_stats),
    ]
    
    total_time = 0
    
    for name, func in processors:
        times = []
        for _ in range(10):
            start = time.time()
            func(request)
            times.append((time.time() - start) * 1000)
        
        avg_time = statistics.mean(times)
        total_time += avg_time
        cached = "✅ cached" if avg_time < 1 else "⚠️ slow"
        print(f"  {cached} {name}: {avg_time:.2f}ms")
    
    print(f"\n  📈 إجمالي Context Processors: {total_time:.2f}ms")
    
    return total_time


def benchmark_template_rendering():
    """قياس أداء تحميل القوالب"""
    from django.template.loader import get_template
    
    print("\n📊 قياس أداء تحميل القوالب")
    print("-" * 50)
    
    templates = ['base.html', 'home.html']
    
    for template_name in templates:
        try:
            times = []
            for _ in range(10):
                start = time.time()
                template = get_template(template_name)
                times.append((time.time() - start) * 1000)
            
            avg_time = statistics.mean(times)
            cached = "✅" if avg_time < 5 else "⚠️"
            print(f"  {cached} {template_name}: {avg_time:.2f}ms")
        except:
            print(f"  ⚠️ {template_name}: غير موجود")


def main():
    """تشغيل جميع الاختبارات"""
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║  🚀 أداة قياس الأداء - Performance Benchmark                             ║
║  قياس سرعة التطبيق                                                       ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    results = {}
    
    try:
        results['database'] = benchmark_database()
    except Exception as e:
        print(f"  ❌ خطأ في قياس قاعدة البيانات: {e}")
    
    try:
        results['cache'] = benchmark_cache()
    except Exception as e:
        print(f"  ❌ خطأ في قياس Cache: {e}")
    
    try:
        results['context_processors'] = benchmark_context_processors()
    except Exception as e:
        print(f"  ❌ خطأ في قياس Context Processors: {e}")
    
    try:
        benchmark_template_rendering()
    except Exception as e:
        print(f"  ❌ خطأ في قياس القوالب: {e}")
    
    # الملخص
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║  📈 ملخص الأداء                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣""")
    
    total = sum(results.values()) if results else 0
    
    if total < 50:
        grade = "🌟 ممتاز"
    elif total < 100:
        grade = "✅ جيد جداً"
    elif total < 200:
        grade = "⚠️ مقبول"
    else:
        grade = "❌ بطيء"
    
    print(f"""║  الدرجة: {grade}
║  إجمالي الوقت: {total:.2f}ms
╚══════════════════════════════════════════════════════════════════════════╝
    """)


if __name__ == '__main__':
    main()
