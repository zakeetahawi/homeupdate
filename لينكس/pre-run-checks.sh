#!/bin/bash
# Pre-run checks for production deployment
# This script validates all requirements before starting the main production script

echo "🔍 بدء فحص متطلبات التشغيل..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function to print colored output
print_error() {
    echo -e "${RED}❌ خطأ: $1${NC}"
    ((ERRORS++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  تحذير: $1${NC}"
    ((WARNINGS++))
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Check if running as correct user
if [ "$USER" != "xhunterx" ]; then
    print_warning "يتم التشغيل بواسطة المستخدم $USER بدلاً من xhunterx"
fi

# Check project directory
PROJECT_DIR="/home/xhunterx/homeupdate"
if [ ! -d "$PROJECT_DIR" ]; then
    print_error "مجلد المشروع غير موجود: $PROJECT_DIR"
else
    print_success "مجلد المشروع موجود"
fi

# Check virtual environment
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    print_error "البيئة الافتراضية غير موجودة: $VENV_DIR"
else
    print_success "البيئة الافتراضية موجودة"
fi

# Check Python executable
if [ -f "$VENV_DIR/bin/python" ]; then
    PYTHON_VERSION=$($VENV_DIR/bin/python --version 2>&1)
    print_success "Python متوفر: $PYTHON_VERSION"
else
    print_error "Python غير موجود في البيئة الافتراضية"
fi

# Check Django project
MANAGE_PY="$PROJECT_DIR/manage.py"
if [ ! -f "$MANAGE_PY" ]; then
    print_error "ملف manage.py غير موجود: $MANAGE_PY"
else
    print_success "ملف Django manage.py موجود"
fi

# Check required Python packages
if [ -f "$VENV_DIR/bin/pip" ]; then
    echo "🔍 فحص الحزم المطلوبة..."
    
    REQUIRED_PACKAGES=("django" "celery" "redis" "psycopg2-binary" "gunicorn")
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if $VENV_DIR/bin/pip show "$package" >/dev/null 2>&1; then
            print_success "حزمة $package مثبتة"
        else
            print_error "حزمة $package غير مثبتة"
        fi
    done
fi

# Check PostgreSQL
if command -v psql >/dev/null 2>&1; then
    print_success "PostgreSQL client متوفر"
    
    # Test database connection
    DB_NAME="${DB_NAME:-crm_system}"
    DB_USER="${DB_USER:-postgres}"
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"
    
    if PGPASSWORD="${DB_PASSWORD:-5525}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
        print_success "اتصال قاعدة البيانات ناجح"
    else
        print_error "فشل الاتصال بقاعدة البيانات"
    fi
else
    print_error "PostgreSQL client غير مثبت"
fi

# Check Redis
if command -v redis-cli >/dev/null 2>&1; then
    print_success "Redis client متوفر"
    
    if redis-cli ping >/dev/null 2>&1; then
        print_success "Redis server يعمل"
    else
        print_error "Redis server لا يعمل"
    fi
else
    print_error "Redis client غير مثبت"
fi

# Check Cloudflare files
CLOUDFLARED_BINARY="$PROJECT_DIR/cloudflared"
CLOUDFLARED_CONFIG="$PROJECT_DIR/cloudflared.yml"
CLOUDFLARED_CREDS="$PROJECT_DIR/cloudflare-credentials.json"
CLOUDFLARED_CERT="$PROJECT_DIR/cert.pem"

if [ -f "$CLOUDFLARED_BINARY" ]; then
    if [ -x "$CLOUDFLARED_BINARY" ]; then
        print_success "Cloudflared binary موجود وقابل للتنفيذ"
    else
        print_warning "Cloudflared binary موجود لكن غير قابل للتنفيذ"
    fi
else
    print_error "Cloudflared binary غير موجود: $CLOUDFLARED_BINARY"
fi

if [ -f "$CLOUDFLARED_CONFIG" ]; then
    print_success "ملف تكوين Cloudflared موجود"
else
    print_error "ملف تكوين Cloudflared غير موجود: $CLOUDFLARED_CONFIG"
fi

if [ -f "$CLOUDFLARED_CREDS" ]; then
    print_success "ملف بيانات اعتماد Cloudflare موجود"
else
    print_error "ملف بيانات اعتماد Cloudflare غير موجود: $CLOUDFLARED_CREDS"
fi

if [ -f "$CLOUDFLARED_CERT" ]; then
    print_success "شهادة Cloudflare موجودة"
else
    print_error "شهادة Cloudflare غير موجودة: $CLOUDFLARED_CERT"
fi

# Check ports availability
echo "🔍 فحص توفر المنافذ..."
PORTS=(8000 6379)
for port in "${PORTS[@]}"; do
    if netstat -tuln 2>/dev/null | grep ":$port " >/dev/null; then
        print_warning "المنفذ $port مستخدم بالفعل"
    else
        print_success "المنفذ $port متاح"
    fi
done

# Check disk space
DISK_USAGE=$(df "$PROJECT_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    print_error "مساحة القرص ممتلئة: ${DISK_USAGE}%"
elif [ "$DISK_USAGE" -gt 80 ]; then
    print_warning "مساحة القرص منخفضة: ${DISK_USAGE}%"
else
    print_success "مساحة القرص كافية: ${DISK_USAGE}%"
fi

# Check memory
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ "$MEMORY_USAGE" -gt 90 ]; then
    print_warning "استخدام الذاكرة مرتفع: ${MEMORY_USAGE}%"
else
    print_success "استخدام الذاكرة طبيعي: ${MEMORY_USAGE}%"
fi

# Create required directories
echo "🔍 فحص وإنشاء المجلدات المطلوبة..."
REQUIRED_DIRS=(
    "$PROJECT_DIR/media/backups"
    "$PROJECT_DIR/static"
    "$PROJECT_DIR/logs"
    "/tmp"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        if mkdir -p "$dir" 2>/dev/null; then
            print_success "تم إنشاء المجلد: $dir"
        else
            print_error "فشل إنشاء المجلد: $dir"
        fi
    else
        print_success "المجلد موجود: $dir"
    fi
done

# Summary
echo ""
echo "📊 ملخص الفحص:"
echo "==============="

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    print_success "جميع الفحوصات نجحت! النظام جاهز للتشغيل."
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  تم العثور على $WARNINGS تحذير(ات). يمكن المتابعة مع الحذر.${NC}"
    exit 1
else
    echo -e "${RED}❌ تم العثور على $ERRORS خطأ(أخطاء) و $WARNINGS تحذير(ات).${NC}"
    echo -e "${RED}يجب إصلاح الأخطاء قبل التشغيل!${NC}"
    exit 2
fi
