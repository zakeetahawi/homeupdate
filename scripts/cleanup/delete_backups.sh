#!/bin/bash
# حذف جميع الملفات الاحتياطية والمكررة
# تشغيل: bash scripts/cleanup/delete_backups.sh

echo "🗑️  بدء حذف الملفات الاحتياطية..."
echo ""

# عداد الملفات
count=0

# البحث عن الملفات الاحتياطية (باستثناء venv و .git)
backup_files=$(find . -type f \
    \( -name "*.backup" \
    -o -name "*_backup.py" \
    -o -name "*_temp.py" \
    -o -name "*.tmp" \
    -o -name "*_old.py" \
    -o -name "*.bak" \) \
    ! -path "./venv/*" \
    ! -path "./.git/*" \
    ! -path "./staticfiles/*" \
    ! -path "./media/*")

# عرض الملفات قبل الحذف
if [ -z "$backup_files" ]; then
    echo "✅ لا توجد ملفات احتياطية للحذف"
    exit 0
fi

echo "📋 الملفات التي سيتم حذفها:"
echo "================================"
echo "$backup_files"
echo "================================"
echo ""

# عد الملفات
file_count=$(echo "$backup_files" | wc -l)
echo "📊 إجمالي الملفات: $file_count"
echo ""

# طلب التأكيد
read -p "❓ هل تريد حذف هذه الملفات؟ (yes/no): " confirm

if [ "$confirm" = "yes" ] || [ "$confirm" = "y" ]; then
    echo ""
    echo "🗑️  جاري الحذف..."
    
    # حذف الملفات
    while IFS= read -r file; do
        if [ -n "$file" ]; then
            echo "  ✓ حذف: $file"
            rm "$file"
            ((count++))
        fi
    done <<< "$backup_files"
    
    echo ""
    echo "✅ تم حذف $count ملف بنجاح"
    
    # البحث عن الملفات الفارغة
    echo ""
    echo "🔍 البحث عن ملفات فارغة..."
    empty_files=$(find . -type f -empty \
        ! -path "./venv/*" \
        ! -path "./.git/*" \
        ! -path "./staticfiles/*" \
        ! -path "./media/*")
    
    if [ -n "$empty_files" ]; then
        echo "📋 ملفات فارغة وجدت:"
        echo "$empty_files"
        echo ""
        read -p "❓ حذف الملفات الفارغة؟ (yes/no): " confirm_empty
        
        if [ "$confirm_empty" = "yes" ] || [ "$confirm_empty" = "y" ]; then
            echo "$empty_files" | xargs rm
            echo "✅ تم حذف الملفات الفارغة"
        fi
    else
        echo "✅ لا توجد ملفات فارغة"
    fi
    
    echo ""
    echo "================================"
    echo "✅ اكتمل التنظيف بنجاح!"
    echo "📊 الملخص:"
    echo "  - ملفات احتياطية محذوفة: $count"
    echo "================================"
else
    echo ""
    echo "❌ تم الإلغاء - لم يتم حذف أي ملفات"
    exit 1
fi
