# Generated migration to update existing ProductSet table
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0032_add_product_set"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add missing fields using raw SQL to avoid state conflicts
        migrations.RunSQL(
            sql="""
                ALTER TABLE inventory_productset 
                ADD COLUMN IF NOT EXISTS cloudflare_synced BOOLEAN DEFAULT FALSE NOT NULL;
                
                ALTER TABLE inventory_productset 
                ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMP WITH TIME ZONE NULL;
                
                ALTER TABLE inventory_productset 
                ADD COLUMN IF NOT EXISTS created_by_id BIGINT NULL;
                
                ALTER TABLE inventory_productset 
                ADD CONSTRAINT inventory_productset_created_by_id_fkey 
                FOREIGN KEY (created_by_id) REFERENCES accounts_user(id) 
                ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
            """,
            reverse_sql="""
                ALTER TABLE inventory_productset DROP CONSTRAINT IF EXISTS inventory_productset_created_by_id_fkey;
                ALTER TABLE inventory_productset DROP COLUMN IF EXISTS created_by_id;
                ALTER TABLE inventory_productset DROP COLUMN IF EXISTS last_synced_at;
                ALTER TABLE inventory_productset DROP COLUMN IF EXISTS cloudflare_synced;
            """
        ),
    ]
