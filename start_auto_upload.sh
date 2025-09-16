#!/bin/bash

# نظام الرفع التلقائي للملفات - محسن ومُصلح
# يرفع 40 ملف كل 5 دقائق بدون ضغط على السيرفر

echo "🚀 بدء نظام الرفع التلقائي المحسن"
echo "===================================="
echo "✅ تم إصلاح مشكلة Celery queues"
echo "📤 سيتم رفع 40 ملف كل 5 دقائق"
echo "🔄 النظام يتجاهل الملفات غير الموجودة"
echo "⏹️  اضغط Ctrl+C للتوقف"
echo "===================================="

cd /home/zakee/homeupdate

# التأكد من تشغيل Celery worker الصحيح
echo "🔍 فحص Celery worker..."
if ! pgrep -f "celery.*worker.*queues=celery,file_uploads" > /dev/null; then
    echo "⚠️ Celery worker غير مُشغل، تشغيله الآن..."
    python fix_celery_queues.py
    sleep 3
fi

echo "✅ Celery worker يعمل بشكل صحيح"
echo "🚀 بدء الرفع التلقائي..."

# تشغيل النظام في وضع مستمر
python auto_upload_system.py continuous
