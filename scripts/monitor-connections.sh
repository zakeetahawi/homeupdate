#!/bin/bash

# سكريبت مراقبة اتصالات قاعدة البيانات
# Database connections monitoring script

# ألوان للعرض
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

LOG_FILE="/tmp/db_connections_monitor.log"
ALERT_THRESHOLD=70
CRITICAL_THRESHOLD=90

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

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

check_connections() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # جلب إحصائيات الاتصالات
    local stats=$(sudo -u postgres psql -t -c "
        SELECT 
            count(*) as total,
            count(*) FILTER (WHERE state = 'active') as active,
            count(*) FILTER (WHERE state = 'idle') as idle,
            count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
        FROM pg_stat_activity 
        WHERE datname = 'crm_system';
    " 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        local total=$(echo $stats | awk '{print $1}')
        local active=$(echo $stats | awk '{print $2}')
        local idle=$(echo $stats | awk '{print $3}')
        local idle_in_transaction=$(echo $stats | awk '{print $4}')
        
        # تسجيل الإحصائيات
        log_message "Total: $total, Active: $active, Idle: $idle, Idle in Transaction: $idle_in_transaction"
        
        # فحص التحذيرات
        if [ "$total" -gt "$CRITICAL_THRESHOLD" ]; then
            print_error "CRITICAL: $total connections (threshold: $CRITICAL_THRESHOLD)"
            log_message "CRITICAL ALERT: $total connections"
            
            # تنظيف طوارئ
            cleanup_emergency_connections
            
        elif [ "$total" -gt "$ALERT_THRESHOLD" ]; then
            print_warning "WARNING: $total connections (threshold: $ALERT_THRESHOLD)"
            log_message "WARNING: $total connections"
            
            # تنظيف الاتصالات الخاملة
            cleanup_idle_connections
            
        else
            print_status "OK: $total connections"
        fi
        
        # عرض الإحصائيات
        echo "[$timestamp] Total: $total | Active: $active | Idle: $idle | Idle in TX: $idle_in_transaction"
        
    else
        print_error "Failed to check database connections"
        log_message "ERROR: Failed to check database connections"
    fi
}

cleanup_idle_connections() {
    print_info "تنظيف الاتصالات الخاملة..."
    
    local killed=$(sudo -u postgres psql -t -c "
        SELECT count(pg_terminate_backend(pid))
        FROM pg_stat_activity 
        WHERE datname = 'crm_system' 
        AND state = 'idle'
        AND state_change < now() - interval '5 minutes'
        AND pid != pg_backend_pid();
    " 2>/dev/null || echo "0")
    
    if [ "$killed" -gt 0 ]; then
        print_status "تم قتل $killed اتصال خامل"
        log_message "Killed $killed idle connections"
    fi
}

cleanup_emergency_connections() {
    print_error "تنظيف طوارئ للاتصالات!"
    
    # قتل جميع الاتصالات الخاملة
    local killed_idle=$(sudo -u postgres psql -t -c "
        SELECT count(pg_terminate_backend(pid))
        FROM pg_stat_activity 
        WHERE datname = 'crm_system' 
        AND state = 'idle'
        AND pid != pg_backend_pid();
    " 2>/dev/null || echo "0")
    
    # قتل الاتصالات المعلقة في المعاملات
    local killed_tx=$(sudo -u postgres psql -t -c "
        SELECT count(pg_terminate_backend(pid))
        FROM pg_stat_activity 
        WHERE datname = 'crm_system' 
        AND state = 'idle in transaction'
        AND state_change < now() - interval '1 minute'
        AND pid != pg_backend_pid();
    " 2>/dev/null || echo "0")
    
    print_status "تنظيف طوارئ: قتل $killed_idle خامل + $killed_tx معلق"
    log_message "EMERGENCY CLEANUP: Killed $killed_idle idle + $killed_tx idle_in_transaction"
}

show_top_connections() {
    print_info "أكثر الاتصالات استهلاكاً:"
    sudo -u postgres psql -c "
        SELECT 
            application_name,
            client_addr,
            state,
            query_start,
            state_change,
            substring(query, 1, 50) as query_preview
        FROM pg_stat_activity 
        WHERE datname = 'crm_system'
        AND pid != pg_backend_pid()
        ORDER BY state_change DESC
        LIMIT 10;
    " 2>/dev/null
}

# الدالة الرئيسية
main() {
    case "${1:-monitor}" in
        "monitor")
            print_info "🔍 بدء مراقبة اتصالات قاعدة البيانات..."
            print_info "📊 حد التحذير: $ALERT_THRESHOLD | حد الخطر: $CRITICAL_THRESHOLD"
            print_info "📝 ملف السجل: $LOG_FILE"
            print_info "⏹️  للإيقاف: Ctrl+C"
            echo ""
            
            # مراقبة مستمرة
            while true; do
                check_connections
                sleep 30
            done
            ;;
            
        "check")
            check_connections
            ;;
            
        "cleanup")
            cleanup_idle_connections
            ;;
            
        "emergency")
            cleanup_emergency_connections
            ;;
            
        "top")
            show_top_connections
            ;;
            
        "log")
            if [ -f "$LOG_FILE" ]; then
                tail -n 50 "$LOG_FILE"
            else
                print_warning "ملف السجل غير موجود"
            fi
            ;;
            
        *)
            echo "الاستخدام: $0 [monitor|check|cleanup|emergency|top|log]"
            echo ""
            echo "الأوامر:"
            echo "  monitor   - مراقبة مستمرة (افتراضي)"
            echo "  check     - فحص واحد"
            echo "  cleanup   - تنظيف الاتصالات الخاملة"
            echo "  emergency - تنظيف طوارئ"
            echo "  top       - عرض أكثر الاتصالات استهلاكاً"
            echo "  log       - عرض آخر 50 سطر من السجل"
            ;;
    esac
}

# تشغيل الدالة الرئيسية
main "$@"
