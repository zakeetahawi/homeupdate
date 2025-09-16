#!/usr/bin/env python3
"""
Script لإصلاح سجلات الحالة الموجودة
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from orders.models import Order, OrderStatusLog
from django.db import transaction

def fix_status_logs():
    """إصلاح سجلات الحالة الموجودة"""
    
    print("🔧 إصلاح سجلات الحالة...")
    print("=" * 60)
    
    # 1. فحص السجلات التي تحتاج إصلاح
    print("\n1️⃣ فحص السجلات التي تحتاج إصلاح:")
    
    # البحث عن سجلات بحالات غير موجودة في ORDER_STATUS_CHOICES
    invalid_old_status = OrderStatusLog.objects.exclude(
        old_status__in=[choice[0] for choice in Order.ORDER_STATUS_CHOICES]
    ).count()
    
    invalid_new_status = OrderStatusLog.objects.exclude(
        new_status__in=[choice[0] for choice in Order.ORDER_STATUS_CHOICES]
    ).count()
    
    print(f"   📊 سجلات بحالة سابقة غير صحيحة: {invalid_old_status}")
    print(f"   📊 سجلات بحالة جديدة غير صحيحة: {invalid_new_status}")
    
    # 2. إصلاح السجلات
    if invalid_old_status > 0 or invalid_new_status > 0:
        print("\n2️⃣ بدء إصلاح السجلات...")
        
        # خريطة تحويل الحالات
        status_mapping = {
            # من TRACKING_STATUS_CHOICES إلى ORDER_STATUS_CHOICES
            'pending': 'pending',
            'processing': 'in_progress',
            'warehouse': 'in_progress',
            'factory': 'in_progress',
            'cutting': 'in_progress',
            'ready': 'ready_install',
            'delivered': 'delivered',
        }
        
        fixed_count = 0
        
        with transaction.atomic():
            # إصلاح الحالات السابقة
            for log in OrderStatusLog.objects.exclude(
                old_status__in=[choice[0] for choice in Order.ORDER_STATUS_CHOICES]
            ):
                original_old_status = log.old_status
                if log.old_status in status_mapping:
                    log.old_status = status_mapping[log.old_status]
                    log.save(update_fields=['old_status'])
                    fixed_count += 1
                    print(f"   ✅ تم إصلاح السجل {log.id}: old_status من '{original_old_status}' إلى '{log.old_status}'")
                else:
                    # إذا لم نجد تطابق، استخدم 'pending' كقيمة افتراضية
                    log.old_status = 'pending'
                    log.save(update_fields=['old_status'])
                    fixed_count += 1
                    print(f"   ✅ تم إصلاح السجل {log.id}: old_status من '{original_old_status}' إلى 'pending' (افتراضي)")
            
            # إصلاح الحالات الجديدة
            for log in OrderStatusLog.objects.exclude(
                new_status__in=[choice[0] for choice in Order.ORDER_STATUS_CHOICES]
            ):
                original_new_status = log.new_status
                if log.new_status in status_mapping:
                    log.new_status = status_mapping[log.new_status]
                    log.save(update_fields=['new_status'])
                    fixed_count += 1
                    print(f"   ✅ تم إصلاح السجل {log.id}: new_status من '{original_new_status}' إلى '{log.new_status}'")
                else:
                    # إذا لم نجد تطابق، استخدم 'pending' كقيمة افتراضية
                    log.new_status = 'pending'
                    log.save(update_fields=['new_status'])
                    fixed_count += 1
                    print(f"   ✅ تم إصلاح السجل {log.id}: new_status من '{original_new_status}' إلى 'pending' (افتراضي)")
        
        print(f"\n   📊 إجمالي السجلات المُصلحة: {fixed_count}")
    else:
        print("\n2️⃣ لا توجد سجلات تحتاج إصلاح")
    
    # 3. اختبار السجلات بعد الإصلاح
    print("\n3️⃣ اختبار السجلات بعد الإصلاح:")
    
    # فحص السجلات المُصلحة
    valid_old_status = OrderStatusLog.objects.filter(
        old_status__in=[choice[0] for choice in Order.ORDER_STATUS_CHOICES]
    ).count()
    
    valid_new_status = OrderStatusLog.objects.filter(
        new_status__in=[choice[0] for choice in Order.ORDER_STATUS_CHOICES]
    ).count()
    
    total_logs = OrderStatusLog.objects.count()
    
    print(f"   📊 إجمالي السجلات: {total_logs}")
    print(f"   ✅ سجلات بحالة سابقة صحيحة: {valid_old_status}")
    print(f"   ✅ سجلات بحالة جديدة صحيحة: {valid_new_status}")
    
    # 4. عرض أمثلة من السجلات المُصلحة
    print("\n4️⃣ أمثلة من السجلات المُصلحة:")
    
    recent_logs = OrderStatusLog.objects.all().order_by('-created_at')[:5]
    
    for i, log in enumerate(recent_logs, 1):
        print(f"   📋 السجل {i}:")
        print(f"      🏷️ الطلب: {log.order.order_number}")
        print(f"      🔄 من '{log.old_status}' إلى '{log.new_status}'")
        print(f"      📅 التاريخ: {log.created_at}")
        print(f"      👤 المستخدم: {log.changed_by}")
        print()
    
    # 5. اختبار عرض الحالات في Admin
    print("\n5️⃣ اختبار عرض الحالات:")
    
    for log in recent_logs[:3]:
        try:
            old_display = log.get_old_status_display()
            new_display = log.get_new_status_display()
            print(f"   📋 السجل {log.id}:")
            print(f"      🔄 الحالة السابقة: '{log.old_status}' -> '{old_display}'")
            print(f"      🔄 الحالة الجديدة: '{log.new_status}' -> '{new_display}'")
        except Exception as e:
            print(f"   ❌ خطأ في عرض السجل {log.id}: {e}")
    
    print("\n" + "=" * 60)
    print("📋 ملخص الإصلاح:")
    print(f"✅ إجمالي السجلات: {total_logs}")
    print(f"✅ سجلات صحيحة: {min(valid_old_status, valid_new_status)}")
    print(f"✅ تم إصلاح: {fixed_count if 'fixed_count' in locals() else 0}")
    
    if min(valid_old_status, valid_new_status) == total_logs:
        print("\n🎉 تم إصلاح جميع السجلات بنجاح!")
        print("✅ الآن ستظهر الحالات السابقة والجديدة بشكل صحيح في Admin")
    else:
        print("\n⚠️ لا تزال هناك سجلات تحتاج إصلاح")

if __name__ == '__main__':
    fix_status_logs()
