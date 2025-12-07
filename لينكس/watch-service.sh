#!/bin/bash
# 📊 أداة مراقبة حية لجميع خدمات النظام

PROJECT_DIR="/home/zakee/homeupdate"
LOGS_DIR="$PROJECT_DIR/logs"
PIDS_DIR="$LOGS_DIR/pids"

# الألوان
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # بدون لون
BOLD='\033[1m'

# رموز
CHECK="✅"
CROSS="❌"
WARN="⚠️"
INFO="ℹ️"
ROCKET="🚀"
GEAR="⚙️"
DB="💾"
WEB="🌐"
CLOCK="⏰"

clear_screen() {
    clear
}

print_header() {
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║${NC}  ${ROCKET}  ${BOLD}مراقبة خدمات نظام HomeUpdate${NC}                          ${BOLD}${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_service() {
    local service_name=$1
    local pid_file=$2
    local icon=$3
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if kill -0 $pid 2>/dev/null; then
            local cpu=$(ps -p $pid -o %cpu= 2>/dev/null | tr -d ' ')
            local mem=$(ps -p $pid -o %mem= 2>/dev/null | tr -d ' ')
            local uptime=$(ps -p $pid -o etime= 2>/dev/null | tr -d ' ')
            echo -e "${icon}  ${BOLD}${service_name}:${NC} ${GREEN}${CHECK} يعمل${NC} (PID: ${pid})"
            echo -e "   └─ CPU: ${cpu}% | RAM: ${mem}% | مدة التشغيل: ${uptime}"
            return 0
        else
            echo -e "${icon}  ${BOLD}${service_name}:${NC} ${RED}${CROSS} متوقف${NC} (PID غير نشط)"
            return 1
        fi
    else
        echo -e "${icon}  ${BOLD}${service_name}:${NC} ${RED}${CROSS} متوقف${NC} (لا يوجد PID)"
        return 1
    fi
}

check_port() {
    local port=$1
    if lsof -i:$port -sTCP:LISTEN >/dev/null 2>&1; then
        echo -e "   └─ ${WEB} المنفذ ${port}: ${GREEN}${CHECK} مفتوح${NC}"
        return 0
    else
        echo -e "   └─ ${WEB} المنفذ ${port}: ${RED}${CROSS} مغلق${NC}"
        return 1
    fi
}

check_database() {
    if pg_isready -q 2>/dev/null; then
        echo -e "${DB}  ${BOLD}قاعدة البيانات:${NC} ${GREEN}${CHECK} متصلة${NC}"
        # عدد الاتصالات النشطة
        local connections=$(psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | tr -d ' ')
        if [ ! -z "$connections" ]; then
            echo -e "   └─ الاتصالات النشطة: ${connections}"
        fi
        return 0
    else
        echo -e "${DB}  ${BOLD}قاعدة البيانات:${NC} ${RED}${CROSS} غير متاحة${NC}"
        return 1
    fi
}

check_redis() {
    if pgrep -x redis-server >/dev/null; then
        echo -e "🔴  ${BOLD}Redis:${NC} ${GREEN}${CHECK} يعمل${NC}"
        return 0
    else
        echo -e "🔴  ${BOLD}Redis:${NC} ${RED}${CROSS} متوقف${NC}"
        return 1
    fi
}

show_recent_logs() {
    echo ""
    echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}📝 آخر 10 تسجيلات من monitor.log:${NC}"
    echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if [ -f "$LOGS_DIR/monitor.log" ]; then
        tail -10 "$LOGS_DIR/monitor.log" | while IFS= read -r line; do
            if [[ $line == *"ERROR"* ]] || [[ $line == *"❌"* ]]; then
                echo -e "${RED}${line}${NC}"
            elif [[ $line == *"SUCCESS"* ]] || [[ $line == *"✅"* ]]; then
                echo -e "${GREEN}${line}${NC}"
            elif [[ $line == *"WARNING"* ]] || [[ $line == *"⚠️"* ]]; then
                echo -e "${YELLOW}${line}${NC}"
            else
                echo -e "${line}"
            fi
        done
    else
        echo -e "${YELLOW}${WARN} ملف monitor.log غير موجود بعد${NC}"
    fi
}

show_log_sizes() {
    echo ""
    echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}📂 أحجام ملفات السجلات:${NC}"
    echo -e "${BOLD}${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    cd "$LOGS_DIR"
    for log in gunicorn_access.log gunicorn_error.log celery_worker.log celery_beat.log monitor.log startup.log; do
        if [ -f "$log" ]; then
            size=$(du -h "$log" | cut -f1)
            echo -e "   📄 ${log}: ${size}"
        fi
    done
}

count_processes() {
    local gunicorn_count=$(pgrep -f "gunicorn crm.wsgi" | wc -l)
    local celery_worker_count=$(pgrep -f "celery.*worker" | wc -l)
    local celery_beat_count=$(pgrep -f "celery.*beat" | wc -l)
    local cloudflared_count=$(pgrep -f cloudflared | wc -l)
    
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}📊 عدد العمليات الجارية:${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if [ $gunicorn_count -gt 0 ]; then
        echo -e "   🚀 Gunicorn: ${GREEN}${gunicorn_count}${NC} عملية"
    else
        echo -e "   🚀 Gunicorn: ${RED}0${NC} عملية"
    fi
    
    if [ $celery_worker_count -gt 0 ]; then
        echo -e "   ⚙️  Celery Worker: ${GREEN}${celery_worker_count}${NC} عملية"
    else
        echo -e "   ⚙️  Celery Worker: ${RED}0${NC} عملية"
    fi
    
    if [ $celery_beat_count -gt 0 ]; then
        echo -e "   ⏰ Celery Beat: ${GREEN}${celery_beat_count}${NC} عملية"
    else
        echo -e "   ⏰ Celery Beat: ${RED}0${NC} عملية"
    fi
    
    if [ $cloudflared_count -gt 0 ]; then
        if [ $cloudflared_count -gt 5 ]; then
            echo -e "   🌐 Cloudflared: ${YELLOW}${cloudflared_count}${NC} عملية ${WARN} (كثير جداً!)"
        else
            echo -e "   🌐 Cloudflared: ${GREEN}${cloudflared_count}${NC} عملية"
        fi
    else
        echo -e "   🌐 Cloudflared: ${RED}0${NC} عملية"
    fi
}

# الحلقة الرئيسية
while true; do
    clear_screen
    print_header
    
    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}🔍 حالة الخدمات:${NC}"
    echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # فحص الخدمات
    check_service "Gunicorn (Web Server)" "$PIDS_DIR/gunicorn.pid" "🚀"
    check_port 8000
    echo ""
    
    check_service "Celery Worker" "$PIDS_DIR/celery_worker.pid" "⚙️"
    echo ""
    
    check_service "Celery Beat" "$PIDS_DIR/celery_beat.pid" "⏰"
    echo ""
    
    check_service "Cloudflare Tunnel" "$PIDS_DIR/cloudflared.pid" "🌐"
    echo ""
    
    check_service "Monitor Service" "$PIDS_DIR/monitor.pid" "👁️"
    echo ""
    
    check_database
    echo ""
    
    check_redis
    
    count_processes
    show_log_sizes
    show_recent_logs
    
    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}⏱️  التحديث التالي بعد 5 ثوانٍ... (Ctrl+C للخروج)${NC}"
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    sleep 5
done
