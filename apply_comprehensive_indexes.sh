#!/bin/bash

# سكريبت تطبيق فهارس قاعدة البيانات الشاملة
# Comprehensive Database Indexes Application Script

echo -e "\033[1;37m==========================================="
echo -e "تطبيق فهارس قاعدة البيانات الشاملة"
echo -e "Applying Comprehensive Database Indexes"
echo -e "===========================================\033[0m"

# الانتقال إلى مجلد المشروع
cd "$(dirname "$0")/.."

# التحقق من وجود ملف الفهارس
INDEXES_FILE="COMPREHENSIVE_DATABASE_INDEXES.sql"

if [ ! -f "$INDEXES_FILE" ]; then
    echo -e "\033[1;31m❌ ملف الفهارس غير موجود: $INDEXES_FILE\033[0m"
    exit 1
fi

echo -e "\033[1;32m✅ تم العثور على ملف الفهارس: $INDEXES_FILE\033[0m"

# تطبيق الفهارس باستخدام Django
echo -e "\033[1;33m🔧 تطبيق الفهارس باستخدام Django...\033[0m"

python manage.py shell -c "
import os
import time
from django.db import connection

print('بدء تطبيق فهارس قاعدة البيانات الشاملة...')
print('Starting comprehensive database indexes application...')

# قراءة ملف الفهارس
indexes_file = '$INDEXES_FILE'
with open(indexes_file, 'r', encoding='utf-8') as f:
    content = f.read()

# تقسيم الملف إلى أوامر منفصلة
commands = []
current_command = []

for line in content.split('\n'):
    line = line.strip()
    if line and not line.startswith('--') and not line.startswith('=') and not line.startswith('*'):
        current_command.append(line)
        if line.endswith(';'):
            commands.append(' '.join(current_command))
            current_command = []

print(f'تم العثور على {len(commands)} أمر SQL للتنفيذ')
print(f'Found {len(commands)} SQL commands to execute')

# تنفيذ الأوامر
cursor = connection.cursor()
success_count = 0
error_count = 0
skipped_count = 0

start_time = time.time()

for i, command in enumerate(commands, 1):
    try:
        print(f'تنفيذ الأمر {i}/{len(commands)}...')
        cursor.execute(command)
        success_count += 1
        print(f'✅ تم بنجاح')
    except Exception as e:
        error_message = str(e)
        if 'already exists' in error_message.lower() or 'does not exist' in error_message.lower():
            skipped_count += 1
            print(f'⚠️ تم تخطيه: {error_message[:100]}...')
        else:
            error_count += 1
            print(f'❌ خطأ: {error_message[:100]}...')

# تحليل الجداول
print('تحليل الجداول...')
analyze_commands = [
    'ANALYZE orders_order;',
    'ANALYZE customers_customer;',
    'ANALYZE manufacturing_manufacturingorder;',
    'ANALYZE installations_installationschedule;',
    'ANALYZE inventory_product;',
    'ANALYZE inventory_stocktransaction;',
    'ANALYZE inspections_inspection;',
    'ANALYZE complaints_complaint;',
    'ANALYZE accounts_user;',
    'ANALYZE user_activity_useractivitylog;'
]

for command in analyze_commands:
    try:
        cursor.execute(command)
    except Exception as e:
        print(f'خطأ في تحليل الجدول: {e}')

end_time = time.time()
duration = end_time - start_time

print('\n' + '='*50)
print('نتائج تطبيق الفهارس:')
print(f'الأوامر المنجزة بنجاح: {success_count}')
print(f'الأوامر المتجاهلة: {skipped_count}')
print(f'الأوامر التي فشلت: {error_count}')
print(f'الوقت المستغرق: {duration:.2f} ثانية')
print('='*50)

if error_count == 0:
    print('✅ تم تطبيق جميع الفهارس بنجاح!')
else:
    print('⚠️ تم تطبيق معظم الفهارس مع بعض الأخطاء')
"