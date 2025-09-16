#!/bin/bash

# تشغيل الخادم بدون رسائل مشتتة
cd /home/zakee/homeupdate

echo "🚀 تشغيل الخادم..."
echo "📱 الرابط: http://127.0.0.1:8000"
echo "🔍 لمراقبة العمليات فقط - بدون رسائل مشتتة"
echo "---"

# تشغيل الخادم مع تصفية الرسائل
python manage.py runserver 127.0.0.1:8000 2>&1 | grep -E "(تم|بدء|✅|🚀|⚠️|❌|HTTP|Starting|Watching|Quit)" 