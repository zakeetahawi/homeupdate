#!/usr/bin/env python3
"""
إصلاح مشكلة تاريخ إضافة العميل في المزامنة المتقدمة
Fix Customer Creation Date Issue in Advanced Sync
"""

import os
import sys
import django

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')
django.setup()

from odoo_db_manager.google_sync_advanced import GoogleSheetMapping
from customers.models import Customer
from orders.models import Order
from django.utils import timezone
from datetime import datetime, timedelta

def main():
    print("🔧 أداة إصلاح تاريخ إضافة العميل في المزامنة المتقدمة")
    print("="*60)
    
    # عرض جميع التعيينات الموجودة
    mappings = GoogleSheetMapping.objects.all()
    
    if not mappings.exists():
        print("❌ لا توجد تعيينات مزامنة موجودة")
        return
    
    print(f"📋 تم العثور على {mappings.count()} ت��يين مزامنة:")
    print()
    
    for i, mapping in enumerate(mappings, 1):
        print(f"{i}. {mapping.name}")
        print(f"   📊 جدول: {mapping.spreadsheet_id}")
        print(f"   📄 صفحة: {mapping.sheet_name}")
        print(f"   📅 استخدام التاريخ الحالي: {'✅ نعم' if mapping.use_current_date_as_created else '❌ لا'}")
        print(f"   🔄 آخر مزامنة: {mapping.last_sync.strftime('%Y-%m-%d %H:%M') if mapping.last_sync else 'لم تتم بعد'}")
        print()
    
    print("📝 شرح الإعدادات:")
    print("   ✅ استخدام التاريخ الحالي = نعم: سيتم استخدام تاريخ المزامنة كتاريخ إضافة العميل")
    print("   ❌ استخدام التاريخ الحالي = لا: سيتم استخدام تاريخ الطلب كتاريخ إضافة العميل")
    print()
    
    # السؤال عن التعيين المراد إصلاحه
    try:
        choice = input("🔧 أدخل رقم التعيين المراد إصلاحه (أو 'q' للخروج): ").strip()
        
        if choice.lower() == 'q':
            print("👋 تم الخروج")
            return
        
        choice_num = int(choice)
        if choice_num < 1 or choice_num > mappings.count():
            print("❌ رقم غير صحيح")
            return
        
        selected_mapping = list(mappings)[choice_num - 1]
        
    except ValueError:
        print("❌ يرجى إدخال رقم صحيح")
        return
    
    print(f"\n🎯 التعيين المختار: {selected_mapping.name}")
    print(f"📅 الإعداد الحالي: {'استخدام التاريخ الحالي' if selected_mapping.use_current_date_as_created else 'استخدام تاريخ الطلب'}")
    
    # عرض الخيارات
    print("\n🔧 خيارات الإصلاح:")
    print("1. تغيير الإعداد إلى 'استخدام تاريخ الطلب كتاريخ إضافة العميل'")
    print("2. تغيير الإعداد إلى 'استخدام التاريخ الحالي كتاريخ إضافة العميل'")
    print("3. عرض إحصائيات العملاء المتأثرين")
    print("4. إصلاح تواريخ العملاء الموجودين (استخدام تاريخ أول طلب)")
    
    action = input("\n🎯 اختر الإجراء (1-4): ").strip()
    
    if action == "1":
        # تغيير الإعداد لاستخدام ��اريخ الطلب
        selected_mapping.use_current_date_as_created = False
        selected_mapping.save()
        print("✅ تم تغيير الإعداد بنجاح!")
        print("📝 الآن سيتم استخدام تاريخ الطلب كتاريخ إضافة العميل في المزامنات القادمة")
        
    elif action == "2":
        # تغيير الإعداد لاستخدام التاريخ الحالي
        selected_mapping.use_current_date_as_created = True
        selected_mapping.save()
        print("✅ تم تغيير الإعداد بنجاح!")
        print("📝 الآن سيتم استخدام التاريخ الحالي كتاريخ إضافة العميل في المزامنات القادمة")
        
    elif action == "3":
        # عرض إحصائيات العملاء
        show_customer_statistics()
        
    elif action == "4":
        # إصلاح تواريخ العملاء الموجودين
        fix_existing_customers()
        
    else:
        print("❌ خيار غير صحيح")

def show_customer_statistics():
    """عرض إحصائيات العملاء وتواريخ الإضافة"""
    print("\n📊 إحصائيات العملاء:")
    print("="*40)
    
    total_customers = Customer.objects.count()
    print(f"👥 إجمالي العملاء: {total_customers}")
    
    # العملاء المضافين اليوم
    today = timezone.now().date()
    today_customers = Customer.objects.filter(created_at__date=today).count()
    print(f"📅 عملاء اليوم: {today_customers}")
    
    # العملاء المضافين هذا الأسبوع
    week_ago = timezone.now() - timedelta(days=7)
    week_customers = Customer.objects.filter(created_at__gte=week_ago).count()
    print(f"📅 عملاء الأسبوع: {week_customers}")
    
    # العملاء المضافين هذا الشهر
    month_ago = timezone.now() - timedelta(days=30)
    month_customers = Customer.objects.filter(created_at__gte=month_ago).count()
    print(f"📅 عملاء الشهر: {month_customers}")
    
    # العملاء الذين لديهم طلبات
    customers_with_orders = Customer.objects.filter(customer_orders__isnull=False).distinct().count()
    print(f"📦 عملاء لديهم طلبات: {customers_with_orders}")
    
    # العملاء الذين تاريخ إضافتهم يطابق تاريخ أول طلب
    matching_dates = 0
    different_dates = 0
    
    for customer in Customer.objects.filter(customer_orders__isnull=False).distinct()[:100]:  # عينة من 100 عميل
        first_order = customer.customer_orders.order_by('order_date').first()
        if first_order and first_order.order_date:
            customer_date = customer.created_at.date()
            order_date = first_order.order_date.date() if hasattr(first_order.order_date, 'date') else first_order.order_date
            
            if customer_date == order_date:
                matching_dates += 1
            else:
                different_dates += 1
    
    print(f"✅ عملاء تطابق تواريخهم مع الطلبات: {matching_dates}")
    print(f"❌ عملاء لا تطابق تواريخهم مع الطلبات: {different_dates}")

def fix_existing_customers():
    """إصلاح تواريخ العملاء الموجودين باستخدام تاريخ أول طلب"""
    print("\n🔧 إصلاح تواريخ العملاء الموجودين:")
    print("="*50)
    
    confirm = input("⚠️  هذا الإجراء سيغير تواريخ إضافة العملاء. هل تريد المتابعة؟ (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ تم إلغاء العملية")
        return
    
    updated_count = 0
    skipped_count = 0
    
    # العملاء الذين لديهم طلبات
    customers_with_orders = Customer.objects.filter(customer_orders__isnull=False).distinct()
    
    print(f"🔍 فحص {customers_with_orders.count()} عميل...")
    
    for customer in customers_with_orders:
        first_order = customer.customer_orders.order_by('order_date').first()
        
        if first_order and first_order.order_date:
            order_date = first_order.order_date
            customer_date = customer.created_at
            
            # التحقق من أن تاريخ الطلب مختلف عن تاريخ إضافة العميل
            if hasattr(order_date, 'date'):
                order_date_only = order_date.date()
            else:
                order_date_only = order_date
                
            if hasattr(customer_date, 'date'):
                customer_date_only = customer_date.date()
            else:
                customer_date_only = customer_date
            
            if order_date_only != customer_date_only:
                # تحديث تاريخ إضافة العميل
                customer.created_at = order_date
                customer.save(update_fields=['created_at'])
                updated_count += 1
                
                if updated_count <= 10:  # عرض أول 10 تحديثات
                    print(f"✅ {customer.name}: {customer_date_only} → {order_date_only}")
            else:
                skipped_count += 1
    
    print(f"\n📊 النتائج:")
    print(f"✅ تم تحديث: {updated_count} عميل")
    print(f"⏭️  تم تخطي: {skipped_count} عميل (التواريخ متطابقة)")
    print("✅ تم إكمال العملية بنجاح!")

if __name__ == "__main__":
    main()