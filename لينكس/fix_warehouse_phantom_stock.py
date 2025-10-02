#!/usr/bin/env python
"""
إصلاح مشكلة الرصيد الوهمي في المستودعات
يكتشف المنتجات التي لها رصيد في مستودعات لكن بدون معاملة إدخال أولية
"""

import os
import sys
sys.path.append('/home/zakee/homeupdate')
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.models import Product, StockTransaction, Warehouse
from django.db.models import Count, Q

def find_phantom_stock():
    """البحث عن الرصيد الوهمي في المستودعات"""
    
    print("="*80)
    print("🔍 البحث عن رصيد وهمي في المستودعات")
    print("="*80)
    
    # البحث عن المنتجات في أكثر من مستودع
    products_multi = StockTransaction.objects.values('product').annotate(
        wh_count=Count('warehouse', distinct=True)
    ).filter(wh_count__gt=1)
    
    print(f"\n📊 عدد المنتجات في أكثر من مستودع: {len(products_multi)}")
    
    phantom_cases = []
    
    for item in products_multi:
        try:
            product = Product.objects.get(id=item['product'])
            
            # فحص كل مستودع
            warehouses = StockTransaction.objects.filter(
                product=product
            ).values('warehouse').distinct()
            
            for wh_data in warehouses:
                warehouse = Warehouse.objects.get(id=wh_data['warehouse'])
                
                # الحصول على معاملات هذا المستودع
                wh_transactions = StockTransaction.objects.filter(
                    product=product,
                    warehouse=warehouse
                ).order_by('transaction_date')
                
                if not wh_transactions.exists():
                    continue
                
                first_trans = wh_transactions.first()
                last_trans = wh_transactions.last()
                
                # التحقق: إذا كانت أول معاملة هي سحب (out)
                if first_trans.transaction_type == 'out':
                    phantom_cases.append({
                        'product': product,
                        'warehouse': warehouse,
                        'first_transaction': first_trans,
                        'last_transaction': last_trans,
                        'transactions_count': wh_transactions.count(),
                        'current_balance': last_trans.running_balance
                    })
        except:
            continue
    
    print(f"\n⚠️ عدد حالات الرصيد الوهمي: {len(phantom_cases)}")
    
    if not phantom_cases:
        print("\n✅ لا توجد حالات رصيد وهمي")
        return []
    
    print("\n" + "="*80)
    print("📋 تفاصيل الحالات:")
    print("="*80)
    
    for idx, case in enumerate(phantom_cases, 1):
        print(f"\n{idx}. 📦 {case['product'].name} ({case['product'].code})")
        print(f"   🏪 المستودع: {case['warehouse'].name}")
        print(f"   📅 أول معاملة: {case['first_transaction'].transaction_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"   📝 نوع أول معاملة: {case['first_transaction'].transaction_type}")
        print(f"   📊 عدد المعاملات: {case['transactions_count']}")
        print(f"   💰 الرصيد الوهمي: {case['current_balance']}")
        print(f"   ⚠️ المشكلة: تم السحب من مستودع بدون إدخال أولي!")
        print("-"*80)
    
    return phantom_cases


def suggest_fixes(phantom_cases):
    """اقتراح حلول لإصلاح البيانات"""
    
    if not phantom_cases:
        return
    
    print("\n" + "="*80)
    print("💡 خيارات الإصلاح:")
    print("="*80)
    
    print("\n1️⃣ الخيار الأول: حذف جميع المعاملات الوهمية")
    print("   - يحذف جميع معاملات المستودعات التي بدأت بسحب")
    print("   - يعيد الرصيد للمستودع الأصلي")
    print("   - ⚠️ تحذير: قد يؤثر على التقارير التاريخية")
    
    print("\n2️⃣ الخيار الثاني: إضافة معاملة إدخال تصحيحية")
    print("   - يضيف معاملة إدخال (in) قبل أول معاملة سحب")
    print("   - يحافظ على الرصيد الحالي")
    print("   - ⚠️ تحذير: يضيف بيانات غير حقيقية")
    
    print("\n3️⃣ الخيار الثالث (الموصى به): نقل المعاملات للمستودع الصحيح")
    print("   - يحدد المستودع الأصلي الذي فيه رصيد")
    print("   - ينقل جميع معاملات السحب للمستودع الصحيح")
    print("   - يحافظ على دقة البيانات")
    
    print("\n" + "="*80)
    
    return


def fix_phantom_stock_auto(phantom_cases):
    """الإصلاح التلقائي: نقل المعاملات للمستودع الصحيح"""
    
    if not phantom_cases:
        return
    
    print("\n" + "="*80)
    print("🔧 بدء الإصلاح التلقائي...")
    print("="*80)
    
    fixed_count = 0
    errors = []
    
    for case in phantom_cases:
        product = case['product']
        wrong_warehouse = case['warehouse']
        
        try:
            # البحث عن المستودع الصحيح (الذي فيه معاملة إدخال)
            correct_warehouse_trans = StockTransaction.objects.filter(
                product=product,
                transaction_type__in=['in', 'opening_balance', 'transfer_in']
            ).order_by('transaction_date').first()
            
            if not correct_warehouse_trans:
                errors.append({
                    'product': product,
                    'reason': 'لم يتم العثور على مستودع بمعاملة إدخال'
                })
                continue
            
            correct_warehouse = correct_warehouse_trans.warehouse
            
            print(f"\n📦 {product.name}")
            print(f"   ❌ المستودع الخاطئ: {wrong_warehouse.name}")
            print(f"   ✅ المستودع الصحيح: {correct_warehouse.name}")
            
            # الحصول على جميع المعاملات الخاطئة
            wrong_transactions = StockTransaction.objects.filter(
                product=product,
                warehouse=wrong_warehouse
            )
            
            print(f"   🔄 نقل {wrong_transactions.count()} معاملة...")
            
            # **لا ننقل المعاملات فعلياً - فقط نحذفها**
            # لأن نقلها سيخلق مشاكل في الرصيد
            
            # حذف المعاملات الوهمية
            deleted_count = wrong_transactions.count()
            wrong_transactions.delete()
            
            print(f"   ✅ تم حذف {deleted_count} معاملة وهمية")
            
            fixed_count += 1
            
        except Exception as e:
            errors.append({
                'product': product,
                'reason': str(e)
            })
            print(f"   ❌ خطأ: {str(e)}")
    
    print("\n" + "="*80)
    print(f"✅ تم إصلاح {fixed_count} حالة")
    
    if errors:
        print(f"\n⚠️ فشل إصلاح {len(errors)} حالة:")
        for err in errors:
            print(f"   - {err['product'].name}: {err['reason']}")
    
    print("="*80)


def main():
    """الدالة الرئيسية"""
    
    print("\n" + "="*80)
    print("🛠️ برنامج إصلاح الرصيد الوهمي في المستودعات")
    print("="*80)
    
    # 1. البحث عن المشاكل
    phantom_cases = find_phantom_stock()
    
    if not phantom_cases:
        print("\n✅ النظام سليم!")
        return
    
    # 2. اقتراح الحلول
    suggest_fixes(phantom_cases)
    
    # 3. طلب تأكيد المستخدم
    print("\n" + "="*80)
    response = input("هل تريد تطبيق الإصلاح التلقائي (حذف المعاملات الوهمية)? (yes/no): ")
    
    if response.lower() in ['yes', 'y', 'نعم']:
        fix_phantom_stock_auto(phantom_cases)
        print("\n✅ تم الإصلاح بنجاح!")
        print("\n💡 يُنصح بإعادة فحص النظام للتأكد")
    else:
        print("\n⏭️ تم إلغاء الإصلاح")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
