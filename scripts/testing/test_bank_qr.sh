#!/bin/bash

# ===========================================
# سكريبت تجريبي لاختبار نظام QR للحسابات البنكية
# Bank QR System - Quick Test Script
# ===========================================

echo "🏦 نظام QR للحسابات البنكية - اختبار سريع"
echo "========================================="
echo ""

# الألوان
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. تطبيق Migration
echo -e "${BLUE}📦 الخطوة 1: تطبيق Migration...${NC}"
python manage.py migrate accounting

echo ""
echo -e "${GREEN}✅ تم تطبيق Migration${NC}"
echo ""

# 2. إنشاء حساب بنك CIB تجريبي
echo -e "${BLUE}🏛️  الخطوة 2: إنشاء حساب بنك CIB...${NC}"

python manage.py shell << EOF
from accounting.models import BankAccount

# حذف الحساب التجريبي إن وجد
BankAccount.objects.filter(unique_code='CIB001').delete()

# إنشاء حساب جديد
bank = BankAccount.objects.create(
    bank_name="بنك CIB شركات",
    bank_name_en="CIB Corporate Bank",
    account_number="100054913731",
    iban="EG380002000534913731000100001",
    swift_code="CIBEEGCX",
    branch="فرع الجيزة",
    branch_en="Giza Branch",
    account_holder="الخواجة",
    account_holder_en="Elkhawaga",
    currency="EGP",
    is_primary=True,
    is_active=True,
    show_in_qr=True,
    display_order=1,
)

print(f"\n{'='*50}")
print(f"✅ تم إنشاء الحساب البنكي بنجاح!")
print(f"{'='*50}")
print(f"📌 الكود الفريد: {bank.unique_code}")
print(f"🏦 اسم البنك: {bank.bank_name}")
print(f"🔢 رقم الحساب: {bank.account_number}")
print(f"🌐 IBAN: {bank.iban}")
print(f"🔐 SWIFT: {bank.swift_code}")
print(f"📍 الفرع: {bank.branch}")
print(f"{'='*50}\n")

EOF

echo ""
echo -e "${GREEN}✅ تم إنشاء الحساب${NC}"
echo ""

# 3. توليد QR Code
echo -e "${BLUE}🔲 الخطوة 3: توليد QR Code...${NC}"
python manage.py generate_bank_qr

echo ""
echo -e "${GREEN}✅ تم توليد QR Code${NC}"
echo ""

# 4. عرض النتائج
echo -e "${YELLOW}════════════════════════════════════════${NC}"
echo -e "${YELLOW}           🎉 تم بنجاح!                ${NC}"
echo -e "${YELLOW}════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}📱 الروابط المتاحة:${NC}"
echo ""
echo -e "  ${BLUE}🔗 Admin Panel:${NC}"
echo -e "     http://localhost:8000/admin/accounting/bankaccount/"
echo ""
echo -e "  ${BLUE}🔗 صفحة حساب CIB:${NC}"
echo -e "     http://localhost:8000/accounting/bank-qr/CIB001/"
echo ""
echo -e "  ${BLUE}🔗 جميع الحسابات:${NC}"
echo -e "     http://localhost:8000/accounting/bank-qr-all/"
echo ""
echo -e "${YELLOW}════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}📝 الخطوات التالية:${NC}"
echo ""
echo "  1. افتح Admin Panel وراجع الحساب المضاف"
echo "  2. اختبر صفحة QR المحلية"
echo "  3. عند الجاهزية، نفذ:"
echo -e "     ${BLUE}python manage.py sync_bank_accounts${NC}"
echo "  4. انشر Cloudflare Worker:"
echo -e "     ${BLUE}cd cloudflare-worker && wrangler deploy${NC}"
echo ""
echo -e "${YELLOW}════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✨ النظام جاهز للاستخدام!${NC}"
echo ""
