#!/bin/bash

# سكريبت فحص سلامة الترحيلات
# المؤلف: نظام إدارة المنزل
# التاريخ: $(date +%Y-%m-%d)

echo -e "\033[1;34m=== فحص سلامة الترحيلات ===\033[0m"

# التحقق من وجود تغييرات في النماذج
echo -e "\033[1;33m[1/4] فحص التغييرات في النماذج...\033[0m"
python manage.py makemigrations --dry-run --verbosity=0

if [ $? -eq 0 ]; then
    echo -e "\033[1;32m✓ لا توجد تغييرات جديدة\033[0m"
else
    echo -e "\033[1;31m⚠ توجد تغييرات جديدة تحتاج ترحيلات\033[0m"
fi

# التحقق من حالة الترحيلات
echo -e "\033[1;33m[2/4] فحص حالة الترحيلات...\033[0m"
python manage.py showmigrations | grep -E "\[ \]" | wc -l > /tmp/pending_migrations.txt
PENDING_COUNT=$(cat /tmp/pending_migrations.txt)

if [ "$PENDING_COUNT" -eq 0 ]; then
    echo -e "\033[1;32m✓ جميع الترحيلات محدثة\033[0m"
else
    echo -e "\033[1;31m⚠ يوجد $PENDING_COUNT ترحيل معلق\033[0m"
fi

# التحقق من صحة قاعدة البيانات
echo -e "\033[1;33m[3/4] فحص صحة قاعدة البيانات...\033[0m"
python manage.py check --database default

if [ $? -eq 0 ]; then
    echo -e "\033[1;32m✓ قاعدة البيانات سليمة\033[0m"
else
    echo -e "\033[1;31m⚠ مشاكل في قاعدة البيانات\033[0m"
fi

# التحقق من الاتصال بقاعدة البيانات
echo -e "\033[1;33m[4/4] فحص الاتصال بقاعدة البيانات...\033[0m"
python manage.py shell -c "
from django.db import connection
try:
    cursor = connection.cursor()
    cursor.execute('SELECT 1')
    print('✓ الاتصال بقاعدة البيانات يعمل')
except Exception as e:
    print(f'⚠ خطأ في الاتصال: {e}')
    exit(1)
"

echo -e "\033[1;34m=== انتهى الفحص ===\033[0m"

# تنظيف الملفات المؤقتة
rm -f /tmp/pending_migrations.txt
