#!/bin/bash
#
# سكريبت إصلاح أوامر التقطيع الموجهة لمستودعات خاطئة
# سكريبت تفاعلي
#

# الحصول على مسار المشروع
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# الانتقال إلى مجلد المشروع
cd "$PROJECT_DIR"

# تفعيل البيئة الافتراضية إذا وجدت
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# تشغيل سكريبت Python
python "$SCRIPT_DIR/fix_cutting_orders_warehouse.py"
