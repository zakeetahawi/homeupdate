#!/bin/bash

# سكريبت اختبار إصلاحات نظام التركيب
echo "🔧 بدء اختبار إصلاحات نظام التركيب..."
echo "=========================================="

# التحقق من تشغيل الخادم
echo "📋 التحقق من تشغيل الخادم..."
if curl -s http://127.0.0.1:8000/installations/ > /dev/null; then
    echo "✅ الخادم يعمل بنجاح"
else
    echo "❌ الخادم غير متاح. يرجى تشغيل Django server أولاً"
    echo "💡 استخدم الأمر: python manage.py runserver 127.0.0.1:8000"
    exit 1
fi

# تشغيل اختبار Python
echo "📋 تشغيل اختبار Python..."
python3 test_installation_fixes.py

echo ""
echo "🎉 تم الانتهاء من الاختبار!"
echo "🌐 يمكنك الوصول للنظام على: http://127.0.0.1:8000/installations/" 