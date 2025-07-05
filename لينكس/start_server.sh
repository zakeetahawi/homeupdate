#!/bin/bash
# HomeUpdate CRM Server (Linux)

echo "==============================================="
echo "          HomeUpdate CRM System"
echo "==============================================="
echo

# (اختياري) تنفيذ سكريبت تهيئة إذا كان موجوداً
if [ -f setup-aliases.sh ]; then
    bash setup-aliases.sh
fi

echo "بدء تشغيل خادم Django..."
echo

echo "الخادم سيعمل على: http://localhost:8000"
echo "لوقف الخادم اضغط Ctrl+C"
echo "==============================================="

# تشغيل خادم Django
python3 manage.py runserver
