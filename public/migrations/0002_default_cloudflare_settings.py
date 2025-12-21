"""
Data migration to create default Cloudflare settings
This ensures settings are available immediately after git pull
"""
from django.db import migrations


def create_default_settings(apps, schema_editor):
    """Create default CloudflareSettings if not exists"""
    CloudflareSettings = apps.get_model('public', 'CloudflareSettings')
    
    if not CloudflareSettings.objects.exists():
        CloudflareSettings.objects.create(
            id=1,
            worker_url='https://qr.elkhawaga.uk',
            sync_api_key='cf_66eed06368ff433b92ac3f80c950038f',
            is_enabled=True,
            auto_sync_on_save=True,
            products_synced=0,
        )


def reverse_migration(apps, schema_editor):
    """Remove default settings"""
    CloudflareSettings = apps.get_model('public', 'CloudflareSettings')
    CloudflareSettings.objects.filter(id=1).delete()


class Migration(migrations.Migration):
    
    dependencies = [
        ('public', '0001_cloudflare_settings'),
    ]
    
    operations = [
        migrations.RunPython(create_default_settings, reverse_migration),
    ]
