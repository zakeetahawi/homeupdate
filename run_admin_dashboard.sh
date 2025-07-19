#!/bin/bash

# سكريبت تشغيل داش بورد الإدارة
# Admin Dashboard Run Script

echo -e "\033[1;36m🚀 بدء تشغيل نظام الخواجه مع داش بورد الإدارة...\033[0m"
echo -e "\033[1;33m📋 معلومات النظام:\033[0m"
echo -e "   • داش بورد إداري احترافي"
echo -e "   • تحليلات شاملة لجميع الأقسام"
echo -e "   • فلاتر متقدمة ومقارنات زمنية"
echo -e "   • رسوم بيانية تفاعلية"
echo -e "   • تصميم حديث ومتجاوب"
echo ""

# التحقق من وجود البيئة الافتراضية
if [ ! -d "venv" ]; then
    echo -e "\033[1;31m❌ البيئة الافتراضية غير موجودة\033[0m"
    echo -e "\033[1;33m💡 يرجى إنشاء البيئة الافتراضية أولاً:\033[0m"
    echo -e "   python -m venv venv"
    echo -e "   source venv/bin/activate"
    echo -e "   pip install -r requirements.txt"
    exit 1
fi

# تفعيل البيئة الافتراضية
echo -e "\033[1;32m✅ تفعيل البيئة الافتراضية...\033[0m"
source venv/bin/activate

# التحقق من تثبيت Django
if ! python -c "import django" 2>/dev/null; then
    echo -e "\033[1;31m❌ Django غير مثبت\033[0m"
    echo -e "\033[1;33m💡 يرجى تثبيت المتطلبات:\033[0m"
    echo -e "   pip install -r requirements.txt"
    exit 1
fi

echo -e "\033[1;32m✅ Django مثبت بنجاح\033[0m"

# فحص النظام
echo -e "\033[1;34m🔍 فحص النظام...\033[0m"
python manage.py check

if [ $? -eq 0 ]; then
    echo -e "\033[1;32m✅ فحص النظام نجح\033[0m"
else
    echo -e "\033[1;31m❌ فحص النظام فشل\033[0m"
    exit 1
fi

# تشغيل الهجرات إذا لزم الأمر
echo -e "\033[1;34m🔄 تشغيل الهجرات...\033[0m"
python manage.py migrate

# جمع الملفات الثابتة
echo -e "\033[1;34m📦 جمع الملفات الثابتة...\033[0m"
python manage.py collectstatic --noinput

echo ""
echo -e "\033[1;35m🎉 النظام جاهز للتشغيل!\033[0m"
echo ""
echo -e "\033[1;33m📋 معلومات الوصول:\033[0m"
echo -e "   🌐 الرابط الرئيسي: http://localhost:8000"
echo -e "   📊 داش بورد الإدارة: http://localhost:8000/admin-dashboard/"
echo -e "   🔧 لوحة الإدارة: http://localhost:8000/admin/"
echo ""
echo -e "\033[1;33m👤 للمدراء:\033[0m"
echo -e "   • تسجيل الدخول كمستخدم مدير"
echo -e "   • سيتم التوجيه تلقائياً للداش بورد"
echo -e "   • أو الوصول مباشرة عبر /admin-dashboard/"
echo ""
echo -e "\033[1;33m👥 للمستخدمين العاديين:\033[0m"
echo -e "   • الوصول للصفحة الرئيسية العادية"
echo -e "   • لا يمكن الوصول للداش بورد الإداري"
echo ""
echo -e "\033[1;36m🚀 بدء تشغيل الخادم...\033[0m"
echo -e "\033[1;33m💡 اضغط Ctrl+C لإيقاف الخادم\033[0m"
echo ""

# تشغيل الخادم
python manage.py runserver 0.0.0.0:8000 