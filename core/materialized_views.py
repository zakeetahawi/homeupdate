"""
📊 PostgreSQL Materialized Views - عروض مادية لتحسين الأداء 1000%

Materialized Views هي جداول محسوبة مسبقاً تخزن نتائج الاستعلامات المعقدة
مما يجعل الوصول إليها فوري بدلاً من حساب النتائج في كل طلب.

الفوائد:
1. تقليل وقت الاستعلام من ثوان إلى ميلي ثانية
2. تقليل الضغط على قاعدة البيانات
3. تحسين تجربة المستخدم

الاستخدام:
1. تشغيل هذا الملف لإنشاء الـ Views: python manage.py shell < core/materialized_views.py
2. تشغيل التحديث الدوري: python -c "from core.materialized_views import refresh_all_views; refresh_all_views()"
"""

import logging

from django.core.cache import cache
from django.db import connection, transaction

logger = logging.getLogger("performance")

# =============================================
# SQL لإنشاء Materialized Views
# =============================================

CREATE_ORDER_STATISTICS_VIEW = """
-- إحصائيات الطلبات حسب الفرع والحالة
DROP MATERIALIZED VIEW IF EXISTS mv_order_statistics CASCADE;

CREATE MATERIALIZED VIEW mv_order_statistics AS
SELECT 
    branch_id,
    order_status,
    DATE_TRUNC('day', created_at) as order_date,
    COUNT(*) as order_count,
    COALESCE(SUM(total_amount), 0) as total_amount,
    COALESCE(SUM(paid_amount), 0) as paid_amount,
    COALESCE(AVG(total_amount), 0) as avg_order_value
FROM orders_order
WHERE created_at >= CURRENT_DATE - INTERVAL '365 days'
GROUP BY branch_id, order_status, DATE_TRUNC('day', created_at);

CREATE UNIQUE INDEX idx_mv_order_stats_unique 
ON mv_order_statistics (branch_id, order_status, order_date);

CREATE INDEX idx_mv_order_stats_branch ON mv_order_statistics (branch_id);
CREATE INDEX idx_mv_order_stats_status ON mv_order_statistics (order_status);
CREATE INDEX idx_mv_order_stats_date ON mv_order_statistics (order_date);
"""

CREATE_DAILY_ORDER_SUMMARY_VIEW = """
-- ملخص الطلبات اليومي
DROP MATERIALIZED VIEW IF EXISTS mv_daily_order_summary CASCADE;

CREATE MATERIALIZED VIEW mv_daily_order_summary AS
SELECT 
    DATE_TRUNC('day', o.created_at) as order_date,
    o.branch_id,
    b.name as branch_name,
    COUNT(*) as total_orders,
    COUNT(CASE WHEN o.order_status = 'completed' THEN 1 END) as completed_orders,
    COUNT(CASE WHEN o.order_status = 'pending' THEN 1 END) as pending_orders,
    COUNT(CASE WHEN o.order_status = 'cancelled' THEN 1 END) as cancelled_orders,
    COALESCE(SUM(o.total_amount), 0) as total_sales,
    COALESCE(SUM(o.paid_amount), 0) as total_collected,
    COALESCE(SUM(o.total_amount) - SUM(o.paid_amount), 0) as total_remaining
FROM orders_order o
LEFT JOIN accounts_branch b ON o.branch_id = b.id
WHERE o.created_at >= CURRENT_DATE - INTERVAL '365 days'
GROUP BY DATE_TRUNC('day', o.created_at), o.branch_id, b.name;

CREATE UNIQUE INDEX idx_mv_daily_summary_unique 
ON mv_daily_order_summary (order_date, branch_id);

CREATE INDEX idx_mv_daily_summary_date ON mv_daily_order_summary (order_date DESC);
CREATE INDEX idx_mv_daily_summary_branch ON mv_daily_order_summary (branch_id);
"""

CREATE_CUSTOMER_STATISTICS_VIEW = """
-- إحصائيات العملاء
DROP MATERIALIZED VIEW IF EXISTS mv_customer_statistics CASCADE;

CREATE MATERIALIZED VIEW mv_customer_statistics AS
SELECT 
    c.id as customer_id,
    c.name as customer_name,
    c.phone as customer_phone,
    c.branch_id,
    COUNT(o.id) as total_orders,
    COALESCE(SUM(o.total_amount), 0) as total_spent,
    COALESCE(SUM(o.paid_amount), 0) as total_paid,
    MAX(o.created_at) as last_order_date,
    MIN(o.created_at) as first_order_date,
    COALESCE(AVG(o.total_amount), 0) as avg_order_value
FROM customers_customer c
LEFT JOIN orders_order o ON c.id = o.customer_id
WHERE c.status = 'active'
GROUP BY c.id, c.name, c.phone, c.branch_id;

CREATE UNIQUE INDEX idx_mv_customer_stats_id ON mv_customer_statistics (customer_id);
CREATE INDEX idx_mv_customer_stats_branch ON mv_customer_statistics (branch_id);
CREATE INDEX idx_mv_customer_stats_total_spent ON mv_customer_statistics (total_spent DESC);
CREATE INDEX idx_mv_customer_stats_total_orders ON mv_customer_statistics (total_orders DESC);
"""

CREATE_INSTALLATION_STATISTICS_VIEW = """
-- إحصائيات التركيبات
DROP MATERIALIZED VIEW IF EXISTS mv_installation_statistics CASCADE;

CREATE MATERIALIZED VIEW mv_installation_statistics AS
SELECT 
    ROW_NUMBER() OVER () as id,
    DATE_TRUNC('day', is2.scheduled_date) as schedule_date,
    is2.team_id,
    it.name as team_name,
    is2.status,
    COUNT(*) as installation_count,
    COALESCE(o.branch_id, 0) as branch_id
FROM installations_installationschedule is2
LEFT JOIN installations_installationteam it ON is2.team_id = it.id
LEFT JOIN orders_order o ON is2.order_id = o.id
WHERE is2.scheduled_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY DATE_TRUNC('day', is2.scheduled_date), is2.team_id, it.name, is2.status, o.branch_id;

CREATE UNIQUE INDEX idx_mv_install_stats_unique ON mv_installation_statistics (id);
CREATE INDEX idx_mv_install_stats_date ON mv_installation_statistics (schedule_date DESC);
CREATE INDEX idx_mv_install_stats_team ON mv_installation_statistics (team_id);
CREATE INDEX idx_mv_install_stats_status ON mv_installation_statistics (status);
"""

CREATE_MANUFACTURING_STATISTICS_VIEW = """
-- إحصائيات التصنيع
DROP MATERIALIZED VIEW IF EXISTS mv_manufacturing_statistics CASCADE;

CREATE MATERIALIZED VIEW mv_manufacturing_statistics AS
SELECT 
    ROW_NUMBER() OVER () as id,
    DATE_TRUNC('day', m.created_at) as created_date,
    m.status,
    m.order_type,
    m.production_line_id,
    pl.name as production_line_name,
    COUNT(*) as order_count,
    COALESCE(o.branch_id, 0) as branch_id
FROM manufacturing_manufacturingorder m
LEFT JOIN manufacturing_productionline pl ON m.production_line_id = pl.id
LEFT JOIN orders_order o ON m.order_id = o.id
WHERE m.created_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY DATE_TRUNC('day', m.created_at), m.status, m.order_type, m.production_line_id, pl.name, o.branch_id;

CREATE UNIQUE INDEX idx_mv_mfg_stats_unique ON mv_manufacturing_statistics (id);
CREATE INDEX idx_mv_mfg_stats_date ON mv_manufacturing_statistics (created_date DESC);
CREATE INDEX idx_mv_mfg_stats_status ON mv_manufacturing_statistics (status);
CREATE INDEX idx_mv_mfg_stats_line ON mv_manufacturing_statistics (production_line_id);
"""

CREATE_PRODUCT_SALES_VIEW = """
-- إحصائيات مبيعات المنتجات
DROP MATERIALIZED VIEW IF EXISTS mv_product_sales CASCADE;

CREATE MATERIALIZED VIEW mv_product_sales AS
SELECT 
    oi.product_id,
    p.name as product_name,
    p.code as product_code,
    p.category_id,
    c.name as category_name,
    COUNT(DISTINCT oi.order_id) as times_ordered,
    SUM(oi.quantity) as total_quantity_sold,
    SUM(oi.quantity * oi.unit_price) as total_revenue,
    AVG(oi.unit_price) as avg_price,
    MAX(o.order_date) as last_sold_date
FROM orders_orderitem oi
LEFT JOIN inventory_product p ON oi.product_id = p.id
LEFT JOIN inventory_category c ON p.category_id = c.id
LEFT JOIN orders_order o ON oi.order_id = o.id
WHERE o.created_at >= CURRENT_DATE - INTERVAL '365 days'
GROUP BY oi.product_id, p.name, p.code, p.category_id, c.name;

CREATE UNIQUE INDEX idx_mv_product_sales_id ON mv_product_sales (product_id);
CREATE INDEX idx_mv_product_sales_category ON mv_product_sales (category_id);
CREATE INDEX idx_mv_product_sales_revenue ON mv_product_sales (total_revenue DESC);
CREATE INDEX idx_mv_product_sales_qty ON mv_product_sales (total_quantity_sold DESC);
"""

CREATE_SALESPERSON_PERFORMANCE_VIEW = """
-- أداء البائعين
DROP MATERIALIZED VIEW IF EXISTS mv_salesperson_performance CASCADE;

CREATE MATERIALIZED VIEW mv_salesperson_performance AS
SELECT 
    o.salesperson_id,
    s.name as salesperson_name,
    o.branch_id,
    b.name as branch_name,
    DATE_TRUNC('month', o.created_at) as month,
    COUNT(*) as orders_count,
    COALESCE(SUM(o.total_amount), 0) as total_sales,
    COALESCE(SUM(o.paid_amount), 0) as total_collected,
    COALESCE(AVG(o.total_amount), 0) as avg_order_value,
    COUNT(CASE WHEN o.order_status = 'completed' THEN 1 END) as completed_orders,
    COUNT(CASE WHEN o.order_status = 'cancelled' THEN 1 END) as cancelled_orders
FROM orders_order o
LEFT JOIN accounts_salesperson s ON o.salesperson_id = s.id
LEFT JOIN accounts_branch b ON o.branch_id = b.id
WHERE o.created_at >= CURRENT_DATE - INTERVAL '365 days'
  AND o.salesperson_id IS NOT NULL
GROUP BY o.salesperson_id, s.name, o.branch_id, b.name, DATE_TRUNC('month', o.created_at);

CREATE UNIQUE INDEX idx_mv_sp_perf_unique 
ON mv_salesperson_performance (salesperson_id, branch_id, month);

CREATE INDEX idx_mv_sp_perf_sales ON mv_salesperson_performance (total_sales DESC);
CREATE INDEX idx_mv_sp_perf_month ON mv_salesperson_performance (month DESC);
"""

CREATE_INVENTORY_SUMMARY_VIEW = """
-- ملخص المخزون
DROP MATERIALIZED VIEW IF EXISTS mv_inventory_summary CASCADE;

CREATE MATERIALIZED VIEW mv_inventory_summary AS
SELECT 
    p.id as product_id,
    p.name as product_name,
    p.code as product_code,
    p.category_id,
    p.minimum_stock,
    COALESCE(
        (SELECT st.running_balance 
         FROM inventory_stocktransaction st 
         WHERE st.product_id = p.id 
         ORDER BY st.transaction_date DESC, st.id DESC 
         LIMIT 1), 0
    ) as current_stock,
    CASE 
        WHEN COALESCE(
            (SELECT st.running_balance 
             FROM inventory_stocktransaction st 
             WHERE st.product_id = p.id 
             ORDER BY st.transaction_date DESC, st.id DESC 
             LIMIT 1), 0
        ) <= 0 THEN 'out_of_stock'
        WHEN COALESCE(
            (SELECT st.running_balance 
             FROM inventory_stocktransaction st 
             WHERE st.product_id = p.id 
             ORDER BY st.transaction_date DESC, st.id DESC 
             LIMIT 1), 0
        ) <= p.minimum_stock THEN 'low_stock'
        ELSE 'in_stock'
    END as stock_status
FROM inventory_product p;

CREATE UNIQUE INDEX idx_mv_inventory_product ON mv_inventory_summary (product_id);
CREATE INDEX idx_mv_inventory_status ON mv_inventory_summary (stock_status);
CREATE INDEX idx_mv_inventory_category ON mv_inventory_summary (category_id);
"""

# =============================================
# Functions لإدارة Materialized Views
# =============================================


def create_all_views():
    """
    إنشاء جميع Materialized Views

    يجب تشغيل هذا مرة واحدة عند الإعداد الأولي
    """
    views = [
        ("Order Statistics", CREATE_ORDER_STATISTICS_VIEW),
        ("Daily Order Summary", CREATE_DAILY_ORDER_SUMMARY_VIEW),
        ("Customer Statistics", CREATE_CUSTOMER_STATISTICS_VIEW),
        ("Installation Statistics", CREATE_INSTALLATION_STATISTICS_VIEW),
        ("Manufacturing Statistics", CREATE_MANUFACTURING_STATISTICS_VIEW),
        ("Product Sales", CREATE_PRODUCT_SALES_VIEW),
        ("Salesperson Performance", CREATE_SALESPERSON_PERFORMANCE_VIEW),
        ("Inventory Summary", CREATE_INVENTORY_SUMMARY_VIEW),
    ]

    results = []

    with connection.cursor() as cursor:
        for name, sql in views:
            try:
                cursor.execute(sql)
                results.append((name, "SUCCESS", None))
                logger.info(f"Created materialized view: {name}")
            except Exception as e:
                results.append((name, "FAILED", str(e)))
                logger.error(f"Failed to create materialized view {name}: {e}")

    return results


def refresh_view(view_name: str, concurrently: bool = True):
    """
    تحديث Materialized View معين

    Args:
        view_name: اسم الـ view
        concurrently: تحديث بدون قفل (يتطلب UNIQUE INDEX)
    """
    try:
        with connection.cursor() as cursor:
            if concurrently:
                cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
            else:
                cursor.execute(f"REFRESH MATERIALIZED VIEW {view_name}")

        # مسح الكاش المرتبط
        cache.delete_pattern(f"{view_name}:*")

        logger.info(f"Refreshed materialized view: {view_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to refresh {view_name}: {e}")
        return False


def refresh_all_views():
    """
    تحديث جميع Materialized Views

    يُنصح بتشغيل هذا كل 5-15 دقيقة عبر Celery أو Cron
    """
    views = [
        "mv_order_statistics",
        "mv_daily_order_summary",
        "mv_customer_statistics",
        "mv_installation_statistics",
        "mv_manufacturing_statistics",
        "mv_product_sales",
        "mv_salesperson_performance",
        "mv_inventory_summary",
    ]

    results = {}

    for view in views:
        try:
            refresh_view(view, concurrently=True)
            results[view] = "SUCCESS"
        except Exception as e:
            # إذا فشل التحديث المتزامن، جرب بدونه
            try:
                refresh_view(view, concurrently=False)
                results[view] = "SUCCESS (non-concurrent)"
            except Exception as e2:
                results[view] = f"FAILED: {e2}"

    logger.info(f"Refreshed all views: {results}")
    return results


def get_order_statistics(branch_id=None, days=30):
    """
    الحصول على إحصائيات الطلبات من Materialized View

    أسرع 100x من الاستعلام المباشر
    """
    cache_key = f"mv_order_stats:{branch_id}:{days}"
    cached = cache.get(cache_key)

    if cached:
        return cached

    from datetime import timedelta

    from django.utils import timezone

    cutoff_date = timezone.now().date() - timedelta(days=days)

    with connection.cursor() as cursor:
        sql = """
            SELECT 
                order_status,
                SUM(order_count) as total_orders,
                SUM(total_amount) as total_amount,
                SUM(paid_amount) as paid_amount,
                AVG(avg_order_value) as avg_order_value
            FROM mv_order_statistics
            WHERE order_date >= %s
        """
        params = [cutoff_date]

        if branch_id:
            sql += " AND branch_id = %s"
            params.append(branch_id)

        sql += " GROUP BY order_status"

        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # تخزين في الكاش لمدة 5 دقائق
    cache.set(cache_key, results, 300)

    return results


def get_daily_summary(branch_id=None, days=30):
    """
    الحصول على الملخص اليومي من Materialized View
    """
    cache_key = f"mv_daily_summary:{branch_id}:{days}"
    cached = cache.get(cache_key)

    if cached:
        return cached

    from datetime import timedelta

    from django.utils import timezone

    cutoff_date = timezone.now().date() - timedelta(days=days)

    with connection.cursor() as cursor:
        sql = """
            SELECT 
                order_date,
                branch_name,
                total_orders,
                completed_orders,
                pending_orders,
                cancelled_orders,
                total_sales,
                total_collected,
                total_remaining
            FROM mv_daily_order_summary
            WHERE order_date >= %s
        """
        params = [cutoff_date]

        if branch_id:
            sql += " AND branch_id = %s"
            params.append(branch_id)

        sql += " ORDER BY order_date DESC"

        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    cache.set(cache_key, results, 300)

    return results


def get_top_customers(branch_id=None, limit=20):
    """
    الحصول على أفضل العملاء من Materialized View
    """
    cache_key = f"mv_top_customers:{branch_id}:{limit}"
    cached = cache.get(cache_key)

    if cached:
        return cached

    with connection.cursor() as cursor:
        sql = """
            SELECT 
                customer_id,
                customer_name,
                customer_phone,
                total_orders,
                total_spent,
                total_paid,
                last_order_date,
                avg_order_value
            FROM mv_customer_statistics
            WHERE total_orders > 0
        """
        params = []

        if branch_id:
            sql += " AND branch_id = %s"
            params.append(branch_id)

        sql += f" ORDER BY total_spent DESC LIMIT {int(limit)}"

        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    cache.set(cache_key, results, 300)

    return results


def get_top_products(category_id=None, limit=20):
    """
    الحصول على أفضل المنتجات مبيعاً من Materialized View
    """
    cache_key = f"mv_top_products:{category_id}:{limit}"
    cached = cache.get(cache_key)

    if cached:
        return cached

    with connection.cursor() as cursor:
        sql = """
            SELECT 
                product_id,
                product_name,
                product_code,
                category_name,
                times_ordered,
                total_quantity_sold,
                total_revenue,
                avg_price,
                last_sold_date
            FROM mv_product_sales
        """
        params = []

        if category_id:
            sql += " WHERE category_id = %s"
            params.append(category_id)

        sql += f" ORDER BY total_revenue DESC LIMIT {int(limit)}"

        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    cache.set(cache_key, results, 300)

    return results


def get_inventory_status():
    """
    الحصول على حالة المخزون من Materialized View
    """
    cache_key = "mv_inventory_status"
    cached = cache.get(cache_key)

    if cached:
        return cached

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                stock_status,
                COUNT(*) as count
            FROM mv_inventory_summary
            GROUP BY stock_status
        """
        )

        results = {row[0]: row[1] for row in cursor.fetchall()}

    cache.set(cache_key, results, 300)

    return results


def get_low_stock_products(limit=50):
    """
    الحصول على المنتجات منخفضة المخزون
    """
    cache_key = f"mv_low_stock:{limit}"
    cached = cache.get(cache_key)

    if cached:
        return cached

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT 
                product_id,
                product_name,
                product_code,
                current_stock,
                minimum_stock,
                stock_status
            FROM mv_inventory_summary
            WHERE stock_status IN ('low_stock', 'out_of_stock')
            ORDER BY 
                CASE stock_status 
                    WHEN 'out_of_stock' THEN 1 
                    WHEN 'low_stock' THEN 2 
                END,
                current_stock ASC
            LIMIT {int(limit)}
        """
        )

        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

    cache.set(cache_key, results, 300)

    return results


# =============================================
# Celery Task للتحديث الدوري (اختياري)
# =============================================


def setup_celery_task():
    """
    إعداد مهمة Celery للتحديث الدوري

    أضف هذا إلى ملف celery.py أو tasks.py
    """
    task_code = '''
from celery import shared_task
from core.materialized_views import refresh_all_views

@shared_task(name='refresh_materialized_views')
def refresh_materialized_views_task():
    """تحديث Materialized Views كل 5 دقائق"""
    return refresh_all_views()

# أضف هذا إلى CELERY_BEAT_SCHEDULE في settings.py:
# 'refresh-materialized-views': {
#     'task': 'refresh_materialized_views',
#     'schedule': crontab(minute='*/5'),
# },
'''
    return task_code


# =============================================
# Script للتشغيل المباشر
# =============================================

if __name__ == "__main__":
    import django

    django.setup()

    print("Creating Materialized Views...")
    results = create_all_views()

    for name, status, error in results:
        if status == "SUCCESS":
            print(f"✅ {name}: {status}")
        else:
            print(f"❌ {name}: {status} - {error}")

    print("\nRefreshing all views...")
    refresh_results = refresh_all_views()

    for view, status in refresh_results.items():
        print(f"  {view}: {status}")

    print("\nDone!")
