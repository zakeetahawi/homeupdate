#!/bin/bash
# 🚀 تشغيل نظام الإنتاج كخدمة خلفية (Daemon)
# مع Cloudflare Tunnel + النسخ الاحتياطي + المراقبة الدورية
# للتشغيل التلقائي عند بدء النظام

set -e

# ═══════════════════════════════════════════════════════════════
# 🎨 الألوان والمتغيرات
# ═══════════════════════════════════════════════════════════════
RED='\033[0;31m'
GREEN='\033[0;32m'
WHITE='\033[1;37m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD_BLUE='\033[1;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/pids"
BACKUP_DIR="$PROJECT_DIR/media/backups"

# ═══════════════════════════════════════════════════════════════
# 📁 إنشاء المجلدات المطلوبة
# ═══════════════════════════════════════════════════════════════
mkdir -p "$LOGS_DIR"
mkdir -p "$PID_DIR"
mkdir -p "$BACKUP_DIR"

# ═══════════════════════════════════════════════════════════════
# 📝 دوال الطباعة مع التسجيل
# ═══════════════════════════════════════════════════════════════
log_file="$LOGS_DIR/production-daemon.log"

print_status() { 
    echo -e "${GREEN}$1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1" >> "$log_file"
}

print_error() { 
    echo -e "${RED}$1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1" >> "$log_file"
}

print_info() { 
    echo -e "${WHITE}$1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️  $1" >> "$log_file"
}

print_warning() { 
    echo -e "${YELLOW}$1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1" >> "$log_file"
}

print_tunnel() { 
    echo -e "${BLUE}$1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🌐 $1" >> "$log_file"
}

print_upload() { 
    echo -e "${PURPLE}$1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📤 $1" >> "$log_file"
}

# ═══════════════════════════════════════════════════════════════
# 🧹 تنظيف العمليات القديمة
# ═══════════════════════════════════════════════════════════════
cleanup_old_processes() {
    print_info "تنظيف العمليات القديمة..."
    
    # إيقاف Gunicorn
    pkill -9 -f "gunicorn.*crm.wsgi" 2>/dev/null || true
    
    # إيقاف Celery
    pkill -9 -f "celery.*worker.*crm" 2>/dev/null || true
    pkill -9 -f "celery.*beat.*crm" 2>/dev/null || true
    
    # إيقاف Cloudflared
    pkill -9 -f "cloudflared.*tunnel" 2>/dev/null || true
    
    # تنظيف ملفات PID القديمة
    rm -f "$PID_DIR"/*.pid 2>/dev/null || true
    rm -f /tmp/gunicorn.pid 2>/dev/null || true
    rm -f "$LOGS_DIR/celerybeat-schedule"* 2>/dev/null || true
    
    sleep 2
    print_status "تم التنظيف"
}

# ═══════════════════════════════════════════════════════════════
# 🔄 التحقق من المجلد والبيئة
# ═══════════════════════════════════════════════════════════════
if [ ! -d "$PROJECT_DIR" ]; then 
    print_error "مجلد المشروع غير موجود: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# تفعيل البيئة الافتراضية
if [ ! -d "$PROJECT_DIR/venv" ]; then
    print_error "البيئة الافتراضية غير موجودة في $PROJECT_DIR/venv"
    exit 1
fi

source "$PROJECT_DIR/venv/bin/activate"

# إعدادات الإنتاج
export DEBUG=False
export DJANGO_LOG_LEVEL=INFO
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export DJANGO_SETTINGS_MODULE=crm.settings

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🚀 نظام الخواجة - خدمة الإنتاج الخلفية${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# تنظيف العمليات القديمة
cleanup_old_processes

# ═══════════════════════════════════════════════════════════════
# 📊 تطبيق التحديثات وتجهيز قاعدة البيانات
# ═══════════════════════════════════════════════════════════════
print_info "تطبيق تحديثات قاعدة البيانات..."
python manage.py migrate --noinput >> "$log_file" 2>&1
print_status "تم تطبيق التحديثات"

# تنظيف الإشعارات القديمة
print_info "تنظيف الإشعارات القديمة..."
python manage.py cleanup_notifications >> "$log_file" 2>&1 || true
print_status "تم تنظيف الإشعارات"

# فحص قاعدة البيانات
print_info "فحص حالة قاعدة البيانات..."
python manage.py monitor_db --once >> "$log_file" 2>&1 || true
print_status "قاعدة البيانات جاهزة"

# تجميع الملفات الثابتة
print_info "تجميع الملفات الثابتة..."
python manage.py collectstatic --noinput --clear >> "$log_file" 2>&1
print_status "تم تجميع الملفات الثابتة"

# التحقق من المستخدمين
print_info "فحص المستخدمين..."
USER_COUNT=$(python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
import django
django.setup()
from accounts.models import User
print(User.objects.count())
" 2>/dev/null || echo "0")

if [ "$USER_COUNT" -eq 0 ]; then
    print_info "إنشاء مستخدم admin افتراضي..."
    python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
import django
django.setup()
from accounts.models import User
User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
print('تم إنشاء المستخدم admin/admin123')
" >> "$log_file" 2>&1
    print_status "تم إنشاء المستخدم admin/admin123"
else
    print_status "عدد المستخدمين: $USER_COUNT"
fi

# ═══════════════════════════════════════════════════════════════
# 🔴 تشغيل Redis
# ═══════════════════════════════════════════════════════════════
print_info "تشغيل Redis..."
if ! pgrep -x "redis-server\|valkey-server" > /dev/null; then
    if command -v valkey-server &> /dev/null; then
        valkey-server --daemonize yes \
            --port 6379 \
            --dir /tmp \
            --maxmemory 256mb \
            --maxmemory-policy allkeys-lru \
            --logfile "$LOGS_DIR/redis.log" \
            --pidfile "$PID_DIR/redis.pid"
    elif command -v redis-server &> /dev/null; then
        redis-server --daemonize yes \
            --port 6379 \
            --dir /tmp \
            --maxmemory 256mb \
            --maxmemory-policy allkeys-lru \
            --logfile "$LOGS_DIR/redis.log" \
            --pidfile "$PID_DIR/redis.pid"
    else
        print_warning "Redis غير مثبت - بعض الميزات قد لا تعمل"
    fi
    sleep 2
    print_status "Redis يعمل"
else
    print_status "Redis يعمل بالفعل"
fi

# ═══════════════════════════════════════════════════════════════
# 🥬 تشغيل Celery Worker
# ═══════════════════════════════════════════════════════════════
print_info "تشغيل Celery Worker..."

celery -A crm worker \
    --loglevel=info \
    --queues=celery,file_uploads \
    --pool=solo \
    --concurrency=1 \
    --max-memory-per-child=200000 \
    --time-limit=300 \
    --soft-time-limit=270 \
    --pidfile="$PID_DIR/celery-worker.pid" \
    --logfile="$LOGS_DIR/celery-worker.log" \
    --detach

sleep 3

if [ -f "$PID_DIR/celery-worker.pid" ] && kill -0 $(cat "$PID_DIR/celery-worker.pid") 2>/dev/null; then
    print_status "Celery Worker جاهز - PID: $(cat $PID_DIR/celery-worker.pid)"
    print_upload "نظام الرفع جاهز: العقود والمعاينات"
else
    print_warning "Celery Worker غير متاح"
fi

# ═══════════════════════════════════════════════════════════════
# ⏰ تشغيل Celery Beat (المهام المجدولة)
# ═══════════════════════════════════════════════════════════════
print_info "تشغيل Celery Beat للمهام المجدولة..."

celery -A crm beat \
    --loglevel=info \
    --pidfile="$PID_DIR/celery-beat.pid" \
    --logfile="$LOGS_DIR/celery-beat.log" \
    --schedule="$LOGS_DIR/celerybeat-schedule" \
    --detach

sleep 2

if [ -f "$PID_DIR/celery-beat.pid" ] && kill -0 $(cat "$PID_DIR/celery-beat.pid") 2>/dev/null; then
    print_status "Celery Beat جاهز - PID: $(cat $PID_DIR/celery-beat.pid)"
else
    print_warning "Celery Beat غير متاح"
fi

# ═══════════════════════════════════════════════════════════════
# 🌐 تشغيل Cloudflare Tunnel
# ═══════════════════════════════════════════════════════════════
print_info "تشغيل Cloudflare Tunnel..."

if [ -f "$PROJECT_DIR/cloudflared" ]; then
    chmod +x "$PROJECT_DIR/cloudflared"
    
    "$PROJECT_DIR/cloudflared" tunnel \
        --config "$PROJECT_DIR/cloudflared.yml" \
        run >> "$LOGS_DIR/cloudflared.log" 2>&1 &
    
    TUNNEL_PID=$!
    echo $TUNNEL_PID > "$PID_DIR/cloudflared.pid"
    
    sleep 5
    
    if kill -0 $TUNNEL_PID 2>/dev/null; then
        print_status "Cloudflare Tunnel جاهز - PID: $TUNNEL_PID"
        print_tunnel "يمكن الوصول للموقع عبر: https://elkhawaga.uk"
    else
        print_warning "فشل تشغيل Cloudflare Tunnel - سيعمل محلياً فقط"
        rm -f "$PID_DIR/cloudflared.pid"
    fi
else
    print_warning "ملف cloudflared غير موجود - سيعمل محلياً فقط"
fi

# ═══════════════════════════════════════════════════════════════
# 💾 تصدير إعدادات قاعدة البيانات للنسخ الاحتياطي
# ═══════════════════════════════════════════════════════════════
if [ -f "$PROJECT_DIR/crm/settings.py" ]; then
    eval $(python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','crm.settings')
import django
django.setup()
from django.conf import settings
db = settings.DATABASES['default']
print(f"export DB_NAME='{db.get('NAME','')}'")
print(f"export DB_USER='{db.get('USER','')}'")
print(f"export DB_HOST='{db.get('HOST','')}'")
print(f"export DB_PORT='{db.get('PORT','')}'")
print(f"export DB_PASSWORD='{db.get('PASSWORD','')}'")
PY
) 2>/dev/null || true
fi

# ═══════════════════════════════════════════════════════════════
# 📦 تشغيل خدمة النسخ الاحتياطي
# ═══════════════════════════════════════════════════════════════
print_info "تشغيل خدمة النسخ الاحتياطي..."

if [ -f "$PROJECT_DIR/لينكس/db-backup.sh" ]; then
    chmod +x "$PROJECT_DIR/لينكس/db-backup.sh"
    
    "$PROJECT_DIR/لينكس/db-backup.sh" >> "$LOGS_DIR/db-backup.log" 2>&1 &
    
    BACKUP_PID=$!
    echo $BACKUP_PID > "$PID_DIR/db-backup.pid"
    
    print_status "خدمة النسخ الاحتياطي جاهزة - PID: $BACKUP_PID"
    print_info "النسخ تُحفظ في: $BACKUP_DIR"
else
    print_warning "ملف النسخ الاحتياطي غير موجود"
fi

# ═══════════════════════════════════════════════════════════════
# 🌐 الحصول على IP
# ═══════════════════════════════════════════════════════════════
LOCAL_IP=$(ip addr show | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | cut -d/ -f1 | head -1)

# ═══════════════════════════════════════════════════════════════
# 🚀 تشغيل Gunicorn
# ═══════════════════════════════════════════════════════════════
print_info "تشغيل خادم الإنتاج Gunicorn..."

gunicorn crm.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --worker-connections 100 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 3 \
    --worker-tmp-dir /dev/shm \
    --access-logfile "$LOGS_DIR/gunicorn-access.log" \
    --error-logfile "$LOGS_DIR/gunicorn-error.log" \
    --log-level info \
    --pid "$PID_DIR/gunicorn.pid" \
    --daemon

sleep 3

# التحقق من التشغيل
if [ -f "$PID_DIR/gunicorn.pid" ] && kill -0 $(cat "$PID_DIR/gunicorn.pid") 2>/dev/null; then
    GUNICORN_PID=$(cat "$PID_DIR/gunicorn.pid")
    print_status "Gunicorn يعمل - PID: $GUNICORN_PID"
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 نظام الإنتاج يعمل في الخلفية بنجاح!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📍 محلي: http://localhost:8000${NC}"
    echo -e "${BLUE}📍 شبكة: http://$LOCAL_IP:8000${NC}"
    if [ -f "$PID_DIR/cloudflared.pid" ]; then
        echo -e "${BLUE}📍 خارجي: https://elkhawaga.uk${NC}"
    fi
    echo -e "${YELLOW}🔐 الدخول: admin / admin123${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}📊 السجلات:${NC}"
    echo -e "   • الأخطاء: $LOGS_DIR/gunicorn-error.log"
    echo -e "   • الوصول: $LOGS_DIR/gunicorn-access.log"
    echo -e "   • Celery: $LOGS_DIR/celery-worker.log"
    echo -e "   • Tunnel: $LOGS_DIR/cloudflared.log"
    echo -e "   • النسخ: $LOGS_DIR/db-backup.log"
    echo -e "   • النظام: $LOGS_DIR/production-daemon.log"
    echo ""
    echo -e "${BLUE}🔍 المراقبة:${NC}"
    echo -e "   tail -f $LOGS_DIR/gunicorn-error.log"
    echo -e "   tail -f $LOGS_DIR/production-daemon.log"
    echo ""
    echo -e "${BLUE}⏹️  الإيقاف:${NC}"
    echo -e "   sudo systemctl stop khawaja-production"
    echo -e "   # أو: $PROJECT_DIR/لينكس/stop-production.sh"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # حفظ معلومات التشغيل
    cat > "$PID_DIR/service_info.txt" <<EOF
═══════════════════════════════════════════════════════
  نظام الخواجة - معلومات الخدمة
═══════════════════════════════════════════════════════
تم البدء: $(date '+%Y-%m-%d %H:%M:%S')
الوضع: إنتاج (Production)

العمليات:
  • Gunicorn: PID $(cat $PID_DIR/gunicorn.pid 2>/dev/null || echo "غير متاح")
  • Celery Worker: PID $(cat $PID_DIR/celery-worker.pid 2>/dev/null || echo "غير متاح")
  • Celery Beat: PID $(cat $PID_DIR/celery-beat.pid 2>/dev/null || echo "غير متاح")
  • Cloudflared: PID $(cat $PID_DIR/cloudflared.pid 2>/dev/null || echo "غير متاح")
  • النسخ الاحتياطي: PID $(cat $PID_DIR/db-backup.pid 2>/dev/null || echo "غير متاح")

العناوين:
  • محلي: http://localhost:8000
  • شبكة: http://$LOCAL_IP:8000
  • خارجي: https://elkhawaga.uk

الدخول: admin / admin123
═══════════════════════════════════════════════════════
EOF

    # ═══════════════════════════════════════════════════════════════
    # 🔄 بدء حلقة المراقبة الدورية
    # ═══════════════════════════════════════════════════════════════
    print_info "بدء المراقبة الدورية..."
    
    # متغيرات التوقيت
    LAST_DB_CHECK=0
    LAST_NOTIFICATION_CLEANUP=0
    LAST_UPLOAD_CHECK=0
    LAST_TUNNEL_CHECK=0
    
    DB_CHECK_INTERVAL=300           # 5 دقائق
    NOTIFICATION_CLEANUP_INTERVAL=1800  # 30 دقيقة
    UPLOAD_CHECK_INTERVAL=600       # 10 دقائق
    TUNNEL_CHECK_INTERVAL=60        # دقيقة واحدة
    
    TUNNEL_STATUS="unknown"
    
    while true; do
        sleep 30
        CURRENT_TIME=$(date +%s)
        
        # ═══════════════════════════════════════════════════════════
        # فحص Gunicorn
        # ═══════════════════════════════════════════════════════════
        if [ -f "$PID_DIR/gunicorn.pid" ]; then
            if ! kill -0 $(cat "$PID_DIR/gunicorn.pid") 2>/dev/null; then
                print_error "Gunicorn توقف! إعادة التشغيل..."
                
                gunicorn crm.wsgi:application \
                    --bind 0.0.0.0:8000 \
                    --workers 2 \
                    --threads 4 \
                    --worker-class gthread \
                    --worker-connections 100 \
                    --max-requests 1000 \
                    --max-requests-jitter 100 \
                    --timeout 120 \
                    --graceful-timeout 30 \
                    --keep-alive 3 \
                    --worker-tmp-dir /dev/shm \
                    --access-logfile "$LOGS_DIR/gunicorn-access.log" \
                    --error-logfile "$LOGS_DIR/gunicorn-error.log" \
                    --log-level info \
                    --pid "$PID_DIR/gunicorn.pid" \
                    --daemon
                
                sleep 2
                if [ -f "$PID_DIR/gunicorn.pid" ]; then
                    print_status "تم إعادة تشغيل Gunicorn"
                fi
            fi
        fi
        
        # ═══════════════════════════════════════════════════════════
        # فحص Celery Worker
        # ═══════════════════════════════════════════════════════════
        if [ -f "$PID_DIR/celery-worker.pid" ]; then
            if ! kill -0 $(cat "$PID_DIR/celery-worker.pid") 2>/dev/null; then
                print_warning "Celery Worker توقف - إعادة التشغيل..."
                
                celery -A crm worker \
                    --loglevel=info \
                    --queues=celery,file_uploads \
                    --pool=solo \
                    --concurrency=1 \
                    --max-memory-per-child=200000 \
                    --time-limit=300 \
                    --soft-time-limit=270 \
                    --pidfile="$PID_DIR/celery-worker.pid" \
                    --logfile="$LOGS_DIR/celery-worker.log" \
                    --detach
                
                sleep 2
                print_status "تم إعادة تشغيل Celery Worker"
            fi
        fi
        
        # ═══════════════════════════════════════════════════════════
        # فحص Celery Beat
        # ═══════════════════════════════════════════════════════════
        if [ -f "$PID_DIR/celery-beat.pid" ]; then
            if ! kill -0 $(cat "$PID_DIR/celery-beat.pid") 2>/dev/null; then
                print_warning "Celery Beat توقف - إعادة التشغيل..."
                
                celery -A crm beat \
                    --loglevel=info \
                    --pidfile="$PID_DIR/celery-beat.pid" \
                    --logfile="$LOGS_DIR/celery-beat.log" \
                    --schedule="$LOGS_DIR/celerybeat-schedule" \
                    --detach
                
                sleep 2
                print_status "تم إعادة تشغيل Celery Beat"
            fi
        fi
        
        # ═══════════════════════════════════════════════════════════
        # فحص Cloudflare Tunnel
        # ═══════════════════════════════════════════════════════════
        if [ $((CURRENT_TIME - LAST_TUNNEL_CHECK)) -ge $TUNNEL_CHECK_INTERVAL ]; then
            if [ -f "$PID_DIR/cloudflared.pid" ]; then
                TUNNEL_PID=$(cat "$PID_DIR/cloudflared.pid")
                
                if ! kill -0 $TUNNEL_PID 2>/dev/null; then
                    print_warning "Cloudflare Tunnel توقف - إعادة التشغيل..."
                    
                    "$PROJECT_DIR/cloudflared" tunnel \
                        --config "$PROJECT_DIR/cloudflared.yml" \
                        run >> "$LOGS_DIR/cloudflared.log" 2>&1 &
                    
                    NEW_TUNNEL_PID=$!
                    echo $NEW_TUNNEL_PID > "$PID_DIR/cloudflared.pid"
                    
                    sleep 5
                    if kill -0 $NEW_TUNNEL_PID 2>/dev/null; then
                        print_status "تم إعادة تشغيل Cloudflare Tunnel"
                        TUNNEL_STATUS="connected"
                    fi
                else
                    # فحص الاتصال
                    if curl -s --max-time 10 https://elkhawaga.uk > /dev/null 2>&1; then
                        if [ "$TUNNEL_STATUS" != "connected" ]; then
                            TUNNEL_STATUS="connected"
                            print_tunnel "الجسر متصل - https://elkhawaga.uk"
                        fi
                    else
                        if [ "$TUNNEL_STATUS" != "disconnected" ]; then
                            TUNNEL_STATUS="disconnected"
                            print_warning "الجسر يعمل لكن الموقع غير متاح خارجياً"
                        fi
                    fi
                fi
            fi
            LAST_TUNNEL_CHECK=$CURRENT_TIME
        fi
        
        # ═══════════════════════════════════════════════════════════
        # فحص قاعدة البيانات (كل 5 دقائق)
        # ═══════════════════════════════════════════════════════════
        if [ $((CURRENT_TIME - LAST_DB_CHECK)) -ge $DB_CHECK_INTERVAL ]; then
            python manage.py monitor_db --once --quiet >> "$log_file" 2>&1 || true
            LAST_DB_CHECK=$CURRENT_TIME
        fi
        
        # ═══════════════════════════════════════════════════════════
        # تنظيف الإشعارات (كل 30 دقيقة)
        # ═══════════════════════════════════════════════════════════
        if [ $((CURRENT_TIME - LAST_NOTIFICATION_CLEANUP)) -ge $NOTIFICATION_CLEANUP_INTERVAL ]; then
            python manage.py cleanup_notifications >> "$log_file" 2>&1 || true
            LAST_NOTIFICATION_CLEANUP=$CURRENT_TIME
        fi
        
        # ═══════════════════════════════════════════════════════════
        # رفع الملفات المعلقة (كل 10 دقائق)
        # ═══════════════════════════════════════════════════════════
        if [ $((CURRENT_TIME - LAST_UPLOAD_CHECK)) -ge $UPLOAD_CHECK_INTERVAL ]; then
            if [ -f "$PROJECT_DIR/auto_upload_system.py" ]; then
                python "$PROJECT_DIR/auto_upload_system.py" single >> "$log_file" 2>&1 || true
            fi
            LAST_UPLOAD_CHECK=$CURRENT_TIME
        fi
    done
    
else
    print_error "فشل تشغيل Gunicorn!"
    print_error "راجع: $LOGS_DIR/gunicorn-error.log"
    exit 1
fi
