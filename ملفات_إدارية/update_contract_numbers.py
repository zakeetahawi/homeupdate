#!/usr/bin/env python
"""
تحديث أرقام العقود الحالية إلى الصيغة الجديدة
يقوم بتحويل أرقام العقود القديمة إلى الصيغة الجديدة: c01, c02, c03, إلخ
"""
import os
import sys
import django

# إعداد Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import transaction
from orders.models import Order

def update_contract_numbers():
    """تحديث أرقام العقود للطلبات الموجودة"""
    
    print("=" * 60)
    print("تحديث أرقام العقود إلى الصيغة الجديدة")
    print("=" * 60)
    
    # البحث عن الطلبات التي لها contract_number ولكن بصيغة قديمة
    orders_to_update = Order.objects.filter(
        contract_number__isnull=False
    ).exclude(
        contract_number__startswith='c'
    ).order_by('customer', 'created_at')
    
    total_count = orders_to_update.count()
    print(f"\nعدد الطلبات التي سيتم تحديثها: {total_count}")
    
    if total_count == 0:
        print("\nلا توجد طلبات تحتاج للتحديث!")
        return
    
    # تأكيد من المستخدم
    confirm = input("\nهل تريد المتابعة؟ (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("تم الإلغاء.")
        return
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    # تجميع الطلبات حسب العميل
    customer_orders = {}
    for order in orders_to_update:
        if order.customer_id not in customer_orders:
            customer_orders[order.customer_id] = []
        customer_orders[order.customer_id].append(order)
    
    with transaction.atomic():
        for customer_id, customer_order_list in customer_orders.items():
            print(f"\nمعالجة طلبات العميل ID: {customer_id}")
            
            # ترتيب الطلبات حسب تاريخ الإنشاء
            customer_order_list.sort(key=lambda x: x.created_at)
            
            # العثور على أعلى رقم عقد موجود لهذا العميل
            existing_contract_orders = Order.objects.filter(
                customer_id=customer_id,
                contract_number__isnull=False,
                contract_number__startswith='c'
            ).order_by('-contract_number')
            
            next_num = 1
            if existing_contract_orders.exists():
                for order in existing_contract_orders:
                    try:
                        contract_num_str = order.contract_number.lower()
                        if contract_num_str.startswith('c'):
                            num = int(contract_num_str[1:])
                            if num >= next_num:
                                next_num = num + 1
                    except (ValueError, IndexError):
                        continue
            
            # تحديث الطلبات
            for order in customer_order_list:
                try:
                    old_contract_number = order.contract_number
                    
                    # التحقق من أن الطلب يحتاج فعلاً إلى عقد
                    order_types = order.get_order_type_list()
                    if 'tailoring' not in order_types and 'installation' not in order_types:
                        print(f"  - تخطي الطلب {order.order_number}: ليس طلب تسليم أو تركيب")
                        skipped_count += 1
                        continue
                    
                    # توليد رقم عقد جديد
                    new_contract_number = f"c{next_num}"
                    
                    # التحقق من عدم التكرار
                    while Order.objects.filter(
                        customer_id=customer_id,
                        contract_number=new_contract_number
                    ).exclude(pk=order.pk).exists():
                        next_num += 1
                        new_contract_number = f"c{next_num}"
                    
                    order.contract_number = new_contract_number
                    order.save(update_fields=['contract_number'])
                    
                    print(f"  ✓ الطلب {order.order_number}: {old_contract_number} → {new_contract_number}")
                    updated_count += 1
                    next_num += 1
                    
                except Exception as e:
                    print(f"  ✗ خطأ في تحديث الطلب {order.order_number}: {e}")
                    error_count += 1
    
    print("\n" + "=" * 60)
    print("تم الانتهاء من التحديث")
    print("=" * 60)
    print(f"إجمالي الطلبات: {total_count}")
    print(f"تم التحديث: {updated_count}")
    print(f"تم التخطي: {skipped_count}")
    print(f"أخطاء: {error_count}")
    print("=" * 60)

if __name__ == '__main__':
    update_contract_numbers()
