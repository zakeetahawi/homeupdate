#!/usr/bin/env python
"""
⚡ اختبار سريع لأداء الويزارد
Quick Wizard Performance Test

الاستخدام:
python test_wizard_performance.py
"""

import os
import sys
import time
from decimal import Decimal

import django

# إعداد Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
sys.path.insert(0, "/home/zakee/homeupdate")
django.setup()

from django.db import connection, reset_queries
from django.test.utils import override_settings

from accounts.models import Branch, User
from customers.models import Customer
from inventory.models import Product
from orders.wizard_models import DraftOrder, DraftOrderItem


class QueryCounter:
    """عداد الاستعلامات"""

    def __enter__(self):
        reset_queries()
        self.start_count = len(connection.queries)
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.query_count = len(connection.queries) - self.start_count
        self.duration = time.time() - self.start_time

    def report(self, operation_name):
        print(f"\n{'='*60}")
        print(f"📊 {operation_name}")
        print(f"{'='*60}")
        print(f"⚡ Queries: {self.query_count}")
        print(f"⏱️  Duration: {self.duration*1000:.2f}ms")
        print(f"{'='*60}\n")


def test_wizard_performance():
    """اختبار أداء الويزارد"""

    print("\n" + "=" * 60)
    print("🚀 بدء اختبار أداء الويزارد")
    print("=" * 60 + "\n")

    # الحصول على مستخدم للاختبار
    user = User.objects.filter(is_active=True).first()
    if not user:
        print("❌ لا يوجد مستخدمون نشطون")
        return

    print(f"👤 المستخدم: {user.username}")

    # 1. اختبار wizard_start (جلب المسودات)
    print("\n1️⃣  اختبار wizard_start - جلب المسودات")
    from orders.performance_optimizations import get_user_drafts_optimized

    with QueryCounter() as counter:
        drafts = get_user_drafts_optimized(user, is_completed=False, limit=10)
        draft_count = len(list(drafts))
    counter.report(f"wizard_start - جلب {draft_count} مسودة")

    # 2. اختبار إنشاء مسودة
    print("\n2️⃣  اختبار إنشاء مسودة جديدة")
    customer = Customer.objects.first()
    branch = Branch.objects.filter(is_active=True).first()

    with QueryCounter() as counter:
        draft = DraftOrder.objects.create(
            created_by=user, customer=customer, branch=branch, current_step=1
        )
    counter.report("إنشاء مسودة جديدة")

    # 3. اختبار إضافة عناصر (bulk)
    print("\n3️⃣  اختبار إضافة 10 عناصر (bulk create)")
    products = list(Product.objects.all()[:10])

    with QueryCounter() as counter:
        items_to_create = [
            DraftOrderItem(
                draft_order=draft,
                product=product,
                quantity=Decimal("1.0"),
                unit_price=product.price or Decimal("100.0"),
                discount_percentage=Decimal("0.0"),
                item_type="product",
            )
            for product in products
        ]
        DraftOrderItem.objects.bulk_create(items_to_create)
    counter.report(f"إضافة {len(items_to_create)} عنصر (bulk)")

    # 4. اختبار حساب المجاميع (optimized)
    print("\n4️⃣  اختبار حساب المجاميع (aggregation)")
    with QueryCounter() as counter:
        totals = draft.calculate_totals()
    counter.report("حساب المجاميع")

    print(f"   💰 Subtotal: {draft.subtotal}")
    print(f"   💸 Discount: {draft.total_discount}")
    print(f"   💵 Final: {draft.final_total}")

    # 5. اختبار جلب المسودة مع كل العلاقات
    print("\n5️⃣  اختبار جلب المسودة مع العلاقات")
    from orders.performance_optimizations import get_draft_with_relations

    with QueryCounter() as counter:
        full_draft = get_draft_with_relations(draft.id, user)
        items = list(full_draft.items.all())
    counter.report(f"جلب المسودة + {len(items)} عنصر")

    # 6. اختبار wizard_step_3 (عرض العناصر)
    print("\n6️⃣  اختبار wizard_step_3 - عرض العناصر")
    with QueryCounter() as counter:
        items_display = draft.items.select_related("product", "product__category").all()
        items_list = list(items_display)
    counter.report(f"عرض {len(items_list)} عنصر مع select_related")

    # 7. اختبار Cache
    print("\n7️⃣  اختبار Cache للمجاميع")
    from django.core.cache import cache

    cache_key = f"draft_totals_{draft.id}"

    # أول مرة - من قاعدة البيانات
    cache.delete(cache_key)
    with QueryCounter() as counter1:
        totals1 = draft.calculate_totals()

    # ثاني مرة - من Cache
    cache.set(cache_key, totals1, 300)
    with QueryCounter() as counter2:
        totals2 = cache.get(cache_key)

    print(f"   ⚡ استعلامات (بدون cache): {counter1.query_count}")
    print(f"   ⚡ استعلامات (مع cache): {counter2.query_count}")
    print(f"   ⏱️  وقت (بدون cache): {counter1.duration*1000:.2f}ms")
    print(f"   ⏱️  وقت (مع cache): {counter2.duration*1000:.2f}ms")
    print(
        f"   📈 تحسين: {((counter1.duration - counter2.duration) / counter1.duration * 100):.1f}%"
    )

    # 8. التنظيف
    print("\n8️⃣  تنظيف البيانات التجريبية")
    draft.delete()
    print("   ✅ تم حذف المسودة التجريبية")

    # النتيجة النهائية
    print("\n" + "=" * 60)
    print("✅ اكتمل الاختبار بنجاح!")
    print("=" * 60)
    print("\n📊 الملاحظات:")
    print("   • استخدم select_related لتقليل الاستعلامات")
    print("   • bulk_create أسرع من save() المتكرر")
    print("   • aggregation أسرع من الحلقات")
    print("   • Cache يقلل الاستعلامات بشكل كبير")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    test_wizard_performance()
