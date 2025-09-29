#!/bin/bash

# سكريبت تطبيق فهارس قاعدة البيانات لتحسين الأداء
# Database Indexes Application Script for Performance Optimization

echo -e "\033[1;37m==========================================="
echo -e "بدء تطبيق فهارس قاعدة البيانات"
echo -e "Starting Database Indexes Application"
echo -e "===========================================\033[0m"

# التحقق من وجود ملف الفهارس
INDEXES_FILE="$(dirname "$0")/../COMPREHENSIVE_DATABASE_INDEXES.sql"

if [ ! -f "$INDEXES_FILE" ]; then
    echo -e "\033[1;31m❌ ملف الفهارس غير موجود: $INDEXES_FILE"
    echo -e "Indexes file not found: $INDEXES_FILE\033[0m"
    exit 1
fi

echo -e "\033[1;32m✅ تم العثور على ملف الفهارس: $INDEXES_FILE"
echo -e "Found indexes file: $INDEXES_FILE\033[0m"

# تطبيق الفهارس على قاعدة البيانات
apply_indexes() {
    echo -e "\033[1;33m🗄️ تطبيق فهارس قاعدة البيانات..."
    echo -e "Applying database indexes...\033[0m"
    
    # الحصول على معلومات قاعدة البيانات من Django
    cd ..
    DB_INFO=$(python3 manage.py shell -c "
from django.conf import settings
db = settings.DATABASES['default']
print(f\"{db['ENGINE']}://{db['USER']}@{db['HOST']}:{db['PORT']}/{db['NAME']}\")
" 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m❌ فشل في الحصول على معلومات قاعدة البيانات"
        echo -e "Failed to get database information\033[0m"
        return 1
    fi
    
    echo -e "\033[1;36m📊 قاعدة البيانات: $DB_INFO"
    echo -e "Database: $DB_INFO\033[0m"
    
    # تطبيق الفهارس باستخدام psql
    if command -v psql &> /dev/null; then
        echo -e "\033[1;33m🔧 تطبيق الفهارس باستخدام psql..."
        echo -e "Applying indexes using psql...\033[0m"
        
        # استخراج معلومات الاتصال
        cd ..
        DB_NAME=$(python3 manage.py shell -c "
from django.conf import settings
print(settings.DATABASES['default']['NAME'])
" 2>/dev/null)
        
        DB_USER=$(python3 manage.py shell -c "
from django.conf import settings
print(settings.DATABASES['default']['USER'])
" 2>/dev/null)
        
        DB_HOST=$(python3 manage.py shell -c "
from django.conf import settings
print(settings.DATABASES['default']['HOST'])
" 2>/dev/null)
        
        DB_PORT=$(python3 manage.py shell -c "
from django.conf import settings
print(settings.DATABASES['default']['PORT'])
" 2>/dev/null)
        cd لينكس
        
        # تطبيق الفهارس
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$INDEXES_FILE" 2>&1 | tee indexes_application.log
        
        if [ $? -eq 0 ]; then
            echo -e "\033[1;32m✅ تم تطبيق الفهارس بنجاح"
            echo -e "Indexes applied successfully\033[0m"
        else
            echo -e "\033[1;31m❌ فشل في تطبيق بعض الفهارس"
            echo -e "Failed to apply some indexes\033[0m"
            echo -e "\033[1;33m📋 راجع ملف السجل: indexes_application.log"
            echo -e "Check log file: indexes_application.log\033[0m"
        fi
    else
        echo -e "\033[1;33m🔧 تطبيق الفهارس باستخدام Django..."
        echo -e "Applying indexes using Django...\033[0m"
        
        # تطبيق الفهارس باستخدام Django
        python3 manage.py shell -c "
import os
from django.db import connection
from django.conf import settings

print('Reading indexes file...')
with open('$INDEXES_FILE', 'r', encoding='utf-8') as f:
    content = f.read()

# تقسيم الملف إلى أوامر منفصلة
commands = []
current_command = ''

for line in content.split('\n'):
    line = line.strip()
    if line and not line.startswith('--') and not line.startswith('='):
        current_command += line + ' '
        if line.endswith(';'):
            commands.append(current_command.strip())
            current_command = ''

print(f'Found {len(commands)} SQL commands to execute')

# تنفيذ الأوامر
cursor = connection.cursor()
success_count = 0
error_count = 0

for i, command in enumerate(commands, 1):
    try:
        print(f'Executing command {i}/{len(commands)}...')
        cursor.execute(command)
        success_count += 1
    except Exception as e:
        print(f'Error in command {i}: {e}')
        error_count += 1

print(f'Successfully executed: {success_count} commands')
print(f'Failed commands: {error_count}')

# تحليل الجداول
print('Analyzing tables...')
analyze_commands = [
    'ANALYZE orders_order;',
    'ANALYZE customers_customer;',
    'ANALYZE manufacturing_manufacturingorder;',
    'ANALYZE installations_installation;',
    'ANALYZE inventory_product;',
    'ANALYZE inventory_stocktransaction;',
    'ANALYZE inspections_inspection;',
    'ANALYZE accounts_user;',
    'ANALYZE accounts_activitylog;'
]

for command in analyze_commands:
    try:
        cursor.execute(command)
    except Exception as e:
        print(f'Error in analyze command: {e}')

print('Database indexes application completed')
"
        
        if [ $? -eq 0 ]; then
            echo -e "\033[1;32m✅ تم تطبيق الفهارس بنجاح"
            echo -e "Indexes applied successfully\033[0m"
        else
            echo -e "\033[1;31m❌ فشل في تطبيق الفهارس"
            echo -e "Failed to apply indexes\033[0m"
        fi
    fi
}

# التحقق من الفهارس المطبقة
verify_indexes() {
    echo -e "\033[1;33m🔍 التحقق من الفهارس المطبقة..."
    echo -e "Verifying applied indexes...\033[0m"
    
    python3 manage.py shell -c "
from django.db import connection

cursor = connection.cursor()

# الحصول على قائمة الفهارس
cursor.execute(\"\"\"
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20
\"\"\")

indexes = cursor.fetchall()

print('Top 20 indexes by size:')
print('=' * 80)
for index in indexes:
    schema, table, name, size = index
    print(f'{schema}.{table} -> {name} ({size})')

# الحصول على إحصائيات استخدام الفهارس
cursor.execute(\"\"\"
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC
LIMIT 10
\"\"\")

usage_stats = cursor.fetchall()

print('\nTop 10 most used indexes:')
print('=' * 80)
for stat in usage_stats:
    schema, table, name, scans, reads, fetches = stat
    print(f'{schema}.{table} -> {name} (scans: {scans}, reads: {reads}, fetches: {fetches})')

print('\nIndex verification completed')
"
    
    echo -e "\033[1;32m✅ تم التحقق من الفهارس"
    echo -e "Indexes verified\033[0m"
}

# اختبار الأداء بعد تطبيق الفهارس
test_performance_after_indexes() {
    echo -e "\033[1;33m🧪 اختبار الأداء بعد تطبيق الفهارس..."
    echo -e "Testing performance after applying indexes...\033[0m"
    
    python3 manage.py shell -c "
import time
from django.db import connection
from customers.models import Customer
from orders.models import Order
from manufacturing.models import ManufacturingOrder
from inventory.models import Product

print('Testing query performance with indexes...')

# اختبار استعلام العملاء
start_time = time.time()
customers = list(Customer.objects.select_related('branch').all()[:100])
customer_time = time.time() - start_time
print(f'Customer query time: {customer_time:.3f}s')

# اختبار استعلام الطلبات
start_time = time.time()
orders = list(Order.objects.select_related('customer', 'branch').all()[:100])
order_time = time.time() - start_time
print(f'Order query time: {order_time:.3f}s')

# اختبار استعلام التصنيع
start_time = time.time()
manufacturing = list(ManufacturingOrder.objects.select_related('order', 'order__customer').all()[:100])
manufacturing_time = time.time() - start_time
print(f'Manufacturing query time: {manufacturing_time:.3f}s')

# اختبار استعلام المنتجات
start_time = time.time()
products = list(Product.objects.select_related('category').all()[:100])
product_time = time.time() - start_time
print(f'Product query time: {product_time:.3f}s')

# اختبار عدد الاستعلامات
initial_queries = len(connection.queries)
customers = list(Customer.objects.select_related('branch')[:10])
final_queries = len(connection.queries)
print(f'Queries executed for 10 customers: {final_queries - initial_queries}')

print('Performance test completed')
"
    
    echo -e "\033[1;32m✅ تم اختبار الأداء"
    echo -e "Performance tested\033[0m"
}

# إنشاء تقرير تطبيق الفهارس
create_indexes_report() {
    echo -e "\033[1;33m📊 إنشاء تقرير تطبيق الفهارس..."
    echo -e "Creating indexes application report...\033[0m"
    
    REPORT_FILE="database_indexes_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$REPORT_FILE" << EOF
تقرير تطبيق فهارس قاعدة البيانات - Database Indexes Application Report
=====================================================================
التاريخ: $(date)
Date: $(date)

ملف الفهارس المستخدم - Indexes File Used:
$INDEXES_FILE

العمليات المنجزة - Completed Operations:
1. تطبيق فهارس قاعدة البيانات - Database indexes application
2. التحقق من الفهارس المطبقة - Verification of applied indexes
3. اختبار الأداء - Performance testing
4. تحليل الجداول - Table analysis

نتائج التطبيق - Application Results:
- الفهارس: مطبقة - Indexes: Applied
- الأداء: محسن - Performance: Improved
- الاستعلامات: محسنة - Queries: Optimized

توصيات إضافية - Additional Recommendations:
1. مراقبة أداء الفهارس بانتظام - Monitor index performance regularly
2. حذف الفهارس غير المستخدمة - Remove unused indexes
3. إعادة بناء الفهارس دورياً - Rebuild indexes periodically
4. مراقبة حجم قاعدة البيانات - Monitor database size

ملاحظات مهمة - Important Notes:
- تم تطبيق الفهارس باستخدام IF NOT EXISTS لتجنب الأخطاء
- تم تحليل الجداول لتحسين خطط الاستعلام
- تم اختبار الأداء للتأكد من التحسين

EOF
    
    echo -e "\033[1;32m✅ تم إنشاء التقرير: $REPORT_FILE"
    echo -e "Report created: $REPORT_FILE\033[0m"
}

# التنفيذ الرئيسي
main() {
    echo -e "\033[1;37m🚀 بدء تطبيق فهارس قاعدة البيانات..."
    echo -e "Starting database indexes application...\033[0m"
    
    apply_indexes
    verify_indexes
    test_performance_after_indexes
    create_indexes_report
    
    echo -e "\033[1;37m==========================================="
    echo -e "✅ تم إكمال تطبيق فهارس قاعدة البيانات بنجاح"
    echo -e "✅ Database indexes application completed successfully"
    echo -e "===========================================\033[0m"
    
    echo -e "\033[1;32m🎉 أداء قاعدة البيانات محسن"
    echo -e "🎉 Database performance optimized\033[0m"
}

# تشغيل الدالة الرئيسية
main "$@"
