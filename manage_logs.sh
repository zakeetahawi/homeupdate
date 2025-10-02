#!/bin/bash
# سكريبت لإدارة ملفات Log

# الألوان
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# مسار مجلد Logs
LOGS_DIR="logs"

# دالة لعرض القائمة الرئيسية
show_menu() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     📋 إدارة ملفات Log - Log Manager  ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}1)${NC} عرض جميع ملفات Log (List all logs)"
    echo -e "${GREEN}2)${NC} عرض آخر 50 سطر من ملف (View last 50 lines)"
    echo -e "${GREEN}3)${NC} متابعة ملف Log مباشرة (Follow log file)"
    echo -e "${GREEN}4)${NC} البحث في ملف Log (Search in log)"
    echo -e "${GREEN}5)${NC} عرض حجم الملفات (Show file sizes)"
    echo -e "${GREEN}6)${NC} تنظيف ملفات Log القديمة (Clean old logs)"
    echo -e "${GREEN}7)${NC} أرشفة ملفات Log (Archive logs)"
    echo -e "${GREEN}8)${NC} عرض الأخطاء فقط (Show errors only)"
    echo -e "${GREEN}9)${NC} عرض إحصائيات Log (Show log statistics)"
    echo -e "${GREEN}10)${NC} مقارنة ملفين Log (Compare two logs)"
    echo -e "${RED}0)${NC} خروج (Exit)"
    echo ""
    echo -n "اختر رقم الخيار (Choose option): "
}

# دالة لعرض جميع ملفات Log
list_logs() {
    echo -e "\n${CYAN}📋 ملفات Log المتاحة:${NC}\n"
    if [ -d "$LOGS_DIR" ]; then
        ls -lh "$LOGS_DIR"/*.log 2>/dev/null | awk '{print $9, "("$5")"}'
    else
        echo -e "${RED}❌ مجلد logs غير موجود${NC}"
    fi
}

# دالة لعرض آخر سطور من ملف
view_last_lines() {
    list_logs
    echo ""
    echo -n "أدخل اسم الملف (Enter filename): "
    read filename
    
    if [ -f "$LOGS_DIR/$filename" ]; then
        echo -e "\n${CYAN}📄 آخر 50 سطر من $filename:${NC}\n"
        tail -n 50 "$LOGS_DIR/$filename"
    else
        echo -e "${RED}❌ الملف غير موجود${NC}"
    fi
}

# دالة لمتابعة ملف Log
follow_log() {
    list_logs
    echo ""
    echo -n "أدخل اسم الملف (Enter filename): "
    read filename
    
    if [ -f "$LOGS_DIR/$filename" ]; then
        echo -e "\n${CYAN}👁️  متابعة $filename (اضغط Ctrl+C للإيقاف):${NC}\n"
        tail -f "$LOGS_DIR/$filename"
    else
        echo -e "${RED}❌ الملف غير موجود${NC}"
    fi
}

# دالة للبحث في ملف Log
search_log() {
    list_logs
    echo ""
    echo -n "أدخل اسم الملف (Enter filename): "
    read filename
    echo -n "أدخل كلمة البحث (Enter search term): "
    read search_term
    
    if [ -f "$LOGS_DIR/$filename" ]; then
        echo -e "\n${CYAN}🔍 نتائج البحث عن '$search_term' في $filename:${NC}\n"
        grep -n --color=always "$search_term" "$LOGS_DIR/$filename" || echo -e "${YELLOW}⚠️  لم يتم العثور على نتائج${NC}"
    else
        echo -e "${RED}❌ الملف غير موجود${NC}"
    fi
}

# دالة لعرض حجم الملفات
show_sizes() {
    echo -e "\n${CYAN}📊 أحجام ملفات Log:${NC}\n"
    if [ -d "$LOGS_DIR" ]; then
        du -h "$LOGS_DIR"/*.log 2>/dev/null | sort -h
        echo ""
        echo -e "${GREEN}الحجم الإجمالي:${NC}"
        du -sh "$LOGS_DIR"
    else
        echo -e "${RED}❌ مجلد logs غير موجود${NC}"
    fi
}

# دالة لتنظيف ملفات Log القديمة
clean_logs() {
    echo -e "\n${YELLOW}⚠️  تحذير: سيتم حذف محتوى جميع ملفات Log${NC}"
    echo -n "هل أنت متأكد؟ (y/N): "
    read confirm
    
    if [[ $confirm =~ ^[Yy]$ ]]; then
        for logfile in "$LOGS_DIR"/*.log; do
            if [ -f "$logfile" ]; then
                > "$logfile"
                echo -e "${GREEN}✅ تم تنظيف: $logfile${NC}"
            fi
        done
        echo -e "\n${GREEN}✅ تم تنظيف جميع ملفات Log${NC}"
    else
        echo -e "${BLUE}ℹ️  تم الإلغاء${NC}"
    fi
}

# دالة لأرشفة ملفات Log
archive_logs() {
    ARCHIVE_DIR="$LOGS_DIR/archive"
    mkdir -p "$ARCHIVE_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    ARCHIVE_FILE="$ARCHIVE_DIR/logs_backup_$TIMESTAMP.tar.gz"
    
    echo -e "\n${CYAN}📦 جاري أرشفة ملفات Log...${NC}"
    
    tar -czf "$ARCHIVE_FILE" "$LOGS_DIR"/*.log 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ تم إنشاء الأرشيف: $ARCHIVE_FILE${NC}"
        
        echo -n "هل تريد تنظيف الملفات الأصلية؟ (y/N): "
        read clean_confirm
        
        if [[ $clean_confirm =~ ^[Yy]$ ]]; then
            for logfile in "$LOGS_DIR"/*.log; do
                if [ -f "$logfile" ]; then
                    > "$logfile"
                fi
            done
            echo -e "${GREEN}✅ تم تنظيف الملفات الأصلية${NC}"
        fi
    else
        echo -e "${RED}❌ فشل إنشاء الأرشيف${NC}"
    fi
}

# دالة لعرض الأخطاء فقط
show_errors() {
    echo -e "\n${CYAN}❌ الأخطاء في جميع ملفات Log:${NC}\n"
    
    if [ -d "$LOGS_DIR" ]; then
        for logfile in "$LOGS_DIR"/*.log; do
            if [ -f "$logfile" ]; then
                errors=$(grep -i "error\|exception\|critical" "$logfile" 2>/dev/null)
                if [ ! -z "$errors" ]; then
                    echo -e "${RED}═══ $(basename $logfile) ═══${NC}"
                    echo "$errors" | tail -n 10
                    echo ""
                fi
            fi
        done
    else
        echo -e "${RED}❌ مجلد logs غير موجود${NC}"
    fi
}

# دالة لعرض إحصائيات Log
show_statistics() {
    echo -e "\n${CYAN}📊 إحصائيات ملفات Log:${NC}\n"
    
    if [ -d "$LOGS_DIR" ]; then
        for logfile in "$LOGS_DIR"/*.log; do
            if [ -f "$logfile" ]; then
                filename=$(basename "$logfile")
                total_lines=$(wc -l < "$logfile")
                info_count=$(grep -c "INFO" "$logfile" 2>/dev/null || echo 0)
                warning_count=$(grep -c "WARNING" "$logfile" 2>/dev/null || echo 0)
                error_count=$(grep -c "ERROR" "$logfile" 2>/dev/null || echo 0)
                
                echo -e "${PURPLE}━━━ $filename ━━━${NC}"
                echo -e "  ${BLUE}إجمالي الأسطر:${NC} $total_lines"
                echo -e "  ${GREEN}INFO:${NC} $info_count"
                echo -e "  ${YELLOW}WARNING:${NC} $warning_count"
                echo -e "  ${RED}ERROR:${NC} $error_count"
                echo ""
            fi
        done
    else
        echo -e "${RED}❌ مجلد logs غير موجود${NC}"
    fi
}

# دالة لمقارنة ملفين
compare_logs() {
    list_logs
    echo ""
    echo -n "أدخل اسم الملف الأول (Enter first filename): "
    read file1
    echo -n "أدخل اسم الملف الثاني (Enter second filename): "
    read file2
    
    if [ -f "$LOGS_DIR/$file1" ] && [ -f "$LOGS_DIR/$file2" ]; then
        echo -e "\n${CYAN}🔄 مقارنة $file1 و $file2:${NC}\n"
        diff -u "$LOGS_DIR/$file1" "$LOGS_DIR/$file2" | head -n 50
    else
        echo -e "${RED}❌ أحد الملفات غير موجود${NC}"
    fi
}

# الحلقة الرئيسية
while true; do
    show_menu
    read choice
    
    case $choice in
        1) list_logs ;;
        2) view_last_lines ;;
        3) follow_log ;;
        4) search_log ;;
        5) show_sizes ;;
        6) clean_logs ;;
        7) archive_logs ;;
        8) show_errors ;;
        9) show_statistics ;;
        10) compare_logs ;;
        0) 
            echo -e "\n${GREEN}👋 مع السلامة!${NC}\n"
            exit 0
            ;;
        *)
            echo -e "\n${RED}❌ خيار غير صحيح${NC}"
            ;;
    esac
    
    echo ""
    echo -n "اضغط Enter للمتابعة..."
    read
done

