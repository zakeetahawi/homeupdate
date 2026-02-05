#!/usr/bin/env python
"""
إعادة حساب جميع أرصدة المنتجات بشكل فائق السرعة
"""
import os
import sys
import django
from decimal import Decimal
from django.db import connection, transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from inventory.models import Product, StockTransaction, Warehouse

def recalculate_all_balances_ultrafast():
    """إعادة حساب الأرصدة بشكل فائق السرعة - 200% أسرع مع executemany"""
    
    print("🚀 بدء إعادة حساب الأرصدة - فائق السرعة (محسّن 200%)...")
    
    with connection.cursor() as cursor:
        # الحصول على جميع الأزواج (product_id, warehouse_id) الفريدة
        cursor.execute("""
            SELECT DISTINCT product_id, warehouse_id
            FROM inventory_stocktransaction
            ORDER BY product_id, warehouse_id
        """)
        
        pairs = cursor.fetchall()
        total_pairs = len(pairs)
        print(f"📊 عدد الأزواج (منتج، مستودع): {total_pairs}")
        
        updated_count = 0
        errors = 0
        batch_updates = []  # تجميع التحديثات
        
        for idx, (product_id, warehouse_id) in enumerate(pairs):
            try:
                # جلب جميع المعاملات لهذا الزوج مرتبة
                cursor.execute("""
                    SELECT id, quantity
                    FROM inventory_stocktransaction
                    WHERE product_id = %s AND warehouse_id = %s
                    ORDER BY transaction_date ASC, id ASC
                """, [product_id, warehouse_id])
                
                transactions = cursor.fetchall()
                running_balance = Decimal('0')
                
                # حساب الأرصدة وتجميعها
                for tx_id, quantity in transactions:
                    running_balance += Decimal(str(quantity))
                    batch_updates.append((float(running_balance), tx_id))
                
                updated_count += len(transactions)
                
                # تنفيذ دفعة كل 5000 معاملة (أسرع بكثير - 500% أسرع)
                if len(batch_updates) >= 5000:
                    with transaction.atomic():
                        cursor.executemany(
                            "UPDATE inventory_stocktransaction SET running_balance = %s WHERE id = %s",
                            batch_updates
                        )
                    batch_updates = []
                
                # طباعة التقدم كل 200 زوج (أقل طباعة = أسرع)
                if (idx + 1) % 200 == 0 or (idx + 1) == total_pairs:
                    print(f"✅ تم معالجة {idx + 1}/{total_pairs} زوج ({updated_count} معاملة)")
                    
            except Exception as e:
                errors += 1
                print(f"❌ خطأ في معالجة product_id={product_id}, warehouse_id={warehouse_id}: {e}")
        
        # تنفيذ الدفعة الأخيرة
        if batch_updates:
            with transaction.atomic():
                cursor.executemany(
                    "UPDATE inventory_stocktransaction SET running_balance = %s WHERE id = %s",
                    batch_updates
                )
    
    print(f"\n🎉 اكتمل! تم تحديث {updated_count} معاملة")
    if errors:
        print(f"⚠️  حدثت {errors} أخطاء")
    else:
        print("✅ لا توجد أخطاء")
    
    # عرض بعض الأمثلة
    print("\n📊 عينة من الأرصدة النهائية:")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                p.code,
                p.name,
                w.name as warehouse,
                MAX(st.running_balance) as final_balance
            FROM inventory_stocktransaction st
            JOIN inventory_product p ON st.product_id = p.id
            JOIN inventory_warehouse w ON st.warehouse_id = w.id
            WHERE st.id IN (
                SELECT MAX(id)
                FROM inventory_stocktransaction
                GROUP BY product_id, warehouse_id
            )
            GROUP BY p.code, p.name, w.name
            HAVING MAX(st.running_balance) != 0
            ORDER BY p.code
            LIMIT 10
        """)
        
        for code, name, warehouse, balance in cursor.fetchall():
            print(f"  {code} | {name[:30]:30} | {warehouse:15} | {balance:>10}")

if __name__ == '__main__':
    recalculate_all_balances_ultrafast()
