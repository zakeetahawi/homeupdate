#!/usr/bin/env python
"""
Script لربط المعاينات القديمة بطلبات جديدة وتطبيق نظام التكويد الموحد
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inspections.models import Inspection
from orders.models import Order
from customers.models import Customer
from accounts.models import Branch, Salesperson
from django.db import transaction
from django.utils import timezone


def fix_old_inspections():
    """ربط المعاينات القديمة بطلبات"""
    
    print("🔄 بدء معالجة المعاينات القديمة...")
    
    # البحث عن المعاينات التي لا تحتوي على طلب مرتبط
    old_inspections = Inspection.objects.filter(order__isnull=True)
    
    print(f"📊 عدد المعاينات التي تحتاج إلى ربط: {old_inspections.count()}")
    
    fixed_count = 0
    error_count = 0
    
    for inspection in old_inspections:
        try:
            with transaction.atomic():
                # إنشاء طلب جديد للمعاينة
                if inspection.customer:
                    # إنشاء طلب جديد مرتبط بالمعاينة
                    order = Order.objects.create(
                        customer=inspection.customer,
                        branch=inspection.branch or Branch.objects.first(),
                        salesperson=inspection.responsible_employee,
                        selected_types='["inspection"]',  # نوع معاينة فقط
                        order_date=inspection.request_date or timezone.now().date(),
                        notes=f"طلب تم إنشاؤه تلقائياً للمعاينة القديمة #{inspection.id}",
                        status='normal',
                        order_status='completed',  # لأنها معاينة مكتملة
                        tracking_status='completed'
                    )
                    
                    # ربط المعاينة بالطلب الجديد
                    inspection.order = order
                    inspection.is_from_orders = True
                    inspection.save()
                    
                    print(f"✅ تم ربط المعاينة #{inspection.id} بالطلب {order.order_number}")
                    fixed_count += 1
                    
                else:
                    print(f"⚠️  المعاينة #{inspection.id} لا تحتوي على عميل - تم تخطيها")
                    error_count += 1
                    
        except Exception as e:
            print(f"❌ خطأ في معالجة المعاينة #{inspection.id}: {str(e)}")
            error_count += 1
    
    print(f"\n📈 تقرير النتائج:")
    print(f"✅ تم إصلاح: {fixed_count} معاينة")
    print(f"❌ أخطاء: {error_count} معاينة")
    print(f"📊 إجمالي: {fixed_count + error_count} معاينة")


def verify_inspection_codes():
    """التحقق من أكواد المعاينات الجديدة"""
    
    print("\n🔍 التحقق من أكواد المعاينات...")
    
    inspections = Inspection.objects.all()[:10]  # عينة للاختبار
    
    for inspection in inspections:
        try:
            code = inspection.inspection_code
            print(f"📋 المعاينة #{inspection.id}: {code}")
        except Exception as e:
            print(f"❌ خطأ في كود المعاينة #{inspection.id}: {str(e)}")


if __name__ == "__main__":
    print("🚀 بدء معالجة المعاينات القديمة...")
    print("=" * 50)
    
    fix_old_inspections()
    verify_inspection_codes()
    
    print("=" * 50)
    print("✨ تمت المعالجة بنجاح!")
