#!/usr/bin/env python
"""
تحسين الصفحات البطيئة
- صفحة تعديل أوامر التصنيع
- صفحة سجلات نشاط المستخدمين
"""

import os
import sys
import django

# إضافة المسار الصحيح
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from django.db import connection
from user_activity.models import UserActivityLog
from datetime import datetime, timedelta
from django.utils import timezone

print("=" * 80)
print("🚀 تحسين الصفحات البطيئة")
print("=" * 80)

# ====================================
# 1. حذف سجلات النشاط القديمة
# ====================================
print("\n📊 سجلات نشاط المستخدمين")
print("-" * 50)

total_logs = UserActivityLog.objects.count()
print(f"  إجمالي السجلات: {total_logs:,}")

# حذف السجلات الأقدم من 30 يوم
cutoff_date = timezone.now() - timedelta(days=30)
old_logs = UserActivityLog.objects.filter(timestamp__lt=cutoff_date)
old_count = old_logs.count()

if old_count > 0:
    print(f"  🗑️ حذف {old_count:,} سجل قديم (+30 يوم)...")
    deleted = old_logs.delete()
    print(f"  ✅ تم حذف {deleted[0]:,} سجل")
else:
    print("  ✅ لا توجد سجلات قديمة للحذف")

remaining = UserActivityLog.objects.count()
print(f"  📈 السجلات المتبقية: {remaining:,}")

# ====================================
# 2. إضافة Indexes للأداء
# ====================================
print("\n🔍 فحص Indexes")
print("-" * 50)

with connection.cursor() as cursor:
    # فحص indexes على جدول UserActivityLog
    cursor.execute("""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'user_activity_useractivitylog'
        ORDER BY indexname;
    """)
    
    existing_indexes = cursor.fetchall()
    print(f"  Indexes موجودة: {len(existing_indexes)}")
    
    # إضافة indexes مفقودة
    indexes_to_create = [
        ("idx_useractivity_timestamp", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_useractivity_timestamp ON user_activity_useractivitylog(timestamp DESC);"),
        ("idx_useractivity_user_timestamp", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_useractivity_user_timestamp ON user_activity_useractivitylog(user_id, timestamp DESC);"),
        ("idx_useractivity_action_type", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_useractivity_action_type ON user_activity_useractivitylog(action_type);"),
    ]
    
    for idx_name, idx_sql in indexes_to_create:
        # فحص إذا كان index موجود
        idx_exists = any(idx_name in str(idx) for idx in existing_indexes)
        if not idx_exists:
            print(f"  ➕ إنشاء: {idx_name}")
            try:
                cursor.execute(idx_sql)
                print(f"  ✅ تم إنشاء {idx_name}")
            except Exception as e:
                print(f"  ⚠️ خطأ: {e}")
        else:
            print(f"  ✅ موجود: {idx_name}")

    # فحص indexes على جدول ManufacturingOrder
    cursor.execute("""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'manufacturing_manufacturingorder'
        ORDER BY indexname;
    """)
    
    mfg_indexes = cursor.fetchall()
    print(f"\n  Manufacturing Indexes: {len(mfg_indexes)}")
    
    mfg_indexes_to_create = [
        ("idx_mfg_order_id", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mfg_order_id ON manufacturing_manufacturingorder(order_id);"),
        ("idx_mfg_status", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mfg_status ON manufacturing_manufacturingorder(status);"),
        ("idx_mfg_production_line", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mfg_production_line ON manufacturing_manufacturingorder(production_line_id);"),
    ]
    
    for idx_name, idx_sql in mfg_indexes_to_create:
        idx_exists = any(idx_name in str(idx) for idx in mfg_indexes)
        if not idx_exists:
            print(f"  ➕ إنشاء: {idx_name}")
            try:
                cursor.execute(idx_sql)
                print(f"  ✅ تم إنشاء {idx_name}")
            except Exception as e:
                print(f"  ⚠️ خطأ: {e}")
        else:
            print(f"  ✅ موجود: {idx_name}")

# ====================================
# 3. VACUUM ANALYZE
# ====================================
print("\n🔧 تحسين الجداول")
print("-" * 50)

with connection.cursor() as cursor:
    tables = [
        'user_activity_useractivitylog',
        'manufacturing_manufacturingorder',
        'manufacturing_manufacturingorderitem'
    ]
    
    for table in tables:
        print(f"  🔄 VACUUM ANALYZE {table}...")
        try:
            cursor.execute(f"VACUUM ANALYZE {table};")
            print(f"  ✅ تم")
        except Exception as e:
            print(f"  ⚠️ خطأ: {e}")

print("\n" + "=" * 80)
print("✅ اكتمل التحسين!")
print("=" * 80)
print("\n📌 التوصيات:")
print("  1. تشغيل هذا السكربت يومياً (cron job)")
print("  2. تقليل عدد ManufacturingOrderItemInline المعروضة")
print("  3. استخدام pagination في الـ inline")
print("  4. تفعيل list_select_related في Admin")
print("=" * 80)
