# Migration to update ProductSetItem table structure
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0033_update_productset_fields"),
    ]

    operations = [
        # Add base_product_id column and update data
        migrations.RunSQL(
            sql="""
                -- Add new column
                ALTER TABLE inventory_productsetitem 
                ADD COLUMN IF NOT EXISTS base_product_id BIGINT NULL;
                
                -- Copy data from variant_id to base_product_id (get base product from variant)
                -- If variant exists, get its base_product_id, otherwise keep NULL
                UPDATE inventory_productsetitem 
                SET base_product_id = (
                    SELECT base_product_id 
                    FROM inventory_productvariant 
                    WHERE inventory_productvariant.id = inventory_productsetitem.variant_id
                )
                WHERE variant_id IS NOT NULL;
                
                -- Make base_product_id NOT NULL after data migration
                ALTER TABLE inventory_productsetitem 
                ALTER COLUMN base_product_id SET NOT NULL;
                
                -- Add foreign key constraint
                ALTER TABLE inventory_productsetitem 
                ADD CONSTRAINT inventory_productsetitem_base_product_id_fkey 
                FOREIGN KEY (base_product_id) 
                REFERENCES inventory_baseproduct(id) 
                ON DELETE CASCADE 
                DEFERRABLE INITIALLY DEFERRED;
                
                -- Drop old variant_id column and its constraint
                ALTER TABLE inventory_productsetitem 
                DROP CONSTRAINT IF EXISTS inventory_productset_variant_id_17f81c03_fk_inventory;
                
                ALTER TABLE inventory_productsetitem 
                DROP COLUMN IF EXISTS variant_id;
            """,
            reverse_sql="""
                -- Recreate variant_id column
                ALTER TABLE inventory_productsetitem 
                ADD COLUMN variant_id BIGINT NULL;
                
                -- Drop new constraints and column
                ALTER TABLE inventory_productsetitem 
                DROP CONSTRAINT IF EXISTS inventory_productsetitem_base_product_id_fkey;
                
                ALTER TABLE inventory_productsetitem 
                DROP COLUMN IF EXISTS base_product_id;
            """
        ),
    ]
