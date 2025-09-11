#!/bin/bash

# ===================================================================
# سكريبت تطبيق الفهارس الحرجة
# Critical Database Indexes Application Script
# ===================================================================

echo "🚀 بدء تطبيق الفهارس الحرجة..."
echo "=================================="

# التحقق من وجود ملف الفهارس الحرجة
if [ ! -f "CRITICAL_DATABASE_INDEXES.sql" ]; then
    echo "❌ خطأ: ملف CRITICAL_DATABASE_INDEXES.sql غير موجود"
    exit 1
fi

# قراءة معلومات قاعدة البيانات من settings.py
DB_NAME=$(python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])")
DB_USER=$(python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['USER'])")
DB_HOST=$(python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['HOST'])")
DB_PORT=$(python manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['PORT'])")

echo "📊 معلومات قاعدة البيانات:"
echo "   اسم قاعدة البيانات: $DB_NAME"
echo "   المستخدم: $DB_USER"
echo "   الخادم: $DB_HOST"
echo "   المنفذ: $DB_PORT"
echo ""

# إنشاء نسخة احتياطية من إحصائيات الفهارس الحالية
echo "💾 إنشاء نسخة احتياطية من إحصائيات الفهارس..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    idx_scan, 
    idx_tup_read 
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
" > indexes_stats_before.txt

echo "✅ تم حفظ إحصائيات الفهارس الحالية في indexes_stats_before.txt"

# تطبيق الفهارس الحرجة
echo ""
echo "🔧 تطبيق الفهارس الحرجة..."
echo "هذا قد يستغرق عدة دقائق..."

# تطبيق الفهارس مع عرض التقدم
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f CRITICAL_DATABASE_INDEXES.sql

if [ $? -eq 0 ]; then
    echo "✅ تم تطبيق الفهارس الحرجة بنجاح!"
else
    echo "❌ حدث خطأ أثناء تطبيق الفهارس"
    exit 1
fi

# التحقق من الفهارس الجديدة
echo ""
echo "🔍 التحقق من الفهارس الجديدة..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT 
    schemaname, 
    tablename, 
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes 
WHERE indexname LIKE 'idx_%'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;
"

# إنشاء تقرير بعد التطبيق
echo ""
echo "📊 إنشاء تقرير ما بعد التطبيق..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    idx_scan, 
    idx_tup_read 
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
" > indexes_stats_after.txt

echo "✅ تم حفظ إحصائيات الفهارس الجديدة في indexes_stats_after.txt"

echo ""
echo "🎉 تم إكمال تطبيق الفهارس الحرجة بنجاح!"
echo "=================================="
echo ""
echo "📋 الخطوات التالية:"
echo "1. إعادة تشغيل خادم Django:"
echo "   sudo systemctl restart gunicorn"
echo "   sudo systemctl restart nginx"
echo ""
echo "2. اختبار الصفحات الثقيلة:"
echo "   - /admin/accounts/user/"
echo "   - /admin/orders/order/"
echo "   - /admin/inventory/product/"
echo ""
echo "3. مراقبة الأداء لمدة 24 ساعة"
echo ""
echo "4. إذا كانت النتائج جيدة، طبق الفهارس الشاملة:"
echo "   psql -d $DB_NAME -f RECOMMENDED_DATABASE_INDEXES.sql"
echo ""
echo "📊 لمقارنة الأداء قبل وبعد:"
echo "   diff indexes_stats_before.txt indexes_stats_after.txt"
