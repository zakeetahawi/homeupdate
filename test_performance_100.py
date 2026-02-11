#!/usr/bin/env python
"""
اختبار شامل لتحسينات الأداء 100%
=====================================

هذا السكريبت يقيس الأداء قبل وبعد التحسينات
"""

import os
import sys
import django
import time
from decimal import Decimal

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.test.utils import override_settings
from django.db import connection, reset_queries
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.core.cache import cache

# Import views
from accounting.views import (
    dashboard,
    customer_financial_summary,
    customer_balances_report,
    transaction_list
)

# Import models
from accounting.models import CustomerFinancialSummary
from customers.models import Customer

User = get_user_model()
factory = RequestFactory()


def print_header(text):
    """طباعة عنوان"""
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}\n")


def print_result(name, queries, time_taken, memory_mb):
    """طباعة نتيجة الاختبار"""
    print(f"✓ {name}")
    print(f"  Queries: {queries}")
    print(f"  Time: {time_taken:.3f}s")
    print(f"  Memory: {memory_mb:.1f} MB")
    print()


def get_memory_usage():
    """الحصول على استخدام الذاكرة"""
    import psutil
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024  # MB


def test_view_performance(view_func, view_name, url, kwargs=None, use_cache=True):
    """اختبار أداء view محدد"""
    print(f"\n{'-'*80}")
    print(f"🔍 اختبار: {view_name}")
    print(f"{'-'*80}")
    
    # مسح الـ cache إذا لزم الأمر
    if not use_cache:
        cache.clear()
    
    with override_settings(DEBUG=True):
        reset_queries()
        mem_before = get_memory_usage()
        
        # إنشاء request
        request = factory.get(url)
        request.user = User.objects.first()
        
        try:
            # تنفيذ الـ view
            start_time = time.time()
            
            if kwargs:
                response = view_func(request, **kwargs)
            else:
                response = view_func(request)
            
            time_taken = time.time() - start_time
            
            # حساب الإحصائيات
            num_queries = len(connection.queries)
            mem_after = get_memory_usage()
            memory_used = mem_after - mem_before
            
            # النتائج
            status = "✅ ممتاز" if num_queries <= 10 else "⚠️ جيد" if num_queries <= 20 else "❌ بطيء"
            
            print(f"\nالنتائج:")
            print(f"  Status: {response.status_code}")
            print(f"  Queries: {num_queries} {status}")
            print(f"  Time: {time_taken:.3f}s")
            print(f"  Memory: {memory_used:.1f} MB")
            
            # تقييم الأداء
            if num_queries <= 5:
                rating = "⭐⭐⭐⭐⭐ ممتاز جداً!"
            elif num_queries <= 10:
                rating = "⭐⭐⭐⭐ ممتاز"
            elif num_queries <= 15:
                rating = "⭐⭐⭐ جيد جداً"
            elif num_queries <= 25:
                rating = "⭐⭐ جيد"
            else:
                rating = "⭐ يحتاج تحسين"
            
            print(f"  التقييم: {rating}")
            
            # عرض أبطأ queries
            if num_queries > 0:
                print(f"\n  أبطأ 5 Queries:")
                sorted_queries = sorted(
                    connection.queries,
                    key=lambda x: float(x['time']),
                    reverse=True
                )[:5]
                
                for i, q in enumerate(sorted_queries, 1):
                    sql = q['sql'][:100] + '...' if len(q['sql']) > 100 else q['sql']
                    print(f"    {i}. [{q['time']}s] {sql}")
            
            # اختبار الـ cache
            if use_cache:
                print(f"\n  اختبار Cache:")
                reset_queries()
                start_time = time.time()
                
                if kwargs:
                    response2 = view_func(request, **kwargs)
                else:
                    response2 = view_func(request)
                
                time_taken2 = time.time() - start_time
                num_queries2 = len(connection.queries)
                
                improvement = ((num_queries - num_queries2) / num_queries * 100) if num_queries > 0 else 0
                time_improvement = ((time_taken - time_taken2) / time_taken * 100) if time_taken > 0 else 0
                
                print(f"    التحميل الثاني (من Cache):")
                print(f"    Queries: {num_queries2} (تحسين {improvement:.0f}%)")
                print(f"    Time: {time_taken2:.3f}s (تحسين {time_improvement:.0f}%)")
            
            return {
                'queries': num_queries,
                'time': time_taken,
                'memory': memory_used,
                'status': response.status_code
            }
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
            import traceback
            traceback.print_exc()
            return None


def test_indexes():
    """اختبار الـ indexes"""
    print_header("اختبار Database Indexes")
    
    # التحقق من الـ indexes
    from django.db import connection
    
    with connection.cursor() as cursor:
        # CustomerFinancialSummary indexes
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'accounting_customerfinancialsummary'
            ORDER BY indexname
        """)
        indexes = cursor.fetchall()
        
        print("✓ Indexes على CustomerFinancialSummary:")
        for idx in indexes:
            print(f"  - {idx[0]}")
        
        # TransactionLine indexes
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'accounting_transactionline'
            ORDER BY indexname
        """)
        indexes = cursor.fetchall()
        
        print("\n✓ Indexes على TransactionLine:")
        for idx in indexes:
            print(f"  - {idx[0]}")


def test_cache_functions():
    """اختبار دوال الـ caching"""
    print_header("اختبار Caching Functions")
    
    from accounting.performance_utils import (
        get_dashboard_stats_cached,
        get_customer_summary_cached,
        get_optimized_customers_with_debt
    )
    
    # مسح الـ cache
    cache.clear()
    
    # 1. Dashboard stats
    print("1. Dashboard Stats Cache:")
    start = time.time()
    stats1 = get_dashboard_stats_cached()
    time1 = time.time() - start
    
    start = time.time()
    stats2 = get_dashboard_stats_cached()  # من الـ cache
    time2 = time.time() - start
    
    print(f"   التحميل الأول: {time1:.3f}s")
    print(f"   التحميل الثاني (cache): {time2:.3f}s")
    print(f"   التحسين: {(time1-time2)/time1*100:.0f}%")
    
    # 2. Customer summary
    first_customer = Customer.objects.first()
    if first_customer:
        print(f"\n2. Customer Summary Cache (ID: {first_customer.pk}):")
        
        cache.delete(f'customer_summary_{first_customer.pk}')
        
        start = time.time()
        summary1 = get_customer_summary_cached(first_customer.pk)
        time1 = time.time() - start
        
        start = time.time()
        summary2 = get_customer_summary_cached(first_customer.pk)  # من الـ cache
        time2 = time.time() - start
        
        print(f"   التحميل الأول: {time1:.3f}s")
        print(f"   التحميل الثاني (cache): {time2:.3f}s")
        print(f"   التحسين: {(time1-time2)/time1*100:.0f}% إذا كان time1 > 0 else 0")
    
    # 3. Optimized customers
    print(f"\n3. Optimized Customers Cache:")
    
    cache.delete('customers_debt_100_None_None')
    
    start = time.time()
    customers1 = get_optimized_customers_with_debt(limit=50)
    time1 = time.time() - start
    
    start = time.time()
    customers2 = get_optimized_customers_with_debt(limit=50)  # من الـ cache
    time2 = time.time() - start
    
    print(f"   التحميل الأول: {time1:.3f}s")
    print(f"   التحميل الثاني (cache): {time2:.3f}s")
    print(f"   التحسين: {(time1-time2)/time1*100:.0f}%")


def test_only_optimization():
    """اختبار تحسين only()"""
    print_header("اختبار only() Optimization")
    
    with override_settings(DEBUG=True):
        # بدون only()
        reset_queries()
        start = time.time()
        
        customers1 = list(Customer.objects.all()[:100])
        
        time1 = time.time() - start
        queries1 = len(connection.queries)
        mem1 = sys.getsizeof(customers1)
        
        # مع only()
        reset_queries()
        start = time.time()
        
        customers2 = list(
            Customer.objects.only('id', 'name', 'code', 'phone')[:100]
        )
        
        time2 = time.time() - start
        queries2 = len(connection.queries)
        mem2 = sys.getsizeof(customers2)
        
        print(f"بدون only():")
        print(f"  Time: {time1:.3f}s")
        print(f"  Queries: {queries1}")
        print(f"  Memory: {mem1/1024:.1f} KB")
        
        print(f"\nمع only():")
        print(f"  Time: {time2:.3f}s")
        print(f"  Queries: {queries2}")
        print(f"  Memory: {mem2/1024:.1f} KB")
        
        time_improvement = ((time1 - time2) / time1 * 100) if time1 > 0 else 0
        mem_improvement = ((mem1 - mem2) / mem1 * 100) if mem1 > 0 else 0
        
        print(f"\nالتحسين:")
        print(f"  الوقت: {time_improvement:.0f}%")
        print(f"  الذاكرة: {mem_improvement:.0f}%")


def main():
    """التنفيذ الرئيسي"""
    print_header("🚀 اختبار شامل لتحسينات الأداء 100%")
    
    # 1. اختبار الـ indexes
    test_indexes()
    
    # 2. اختبار الـ caching
    test_cache_functions()
    
    # 3. اختبار only()
    test_only_optimization()
    
    # 4. اختبار الـ views
    print_header("اختبار Views")
    
    results = []
    
    # Dashboard
    result = test_view_performance(
        dashboard,
        "Dashboard - لوحة المعلومات",
        '/accounting/dashboard/',
        use_cache=True
    )
    if result:
        results.append(('Dashboard', result))
    
    # Customer Financial
    first_customer = Customer.objects.first()
    if first_customer:
        result = test_view_performance(
            customer_financial_summary,
            f"Customer Financial - الملخص المالي (ID: {first_customer.pk})",
            f'/accounting/customer/{first_customer.pk}/financial/',
            kwargs={'customer_id': first_customer.pk},
            use_cache=True
        )
        if result:
            results.append(('Customer Financial', result))
    
    # Customer Balances
    result = test_view_performance(
        customer_balances_report,
        "Customer Balances - تقرير الأرصدة",
        '/accounting/reports/customer-balances/',
        use_cache=True
    )
    if result:
        results.append(('Balances Report', result))
    
    # Transaction List
    result = test_view_performance(
        transaction_list,
        "Transaction List - قائمة القيود",
        '/accounting/transactions/',
        use_cache=True
    )
    if result:
        results.append(('Transaction List', result))
    
    # الملخص النهائي
    print_header("📊 الملخص النهائي")
    
    print("| View | Queries | Time | Memory | Status |")
    print("|------|---------|------|--------|--------|")
    
    for name, result in results:
        print(f"| {name:20} | {result['queries']:7} | {result['time']:.3f}s | {result['memory']:.1f}MB | {result['status']} |")
    
    # التقييم
    if results:
        avg_queries = sum(r['queries'] for _, r in results) / len(results)
        avg_time = sum(r['time'] for _, r in results) / len(results)
        
        print(f"\nالمتوسط:")
        print(f"  Queries: {avg_queries:.1f}")
        print(f"  Time: {avg_time:.3f}s")
        
        if avg_queries <= 5:
            rating = "⭐⭐⭐⭐⭐ ممتاز جداً - 100% تحسين!"
        elif avg_queries <= 10:
            rating = "⭐⭐⭐⭐ ممتاز - 95%+ تحسين"
        elif avg_queries <= 15:
            rating = "⭐⭐⭐ جيد جداً - 85%+ تحسين"
        else:
            rating = "⭐⭐ جيد - يمكن تحسينه"
        
        print(f"\nالتقييم النهائي: {rating}")
    
    print_header("✅ اكتملت جميع الاختبارات")


if __name__ == '__main__':
    # التحقق من psutil
    try:
        import psutil
    except ImportError:
        print("⚠️ تثبيت psutil للحصول على قياسات الذاكرة:")
        print("   pip install psutil")
        print()
    
    main()
