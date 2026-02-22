#!/bin/bash
# سكربت النشر - نظام الخواجه
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}══════════════════════════════════════${NC}"
echo -e "${BLUE}   نشر تحديثات نظام الخواجه${NC}"
echo -e "${BLUE}══════════════════════════════════════${NC}"

# 1. سحب التحديثات
echo -e "\n${BLUE}[1/4] سحب التحديثات من GitHub...${NC}"
git pull origin main
echo -e "${GREEN}  ✅ تم${NC}"

# 2. تثبيت المتطلبات فقط إذا تغيّر requirements.txt
echo -e "\n${BLUE}[2/4] فحص المتطلبات...${NC}"
REQ_HASH_FILE="$PROJECT_DIR/.req_hash"
CURRENT_HASH=$(md5sum requirements.txt | cut -d' ' -f1)
SAVED_HASH=$(cat "$REQ_HASH_FILE" 2>/dev/null || echo "")

if [ "$CURRENT_HASH" != "$SAVED_HASH" ]; then
    echo -e "${YELLOW}  تغيّرت المتطلبات - جاري التثبيت...${NC}"
    pip install -r requirements.txt
    echo "$CURRENT_HASH" > "$REQ_HASH_FILE"
    echo -e "${GREEN}  ✅ تم تثبيت المتطلبات${NC}"
else
    echo -e "${GREEN}  ✅ لا يوجد تغيير في المتطلبات${NC}"
fi

# 3. تطبيق الـ Migrations
echo -e "\n${BLUE}[3/4] تطبيق Migrations...${NC}"
python manage.py migrate --noinput
echo -e "${GREEN}  ✅ تم${NC}"

# 4. إعادة تشغيل الخدمة
echo -e "\n${BLUE}[4/4] إعادة تشغيل الخدمة...${NC}"
bash "$PROJECT_DIR/لينكس/stop-service.sh" 2>/dev/null || true
sleep 2
bash "$PROJECT_DIR/لينكس/start-service.sh"
echo -e "${GREEN}  ✅ تم${NC}"

echo -e "\n${BLUE}══════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ تم النشر بنجاح${NC}"
echo -e "${BLUE}══════════════════════════════════════${NC}\n"
