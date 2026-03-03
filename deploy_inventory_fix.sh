#!/bin/bash
# ══════════════════════════════════════════════════════════
# سكريبت نشر: إصلاح المخزون + نظام تسعير التفصيل
# تاريخ: 2026-03-03
# ══════════════════════════════════════════════════════════
#
# التغييرات المشمولة:
# 1. نظام تسعير التفصيل (TailoringTypePricing) بدلاً من double_meter
# 2. إصلاح الأرصدة السالبة في المخزون (IN/OUT case fix + full transfer)
# 3. حماية ذكية للمخزون (smart warehouse selection)
# 4. عرض تكلفة الخياطين حسب نظام التسعير في التقارير
#
# ══════════════════════════════════════════════════════════

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   نشر: إصلاح المخزون + تسعير التفصيل${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"

# تفعيل البيئة الافتراضية
source "$PROJECT_DIR/venv/bin/activate"

# ──────────────────────────────────────
# 1. سحب التحديثات
# ──────────────────────────────────────
echo -e "\n${BLUE}[1/6] سحب التحديثات من GitHub...${NC}"
git pull origin main
echo -e "${GREEN}  ✅ تم${NC}"

# ──────────────────────────────────────
# 2. تطبيق Migrations
# ──────────────────────────────────────
echo -e "\n${BLUE}[2/6] تطبيق Migrations...${NC}"
echo -e "${YELLOW}  → factory_accounting: جداول تسعير التفصيل${NC}"
python manage.py migrate factory_accounting --noinput
echo -e "${YELLOW}  → inventory: حقل original_warehouse${NC}"
python manage.py migrate inventory --noinput
echo -e "${GREEN}  ✅ تم${NC}"

# ──────────────────────────────────────
# 3. إصلاح الأرصدة السالبة في المخزون
# ──────────────────────────────────────
FIX_FLAG="$PROJECT_DIR/.fix_negative_stock_done"
if [ ! -f "$FIX_FLAG" ]; then
    echo -e "\n${YELLOW}[3/6] إصلاح الأرصدة السالبة في المخزون...${NC}"
    echo -e "${YELLOW}  → تصحيح أنواع المعاملات (IN/OUT → in/out)${NC}"
    echo -e "${YELLOW}  → إعادة حساب الأرصدة الجارية${NC}"
    echo -e "${YELLOW}  → نقل المعاملات من المخازن الخاطئة${NC}"
    python manage.py fix_negative_stock
    touch "$FIX_FLAG"
    echo -e "${GREEN}  ✅ تم إصلاح الأرصدة${NC}"
else
    echo -e "\n${GREEN}[3/6] ✅ إصلاح الأرصدة تم مسبقاً${NC}"
fi

# ──────────────────────────────────────
# 4. إعادة حساب تكاليف التفصيل
# ──────────────────────────────────────
RECALC_FLAG="$PROJECT_DIR/.recalc_tailoring_cost_done"
if [ ! -f "$RECALC_FLAG" ]; then
    echo -e "\n${YELLOW}[4/6] إعادة حساب تكاليف التفصيل لجميع البطاقات...${NC}"
    echo -e "${YELLOW}  → حساب total_tailoring_cost حسب نظام التسعير الجديد${NC}"
    echo -e "${YELLOW}  → حساب tailoring_cost_breakdown (تفاصيل لكل نوع)${NC}"
    python manage.py recalculate_unpaid_prices --tailoring-cost
    touch "$RECALC_FLAG"
    echo -e "${GREEN}  ✅ تم إعادة الحساب${NC}"
else
    echo -e "\n${GREEN}[4/6] ✅ إعادة حساب التكاليف تمت مسبقاً${NC}"
fi

# ──────────────────────────────────────
# 5. جمع الملفات الثابتة
# ──────────────────────────────────────
echo -e "\n${BLUE}[5/6] جمع الملفات الثابتة...${NC}"
python manage.py collectstatic --noinput --clear 2>/dev/null || python manage.py collectstatic --noinput
echo -e "${GREEN}  ✅ تم${NC}"

# ──────────────────────────────────────
# 6. إعادة تشغيل الخدمة
# ──────────────────────────────────────
echo -e "\n${BLUE}[6/6] إعادة تشغيل الخدمة...${NC}"
if systemctl is-active --quiet run-production; then
    sudo systemctl restart run-production
    echo -e "${GREEN}  ✅ تم إعادة تشغيل run-production${NC}"
else
    echo -e "${YELLOW}  ⚠️  الخدمة run-production غير نشطة — محاولة التشغيل...${NC}"
    bash "$PROJECT_DIR/لينكس/stop-service.sh" 2>/dev/null || true
    sleep 2
    bash "$PROJECT_DIR/لينكس/start-service.sh"
    echo -e "${GREEN}  ✅ تم التشغيل${NC}"
fi

echo -e "\n${BLUE}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ تم النشر بنجاح!${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════${NC}\n"
