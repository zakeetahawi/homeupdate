# Generated manually to fix Salesperson user field issue

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_remove_useractivitylog_session_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesperson',
            name='user',
            field=models.OneToOneField(
                blank=True, 
                help_text='ربط البائع بحساب مستخدم (اختياري)', 
                null=True, 
                on_delete=django.db.models.deletion.SET_NULL, 
                related_name='salesperson_profile', 
                to=settings.AUTH_USER_MODEL, 
                verbose_name='حساب المستخدم'
            ),
        ),
    ]
