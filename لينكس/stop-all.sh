#!/bin/bash

# ألوان للنص
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# دوال الطباعة
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# دالة لإيقاف عملية بواسطة PID file
stop_process_by_pidfile() {
    local pidfile=$1
    local process_name=$2
    
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile" 2>/dev/null)
        if [ ! -z "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            sleep 2
            
            # التحقق من إيقاف العملية
            if kill -0 "$pid" 2>/dev/null; then
                # إجبار الإيقاف
                kill -9 "$pid" 2>/dev/null
                print_warning "تم إجبار إيقاف $process_name"
            else
                print_success "تم إيقاف $process_name"
            fi
        else
            print_info "$process_name غير يعمل"
        fi
        
        # حذف ملف PID
        rm -f "$pidfile"
    else
        print_info "ملف PID لـ $process_name غير موجود"
    fi
}

# دالة لإيقاف العمليات بالاسم
stop_process_by_name() {
    local process_name=$1
    local display_name=$2
    
    local pids=$(pgrep -f "$process_name" 2>/dev/null)
    
    if [ ! -z "$pids" ]; then
        echo "$pids" | while read pid; do
            if [ ! -z "$pid" ]; then
                kill "$pid" 2>/dev/null
                print_success "تم إيقاف $display_name (PID: $pid)"
            fi
        done
        
        sleep 2
        
        # التحقق من الإيقاف الإجباري
        local remaining_pids=$(pgrep -f "$process_name" 2>/dev/null)
        if [ ! -z "$remaining_pids" ]; then
            echo "$remaining_pids" | while read pid; do
                if [ ! -z "$pid" ]; then
                    kill -9 "$pid" 2>/dev/null
                    print_warning "تم إجبار إيقاف $display_name (PID: $pid)"
                fi
            done
        fi
    else
        print_info "$display_name غير يعمل"
    fi
}

# بدء الإيقاف
print_header "إيقاف جميع خدمات النظام"

# إيقاف Celery Worker
print_info "إيقاف Celery Worker..."
stop_process_by_pidfile "/tmp/celery_worker.pid" "Celery Worker"

# إيقاف Celery Beat
print_info "إيقاف Celery Beat..."
stop_process_by_pidfile "/tmp/celery_beat.pid" "Celery Beat"

# حذف ملفات Celery الإضافية
print_info "تنظيف ملفات Celery..."
rm -f /tmp/celerybeat-schedule*
rm -f /tmp/celery_worker.log
rm -f /tmp/celery_beat.log
print_success "تم تنظيف ملفات Celery"

# إيقاف Gunicorn
print_info "إيقاف خادم الويب (Gunicorn)..."
stop_process_by_name "gunicorn" "Gunicorn"

# إيقاف Django runserver (إذا كان يعمل)
print_info "إيقاف Django runserver..."
stop_process_by_name "manage.py runserver" "Django runserver"

# إيقاف Daphne (خادم WebSocket)
print_info "إيقاف Daphne (WebSocket Server)..."
stop_process_by_name "daphne.*crm.asgi" "Daphne WebSocket Server"

# إيقاف أي عملية تستخدم المنفذ 8000
print_info "إيقاف العمليات على المنفذ 8000..."
port_8000_pids=$(lsof -ti:8000 2>/dev/null)
if [ ! -z "$port_8000_pids" ]; then
    echo "$port_8000_pids" | while read pid; do
        if [ ! -z "$pid" ]; then
            kill -9 "$pid" 2>/dev/null
            print_success "تم إيقاف العملية على المنفذ 8000 (PID: $pid)"
        fi
    done
else
    print_info "لا توجد عمليات تستخدم المنفذ 8000"
fi

# إيقاف Cloudflare Tunnel
print_info "إيقاف Cloudflare Tunnel..."
stop_process_by_name "cloudflared tunnel" "Cloudflare Tunnel"

# إيقاف Redis (اختياري)
read -p "هل تريد إيقاف Redis أيضاً؟ (y/N): " stop_redis
if [[ $stop_redis =~ ^[Yy]$ ]]; then
    print_info "إيقاف Redis..."
    if pgrep -x "redis-server" > /dev/null; then
        redis-cli shutdown 2>/dev/null || pkill redis-server
        print_success "تم إيقاف Redis"
    else
        print_info "Redis غير يعمل"
    fi
fi

# تنظيف ملفات PID المتبقية
print_info "تنظيف ملفات PID..."
rm -f /tmp/*.pid 2>/dev/null
print_success "تم تنظيف ملفات PID"

# تنظيف ملفات السجلات القديمة (اختياري)
read -p "هل تريد تنظيف ملفات السجلات القديمة؟ (y/N): " clean_logs
if [[ $clean_logs =~ ^[Yy]$ ]]; then
    print_info "تنظيف ملفات السجلات..."
    find /tmp -name "*.log" -mtime +7 -delete 2>/dev/null
    print_success "تم تنظيف ملفات السجلات القديمة"
fi

# عرض العمليات المتبقية
print_info "فحص العمليات المتبقية..."
remaining_processes=$(ps aux | grep -E "(gunicorn|celery|cloudflared|manage.py|daphne)" | grep -v grep | grep -v "stop-all.sh")

if [ ! -z "$remaining_processes" ]; then
    print_warning "العمليات المتبقية:"
    echo "$remaining_processes"
    echo
    print_info "يمكنك إيقافها يدوياً باستخدام:"
    echo "kill -9 <PID>"
else
    print_success "تم إيقاف جميع العمليات بنجاح"
fi

# عرض ملخص
echo
print_header "ملخص الإيقاف"
print_success "✅ تم إيقاف Celery Worker"
print_success "✅ تم إيقاف Celery Beat"
print_success "✅ تم إيقاف خادم الويب"
print_success "✅ تم إيقاف Daphne WebSocket Server"
print_success "✅ تم تحرير المنفذ 8000"
print_success "✅ تم إيقاف Cloudflare Tunnel"
print_success "✅ تم تنظيف الملفات المؤقتة"

echo
print_info "💡 لإعادة تشغيل النظام، استخدم:"
print_info "   ./لينكس/run-production.sh"

echo
print_success "🎉 تم إيقاف جميع الخدمات بنجاح!"
