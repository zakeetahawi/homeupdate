#!/usr/bin/env python
"""
تحديث سجلات الحالة الموجودة لإضافة نوع التغيير والتفاصيل
"""

import os
import sys
import django

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import OrderStatusLog
from django.db import transaction

def update_existing_logs():
    """تحديث السجلات الموجودة"""
    print("بدء تحديث سجلات الحالة الموجودة...")

    # الحصول على جميع السجلات التي لا تحتوي على نوع تغيير
    logs_to_update = OrderStatusLog.objects.filter(change_type='status')
    total_logs = logs_to_update.count()

    print(f"عدد السجلات المراد تحديثها: {total_logs}")

    updated_count = 0

    # تحديث بدون transaction لتجنب المشاكل
    for log in logs_to_update:
        try:
            # تحديد نوع التغيير بناءً على الملاحظات والحالة
            if log.notes:
                if 'تم إنشاء الطلب' in log.notes:
                    log.change_type = 'creation'
                elif 'تم تغيير العميل' in log.notes or 'العميل:' in log.notes:
                    log.change_type = 'customer'
                elif 'السعر' in log.notes or 'المبلغ' in log.notes:
                    log.change_type = 'price'
                elif 'تاريخ' in log.notes:
                    log.change_type = 'date'
                elif 'تصنيع' in log.notes or 'مصنع' in log.notes:
                    log.change_type = 'manufacturing'
                elif 'تركيب' in log.notes:
                    log.change_type = 'installation'
                elif 'دفع' in log.notes or 'مدفوع' in log.notes:
                    log.change_type = 'payment'
                elif 'تم تبديل الحالة' in log.notes or log.old_status != log.new_status:
                    log.change_type = 'status'
                else:
                    log.change_type = 'general'
            else:
                # إذا لم تكن هناك ملاحظات، نحدد بناءً على الحالة
                if not log.old_status:
                    log.change_type = 'creation'
                elif log.old_status != log.new_status:
                    log.change_type = 'status'
                else:
                    log.change_type = 'general'

            # تحديد إذا كان التغيير تلقائي
            if not log.changed_by:
                log.is_automatic = True
            elif 'مزامنة' in (log.notes or '') or 'تلقائي' in (log.notes or ''):
                log.is_automatic = True
            else:
                log.is_automatic = False

            # تحديث مباشر في قاعدة البيانات لتجنب مشاكل save()
            OrderStatusLog.objects.filter(id=log.id).update(
                change_type=log.change_type,
                is_automatic=log.is_automatic
            )
            updated_count += 1

            if updated_count % 100 == 0:
                print(f"تم تحديث {updated_count} من {total_logs} سجل...")

        except Exception as e:
            print(f"خطأ في تحديث السجل {log.id}: {e}")
            continue

    print(f"تم الانتهاء! تم تحديث {updated_count} سجل من أصل {total_logs}")

def create_sample_detailed_logs():
    """إنشاء بعض السجلات المفصلة كمثال"""
    print("إنشاء سجلات مفصلة كمثال...")
    
    from orders.models import Order
    
    # الحصول على أول 5 طلبات
    orders = Order.objects.all()[:5]
    
    for order in orders:
        try:
            # إنشاء سجل تغيير سعر كمثال
            if order.final_price:
                OrderStatusLog.create_detailed_log(
                    order=order,
                    change_type='price',
                    old_value=order.final_price - 100,
                    new_value=order.final_price,
                    notes='مثال على تغيير السعر'
                )
            
            # إنشاء سجل تغيير تاريخ كمثال
            if order.expected_delivery_date:
                OrderStatusLog.create_detailed_log(
                    order=order,
                    change_type='date',
                    old_value='2024-01-01',
                    new_value=str(order.expected_delivery_date),
                    field_name='تاريخ التسليم المتوقع',
                    notes='مثال على تغيير التاريخ'
                )
                
        except Exception as e:
            print(f"خطأ في إنشاء سجل مفصل للطلب {order.order_number}: {e}")
            continue
    
    print("تم إنشاء السجلات المفصلة كمثال")

if __name__ == '__main__':
    print("=" * 50)
    print("تحديث سجلات الحالة الموجودة")
    print("=" * 50)
    
    try:
        update_existing_logs()
        print("\n" + "=" * 50)
        create_sample_detailed_logs()
        print("=" * 50)
        print("تم الانتهاء من جميع العمليات بنجاح!")
        
    except Exception as e:
        print(f"خطأ عام: {e}")
        sys.exit(1)
