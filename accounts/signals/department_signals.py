"""
Signals لإدارة الأقسام بشكل تلقائي
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import Department


@receiver(post_save, sender=Department)
def auto_enable_department_navbar_visibility(sender, instance, created, **kwargs):
    """
    تفعيل حقل show_* التلقائي للأقسام والوحدات الجديدة
    بناءً على code القسم أو القسم الأب
    """
    if created and instance.is_core:
        # خريطة الأقسام وحقول show_* المرتبطة بها
        department_mapping = {
            'customers': 'show_customers',
            'orders': 'show_orders',
            'inventory': 'show_inventory',
            'inspections': 'show_inspections',
            'installations': 'show_installations',
            'manufacturing': 'show_manufacturing',
            'complaints': 'show_complaints',
            'reports': 'show_reports',
            'accounting': 'show_accounting',
            'database': 'show_database',
            'cutting': 'show_inventory',  # التقطيع يظهر في المخزون
        }
        
        # إذا كان قسم رئيسي
        if not instance.parent and instance.code in department_mapping:
            field_name = department_mapping[instance.code]
            setattr(instance, field_name, True)
            instance.save(update_fields=[field_name])
        
        # إذا كان وحدة فرعية
        elif instance.parent and instance.parent.code in department_mapping:
            field_name = department_mapping[instance.parent.code]
            setattr(instance, field_name, True)
            instance.save(update_fields=[field_name])
