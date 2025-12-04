#!/bin/bash
# ===================================================================
# سكريبت تطبيق نظام الفهرسة الشامل والمتكامل
# ULTIMATE DATABASE INDEXING APPLICATION SCRIPT
# ===================================================================

set -e  # إيقاف السكريبت عند حدوث خطأ

# الألوان للطباعة
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# دالة طباعة ملونة
print_colored() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# دالة طباعة العنوان
print_header() {
    echo ""
    print_colored $CYAN "=================================================================="
    print_colored $CYAN "$1"
    print_colored $CYAN "=================================================================="
    echo ""
}

# دالة التحقق من المتطلبات
check_requirements() {
    print_header "🔍 فحص المتطلبات"
    
    # التحقق من Python
    if ! command -v python3 &> /dev/null; then
        print_colored $RED "❌ Python 3 غير مثبت"
        exit 1
    fi
    print_colored $GREEN "✅ Python 3 متوفر"
    
    # التحقق من pip
    if ! command -v pip3 &> /dev/null; then
        print_colored $RED "❌ pip3 غير مثبت"
        exit 1
    fi
    print_colored $GREEN "✅ pip3 متوفر"
    
    # التحقق من psycopg2
    if ! python3 -c "import psycopg2" 2>/dev/null; then
        print_colored $YELLOW "⚠️  psycopg2 غير مثبت، جاري التثبيت..."
        pip3 install psycopg2-binary
        print_colored $GREEN "✅ تم تثبيت psycopg2"
    else
        print_colored $GREEN "✅ psycopg2 متوفر"
    fi
    
    # التحقق من ملف الفهارس
    if [ "$USE_SIMPLE" = true ]; then
        if [ ! -f "ULTIMATE_DATABASE_INDEXES_SIMPLE.sql" ]; then
            print_colored $RED "❌ ملف الفهارس المبسط غير موجود: ULTIMATE_DATABASE_INDEXES_SIMPLE.sql"
            exit 1
        fi
        print_colored $GREEN "✅ ملف الفهارس المبسط موجود"
    else
        if [ ! -f "ULTIMATE_DATABASE_INDEXES.sql" ]; then
            print_colored $RED "❌ ملف الفهارس غير موجود: ULTIMATE_DATABASE_INDEXES.sql"
            exit 1
        fi
        print_colored $GREEN "✅ ملف الفهارس موجود"
    fi
    
    # التحقق من سكريبت Python
    if [ ! -f "apply_ultimate_indexes.py" ]; then
        print_colored $RED "❌ سكريبت Python غير موجود: apply_ultimate_indexes.py"
        exit 1
    fi
    print_colored $GREEN "✅ سكريبت Python موجود"
}

# دالة عرض المساعدة
show_help() {
    print_header "📖 مساعدة سكريبت تطبيق الفهارس"
    
    echo "الاستخدام:"
    echo "  $0 [OPTIONS]"
    echo ""
    echo "الخيارات:"
    echo "  -h, --help              عرض هذه المساعدة"
    echo "  -c, --config FILE       ملف إعدادات قاعدة البيانات"
    echo "  -H, --host HOST         عنوان خادم قاعدة البيانات"
    echo "  -p, --port PORT         منفذ قاعدة البيانات"
    echo "  -d, --database DB       اسم قاعدة البيانات"
    echo "  -u, --user USER         اسم المستخدم"
    echo "  -P, --password PASS     كلمة المرور"
    echo "  -r, --report FILE       ملف التقرير"
    echo "  -s, --secondary         استخدام إعدادات الخادم الثاني"
    echo "  -l, --local             استخدام إعدادات الخادم المحلي"
    echo "  --simple                استخدام الفهارس المبسطة بدون CONCURRENTLY"
    echo "  -m, --monitor           تشغيل مراقب الفهارس بعد التطبيق"
    echo "  -t, --test              اختبار الاتصال فقط"
    echo ""
    echo "أمثلة:"
    echo "  $0 --local                          # تطبيق على الخادم المحلي"
    echo "  $0 --secondary                      # تطبيق على الخادم الثاني"
    echo "  $0 --config my_config.json          # استخدام ملف إعدادات مخصص"
    echo "  $0 --host 192.168.1.100 --user admin # إعدادات مخصصة"
    echo "  $0 --test --secondary               # اختبار الاتصال بالخادم الثاني"
    echo ""
}

# دالة اختبار الاتصال
test_connection() {
    print_header "🔌 اختبار الاتصال بقاعدة البيانات"
    
    local config_args=""
    
    if [ ! -z "$CONFIG_FILE" ]; then
        config_args="--config-file $CONFIG_FILE"
    fi
    
    if [ ! -z "$HOST" ]; then
        config_args="$config_args --host $HOST"
    fi
    
    if [ ! -z "$PORT" ]; then
        config_args="$config_args --port $PORT"
    fi
    
    if [ ! -z "$DATABASE" ]; then
        config_args="$config_args --database $DATABASE"
    fi
    
    if [ ! -z "$USER" ]; then
        config_args="$config_args --user $USER"
    fi
    
    if [ ! -z "$PASSWORD" ]; then
        config_args="$config_args --password $PASSWORD"
    fi
    
    # إنشاء سكريبت اختبار مؤقت
    cat > test_connection.py << 'EOF'
import sys
import psycopg2
import json
import os

def load_config(config_file=None):
    default_config = {
        'host': 'localhost',
        'port': '5432',
        'database': 'crm_system',
        'user': 'postgres',
        'password': 'your_password'
    }
    
    if config_file and os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    
    return default_config

def test_connection(config):
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        print(f"✅ الاتصال ناجح: {version}")
        return True
    except Exception as e:
        print(f"❌ فشل الاتصال: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file')
    parser.add_argument('--host')
    parser.add_argument('--port')
    parser.add_argument('--database')
    parser.add_argument('--user')
    parser.add_argument('--password')
    
    args = parser.parse_args()
    
    config = load_config(args.config_file)
    
    if args.host:
        config['host'] = args.host
    if args.port:
        config['port'] = args.port
    if args.database:
        config['database'] = args.database
    if args.user:
        config['user'] = args.user
    if args.password:
        config['password'] = args.password
    
    success = test_connection(config)
    sys.exit(0 if success else 1)
EOF
    
    python3 test_connection.py $config_args
    local result=$?
    
    # حذف الملف المؤقت
    rm -f test_connection.py
    
    return $result
}

# دالة تطبيق الفهارس
apply_indexes() {
    print_header "🚀 تطبيق نظام الفهرسة الشامل"
    
    local python_args=""
    
    if [ ! -z "$CONFIG_FILE" ]; then
        python_args="--config-file $CONFIG_FILE"
    fi
    
    if [ ! -z "$HOST" ]; then
        python_args="$python_args --host $HOST"
    fi
    
    if [ ! -z "$PORT" ]; then
        python_args="$python_args --port $PORT"
    fi
    
    if [ ! -z "$DATABASE" ]; then
        python_args="$python_args --database $DATABASE"
    fi
    
    if [ ! -z "$USER" ]; then
        python_args="$python_args --user $USER"
    fi
    
    if [ ! -z "$PASSWORD" ]; then
        python_args="$python_args --password $PASSWORD"
    fi
    
    if [ ! -z "$REPORT_FILE" ]; then
        python_args="$python_args --report-file $REPORT_FILE"
    fi

    if [ "$USE_SIMPLE" = true ]; then
        python_args="$python_args --simple"
        print_colored $YELLOW "🔧 استخدام الفهارس المبسطة بدون CONCURRENTLY"
    fi

    print_colored $BLUE "🔨 جاري تطبيق الفهارس..."
    python3 apply_ultimate_indexes.py $python_args
    
    if [ $? -eq 0 ]; then
        print_colored $GREEN "🎉 تم تطبيق الفهارس بنجاح!"
        return 0
    else
        print_colored $RED "❌ فشل في تطبيق الفهارس"
        return 1
    fi
}

# دالة تشغيل مراقب الفهارس
run_monitor() {
    print_header "📊 تشغيل مراقب الفهارس"
    
    if [ ! -f "monitor_indexes.py" ]; then
        print_colored $YELLOW "⚠️  مراقب الفهارس غير متوفر"
        return 1
    fi
    
    local monitor_args=""
    
    if [ ! -z "$CONFIG_FILE" ]; then
        monitor_args="--config-file $CONFIG_FILE"
    fi
    
    local monitor_report="indexes_monitoring_report_$(date +%Y%m%d_%H%M%S).json"
    monitor_args="$monitor_args --report-file $monitor_report"
    
    print_colored $BLUE "📊 جاري إنشاء تقرير المراقبة..."
    python3 monitor_indexes.py $monitor_args
    
    if [ $? -eq 0 ]; then
        print_colored $GREEN "📄 تم إنشاء تقرير المراقبة: $monitor_report"
        return 0
    else
        print_colored $RED "❌ فشل في إنشاء تقرير المراقبة"
        return 1
    fi
}

# دالة النسخ الاحتياطي للفهارس الحالية
backup_current_indexes() {
    print_header "💾 إنشاء نسخة احتياطية من الفهارس الحالية"
    
    local backup_file="current_indexes_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    # إنشاء سكريبت استخراج الفهارس
    cat > extract_indexes.py << 'EOF'
import sys
import psycopg2
import json
import os

def extract_indexes(config, output_file):
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        cursor = conn.cursor()
        
        # استخراج تعريفات الفهارس
        query = """
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND indexname LIKE 'idx_%'
        ORDER BY indexname;
        """
        
        cursor.execute(query)
        indexes = cursor.fetchall()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("-- نسخة احتياطية من الفهارس الحالية\n")
            f.write(f"-- تم الإنشاء في: {datetime.now().isoformat()}\n\n")
            
            for index_name, index_def in indexes:
                f.write(f"-- {index_name}\n")
                f.write(f"{index_def};\n\n")
        
        cursor.close()
        conn.close()
        
        print(f"✅ تم إنشاء النسخة الاحتياطية: {output_file}")
        print(f"📊 تم حفظ {len(indexes)} فهرس")
        return True
        
    except Exception as e:
        print(f"❌ فشل في إنشاء النسخة الاحتياطية: {str(e)}")
        return False

if __name__ == "__main__":
    from datetime import datetime
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file')
    parser.add_argument('--output-file', required=True)
    parser.add_argument('--host')
    parser.add_argument('--port')
    parser.add_argument('--database')
    parser.add_argument('--user')
    parser.add_argument('--password')
    
    args = parser.parse_args()
    
    # تحميل الإعدادات
    default_config = {
        'host': 'localhost',
        'port': '5432',
        'database': 'crm_system',
        'user': 'postgres',
        'password': 'your_password'
    }
    
    if args.config_file and os.path.exists(args.config_file):
        with open(args.config_file, 'r') as f:
            config = json.load(f)
    else:
        config = default_config
    
    if args.host:
        config['host'] = args.host
    if args.port:
        config['port'] = args.port
    if args.database:
        config['database'] = args.database
    if args.user:
        config['user'] = args.user
    if args.password:
        config['password'] = args.password
    
    success = extract_indexes(config, args.output_file)
    sys.exit(0 if success else 1)
EOF
    
    local config_args=""
    
    if [ ! -z "$CONFIG_FILE" ]; then
        config_args="--config-file $CONFIG_FILE"
    fi
    
    if [ ! -z "$HOST" ]; then
        config_args="$config_args --host $HOST"
    fi
    
    if [ ! -z "$PORT" ]; then
        config_args="$config_args --port $PORT"
    fi
    
    if [ ! -z "$DATABASE" ]; then
        config_args="$config_args --database $DATABASE"
    fi
    
    if [ ! -z "$USER" ]; then
        config_args="$config_args --user $USER"
    fi
    
    if [ ! -z "$PASSWORD" ]; then
        config_args="$config_args --password $PASSWORD"
    fi
    
    python3 extract_indexes.py $config_args --output-file "$backup_file"
    local result=$?
    
    # حذف الملف المؤقت
    rm -f extract_indexes.py
    
    if [ $result -eq 0 ]; then
        print_colored $GREEN "💾 تم إنشاء النسخة الاحتياطية: $backup_file"
    fi
    
    return $result
}

# المتغيرات الافتراضية
CONFIG_FILE=""
HOST=""
PORT=""
DATABASE=""
USER=""
PASSWORD=""
REPORT_FILE=""
TEST_ONLY=false
RUN_MONITOR=false
CREATE_BACKUP=false
USE_SIMPLE=false

# معالجة المعاملات
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -H|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -d|--database)
            DATABASE="$2"
            shift 2
            ;;
        -u|--user)
            USER="$2"
            shift 2
            ;;
        -P|--password)
            PASSWORD="$2"
            shift 2
            ;;
        -r|--report)
            REPORT_FILE="$2"
            shift 2
            ;;
        -s|--secondary)
            CONFIG_FILE="database_config_secondary.json"
            shift
            ;;
        -l|--local)
            CONFIG_FILE="database_config_local.json"
            shift
            ;;
        -m|--monitor)
            RUN_MONITOR=true
            shift
            ;;
        -t|--test)
            TEST_ONLY=true
            shift
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
            ;;
        --simple)
            USE_SIMPLE=true
            shift
            ;;
        *)
            print_colored $RED "❌ معامل غير معروف: $1"
            show_help
            exit 1
            ;;
    esac
done

# الدالة الرئيسية
main() {
    print_header "🚀 نظام الفهرسة الشامل والمتكامل"
    
    # فحص المتطلبات
    check_requirements
    
    # اختبار الاتصال
    if ! test_connection; then
        print_colored $RED "❌ فشل اختبار الاتصال"
        exit 1
    fi
    
    # إذا كان الاختبار فقط
    if [ "$TEST_ONLY" = true ]; then
        print_colored $GREEN "🎉 اختبار الاتصال ناجح!"
        exit 0
    fi
    
    # إنشاء نسخة احتياطية
    if [ "$CREATE_BACKUP" = true ]; then
        backup_current_indexes
    fi
    
    # تطبيق الفهارس
    if ! apply_indexes; then
        print_colored $RED "❌ فشل في تطبيق الفهارس"
        exit 1
    fi
    
    # تشغيل المراقب
    if [ "$RUN_MONITOR" = true ]; then
        run_monitor
    fi
    
    print_colored $GREEN "🎉 تم تطبيق نظام الفهرسة بنجاح!"
    print_colored $CYAN "📄 تحقق من ملفات التقارير للحصول على تفاصيل إضافية"
}

# تشغيل الدالة الرئيسية
main
