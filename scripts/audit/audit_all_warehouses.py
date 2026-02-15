#!/usr/bin/env python
"""
فحص شامل لجميع المستودعات للبحث عن رصيد وهمي
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from django.db.models import Count

from inventory.models import Product, StockTransaction, Warehouse


def comprehensive_warehouse_audit():
    """فحص شامل لجميع المستودعات"""

    print("=" * 80)
    print("🔍 فحص شامل لجميع المستودعات")
    print("=" * 80)

    # 1. إحصائيات عامة
    all_warehouses = Warehouse.objects.filter(is_active=True)
    print(f"\n📊 عدد المستودعات النشطة: {all_warehouses.count()}")

    for wh in all_warehouses:
        products_count = (
            StockTransaction.objects.filter(warehouse=wh)
            .values("product")
            .distinct()
            .count()
        )

        trans_count = StockTransaction.objects.filter(warehouse=wh).count()

        print(f"   🏪 {wh.name}: {products_count} منتج، {trans_count} معاملة")

    # 2. المنتجات في مستودعات متعددة
    print("\n" + "=" * 80)
    print("🔍 المنتجات في مستودعات متعددة:")
    print("=" * 80)

    products_multi = (
        StockTransaction.objects.values("product")
        .annotate(wh_count=Count("warehouse", distinct=True))
        .filter(wh_count__gt=1)
        .order_by("-wh_count")
    )

    print(f"\nإجمالي: {len(products_multi)} منتج في أكثر من مستودع")

    # توزيع حسب عدد المستودعات
    in_2_wh = len([p for p in products_multi if p["wh_count"] == 2])
    in_3_wh = len([p for p in products_multi if p["wh_count"] == 3])
    in_4_plus = len([p for p in products_multi if p["wh_count"] >= 4])

    print(f"   - في مستودعين: {in_2_wh}")
    print(f"   - في 3 مستودعات: {in_3_wh}")
    print(f"   - في 4+ مستودعات: {in_4_plus}")

    # 3. فحص الرصيد الوهمي
    print("\n" + "=" * 80)
    print("⚠️ فحص الرصيد الوهمي:")
    print("=" * 80)

    phantom_cases = []

    for item in products_multi:
        try:
            product = Product.objects.get(id=item["product"])

            # فحص كل مستودع
            warehouses = (
                StockTransaction.objects.filter(product=product)
                .values("warehouse")
                .distinct()
            )

            for wh_data in warehouses:
                warehouse = Warehouse.objects.get(id=wh_data["warehouse"])

                # أول معاملة في هذا المستودع
                first_trans = (
                    StockTransaction.objects.filter(
                        product=product, warehouse=warehouse
                    )
                    .order_by("transaction_date")
                    .first()
                )

                if not first_trans:
                    continue

                # التحقق من نوع أول معاملة
                if first_trans.transaction_type == "out":
                    last_trans = (
                        StockTransaction.objects.filter(
                            product=product, warehouse=warehouse
                        )
                        .order_by("-transaction_date")
                        .first()
                    )

                    phantom_cases.append(
                        {
                            "product": product,
                            "warehouse": warehouse,
                            "first_date": first_trans.transaction_date,
                            "first_type": first_trans.transaction_type,
                            "balance": last_trans.running_balance if last_trans else 0,
                            "trans_count": StockTransaction.objects.filter(
                                product=product, warehouse=warehouse
                            ).count(),
                        }
                    )
        except Exception as e:
            continue

    if phantom_cases:
        print(f"\n⚠️ وجد {len(phantom_cases)} حالة رصيد وهمي:")
        print("-" * 80)

        for idx, case in enumerate(phantom_cases[:20], 1):
            print(f"\n{idx}. 📦 {case['product'].name} ({case['product'].code})")
            print(f"   🏪 المستودع: {case['warehouse'].name}")
            print(f"   📅 أول معاملة: {case['first_date'].strftime('%Y-%m-%d')}")
            print(f"   📝 النوع: {case['first_type']}")
            print(f"   📊 عدد المعاملات: {case['trans_count']}")
            print(f"   💰 الرصيد: {case['balance']}")

        if len(phantom_cases) > 20:
            print(f"\n... و {len(phantom_cases) - 20} حالة أخرى")
    else:
        print("\n✅ لا يوجد رصيد وهمي")

    # 4. معاملات النقل
    print("\n" + "=" * 80)
    print("🔄 معاملات النقل بين المستودعات:")
    print("=" * 80)

    transfer_in = StockTransaction.objects.filter(
        transaction_type="transfer_in"
    ).count()

    transfer_out = StockTransaction.objects.filter(
        transaction_type="transfer_out"
    ).count()

    print(f"   📥 معاملات نقل داخل: {transfer_in}")
    print(f"   📤 معاملات نقل خارج: {transfer_out}")

    if transfer_in != transfer_out:
        print(f"   ⚠️ تحذير: عدم تطابق ({transfer_in} ≠ {transfer_out})")
    else:
        print(f"   ✅ متطابق")

    # 5. منتجات لها رصيد صفر في مستودعات
    print("\n" + "=" * 80)
    print("📊 منتجات لها رصيد صفر في مستودعات:")
    print("=" * 80)

    zero_balance_count = 0

    for wh in all_warehouses:
        # البحث عن منتجات لها معاملات لكن رصيدها صفر
        products_in_wh = (
            StockTransaction.objects.filter(warehouse=wh).values("product").distinct()
        )

        for p_data in products_in_wh:
            try:
                product = Product.objects.get(id=p_data["product"])

                last_trans = (
                    StockTransaction.objects.filter(product=product, warehouse=wh)
                    .order_by("-transaction_date")
                    .first()
                )

                if last_trans and last_trans.running_balance == 0:
                    zero_balance_count += 1
            except Exception:
                continue

    print(f"   عدد المنتجات برصيد صفر: {zero_balance_count}")

    # الخلاصة
    print("\n" + "=" * 80)
    print("📋 الخلاصة:")
    print("=" * 80)

    if phantom_cases:
        print(f"   ⚠️ يوجد {len(phantom_cases)} حالة رصيد وهمي تحتاج إصلاح")
    else:
        print(f"   ✅ لا يوجد رصيد وهمي")

    if len(products_multi) > 0:
        print(f"   ⚠️ يوجد {len(products_multi)} منتج في مستودعات متعددة")
        print(f"      (قد يكون طبيعياً إذا تم نقلها)")

    print("=" * 80)

    return phantom_cases


if __name__ == "__main__":
    phantom_cases = comprehensive_warehouse_audit()

    if phantom_cases:
        print("\n💡 لإصلاح المشكلة، قم بتشغيل:")
        print("   python fix_phantom_stock_simple.py")
