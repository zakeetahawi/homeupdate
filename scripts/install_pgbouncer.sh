#!/bin/bash

# سكريبت تثبيت وإعداد pgbouncer لحل مشكلة "too many clients"
# PgBouncer installation and configuration script

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

print_info "🔧 بدء تثبيت وإعداد PgBouncer..."

# التحقق من صلاحيات المستخدم
if [[ $EUID -ne 0 ]]; then
	print_error "يجب تشغيل هذا السكريبت كـ root (استخدم sudo)"
	exit 1
fi

# الخطوة 1: تثبيت pgbouncer
print_info "1️⃣ تثبيت PgBouncer..."
apt-get update
apt-get install -y pgbouncer

if command -v pgbouncer &>/dev/null; then
	print_status "تم تثبيت PgBouncer بنجاح"
else
	print_error "فشل في تثبيت PgBouncer"
	exit 1
fi

# الخطوة 2: إنشاء ملف الإعدادات
print_info "2️⃣ إعداد ملف التكوين..."

# إنشاء نسخة احتياطية من الإعدادات الحالية
if [ -f "/etc/pgbouncer/pgbouncer.ini" ]; then
	cp /etc/pgbouncer/pgbouncer.ini /etc/pgbouncer/pgbouncer.ini.backup.$(date +%Y%m%d_%H%M%S)
	print_status "تم إنشاء نسخة احتياطية من الإعدادات"
fi

# إنشاء ملف الإعدادات الجديد
cat >/etc/pgbouncer/pgbouncer.ini <<'EOF'
;; Database name = connect string
;;
;; connect string params:
;;   dbname= host= port= user= password=
;;   client_encoding= datestyle= timezone=
;;   pool_size= connect_query=
[databases]
crm_system = host=localhost port=5432 dbname=crm_system user=postgres

[pgbouncer]
;;;
;;; Administrative settings
;;;
logfile = /var/log/postgresql/pgbouncer.log
pidfile = /var/run/postgresql/pgbouncer.pid

;;;
;;; Where to wait for clients
;;;
listen_addr = 127.0.0.1
listen_port = 6432

;;;
;;; Authentication settings
;;;
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

;;;
;;; Users allowed into database 'pgbouncer'
;;;
admin_users = postgres

;;;
;;; Pooler personality questions
;;;
pool_mode = transaction
server_reset_query = DISCARD ALL

;;;
;;; Connection limits
;;;
max_client_conn = 100
default_pool_size = 10
min_pool_size = 5
reserve_pool_size = 3
reserve_pool_timeout = 5

;;;
;;; Logging
;;;
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1

;;;
;;; Timeouts
;;;
server_lifetime = 3600
server_idle_timeout = 600
client_idle_timeout = 0
client_login_timeout = 60
autodb_idle_timeout = 3600

;;;
;;; Dangerous timeouts
;;;
query_timeout = 0
query_wait_timeout = 120
client_login_timeout = 60
idle_transaction_timeout = 0

;;;
;;; Low-level tuning options
;;;
pkt_buf = 4096
max_packet_size = 2147483647
listen_backlog = 128
sbuf_loopcnt = 5

;;;
;;; TLS settings
;;;
server_tls_sslmode = prefer
client_tls_sslmode = disable

;;;
;;; Dangerous options
;;;
ignore_startup_parameters = extra_float_digits

;;;
;;; Only set if you have special needs
;;;
application_name_add_host = 0
EOF

print_status "تم إنشاء ملف الإعدادات"

# الخطوة 3: إنشاء ملف المستخدمين
print_info "3️⃣ إعداد ملف المستخدمين..."

# الحصول على كلمة مرور postgres المشفرة
POSTGRES_PASSWORD_HASH=$(echo -n "5525postgres" | md5sum | cut -d' ' -f1)

cat >/etc/pgbouncer/userlist.txt <<EOF
"postgres" "md5$POSTGRES_PASSWORD_HASH"
EOF

print_status "تم إنشاء ملف المستخدمين"

# الخطوة 4: تعيين الصلاحيات
print_info "4️⃣ تعيين الصلاحيات..."
chown postgres:postgres /etc/pgbouncer/pgbouncer.ini
chown postgres:postgres /etc/pgbouncer/userlist.txt
chmod 640 /etc/pgbouncer/pgbouncer.ini
chmod 640 /etc/pgbouncer/userlist.txt

# إنشاء مجلد السجلات
mkdir -p /var/log/postgresql
chown postgres:postgres /var/log/postgresql

print_status "تم تعيين الصلاحيات"

# الخطوة 5: إنشاء خدمة systemd
print_info "5️⃣ إعداد خدمة systemd..."

cat >/etc/systemd/system/pgbouncer.service <<'EOF'
[Unit]
Description=PgBouncer PostgreSQL connection pooler
Documentation=https://pgbouncer.github.io/
After=postgresql.service
Requires=postgresql.service

[Service]
Type=forking
User=postgres
ExecStart=/usr/sbin/pgbouncer -d /etc/pgbouncer/pgbouncer.ini
ExecReload=/bin/kill -HUP $MAINPID
PIDFile=/var/run/postgresql/pgbouncer.pid
LimitNOFILE=65536

# Restart settings
Restart=on-failure
RestartSec=5
StartLimitInterval=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF

# إعادة تحميل systemd
systemctl daemon-reload
systemctl enable pgbouncer

print_status "تم إعداد خدمة systemd"

# الخطوة 6: تشغيل pgbouncer
print_info "6️⃣ تشغيل PgBouncer..."

# التأكد من أن PostgreSQL يعمل
if ! systemctl is-active --quiet postgresql; then
	print_info "تشغيل PostgreSQL..."
	systemctl start postgresql
	sleep 3
fi

# تشغيل pgbouncer
systemctl start pgbouncer

# التحقق من حالة الخدمة
sleep 3
if systemctl is-active --quiet pgbouncer; then
	print_status "PgBouncer يعمل بنجاح"
else
	print_error "فشل في تشغيل PgBouncer"
	print_info "فحص السجلات:"
	journalctl -u pgbouncer --no-pager -n 20
	exit 1
fi

# الخطوة 7: اختبار الاتصال
print_info "7️⃣ اختبار الاتصال..."

# اختبار الاتصال عبر pgbouncer
if psql -h 127.0.0.1 -p 6432 -U postgres -d crm_system -c "SELECT 1;" &>/dev/null; then
	print_status "اختبار الاتصال نجح"
else
	print_warning "فشل اختبار الاتصال - قد تحتاج لضبط كلمة المرور"
fi

# الخطوة 8: عرض معلومات الحالة
print_info "8️⃣ معلومات الحالة:"

echo ""
print_info "📊 حالة PgBouncer:"
systemctl status pgbouncer --no-pager -l

echo ""
print_info "🔌 معلومات الاتصال:"
echo "   - Host: 127.0.0.1"
echo "   - Port: 6432"
echo "   - Database: crm_system"
echo "   - User: postgres"

echo ""
print_info "📝 ملفات مهمة:"
echo "   - الإعدادات: /etc/pgbouncer/pgbouncer.ini"
echo "   - المستخدمين: /etc/pgbouncer/userlist.txt"
echo "   - السجلات: /var/log/postgresql/pgbouncer.log"

echo ""
print_info "🔧 أوامر مفيدة:"
echo "   - إعادة تشغيل: sudo systemctl restart pgbouncer"
echo "   - فحص الحالة: sudo systemctl status pgbouncer"
echo "   - فحص السجلات: sudo tail -f /var/log/postgresql/pgbouncer.log"
echo "   - اختبار الاتصال: psql -h 127.0.0.1 -p 6432 -U postgres -d crm_system"

print_status "🎉 تم تثبيت وإعداد PgBouncer بنجاح!"

print_warning "⚠️  الخطوة التالية: تحديث إعدادات Django لاستخدام PgBouncer"
print_info "   غير PORT في DATABASES من 5432 إلى 6432"
