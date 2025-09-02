#!/usr/bin/env python
"""
تبديل حالة جميع المعاينات والطلبات وأوامر التصنيع إلى مكتملة وناجحة.
"""
import os
import sys
import django
from django.utils import timezone
from django.db import transaction

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
# Adjust path to be relative to the script's location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from inspections.models import Inspection
from manufacturing.models import ManufacturingOrder
from installations.models import InstallationSchedule
from orders.models import Order


def main():
    """
    الوظيفة الرئيسية لتنفيذ التحديثات على المعاينات وأوامر التصنيع والتركيبات.
    """
    # استخدام معاملة لضمان أن جميع التحديثات تتم بنجاح أو لا يتم أي منها
    with transaction.atomic():
        # 1. تحديث جميع المعاينات إلى 'مكتملة' و 'ناجحة'
        print("🔄 بدء تحديث المعاينات إلى 'مكتملة' و 'ناجحة'...")
        
        # أولاً: إصلاح القيم الخاطئة الموجودة (success -> passed)
        wrong_results = Inspection.objects.filter(result='success')
        if wrong_results.exists():
            print(f"🔧 إصلاح {wrong_results.count()} معاينة تحتوي على قيمة 'success' خاطئة...")
            wrong_results.update(result='passed')
        
        # ثانياً: تحديث المعاينات غير المكتملة
        inspections_to_update = Inspection.objects.exclude(status='completed')
        count = 0
        for inspection in inspections_to_update:
            inspection.status = 'completed'
            inspection.result = 'passed'  # 'passed' هي القيمة الصحيحة من الخيارات
            # سيقوم التابع save بمعالجة تعيين completed_at
            inspection.save()
            count += 1
        print(f"✅ تم تحديث {count} معاينة جديدة.")
        
        # ثالثاً: التأكد من أن جميع المعاينات المكتملة لها نتيجة صحيحة
        completed_without_result = Inspection.objects.filter(status='completed', result__isnull=True)
        if completed_without_result.exists():
            print(f"🔧 إضافة نتيجة لـ {completed_without_result.count()} معاينة مكتملة بدون نتيجة...")
            completed_without_result.update(result='passed')
        
        print(f"✅ تم الانتهاء من تحديث جميع المعاينات.")

        # 2. تحديث جميع أوامر التصنيع إلى 'تم التسليم'
        print("🔄 بدء تحديث أوامر التصنيع إلى 'تم التسليم'...")
        manufacturing_orders_to_update = ManufacturingOrder.objects.exclude(status__in=['delivered', 'completed'])
        count = 0
        for manu_order in manufacturing_orders_to_update.select_related('order'):
            # تعيين الحالة والحقول المرتبطة
            manu_order.status = 'delivered'
            manu_order.delivery_recipient_name = 'المستلم 2024'
            manu_order.delivery_permit_number = '2024'
            
            # تعيين تواريخ الإكمال والتسليم من تاريخ الطلب الأصلي
            if manu_order.order and manu_order.order.order_date:
                order_date = manu_order.order.order_date
                manu_order.completion_date = order_date
                manu_order.delivery_date = order_date
            else:
                # تعيين تاريخ احتياطي إذا لم يكن تاريخ الطلب متاحًا
                manu_order.completion_date = timezone.now()
                manu_order.delivery_date = timezone.now()

            # سيقوم التابع save بتشغيل update_order_status (إذا كان متصلاً عبر إشارة)
            manu_order.save()
            # استدعاء التابع يدوياً لضمان تحديث حالة الطلب
            manu_order.update_order_status()
            count += 1
        print(f"✅ تم تحديث {count} أمر تصنيع.")

        # 3. إنشاء جدولة تركيب لجميع طلبات التركيب التي لا تحتوي على جدولة
        print("🔄 بدء إنشاء جدولة التركيب للطلبات التي تحتاج تركيب...")
        installation_orders = Order.objects.filter(
            selected_types__contains='installation'
        ).exclude(
            id__in=InstallationSchedule.objects.values_list('order_id', flat=True)
        )
        
        created_count = 0
        for order in installation_orders:
            # إنشاء جدولة تركيب جديدة
            installation_schedule = InstallationSchedule.objects.create(
                order=order,
                scheduled_date=order.order_date.date() if order.order_date else timezone.now().date(),
                completion_date=order.order_date if order.order_date else timezone.now(),
                status='completed',
                notes=f'تم إنشاء الجدولة تلقائياً للطلب {order.order_number}'
            )
            created_count += 1
        print(f"✅ تم إنشاء {created_count} جدولة تركيب جديدة.")

        # 4. تحديث جميع التركيبات الموجودة إلى 'مكتمل'
        print("🔄 بدء تحديث جميع التركيبات إلى 'مكتمل'...")
        installations_to_update = InstallationSchedule.objects.exclude(status='completed').select_related('order')
        count = 0
        for inst in installations_to_update:
            # استخدام order_date للجدولة والإكمال
            if inst.order and inst.order.order_date:
                event_date = inst.order.order_date
            else:
                event_date = inst.created_at  # استخدام وقت الإنشاء كاحتياطي

            # تحديث تاريخ الجدولة إذا لم يكن محدداً
            if not inst.scheduled_date:
                inst.scheduled_date = event_date.date()
            
            # تحديث تاريخ الإكمال
            inst.completion_date = event_date
            inst.status = 'completed'
            
            # سيقوم التابع save بمعالجة منطق الحفظ الخاص به
            inst.save()
            count += 1
        print(f"✅ تم تحديث {count} تركيب موجود.")

        # 5. مزامنة جميع حالات الطلبات الرئيسية لضمان الاتساق
        print("🔄 مزامنة الحالات النهائية لجميع الطلبات...")
        all_orders = Order.objects.all()
        count = 0
        for order in all_orders:
            # هذا التابع يستدعي update_installation_status, update_inspection_status, و update_completion_status
            order.update_all_statuses()
            count += 1
        print(f"✅ تمت مزامنة {count} طلب.")

    print("\n🎉 تم إنجاز جميع التحديثات بنجاح!")


if __name__ == "__main__":
    main()