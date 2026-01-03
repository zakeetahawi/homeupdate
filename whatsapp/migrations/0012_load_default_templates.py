# Generated data migration for loading default templates

from django.db import migrations
from django.core.management import call_command
import os


def load_fixtures(apps, schema_editor):
    """Load default WhatsApp templates from fixtures"""
    # Check if templates already exist
    WhatsAppMessageTemplate = apps.get_model('whatsapp', 'WhatsAppMessageTemplate')
    
    if WhatsAppMessageTemplate.objects.count() == 0:
        # Only load fixtures if no templates exist
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'fixtures',
            'whatsapp_templates.json'
        )
        
        if os.path.exists(fixture_path):
            call_command('loaddata', fixture_path, verbosity=0)
            print("✅ Loaded default WhatsApp templates from fixtures")
        else:
            print("⚠️ Fixture file not found, skipping template loading")
    else:
        print("ℹ️ Templates already exist, skipping fixture loading")


def unload_fixtures(apps, schema_editor):
    """Reverse migration - do nothing"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('whatsapp', '0011_add_header_footer_to_template'),
    ]

    operations = [
        migrations.RunPython(load_fixtures, unload_fixtures),
    ]
