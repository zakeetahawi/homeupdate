#!/usr/bin/env python3
"""
اختبار تحديث حالة التركيب لأمر تصنيع واحد
Test updating installation status for a single manufacturing order
"""

import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from manufacturing.models import ManufacturingOrder
from orders.models import Order


def test_single_update():
    """اختبار تحديث أمر واحد"""
    print("🧪 اختبار تحديث حالة أمر تصنيع واحد...")
    print("=" * 50)
    
    # البحث عن أمر تصنيع من نوع التركيب مع حالة needs_scheduling
    mfg_order = ManufacturingOrder.objects.filter(
        order_type='installation',
        status='ready_install',
        order__installation_status='needs_scheduling'
    ).select_related('order').first()
    
    if not mfg_order:
        print("❌ لم يتم العثور على أمر تصنيع مناسب للاختبار")
        return
    
    print(f"📋 أمر التصنيع: {mfg_order.manufacturing_code}")
    print(f"📋 رقم الطلب: {mfg_order.order.order_number}")
    print(f"📋 العميل: {mfg_order.order.customer.name if mfg_order.order.customer else 'غير محدد'}")
    print(f"📋 حالة التصنيع الحالية: {mfg_order.get_status_display()} ({mfg_order.status})")
    print(f"📋 حالة التركيب الحالية: {mfg_order.order.get_installation_status_display()} ({mfg_order.order.installation_status})")
    
    # تحديث الحالة
    print(f"\n🔄 تحديث حالة التصنيع إلى 'completed'...")
    
    old_manufacturing_status = mfg_order.status
    old_installation_status = mfg_order.order.installation_status
    
    # تحديث حالة التصنيع
    mfg_order.status = 'completed'
    mfg_order.save()
    
    # تحديث حالة التركيب
    mfg_order.order.installation_status = 'completed'
    mfg_order.order.save(update_fields=['installation_status'])
    
    # إعادة تحميل البيانات من قاعدة البيانات
    mfg_order.refresh_from_db()
    mfg_order.order.refresh_from_db()
    
    print(f"✅ تم التحديث بنجاح!")
    print(f"📋 حالة التصنيع الجديدة: {mfg_order.get_status_display()} ({mfg_order.status})")
    print(f"📋 حالة التركيب الجديدة: {mfg_order.order.get_installation_status_display()} ({mfg_order.order.installation_status})")
    
    # التحقق من التحديث في قاعدة البيانات
    fresh_mfg_order = ManufacturingOrder.objects.select_related('order').get(pk=mfg_order.pk)
    
    print(f"\n🔍 التحقق من قاعدة البيانات:")
    print(f"📋 حالة التصنيع في قاعدة البيانات: {fresh_mfg_order.get_status_display()} ({fresh_mfg_order.status})")
    print(f"📋 حالة التركيب في قاعدة البيانات: {fresh_mfg_order.order.get_installation_status_display()} ({fresh_mfg_order.order.installation_status})")
    
    if (fresh_mfg_order.status == 'completed' and 
        fresh_mfg_order.order.installation_status == 'completed'):
        print(f"🎉 الاختبار نجح! التحديث تم بشكل صحيح في قاعدة البيانات")
    else:
        print(f"❌ الاختبار فشل! هناك مشكلة في التحديث")
    
    return mfg_order


if __name__ == "__main__":
    test_single_update()
