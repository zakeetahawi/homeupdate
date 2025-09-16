#!/bin/bash

# مراقبة اللوغات النظيفة في الوقت الفعلي

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${GREEN}🔍 مراقبة اللوغات النظيفة${NC}"
echo "=================================="
echo -e "${BLUE}📝 Django: logs/django.log${NC}"
echo -e "${PURPLE}⚙️ Celery: logs/celery_fixed.log${NC}"
echo -e "${RED}❌ Errors: logs/errors.log${NC}"
echo "=================================="
echo -e "${YELLOW}اضغط Ctrl+C للتوقف${NC}"
echo ""

# مراقبة متعددة للوغات
tail -f logs/django.log logs/celery_fixed.log logs/errors.log 2>/dev/null | while read line; do
    # تلوين الرسائل حسب النوع
    if [[ $line == *"ERROR"* ]] || [[ $line == *"❌"* ]]; then
        echo -e "${RED}$line${NC}"
    elif [[ $line == *"SUCCESS"* ]] || [[ $line == *"✅"* ]] || [[ $line == *"succeeded"* ]]; then
        echo -e "${GREEN}$line${NC}"
    elif [[ $line == *"WARNING"* ]] || [[ $line == *"⚠️"* ]]; then
        echo -e "${YELLOW}$line${NC}"
    elif [[ $line == *"upload"* ]] || [[ $line == *"رفع"* ]] || [[ $line == *"📤"* ]]; then
        echo -e "${PURPLE}$line${NC}"
    elif [[ $line == *"INFO"* ]] || [[ $line == *"تم"* ]]; then
        echo -e "${BLUE}$line${NC}"
    else
        echo "$line"
    fi
done
