# Generated manually for comprehensive performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0015_product_product_code_idx_product_product_name_idx_and_more'),
    ]

    operations = [
        # إضافة فهارس إضافية على StockTransaction (بالإضافة للموجود)
        migrations.AddIndex(
            model_name='stocktransaction',
            index=models.Index(fields=['created_by'], name='stock_created_by_idx'),
        ),
        migrations.AddIndex(
            model_name='stocktransaction',
            index=models.Index(fields=['running_balance'], name='stock_balance_idx'),
        ),
        migrations.AddIndex(
            model_name='stocktransaction',
            index=models.Index(fields=['date'], name='stock_date_created_idx'),
        ),
        
        # إضافة فهارس محسّنة على Product
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['currency'], name='product_currency_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['unit'], name='product_unit_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['minimum_stock'], name='product_min_stock_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', 'created_at'], name='product_cat_created_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['updated_at'], name='product_updated_idx'),
        ),
        
        # إضافة فهارس على Warehouse
        migrations.AddIndex(
            model_name='warehouse',
            index=models.Index(fields=['branch'], name='warehouse_branch_idx'),
        ),
        migrations.AddIndex(
            model_name='warehouse',
            index=models.Index(fields=['manager'], name='warehouse_manager_idx'),
        ),
        # Warehouse already has is_active index in Meta
        
        # إضافة فهارس على Category
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['parent'], name='category_parent_idx'),
        ),
        # Category doesn't have is_active field
    ]

