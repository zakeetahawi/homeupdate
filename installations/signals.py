from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import InstallationSchedule, InstallationArchive
from accounts.middleware.current_user import get_current_user


@receiver(post_save, sender=InstallationSchedule)
def installation_status_changed(sender, instance, created, **kwargs):
    """معالجة تغيير حالة التركيب"""
    # الحصول على المستخدم الحالي من thread local storage
    current_user = get_current_user()

    # إنشاء أرشيف تلقائي إذا تم إكمال التركيب
    if not created and instance.status == 'completed':
        # التحقق من أن الحالة تغيرت إلى مكتملة
        old_status = getattr(instance, '_original_status', None)
        if old_status and old_status != 'completed':
            archive, created = InstallationArchive.objects.get_or_create(
                installation=instance,
                defaults={
                    'archived_by': current_user,
                    'archive_notes': f'تم الأرشفة تلقائياً عند إكمال التركيب بواسطة {current_user.get_full_name() or current_user.username if current_user else "نظام تلقائي"}'
                }
            )

            # تسجيل الأرشفة في سجل الأحداث
            if created and current_user:
                from .models import InstallationEventLog
                InstallationEventLog.objects.create(
                    installation=instance,
                    event_type='completion',
                    description=f'تم إكمال التركيب وأرشفته تلقائياً',
                    user=current_user,
                    metadata={
                        'auto_archived': True,
                        'completion_date': str(instance.completion_date),
                        'archived_by': current_user.get_full_name() or current_user.username
                    }
                )


@receiver(post_delete, sender=InstallationSchedule)
def installation_deleted(sender, instance, **kwargs):
    """معالجة حذف التركيب"""
    # يمكن إضافة منطق إضافي هنا عند الحاجة
    pass
