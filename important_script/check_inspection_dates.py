#!/usr/bin/env python
"""
التحقق من تواريخ المعاينات مقارنة بتواريخ الطلبات المرتبطة بها
"""
import os
import sys
import django
from django.utils import timezone

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
# Adjust path to be relative to the script's location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from inspections.models import Inspection
from orders.models import Order


def main():
    """
    التحقق من تواريخ المعاينات للطلبات المحددة
    """
    # أرقام الطلبات المشكوك في تواريخها
    suspicious_order_numbers = [
        '9-0628-0002',
        '9-0627-0002', 
        '12-0389-0004',
        '13-0470-0004',
        '10-0652-0004',
        '11-0261-0002',
        '13-0476-0002',
        '10-0146-0006',
        '13-0759-0002',
        '10-0888-0002',
        '8-0405-0004',
        '7-0832-0003',
        '14-0373-0008'
    ]
    
    print("🔍 التحقق من تواريخ المعاينات للطلبات المحددة...")
    print("=" * 80)
    
    # البحث عن الطلبات
    orders = Order.objects.filter(order_number__in=suspicious_order_numbers)
    
    if not orders.exists():
        print("❌ لم يتم العثور على أي من الطلبات المحددة.")
        return
    
    found_orders = list(orders.values_list('order_number', flat=True))
    missing_orders = set(suspicious_order_numbers) - set(found_orders)
    
    print(f"✅ تم العثور على {orders.count()} طلب من أصل {len(suspicious_order_numbers)}")
    
    if missing_orders:
        print(f"⚠️ الطلبات غير الموجودة: {', '.join(missing_orders)}")
    
    print("\n📋 تفاصيل الطلبات والمعاينات:")
    print("-" * 80)
    
    issues_found = 0
    
    for order in orders.order_by('order_number'):
        print(f"\n🔸 الطلب: {order.order_number}")
        print(f"   📅 تاريخ الطلب: {order.order_date}")
        print(f"   👤 العميل: {order.customer_name if hasattr(order, 'customer_name') else 'غير محدد'}")
        
        # البحث عن المعاينات المرتبطة بهذا الطلب
        inspections = Inspection.objects.filter(order=order)
        
        if not inspections.exists():
            print("   ❌ لا توجد معاينات مرتبطة بهذا الطلب")
            continue
        
        print(f"   🔍 عدد المعاينات: {inspections.count()}")
        
        for i, inspection in enumerate(inspections, 1):
            print(f"   📝 المعاينة {i}:")
            print(f"      - ID: {inspection.id}")
            print(f"      - الحالة: {inspection.status}")
            print(f"      - النتيجة: {inspection.result}")
            print(f"      - تاريخ الإنشاء: {inspection.created_at}")
            print(f"      - تاريخ الإكمال: {inspection.completed_at}")
            
            # التحقق من التطابق مع تاريخ الطلب
            if inspection.completed_at and order.order_date:
                if inspection.completed_at.date() != order.order_date.date():
                    print(f"      ⚠️ تاريخ الإكمال لا يطابق تاريخ الطلب!")
                    print(f"         - تاريخ الطلب: {order.order_date.date()}")
                    print(f"         - تاريخ إكمال المعاينة: {inspection.completed_at.date()}")
                    issues_found += 1
                else:
                    print(f"      ✅ تاريخ الإكمال يطابق تاريخ الطلب")
            elif inspection.completed_at is None:
                print(f"      ⚠️ لا يوجد تاريخ إكمال للمعاينة")
                issues_found += 1
            elif order.order_date is None:
                print(f"      ⚠️ لا يوجد تاريخ للطلب")
                issues_found += 1
        
        print("-" * 40)
    
    # ملخص النتائج
    print(f"\n📊 ملخص النتائج:")
    print(f"   📋 إجمالي الطلبات المفحوصة: {orders.count()}")
    print(f"   ⚠️ المشاكل المكتشفة: {issues_found}")
    
    if issues_found > 0:
        print(f"\n🔧 يُنصح بتشغيل سكريبت تصحيح التواريخ لإصلاح هذه المشاكل.")
    else:
        print(f"\n✅ جميع التواريخ صحيحة!")


if __name__ == "__main__":
    main()