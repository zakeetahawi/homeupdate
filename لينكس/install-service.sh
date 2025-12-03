#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# 🔧 تثبيت خدمة الإنتاج - نظام الخواجة
# ═══════════════════════════════════════════════════════════════════════════
# يقوم بتثبيت الخدمة وتفعيل البدء التلقائي
# استخدم: sudo ./install-service.sh
# ═══════════════════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/home/zakee/homeupdate"
SCRIPT_DIR="$PROJECT_DIR/لينكس"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🔧 تثبيت خدمة الإنتاج - نظام الخواجة${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# التحقق من صلاحيات root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ يجب تشغيل هذا السكريبت بصلاحيات root${NC}"
    echo -e "${YELLOW}استخدم: sudo $0${NC}"
    exit 1
fi

# التحقق من وجود الملفات المطلوبة
echo -e "${YELLOW}⏳ التحقق من الملفات المطلوبة...${NC}"

if [ ! -f "$SCRIPT_DIR/khawaja-production.service" ]; then
    echo -e "${RED}❌ ملف الخدمة غير موجود: $SCRIPT_DIR/khawaja-production.service${NC}"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/run-production-daemon.sh" ]; then
    echo -e "${RED}❌ ملف التشغيل غير موجود: $SCRIPT_DIR/run-production-daemon.sh${NC}"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/stop-production.sh" ]; then
    echo -e "${RED}❌ ملف الإيقاف غير موجود: $SCRIPT_DIR/stop-production.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✅ جميع الملفات موجودة${NC}"

# إعطاء صلاحيات التنفيذ
echo -e "${YELLOW}⏳ إعطاء صلاحيات التنفيذ...${NC}"
chmod +x "$SCRIPT_DIR/run-production-daemon.sh"
chmod +x "$SCRIPT_DIR/stop-production.sh"
chmod +x "$SCRIPT_DIR/run-production.sh" 2>/dev/null || true
echo -e "${GREEN}✅ تم إعطاء الصلاحيات${NC}"

# إنشاء المجلدات المطلوبة
echo -e "${YELLOW}⏳ إنشاء المجلدات المطلوبة...${NC}"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/pids"
mkdir -p "$PROJECT_DIR/media/backups"
chown -R zakee:zakee "$PROJECT_DIR/logs"
chown -R zakee:zakee "$PROJECT_DIR/pids"
chown -R zakee:zakee "$PROJECT_DIR/media"
echo -e "${GREEN}✅ تم إنشاء المجلدات${NC}"

# إيقاف الخدمة القديمة إذا كانت موجودة
echo -e "${YELLOW}⏳ إيقاف الخدمات القديمة...${NC}"
systemctl stop khawaja-production 2>/dev/null || true
systemctl stop khawaja-system 2>/dev/null || true
systemctl disable khawaja-production 2>/dev/null || true
systemctl disable khawaja-system 2>/dev/null || true
echo -e "${GREEN}✅ تم إيقاف الخدمات القديمة${NC}"

# نسخ ملف الخدمة
echo -e "${YELLOW}⏳ نسخ ملف الخدمة...${NC}"
cp "$SCRIPT_DIR/khawaja-production.service" /etc/systemd/system/
echo -e "${GREEN}✅ تم نسخ ملف الخدمة${NC}"

# إعادة تحميل systemd
echo -e "${YELLOW}⏳ إعادة تحميل systemd...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✅ تم إعادة التحميل${NC}"

# تفعيل البدء التلقائي
echo -e "${YELLOW}⏳ تفعيل البدء التلقائي...${NC}"
systemctl enable khawaja-production
echo -e "${GREEN}✅ تم تفعيل البدء التلقائي${NC}"

# إعداد Log Rotation
echo -e "${YELLOW}⏳ إعداد Log Rotation...${NC}"
cat > /etc/logrotate.d/khawaja-production <<'EOF'
/home/zakee/homeupdate/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 zakee zakee
    postrotate
        if [ -f /home/zakee/homeupdate/pids/gunicorn.pid ]; then
            kill -USR1 $(cat /home/zakee/homeupdate/pids/gunicorn.pid) 2>/dev/null || true
        fi
    endscript
    maxsize 100M
    minsize 10M
}

/home/zakee/homeupdate/logs/systemd-*.log {
    weekly
    rotate 8
    compress
    delaycompress
    missingok
    notifempty
    create 0644 zakee zakee
    maxsize 50M
}
EOF
echo -e "${GREEN}✅ تم إعداد Log Rotation${NC}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 تم تثبيت الخدمة بنجاح!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}الأوامر المتاحة:${NC}"
echo ""
echo -e "${YELLOW}▶️  بدء الخدمة:${NC}"
echo "   sudo systemctl start khawaja-production"
echo ""
echo -e "${YELLOW}⏹️  إيقاف الخدمة:${NC}"
echo "   sudo systemctl stop khawaja-production"
echo ""
echo -e "${YELLOW}🔄 إعادة التشغيل:${NC}"
echo "   sudo systemctl restart khawaja-production"
echo ""
echo -e "${YELLOW}📊 حالة الخدمة:${NC}"
echo "   sudo systemctl status khawaja-production"
echo ""
echo -e "${YELLOW}📋 السجلات:${NC}"
echo "   sudo journalctl -u khawaja-production -f"
echo "   tail -f $PROJECT_DIR/logs/production-daemon.log"
echo ""
echo -e "${YELLOW}🚫 تعطيل البدء التلقائي:${NC}"
echo "   sudo systemctl disable khawaja-production"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# سؤال المستخدم عن بدء الخدمة الآن
read -p "هل تريد بدء الخدمة الآن؟ (y/n): " START_NOW

if [[ "$START_NOW" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}⏳ بدء الخدمة...${NC}"
    systemctl start khawaja-production
    sleep 5
    
    if systemctl is-active --quiet khawaja-production; then
        echo -e "${GREEN}✅ الخدمة تعمل بنجاح!${NC}"
        echo ""
        systemctl status khawaja-production --no-pager
    else
        echo -e "${RED}❌ فشل بدء الخدمة${NC}"
        echo -e "${YELLOW}راجع السجلات:${NC}"
        echo "   sudo journalctl -u khawaja-production -n 50"
    fi
else
    echo ""
    echo -e "${BLUE}يمكنك بدء الخدمة لاحقاً باستخدام:${NC}"
    echo "   sudo systemctl start khawaja-production"
fi

echo ""
