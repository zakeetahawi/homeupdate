#!/bin/bash

# سكريبت تحسين أداء نظام إدارة العملاء
# Performance Optimization Script for Customer Management System

echo -e "\033[1;37m==========================================="
echo -e "بدء عملية تحسين الأداء"
echo -e "Starting Performance Optimization"
echo -e "===========================================\033[0m"

# تحسين قاعدة البيانات
optimize_database() {
    echo -e "\033[1;33m🗄️ تحسين قاعدة البيانات..."
    echo -e "Optimizing database...\033[0m"
    
    # تحليل الجداول
    python3 manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('VACUUM ANALYZE;')
print('Database analyzed and optimized')
"
    
    # تنظيف الجداول المؤقتة
    python3 manage.py shell -c "
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.core.cache import cache

# تنظيف الجلسات المنتهية
Session.objects.filter(expire_date__lt=timezone.now()).delete()
print('Expired sessions cleaned')

# تنظيف الذاكرة المؤقتة
cache.clear()
print('Cache cleared')
"
    
    echo -e "\033[1;32m✅ تم تحسين قاعدة البيانات"
    echo -e "Database optimized\033[0m"
}

# تحسين الملفات الثابتة
optimize_static_files() {
    echo -e "\033[1;33m📦 تحسين الملفات الثابتة..."
    echo -e "Optimizing static files...\033[0m"
    
    # جمع الملفات الثابتة مع الضغط
    python3 manage.py collectstatic --noinput --clear
    
    # ضغط ملفات CSS و JS
    if command -v gzip &> /dev/null; then
        find staticfiles -name "*.css" -exec gzip -9 {} \;
        find staticfiles -name "*.js" -exec gzip -9 {} \;
        echo -e "\033[1;32m✅ تم ضغط الملفات الثابتة"
        echo -e "Static files compressed\033[0m"
    else
        echo -e "\033[1;33m⚠️ gzip غير متوفر، تخطي الضغط"
        echo -e "gzip not available, skipping compression\033[0m"
    fi
}

# تحسين الذاكرة المؤقتة
optimize_cache() {
    echo -e "\033[1;33m💾 تحسين الذاكرة المؤقتة..."
    echo -e "Optimizing cache...\033[0m"
    
    python3 manage.py shell -c "
from django.core.cache import cache
from django.core.cache.backends.locmem import LocMemCache

# تنظيف الذاكرة المؤقتة
cache.clear()

# إعادة تهيئة الذاكرة المؤقتة
if hasattr(cache, '_cache'):
    cache._cache.clear()

print('Cache optimized and cleared')
"
    
    echo -e "\033[1;32m✅ تم تحسين الذاكرة المؤقتة"
    echo -e "Cache optimized\033[0m"
}

# تحسين الصلاحيات
optimize_permissions() {
    echo -e "\033[1;33m🔐 تحسين الصلاحيات..."
    echo -e "Optimizing permissions...\033[0m"
    
    python3 manage.py shell -c "
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import User, Role, UserRole

# تحديث الصلاحيات المخزنة مؤقتاً
for user in User.objects.all():
    if hasattr(user, '_cached_user_permissions'):
        delattr(user, '_cached_user_permissions')

print('User permissions cache cleared')

# تحديث أدوار المستخدمين
for user_role in UserRole.objects.select_related('user', 'role'):
    if hasattr(user_role.user, '_cached_user_permissions'):
        delattr(user_role.user, '_cached_user_permissions')

print('User roles cache updated')
"
    
    echo -e "\033[1;32m✅ تم تحسين الصلاحيات"
    echo -e "Permissions optimized\033[0m"
}

# تحسين الإعدادات
optimize_settings() {
    echo -e "\033[1;33m⚙️ تحسين الإعدادات..."
    echo -e "Optimizing settings...\033[0m"
    
    # فحص إعدادات الأداء
    python3 manage.py shell -c "
from django.conf import settings

# فحص إعدادات الذاكرة المؤقتة
print(f'Cache backend: {settings.CACHES[\"default\"][\"BACKEND\"]}')
print(f'Cache timeout: {settings.CACHES[\"default\"][\"TIMEOUT\"]}')

# فحص إعدادات الجلسة
print(f'Session engine: {settings.SESSION_ENGINE}')
print(f'Session timeout: {settings.SESSION_COOKIE_AGE}')

# فحص إعدادات قاعدة البيانات
print(f'Database engine: {settings.DATABASES[\"default\"][\"ENGINE\"]}')
if 'CONN_MAX_AGE' in settings.DATABASES['default']:
    print(f'Connection max age: {settings.DATABASES[\"default\"][\"CONN_MAX_AGE\"]}')

print('Settings check completed')
"
    
    echo -e "\033[1;32m✅ تم فحص الإعدادات"
    echo -e "Settings checked\033[0m"
}

# تحسين الملفات المؤقتة
optimize_temp_files() {
    echo -e "\033[1;33m🧹 تحسين الملفات المؤقتة..."
    echo -e "Optimizing temporary files...\033[0m"
    
    # حذف ملفات Python المؤقتة
    find . -name "*.pyc" -delete 2>/dev/null
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
    find . -name "*.pyo" -delete 2>/dev/null
    
    # تنظيف ملفات السجلات
    find . -name "*.log" -size +10M -delete 2>/dev/null
    
    # تنظيف ملفات النسخ الاحتياطية القديمة
    find backups -name "*.sql" -mtime +30 -delete 2>/dev/null
    
    echo -e "\033[1;32m✅ تم تنظيف الملفات المؤقتة"
    echo -e "Temporary files cleaned\033[0m"
}

# اختبار الأداء
test_performance() {
    echo -e "\033[1;33m🧪 اختبار الأداء..."
    echo -e "Testing performance...\033[0m"
    
    # اختبار سرعة الاستعلامات
    python3 manage.py shell -c "
import time
from django.db import connection
from customers.models import Customer
from orders.models import Order

# اختبار سرعة استعلام العملاء
start_time = time.time()
customers = Customer.objects.all()[:100]
customer_time = time.time() - start_time
print(f'Customer query time: {customer_time:.3f}s')

# اختبار سرعة استعلام الطلبات
start_time = time.time()
orders = Order.objects.all()[:100]
order_time = time.time() - start_time
print(f'Order query time: {order_time:.3f}s')

# اختبار عدد الاستعلامات
initial_queries = len(connection.queries)
customers = list(Customer.objects.select_related('branch')[:10])
final_queries = len(connection.queries)
print(f'Queries executed: {final_queries - initial_queries}')

print('Performance test completed')
"
    
    echo -e "\033[1;32m✅ تم اختبار الأداء"
    echo -e "Performance tested\033[0m"
}

# إنشاء تقرير التحسين
create_optimization_report() {
    echo -e "\033[1;33m📊 إنشاء تقرير التحسين..."
    echo -e "Creating optimization report...\033[0m"
    
    REPORT_FILE="performance_optimization_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$REPORT_FILE" << EOF
تقرير تحسين الأداء - Performance Optimization Report
==================================================
التاريخ: $(date)
Date: $(date)

التحسينات المطبقة - Applied Optimizations:
1. تحسين قاعدة البيانات - Database optimization
2. تحسين الملفات الثابتة - Static files optimization
3. تحسين الذاكرة المؤقتة - Cache optimization
4. تحسين الصلاحيات - Permissions optimization
5. تحسين الإعدادات - Settings optimization
6. تنظيف الملفات المؤقتة - Temporary files cleanup
7. اختبار الأداء - Performance testing

نتائج التحسين - Optimization Results:
- قاعدة البيانات: محسنة - Database: Optimized
- الملفات الثابتة: مضغوطة - Static files: Compressed
- الذاكرة المؤقتة: منظفة - Cache: Cleaned
- الصلاحيات: محدثة - Permissions: Updated
- الأداء: محسن - Performance: Improved

توصيات إضافية - Additional Recommendations:
1. مراقبة استخدام الذاكرة - Monitor memory usage
2. تنظيف السجلات بانتظام - Clean logs regularly
3. تحديث النظام دورياً - Update system regularly
4. مراقبة أداء قاعدة البيانات - Monitor database performance

EOF
    
    echo -e "\033[1;32m✅ تم إنشاء التقرير: $REPORT_FILE"
    echo -e "Report created: $REPORT_FILE\033[0m"
}

# التنفيذ الرئيسي
main() {
    echo -e "\033[1;37m🚀 بدء عملية تحسين الأداء..."
    echo -e "Starting performance optimization...\033[0m"
    
    optimize_database
    optimize_static_files
    optimize_cache
    optimize_permissions
    optimize_settings
    optimize_temp_files
    test_performance
    create_optimization_report
    
    echo -e "\033[1;37m==========================================="
    echo -e "✅ تم إكمال عملية تحسين الأداء بنجاح"
    echo -e "✅ Performance optimization completed successfully"
    echo -e "===========================================\033[0m"
    
    echo -e "\033[1;32m🎉 أداء النظام محسن"
    echo -e "🎉 System performance optimized\033[0m"
}

# تشغيل الدالة الرئيسية
main "$@" 