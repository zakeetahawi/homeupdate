#!/usr/bin/env python
"""
فحص عميق لمشكلة المنتجات المكررة
"""
import os
import sys
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.db import connection
from inventory.models import Product, StockTransaction, Warehouse
from inventory.smart_upload_logic import find_duplicate_products

print("="*80)
print("🔍 فحص عميق للمنتجات المكررة")
print("="*80)

# 1. الحصول على المنتجات المكررة
duplicates = find_duplicate_products()
print(f"\n📊 عدد المنتجات المكررة: {len(duplicates)}")

if duplicates:
    # 2. فحص أول 3 منتجات مكررة بالتفصيل
    print("\n" + "="*80)
    print("🔬 فحص تفصيلي لأول 3 منتجات:")
    print("="*80)
    
    for i, dup in enumerate(duplicates[:3], 1):
        product = dup["product"]
        print(f"\n{'─'*80}")
        print(f"المنتج #{i}: {product.code} | {product.name}")
        print(f"{'─'*80}")
        print(f"المستودعات: {dup['warehouses']}")
        print(f"الكميات: {dup['quantities']}")
        
        # 3. فحص آخر معاملات لهذا المنتج من قاعدة البيانات
        print(f"\n📋 آخر 10 معاملات لهذا المنتج:")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    st.id,
                    w.name as warehouse,
                    st.transaction_type,
                    st.quantity,
                    st.running_balance,
                    st.transaction_date,
                    st.notes
                FROM inventory_stocktransaction st
                JOIN inventory_warehouse w ON st.warehouse_id = w.id
                WHERE st.product_id = %s
                ORDER BY st.transaction_date DESC, st.id DESC
                LIMIT 10
            """, [product.id])
            
            rows = cursor.fetchall()
            for row in rows:
                tx_id, wh, tx_type, qty, balance, date, notes = row
                print(f"  [{tx_id}] {wh:15} | {tx_type:4} | كمية: {qty:>8.1f} | رصيد: {balance:>8.1f} | {notes or ''}")
        
        # 4. فحص الرصيد الحالي لكل مستودع
        print(f"\n💰 الأرصدة الحالية (آخر running_balance):")
        with connection.cursor() as cursor:
            for wh_name in dup['warehouses']:
                cursor.execute("""
                    SELECT st.running_balance, st.transaction_date
                    FROM inventory_stocktransaction st
                    JOIN inventory_warehouse w ON st.warehouse_id = w.id
                    WHERE st.product_id = %s AND w.name = %s
                    ORDER BY st.transaction_date DESC, st.id DESC
                    LIMIT 1
                """, [product.id, wh_name])
                
                result = cursor.fetchone()
                if result:
                    balance, date = result
                    status = "✅ صفر" if balance == 0 else f"⚠️  {balance}"
                    print(f"  {wh_name:20} | الرصيد: {status:>12} | آخر تاريخ: {date}")

# 5. فحص منطق اكتشاف المكررات
print("\n" + "="*80)
print("🔍 فحص استعلام اكتشاف المكررات:")
print("="*80)

with connection.cursor() as cursor:
    # نفس الاستعلام من find_duplicate_products
    cursor.execute("""
        WITH last_balances AS (
            SELECT DISTINCT ON (product_id, warehouse_id)
                product_id,
                warehouse_id,
                running_balance,
                transaction_date
            FROM inventory_stocktransaction
            ORDER BY product_id, warehouse_id, transaction_date DESC, id DESC
        )
        SELECT 
            p.code,
            p.name,
            COUNT(DISTINCT lb.warehouse_id) as warehouse_count,
            STRING_AGG(DISTINCT w.name, ', ') as warehouses,
            SUM(lb.running_balance) as total_balance
        FROM last_balances lb
        JOIN inventory_product p ON lb.product_id = p.id
        JOIN inventory_warehouse w ON lb.warehouse_id = w.id
        WHERE lb.running_balance > 0
        GROUP BY p.id, p.code, p.name
        HAVING COUNT(DISTINCT lb.warehouse_id) > 1
        ORDER BY warehouse_count DESC
        LIMIT 5
    """)
    
    print("\nأول 5 منتجات مكررة حسب SQL مباشر:")
    for row in cursor.fetchall():
        code, name, wh_count, warehouses, total = row
        print(f"  {code:15} | {name[:30]:30} | {wh_count} مستودعات | مجموع: {total}")

print("\n" + "="*80)
print("✅ انتهى الفحص")
print("="*80)
