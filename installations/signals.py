from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import InstallationSchedule, InstallationArchive


@receiver(post_save, sender=InstallationSchedule)
def installation_status_changed(sender, instance, created, **kwargs):
    """معالجة تغيير حالة التركيب"""
    if not created and instance.status == 'completed':
        # إنشاء أرشيف تلقائياً عند إكمال التركيب
        InstallationArchive.objects.get_or_create(
            installation=instance,
            defaults={'archived_by': get_user_model().objects.first()}  # سيتم تحديثه لاحقاً
        )


@receiver(post_delete, sender=InstallationSchedule)
def installation_deleted(sender, instance, **kwargs):
    """معالجة حذف التركيب"""
    # يمكن إضافة منطق إضافي هنا عند الحاجة
    pass
