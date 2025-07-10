#!/usr/bin/env python3
"""
سكريبت تشغيل الإصلاحات واختبار النظام بعد الإصلاح
"""

import os
import sys
import django
from django.db import transaction
from django.core.management import call_command
from django.utils import timezone
from datetime import datetime, timedelta
import json

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.apps import apps
from orders.models import Order, OrderItem
from manufacturing.models import ManufacturingOrder
from customers.models import Customer
from accounts.models import User, Branch, Salesperson
from inventory.models import Product, Category
from crm.services.base_service import StatusSyncService


def print_colored_message(message, color='white'):
    """طباعة رسالة ملونة حسب تفضيلات المستخدم"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'white': '\033[97m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'end': '\033[0m'
    }
    
    print(f"{colors.get(color, colors['white'])}{message}{colors['end']}")


def run_comprehensive_test():
    """تشغيل اختبار شامل محدث للنظام"""
    print_colored_message("🧪 تشغيل الاختبار الشامل المحدث...", 'blue')
    
    try:
        # استيراد واستخدام الاختبارات الموجودة
        from comprehensive_system_test import ComprehensiveSystemTest
        from advanced_test_scenarios import AdvancedTestScenarios
        
        # تشغيل الاختبار الشامل
        comprehensive_test = ComprehensiveSystemTest()
        comprehensive_report = comprehensive_test.run_all_tests()
        
        # تشغيل الاختبارات المتقدمة
        advanced_test = AdvancedTestScenarios()
        advanced_report = advanced_test.run_all_tests()
        
        # دمج التقارير
        combined_report = {
            'timestamp': datetime.now().isoformat(),
            'comprehensive_test': comprehensive_report,
            'advanced_test': advanced_report,
            'overall_success_rate': (
                comprehensive_report['overall_success_rate'] + 
                advanced_report['overall_success_rate']
            ) / 2
        }
        
        # حفظ التقرير المحدث
        report_filename = f"updated_system_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(combined_report, f, ensure_ascii=False, indent=2)
        
        print_colored_message(f"📄 تم حفظ التقرير المحدث في: {report_filename}", 'blue')
        
        # عرض النتائج
        overall_rate = combined_report['overall_success_rate']
        if overall_rate >= 90:
            print_colored_message(f"🎉 معدل النجاح الإجمالي: {overall_rate:.1f}% - ممتاز!", 'green')
        elif overall_rate >= 75:
            print_colored_message(f"✅ معدل النجاح الإجمالي: {overall_rate:.1f}% - جيد", 'yellow')
        else:
            print_colored_message(f"⚠️ معدل النجاح الإجمالي: {overall_rate:.1f}% - يحتاج تحسين", 'red')
        
        return combined_report
        
    except Exception as e:
        print_colored_message(f"❌ خطأ في تشغيل الاختبار: {str(e)}", 'red')
        return None


def create_sample_data():
    """إنشاء بيانات اختبارية محدثة"""
    print_colored_message("📊 إنشاء بيانات اختبارية محدثة...", 'yellow')
    
    try:
        with transaction.atomic():
            # إنشاء فرع اختباري إذا لم يكن موجوداً
            branch, created = Branch.objects.get_or_create(
                code='TEST',
                defaults={
                    'name': 'فرع اختباري',
                    'address': 'عنوان اختباري',
                    'phone': '0123456789',
                    'is_active': True
                }
            )
            
            # إنشاء مستخدم اختباري
            user, created = User.objects.get_or_create(
                username='test_user',
                defaults={
                    'email': 'test@example.com',
                    'first_name': 'مستخدم',
                    'last_name': 'اختباري',
                    'branch': branch
                }
            )
            
            # إنشاء بائع اختباري
            salesperson, created = Salesperson.objects.get_or_create(
                name='بائع اختباري',
                defaults={
                    'employee_number': 'EMP001',
                    'phone': '0123456789',
                    'branch': branch,
                    'is_active': True
                }
            )
            
            # إنشاء تصنيف منتجات
            category, created = Category.objects.get_or_create(
                name='تصنيف اختباري',
                defaults={'description': 'تصنيف للاختبار'}
            )
            
            # إنشاء منتج اختباري
            product, created = Product.objects.get_or_create(
                name='منتج اختباري',
                defaults={
                    'category': category,
                    'price': 100.00,
                    'stock_quantity': 50,
                    'is_active': True
                }
            )
            
            # إنشاء عميل اختباري
            customer, created = Customer.objects.get_or_create(
                name='عميل اختباري محدث',
                defaults={
                    'phone': '0123456789',
                    'email': 'customer@example.com',
                    'address': 'عنوان اختباري',
                    'customer_type': 'retail',
                    'branch': branch,
                    'created_by': user
                }
            )
            
            print_colored_message("✅ تم إنشاء البيانات الاختبارية بنجاح", 'green')
            
            return {
                'branch': branch,
                'user': user,
                'salesperson': salesperson,
                'category': category,
                'product': product,
                'customer': customer
            }
            
    except Exception as e:
        print_colored_message(f"❌ خطأ في إنشاء البيانات الاختبارية: {str(e)}", 'red')
        return None


def main():
    """الدالة الرئيسية"""
    print_colored_message("🚀 بدء تشغيل إصلاحات النظام والاختبار", 'blue')
    print_colored_message("=" * 60, 'blue')
    
    try:
        # الخطوة 1: تشغيل الإصلاحات
        print_colored_message("الخطوة 1: تشغيل الإصلاحات الشاملة", 'yellow')
        os.system('python fix_system_issues.py')
        
        # الخطوة 2: إنشاء بيانات اختبارية
        print_colored_message("الخطوة 2: إنشاء بيانات اختبارية", 'yellow')
        sample_data = create_sample_data()
        
        if sample_data:
            print_colored_message("✅ تم إنشاء البيانات الاختبارية", 'green')
        else:
            print_colored_message("❌ فشل في إنشاء البيانات الاختبارية", 'red')
            return
        
        # الخطوة 3: تشغيل الاختبار الشامل
        print_colored_message("الخطوة 3: تشغيل الاختبار الشامل", 'yellow')
        test_report = run_comprehensive_test()
        
        if test_report:
            print_colored_message("✅ تم تشغيل الاختبار بنجاح", 'green')
        else:
            print_colored_message("❌ فشل في تشغيل الاختبار", 'red')
            return
        
        # الخطوة 4: عرض النتائج النهائية
        print_colored_message("=" * 60, 'blue')
        print_colored_message("📊 النتائج النهائية:", 'blue')
        
        if test_report:
            overall_rate = test_report['overall_success_rate']
            print_colored_message(f"معدل النجاح الإجمالي: {overall_rate:.1f}%", 'white')
            
            if overall_rate >= 90:
                print_colored_message("🎉 النظام يعمل بكفاءة عالية!", 'green')
            elif overall_rate >= 75:
                print_colored_message("✅ النظام يعمل بشكل جيد", 'yellow')
            else:
                print_colored_message("⚠️ النظام يحتاج مزيد من التحسين", 'red')
        
        print_colored_message("=" * 60, 'blue')
        print_colored_message("✅ تم إكمال جميع العمليات بنجاح!", 'green')
        
    except Exception as e:
        print_colored_message(f"❌ خطأ عام: {str(e)}", 'red')


if __name__ == "__main__":
    main() 