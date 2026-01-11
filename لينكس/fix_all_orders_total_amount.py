#!/usr/bin/env python
"""
Script لتحديث جميع الطلبات
يصحح قيمة total_amount لتكون المجموع الصحيح قبل الخصم لجميع الطلبات
ويصحح أيضاً مبالغ الخصم في العناصر ويحدث السعر النهائي بعد الخصم
"""
import os
import sys
from pathlib import Path

import django

# إضافة مسار المشروع إلى sys.path
# البحث عن المجلد الذي يحتوي على manage.py
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent  # نفترض أن المشروع في المجلد الأب

# إضافة مسار المشروع
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from decimal import Decimal

from orders.models import Order


def fix_all_orders():
    """تحديث جميع الطلبات وإصلاح الخصومات"""

    all_orders = Order.objects.all().order_by("order_date")
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
            total_before_discount = Decimal("0")
            total_discount = Decimal("0")

            for item in order.items.all():
                # التحقق من صحة القيم
                qty = Decimal(str(item.quantity or 0))
                price = Decimal(str(item.unit_price or 0))
                item_total = qty * price
                total_before_discount += item_total

                # التحقق من وجود نسبة خصم وإصلاح مبلغ الخصم إذا لزم
                discount_pct = Decimal(str(item.discount_percentage or 0))
                old_discount_amt = Decimal(str(item.discount_amount or 0))

                if discount_pct > 0:
                    # حساب مبلغ الخصم الصحيح
                    expected_discount = (item_total * discount_pct) / 100

                    if abs(old_discount_amt - expected_discount) > Decimal("0.01"):
                        print(f"   🔧 إصلاح خصم العنصر: {item.product.name}")
                        print(f"      نسبة الخصم: {discount_pct}%")
                        print(f"      مبلغ الخصم القديم: {old_discount_amt}")
                        print(f"      مبلغ الخصم الجديد: {expected_discount}")

                        # تحديث مبلغ الخصم
                        item.discount_amount = expected_discount
                        item.save(update_fields=["discount_amount"])
                        items_discount_fixed += 1
                        order_modified = True

                    total_discount += expected_discount
                else:
                    # إذا لم يكن هناك نسبة خصم ولكن يوجد مبلغ خصم، نصفره
                    if old_discount_amt > 0:
                        print(f"   🔧 تصفير خصم غير صحيح للعنصر: {item.product.name}")
                        item.discount_amount = Decimal("0")
                        item.save(update_fields=["discount_amount"])
                        items_discount_fixed += 1
                        order_modified = True

            if items_discount_fixed > 0:
                print(f"   ✅ تم إصلاح {items_discount_fixed} عنصر من الخصومات")
                discount_fixed_count += 1

            # استخدام ميثود الموديل لإعادة الحساب بشكل نهائي
            old_total_amount = Decimal(str(order.total_amount or 0))
            old_final_price = Decimal(str(order.final_price or 0))

            # استدعاء الميثود التي قمنا بتصحيحها في الموديل
            order.calculate_final_price(force_update=True)

            new_total_amount = Decimal(str(order.total_amount or 0))
            new_final_price = Decimal(str(order.final_price or 0))

            if abs(new_total_amount - old_total_amount) > Decimal("0.01") or abs(
                new_final_price - old_final_price
            ) > Decimal("0.01"):
                order_modified = True

            # حفظ التغييرات إذا وجدت
            if order_modified:
                order.save(update_fields=["total_amount", "final_price"])
                print(f"   ✅ تم تحديث الطلب بنجاح!")
                print(f"      total_amount: {old_total_amount} -> {order.total_amount}")
                print(
                    f"      final_price: {old_final_price} -> {order.final_price} (يشمل إضافات: {order.financial_addition or 0})"
                )
                fixed_count += 1
            else:
                print(
                    f"   ✓ الطلب صحيح (المبلغ: {order.total_amount} ج.م، النهائي: {order.final_price} ج.م)"
                )
                correct_count += 1

            print()

        except Exception as e:
            print(f"   ❌ حدث خطأ في الطلب {order.order_number}: {e}")
            import traceback

            traceback.print_exc()
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


if __name__ == "__main__":
    print("=" * 80)
    print("تحديث جميع الطلبات - تصحيح total_amount والخصومات")
    print("=" * 80)
    print()

    fix_all_orders()

    print()
