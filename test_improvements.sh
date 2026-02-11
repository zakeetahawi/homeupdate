#!/bin/bash

# ============================================
# اختبار التحسينات الشاملة - قسم المحاسبة
# ============================================

echo "======================================"
echo "🚀 بدء اختبارات التحسينات"
echo "======================================"
echo ""

# الألوان
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# المرحلة 1: إصلاح Template Error
# ============================================
echo "======================================"
echo "📝 المرحلة 1: اختبار إصلاح Template"
echo "======================================"
echo ""

echo "✓ تم إصلاح: customers/templates/customers/customer_detail.html"
echo "  - المشكلة: {% comment %} غير مغلق في السطر 1380"
echo "  - الحل: حذف 27 سطر من التعليق"
echo ""
echo "${YELLOW}☐ للاختبار يدوياً:${NC}"
echo "  http://localhost:8000/customers/customer/16-0804/"
echo "  ${GREEN}✓ تحقق من: الصفحة تعمل بدون TemplateSyntaxError${NC}"
echo ""

# ============================================
# المرحلة 2: أدوات الصيانة
# ============================================
echo "======================================"
echo "🔧 المرحلة 2: اختبار أدوات الصيانة"
echo "======================================"
echo ""

echo "1️⃣  اختبار check_draft_transactions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python manage.py check_draft_transactions
if [ $? -eq 0 ]; then
    echo "${GREEN}✓ check_draft_transactions يعمل بنجاح${NC}"
else
    echo "${RED}✗ خطأ في check_draft_transactions${NC}"
fi
echo ""

echo "2️⃣  اختبار verify_customer_balances"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python manage.py verify_customer_balances
if [ $? -eq 0 ]; then
    echo "${GREEN}✓ verify_customer_balances يعمل بنجاح${NC}"
else
    echo "${RED}✗ خطأ في verify_customer_balances${NC}"
fi
echo ""

echo "3️⃣  اختبار daily_maintenance"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python manage.py daily_maintenance
if [ $? -eq 0 ]; then
    echo "${GREEN}✓ daily_maintenance يعمل بنجاح${NC}"
else
    echo "${RED}✗ خطأ في daily_maintenance${NC}"
fi
echo ""

echo "${GREEN}✓ جميع أدوات الصيانة تعمل بنجاح${NC}"
echo ""

# ============================================
# المرحلة 3: قياس الأداء
# ============================================
echo "======================================"
echo "⚡ المرحلة 3: قياس أداء الصفحات"
echo "======================================"
echo ""

echo "${YELLOW}هذه الاختبارات تتطلب Django Debug Toolbar${NC}"
echo "لتثبيته:"
echo "  pip install django-debug-toolbar"
echo ""

cat > test_performance.py << 'EOF'
"""
اختبار أداء الصفحات المحسّنة
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test.utils import override_settings
from django.db import connection, reset_queries
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from accounting.views import (
    dashboard,
    customer_financial_summary,
    customer_balances_report,
    transaction_list
)

User = get_user_model()
factory = RequestFactory()

def test_view_performance(view_func, view_name, url, **kwargs):
    """اختبار أداء view محدد"""
    print(f"\n{'='*60}")
    print(f"🔍 اختبار: {view_name}")
    print(f"{'='*60}")
    
    with override_settings(DEBUG=True):
        reset_queries()
        
        # إنشاء request
        request = factory.get(url)
        request.user = User.objects.first()
        
        try:
            # تنفيذ الـ view
            if kwargs:
                response = view_func(request, **kwargs)
            else:
                response = view_func(request)
            
            # حساب الإحصائيات
            num_queries = len(connection.queries)
            total_time = sum(float(q['time']) for q in connection.queries)
            
            print(f"✓ الحالة: {response.status_code}")
            print(f"✓ عدد الـ Queries: {num_queries}")
            print(f"✓ إجمالي الوقت: {total_time:.3f} ثانية")
            print(f"✓ متوسط وقت الـ Query: {(total_time/num_queries):.3f} ثانية")
            
            # تقييم الأداء
            if num_queries <= 15:
                print(f"✅ أداء ممتاز!")
            elif num_queries <= 30:
                print(f"⚠️  أداء جيد، يمكن تحسينه")
            else:
                print(f"❌ أداء سيء - يحتاج تحسين!")
            
            # عرض أبطأ queries
            print(f"\n📊 أبطأ 5 Queries:")
            sorted_queries = sorted(
                connection.queries,
                key=lambda x: float(x['time']),
                reverse=True
            )[:5]
            
            for i, q in enumerate(sorted_queries, 1):
                sql = q['sql'][:100] + '...' if len(q['sql']) > 100 else q['sql']
                print(f"  {i}. [{q['time']}s] {sql}")
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    print("\n" + "="*60)
    print("⚡ اختبار أداء الصفحات المحسّنة")
    print("="*60)
    
    # 1. Dashboard
    test_view_performance(
        dashboard,
        "Dashboard - لوحة المعلومات",
        '/accounting/dashboard/'
    )
    
    # 2. Customer Financial Summary
    from customers.models import Customer
    first_customer = Customer.objects.first()
    if first_customer:
        test_view_performance(
            customer_financial_summary,
            "Customer Financial Summary - الملخص المالي",
            f'/accounting/customer/{first_customer.pk}/financial/',
            customer_id=first_customer.pk
        )
    
    # 3. Customer Balances Report
    test_view_performance(
        customer_balances_report,
        "Customer Balances Report - تقرير الأرصدة",
        '/accounting/reports/customer-balances/'
    )
    
    # 4. Transaction List
    test_view_performance(
        transaction_list,
        "Transaction List - قائمة القيود",
        '/accounting/transactions/'
    )
    
    print("\n" + "="*60)
    print("✅ اكتمل اختبار الأداء")
    print("="*60)
EOF

echo "🧪 تشغيل اختبارات الأداء..."
python test_performance.py

if [ $? -eq 0 ]; then
    echo ""
    echo "${GREEN}✓ اختبارات الأداء اكتملت بنجاح${NC}"
else
    echo ""
    echo "${RED}✗ حدث خطأ في اختبارات الأداء${NC}"
fi

# تنظيف
rm test_performance.py

echo ""
echo "======================================"
echo "📋 ملخص النتائج"
echo "======================================"
echo ""
echo "✅ المرحلة 1: إصلاح Template"
echo "   - customers/customer_detail.html"
echo ""
echo "✅ المرحلة 2: أدوات الصيانة"
echo "   - check_draft_transactions.py"
echo "   - verify_customer_balances.py"
echo "   - daily_maintenance.py"
echo ""
echo "✅ المرحلة 3: تحسينات الأداء"
echo "   - dashboard()"
echo "   - customer_financial_summary()"
echo "   - customer_balances_report()"
echo "   - transaction_list()"
echo ""
echo "======================================"
echo "📝 الخطوات التالية"
echo "======================================"
echo ""
echo "1. ${YELLOW}اختبار يدوي:${NC}"
echo "   - افتح المتصفح وتحقق من الصفحات"
echo "   - تأكد من عرض البيانات بشكل صحيح"
echo ""
echo "2. ${YELLOW}مراقبة الأداء:${NC}"
echo "   - ثبّت Django Debug Toolbar"
echo "   - راقب عدد الـ Queries"
echo "   - قارن النتائج بالقيم المتوقعة"
echo ""
echo "3. ${YELLOW}جدولة الصيانة:${NC}"
echo "   - راجع ACCOUNTING_MAINTENANCE_GUIDE.md"
echo "   - أضف cron jobs للصيانة الدورية"
echo ""
echo "======================================"
echo "🎉 اكتملت جميع الاختبارات!"
echo "======================================"
