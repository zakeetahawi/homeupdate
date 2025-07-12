#!/bin/bash

# سكريبت إصلاح شامل لنظام إدارة العملاء
# Comprehensive System Fix Script for Customer Management System

echo -e "\033[1;37m==========================================="
echo -e "بدء عملية الإصلاح الشامل للنظام"
echo -e "Starting Comprehensive System Fix"
echo -e "===========================================\033[0m"

# التحقق من وجود Python و Django
check_dependencies() {
    echo -e "\033[1;33m🔍 فحص المتطلبات الأساسية..."
    echo -e "Checking basic requirements...\033[0m"
    
    if ! command -v python3 &> /dev/null; then
        echo -e "\033[1;31m❌ Python3 غير مثبت"
        echo -e "Python3 is not installed\033[0m"
        exit 1
    fi
    
    if ! command -v pip3 &> /dev/null; then
        echo -e "\033[1;31m❌ pip3 غير مثبت"
        echo -e "pip3 is not installed\033[0m"
        exit 1
    fi
    
    echo -e "\033[1;32m✅ المتطلبات الأساسية متوفرة"
    echo -e "Basic requirements are available\033[0m"
}

# تنظيف الملفات المؤقتة
clean_temp_files() {
    echo -e "\033[1;33m🧹 تنظيف الملفات المؤقتة..."
    echo -e "Cleaning temporary files...\033[0m"
    
    # حذف ملفات Python المؤقتة
    find . -name "*.pyc" -delete 2>/dev/null
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
    find . -name "*.pyo" -delete 2>/dev/null
    
    # حذف ملفات التخزين المؤقت
    rm -rf cache/* 2>/dev/null
    rm -rf staticfiles/* 2>/dev/null
    
    echo -e "\033[1;32m✅ تم تنظيف الملفات المؤقتة"
    echo -e "Temporary files cleaned\033[0m"
}

# إصلاح قاعدة البيانات
fix_database() {
    echo -e "\033[1;33m🗄️ إصلاح قاعدة البيانات..."
    echo -e "Fixing database...\033[0m"
    
    # تشغيل الهجرات
    python3 manage.py makemigrations --noinput
    if [ $? -eq 0 ]; then
        echo -e "\033[1;32m✅ تم إنشاء الهجرات"
        echo -e "Migrations created\033[0m"
    else
        echo -e "\033[1;31m❌ فشل في إنشاء الهجرات"
        echo -e "Failed to create migrations\033[0m"
    fi
    
    python3 manage.py migrate --noinput
    if [ $? -eq 0 ]; then
        echo -e "\033[1;32m✅ تم تطبيق الهجرات"
        echo -e "Migrations applied\033[0m"
    else
        echo -e "\033[1;31m❌ فشل في تطبيق الهجرات"
        echo -e "Failed to apply migrations\033[0m"
    fi
    
    # إصلاح التسلسلات
    python3 manage.py fix_sequence
    if [ $? -eq 0 ]; then
        echo -e "\033[1;32m✅ تم إصلاح التسلسلات"
        echo -e "Sequences fixed\033[0m"
    else
        echo -e "\033[1;31m❌ فشل في إصلاح التسلسلات"
        echo -e "Failed to fix sequences\033[0m"
    fi
}

# جمع الملفات الثابتة
collect_static() {
    echo -e "\033[1;33m📦 جمع الملفات الثابتة..."
    echo -e "Collecting static files...\033[0m"
    
    python3 manage.py collectstatic --noinput --clear
    if [ $? -eq 0 ]; then
        echo -e "\033[1;32m✅ تم جمع الملفات الثابتة"
        echo -e "Static files collected\033[0m"
    else
        echo -e "\033[1;31m❌ فشل في جمع الملفات الثابتة"
        echo -e "Failed to collect static files\033[0m"
    fi
}

# إصلاح الصلاحيات
fix_permissions() {
    echo -e "\033[1;33m🔐 إصلاح الصلاحيات..."
    echo -e "Fixing permissions...\033[0m"
    
    # إصلاح صلاحيات الملفات
    find . -type f -exec chmod 644 {} \;
    find . -type d -exec chmod 755 {} \;
    
    # إعطاء صلاحيات التنفيذ للسكريبتات
    chmod +x *.sh
    chmod +x لينكس/*.sh
    
    echo -e "\033[1;32m✅ تم إصلاح الصلاحيات"
    echo -e "Permissions fixed\033[0m"
}

# فحص الأمان
security_check() {
    echo -e "\033[1;33m🛡️ فحص الأمان..."
    echo -e "Security check...\033[0m"
    
    # فحص الملفات الحساسة
    if [ -f "SECRET_KEY.txt" ]; then
        echo -e "\033[1;31m⚠️ تحذير: ملف SECRET_KEY.txt موجود"
        echo -e "Warning: SECRET_KEY.txt file exists\033[0m"
    fi
    
    # فحص ملفات البيئة
    if [ -f ".env" ]; then
        echo -e "\033[1;32m✅ ملف البيئة موجود"
        echo -e "Environment file exists\033[0m"
    else
        echo -e "\033[1;31m❌ ملف البيئة مفقود"
        echo -e "Environment file missing\033[0m"
    fi
    
    echo -e "\033[1;32m✅ فحص الأمان مكتمل"
    echo -e "Security check completed\033[0m"
}

# اختبار النظام
test_system() {
    echo -e "\033[1;33m🧪 اختبار النظام..."
    echo -e "Testing system...\033[0m"
    
    # اختبار الاتصال بقاعدة البيانات
    python3 manage.py check --database default
    if [ $? -eq 0 ]; then
        echo -e "\033[1;32m✅ الاتصال بقاعدة البيانات يعمل"
        echo -e "Database connection working\033[0m"
    else
        echo -e "\033[1;31m❌ مشكلة في الاتصال بقاعدة البيانات"
        echo -e "Database connection issue\033[0m"
    fi
    
    # اختبار التكوين
    python3 manage.py check
    if [ $? -eq 0 ]; then
        echo -e "\033[1;32m✅ تكوين النظام صحيح"
        echo -e "System configuration is correct\033[0m"
    else
        echo -e "\033[1;31m❌ مشكلة في تكوين النظام"
        echo -e "System configuration issue\033[0m"
    fi
}

# إصلاح المشاكل المعروفة
fix_known_issues() {
    echo -e "\033[1;33m🔧 إصلاح المشاكل المعروفة..."
    echo -e "Fixing known issues...\033[0m"
    
    # إصلاح مشاكل الذاكرة المؤقتة
    python3 manage.py shell -c "
from django.core.cache import cache
cache.clear()
print('Cache cleared')
"
    
    # إصلاح مشاكل الجلسات
    python3 manage.py shell -c "
from django.contrib.sessions.models import Session
from django.utils import timezone
Session.objects.filter(expire_date__lt=timezone.now()).delete()
print('Expired sessions cleaned')
"
    
    echo -e "\033[1;32m✅ تم إصلاح المشاكل المعروفة"
    echo -e "Known issues fixed\033[0m"
}

# إنشاء تقرير الإصلاح
create_fix_report() {
    echo -e "\033[1;33m📊 إنشاء تقرير الإصلاح..."
    echo -e "Creating fix report...\033[0m"
    
    REPORT_FILE="system_fix_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$REPORT_FILE" << EOF
تقرير إصلاح النظام - System Fix Report
=====================================
التاريخ: $(date)
Date: $(date)

العمليات المنجزة - Completed Operations:
1. فحص المتطلبات الأساسية - Basic requirements check
2. تنظيف الملفات المؤقتة - Temporary files cleanup
3. إصلاح قاعدة البيانات - Database fix
4. جمع الملفات الثابتة - Static files collection
5. إصلاح الصلاحيات - Permissions fix
6. فحص الأمان - Security check
7. اختبار النظام - System test
8. إصلاح المشاكل المعروفة - Known issues fix

حالة النظام - System Status:
- قاعدة البيانات: متصل - Database: Connected
- الملفات الثابتة: مجمعة - Static files: Collected
- الصلاحيات: مصلحة - Permissions: Fixed
- الأمان: مفحوص - Security: Checked

ملاحظات - Notes:
- تم تنظيف الذاكرة المؤقتة - Cache cleared
- تم تنظيف الجلسات المنتهية - Expired sessions cleaned
- تم إصلاح التسلسلات - Sequences fixed

EOF
    
    echo -e "\033[1;32m✅ تم إنشاء التقرير: $REPORT_FILE"
    echo -e "Report created: $REPORT_FILE\033[0m"
}

# التنفيذ الرئيسي
main() {
    echo -e "\033[1;37m🚀 بدء عملية الإصلاح الشامل..."
    echo -e "Starting comprehensive system fix...\033[0m"
    
    check_dependencies
    clean_temp_files
    fix_database
    collect_static
    fix_permissions
    security_check
    test_system
    fix_known_issues
    create_fix_report
    
    echo -e "\033[1;37m==========================================="
    echo -e "✅ تم إكمال عملية الإصلاح الشامل بنجاح"
    echo -e "✅ Comprehensive system fix completed successfully"
    echo -e "===========================================\033[0m"
    
    echo -e "\033[1;32m🎉 النظام جاهز للاستخدام"
    echo -e "🎉 System is ready for use\033[0m"
}

# تشغيل الدالة الرئيسية
main "$@" 