#!/usr/bin/env python
"""
إصلاح سريع للرصيد الوهمي - حذف معاملات السحب الخاطئة من مستودع الإكسسوار
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.models import Product, StockTransaction, Warehouse
from django.db.models import Count
from django.db import transaction as db_transaction

def fix_phantom_stock():
    """حذف معاملات السحب الوهمية من المستودعات"""
    
    print("="*80)
    print("🔧 إصلاح الرصيد الوهمي في المستودعات")
    print("="*80)
    
    # البحث عن المنتجات في مستودعات متعددة
    products_multi = StockTransaction.objects.values('product').annotate(
        wh_count=Count('warehouse', distinct=True)
    ).filter(wh_count__gt=1)
    
    print(f"\n🔍 فحص {len(products_multi)} منتج...")
    
    to_delete = []
    
    for item in products_multi:
        try:
            product = Product.objects.get(id=item['product'])
            
            # فحص كل مستودع
            warehouses = StockTransaction.objects.filter(
                product=product
            ).values('warehouse').distinct()
            
            for wh_data in warehouses:
                warehouse = Warehouse.objects.get(id=wh_data['warehouse'])
                
                # أول معاملة
                first_trans = StockTransaction.objects.filter(
                    product=product,
                    warehouse=warehouse
                ).order_by('transaction_date').first()
                
                # إذا كانت أول معاملة سحب = وهمية
                if first_trans and first_trans.transaction_type == 'out':
                    # جميع معاملات هذا المنتج في هذا المستودع وهمية
                    phantom_trans = StockTransaction.objects.filter(
                        product=product,
                        warehouse=warehouse
                    )
                    
                    to_delete.append({
                        'product': product,
                        'warehouse': warehouse,
                        'transactions': phantom_trans,
                        'count': phantom_trans.count()
                    })
        except:
            continue
    
    if not to_delete:
        print("\n✅ لا توجد معاملات وهمية للحذف")
        return
    
    print(f"\n⚠️ وجد {len(to_delete)} حالة رصيد وهمي")
    print("\n📋 التفاصيل:")
    print("-"*80)
    
    total_transactions = 0
    for item in to_delete:
        print(f"📦 {item['product'].name} ({item['product'].code})")
        print(f"   🏪 {item['warehouse'].name}")
        print(f"   🗑️ سيتم حذف {item['count']} معاملة")
        total_transactions += item['count']
        print("-"*80)
    
    print(f"\n📊 إجمالي المعاملات التي ستُحذف: {total_transactions}")
    print("\n" + "="*80)
    
    # طلب التأكيد
    response = input("⚠️ هل تريد حذف هذه المعاملات الوهمية؟ (yes/no): ")
    
    if response.lower() not in ['yes', 'y', 'نعم']:
        print("\n❌ تم إلغاء العملية")
        return
    
    # الحذف
    print("\n🔄 جاري الحذف...")
    
    deleted_count = 0
    with db_transaction.atomic():
        for item in to_delete:
            count = item['transactions'].count()
            item['transactions'].delete()
            deleted_count += count
            print(f"✅ حذف {count} معاملة من {item['warehouse'].name} للمنتج {item['product'].name}")
    
    print("\n" + "="*80)
    print(f"✅ تم حذف {deleted_count} معاملة وهمية بنجاح!")
    print("="*80)
    
    # التحقق بعد الإصلاح
    print("\n🔍 التحقق من النتيجة...")
    
    remaining = []
    for item in to_delete:
        still_exists = StockTransaction.objects.filter(
            product=item['product'],
            warehouse=item['warehouse']
        ).exists()
        
        if still_exists:
            remaining.append(item['product'].name)
    
    if remaining:
        print(f"\n⚠️ تحذير: {len(remaining)} منتج لا يزال لديه معاملات")
    else:
        print("\n✅ تم إصلاح جميع الحالات بنجاح!")
    
    print("\n💡 يُنصح بإعادة حساب الرصيد في جميع المستودعات")
    print("="*80)

if __name__ == '__main__':
    fix_phantom_stock()
