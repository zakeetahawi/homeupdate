# Generated manually for comprehensive performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manufacturing', '0024_manufacturingorder_mfg_status_type_idx_and_more'),
    ]

    operations = [
        # إضافة فهارس حرجة مفقودة على ManufacturingOrderItem
        migrations.AddIndex(
            model_name='manufacturingorderitem',
            index=models.Index(fields=['manufacturing_order'], name='mfg_item_order_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorderitem',
            index=models.Index(fields=['order_item'], name='mfg_item_orderitem_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorderitem',
            index=models.Index(fields=['cutting_item'], name='mfg_item_cutting_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorderitem',
            index=models.Index(fields=['status'], name='mfg_item_status_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorderitem',
            index=models.Index(fields=['manufacturing_order', 'fabric_received'], name='mfg_item_ord_rcvd_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorderitem',
            index=models.Index(fields=['manufacturing_order', 'status'], name='mfg_item_ord_sts_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorderitem',
            index=models.Index(fields=['fabric_received_by'], name='mfg_item_rcvd_by_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorderitem',
            index=models.Index(fields=['cutting_date'], name='mfg_item_cut_date_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorderitem',
            index=models.Index(fields=['delivery_date'], name='mfg_item_dlv_date_idx'),
        ),
        
        # إضافة فهارس محسّنة على ManufacturingOrder
        migrations.AddIndex(
            model_name='manufacturingorder',
            index=models.Index(fields=['contract_number'], name='mfg_contract_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorder',
            index=models.Index(fields=['invoice_number'], name='mfg_invoice_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorder',
            index=models.Index(fields=['exit_permit_number'], name='mfg_exit_permit_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorder',
            index=models.Index(fields=['delivery_permit_number'], name='mfg_dlv_permit_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorder',
            index=models.Index(fields=['completion_date'], name='mfg_completion_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorder',
            index=models.Index(fields=['delivery_date'], name='mfg_delivery_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorder',
            index=models.Index(fields=['order_date'], name='mfg_order_date_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorder',
            index=models.Index(fields=['expected_delivery_date', 'status'], name='mfg_exp_dlv_sts_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorder',
            index=models.Index(fields=['production_line', 'status', 'created_at'], name='mfg_line_sts_crt_idx'),
        ),
        migrations.AddIndex(
            model_name='manufacturingorder',
            index=models.Index(fields=['order_type', 'status', 'order_date'], name='mfg_type_sts_date_idx'),
        ),
    ]
