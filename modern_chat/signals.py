from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserStatus, Message, ChatRoom

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_status(sender, instance, created, **kwargs):
    """إنشاء حالة المستخدم عند إنشاء مستخدم جديد"""
    if created:
        UserStatus.objects.get_or_create(user=instance)


@receiver(post_save, sender=Message)
def update_room_timestamp(sender, instance, created, **kwargs):
    """تحديث وقت آخر نشاط في الغرفة عند إرسال رسالة جديدة"""
    if created and not instance.is_deleted:
        instance.room.save()  # سيحدث updated_at تلقائياً


@receiver(post_delete, sender=Message)
def update_room_on_message_delete(sender, instance, **kwargs):
    """تحديث الغرفة عند حذف رسالة"""
    if instance.room:
        instance.room.save()
