# This migration was originally separate but its operations were merged into
# 0017_customer_deleted_at_customer_deleted_by_and_more.py.
# This stub exists to satisfy the dependency chain since the database already
# has a record of this migration being applied.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0017_customer_deleted_at_customer_deleted_by_and_more"),
    ]

    operations = [
        # No operations — merged into 0017
    ]
