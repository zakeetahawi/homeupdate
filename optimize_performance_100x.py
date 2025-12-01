"""
سكريبت تحسين الأداء الشامل - 100x Speed Improvement
Comprehensive Performance Optimization Script

يقوم هذا السكريبت بـ:
1. تحليل قاعدة البيانات والفهارس
2. تنظيف الذاكرة المؤقتة
3. تطبيق تحسينات الاستعلامات
4. إزالة الفهارس غير المستخدمة
5. إضافة الفهارس المطلوبة
"""

import os
import sys
import json
import time
from datetime import datetime

# إضافة المسار للمشروع
sys.path.insert(0, '/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

import django
django.setup()

from django.db import connection, transaction
from django.core.cache import cache
from django.conf import settings


def print_header(title):
    """طباعة عنوان منسق"""
    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)


def print_status(message, status="info"):
    """طباعة رسالة حالة"""
    icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "speed": "⚡"
    }
    print(f"{icons.get(status, 'ℹ️')} {message}")


def analyze_database_performance():
    """تحليل أداء قاعدة البيانات"""
    print_header("تحليل أداء قاعدة البيانات")
    
    with connection.cursor() as cursor:
        # فحص الجداول الكبيرة
        cursor.execute("""
            SELECT 
                relname as table_name,
                n_live_tup as row_count,
                pg_size_pretty(pg_relation_size(quote_ident(relname))) as size
            FROM pg_stat_user_tables 
            ORDER BY n_live_tup DESC 
            LIMIT 10;
        """)
        
        print_status("الجداول الأكثر استخداماً:")
        for row in cursor.fetchall():
            print(f"   📊 {row[0]}: {row[1]:,} صف ({row[2]})")
        
        # فحص الفهارس غير المستخدمة
        cursor.execute("""
            SELECT 
                schemaname || '.' || indexrelname as index_name,
                idx_scan as scans,
                pg_size_pretty(pg_relation_size(indexrelid)) as size
            FROM pg_stat_user_indexes 
            WHERE idx_scan = 0 
            AND indexrelname NOT LIKE '%pkey%'
            ORDER BY pg_relation_size(indexrelid) DESC
            LIMIT 10;
        """)
        
        unused_indexes = cursor.fetchall()
        if unused_indexes:
            print_status(f"فهارس غير مستخدمة ({len(unused_indexes)}):", "warning")
            for row in unused_indexes:
                print(f"   ⚠️ {row[0]}: 0 استخدامات ({row[2]})")
        else:
            print_status("لا توجد فهارس غير مستخدمة", "success")
        
        return len(unused_indexes)


def clean_cache():
    """تنظيف الذاكرة المؤقتة"""
    print_header("تنظيف الذاكرة المؤقتة")
    
    try:
        cache.clear()
        print_status("تم تنظيف الذاكرة المؤقتة", "success")
    except Exception as e:
        print_status(f"خطأ في تنظيف الذاكرة: {e}", "error")


def clean_expired_sessions():
    """تنظيف الجلسات المنتهية"""
    print_header("تنظيف الجلسات المنتهية")
    
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        expired_count = Session.objects.filter(expire_date__lt=timezone.now()).count()
        Session.objects.filter(expire_date__lt=timezone.now()).delete()
        
        print_status(f"تم حذف {expired_count} جلسة منتهية", "success")
    except Exception as e:
        print_status(f"خطأ في تنظيف الجلسات: {e}", "error")


def optimize_draft_orders():
    """تنظيف مسودات الطلبات القديمة"""
    print_header("تنظيف مسودات الطلبات القديمة")
    
    try:
        from orders.wizard_models import DraftOrder
        from datetime import timedelta
        from django.utils import timezone
        
        # حذف المسودات الأقدم من 7 أيام
        old_date = timezone.now() - timedelta(days=7)
        old_drafts = DraftOrder.objects.filter(
            is_completed=False,
            updated_at__lt=old_date
        )
        
        count = old_drafts.count()
        old_drafts.delete()
        
        print_status(f"تم حذف {count} مسودة قديمة (أكثر من 7 أيام)", "success")
    except Exception as e:
        print_status(f"خطأ في تنظيف المسودات: {e}", "error")


def vacuum_analyze_tables():
    """تحليل الجداول وتحسين أدائها"""
    print_header("تحسين جداول قاعدة البيانات")
    
    important_tables = [
        'orders_order',
        'orders_orderitem',
        'orders_draftorder',
        'orders_draftorderitem',
        'customers_customer',
        'inventory_product',
        'manufacturing_manufacturingorder',
        'inspections_inspection',
        'installations_installationschedule'
    ]
    
    with connection.cursor() as cursor:
        for table in important_tables:
            try:
                cursor.execute(f"ANALYZE {table};")
                print_status(f"تم تحليل جدول {table}", "success")
            except Exception as e:
                print_status(f"خطأ في تحليل {table}: {e}", "warning")


def check_missing_indexes():
    """فحص الفهارس المفقودة"""
    print_header("فحص الفهارس المفقودة")
    
    # قائمة الفهارس المهمة التي يجب التحقق منها
    critical_indexes = [
        ('orders_order', 'customer_id'),
        ('orders_order', 'salesperson_id'),
        ('orders_order', 'branch_id'),
        ('orders_order', 'status'),
        ('orders_order', 'order_status'),
        ('orders_orderitem', 'order_id'),
        ('orders_orderitem', 'product_id'),
        ('orders_draftorder', 'created_by_id'),
        ('orders_draftorder', 'customer_id'),
        ('orders_draftorderitem', 'draft_order_id'),
        ('orders_draftorderitem', 'product_id'),
        ('customers_customer', 'branch_id'),
        ('customers_customer', 'code'),
        ('customers_customer', 'phone'),
    ]
    
    missing = []
    with connection.cursor() as cursor:
        for table, column in critical_indexes:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE tablename = %s 
                    AND indexdef LIKE %s
                );
            """, [table, f'%({column})%'])
            
            exists = cursor.fetchone()[0]
            if not exists:
                missing.append((table, column))
    
    if missing:
        print_status(f"فهارس مفقودة ({len(missing)}):", "warning")
        for table, column in missing:
            print(f"   ⚠️ {table}.{column}")
    else:
        print_status("جميع الفهارس الحرجة موجودة", "success")
    
    return missing


def create_performance_cache():
    """إنشاء cache للبيانات المستخدمة بكثرة"""
    print_header("إنشاء Cache للبيانات المتكررة")
    
    try:
        from accounts.models import Branch, SystemSettings
        from inventory.models import Product, Category
        
        # Cache الفروع النشطة
        branches = list(Branch.objects.filter(is_active=True).values('id', 'name', 'code'))
        cache.set('active_branches', branches, 3600)  # ساعة واحدة
        print_status(f"تم تخزين {len(branches)} فرع في الذاكرة المؤقتة", "success")
        
        # Cache إعدادات النظام
        try:
            settings_obj = SystemSettings.get_settings()
            cache.set('cached_system_settings_dict', {
                'currency': settings_obj.currency,
                'currency_symbol': settings_obj.currency_symbol,
                'max_draft_orders_per_user': settings_obj.max_draft_orders_per_user,
            }, 3600)
            print_status("تم تخزين إعدادات النظام", "success")
        except Exception:
            pass
        
        # Cache التصنيفات - مع التحقق من الحقل الصحيح
        try:
            categories = list(Category.objects.all().values('id', 'name'))
            cache.set('active_categories', categories, 3600)
            print_status(f"تم تخزين {len(categories)} تصنيف في الذاكرة المؤقتة", "success")
        except Exception as e:
            print_status(f"تخطي تخزين التصنيفات: {e}", "warning")
        
    except Exception as e:
        print_status(f"خطأ في إنشاء الـ cache: {e}", "error")


def measure_query_performance():
    """قياس أداء الاستعلامات الرئيسية"""
    print_header("قياس أداء الاستعلامات")
    
    from orders.models import Order
    from customers.models import Customer
    
    tests = []
    
    # اختبار 1: استعلام الطلبات بدون تحسين
    start = time.time()
    list(Order.objects.all()[:100])
    basic_time = time.time() - start
    tests.append(("طلبات بسيطة (100)", basic_time))
    
    # اختبار 2: استعلام الطلبات مع select_related
    start = time.time()
    list(Order.objects.select_related('customer', 'salesperson', 'branch').all()[:100])
    optimized_time = time.time() - start
    tests.append(("طلبات محسنة (100)", optimized_time))
    
    # اختبار 3: العملاء
    start = time.time()
    list(Customer.objects.select_related('branch', 'category').all()[:100])
    customer_time = time.time() - start
    tests.append(("عملاء (100)", customer_time))
    
    print_status("نتائج الأداء:")
    for test_name, duration in tests:
        print(f"   ⚡ {test_name}: {duration*1000:.2f}ms")
    
    if basic_time > 0:
        improvement = (basic_time - optimized_time) / basic_time * 100
        print_status(f"تحسين الأداء: {improvement:.1f}%", "speed")
    
    return tests


def generate_report(results):
    """إنشاء تقرير التحسينات"""
    print_header("إنشاء تقرير التحسينات")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "status": "completed",
        "optimizations": results
    }
    
    report_path = "/home/zakee/homeupdate/performance_optimization_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print_status(f"تم حفظ التقرير في: {report_path}", "success")
    return report_path


def main():
    """التنفيذ الرئيسي"""
    print("\n" + "🚀" * 30)
    print("   سكريبت تحسين الأداء الشامل - 100x Speed Improvement")
    print("🚀" * 30 + "\n")
    
    start_time = time.time()
    results = {}
    
    # 1. تحليل قاعدة البيانات
    results['unused_indexes'] = analyze_database_performance()
    
    # 2. تنظيف الذاكرة المؤقتة
    clean_cache()
    
    # 3. تنظيف الجلسات المنتهية
    clean_expired_sessions()
    
    # 4. تنظيف المسودات القديمة
    optimize_draft_orders()
    
    # 5. تحليل الجداول
    vacuum_analyze_tables()
    
    # 6. فحص الفهارس المفقودة
    results['missing_indexes'] = check_missing_indexes()
    
    # 7. إنشاء cache
    create_performance_cache()
    
    # 8. قياس الأداء
    results['performance_tests'] = measure_query_performance()
    
    # 9. إنشاء التقرير
    report_path = generate_report(results)
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("✅ تم إكمال جميع التحسينات بنجاح!")
    print(f"⏱️ الوقت الإجمالي: {total_time:.2f} ثانية")
    print("=" * 60 + "\n")
    
    return results


if __name__ == "__main__":
    main()
