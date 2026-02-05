#!/usr/bin/env python
"""
اختبار دمج منتج واحد
"""
import os
import sys
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.db import connection, transaction
from django.db.models import signals
from inventory.models import Product, StockTransaction, Warehouse
from inventory.smart_upload_logic import find_duplicate_products
from inventory import signals as inventory_signals

# الحصول على أول منتج مكرر
duplicates = find_duplicate_products()
if not duplicates:
    print("❌ لا توجد منتجات مكررة!")
    sys.exit(1)

dup = duplicates[0]
product = dup["product"]
target_warehouse_id = dup.get("suggested_warehouse_id") or dup["warehouse_ids"][0]

print(f"🧪 اختبار دمج المنتج: {product.code} | {product.name}")
print(f"المستودعات قبل الدمج: {dup['warehouses']}")
print(f"الكميات: {dup['quantities']}")
print(f"المستودع المستهدف ID: {target_warehouse_id}")

# تعطيل signals
print("\n⏸️  تعطيل signals...")
signals.post_save.disconnect(inventory_signals.stock_manager_handler, sender=StockTransaction)

try:
    with transaction.atomic():
        with connection.cursor() as cursor:
            for warehouse_id in dup.get("warehouse_ids", []):
                if warehouse_id != target_warehouse_id:
                    # الحصول على الرصيد الحالي
                    cursor.execute("""
                        SELECT running_balance
                        FROM inventory_stocktransaction
                        WHERE product_id = %s AND warehouse_id = %s
                        ORDER BY transaction_date DESC, id DESC
                        LIMIT 1
                    """, [product.id, warehouse_id])
                    
                    result = cursor.fetchone()
                    current_balance = Decimal(str(result[0])) if result and result[0] else Decimal('0')
                    
                    print(f"\n📦 معالجة المستودع ID={warehouse_id}, الرصيد الحالي: {current_balance}")
                    
                    if current_balance != 0:
                        # إفراغ المستودع القديم
                        cursor.execute("""
                            INSERT INTO inventory_stocktransaction 
                            (product_id, warehouse_id, transaction_type, reason, 
                             quantity, reference, notes, created_by_id, 
                             running_balance, transaction_date)
                            VALUES (%s, %s, 'OUT', 'transfer', %s, 
                                    'دمج تجريبي', 'إفراغ لدمج المكررات - اختبار', 1, 0, NOW())
                        """, [product.id, warehouse_id, float(-current_balance)])
                        print(f"  ✅ أضيفت معاملة OUT بكمية {-current_balance}, running_balance=0")
                        
                        # الحصول على رصيد المستودع المستهدف
                        cursor.execute("""
                            SELECT running_balance
                            FROM inventory_stocktransaction
                            WHERE product_id = %s AND warehouse_id = %s
                            ORDER BY transaction_date DESC, id DESC
                            LIMIT 1
                        """, [product.id, target_warehouse_id])
                        
                        result_target = cursor.fetchone()
                        target_current = Decimal(str(result_target[0])) if result_target and result_target[0] else Decimal('0')
                        new_balance = target_current + current_balance
                        
                        # إضافة للمستودع المستهدف
                        cursor.execute("""
                            INSERT INTO inventory_stocktransaction 
                            (product_id, warehouse_id, transaction_type, reason, 
                             quantity, reference, notes, created_by_id, 
                             running_balance, transaction_date)
                            VALUES (%s, %s, 'IN', 'transfer', %s, 
                                    'دمج تجريبي', 'استقبال من دمج المكررات - اختبار', 1, %s, NOW())
                        """, [product.id, target_warehouse_id, float(current_balance), float(new_balance)])
                        print(f"  ✅ أضيفت معاملة IN للمستودع المستهدف، running_balance={new_balance}")
    
    print("\n✅ تم حفظ المعاملات بنجاح!")
    
finally:
    # إعادة تفعيل signals
    print("\n▶️  إعادة تفعيل signals...")
    signals.post_save.connect(inventory_signals.stock_manager_handler, sender=StockTransaction)

# فحص النتائج
print("\n" + "="*80)
print("📊 فحص النتائج:")
print("="*80)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT 
            w.name,
            st.running_balance,
            st.transaction_date,
            st.notes
        FROM inventory_stocktransaction st
        JOIN inventory_warehouse w ON st.warehouse_id = w.id
        WHERE st.product_id = %s
        ORDER BY st.transaction_date DESC, st.id DESC
        LIMIT 10
    """, [product.id])
    
    for wh_name, balance, date, notes in cursor.fetchall():
        print(f"{wh_name:20} | رصيد: {balance:>10.2f} | {notes or ''}")

# فحص المنتجات المكررة بعد الدمج
duplicates_after = find_duplicate_products()
still_duplicate = any(d["product"].id == product.id for d in duplicates_after)

print(f"\n{'❌' if still_duplicate else '✅'} المنتج {'لا يزال' if still_duplicate else 'اختفى من'} قائمة المكررات")
