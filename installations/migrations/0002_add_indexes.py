# Generated manually for performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("installations", "0001_initial"),
        ("orders", "0001_initial"),
        ("manufacturing", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            # إضافة فهرس مركب للطلبات مع cast للـ JSONB
            """
            CREATE INDEX IF NOT EXISTS idx_orders_installation_filter 
            ON orders_order (order_status) 
            WHERE selected_types::text LIKE '%installation%';
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_orders_installation_filter;",
        ),
        migrations.RunSQL(
            # إضافة فهرس لأوامر التصنيع الجاهزة للتركيب
            """
            CREATE INDEX IF NOT EXISTS idx_manufacturing_ready_install 
            ON manufacturing_manufacturingorder (status, order_id) 
            WHERE status IN ('ready_install', 'delivered');
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_manufacturing_ready_install;",
        ),
        migrations.RunSQL(
            # إضافة فهرس لجدولة التركيبات
            """
            CREATE INDEX IF NOT EXISTS idx_installation_schedule_status 
            ON installations_installationschedule (status, order_id, scheduled_date);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_installation_schedule_status;",
        ),
        migrations.RunSQL(
            # إضافة فهرس للبحث في أرقام الطلبات
            """
            CREATE INDEX IF NOT EXISTS idx_orders_search 
            ON orders_order (order_number);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_orders_search;",
        ),
        migrations.RunSQL(
            # إضافة فهرس للعملاء للبحث السريع
            """
            CREATE INDEX IF NOT EXISTS idx_customers_name_search 
            ON customers_customer (name);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_customers_name_search;",
        ),
        migrations.RunSQL(
            # إضافة فهرس للبحث في أرقام الهواتف
            """
            CREATE INDEX IF NOT EXISTS idx_customers_phone_search 
            ON customers_customer (phone);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_customers_phone_search;",
        ),
    ]
