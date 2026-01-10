#!/usr/bin/env python
"""
سكريبت لمرة واحدة: إقفال أوامر التقطيع وإتمام استلام الأقمشة للطلبات ذات أوامر التصنيع المكتملة

الاستخدام:
    python manage.py shell < لينكس/complete_cutting_orders_by_manufacturing_status.py

أو:
    python manage.py shell
    >>> exec(open('لينكس/complete_cutting_orders_by_manufacturing_status.py').read())
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'homeupdate.settings')

try:
    django.setup()
except:
    pass  # Django may already be set up if running from shell

from django.utils import timezone
from django.db import transaction
from cutting.models import CuttingOrder
from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem, FabricReceipt, FabricReceiptItem

print("=" * 70)
print("🔄 بدء إقفال أوامر التقطيع وإتمام استلام الأقمشة")
print("=" * 70)

# الحالات التي تعني أن التصنيع مكتمل
MANUFACTURING_COMPLETED_STATUSES = ['completed', 'ready_for_installation', 'delivered']

# البحث عن أوامر التقطيع غير المكتملة
cutting_orders_to_check = CuttingOrder.objects.exclude(status='completed')

total_checked = cutting_orders_to_check.count()
print(f"\n📊 عدد أوامر التقطيع غير المكتملة للفحص: {total_checked}")

if total_checked == 0:
    print("✅ جميع أوامر التقطيع مكتملة بالفعل.")

updated_count = 0
skipped_count = 0
error_count = 0
fabric_receipt_count = 0

for cutting_order in cutting_orders_to_check:
    try:
        # البحث عن أمر التصنيع المرتبط بنفس الطلب
        manufacturing_order = ManufacturingOrder.objects.filter(
            order=cutting_order.order
        ).order_by('-created_at').first()
        
        if not manufacturing_order:
            print(f"  ⏭️  أمر التقطيع {cutting_order.cutting_code}: لا يوجد أمر تصنيع مرتبط - تم التخطي")
            skipped_count += 1
            continue
        
        # التحقق من حالة أمر التصنيع
        if manufacturing_order.status not in MANUFACTURING_COMPLETED_STATUSES:
            print(f"  ⏭️  أمر التقطيع {cutting_order.cutting_code}: حالة التصنيع ({manufacturing_order.get_status_display()}) غير مكتملة - تم التخطي")
            skipped_count += 1
            continue
        
        # تحديث حالة أمر التقطيع إلى مكتمل
        with transaction.atomic():
            old_status = cutting_order.status
            cutting_order.status = 'completed'
            cutting_order.completed_at = timezone.now()
            cutting_order.notes = (cutting_order.notes or '') + f'\n[تم الإقفال تلقائياً - سكريبت] أمر التصنيع: {manufacturing_order.status}'
            cutting_order.save(update_fields=['status', 'completed_at', 'notes'])
            
            # تحديث حالة جميع عناصر التقطيع غير المكتملة إلى مكتملة
            items_updated = cutting_order.items.exclude(status='completed').update(
                status='completed'
            )
            
            updated_count += 1
            print(f"  ✅ تم إقفال: {cutting_order.cutting_code} (كان {old_status} → completed) | أمر التصنيع: {manufacturing_order.status} | عناصر محدثة: {items_updated}")
            
    except Exception as e:
        error_count += 1
        print(f"  ❌ خطأ في أمر التقطيع {cutting_order.cutting_code}: {str(e)}")

print("\n" + "=" * 70)
print("📦 بدء إتمام استلام الأقمشة من المصنع")
print("=" * 70)

# الجزء الثاني: إتمام استلام الأقمشة لأوامر التصنيع المكتملة
manufacturing_orders_completed = ManufacturingOrder.objects.filter(
    status__in=MANUFACTURING_COMPLETED_STATUSES
)

print(f"\n📊 عدد أوامر التصنيع المكتملة: {manufacturing_orders_completed.count()}")

for mfg_order in manufacturing_orders_completed:
    try:
        # البحث عن عناصر التصنيع التي لم يتم استلامها
        unreceived_items = mfg_order.items.filter(fabric_received=False)
        
        if not unreceived_items.exists():
            continue
        
        with transaction.atomic():
            for item in unreceived_items:
                # تحديث حالة الاستلام في ManufacturingOrderItem
                item.fabric_received = True
                item.fabric_received_date = timezone.now()
                item.fabric_notes = (item.fabric_notes or '') + '\n[تم الاستلام تلقائياً - سكريبت إتمام أوامر التقطيع]'
                
                # تعيين رقم شنطة تلقائي إذا لم يكن موجوداً
                if not item.bag_number:
                    item.bag_number = 'AUTO-SCRIPT'
                
                item.save(update_fields=['fabric_received', 'fabric_received_date', 'fabric_notes', 'bag_number'])
                
                # تحديث حالة الاستلام في CuttingOrderItem أيضاً (لإخفائه من صفحة الاستلام)
                if item.cutting_item:
                    item.cutting_item.fabric_received = True
                    item.cutting_item.save(update_fields=['fabric_received'])
                
                # البحث عن عناصر التقطيع المرتبطة عبر order_item إذا لم يكن هناك ربط مباشر
                if item.order_item:
                    from cutting.models import CuttingOrderItem
                    CuttingOrderItem.objects.filter(
                        order_item=item.order_item,
                        fabric_received=False
                    ).update(fabric_received=True)
                
                # إنشاء سجل FabricReceipt إذا لم يكن موجوداً
                fabric_receipt, created = FabricReceipt.objects.get_or_create(
                    manufacturing_order=mfg_order,
                    bag_number=item.bag_number,
                    defaults={
                        'receipt_type': 'manufacturing_order',
                        'order': mfg_order.order,
                        'permit_number': item.permit_number or 'AUTO-SCRIPT',
                        'received_by_name': 'نظام آلي',
                        'receipt_date': timezone.now(),
                        'notes': 'تم الاستلام تلقائياً - سكريبت إتمام أوامر التقطيع'
                    }
                )
                
                # إنشاء عنصر الاستلام إذا لم يكن موجوداً
                if not FabricReceiptItem.objects.filter(
                    fabric_receipt=fabric_receipt,
                    order_item=item.order_item
                ).exists():
                    FabricReceiptItem.objects.create(
                        fabric_receipt=fabric_receipt,
                        order_item=item.order_item,
                        cutting_item=item.cutting_item,
                        product_name=item.product_name,
                        quantity_received=item.quantity,
                        item_notes='تم الاستلام تلقائياً - سكريبت'
                    )
                
                fabric_receipt_count += 1
            
            print(f"  📦 تم إتمام استلام {unreceived_items.count()} عنصر لأمر التصنيع: {mfg_order.manufacturing_code}")
            
    except Exception as e:
        error_count += 1
        print(f"  ❌ خطأ في أمر التصنيع {mfg_order.manufacturing_code}: {str(e)}")

print("\n" + "=" * 70)
print(f"📊 ملخص التحديث النهائي:")
print(f"   - أوامر التقطيع المفحوصة: {total_checked}")
print(f"   - أوامر التقطيع المُقفلة: {updated_count}")
print(f"   - تم التخطي: {skipped_count}")
print(f"   - عناصر استلام الأقمشة المُكتملة: {fabric_receipt_count}")
print(f"   - أخطاء: {error_count}")
print("=" * 70)
print("✅ اكتمل السكريبت!")

