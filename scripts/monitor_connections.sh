#!/bin/bash

# سكريبت مراقبة اتصالات قاعدة البيانات

echo "📊 مراقبة اتصالات قاعدة البيانات PostgreSQL"
echo "================================================"

# التحقق من وجود PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL غير مثبت"
    exit 1
fi

# دالة لعرض الاتصالات الحالية
show_connections() {
    echo ""
    echo "🔍 الاتصالات الحالية:"
    echo "----------------------"
    
    sudo -u postgres psql -d crm_system -c "
    SELECT 
        count(*) as total_connections,
        count(*) FILTER (WHERE state = 'active') as active_connections,
        count(*) FILTER (WHERE state = 'idle') as idle_connections,
        count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
        count(*) FILTER (WHERE state = 'idle in transaction (aborted)') as aborted_transactions
    FROM pg_stat_activity 
    WHERE datname = 'crm_system';
    "
}

# دالة لعرض تفاصيل الاتصالات
show_connection_details() {
    echo ""
    echo "📋 تفاصيل الاتصالات:"
    echo "--------------------"
    
    sudo -u postgres psql -d crm_system -c "
    SELECT 
        pid,
        usename,
        application_name,
        client_addr,
        state,
        query_start,
        state_change,
        EXTRACT(EPOCH FROM (now() - query_start)) as query_duration_seconds
    FROM pg_stat_activity 
    WHERE datname = 'crm_system'
    ORDER BY query_start DESC
    LIMIT 20;
    "
}

# دالة لإنهاء الاتصالات الخاملة
kill_idle_connections() {
    echo ""
    echo "🧹 إنهاء الاتصالات الخاملة (أكثر من 5 دقائق):"
    echo "-----------------------------------------------"
    
    sudo -u postgres psql -d crm_system -c "
    SELECT 
        pg_terminate_backend(pid),
        usename,
        application_name,
        state,
        state_change
    FROM pg_stat_activity 
    WHERE datname = 'crm_system'
    AND state = 'idle'
    AND state_change < now() - interval '5 minutes'
    AND pid <> pg_backend_pid();
    "
}

# دالة لإنهاء المعاملات المعلقة
kill_hanging_transactions() {
    echo ""
    echo "🔄 إنهاء المعاملات المعلقة (أكثر من 2 دقيقة):"
    echo "----------------------------------------------"
    
    sudo -u postgres psql -d crm_system -c "
    SELECT 
        pg_terminate_backend(pid),
        usename,
        application_name,
        state,
        query_start
    FROM pg_stat_activity 
    WHERE datname = 'crm_system'
    AND state LIKE '%transaction%'
    AND query_start < now() - interval '2 minutes'
    AND pid <> pg_backend_pid();
    "
}

# دالة لعرض الإحصائيات
show_stats() {
    echo ""
    echo "📈 إحصائيات قاعدة البيانات:"
    echo "----------------------------"
    
    sudo -u postgres psql -d crm_system -c "
    SELECT 
        setting as max_connections
    FROM pg_settings 
    WHERE name = 'max_connections';
    "
    
    echo ""
    sudo -u postgres psql -d crm_system -c "
    SELECT 
        datname,
        numbackends as current_connections,
        xact_commit as transactions_committed,
        xact_rollback as transactions_rolled_back,
        blks_read,
        blks_hit,
        temp_files,
        temp_bytes
    FROM pg_stat_database 
    WHERE datname = 'crm_system';
    "
}

# معالجة المعاملات
case "${1:-show}" in
    "show")
        show_connections
        show_connection_details
        show_stats
        ;;
    "clean")
        show_connections
        kill_idle_connections
        kill_hanging_transactions
        echo ""
        echo "✅ تم تنظيف الاتصالات"
        show_connections
        ;;
    "monitor")
        echo "🔄 مراقبة مستمرة (Ctrl+C للإيقاف)..."
        while true; do
            clear
            echo "📊 مراقبة اتصالات قاعدة البيانات - $(date)"
            echo "================================================"
            show_connections
            
            # فحص إذا كان عدد الاتصالات مرتفع
            TOTAL_CONNECTIONS=$(sudo -u postgres psql -d crm_system -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'crm_system';" | xargs)
            
            if [ "$TOTAL_CONNECTIONS" -gt 50 ]; then
                echo ""
                echo "⚠️  تحذير: عدد الاتصالات مرتفع ($TOTAL_CONNECTIONS)"
                echo "💡 يمكنك تشغيل: $0 clean"
            fi
            
            sleep 10
        done
        ;;
    "help")
        echo "الاستخدام: $0 [show|clean|monitor|help]"
        echo ""
        echo "الأوامر:"
        echo "  show     - عرض الاتصالات الحالية (افتراضي)"
        echo "  clean    - تنظيف الاتصالات الخاملة والمعاملات المعلقة"
        echo "  monitor  - مراقبة مستمرة للاتصالات"
        echo "  help     - عرض هذه المساعدة"
        ;;
    *)
        echo "❌ أمر غير معروف: $1"
        echo "استخدم: $0 help للمساعدة"
        exit 1
        ;;
esac
