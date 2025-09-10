#!/bin/bash

# سكريبت تحسين إعدادات PostgreSQL لتجنب مشكلة "too many clients"

echo "🔧 تحسين إعدادات PostgreSQL..."

# التحقق من وجود PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL غير مثبت"
    exit 1
fi

# إنشاء ملف إعدادات محسن
POSTGRES_CONF="/etc/postgresql/*/main/postgresql.conf"

# البحث عن ملف الإعدادات
CONF_FILE="/var/lib/postgres/data/postgresql.conf"

if [ ! -f "$CONF_FILE" ]; then
    # محاولة البحث في مواقع أخرى
    CONF_FILE=$(find /etc/postgresql -name "postgresql.conf" 2>/dev/null | head -1)
    if [ -z "$CONF_FILE" ]; then
        echo "❌ لم يتم العثور على ملف إعدادات PostgreSQL"
        exit 1
    fi
fi

echo "📁 ملف الإعدادات: $CONF_FILE"

# إنشاء نسخة احتياطية
sudo cp "$CONF_FILE" "$CONF_FILE.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ تم إنشاء نسخة احتياطية"

# تطبيق الإعدادات المحسنة
echo "⚙️ تطبيق الإعدادات المحسنة..."

sudo tee -a "$CONF_FILE" > /dev/null << 'EOF'

# ===== إعدادات محسنة لتجنب مشكلة "too many clients" =====

# زيادة عدد الاتصالات المسموحة
max_connections = 200

# تحسين إدارة الذاكرة
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# تحسين إعدادات الاتصال
tcp_keepalives_idle = 600
tcp_keepalives_interval = 30
tcp_keepalives_count = 3

# تحسين إعدادات الجلسات
idle_in_transaction_session_timeout = 60000  # 1 دقيقة
statement_timeout = 30000  # 30 ثانية

# تحسين إعدادات WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# تحسين إعدادات الفهرسة
random_page_cost = 1.1
effective_io_concurrency = 200

# تمكين التسجيل للاتصالات
log_connections = on
log_disconnections = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '

# تسجيل الاستعلامات البطيئة
log_min_duration_statement = 1000  # 1 ثانية

EOF

echo "✅ تم تطبيق الإعدادات المحسنة"

# إعادة تشغيل PostgreSQL
echo "🔄 إعادة تشغيل PostgreSQL..."
sudo systemctl restart postgresql

# التحقق من حالة الخدمة
if sudo systemctl is-active --quiet postgresql; then
    echo "✅ PostgreSQL يعمل بنجاح"
else
    echo "❌ فشل في إعادة تشغيل PostgreSQL"
    echo "🔄 استعادة النسخة الاحتياطية..."
    sudo cp "$CONF_FILE.backup."* "$CONF_FILE"
    sudo systemctl restart postgresql
    exit 1
fi

# عرض معلومات الاتصالات الحالية
echo ""
echo "📊 معلومات الاتصالات الحالية:"
sudo -u postgres psql -c "
SELECT 
    count(*) as total_connections,
    count(*) FILTER (WHERE state = 'active') as active_connections,
    count(*) FILTER (WHERE state = 'idle') as idle_connections,
    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity 
WHERE datname = 'crm_system';
"

echo ""
echo "🎉 تم تحسين PostgreSQL بنجاح!"
echo ""
echo "📋 الإعدادات المطبقة:"
echo "   - max_connections: 200"
echo "   - idle_in_transaction_session_timeout: 60 ثانية"
echo "   - statement_timeout: 30 ثانية"
echo "   - تمكين تسجيل الاتصالات"
echo ""
echo "💡 نصائح إضافية:"
echo "   - راقب الاتصالات بانتظام"
echo "   - استخدم connection pooling"
echo "   - قم بتنظيف الاتصالات الخاملة دورياً"
