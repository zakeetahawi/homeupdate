#!/usr/bin/env python
"""
تصحيح تواريخ المعاينات للطلبات المحددة لتتناسب مع تواريخ طلباتها المصححة
"""
import os
import sys
import django
from django.utils import timezone
from django.db import transaction
from datetime import datetime

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
# Adjust path to be relative to the script's location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from inspections.models import Inspection
from orders.models import Order


def main():
    """
    تصحيح تواريخ المعاينات للطلبات المحددة
    """
    # أرقام الطلبات التي تحتاج تصحيح تواريخ معايناتها
    target_order_numbers = [
        '12-0389-0004',  # احمد عبد الفتاح
        '9-0628-0002',   # احمد السيد عبد السلام
        '9-0627-0002',   # حسام محمد طل��ت
        '13-0470-0004',  # ميادة الشريف
        '10-0652-0004',  # كريم حسام الدين
        '11-0261-0002',  # عادل حمزة الخضر
        '13-0476-0002',  # فريدة عزام
        '10-0146-0006',  # محمد عبد المنعم
        '13-0759-0002',  # نهلة حسين خليفه
        '10-0888-0002',  # مجدي عويس محمود
        '8-0405-0004',   # ايمن جمال
        '7-0832-0003',   # محمد فؤاد احمد
        '14-0373-0008'   # سحر محمود
    ]
    
    print("🔧 بدء تصحيح تواريخ المعاينات للطلبات المحددة...")
    print("=" * 80)
    
    # البحث عن الطلبات
    target_orders = Order.objects.filter(order_number__in=target_order_numbers)
    
    if not target_orders.exists():
        print("❌ لم يتم العثور على أي من الطلبات المحددة.")
        return
    
    found_orders = list(target_orders.values_list('order_number', flat=True))
    missing_orders = set(target_order_numbers) - set(found_orders)
    
    print(f"✅ تم العثور على {target_orders.count()} طلب من أصل {len(target_order_numbers)}")
    print(f"📋 الطلبات الموجودة: {', '.join(found_orders)}")
    
    if missing_orders:
        print(f"⚠️ الطلبات غير الموجودة: {', '.join(missing_orders)}")
    
    # استخدام معاملة لضمان أن جميع التحديثات تتم بنجاح أو لا يتم أي منها
    with transaction.atomic():
        
        print(f"\n🔄 تصحيح تواريخ المعاينات...")
        print("-" * 60)
        
        total_inspections_updated = 0
        orders_processed = 0
        
        for order in target_orders.order_by('order_number'):
            print(f"\n🔸 معالجة الطلب: {order.order_number}")
            print(f"   📅 تاريخ الطلب الحالي: {order.order_date}")
            
            # البحث عن المعاينات المرتبطة بهذا الطلب
            inspections = Inspection.objects.filter(order=order)
            
            if not inspections.exists():
                print(f"   ⚠️ لا توجد معاينات مرتبطة بهذا الطلب")
                continue
            
            inspections_updated_for_order = 0
            
            for inspection in inspections:
                print(f"   🔍 معاينة ID: {inspection.id}")
                
                # ��رض التواريخ الحالية
                print(f"      📅 تاريخ الإنشاء الحالي: {inspection.created_at}")
                print(f"      ⏰ تاريخ الإكمال الحالي: {inspection.completed_at}")
                
                # تحديث التواريخ بناءً على تاريخ الطلب
                if order.order_date:
                    # تحديث تاريخ الإنشاء ليكون نفس تاريخ الطلب
                    old_created = inspection.created_at
                    inspection.created_at = order.order_date
                    
                    # تحديث تاريخ الإكمال ليكون نفس تاريخ الطلب (إذا كانت المعاينة مكتملة)
                    if inspection.status == 'completed':
                        old_completed = inspection.completed_at
                        inspection.completed_at = order.order_date
                        print(f"      ✅ تحديث تاريخ الإكمال: {old_completed} → {inspection.completed_at}")
                    
                    print(f"      ✅ تحديث تاريخ الإنشاء: {old_created} → {inspection.created_at}")
                    
                    # حفظ التغييرات
                    inspection.save()
                    inspections_updated_for_order += 1
                    total_inspections_updated += 1
                else:
                    print(f"      ⚠️ لا يوجد تاريخ للطلب - لا يمكن التحديث")
            
            print(f"   📊 تم تحديث {inspections_updated_for_order} معاينة لهذا الطلب")
            orders_processed += 1
        
        print(f"\n📊 إحصائيات التحديث النهائية:")
        print("=" * 50)
        print(f"   📋 الطلبات المعالجة: {orders_processed}")
        print(f"   🔍 إجمالي المعاينات المحدثة: {total_inspections_updated}")
        print(f"   🕐 وقت التنفيذ: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # التحقق من النتائج
        print(f"\n🔍 التحقق من النتائج...")
        
        for order in target_orders[:5]:  # عرض أول 5 طلبات للتحقق
            inspections = Inspection.objects.filter(order=order)
            print(f"   📋 الطلب {order.order_number}:")
            print(f"      📅 تاريخ الطلب: {order.order_date}")
            
            for inspection in inspections:
                print(f"      🔍 معاينة {inspection.id}:")
                print(f"         📅 تاريخ الإنشاء: {inspection.created_at}")
                print(f"         ⏰ تاريخ الإكمال: {inspection.completed_at}")
                print(f"         📊 الحالة: {inspection.status}")
                
                # التحقق من التطابق
                if inspection.created_at and order.order_date:
                    if inspection.created_at.date() == order.order_date.date():
                        print(f"         ✅ تاريخ الإنشاء يطابق تاريخ الطلب")
                    else:
                        print(f"         ⚠️ تاريخ الإنشاء لا يطابق تاريخ الطلب")
                
                if inspection.completed_at and order.order_date and inspection.status == 'completed':
                    if inspection.completed_at.date() == order.order_date.date():
                        print(f"         ✅ تاريخ الإكمال يطابق تاريخ الطلب")
                    else:
                        print(f"         ⚠️ تاريخ الإكمال لا يطابق تاريخ الطلب")

    print(f"\n🎉 تم إنجاز تصحيح تواريخ المعاينات بنجاح!")
    print("✨ جميع المعاينات الآن لها تواريخ تتطابق مع تواريخ طلباتها")


if __name__ == "__main__":
    main()