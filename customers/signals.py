from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import CustomerType, get_customer_types

@receiver([post_save, post_delete], sender=CustomerType)
def update_customer_type_choices(sender, instance=None, **kwargs):
    """تحديث قائمة أنواع العملاء عند إضافة أو تعديل أو حذف نوع"""
    # مسح الذاكرة المؤقتة
    cache.delete('customer_types_choices')

    # إعادة تحميل الخيارات من قاعدة البيانات
    from .models import CustomerType
    cache_key = 'customer_types_choices'
    types = [(t.code, t.name) for t in CustomerType.objects.filter(is_active=True).order_by('name')]
    cache.set(cache_key, types, timeout=3600)
