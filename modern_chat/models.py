from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import uuid

User = get_user_model()


class ChatRoom(models.Model):
    """غرفة الدردشة"""
    ROOM_TYPES = [
        ('private', 'خاص'),
        ('group', 'مجموعة'),
        ('public', 'عام'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name='اسم الغرفة')
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='private', verbose_name='نوع الغرفة')
    description = models.TextField(blank=True, null=True, verbose_name='الوصف')
    participants = models.ManyToManyField(User, related_name='chat_rooms', verbose_name='المشاركون')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms', verbose_name='منشئ الغرفة')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    
    class Meta:
        verbose_name = 'غرفة دردشة'
        verbose_name_plural = 'غرف الدردشة'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
    
    def get_last_message(self):
        """الحصول على آخر رسالة في الغرفة"""
        return self.messages.filter(is_deleted=False).order_by('-created_at').first()
    
    def get_unread_count(self, user):
        """عدد الرسائل غير المقروءة للمستخدم"""
        return self.messages.filter(
            is_deleted=False,
            created_at__gt=user.last_seen_at if hasattr(user, 'last_seen_at') else timezone.now()
        ).exclude(sender=user).count()


class Message(models.Model):
    """الرسالة"""
    MESSAGE_TYPES = [
        ('text', 'نص'),
        ('image', 'صورة'),
        ('file', 'ملف'),
        ('system', 'نظام'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages', verbose_name='الغرفة')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='المرسل')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text', verbose_name='نوع الرسالة')
    content = models.TextField(verbose_name='المحتوى')
    file = models.FileField(
        upload_to='chat_files/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'txt'])],
        verbose_name='الملف'
    )
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, verbose_name='رد على')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإرسال')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')
    is_edited = models.BooleanField(default=False, verbose_name='معدل')
    is_deleted = models.BooleanField(default=False, verbose_name='محذوف')
    
    class Meta:
        verbose_name = 'رسالة'
        verbose_name_plural = 'الرسائل'
        ordering = ['created_at']
    
    def __str__(self):
        return f'{self.sender.get_full_name()}: {self.content[:50]}...'


class MessageRead(models.Model):
    """قراءة الرسالة"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reads', verbose_name='الرسالة')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reads', verbose_name='المستخدم')
    read_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ القراءة')
    
    class Meta:
        verbose_name = 'قراءة رسالة'
        verbose_name_plural = 'قراءات الرسائل'
        unique_together = ['message', 'user']
    
    def __str__(self):
        return f'{self.user.get_full_name()} قرأ رسالة {self.message.id}'


class UserStatus(models.Model):
    """حالة المستخدم"""
    STATUS_CHOICES = [
        ('online', 'متصل'),
        ('away', 'غائب'),
        ('busy', 'مشغول'),
        ('offline', 'غير متصل'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_status', verbose_name='المستخدم')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='offline', verbose_name='الحالة')
    last_seen = models.DateTimeField(auto_now=True, verbose_name='آخر ظهور')
    is_typing_in = models.ForeignKey(ChatRoom, on_delete=models.SET_NULL, blank=True, null=True, verbose_name='يكتب في')
    
    class Meta:
        verbose_name = 'حالة مستخدم'
        verbose_name_plural = 'حالات المستخدمين'
    
    def __str__(self):
        return f'{self.user.get_full_name()} - {self.get_status_display()}'
