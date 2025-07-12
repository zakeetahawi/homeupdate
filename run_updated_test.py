#!/usr/bin/env python3
"""
سكريبت تشغيل الاختبار الشامل المحدث
يتضمن اختبار أكواد العملاء الفريدة، أرقام الطلبات الفريدة، ومزامنة الحالات
"""

import os
import sys
import django
from django.db import transaction
from datetime import datetime
import json

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from comprehensive_system_test import ComprehensiveSystemTest


def print_colored_message(message, color='white'):
    """طباعة رسالة ملونة"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'white': '\033[97m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'end': '\033[0m'
    }
    
    print(f"{colors.get(color, colors['white'])}{message}{colors['end']}")


def run_updated_comprehensive_test():
    """تشغيل الاختبار الشامل المحدث"""
    print_colored_message("🚀 تشغيل الاختبار الشامل المحدث...", 'blue')
    print_colored_message("=" * 70, 'blue')
    
    try:
        # إنشاء مثيل الاختبار
        test = ComprehensiveSystemTest()
        
        # تشغيل الاختبار
        report = test.run_all_tests()
        
        # عرض النتائج المفصلة
        print_colored_message("\n📊 تفاصيل النتائج:", 'blue')
        
        # عرض الإحصائيات
        if 'statistics' in report:
            stats = report['statistics']
            print_colored_message(f"👥 العملاء المُنشأون: {stats.get('customers_created', 0)}", 'white')
            print_colored_message(f"📋 الطلبات المُنشأة: {stats.get('orders_created', 0)}", 'white')
            print_colored_message(f"🏭 أوامر التصنيع المُنشأة: {stats.get('manufacturing_orders_created', 0)}", 'white')
            print_colored_message(f"🏢 الفروع المستخدمة: {stats.get('branches_used', 0)}", 'white')
            print_colored_message(f"👨‍💼 البائعون المستخدمون: {stats.get('salespersons_used', 0)}", 'white')
        
        # عرض سلامة البيانات
        if 'data_integrity' in report:
            integrity = report['data_integrity']
            print_colored_message("\n🔍 فحص سلامة البيانات:", 'yellow')
            
            # أكواد العملاء
            customer_codes = integrity.get('unique_customer_codes', {})
            if 'error' not in customer_codes:
                if customer_codes.get('has_duplicates', False):
                    print_colored_message(f"❌ أكواد العملاء: {customer_codes['duplicate_count']} كود مكرر", 'red')
                else:
                    print_colored_message(f"✅ أكواد العملاء: جميع الأكواد فريدة ({customer_codes['unique_codes']})", 'green')
            
            # أرقام الطلبات
            order_numbers = integrity.get('unique_order_numbers', {})
            if 'error' not in order_numbers:
                if order_numbers.get('has_duplicates', False):
                    print_colored_message(f"❌ أرقام الطلبات: {order_numbers['duplicate_count']} رقم مكرر", 'red')
                else:
                    print_colored_message(f"✅ أرقام الطلبات: جميع الأرقام فريدة ({order_numbers['unique_numbers']})", 'green')
            
            # تطابق الحالات
            status_consistency = integrity.get('status_consistency', {})
            if 'error' not in status_consistency:
                consistency_rate = status_consistency.get('consistency_rate', 0)
                if consistency_rate == 100:
                    print_colored_message(f"✅ تطابق الحالات: مثالي (100%)", 'green')
                elif consistency_rate >= 90:
                    print_colored_message(f"⚠️ تطابق الحالات: جيد ({consistency_rate:.1f}%)", 'yellow')
                else:
                    print_colored_message(f"❌ تطابق الحالات: يحتاج إصلاح ({consistency_rate:.1f}%)", 'red')
        
        # عرض التوصيات
        if 'recommendations' in report and report['recommendations']:
            print_colored_message("\n💡 التوصيات:", 'yellow')
            for i, recommendation in enumerate(report['recommendations'], 1):
                print_colored_message(f"  {i}. {recommendation}", 'white')
        
        # حفظ التقرير
        report_filename = f"updated_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print_colored_message(f"\n📄 تم حفظ التقرير في: {report_filename}", 'blue')
        
        # تقييم النتيجة النهائية
        success_rate = report.get('overall_success_rate', 0)
        
        print_colored_message("\n" + "=" * 70, 'blue')
        if success_rate >= 95:
            print_colored_message(f"🎉 ممتاز! النظام يعمل بكفاءة عالية ({success_rate:.1f}%)", 'green')
        elif success_rate >= 85:
            print_colored_message(f"✅ جيد! النظام يعمل بشكل مقبول ({success_rate:.1f}%)", 'yellow')
        elif success_rate >= 70:
            print_colored_message(f"⚠️ مقبول! النظام يحتاج تحسينات ({success_rate:.1f}%)", 'yellow')
        else:
            print_colored_message(f"❌ ضعيف! النظام يحتاج إصلاحات جوهرية ({success_rate:.1f}%)", 'red')
        
        return report
        
    except Exception as e:
        print_colored_message(f"❌ خطأ في تشغيل الاختبار: {str(e)}", 'red')
        import traceback
        traceback.print_exc()
        return None


def generate_summary_report(report):
    """إنشاء تقرير ملخص"""
    if not report:
        return
    
    print_colored_message("\n📋 ملخص التقرير:", 'blue')
    print_colored_message("=" * 50, 'blue')
    
    # معلومات عامة
    print_colored_message(f"📅 تاريخ الاختبار: {report.get('timestamp', 'غير محدد')}", 'white')
    print_colored_message(f"⏱️ مدة التنفيذ: {report.get('duration_seconds', 0):.2f} ثانية", 'white')
    print_colored_message(f"📈 معدل النجاح الإجمالي: {report.get('overall_success_rate', 0):.1f}%", 'white')
    
    # نتائج الاختبارات
    test_results = report.get('test_results', {})
    successful_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    print_colored_message(f"✅ اختبارات ناجحة: {successful_tests}/{total_tests}", 'white')
    
    # تفاصيل كل اختبار
    for test_name, result in test_results.items():
        status = "✅ نجح" if result else "❌ فشل"
        test_display_name = {
            'customers_with_codes': 'اختبار العملاء والأكواد',
            'orders_with_unique_numbers': 'اختبار الطلبات والأرقام الفريدة',
            'manufacturing_and_sync': 'اختبار التصنيع ومزامنة الحالات',
            'status_transitions': 'اختبار انتقال الحالات',
            'final_status_validation': 'التحقق النهائي من الحالات'
        }.get(test_name, test_name)
        
        print_colored_message(f"  - {test_display_name}: {status}", 'white')


def main():
    """الدالة الرئيسية"""
    print_colored_message("🔧 اختبار نظام إدارة الخواجة المحدث", 'blue')
    print_colored_message("تم تحديث الاختبار ليشمل:", 'white')
    print_colored_message("  ✓ أرقام عقود وفواتير فريدة للاختبار", 'white')
    print_colored_message("  ✓ ربط العملاء بالفروع والبائعين", 'white')
    print_colored_message("  ✓ التحقق من عدم تكرار الأكواد", 'white')
    print_colored_message("  ✓ مزامنة الحالات بين الطلبات والتصنيع", 'white')
    print_colored_message("", 'white')
    
    # تشغيل الاختبار
    report = run_updated_comprehensive_test()
    
    if report:
        # إنشاء ملخص التقرير
        generate_summary_report(report)
        
        print_colored_message("\n✅ تم إكمال الاختبار بنجاح!", 'green')
    else:
        print_colored_message("\n❌ فشل في تشغيل الاختبار!", 'red')


if __name__ == "__main__":
    main() 