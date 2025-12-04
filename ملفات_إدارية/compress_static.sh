#!/bin/bash
# سكريبت ضغط وتحسين الملفات الثابتة

echo "🚀 ضغط وتحسين الملفات الثابتة"
echo "================================"

# التحقق من وجود الأدوات
command -v terser >/dev/null 2>&1 || {
    echo "⚠️ terser غير مثبت. جاري التثبيت..."
    npm install -g terser 2>/dev/null || echo "❌ فشل تثبيت terser"
}

command -v cssnano >/dev/null 2>&1 || {
    echo "⚠️ cssnano غير مثبت. تخطي ضغط CSS..."
}

cd /home/zakee/homeupdate

# ضغط ملفات JS
echo ""
echo "📜 ضغط ملفات JavaScript..."
find static/js -name "*.js" ! -name "*.min.js" -type f | while read file; do
    minified="${file%.js}.min.js"
    if command -v terser >/dev/null 2>&1; then
        terser "$file" -o "$minified" --compress --mangle 2>/dev/null && \
        echo "  ✅ $file → $minified"
    fi
done

# ضغط ملفات CSS
echo ""
echo "📄 ضغط ملفات CSS..."
find static/css -name "*.css" ! -name "*.min.css" -type f | while read file; do
    minified="${file%.css}.min.css"
    # استخدام cssnano أو بديل بسيط
    if command -v cssnano >/dev/null 2>&1; then
        cssnano "$file" "$minified" 2>/dev/null && \
        echo "  ✅ $file → $minified"
    else
        # ضغط بسيط بإزالة التعليقات والمسافات
        sed 's/\/\*.*\*\///g' "$file" | \
        tr -d '\n' | \
        sed 's/  */ /g' > "$minified" && \
        echo "  ✅ $file → $minified (basic)"
    fi
done

echo ""
echo "📊 إحصائيات:"
du -sh static/js static/css 2>/dev/null || echo "لا توجد ملفات"

echo ""
echo "✅ تم الانتهاء!"
