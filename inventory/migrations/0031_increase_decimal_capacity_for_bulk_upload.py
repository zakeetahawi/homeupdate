# Generated manually for numeric field overflow fix (precision 10, scale 2 → 18, 2)
# Drops mv_inventory_summary before altering running_balance (PostgreSQL blocks alter if view depends on column).

from django.db import migrations, models

DROP_MV_INVENTORY_SUMMARY = "DROP MATERIALIZED VIEW IF EXISTS mv_inventory_summary CASCADE;"

RECREATE_MV_INVENTORY_SUMMARY = """
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


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0030_product_deleted_by_productbatch_deleted_by_and_more"),
    ]

    operations = [
        # Drop materialized view so we can alter running_balance column type (PostgreSQL restriction).
        migrations.RunSQL(DROP_MV_INVENTORY_SUMMARY, reverse_sql=RECREATE_MV_INVENTORY_SUMMARY),
        # Product
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(
                decimal_places=2,
                help_text="سعر التجزئة للمنتج",
                max_digits=18,
                verbose_name="السعر القطاعي",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="wholesale_price",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="سعر الجملة للمنتج",
                max_digits=18,
                verbose_name="سعر الجملة",
            ),
        ),
        # StockTransaction (السبب الرئيسي لخطأ الرفع الجماعي)
        migrations.AlterField(
            model_name="stocktransaction",
            name="quantity",
            field=models.DecimalField(decimal_places=2, max_digits=18, verbose_name="الكمية"),
        ),
        migrations.AlterField(
            model_name="stocktransaction",
            name="running_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                verbose_name="الرصيد المتحرك",
            ),
        ),
        # BaseProduct
        migrations.AlterField(
            model_name="baseproduct",
            name="base_price",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="السعر الافتراضي لعملاء التجزئة",
                max_digits=18,
                verbose_name="السعر القطاعي",
            ),
        ),
        migrations.AlterField(
            model_name="baseproduct",
            name="wholesale_price",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="السعر لعملاء الجملة",
                max_digits=18,
                verbose_name="سعر الجملة",
            ),
        ),
        # ProductVariant
        migrations.AlterField(
            model_name="productvariant",
            name="price_override",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="اتركه فارغاً لاستخدام السعر القطاعي الأساسي",
                max_digits=18,
                null=True,
                verbose_name="تجاوز السعر القطاعي",
            ),
        ),
        migrations.AlterField(
            model_name="productvariant",
            name="wholesale_price_override",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="اتركه فارغاً لاستخدام سعر الجملة الأساسي",
                max_digits=18,
                null=True,
                verbose_name="تجاوز سعر الجملة",
            ),
        ),
        # ProductBatch
        migrations.AlterField(
            model_name="productbatch",
            name="cost_price",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                verbose_name="سعر التكلفة",
            ),
        ),
        # PurchaseOrderItem
        migrations.AlterField(
            model_name="purchaseorderitem",
            name="unit_price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=18,
                verbose_name="سعر الوحدة",
            ),
        ),
        # InventoryAdjustment
        migrations.AlterField(
            model_name="inventoryadjustment",
            name="quantity_before",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=18,
                verbose_name="الكمية قبل",
            ),
        ),
        migrations.AlterField(
            model_name="inventoryadjustment",
            name="quantity_after",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=18,
                verbose_name="الكمية بعد",
            ),
        ),
        # StockAlert
        migrations.AlterField(
            model_name="stockalert",
            name="quantity_before",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                verbose_name="الكمية السابقة",
            ),
        ),
        migrations.AlterField(
            model_name="stockalert",
            name="quantity_after",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                verbose_name="الكمية الحالية",
            ),
        ),
        migrations.AlterField(
            model_name="stockalert",
            name="threshold_limit",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                verbose_name="حد التنبيه",
            ),
        ),
        # StockTransferItem
        migrations.AlterField(
            model_name="stocktransferitem",
            name="quantity",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=18,
                verbose_name="الكمية المطلوبة",
            ),
        ),
        migrations.AlterField(
            model_name="stocktransferitem",
            name="received_quantity",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                verbose_name="الكمية المستلمة",
            ),
        ),
        # VariantStock (مخزون المتغير حسب المستودع)
        migrations.AlterField(
            model_name="variantstock",
            name="current_quantity",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=18,
                verbose_name="الكمية الحالية",
            ),
        ),
        migrations.AlterField(
            model_name="variantstock",
            name="reserved_quantity",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="الكمية المحجوزة للطلبات غير المكتملة",
                max_digits=18,
                verbose_name="الكمية المحجوزة",
            ),
        ),
        # PriceHistory
        migrations.AlterField(
            model_name="pricehistory",
            name="old_price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=18,
                verbose_name="السعر القديم",
            ),
        ),
        migrations.AlterField(
            model_name="pricehistory",
            name="new_price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=18,
                verbose_name="السعر الجديد",
            ),
        ),
        migrations.AlterField(
            model_name="pricehistory",
            name="change_value",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="النسبة أو القيمة المطبقة",
                max_digits=18,
                null=True,
                verbose_name="قيمة التغيير",
            ),
        ),
        # Recreate materialized view after column type change.
        migrations.RunSQL(RECREATE_MV_INVENTORY_SUMMARY, reverse_sql=DROP_MV_INVENTORY_SUMMARY),
    ]
