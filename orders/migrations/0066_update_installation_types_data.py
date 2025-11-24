# Generated migration to update installation types to match existing data

from django.db import migrations


def update_installation_types(apps, schema_editor):
    """تحديث أنواع التركيب لتطابق البيانات الموجودة"""
    WizardFieldOption = apps.get_model('orders', 'WizardFieldOption')
    
    # حذف الأنواع القديمة
    WizardFieldOption.objects.filter(field_type='installation_type').delete()
    
    # إضافة أنواع التركيب الصحيحة (مطابقة للنظام القديم)
    installation_types = [
        ('wall_gypsum', 'حائط - جبس', 'fas fa-th-large', 1, False),
        ('wall_concrete', 'حائط - مسلح', 'fas fa-building', 2, True),  # افتراضي
        ('ceiling_gypsum', 'سقف - جبس', 'fas fa-arrow-up', 3, False),
        ('ceiling_concrete', 'سقف - مسلح', 'fas fa-home', 4, False),
        ('curtain_box_concrete', 'بيت ستارة مسلح', 'fas fa-box', 5, False),
        ('curtain_box_gypsum', 'بيت ستارة جبس', 'fas fa-box-open', 6, False),
    ]
    
    for value, display, icon, seq, is_default in installation_types:
        # إضافة extra_data لتحديد ما إذا كان يتطلب بيت ستارة
        requires_curtain_box = value.startswith('curtain_box_')
        
        WizardFieldOption.objects.create(
            field_type='installation_type',
            value=value,
            display_name_ar=display,
            icon=icon,
            sequence=seq,
            is_active=True,
            is_default=is_default,
            extra_data={'requires_curtain_box': requires_curtain_box}
        )


def reverse_migration(apps, schema_editor):
    """التراجع عن التحديث"""
    WizardFieldOption = apps.get_model('orders', 'WizardFieldOption')
    WizardFieldOption.objects.filter(field_type='installation_type').delete()
    
    # استعادة القيم القديمة
    installation_types = [
        ('wall_mount', 'تركيب جداري', 'fas fa-arrows-alt-h', 1),
        ('ceiling_mount', 'تركيب سقفي', 'fas fa-arrow-up', 2),
        ('curtain_box', 'بيت ستارة', 'fas fa-box', 3),
        ('rod_only', 'قضيب فقط', 'fas fa-minus', 4),
    ]
    
    for value, display, icon, seq in installation_types:
        WizardFieldOption.objects.create(
            field_type='installation_type',
            value=value,
            display_name_ar=display,
            icon=icon,
            sequence=seq,
            is_active=True,
            is_default=(value == 'wall_mount')
        )


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0065_update_installation_type_field'),
    ]

    operations = [
        migrations.RunPython(
            update_installation_types,
            reverse_code=reverse_migration
        ),
    ]
