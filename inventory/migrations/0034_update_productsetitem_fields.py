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
                -- Check if base_product_id column already exists (via base_product field)
                DO $$
                BEGIN
                    -- If variant_id column exists, migrate from it to base_product_id
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'inventory_productsetitem' 
                        AND column_name = 'variant_id'
                    ) THEN
                        -- Add new column if not exists
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'inventory_productsetitem' 
                            AND column_name = 'base_product_id'
                        ) THEN
                            ALTER TABLE inventory_productsetitem 
                            ADD COLUMN base_product_id BIGINT NULL;
                        END IF;
                        
                        -- Copy data from variant_id to base_product_id
                        UPDATE inventory_productsetitem 
                        SET base_product_id = (
                            SELECT base_product_id 
                            FROM inventory_productvariant 
                            WHERE inventory_productvariant.id = inventory_productsetitem.variant_id
                        )
                        WHERE variant_id IS NOT NULL AND base_product_id IS NULL;
                        
                        -- Make base_product_id NOT NULL after data migration
                        ALTER TABLE inventory_productsetitem 
                        ALTER COLUMN base_product_id SET NOT NULL;
                        
                        -- Add foreign key constraint if not exists
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints 
                            WHERE constraint_name = 'inventory_productsetitem_base_product_id_fkey'
                        ) THEN
                            ALTER TABLE inventory_productsetitem 
                            ADD CONSTRAINT inventory_productsetitem_base_product_id_fkey 
                            FOREIGN KEY (base_product_id) 
                            REFERENCES inventory_baseproduct(id) 
                            ON DELETE CASCADE 
                            DEFERRABLE INITIALLY DEFERRED;
                        END IF;
                        
                        -- Drop old variant_id column and its constraint
                        ALTER TABLE inventory_productsetitem 
                        DROP CONSTRAINT IF EXISTS inventory_productset_variant_id_17f81c03_fk_inventory;
                        
                        ALTER TABLE inventory_productsetitem 
                        DROP COLUMN IF EXISTS variant_id;
                    END IF;
                    -- If variant_id does not exist, the table already has the correct structure
                END $$;
            """,
            reverse_sql="""
                -- This migration is mostly idempotent, reverse is no-op
                DO $$ BEGIN END $$;
            """
        ),
    ]
