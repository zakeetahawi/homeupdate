#!/bin/bash
# 🛑 إيقاف نظام الإنتاج بشكل آمن
# يوقف جميع الخدمات: Gunicorn, Celery, Cloudflare Tunnel, النسخ الاحتياطي

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/pids"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🛑 إيقاف نظام الخواجة - الإنتاج${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# تسجيل الإيقاف
echo "[$(date '+%Y-%m-%d %H:%M:%S')] بدء إيقاف النظام..." >> "$LOGS_DIR/production-daemon.log"

# ═══════════════════════════════════════════════════════════════
# إيقاف Gunicorn
# ═══════════════════════════════════════════════════════════════
echo -e "${YELLOW}⏳ إيقاف Gunicorn...${NC}"
if [ -f "$PID_DIR/gunicorn.pid" ]; then
    GUNICORN_PID=$(cat "$PID_DIR/gunicorn.pid")
    if kill -0 $GUNICORN_PID 2>/dev/null; then
        kill -TERM $GUNICORN_PID
        sleep 3
        # إجبار الإيقاف إذا لم يتوقف
        kill -0 $GUNICORN_PID 2>/dev/null && kill -9 $GUNICORN_PID
        echo -e "${GREEN}✅ تم إيقاف Gunicorn (PID: $GUNICORN_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  Gunicorn غير يعمل${NC}"
    fi
    rm -f "$PID_DIR/gunicorn.pid"
else
    # محاولة إيقاف بالاسم
    pkill -TERM -f "gunicorn.*crm.wsgi" 2>/dev/null || true
    sleep 2
    pkill -9 -f "gunicorn.*crm.wsgi" 2>/dev/null || true
    echo -e "${GREEN}✅ تم إيقاف Gunicorn${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# إيقاف Celery Worker
# ═══════════════════════════════════════════════════════════════
echo -e "${YELLOW}⏳ إيقاف Celery Worker...${NC}"
if [ -f "$PID_DIR/celery-worker.pid" ]; then
    CELERY_PID=$(cat "$PID_DIR/celery-worker.pid")
    if kill -0 $CELERY_PID 2>/dev/null; then
        kill -TERM $CELERY_PID
        sleep 2
        kill -0 $CELERY_PID 2>/dev/null && kill -9 $CELERY_PID
        echo -e "${GREEN}✅ تم إيقاف Celery Worker (PID: $CELERY_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  Celery Worker غير يعمل${NC}"
    fi
    rm -f "$PID_DIR/celery-worker.pid"
else
    pkill -9 -f "celery.*worker.*crm" 2>/dev/null || true
    echo -e "${GREEN}✅ تم إيقاف Celery Worker${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# إيقاف Celery Beat
# ═══════════════════════════════════════════════════════════════
echo -e "${YELLOW}⏳ إيقاف Celery Beat...${NC}"
if [ -f "$PID_DIR/celery-beat.pid" ]; then
    BEAT_PID=$(cat "$PID_DIR/celery-beat.pid")
    if kill -0 $BEAT_PID 2>/dev/null; then
        kill -TERM $BEAT_PID
        sleep 2
        kill -0 $BEAT_PID 2>/dev/null && kill -9 $BEAT_PID
        echo -e "${GREEN}✅ تم إيقاف Celery Beat (PID: $BEAT_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  Celery Beat غير يعمل${NC}"
    fi
    rm -f "$PID_DIR/celery-beat.pid"
    rm -f "$LOGS_DIR/celerybeat-schedule"*
else
    pkill -9 -f "celery.*beat.*crm" 2>/dev/null || true
    echo -e "${GREEN}✅ تم إيقاف Celery Beat${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# إيقاف Cloudflare Tunnel
# ═══════════════════════════════════════════════════════════════
echo -e "${YELLOW}⏳ إيقاف Cloudflare Tunnel...${NC}"
if [ -f "$PID_DIR/cloudflared.pid" ]; then
    TUNNEL_PID=$(cat "$PID_DIR/cloudflared.pid")
    if kill -0 $TUNNEL_PID 2>/dev/null; then
        kill -TERM $TUNNEL_PID
        sleep 2
        kill -0 $TUNNEL_PID 2>/dev/null && kill -9 $TUNNEL_PID
        echo -e "${GREEN}✅ تم إيقاف Cloudflare Tunnel (PID: $TUNNEL_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  Cloudflare Tunnel غير يعمل${NC}"
    fi
    rm -f "$PID_DIR/cloudflared.pid"
else
    pkill -9 -f "cloudflared.*tunnel" 2>/dev/null || true
    echo -e "${GREEN}✅ تم إيقاف Cloudflare Tunnel${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# إيقاف خدمة النسخ الاحتياطي
# ═══════════════════════════════════════════════════════════════
echo -e "${YELLOW}⏳ إيقاف خدمة النسخ الاحتياطي...${NC}"
if [ -f "$PID_DIR/db-backup.pid" ]; then
    BACKUP_PID=$(cat "$PID_DIR/db-backup.pid")
    if kill -0 $BACKUP_PID 2>/dev/null; then
        kill -TERM $BACKUP_PID
        sleep 1
        kill -0 $BACKUP_PID 2>/dev/null && kill -9 $BACKUP_PID
        echo -e "${GREEN}✅ تم إيقاف خدمة النسخ الاحتياطي (PID: $BACKUP_PID)${NC}"
    else
        echo -e "${YELLOW}⚠️  خدمة النسخ الاحتياطي غير تعمل${NC}"
    fi
    rm -f "$PID_DIR/db-backup.pid"
else
    echo -e "${YELLOW}⚠️  خدمة النسخ الاحتياطي غير تعمل${NC}"
fi

# ═══════════════════════════════════════════════════════════════
# تنظيف ملفات PID المتبقية
# ═══════════════════════════════════════════════════════════════
echo -e "${YELLOW}⏳ تنظيف الملفات المؤقتة...${NC}"
rm -f "$PID_DIR"/*.pid 2>/dev/null || true
rm -f /tmp/gunicorn.pid 2>/dev/null || true
rm -f "$PID_DIR/service_info.txt" 2>/dev/null || true
echo -e "${GREEN}✅ تم التنظيف${NC}"

# تسجيل الإيقاف
echo "[$(date '+%Y-%m-%d %H:%M:%S')] تم إيقاف النظام بنجاح" >> "$LOGS_DIR/production-daemon.log"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ تم إيقاف جميع الخدمات بنجاح${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}لإعادة التشغيل:${NC}"
echo -e "   sudo systemctl start khawaja-production"
echo -e "   # أو: $PROJECT_DIR/لينكس/run-production-daemon.sh"
echo ""

exit 0
