#!/bin/bash

echo "🚀 تشغيل خادم Django..."

# تفعيل البيئة الافتراضية
source venv/bin/activate

# جمع الملفات الثابتة (إذا لزم الأمر)
echo "📦 جمع الملفات الثابتة..."
python manage.py collectstatic --noinput --clear 2>&1 | grep -E "copied|static files"

# تشغيل الخادم
echo "✅ بدء الخادم على http://localhost:8000"
python manage.py runserver 0.0.0.0:8000
