#!/usr/bin/env python
"""
سكريبت لإنشاء أوامر التصنيع المفقودة للطلبات
"""
import os
import sys
import django

# إعداد Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from manufacturing.models import ManufacturingOrder
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

def create_manufacturing_orders(order_ids=None):
    """إنشاء أوامر تصنيع للطلبات المحددة"""
    
    print("=" * 80)
    print("إنشاء أوامر التصنيع المفقودة")
    print("=" * 80)
    
    # إذا تم تحديد IDs معينة
    if order_ids:
        orders = Order.objects.filter(id__in=order_ids)
        print(f"\nعدد الطلبات المحددة: {len(order_ids)}")
    else:
        # إنشاء لجميع الطلبات الصالحة بدون أوامر تصنيع
        from datetime import timedelta
        date_threshold = timezone.now() - timedelta(days=15)
        
        orders = Order.objects.filter(
            models.Q(order_date__gte=date_threshold) | models.Q(created_at__gte=date_threshold)
        ).filter(
            models.Q(selected_types__icontains='installation') |
            models.Q(selected_types__icontains='tailoring') |
            models.Q(selected_types__icontains='accessory')
        ).exclude(
            order_status__in=['cancelled', 'rejected']
        ).annotate(
            manufacturing_count=models.Count('manufacturing_orders')
        ).filter(manufacturing_count=0)
        
        print(f"\nعدد الطلبات الصالحة بدون أوامر تصنيع: {orders.count()}")
    
    if not orders.exists():
        print("\n⚠️  لا توجد طلبات لإنشاء أوامر تصنيع لها")
        return
    
    # الحصول على مستخدم النظام لتسجيل من قام بالإنشاء
    try:
        system_user = User.objects.filter(is_superuser=True).first()
    except:
        system_user = None
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    print("\nبدء إنشاء أوامر التصنيع...\n")
    
    for order in orders:
        try:
            # التحقق من عدم وجود أمر تصنيع
            if ManufacturingOrder.objects.filter(order=order).exists():
                print(f"⏭️  تم تخطي الطلب {order.order_number} (يوجد أمر تصنيع مسبقاً)")
                skipped_count += 1
                continue
            
            # تحديد نوع الطلب
            order_types = order.get_selected_types_list()
            
            # تحديد نوع أمر التصنيع
            if 'installation' in order_types:
                mfg_order_type = 'installation'
            elif 'tailoring' in order_types:
                mfg_order_type = 'delivery'
            elif 'accessory' in order_types:
                mfg_order_type = 'accessory'
            else:
                print(f"⚠️  تم تخطي الطلب {order.order_number} (نوع غير مدعوم: {', '.join(order_types)})")
                skipped_count += 1
                continue
            
            # إنشاء أمر التصنيع
            manufacturing_order = ManufacturingOrder.objects.create(
                order=order,
                order_type=mfg_order_type,
                contract_number=order.contract_number,
                order_date=order.order_date.date() if order.order_date else timezone.now().date(),
                expected_delivery_date=order.expected_delivery_date,
                created_by=system_user,
                status='pending'  # حالة قيد الانتظار
            )
            
            print(f"✅ تم إنشاء أمر تصنيع للطلب {order.order_number} (نوع: {mfg_order_type})")
            created_count += 1
            
        except Exception as e:
            print(f"❌ خطأ في إنشاء أمر تصنيع للطلب {order.order_number}: {str(e)}")
            error_count += 1
    
    # ملخص النتائج
    print("\n" + "=" * 80)
    print("ملخص النتائج:")
    print("=" * 80)
    print(f"✅ تم إنشاء: {created_count} أمر تصنيع")
    print(f"⏭️  تم التخطي: {skipped_count} طلب")
    print(f"❌ أخطاء: {error_count} طلب")
    print("=" * 80)

if __name__ == '__main__':
    from django.db import models
    
    # التحقق من وجود IDs في الأوامر
    if len(sys.argv) > 1:
        order_ids = [int(id) for id in sys.argv[1:]]
        create_manufacturing_orders(order_ids)
    else:
        # إنشاء لجميع الطلبات الصالحة
        print("\nلم يتم تحديد IDs، سيتم إنشاء أوامر تصنيع لجميع الطلبات الصالحة خلال آخر 15 يوم")
        print("للتأكيد، اكتب 'yes' للمتابعة أو أي شيء آخر للإلغاء: ", end='')
        confirmation = input().strip().lower()
        
        if confirmation == 'yes':
            create_manufacturing_orders()
        else:
            print("\n❌ تم الإلغاء")
