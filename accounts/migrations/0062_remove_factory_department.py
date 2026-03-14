"""
Data migration to permanently remove the factory department.
The factory app was removed and replaced by manufacturing.
"""

from django.db import migrations


def remove_factory_department(apps, schema_editor):
    """حذف قسم المصنع (factory) نهائياً من قاعدة البيانات"""
    Department = apps.get_model("accounts", "Department")
    
    # Remove is_core protection first so delete works
    factory_deps = Department.objects.filter(code="factory")
    factory_deps.update(is_core=False)
    
    # Delete factory department and any children
    for dept in factory_deps:
        # Delete children first
        Department.objects.filter(parent=dept).delete()
        dept.delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0061_add_show_external_sales_to_department"),
    ]

    operations = [
        migrations.RunPython(remove_factory_department, noop),
    ]
