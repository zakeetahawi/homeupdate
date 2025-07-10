#!/bin/bash
# اختبار مباشر لرفع الملف

echo "🔍 اختبار رفع الملف مباشرة..."

# التحقق من وجود ملف الاختبار
if [ ! -f "test_backup_small.json" ]; then
    echo "❌ ملف الاختبار غير موجود"
    echo "📋 إنشاء ملف اختبار..."
    cat > test_backup_small.json << 'TESTEOF'
[
    {
        "model": "auth.user",
        "pk": 999,
        "fields": {
            "username": "test_user",
            "email": "test@example.com",
            "is_active": true
        }
    }
]
TESTEOF
    echo "✅ تم إنشاء ملف الاختبار"
fi

# الحصول على CSRF token
echo "🔑 الحصول على CSRF token..."
CSRF_TOKEN=$(curl -s -c cookies.txt "http://127.0.0.1:8000/odoo-db-manager/backups/upload/" | grep -oP 'name="csrfmiddlewaretoken" value="\K[^"]*')

if [ -z "$CSRF_TOKEN" ]; then
    echo "❌ فشل في الحصول على CSRF token"
    exit 1
fi

echo "✅ CSRF token: ${CSRF_TOKEN:0:20}..."

# إرسال الملف
echo "📤 إرسال الملف..."
RESPONSE=$(curl -s -b cookies.txt -X POST \
    -H "X-Requested-With: XMLHttpRequest" \
    -F "csrfmiddlewaretoken=$CSRF_TOKEN" \
    -F "backup_file=@test_backup_small.json" \
    -F "database_id=1" \
    -F "backup_type=full" \
    -F "clear_data=off" \
    -F "session_id=test_$(date +%s)" \
    "http://127.0.0.1:8000/odoo-db-manager/backups/upload/")

echo "📨 استجابة الخادم:"
echo "$RESPONSE"

# تنظيف
rm -f cookies.txt

echo "✅ انتهى الاختبار"
