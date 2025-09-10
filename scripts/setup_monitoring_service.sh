#!/bin/bash

# سكريبت إعداد خدمة مراقبة النظام
# System monitoring service setup script

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

# التحقق من صلاحيات المستخدم
if [[ $EUID -ne 0 ]]; then
    print_error "يجب تشغيل هذا السكريبت كـ root (استخدم sudo)"
    exit 1
fi

PROJECT_DIR="/home/xhunterx/homeupdate"
VENV_DIR="$PROJECT_DIR/venv"
USER="xhunterx"

print_info "🔧 إعداد خدمة مراقبة النظام..."

# الخطوة 1: إنشاء خدمة مراقبة قاعدة البيانات
print_info "1️⃣ إنشاء خدمة مراقبة قاعدة البيانات..."

cat > /etc/systemd/system/homeupdate-db-monitor.service << EOF
[Unit]
Description=HomeUpdate Database Monitor
Documentation=https://github.com/homeupdate/monitoring
After=postgresql.service pgbouncer.service
Wants=postgresql.service pgbouncer.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin
Environment=DJANGO_SETTINGS_MODULE=crm.settings
ExecStart=$VENV_DIR/bin/python manage.py monitor_db --interval=30
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

# Restart settings
Restart=on-failure
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# Resource limits
LimitNOFILE=65536
MemoryMax=256M
CPUQuota=50%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=homeupdate-db-monitor

[Install]
WantedBy=multi-user.target
EOF

print_status "تم إنشاء خدمة مراقبة قاعدة البيانات"

# الخطوة 2: إنشاء خدمة تنظيف دورية
print_info "2️⃣ إنشاء خدمة التنظيف الدورية..."

cat > /etc/systemd/system/homeupdate-db-cleanup.service << EOF
[Unit]
Description=HomeUpdate Database Cleanup
Documentation=https://github.com/homeupdate/monitoring
After=postgresql.service pgbouncer.service
Wants=postgresql.service pgbouncer.service

[Service]
Type=oneshot
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin
Environment=DJANGO_SETTINGS_MODULE=crm.settings
ExecStart=$VENV_DIR/bin/python manage.py monitor_db --cleanup
StandardOutput=journal
StandardError=journal
SyslogIdentifier=homeupdate-db-cleanup
EOF

# إنشاء timer للتنظيف الدوري
cat > /etc/systemd/system/homeupdate-db-cleanup.timer << EOF
[Unit]
Description=HomeUpdate Database Cleanup Timer
Requires=homeupdate-db-cleanup.service

[Timer]
OnCalendar=*:0/10  # كل 10 دقائق
Persistent=true
AccuracySec=1min

[Install]
WantedBy=timers.target
EOF

print_status "تم إنشاء خدمة التنظيف الدورية"

# الخطوة 3: إنشاء خدمة تحسين قاعدة البيانات
print_info "3️⃣ إنشاء خدمة تحسين قاعدة البيانات..."

cat > /etc/systemd/system/homeupdate-db-optimize.service << EOF
[Unit]
Description=HomeUpdate Database Optimization
Documentation=https://github.com/homeupdate/monitoring
After=postgresql.service pgbouncer.service
Wants=postgresql.service pgbouncer.service

[Service]
Type=oneshot
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin
Environment=DJANGO_SETTINGS_MODULE=crm.settings
ExecStart=$VENV_DIR/bin/python manage.py optimize_db --analyze --vacuum
StandardOutput=journal
StandardError=journal
SyslogIdentifier=homeupdate-db-optimize
TimeoutStartSec=1800  # 30 دقيقة
EOF

# إنشاء timer للتحسين الدوري
cat > /etc/systemd/system/homeupdate-db-optimize.timer << EOF
[Unit]
Description=HomeUpdate Database Optimization Timer
Requires=homeupdate-db-optimize.service

[Timer]
OnCalendar=daily  # يومياً في منتصف الليل
Persistent=true
AccuracySec=1h

[Install]
WantedBy=timers.target
EOF

print_status "تم إنشاء خدمة تحسين قاعدة البيانات"

# الخطوة 4: إنشاء خدمة مراقبة النظام العامة
print_info "4️⃣ إنشاء خدمة مراقبة النظام العامة..."

cat > /etc/systemd/system/homeupdate-system-monitor.service << EOF
[Unit]
Description=HomeUpdate System Monitor
Documentation=https://github.com/homeupdate/monitoring
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin
ExecStart=$PROJECT_DIR/scripts/monitor-connections.sh monitor
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5

# Restart settings
Restart=on-failure
RestartSec=15
StartLimitInterval=60
StartLimitBurst=3

# Resource limits
LimitNOFILE=1024
MemoryMax=128M
CPUQuota=25%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=homeupdate-system-monitor

[Install]
WantedBy=multi-user.target
EOF

print_status "تم إنشاء خدمة مراقبة النظام العامة"

# الخطوة 5: إعادة تحميل systemd وتمكين الخدمات
print_info "5️⃣ تمكين الخدمات..."

systemctl daemon-reload

# تمكين الخدمات
systemctl enable homeupdate-db-monitor.service
systemctl enable homeupdate-db-cleanup.timer
systemctl enable homeupdate-db-optimize.timer
systemctl enable homeupdate-system-monitor.service

print_status "تم تمكين جميع الخدمات"

# الخطوة 6: بدء الخدمات
print_info "6️⃣ بدء الخدمات..."

# بدء خدمة مراقبة قاعدة البيانات
systemctl start homeupdate-db-monitor.service
sleep 2

# بدء timer التنظيف
systemctl start homeupdate-db-cleanup.timer
sleep 1

# بدء timer التحسين
systemctl start homeupdate-db-optimize.timer
sleep 1

# بدء خدمة مراقبة النظام
systemctl start homeupdate-system-monitor.service
sleep 2

print_status "تم بدء جميع الخدمات"

# الخطوة 7: فحص حالة الخدمات
print_info "7️⃣ فحص حالة الخدمات..."

echo ""
print_info "📊 حالة الخدمات:"

services=(
    "homeupdate-db-monitor.service"
    "homeupdate-db-cleanup.timer"
    "homeupdate-db-optimize.timer"
    "homeupdate-system-monitor.service"
)

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        print_status "$service: نشط"
    else
        print_error "$service: غير نشط"
        echo "   السجلات:"
        journalctl -u "$service" --no-pager -n 5
    fi
done

# الخطوة 8: إنشاء سكريبت إدارة الخدمات
print_info "8️⃣ إنشاء سكريبت إدارة الخدمات..."

cat > /usr/local/bin/homeupdate-services << 'EOF'
#!/bin/bash

# سكريبت إدارة خدمات HomeUpdate
# HomeUpdate services management script

SERVICES=(
    "homeupdate-db-monitor.service"
    "homeupdate-db-cleanup.timer"
    "homeupdate-db-optimize.timer"
    "homeupdate-system-monitor.service"
)

case "${1:-status}" in
    "start")
        echo "🚀 بدء جميع خدمات HomeUpdate..."
        for service in "${SERVICES[@]}"; do
            systemctl start "$service"
            echo "   ✅ $service"
        done
        ;;
        
    "stop")
        echo "⏹️  إيقاف جميع خدمات HomeUpdate..."
        for service in "${SERVICES[@]}"; do
            systemctl stop "$service"
            echo "   ⏹️  $service"
        done
        ;;
        
    "restart")
        echo "🔄 إعادة تشغيل جميع خدمات HomeUpdate..."
        for service in "${SERVICES[@]}"; do
            systemctl restart "$service"
            echo "   🔄 $service"
        done
        ;;
        
    "status")
        echo "📊 حالة خدمات HomeUpdate:"
        for service in "${SERVICES[@]}"; do
            if systemctl is-active --quiet "$service"; then
                echo "   ✅ $service: نشط"
            else
                echo "   ❌ $service: غير نشط"
            fi
        done
        ;;
        
    "logs")
        service="${2:-homeupdate-db-monitor.service}"
        echo "📝 سجلات $service:"
        journalctl -u "$service" -f
        ;;
        
    *)
        echo "الاستخدام: $0 [start|stop|restart|status|logs [service]]"
        echo ""
        echo "الخدمات المتاحة:"
        for service in "${SERVICES[@]}"; do
            echo "   - $service"
        done
        ;;
esac
EOF

chmod +x /usr/local/bin/homeupdate-services

print_status "تم إنشاء سكريبت إدارة الخدمات: /usr/local/bin/homeupdate-services"

# الخطوة 9: عرض معلومات الاستخدام
print_info "9️⃣ معلومات الاستخدام:"

echo ""
print_info "🔧 أوامر إدارة الخدمات:"
echo "   homeupdate-services start    - بدء جميع الخدمات"
echo "   homeupdate-services stop     - إيقاف جميع الخدمات"
echo "   homeupdate-services restart  - إعادة تشغيل جميع الخدمات"
echo "   homeupdate-services status   - فحص حالة الخدمات"
echo "   homeupdate-services logs     - عرض السجلات"

echo ""
print_info "📝 فحص السجلات:"
echo "   journalctl -u homeupdate-db-monitor -f"
echo "   journalctl -u homeupdate-system-monitor -f"

echo ""
print_info "⚙️  إدارة الخدمات الفردية:"
echo "   systemctl status homeupdate-db-monitor"
echo "   systemctl restart homeupdate-db-monitor"

print_status "🎉 تم إعداد جميع خدمات المراقبة بنجاح!"

print_warning "⚠️  تأكد من مراجعة السجلات للتأكد من عمل الخدمات بشكل صحيح"
