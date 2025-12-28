#!/usr/bin/env python
"""
Script لتحديث جميع الطلبات
يصحح قيمة total_amount لتكون المجموع الصحيح قبل الخصم لجميع الطلبات
"""
import os
import sys
import django
from pathlib import Path

# إضافة مسار المشروع إلى sys.path
# البحث عن المجلد الذي يحتوي على manage.py
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent  # نفترض أن المشروع في المجلد الأب

# إضافة مسار المشروع
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from decimal import Decimal

def fix_all_orders():
    """تحديث جميع الطلبات"""
    
    all_orders = Order.objects.all().order_by('order_date')
    total_orders = all_orders.count()
    
    print(f"📦 عدد الطلبات الإجمالي: {total_orders}")
    print()
    
    fixed_count = 0
    correct_count = 0
    error_count = 0
    
    for index, order in enumerate(all_orders, 1):
        try:
            print(f"[{index}/{total_orders}] معالجة الطلب: {order.order_number}")
            
            # حساب المجموع الصحيح قبل الخصم
            total_before_discount = Decimal('0')
            total_discount = Decimal('0')
            
            for item in order.items.all():
                item_total = item.quantity * item.unit_price
                item_discount = item.discount_amount if item.discount_amount else Decimal('0')
                
                total_before_discount += item_total
                total_discount += item_discount
            
            # التحقق من وجود فرق
            if order.total_amount != total_before_discount:
                difference = total_before_discount - order.total_amount
                print(f"   ⚠️  يوجد فرق: {difference} ج.م")
                print(f"      القديم: {order.total_amount} ج.م")
                print(f"      الجديد: {total_before_discount} ج.م")
                
                # تحديث
                order.total_amount = total_before_discount
                order.save(update_fields=['total_amount'])
                
                print(f"   ✅ تم التحديث بنجاح!")
                fixed_count += 1
            else:
                print(f"   ✓ القيمة صحيحة ({order.total_amount} ج.م)")
                correct_count += 1
            
            print()
            
        except Exception as e:
            print(f"   ❌ حدث خطأ: {e}")
            error_count += 1
            print()
    
    # ملخص النتائج
    print("=" * 80)
    print("📊 ملخص النتائج:")
    print("=" * 80)
    print(f"   إجمالي الطلبات: {total_orders}")
    print(f"   ✅ تم تصحيحها: {fixed_count}")
    print(f"   ✓ كانت صحيحة: {correct_count}")
    print(f"   ❌ حدثت أخطاء: {error_count}")
    print("=" * 80)

if __name__ == '__main__':
    print("=" * 80)
    print("تحديث جميع الطلبات - تصحيح total_amount")
    print("=" * 80)
    print()
    
    # تأكيد من المستخدم
    response = input("⚠️  هل أنت متأكد من تحديث جميع الطلبات؟ (نعم/لا): ")
    
    if response.strip().lower() in ['نعم', 'yes', 'y']:
        print()
        fix_all_orders()
    else:
        print("\n❌ تم إلغاء العملية")
    
    print()
