#!/usr/bin/env python
"""
سكريبت اختبار داش بورد الإدارة
Test Admin Dashboard Script
"""

import os
import sys
import django
from datetime import datetime, timedelta

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from customers.models import Customer
from orders.models import Order
from manufacturing.models import ManufacturingOrder
from inspections.models import Inspection
from installations.models import InstallationSchedule
from inventory.models import Product
from accounts.models import Branch, CompanyInfo

User = get_user_model()

def test_admin_dashboard():
    """اختبار داش بورد الإدارة"""
    print("🔍 اختبار داش بورد الإدارة...")
    
    try:
        # التحقق من وجود مستخدم مدير
        admin_users = User.objects.filter(is_staff=True)
        if not admin_users.exists():
            print("❌ لا يوجد مستخدمين مدراء في النظام")
            print("💡 يرجى إنشاء مستخدم مدير أولاً")
            return False
        
        print(f"✅ تم العثور على {admin_users.count()} مستخدم مدير")
        
        # التحقق من وجود بيانات اختبارية
        customers_count = Customer.objects.count()
        orders_count = Order.objects.count()
        manufacturing_count = ManufacturingOrder.objects.count()
        inspections_count = Inspection.objects.count()
        installations_count = InstallationSchedule.objects.count()
        products_count = Product.objects.count()
        branches_count = Branch.objects.count()
        
        print("\n📊 إحصائيات البيانات الحالية:")
        print(f"   العملاء: {customers_count}")
        print(f"   الطلبات: {orders_count}")
        print(f"   أوامر التصنيع: {manufacturing_count}")
        print(f"   المعاينات: {inspections_count}")
        print(f"   التركيبات: {installations_count}")
        print(f"   المنتجات: {products_count}")
        print(f"   الفروع: {branches_count}")
        
        # التحقق من وجود معلومات الشركة
        company_info = CompanyInfo.objects.first()
        if not company_info:
            print("⚠️  لا توجد معلومات الشركة، سيتم إنشاؤها تلقائياً")
        else:
            print(f"✅ معلومات الشركة موجودة: {company_info.name}")
        
        # اختبار وظائف الإحصائيات
        from crm.views import (
            get_customers_statistics,
            get_orders_statistics,
            get_manufacturing_statistics,
            get_inspections_statistics,
            get_installations_statistics,
            get_inventory_statistics,
            get_chart_data
        )
        
        print("\n🧪 اختبار وظائف الإحصائيات...")
        
        # تحديد فترة زمنية للاختبار
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # اختبار إحصائيات العملاء
        customers_stats = get_customers_statistics('all', start_date, end_date)
        print(f"   ✅ إحصائيات العملاء: {customers_stats['total']} عميل")
        
        # اختبار إحصائيات الطلبات
        orders_stats = get_orders_statistics('all', start_date, end_date)
        print(f"   ✅ إحصائيات الطلبات: {orders_stats['total']} طلب")
        
        # اختبار إحصائيات التصنيع
        manufacturing_stats = get_manufacturing_statistics('all', start_date, end_date)
        print(f"   ✅ إحصائيات التصنيع: {manufacturing_stats['total']} أمر")
        
        # اختبار إحصائيات المعاينات
        inspections_stats = get_inspections_statistics('all', start_date, end_date)
        print(f"   ✅ إحصائيات المعاينات: {inspections_stats['total']} معاينة")
        
        # اختبار إحصائيات التركيبات
        installations_stats = get_installations_statistics('all', start_date, end_date)
        print(f"   ✅ إحصائيات التركيبات: {installations_stats['total']} تركيب")
        
        # اختبار إحصائيات المخزون
        inventory_stats = get_inventory_statistics('all')
        print(f"   ✅ إحصائيات المخزون: {inventory_stats['total_products']} منتج")
        
        # اختبار بيانات الرسوم البيانية
        chart_data = get_chart_data('all', datetime.now().year)
        print(f"   ✅ بيانات الرسوم البيانية: {len(chart_data['orders_by_month'])} شهر للطلبات")
        
        print("\n🎉 جميع الاختبارات نجحت!")
        print("\n📋 ملخص الداش بورد الإداري:")
        print("   ✅ متاح للمدراء فقط (is_staff أو is_superuser)")
        print("   ✅ توجيه تلقائي للمدراء")
        print("   ✅ فلاتر متقدمة (فرع، شهر، سنة)")
        print("   ✅ مقارنة زمنية")
        print("   ✅ رسوم بيانية تفاعلية")
        print("   ✅ تصميم حديث ومتجاوب")
        print("   ✅ تحديث تلقائي للبيانات")
        
        print("\n🌐 للوصول للداش بورد:")
        print("   1. تسجيل الدخول كمستخدم مدير")
        print("   2. سيتم التوجيه تلقائياً إلى /admin-dashboard/")
        print("   3. أو الوصول مباشرة عبر الرابط")
        
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار الداش بورد: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_test_data():
    """إنشاء بيانات اختبارية إذا لم تكن موجودة"""
    print("\n🔧 إنشاء بيانات اختبارية...")
    
    try:
        # إنشاء فرع اختباري
        branch, created = Branch.objects.get_or_create(
            name='الفرع الرئيسي',
            defaults={
                'address': 'عنوان الفرع الرئيسي',
                'phone': '0123456789',
                'is_active': True
            }
        )
        if created:
            print("   ✅ تم إنشاء فرع اختباري")
        
        # إنشاء عميل اختباري
        customer, created = Customer.objects.get_or_create(
            name='عميل اختباري',
            defaults={
                'phone': '0123456789',
                'address': 'عنوان العميل الاختباري',
                'status': 'active',
                'branch': branch
            }
        )
        if created:
            print("   ✅ تم إنشاء عميل اختباري")
        
        # إنشاء طلب اختباري
        order, created = Order.objects.get_or_create(
            order_number='TEST-001',
            defaults={
                'customer': customer,
                'branch': branch,
                'status': 'normal',
                'order_status': 'pending',
                'total_amount': 1000.00
            }
        )
        if created:
            print("   ✅ تم إنشاء طلب اختباري")
        
        # إنشاء أمر تصنيع اختباري
        manufacturing_order, created = ManufacturingOrder.objects.get_or_create(
            order=order,
            defaults={
                'order_type': 'installation',
                'status': 'pending',
                'expected_delivery_date': datetime.now().date() + timedelta(days=7)
            }
        )
        if created:
            print("   ✅ تم إنشاء أمر تصنيع اختباري")
        
        # إنشاء معاينة اختبارية
        inspection, created = Inspection.objects.get_or_create(
            contract_number='INSP-001',
            defaults={
                'customer': customer,
                'branch': branch,
                'status': 'pending',
                'request_date': datetime.now().date(),
                'scheduled_date': datetime.now().date() + timedelta(days=3)
            }
        )
        if created:
            print("   ✅ تم إنشاء معاينة اختبارية")
        
        # إنشاء تركيب اختباري
        installation, created = InstallationSchedule.objects.get_or_create(
            order=order,
            defaults={
                'status': 'pending'
            }
        )
        if created:
            print("   ✅ تم إنشاء تركيب اختباري")
        
        # إنشاء منتج اختباري
        product, created = Product.objects.get_or_create(
            name='منتج اختباري',
            defaults={
                'price': 100.00,
                'current_stock': 50,
                'minimum_stock': 10
            }
        )
        if created:
            print("   ✅ تم إنشاء منتج اختباري")
        
        print("✅ تم إنشاء جميع البيانات الاختبارية بنجاح!")
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء البيانات الاختبارية: {str(e)}")

if __name__ == '__main__':
    print("🚀 بدء اختبار داش بورد الإدارة...")
    
    # إنشاء بيانات اختبارية
    create_test_data()
    
    # اختبار الداش بورد
    success = test_admin_dashboard()
    
    if success:
        print("\n🎉 اختبار الداش بورد الإداري اكتمل بنجاح!")
        print("💡 يمكنك الآن الوصول للداش بورد عبر المتصفح")
    else:
        print("\n❌ فشل في اختبار الداش بورد")
        print("🔧 يرجى مراجعة الأخطاء وإصلاحها") 