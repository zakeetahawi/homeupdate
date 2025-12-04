#!/usr/bin/env python
"""
سكريبت لإعادة بناء سجلات حالة أوامر التصنيع بالتواريخ الحقيقية
يحذف جميع السجلات الحالية ويعيد إنشاءها من تواريخ أوامر التصنيع
"""

import os
import sys
import django
from datetime import datetime

# إعداد Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from manufacturing.models import ManufacturingOrder, ManufacturingStatusLog


def rebuild_status_logs():
    """إعادة بناء سجلات الحالة بالتواريخ الصحيحة"""
    
    print("=" * 80)
    print("بدء إعادة بناء سجلات حالة أوامر التصنيع")
    print("=" * 80)
    
    # حساب عدد السجلات الحالية
    current_logs_count = ManufacturingStatusLog.objects.count()
    print(f"\n✓ عدد السجلات الحالية: {current_logs_count:,}")
    
    # حذف جميع السجلات الحالية
    print("\n" + "-" * 80)
    print("الخطوة 1: حذف السجلات الحالية...")
    print("-" * 80)
    
    with transaction.atomic():
        deleted_count, _ = ManufacturingStatusLog.objects.all().delete()
        print(f"✓ تم حذف {deleted_count:,} سجل")
    
    # الحصول على جميع أوامر التصنيع
    print("\n" + "-" * 80)
    print("الخطوة 2: إعادة إنشاء السجلات من أوامر التصنيع...")
    print("-" * 80)
    
    orders = ManufacturingOrder.objects.select_related('order', 'created_by').all()
    total_orders = orders.count()
    print(f"✓ عدد أوامر التصنيع: {total_orders:,}")
    
    created_logs = 0
    errors = []
    
    with transaction.atomic():
        for idx, order in enumerate(orders, 1):
            try:
                # طباعة التقدم كل 100 أمر
                if idx % 100 == 0 or idx == total_orders:
                    print(f"  معالجة: {idx}/{total_orders} ({idx*100//total_orders}%)")
                
                # إنشاء سجل للحالة الأولية (pending) عند إنشاء الأمر
                # استخدام تاريخ إنشاء الأمر
                initial_log = ManufacturingStatusLog(
                    manufacturing_order=order,
                    previous_status='',  # لا توجد حالة سابقة
                    new_status='pending',
                    changed_by=order.created_by,
                    notes='إنشاء أمر التصنيع'
                )
                # حفظ بدون auto_now_add للسماح بتعيين التاريخ يدوياً
                initial_log.save()
                # تعيين التاريخ الحقيقي
                ManufacturingStatusLog.objects.filter(pk=initial_log.pk).update(
                    changed_at=order.created_at
                )
                created_logs += 1
                
                # إذا كانت الحالة الحالية مختلفة عن pending، أنشئ سجل آخر
                if order.status != 'pending':
                    status_change_log = ManufacturingStatusLog(
                        manufacturing_order=order,
                        previous_status='pending',
                        new_status=order.status,
                        changed_by=order.created_by,  # سنستخدم منشئ الأمر إذا لم يكن هناك مستخدم آخر
                        notes=f'تغيير الحالة إلى {order.get_status_display()}'
                    )
                    status_change_log.save()
                    # استخدام تاريخ آخر تحديث للأمر
                    ManufacturingStatusLog.objects.filter(pk=status_change_log.pk).update(
                        changed_at=order.updated_at
                    )
                    created_logs += 1
                
            except Exception as e:
                error_msg = f"خطأ في معالجة الأمر {order.manufacturing_code}: {str(e)}"
                errors.append(error_msg)
                print(f"  ✗ {error_msg}")
    
    # طباعة النتائج
    print("\n" + "=" * 80)
    print("النتائج النهائية")
    print("=" * 80)
    print(f"✓ عدد السجلات المحذوفة: {deleted_count:,}")
    print(f"✓ عدد السجلات المُنشأة: {created_logs:,}")
    print(f"✓ عدد الأوامر المعالجة: {total_orders:,}")
    
    if errors:
        print(f"\n⚠ عدد الأخطاء: {len(errors)}")
        print("\nتفاصيل الأخطاء:")
        for error in errors[:10]:  # إظهار أول 10 أخطاء فقط
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... و {len(errors) - 10} خطأ آخر")
    else:
        print("\n✓ تمت العملية بنجاح بدون أخطاء!")
    
    # التحقق النهائي
    print("\n" + "-" * 80)
    print("التحقق النهائي من السجلات الجديدة:")
    print("-" * 80)
    
    new_logs_count = ManufacturingStatusLog.objects.count()
    print(f"✓ عدد السجلات الجديدة: {new_logs_count:,}")
    
    # عرض عينة من السجلات الجديدة
    print("\nعينة من السجلات (أحدث 5 سجلات):")
    sample_logs = ManufacturingStatusLog.objects.select_related(
        'manufacturing_order', 'changed_by'
    ).order_by('-changed_at')[:5]
    
    for log in sample_logs:
        user_name = log.changed_by.get_full_name() if log.changed_by else 'غير محدد'
        print(f"  • {log.manufacturing_order.manufacturing_code}: "
              f"{log.get_previous_status_display() or 'جديد'} → "
              f"{log.get_new_status_display()} "
              f"({log.changed_at.strftime('%Y-%m-%d %H:%M')} - {user_name})")
    
    # إحصائيات التواريخ
    print("\n" + "-" * 80)
    print("إحصائيات التواريخ:")
    print("-" * 80)
    
    from django.db.models import Min, Max, Count
    from django.db.models.functions import TruncDate
    
    date_stats = ManufacturingStatusLog.objects.aggregate(
        earliest=Min('changed_at'),
        latest=Max('changed_at')
    )
    
    if date_stats['earliest'] and date_stats['latest']:
        print(f"✓ أقدم سجل: {date_stats['earliest'].strftime('%Y-%m-%d %H:%M')}")
        print(f"✓ أحدث سجل: {date_stats['latest'].strftime('%Y-%m-%d %H:%M')}")
        
        # عدد السجلات لكل يوم (أول 10 أيام)
        daily_counts = ManufacturingStatusLog.objects.annotate(
            date=TruncDate('changed_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('-date')[:10]
        
        if daily_counts:
            print("\nتوزيع السجلات (أحدث 10 أيام):")
            for day in daily_counts:
                print(f"  • {day['date']}: {day['count']:,} سجل")
    
    print("\n" + "=" * 80)
    print("✓ اكتملت عملية إعادة بناء سجلات الحالة بنجاح!")
    print("=" * 80)


if __name__ == '__main__':
    try:
        rebuild_status_logs()
    except KeyboardInterrupt:
        print("\n\n⚠ تم إلغاء العملية بواسطة المستخدم")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ حدث خطأ غير متوقع: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
