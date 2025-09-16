# Generated manually on 2025-09-09

from django.db import migrations


def create_default_resolution_methods(apps, schema_editor):
    """Create default resolution methods"""
    ResolutionMethod = apps.get_model('complaints', 'ResolutionMethod')
    
    default_methods = [
        {
            'name': 'حل فني مباشر',
            'description': 'حل المشكلة من خلال التدخل الفني المباشر وإصلاح العطل أو المشكلة',
            'order': 1
        },
        {
            'name': 'استبدال المنتج',
            'description': 'استبدال المنتج المعيب أو غير المطابق للمواصفات بمنتج جديد',
            'order': 2
        },
        {
            'name': 'تعويض مالي',
            'description': 'تقديم تعويض مالي للعميل عن الضرر أو الإزعاج الذي تعرض له',
            'order': 3
        },
        {
            'name': 'إعادة تنفيذ الخدمة',
            'description': 'إعادة تنفيذ الخدمة بالشكل الصحيح والمطلوب',
            'order': 4
        },
        {
            'name': 'استرداد نقود',
            'description': 'استرداد المبلغ المدفوع للعميل كاملاً أو جزئياً',
            'order': 5
        },
        {
            'name': 'اعادة تركيب',
            'description': 'إعادة تركيب المنتج أو الخدمة بالشكل الصحيح',
            'order': 6
        },
        {
            'name': 'تبديل قماش',
            'description': 'تبديل القماش أو المادة المستخدمة بمادة أخرى مناسبة',
            'order': 7
        }
    ]
    
    for method_data in default_methods:
        ResolutionMethod.objects.get_or_create(
            name=method_data['name'],
            defaults={
                'description': method_data['description'],
                'order': method_data['order'],
                'is_active': True
            }
        )


def reverse_default_resolution_methods(apps, schema_editor):
    """Remove default resolution methods"""
    ResolutionMethod = apps.get_model('complaints', 'ResolutionMethod')
    
    default_method_names = [
        'حل فني مباشر',
        'استبدال المنتج',
        'تعويض مالي',
        'إعادة تنفيذ الخدمة',
        'استرداد نقود',
        'اعادة تركيب',
        'تبديل قماش'
    ]
    
    ResolutionMethod.objects.filter(name__in=default_method_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('complaints', '0004_complaintupdate_resolution_method'),
    ]

    operations = [
        migrations.RunPython(
            create_default_resolution_methods,
            reverse_default_resolution_methods
        ),
    ]
