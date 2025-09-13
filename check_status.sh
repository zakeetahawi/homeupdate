#!/bin/bash

# فحص حالة الرفع بسرعة

echo "📊 فحص حالة النظام"
echo "===================="

cd /home/zakee/homeupdate

# عرض الحالة العامة
python simple_monitor.py

echo ""
echo "🔍 فحص الملفات الموجودة..."
python simple_monitor.py files

echo ""
echo "⚙️ حالة Celery:"
celery -A crm inspect active | grep -E "(OK|empty|Error)" || echo "❌ Celery غير متاح"

echo ""
echo "===================="
echo "💡 لبدء الرفع التلقائي: ./start_auto_upload.sh"
echo "💡 لرفع دفعة واحدة: python auto_upload_system.py single"
