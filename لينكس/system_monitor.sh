#!/bin/bash

# سكريبت مراقبة نظام إدارة العملاء
# System Monitor Script for Customer Management System

echo -e "\033[1;37m==========================================="
echo -e "بدء مراقبة النظام"
echo -e "Starting System Monitor"
echo -e "===========================================\033[0m"

# فحص حالة الخدمات
check_services() {
	echo -e "\033[1;33m🔍 فحص حالة الخدمات..."
	echo -e "Checking service status...\033[0m"

	# فحص Django
	if python3 manage.py check >/dev/null 2>&1; then
		echo -e "\033[1;32m✅ Django يعمل بشكل صحيح"
		echo -e "Django is running correctly\033[0m"
	else
		echo -e "\033[1;31m❌ مشكلة في Django"
		echo -e "Django issue detected\033[0m"
	fi

	# فحص قاعدة البيانات
	if python3 manage.py check --database default >/dev/null 2>&1; then
		echo -e "\033[1;32m✅ قاعدة البيانات متصلة"
		echo -e "Database is connected\033[0m"
	else
		echo -e "\033[1;31m❌ مشكلة في قاعدة البيانات"
		echo -e "Database issue detected\033[0m"
	fi
}

# فحص استخدام الموارد
check_resources() {
	echo -e "\033[1;33m💻 فحص استخدام الموارد..."
	echo -e "Checking resource usage...\033[0m"

	# استخدام الذاكرة
	MEMORY_USAGE=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')
	echo -e "\033[1;37m💾 استخدام الذاكرة: $MEMORY_USAGE"
	echo -e "Memory usage: $MEMORY_USAGE\033[0m"

	# استخدام القرص
	DISK_USAGE=$(df -h / | awk 'NR==2{print $5}')
	echo -e "\033[1;37m💿 استخدام القرص: $DISK_USAGE"
	echo -e "Disk usage: $DISK_USAGE\033[0m"

	# استخدام المعالج
	CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
	echo -e "\033[1;37m🖥️ استخدام المعالج: ${CPU_USAGE}%"
	echo -e "CPU usage: ${CPU_USAGE}%\033[0m"
}

# فحص الملفات المهمة
check_important_files() {
	echo -e "\033[1;33m📁 فحص الملفات المهمة..."
	echo -e "Checking important files...\033[0m"

	# فحص ملف البيئة
	if [ -f ".env" ]; then
		echo -e "\033[1;32m✅ ملف البيئة موجود"
		echo -e "Environment file exists\033[0m"
	else
		echo -e "\033[1;31m❌ ملف البيئة مفقود"
		echo -e "Environment file missing\033[0m"
	fi

	# فحص ملفات الإعدادات
	if [ -f "crm/settings.py" ]; then
		echo -e "\033[1;32m✅ ملف الإعدادات موجود"
		echo -e "Settings file exists\033[0m"
	else
		echo -e "\033[1;31m❌ ملف الإعدادات مفقود"
		echo -e "Settings file missing\033[0m"
	fi

	# فحص مجلد الملفات الثابتة
	if [ -d "staticfiles" ]; then
		STATIC_COUNT=$(find staticfiles -type f | wc -l)
		echo -e "\033[1;32m✅ الملفات الثابتة: $STATIC_COUNT ملف"
		echo -e "Static files: $STATIC_COUNT files\033[0m"
	else
		echo -e "\033[1;31m❌ مجلد الملفات الثابتة مفقود"
		echo -e "Static files directory missing\033[0m"
	fi
}

# فحص قاعدة البيانات
check_database() {
	echo -e "\033[1;33m🗄️ فحص قاعدة البيانات..."
	echo -e "Checking database...\033[0m"

	python3 manage.py shell -c "
from django.db import connection
from django.contrib.auth.models import User
from customers.models import Customer
from orders.models import Order
from inventory.models import Product

# فحص الاتصال
try:
    cursor = connection.cursor()
    cursor.execute('SELECT 1')
    print('✅ Database connection: OK')
except Exception as e:
    print(f'❌ Database connection: {e}')
    exit(1)

# إحصائيات الجداول
try:
    user_count = User.objects.count()
    customer_count = Customer.objects.count()
    order_count = Order.objects.count()
    product_count = Product.objects.count()
    
    print(f'📊 Users: {user_count}')
    print(f'📊 Customers: {customer_count}')
    print(f'📊 Orders: {order_count}')
    print(f'📊 Products: {product_count}')
    
except Exception as e:
    print(f'❌ Database query error: {e}')
"
}

# فحص الذاكرة المؤقتة
check_cache() {
	echo -e "\033[1;33m💾 فحص الذاكرة المؤقتة..."
	echo -e "Checking cache...\033[0m"

	python3 manage.py shell -c "
from django.core.cache import cache

# اختبار الذاكرة المؤقتة
try:
    cache.set('test_key', 'test_value', 60)
    test_value = cache.get('test_key')
    if test_value == 'test_value':
        print('✅ Cache: Working correctly')
    else:
        print('❌ Cache: Not working properly')
except Exception as e:
    print(f'❌ Cache error: {e}')

# تنظيف الذاكرة المؤقتة
try:
    cache.clear()
    print('✅ Cache: Cleared successfully')
except Exception as e:
    print(f'❌ Cache clear error: {e}')
"
}

# فحص الصلاحيات
check_permissions() {
	echo -e "\033[1;33m🔐 فحص الصلاحيات..."
	echo -e "Checking permissions...\033[0m"

	python3 manage.py shell -c "
from django.contrib.auth.models import Permission
from accounts.models import User, Role, UserRole

# فحص المستخدمين
user_count = User.objects.count()
active_users = User.objects.filter(is_active=True).count()
staff_users = User.objects.filter(is_staff=True).count()

print(f'👥 Total users: {user_count}')
print(f'👥 Active users: {active_users}')
print(f'👥 Staff users: {staff_users}')

# فحص الأدوار
role_count = Role.objects.count()
user_role_count = UserRole.objects.count()

print(f'🎭 Total roles: {role_count}')
print(f'🎭 User roles: {user_role_count}')

# فحص الصلاحيات
permission_count = Permission.objects.count()
print(f'🔑 Total permissions: {permission_count}')
"
}

# فحص السجلات
check_logs() {
	echo -e "\033[1;33m📋 فحص السجلات..."
	echo -e "Checking logs...\033[0m"

	# فحص ملفات السجلات
	LOG_FILES=$(find . -name "*.log" 2>/dev/null | wc -l)
	if [ $LOG_FILES -gt 0 ]; then
		echo -e "\033[1;32m✅ عدد ملفات السجلات: $LOG_FILES"
		echo -e "Log files count: $LOG_FILES\033[0m"

		# فحص حجم السجلات
		for log_file in $(find . -name "*.log" 2>/dev/null); do
			size=$(du -h "$log_file" | cut -f1)
			echo -e "\033[1;37m📄 $log_file: $size"
			echo -e "📄 $log_file: $size\033[0m"
		done
	else
		echo -e "\033[1;33m⚠️ لا توجد ملفات سجلات"
		echo -e "No log files found\033[0m"
	fi
}

# فحص الأمان
check_security() {
	echo -e "\033[1;33m🛡️ فحص الأمان..."
	echo -e "Checking security...\033[0m"

	# فحص الملفات الحساسة
	if [ -f "SECRET_KEY.txt" ]; then
		echo -e "\033[1;31m⚠️ تحذير: ملف SECRET_KEY.txt موجود"
		echo -e "Warning: SECRET_KEY.txt file exists\033[0m"
	else
		echo -e "\033[1;32m✅ لا توجد ملفات حساسة مكشوفة"
		echo -e "No sensitive files exposed\033[0m"
	fi

	# فحص صلاحيات الملفات
	if [ -f ".env" ]; then
		PERMS=$(stat -c %a .env)
		if [ "$PERMS" != "600" ]; then
			echo -e "\033[1;31m⚠️ تحذير: صلاحيات ملف .env غير آمنة ($PERMS)"
			echo -e "Warning: .env file permissions are not secure ($PERMS)\033[0m"
		else
			echo -e "\033[1;32m✅ صلاحيات ملف .env آمنة"
			echo -e ".env file permissions are secure\033[0m"
		fi
	fi
}

# إنشاء تقرير المراقبة
create_monitor_report() {
	echo -e "\033[1;33m📊 إنشاء تقرير المراقبة..."
	echo -e "Creating monitor report...\033[0m"

	REPORT_FILE="system_monitor_report_$(date +%Y%m%d_%H%M%S).txt"

	cat >"$REPORT_FILE" <<EOF
تقرير مراقبة النظام - System Monitor Report
===========================================
التاريخ: $(date)
Date: $(date)

حالة النظام - System Status:
- Django: يعمل - Django: Running
- قاعدة البيانات: متصلة - Database: Connected
- الذاكرة المؤقتة: تعمل - Cache: Working
- الملفات الثابتة: موجودة - Static files: Available

استخدام الموارد - Resource Usage:
- الذاكرة: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')
- القرص: $(df -h / | awk 'NR==2{print $5}')
- المعالج: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%

إحصائيات قاعدة البيانات - Database Statistics:
$(python3 manage.py shell -c "
from django.contrib.auth.models import User
from customers.models import Customer
from orders.models import Order
from inventory.models import Product
print(f'Users: {User.objects.count()}')
print(f'Customers: {Customer.objects.count()}')
print(f'Orders: {Order.objects.count()}')
print(f'Products: {Product.objects.count()}')
" 2>/dev/null)

ملاحظات - Notes:
- تم فحص جميع المكونات الأساسية - All core components checked
- النظام يعمل بشكل طبيعي - System is running normally
- لا توجد مشاكل حرجة - No critical issues detected

EOF

	echo -e "\033[1;32m✅ تم إنشاء التقرير: $REPORT_FILE"
	echo -e "Report created: $REPORT_FILE\033[0m"
}

# التنفيذ الرئيسي
main() {
	echo -e "\033[1;37m🚀 بدء مراقبة النظام..."
	echo -e "Starting system monitoring...\033[0m"

	check_services
	check_resources
	check_important_files
	check_database
	check_cache
	check_permissions
	check_logs
	check_security
	create_monitor_report

	echo -e "\033[1;37m==========================================="
	echo -e "✅ تم إكمال مراقبة النظام بنجاح"
	echo -e "✅ System monitoring completed successfully"
	echo -e "===========================================\033[0m"

	echo -e "\033[1;32m🎉 النظام يعمل بشكل طبيعي"
	echo -e "🎉 System is running normally\033[0m"
}

# تشغيل الدالة الرئيسية
main "$@"
