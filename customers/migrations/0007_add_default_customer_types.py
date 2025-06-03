from django.db import migrations
from django.utils.translation import gettext_lazy as _

def create_default_types(apps, schema_editor):
    CustomerType = apps.get_model('customers', 'CustomerType')
    default_types = [
        {
            'code': 'retail',
            'name': 'أفراد',
            'description': 'عملاء التجزئة',
            'is_active': True
        },
        {
            'code': 'wholesale',
            'name': 'جملة',
            'description': 'عملاء الجملة',
            'is_active': True
        },
        {
            'code': 'corporate',
            'name': 'شركات',
            'description': 'العملاء من الشركات',
            'is_active': True
        }
    ]
    
    for type_data in default_types:
        CustomerType.objects.update_or_create(
            code=type_data['code'],
            defaults=type_data
        )

def remove_default_types(apps, schema_editor):
    CustomerType = apps.get_model('customers', 'CustomerType')
    CustomerType.objects.filter(code__in=['retail', 'wholesale', 'corporate']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('customers', '0006_remove_customer_customer_type_custom_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_types, remove_default_types),
    ]