# Generated data migration for loading default templates, rules, and event types

from django.db import migrations
from django.core.management import call_command
import os


def load_fixtures(apps, schema_editor):
    """Load default WhatsApp templates, rules, and event types from fixtures"""
    fixtures_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'fixtures'
    )
    
    # Load event types first (they may be referenced by rules)
    WhatsAppEventType = apps.get_model('whatsapp', 'WhatsAppEventType')
    if WhatsAppEventType.objects.count() == 0:
        event_types_path = os.path.join(fixtures_dir, 'whatsapp_event_types.json')
        if os.path.exists(event_types_path):
            call_command('loaddata', event_types_path, verbosity=0)
            print("✅ Loaded default WhatsApp event types")
    else:
        print("ℹ️ Event types already exist, skipping")
    
    # Load templates
    WhatsAppMessageTemplate = apps.get_model('whatsapp', 'WhatsAppMessageTemplate')
    if WhatsAppMessageTemplate.objects.count() == 0:
        templates_path = os.path.join(fixtures_dir, 'whatsapp_templates.json')
        if os.path.exists(templates_path):
            call_command('loaddata', templates_path, verbosity=0)
            print("✅ Loaded default WhatsApp templates")
    else:
        print("ℹ️ Templates already exist, skipping")
    
    # Load rules
    WhatsAppNotificationRule = apps.get_model('whatsapp', 'WhatsAppNotificationRule')
    if WhatsAppNotificationRule.objects.count() == 0:
        rules_path = os.path.join(fixtures_dir, 'whatsapp_rules.json')
        if os.path.exists(rules_path):
            call_command('loaddata', rules_path, verbosity=0)
            print("✅ Loaded default WhatsApp notification rules")
    else:
        print("ℹ️ Rules already exist, skipping")


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
