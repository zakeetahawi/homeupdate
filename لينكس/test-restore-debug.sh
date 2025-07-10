#!/bin/bash

# سكريبت اختبار نظام الاستعادة مع التشخيص
echo "🔍 بدء اختبار نظام الاستعادة مع التشخيص..."

# تشغيل الخادم مع مراقبة الرسائل
cd /home/zakee/homeupdate

echo "🚀 تشغيل الخادم..."
echo "📋 ملاحظة: راقب الرسائل التشخيصية في الطرفية"
echo "🌐 افتح المتصفح على: http://localhost:8000/odoo-db-manager/backups/upload/"
echo "🔍 افتح أدوات المطور (F12) وانتقل لتبويب Console"
echo "📁 جرب رفع ملف نسخة احتياطية"
echo ""
echo "الرسائل التشخيصية:"
echo "- [DEBUG] في الطرفية: رسائل الخادم"
echo "- [DEBUG] في Console: رسائل JavaScript"
echo ""
echo "⏹️ اضغط Ctrl+C لإيقاف الخادم"
echo ""

# تشغيل الخادم مع عرض جميع الرسائل
python manage.py runserver 0.0.0.0:8000 