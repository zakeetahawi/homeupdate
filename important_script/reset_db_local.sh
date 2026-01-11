#!/bin/bash

# ألوان للرسائل
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# دالة للتحقق من نجاح الأمر السابق
check_success() {
	if [ $? -ne 0 ]; then
		echo -e "${RED}خطأ: فشل في تنفيذ: $1${NC}"
		exit 1
	fi
}

echo -e "${YELLOW}بدء عملية إعادة تعيين قاعدة البيانات...${NC}"

# تعيين قيم افتراضية ثابتة
DB_NAME="crm_system" # اسم قاعدة البيانات المطلوب
DB_USER="postgres"   # اسم المستخدم
DB_PASSWORD="5525"   # كلمة المرور
DB_HOST="localhost"  # عنوان الخادم
DB_PORT="5432"       # منفذ قاعدة البيانات

export PGPASSWORD="$DB_PASSWORD"

# عرض إعدادات قاعدة البيانات
echo -e "${YELLOW}إعدادات قاعدة البيانات:${NC}"
echo "- اسم قاعدة البيانات: $DB_NAME"
echo "- اسم المستخدم: $DB_USER"
echo "- المضيف: $DB_HOST"
echo "- المنفذ: $DB_PORT"

# التحقق من اتصال PostgreSQL
if ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER >/dev/null 2>&1; then
	echo -e "${RED}خطأ: لا يمكن الاتصال بخادم PostgreSQL${NC}"
	exit 1
fi

# تأكيد من المستخدم
echo -e "\n${YELLOW}تحذير: سيتم حذف قاعدة البيانات '$DB_NAME' وإنشاؤها من جديد${NC}"
read -p "اكتب 'نعم' للمتابعة: " confirm

if [ "$confirm" != "نعم" ]; then
	echo -e "${YELLOW}تم إلغاء العملية${NC}"
	exit 0
fi

# 2. إيقاف أي عمليات سيرفر
echo -e "${YELLOW}إيقاف أي عمليات سيرفر...${NC}"
pkill -f "python manage.py runserver" 2>/dev/null

# 3. حذف الملفات المؤقتة
echo -e "${YELLOW}حذف الملفات المؤقتة...${NC}"
find . -name "*.pyc" -delete
find . -name "__pycache__" -exec rm -rf {} +

# 4. إنهاء الاتصالات النشطة وحذف قاعدة البيانات موجودة
echo -e "${YELLOW}إعادة تعيين قاعدة البيانات...${NC}"

# التحقق مما إذا كانت قاعدة البيانات موجودة
DB_EXISTS=$(PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "0")

if [ "$DB_EXISTS" = "1" ]; then
	echo -e "${YELLOW}إنهاء الاتصالات النشطة بقاعدة البيانات...${NC}"
	PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -c "
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = '$DB_NAME' AND pid <> pg_backend_pid()" 2>/dev/null || true

	echo -e "${YELLOW}حذف قاعدة البيانات الموجودة...${NC}"
	dropdb -h $DB_HOST -U $DB_USER "$DB_NAME" 2>/dev/null || {
		echo -e "${RED}خطأ: فشل في حذف قاعدة البيانات. تأكد من أنك تملك الصلاحيات الكافية.${NC}"
		exit 1
	}
	echo -e "${GREEN}✓ تم حذف قاعدة البيانات بنجاح${NC}"
else
	echo -e "${YELLOW}قاعدة البيانات غير موجودة، سيتم إنشاؤها...${NC}"
fi

# 5. إنشاء قاعدة بيانات جديدة
echo -e "${YELLOW}إنشاء قاعدة بيانات جديدة...${NC}"
createdb -h $DB_HOST -U $DB_USER -E UTF-8 "$DB_NAME"
check_success "إنشاء قاعدة البيانات"

# 6. إنشاء المستخدم إذا لم يكن موجوداً
echo -e "${YELLOW}التحقق من وجود مستخدم قاعدة البيانات...${NC}"

# التحقق مما إذا كان المستخدم موجوداً
USER_EXISTS=$(PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null || echo "0")

if [ "$USER_EXISTS" != "1" ]; then
	echo -e "${YELLOW}إنشاء مستخدم قاعدة البيانات '$DB_USER'...${NC}"
	createuser -h $DB_HOST -U $DB_USER --superuser "$DB_USER" 2>/dev/null || {
		echo -e "${RED}خطأ: فشل في إنشاء المستخدم${NC}"
		exit 1
	}
	# تعيين كلمة المرور للمستخدم
	PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
	echo -e "${GREEN}✓ تم إنشاء المستخدم وتعيين كلمة المرور${NC}"
else
	echo -e "${YELLOW}المستخدم '$DB_USER' موجود بالفعل${NC}"
fi

# 7. تعيين ملكية قاعدة البيانات
echo -e "${YELLOW}تعيين ملكية قاعدة البيانات...${NC}"
PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -c "ALTER DATABASE \"$DB_NAME\" OWNER TO \"$DB_USER\";"
check_success "تعيين ملكية قاعدة البيانات"

# 8. منح الصلاحيات
echo -e "${YELLOW}منح الصلاحيات...${NC}"
PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -d "$DB_NAME" -c "
    GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO \"$DB_USER\";
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"$DB_USER\";
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"$DB_USER\";
    GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO \"$DB_USER\";
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO \"$DB_USER\";
"
check_success "منح الصلاحيات"

# 9. إنشاء الترحيلات
echo -e "${YELLOW}إنشاء الترحيلات...${NC}"
python manage.py makemigrations
check_success "إنشاء الترحيلات"

# 10. تطبيق الترحيلات
# 8. تطبيق الترحيلات
echo -e "${YELLOW}تطبيق الترحيلات...${NC}"
python manage.py migrate
check_success "تطبيق الترحيلات"

# 9. إنشاء مستخدم مسؤول
echo -e "${YELLOW}إنشاء مستخدم مسؤول...${NC}"
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✓ تم إنشاء مستخدم مسؤول جديد')
else:
    print('✓ المستخدم المسؤول موجود بالفعل')
"

echo -e "\n${GREEN}✓ تم إعادة تعيين قاعدة البيانات بنجاح${NC}"
echo -e "اسم المستخدم: admin"
echo -e "كلمة المرور: admin123"
