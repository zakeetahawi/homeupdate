#!/bin/bash
# سكريبت لاستقبال التحديثات من الفرع الأصلي (main) مع البقاء في الفرع الحالي

echo "🔄 استقبال التحديثات من الفرع الأصلي..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# الحصول على اسم الفرع الحالي
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 الفرع الحالي: $CURRENT_BRANCH"

# التأكد من أننا لسنا في main
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
    echo "⚠️  أنت في الفرع الأصلي! هذا السكريبت للفروع الفرعية فقط."
    exit 1
fi

# جلب آخر التحديثات من الريبو
echo ""
echo "📥 جلب التحديثات من origin..."
git fetch origin

# عرض الفروق
echo ""
echo "📊 الفروق بين فرعك والفرع الأصلي:"
git log HEAD..origin/main --oneline --max-count=10

# سؤال المستخدم
echo ""
read -p "هل تريد دمج التحديثات من main؟ (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔀 دمج التحديثات من origin/main..."
    
    # محاولة الدمج
    if git merge origin/main --no-edit; then
        echo ""
        echo "✅ تم دمج التحديثات بنجاح!"
        echo "📍 أنت الآن في الفرع: $CURRENT_BRANCH"
        echo "📦 مع آخر تحديثات من main"
    else
        echo ""
        echo "⚠️  حدثت تعارضات! يرجى حلها يدوياً:"
        echo "   1. افتح الملفات المتعارضة"
        echo "   2. حل التعارضات"
        echo "   3. نفذ: git add ."
        echo "   4. نفذ: git commit"
        exit 1
    fi
else
    echo ""
    echo "❌ تم إلغاء الدمج"
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ الخطوات التالية:"
echo "   1. راجع التغييرات: git log --oneline -5"
echo "   2. اختبر المشروع"
echo "   3. ارفع التحديثات: git push"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
