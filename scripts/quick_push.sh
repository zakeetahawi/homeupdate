#!/bin/bash
# سكريبت سريع لإضافة وcommit ورفع التحديثات

# التحقق من وجود رسالة commit
if [ -z "$1" ]; then
    echo "❌ يرجى تقديم رسالة commit"
    echo "الاستخدام: ./scripts/quick_push.sh \"رسالة التحديث\""
    exit 1
fi

COMMIT_MESSAGE="$1"
CURRENT_BRANCH=$(git branch --show-current)

echo "🚀 رفع سريع للتحديثات"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 الفرع: $CURRENT_BRANCH"
echo "💬 الرسالة: $COMMIT_MESSAGE"
echo ""

# إضافة جميع التغييرات
echo "📦 إضافة الملفات..."
git add .

# عرض الملفات المضافة
echo ""
echo "📝 الملفات المعدلة:"
git status --short

# عمل commit
echo ""
echo "💾 عمل commit..."
git commit -m "$COMMIT_MESSAGE"

# رفع التحديثات
echo ""
echo "⬆️  رفع التحديثات..."
if git push; then
    echo ""
    echo "✅ تم رفع التحديثات بنجاح!"
    echo "🔗 الفرع: $CURRENT_BRANCH"
else
    echo ""
    echo "⚠️  فشل الرفع. جرب:"
    echo "   git push -u origin $CURRENT_BRANCH"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ تم بنجاح!"
