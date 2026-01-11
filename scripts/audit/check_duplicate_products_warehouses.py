#!/usr/bin/env python
"""
فحص الأصناف المكررة في أكثر من مستودع
يعرض كيف تم إدراج المنتجات في مستودعات متعددة
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "home_update.settings")
django.setup()

from django.db.models import Count, Q

from inventory.models import Product, StockTransaction, Warehouse


def check_duplicate_products():
    """فحص المنتجات الموجودة في أكثر من مستودع"""

    print("=" * 80)
    print("📊 فحص الأصناف المكررة في المستودعات")
    print("=" * 80)

    # البحث عن المنتجات التي لها معاملات في أكثر من مستودع
    products_with_transactions = (
        StockTransaction.objects.values("product")
        .annotate(warehouse_count=Count("warehouse", distinct=True))
        .filter(warehouse_count__gt=1)
        .order_by("-warehouse_count")
    )

    print(f"\n🔍 عدد المنتجات في أكثر من مستودع: {len(products_with_transactions)}")

    if not products_with_transactions:
        print("\n✅ لا توجد منتجات مكررة في المستودعات")
        return

    print("\n" + "=" * 80)
    print("📦 المنتجات المكررة (أول 20 منتج):")
    print("=" * 80)

    for idx, item in enumerate(products_with_transactions[:20], 1):
        try:
            product = Product.objects.get(id=item["product"])
            warehouse_count = item["warehouse_count"]

            print(f"\n{idx}. 📦 {product.name}")
            print(f"   🆔 الكود: {product.code}")
            print(
                f"   🏷️ الفئة: {product.category.name if product.category else 'غير محدد'}"
            )
            print(f"   🏪 عدد المستودعات: {warehouse_count}")

            # الحصول على المعاملات لكل مستودع
            transactions = StockTransaction.objects.filter(product=product)

            warehouses_data = {}
            for t in transactions:
                if t.warehouse.id not in warehouses_data:
                    warehouses_data[t.warehouse.id] = {
                        "warehouse": t.warehouse,
                        "first_transaction": t,
                        "last_transaction": t,
                        "in_count": 0,
                        "out_count": 0,
                        "current_balance": 0,
                    }

                data = warehouses_data[t.warehouse.id]

                # تحديث أول وآخر معاملة
                if t.transaction_date < data["first_transaction"].transaction_date:
                    data["first_transaction"] = t
                if t.transaction_date > data["last_transaction"].transaction_date:
                    data["last_transaction"] = t
                    data["current_balance"] = t.running_balance

                # عد المعاملات
                if t.transaction_type == "in":
                    data["in_count"] += 1
                elif t.transaction_type == "out":
                    data["out_count"] += 1

            print(f"\n   💰 تفاصيل المستودعات:")
            for wid, data in warehouses_data.items():
                w = data["warehouse"]
                first = data["first_transaction"]
                last = data["last_transaction"]

                print(f"\n   🏪 {w.name}:")
                print(
                    f"      📅 أول معاملة: {first.transaction_date.strftime('%Y-%m-%d')} - {first.transaction_type} ({first.quantity} وحدة)"
                )
                print(
                    f"      📅 آخر معاملة: {last.transaction_date.strftime('%Y-%m-%d')} - {last.transaction_type} ({last.quantity} وحدة)"
                )
                print(
                    f"      📊 معاملات الدخول: {data['in_count']} | معاملات الخروج: {data['out_count']}"
                )
                print(f"      💰 الرصيد الحالي: {data['current_balance']} وحدة")

                # تحديد كيف تم الإدراج
                if first.transaction_type == "in":
                    print(f"      ✅ تم إدراجه بمعاملة دخول طبيعية")
                elif first.transaction_type == "transfer_in":
                    print(f"      🔄 تم نقله من مستودع آخر")
                elif first.transaction_type == "opening_balance":
                    print(f"      📊 رصيد افتتاحي")
                else:
                    print(
                        f"      ⚠️ تم إدراجه بمعاملة غير معتادة: {first.transaction_type}"
                    )

            print("-" * 80)

        except Product.DoesNotExist:
            continue

    if len(products_with_transactions) > 20:
        print(f"\n... وهناك {len(products_with_transactions) - 20} منتج آخر")

    # إحصائيات عامة
    print("\n" + "=" * 80)
    print("📊 إحصائيات التكرار:")
    print("=" * 80)

    in_2_warehouses = len(
        [p for p in products_with_transactions if p["warehouse_count"] == 2]
    )
    in_3_warehouses = len(
        [p for p in products_with_transactions if p["warehouse_count"] == 3]
    )
    in_4_plus = len(
        [p for p in products_with_transactions if p["warehouse_count"] >= 4]
    )

    print(f"📦 منتجات في مستودعين: {in_2_warehouses}")
    print(f"📦 منتجات في 3 مستودعات: {in_3_warehouses}")
    print(f"📦 منتجات في 4+ مستودعات: {in_4_plus}")

    # تحليل أسباب التكرار
    print("\n" + "=" * 80)
    print("🔍 تحليل أسباب التكرار:")
    print("=" * 80)

    total_transfers = StockTransaction.objects.filter(
        transaction_type__in=["transfer_in", "transfer_out"]
    ).count()

    print(f"🔄 إجمالي معاملات النقل: {total_transfers}")

    # فحص المنتجات بدون نقل لكن في مستودعات متعددة
    products_without_transfer = []
    for item in products_with_transactions[:50]:
        try:
            product = Product.objects.get(id=item["product"])
            has_transfer = StockTransaction.objects.filter(
                product=product, transaction_type__in=["transfer_in", "transfer_out"]
            ).exists()

            if not has_transfer:
                products_without_transfer.append(product)
        except:
            continue

    if products_without_transfer:
        print(
            f"\n⚠️ منتجات في مستودعات متعددة بدون معاملات نقل: {len(products_without_transfer)}"
        )
        print("   (قد يكون السبب: معاملات دخول مباشرة أو رصيد افتتاحي في كل مستودع)")

        for p in products_without_transfer[:5]:
            print(f"\n   📦 {p.name} ({p.code})")
            transactions = StockTransaction.objects.filter(product=p)
            warehouses = transactions.values("warehouse__name").distinct()
            print(
                f"      🏪 المستودعات: {', '.join([w['warehouse__name'] for w in warehouses])}"
            )

    print("\n" + "=" * 80)
    print("💡 التوصيات:")
    print("=" * 80)
    print("1. المنتجات يجب أن تكون في مستودع واحد فقط (إلا في حالة النقل المؤقت)")
    print("2. استخدم معاملات النقل (transfer) لنقل المنتجات بين المستودعات")
    print("3. تجنب إنشاء رصيد افتتاحي أو معاملات دخول مباشرة في مستودعات متعددة")
    print("4. راجع نظام توزيع المنتجات على المستودعات")
    print("=" * 80)


if __name__ == "__main__":
    check_duplicate_products()
