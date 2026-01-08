#!/usr/bin/env python
"""
Script لتحديث جميع الطلبات
يصحح قيمة total_amount لتكون المجموع الصحيح قبل الخصم لجميع الطلبات
ويصحح أيضاً مبالغ الخصم في العناصر ويحدث السعر النهائي بعد الخصم
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
    """تحديث جميع الطلبات وإصلاح الخصومات"""
    
    all_orders = Order.objects.all().order_by('order_date')
    total_orders = all_orders.count()
    
    print(f"📦 عدد الطلبات الإجمالي: {total_orders}")
    print()
    
    fixed_count = 0
    discount_fixed_count = 0
    correct_count = 0
    error_count = 0
    
    for index, order in enumerate(all_orders, 1):
        try:
            print(f"[{index}/{total_orders}] معالجة الطلب: {order.order_number}")
            
            order_modified = False
            items_discount_fixed = 0
            
            # حساب المجموع الصحيح قبل الخصم وإصلاح الخصومات
            total_before_discount = Decimal('0')
            total_discount = Decimal('0')
            
            for item in order.items.all():
                item_total = item.quantity * item.unit_price
                total_before_discount += item_total
                
                # التحقق من وجود نسبة خصم وإصلاح مبلغ الخصم إذا لزم
                discount_pct = item.discount_percentage or Decimal('0')
                old_discount_amt = item.discount_amount or Decimal('0')
                
                if discount_pct and discount_pct > 0:
                    # حساب مبلغ الخصم الصحيح
                    expected_discount = (item_total * discount_pct) / 100
                    
                    if old_discount_amt != expected_discount:
                        print(f"   🔧 إصلاح خصم العنصر: {item.product.name}")
                        print(f"      نسبة الخصم: {discount_pct}%")
                        print(f"      مبلغ الخصم القديم: {old_discount_amt}")
                        print(f"      مبلغ الخصم الجديد: {expected_discount}")
                        
                        # تحديث مبلغ الخصم
                        item.discount_amount = expected_discount
                        item.save(update_fields=['discount_amount'])
                        items_discount_fixed += 1
                        order_modified = True
                    
                    total_discount += expected_discount
                else:
                    # إذا لم يكن هناك نسبة خصم ولكن يوجد مبلغ خصم، نصفره
                    if old_discount_amt and old_discount_amt > 0:
                        print(f"   🔧 تصفير خصم غير صحيح للعنصر: {item.product.name}")
                        item.discount_amount = Decimal('0')
                        item.save(update_fields=['discount_amount'])
                        items_discount_fixed += 1
                        order_modified = True
            
            if items_discount_fixed > 0:
                print(f"   ✅ تم إصلاح {items_discount_fixed} عنصر من الخصومات")
                discount_fixed_count += 1
            
            # التحقق من وجود فرق في total_amount
            if order.total_amount != total_before_discount:
                difference = total_before_discount - order.total_amount
                print(f"   ⚠️  يوجد فرق في المبلغ الإجمالي: {difference} ج.م")
                print(f"      القديم: {order.total_amount} ج.م")
                print(f"      الجديد: {total_before_discount} ج.م")
                
                # تحديث
                order.total_amount = total_before_discount
                order_modified = True
            
            # تحديث السعر النهائي بعد الخصم
            final_price = total_before_discount - total_discount
            old_final_price = order.final_price or Decimal('0')
            
            if old_final_price != final_price:
                print(f"   💰 تحديث السعر النهائي:")
                print(f"      القديم: {old_final_price} ج.م")
                print(f"      الجديد: {final_price} ج.م")
                print(f"      الخصم: {total_discount} ج.م")
                order.final_price = final_price
                order_modified = True
            
            # حفظ التغييرات إذا وجدت
            if order_modified:
                order.save(update_fields=['total_amount', 'final_price'])
                print(f"   ✅ تم تحديث الطلب بنجاح!")
                fixed_count += 1
            else:
                print(f"   ✓ الطلب صحيح (المبلغ: {order.total_amount} ج.م، النهائي: {order.final_price} ج.م)")
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
    print(f"   ✅ طلبات تم تصحيحها: {fixed_count}")
    print(f"   🔧 طلبات تم إصلاح خصوماتها: {discount_fixed_count}")
    print(f"   ✓ طلبات كانت صحيحة: {correct_count}")
    print(f"   ❌ حدثت أخطاء: {error_count}")
    print("=" * 80)

if __name__ == '__main__':
    print("=" * 80)
    print("تحديث جميع الطلبات - تصحيح total_amount والخصومات")
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

