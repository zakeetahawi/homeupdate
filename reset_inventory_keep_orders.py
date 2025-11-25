#!/usr/bin/env python
"""
سكريبت إعادة تهيئة المخزون - حذف كل حركات المخزون والتكرارات
مع الحفاظ على الطلبات وأوامر التقطيع

⚠️ تحذير: هذا السكريبت يحذف:
- كل معاملات المخزون (StockTransaction)
- كل تحويلات المخزون (StockTransfer)
- المنتجات المكررة

✅ يحافظ على:
- الطلبات (Orders) وعناصرها (OrderItems)
- أوامر التقطيع (CuttingOrder) وعناصرها (CuttingOrderItem)
- المنتجات الأساسية (Products) - لكن بدون مخزون

الاستخدام:
    python reset_inventory_keep_orders.py
    python reset_inventory_keep_orders.py --confirm
"""

import os
import sys
import django
from decimal import Decimal

# إعداد Django
sys.path.insert(0, '/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from inventory.models import Product, StockTransaction, Warehouse, StockTransfer
from orders.models import Order, OrderItem
from cutting.models import CuttingOrder, CuttingOrderItem

User = get_user_model()


def print_header(text):
    """طباعة عنوان منسق"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_info(text, emoji="ℹ️"):
    """طباعة معلومات"""
    print(f"{emoji}  {text}")


def print_success(text):
    """طباعة نجاح"""
    print(f"✅ {text}")


def print_warning(text):
    """طباعة تحذير"""
    print(f"⚠️  {text}")


def print_error(text):
    """طباعة خطأ"""
    print(f"❌ {text}")


def get_inventory_statistics():
    """الحصول على إحصائيات المخزون الحالية"""
    stats = {
        'products': Product.objects.count(),
        'warehouses': Warehouse.objects.count(),
        'stock_transactions': StockTransaction.objects.count(),
        'stock_transfers': StockTransfer.objects.count(),
        'orders': Order.objects.count(),
        'order_items': OrderItem.objects.count(),
        'cutting_orders': CuttingOrder.objects.count(),
        'cutting_order_items': CuttingOrderItem.objects.count(),
    }
    
    # حساب المنتجات المكررة
    duplicates = find_duplicate_products()
    stats['duplicate_products'] = len(duplicates)
    
    # حساب المنتجات التي لها مخزون
    products_with_stock = StockTransaction.objects.values('product').distinct().count()
    stats['products_with_stock'] = products_with_stock
    
    return stats, duplicates


def find_duplicate_products():
    """البحث عن المنتجات المكررة في عدة مستودعات"""
    from django.db.models import Sum, Count
    
    duplicates = []
    
    for product in Product.objects.all():
        warehouses_with_stock = StockTransaction.objects.filter(
            product=product
        ).values('warehouse__name', 'warehouse__id').annotate(
            total=Sum('quantity')
        ).filter(total__gt=0)
        
        if len(warehouses_with_stock) > 1:
            duplicates.append({
                'product': product,
                'code': product.code,
                'name': product.name,
                'warehouses_count': len(warehouses_with_stock),
                'warehouses': list(warehouses_with_stock)
            })
    
    return duplicates


def display_statistics(stats, duplicates):
    """عرض الإحصائيات"""
    print_header("📊 الإحصائيات الحالية")
    
    print_info(f"المنتجات: {stats['products']:,}")
    print_info(f"المنتجات التي لها مخزون: {stats['products_with_stock']:,}")
    print_info(f"المستودعات: {stats['warehouses']:,}")
    print_info(f"معاملات المخزون: {stats['stock_transactions']:,}")
    print_info(f"تحويلات المخزون: {stats['stock_transfers']:,}")
    
    print("\n" + "-"*70)
    print_info(f"الطلبات: {stats['orders']:,}", "📦")
    print_info(f"عناصر الطلبات: {stats['order_items']:,}", "📦")
    print_info(f"أوامر التقطيع: {stats['cutting_orders']:,}", "✂️")
    print_info(f"عناصر أوامر التقطيع: {stats['cutting_order_items']:,}", "✂️")
    
    if stats['duplicate_products'] > 0:
        print("\n" + "-"*70)
        print_warning(f"المنتجات المكررة: {stats['duplicate_products']}")
        print_info("عرض أول 10 منتجات مكررة:")
        for i, dup in enumerate(duplicates[:10], 1):
            print(f"\n  {i}. {dup['name']} ({dup['code']})")
            print(f"     موجود في {dup['warehouses_count']} مستودعات:")
            for wh in dup['warehouses']:
                print(f"       - {wh['warehouse__name']}: {wh['total']} وحدة")


def reset_inventory(dry_run=True):
    """
    إعادة تهيئة المخزون
    
    Args:
        dry_run: إذا True، سيعرض فقط ما سيحذف بدون حذف فعلي
    """
    
    if dry_run:
        print_header("🔍 وضع الفحص (Dry Run)")
        print_warning("لن يتم حذف أي بيانات فعلياً")
        print_info("لتنفيذ الحذف الفعلي، استخدم: --confirm")
    else:
        print_header("⚠️  وضع التنفيذ الفعلي")
        print_warning("سيتم حذف البيانات بشكل نهائي!")
    
    # الحصول على الإحصائيات
    stats, duplicates = get_inventory_statistics()
    display_statistics(stats, duplicates)
    
    # التأكيد
    if not dry_run:
        print("\n" + "="*70)
        print_warning("هل أنت متأكد من المتابعة؟")
        print_error("سيتم حذف:")
        print(f"  - {stats['stock_transactions']:,} معاملة مخزون")
        print(f"  - {stats['stock_transfers']:,} تحويل مخزون")
        print(f"  - إعادة ضبط {stats['products_with_stock']:,} منتج")
        
        print("\n" + "="*70)
        print_success("سيتم الحفاظ على:")
        print(f"  - {stats['orders']:,} طلب")
        print(f"  - {stats['order_items']:,} عنصر طلب")
        print(f"  - {stats['cutting_orders']:,} أمر تقطيع")
        print(f"  - {stats['cutting_order_items']:,} عنصر تقطيع")
        
        print("\n" + "="*70)
        confirm = input("اكتب 'نعم' أو 'yes' للتأكيد: ").strip().lower()
        
        if confirm not in ['نعم', 'yes']:
            print_error("تم الإلغاء!")
            return False
    
    # تنفيذ الحذف
    print_header("🔄 بدء عملية إعادة التهيئة")
    
    try:
        with transaction.atomic():
            # 1. حذف تحويلات المخزون
            print_info("حذف تحويلات المخزون...")
            transfers_count = StockTransfer.objects.count()
            if not dry_run:
                StockTransfer.objects.all().delete()
            print_success(f"تم حذف {transfers_count:,} تحويل مخزون")
            
            # 2. حذف معاملات المخزون
            print_info("حذف معاملات المخزون...")
            transactions_count = StockTransaction.objects.count()
            if not dry_run:
                StockTransaction.objects.all().delete()
            print_success(f"تم حذف {transactions_count:,} معاملة مخزون")
            
            # 3. التحقق من المنتجات
            print_info("التحقق من المنتجات...")
            products_count = Product.objects.count()
            print_success(f"تم الحفاظ على {products_count:,} منتج (بدون مخزون)")
            
            # 4. التحقق من الطلبات
            print_info("التحقق من الطلبات...")
            orders_count = Order.objects.count()
            order_items_count = OrderItem.objects.count()
            print_success(f"تم الحفاظ على {orders_count:,} طلب و {order_items_count:,} عنصر")
            
            # 5. التحقق من أوامر التقطيع
            print_info("التحقق من أوامر التقطيع...")
            cutting_orders_count = CuttingOrder.objects.count()
            cutting_items_count = CuttingOrderItem.objects.count()
            print_success(f"تم الحفاظ على {cutting_orders_count:,} أمر تقطيع و {cutting_items_count:,} عنصر")
            
            if dry_run:
                print("\n" + "="*70)
                print_warning("وضع الفحص - لم يتم حذف أي بيانات")
                print_info("لتنفيذ الحذف الفعلي، استخدم: --confirm")
                # إلغاء المعاملة
                transaction.set_rollback(True)
            else:
                print_header("✅ اكتملت عملية إعادة التهيئة بنجاح!")
                
                print("\n📋 الملخص:")
                print(f"  ✅ حُذف {transfers_count:,} تحويل مخزون")
                print(f"  ✅ حُذف {transactions_count:,} معاملة مخزون")
                print(f"  ✅ حُفظ {products_count:,} منتج")
                print(f"  ✅ حُفظ {orders_count:,} طلب")
                print(f"  ✅ حُفظ {cutting_orders_count:,} أمر تقطيع")
                
                print("\n💡 الخطوات التالية:")
                print("  1. قم برفع ملف Excel جديد للمخزون")
                print("  2. استخدم وضع 'smart_update' أو 'merge_warehouses'")
                print("  3. سيتم إنشاء المخزون من الصفر بدون تكرارات")
        
        return True
        
    except Exception as e:
        print_error(f"حدث خطأ: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """الدالة الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='إعادة تهيئة المخزون - حذف التكرارات والحركات',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة:
  # فحص فقط (لا يحذف)
  python reset_inventory_keep_orders.py
  
  # تنفيذ الحذف الفعلي
  python reset_inventory_keep_orders.py --confirm
  
  # عرض المساعدة
  python reset_inventory_keep_orders.py --help
        """
    )
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='تأكيد الحذف الفعلي (بدون هذا الخيار سيكون وضع فحص فقط)'
    )
    
    args = parser.parse_args()
    
    # تشغيل السكريبت
    success = reset_inventory(dry_run=not args.confirm)
    
    if success and not args.confirm:
        print("\n" + "="*70)
        print_info("لتنفيذ الحذف الفعلي، قم بتشغيل:")
        print("  python reset_inventory_keep_orders.py --confirm")
    
    return 0 if success else 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n")
        print_error("تم الإيقاف بواسطة المستخدم")
        sys.exit(1)
    except Exception as e:
        print_error(f"خطأ غير متوقع: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
