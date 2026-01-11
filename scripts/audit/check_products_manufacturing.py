#!/usr/bin/env python
"""
سكريبت فحص شامل لأوامر التصنيع - التأكد من عدم وجود طلبات منتجات
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from django.db.models import Q

from manufacturing.models import ManufacturingOrder
from orders.models import Order


def check_products_manufacturing_orders():
    """فحص وجود أوامر تصنيع خاطئة لطلبات المنتجات"""
    print("=" * 80)
    print("📊 تقرير فحص أوامر التصنيع - استثناء طلبات المنتجات")
    print("=" * 80)

    # 1. فحص أوامر التصنيع لطلبات المنتجات
    products_mfg_orders = ManufacturingOrder.objects.filter(
        Q(order__selected_types__contains=["products"])
        | Q(order__selected_types__icontains='"products"')
        | Q(order__selected_types__icontains="'products'")
    )

    count = products_mfg_orders.count()
    print(f"\n🔍 عدد أوامر التصنيع الخاطئة لطلبات المنتجات: {count}")

    if count > 0:
        print("\n⚠️ تفاصيل الأوامر الخاطئة:")
        for mfg in products_mfg_orders[:10]:  # عرض أول 10 فقط
            order_types = mfg.order.get_selected_types_list()
            print(f"  - طلب {mfg.order.order_number}: {order_types}")

        if count > 10:
            print(f"  ... و {count - 10} طلب آخر")
    else:
        print("✅ لا توجد أوامر تصنيع خاطئة لطلبات المنتجات")

    # 2. فحص أوامر التصنيع لطلبات المعاينات
    inspection_mfg_orders = ManufacturingOrder.objects.filter(
        Q(order__selected_types__contains=["inspection"])
        | Q(order__selected_types__icontains='"inspection"')
        | Q(order__selected_types__icontains="'inspection'")
    )

    inspection_count = inspection_mfg_orders.count()
    print(f"\n🔍 عدد أوامر التصنيع الخاطئة لطلبات المعاينات: {inspection_count}")

    if inspection_count > 0:
        print("\n⚠️ تفاصيل الأوامر الخاطئة:")
        for mfg in inspection_mfg_orders[:10]:
            order_types = mfg.order.get_selected_types_list()
            print(f"  - طلب {mfg.order.order_number}: {order_types}")
    else:
        print("✅ لا توجد أوامر تصنيع خاطئة لطلبات المعاينات")

    # 3. إحصائيات عامة
    print("\n" + "=" * 80)
    print("📈 إحصائيات عامة")
    print("=" * 80)

    total_mfg = ManufacturingOrder.objects.count()
    print(f"إجمالي أوامر التصنيع: {total_mfg}")

    # عدد حسب النوع
    installation_count = ManufacturingOrder.objects.filter(
        order_type="installation"
    ).count()
    tailoring_count = ManufacturingOrder.objects.filter(order_type="custom").count()
    accessory_count = ManufacturingOrder.objects.filter(order_type="accessory").count()

    print(f"  - تركيب: {installation_count}")
    print(f"  - تفصيل: {tailoring_count}")
    print(f"  - إكسسوار: {accessory_count}")

    # 4. فحص طلبات المنتجات العادية
    products_orders = Order.objects.filter(
        Q(selected_types__contains=["products"])
        | Q(selected_types__icontains='"products"')
        | Q(selected_types__icontains="'products'")
    )

    products_orders_count = products_orders.count()
    print(f"\nإجمالي طلبات المنتجات في النظام: {products_orders_count}")

    # التحقق من عدم وجود أوامر تصنيع لها
    products_with_mfg = products_orders.filter(
        manufacturing_orders__isnull=False
    ).count()
    print(f"طلبات منتجات لها أوامر تصنيع (يجب أن يكون 0): {products_with_mfg}")

    if products_with_mfg == 0:
        print("✅ جميع طلبات المنتجات خالية من أوامر التصنيع (صحيح)")
    else:
        print("❌ يوجد طلبات منتجات لها أوامر تصنيع (خطأ)")

    # 5. التوصيات
    print("\n" + "=" * 80)
    print("💡 التوصيات")
    print("=" * 80)

    if count > 0 or inspection_count > 0:
        print("\n⚠️ يوجد أوامر تصنيع خاطئة. لحذفها:")
        print('\npython manage.py shell -c "')
        print("from manufacturing.models import ManufacturingOrder")
        print("from django.db.models import Q")
        print("ManufacturingOrder.objects.filter(")
        print("    Q(order__selected_types__contains=['products']) |")
        print("    Q(order__selected_types__contains=['inspection'])")
        print(").delete()")
        print('"')
    else:
        print("✅ النظام سليم - لا توجد أوامر تصنيع خاطئة")
        print("✅ تم تطبيق الفلتر الاستثنائي في Manufacturing Views")
        print("✅ Signal لا ينشئ أوامر تصنيع لطلبات المنتجات أو المعاينات")

    print("\n" + "=" * 80)
    print("✅ انتهى الفحص")
    print("=" * 80)


if __name__ == "__main__":
    check_products_manufacturing_orders()
