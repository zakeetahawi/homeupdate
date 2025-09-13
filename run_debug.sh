#!/bin/bash
# Script لتشغيل الخادم في وضع التطوير مع عرض الأخطاء

echo "🚀 بدء تشغيل الخادم في وضع التطوير..."
echo "=================================================="

# تعيين متغيرات البيئة لوضع التطوير
export DEBUG=True
export ALLOWED_HOSTS="localhost,127.0.0.1,192.168.2.25,*.trycloudflare.com,*.ngrok-free.app,testserver"

# تفعيل البيئة الافتراضية
source venv/bin/activate

# التحقق من الإعدادات
echo "🔧 فحص إعدادات النظام..."
python test_debug_mode.py

echo ""
echo "🌐 بدء تشغيل الخادم على http://127.0.0.1:8000"
echo "📌 ستظهر الأخطاء التفصيلية في المتصفح"
echo "📌 اضغط Ctrl+C لإيقاف الخادم"
echo ""

# تشغيل الخادم
python manage.py runserver 0.0.0.0:8000
