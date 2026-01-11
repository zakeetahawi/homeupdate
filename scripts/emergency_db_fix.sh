#!/bin/bash

# سكريبت إصلاح طوارئ لمشكلة "too many clients already"
# Emergency fix script for PostgreSQL "too many clients" issue

set -e

# ألوان للعرض
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
	echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
	echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
	echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
	echo -e "${RED}❌ $1${NC}"
}

print_info "🚨 بدء إصلاح طوارئ لمشكلة اتصالات قاعدة البيانات"

# التحقق من صلاحيات المستخدم
if [[ $EUID -eq 0 ]]; then
	print_warning "يتم تشغيل السكريبت كـ root"
	POSTGRES_USER="postgres"
else
	print_info "يتم تشغيل السكريبت كمستخدم عادي"
	POSTGRES_USER=$(whoami)
fi

# الخطوة 1: فحص حالة PostgreSQL
print_info "1️⃣ فحص حالة PostgreSQL..."
if systemctl is-active --quiet postgresql; then
	print_status "PostgreSQL يعمل"
else
	print_error "PostgreSQL لا يعمل!"
	print_info "محاولة تشغيل PostgreSQL..."
	sudo systemctl start postgresql
	sleep 3
	if systemctl is-active --quiet postgresql; then
		print_status "تم تشغيل PostgreSQL بنجاح"
	else
		print_error "فشل في تشغيل PostgreSQL"
		exit 1
	fi
fi

# الخطوة 2: فحص عدد الاتصالات الحالية
print_info "2️⃣ فحص عدد الاتصالات الحالية..."
CONNECTION_COUNT=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'crm_system';" 2>/dev/null || echo "0")
print_info "عدد الاتصالات الحالية: $CONNECTION_COUNT"

if [ "$CONNECTION_COUNT" -gt 50 ]; then
	print_warning "عدد الاتصالات مرتفع جداً!"

	# الخطوة 3: قتل الاتصالات الخاملة
	print_info "3️⃣ قتل الاتصالات الخاملة..."
	KILLED_CONNECTIONS=$(sudo -u postgres psql -t -c "
        SELECT count(pg_terminate_backend(pid))
        FROM pg_stat_activity 
        WHERE datname = 'crm_system' 
        AND state = 'idle'
        AND state_change < now() - interval '2 minutes'
        AND pid != pg_backend_pid();
    " 2>/dev/null || echo "0")
	print_status "تم قتل $KILLED_CONNECTIONS اتصال خامل"

	# الخطوة 4: قتل الاتصالات المعلقة في المعاملات
	print_info "4️⃣ قتل الاتصالات المعلقة في المعاملات..."
	KILLED_TRANSACTIONS=$(sudo -u postgres psql -t -c "
        SELECT count(pg_terminate_backend(pid))
        FROM pg_stat_activity 
        WHERE datname = 'crm_system' 
        AND state = 'idle in transaction'
        AND state_change < now() - interval '1 minute'
        AND pid != pg_backend_pid();
    " 2>/dev/null || echo "0")
	print_status "تم قتل $KILLED_TRANSACTIONS اتصال معلق في معاملة"
else
	print_status "عدد الاتصالات ضمن الحد المقبول"
fi

# الخطوة 5: تحسين إعدادات PostgreSQL
print_info "5️⃣ تحسين إعدادات PostgreSQL..."

# البحث عن ملف الإعدادات
POSTGRES_CONF=""
for conf_path in "/etc/postgresql/*/main/postgresql.conf" "/var/lib/pgsql/data/postgresql.conf" "/usr/local/pgsql/data/postgresql.conf"; do
	if [ -f $conf_path ]; then
		POSTGRES_CONF=$conf_path
		break
	fi
done

if [ -z "$POSTGRES_CONF" ]; then
	# محاولة العثور على الملف باستخدام PostgreSQL
	POSTGRES_CONF=$(sudo -u postgres psql -t -c "SHOW config_file;" 2>/dev/null | xargs)
fi

if [ -n "$POSTGRES_CONF" ] && [ -f "$POSTGRES_CONF" ]; then
	print_info "ملف الإعدادات: $POSTGRES_CONF"

	# إنشاء نسخة احتياطية
	sudo cp "$POSTGRES_CONF" "$POSTGRES_CONF.backup.$(date +%Y%m%d_%H%M%S)"
	print_status "تم إنشاء نسخة احتياطية"

	# تطبيق الإعدادات المحسنة
	print_info "تطبيق الإعدادات المحسنة..."

	# إزالة الإعدادات القديمة إن وجدت
	sudo sed -i '/# === إعدادات محسنة لتجنب مشكلة "too many clients" ===/,/# === نهاية الإعدادات المحسنة ===/d' "$POSTGRES_CONF"

	# إضافة الإعدادات الجديدة
	sudo tee -a "$POSTGRES_CONF" >/dev/null <<'EOF'

# === إعدادات محسنة لتجنب مشكلة "too many clients" ===

# زيادة عدد الاتصالات المسموحة
max_connections = 200

# تحسين إدارة الذاكرة
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# تحسين إعدادات الاتصال
tcp_keepalives_idle = 300
tcp_keepalives_interval = 30
tcp_keepalives_count = 3

# تحسين إعدادات الجلسات - قيم أقل للإغلاق السريع
idle_in_transaction_session_timeout = 30000  # 30 ثانية
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

# === نهاية الإعدادات المحسنة ===
EOF

	print_status "تم تطبيق الإعدادات المحسنة"

	# إعادة تشغيل PostgreSQL
	print_info "6️⃣ إعادة تشغيل PostgreSQL..."
	sudo systemctl restart postgresql

	# انتظار بدء الخدمة
	sleep 5

	# التحقق من حالة الخدمة
	if systemctl is-active --quiet postgresql; then
		print_status "PostgreSQL يعمل بنجاح مع الإعدادات الجديدة"
	else
		print_error "فشل في إعادة تشغيل PostgreSQL"
		print_info "استعادة النسخة الاحتياطية..."
		sudo cp "$POSTGRES_CONF.backup."* "$POSTGRES_CONF"
		sudo systemctl restart postgresql
		exit 1
	fi
else
	print_warning "لم يتم العثور على ملف إعدادات PostgreSQL"
fi

# الخطوة 7: فحص نهائي
print_info "7️⃣ فحص نهائي للاتصالات..."
sleep 2
FINAL_COUNT=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'crm_system';" 2>/dev/null || echo "0")
print_info "عدد الاتصالات بعد التحسين: $FINAL_COUNT"

# عرض إحصائيات مفصلة
print_info "📊 إحصائيات مفصلة:"
sudo -u postgres psql -c "
SELECT 
    count(*) as total_connections,
    count(*) FILTER (WHERE state = 'active') as active_connections,
    count(*) FILTER (WHERE state = 'idle') as idle_connections,
    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity 
WHERE datname = 'crm_system';
"

print_status "🎉 تم إكمال الإصلاح الطارئ بنجاح!"

print_info ""
print_info "📋 ملخص التحسينات المطبقة:"
print_info "   - max_connections: 200"
print_info "   - idle_in_transaction_session_timeout: 30 ثانية"
print_info "   - statement_timeout: 30 ثانية"
print_info "   - تمكين تسجيل الاتصالات"
print_info "   - تحسين إعدادات الذاكرة"
print_info ""
print_info "💡 خطوات إضافية موصى بها:"
print_info "   - راقب الاتصالات بانتظام"
print_info "   - فكر في تثبيت pgbouncer"
print_info "   - راجع إعدادات Django CONN_MAX_AGE"
print_info "   - تأكد من إغلاق الاتصالات في التطبيق"
