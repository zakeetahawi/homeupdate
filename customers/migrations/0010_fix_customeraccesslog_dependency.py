# Generated manually to fix dependency issue

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0016_delete_notification"),
        ("customers", "0008_discounttype_customer_discount_type_and_more"),
    ]

    operations = [
        # No operations needed, just fixing the dependency
    ]
