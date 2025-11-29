"""
نظام تتبع شامل لجميع العمليات الحساسة
Audit Trail متقدم
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class AuditLog(models.Model):
    """
    سجل تدقيق شامل لجميع العمليات
    """
    
    ACTION_TYPES = (
        ('CREATE', 'إنشاء'),
        ('UPDATE', 'تحديث'),
        ('DELETE', 'حذف'),
        ('LOGIN', 'تسجيل دخول'),
        ('LOGOUT', 'تسجيل خروج'),
        ('PERMISSION_CHANGE', 'تغيير صلاحيات'),
        ('SECURITY_EVENT', 'حدث أمني'),
        ('DATA_EXPORT', 'تصدير بيانات'),
        ('SETTINGS_CHANGE', 'تغيير إعدادات'),
    )
    
    SEVERITY_LEVELS = (
        ('INFO', 'معلومات'),
        ('WARNING', 'تحذير'),
        ('ERROR', 'خطأ'),
        ('CRITICAL', 'حرج'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='المستخدم'
    )
    action = models.CharField(
        max_length=50, 
        choices=ACTION_TYPES,
        verbose_name='نوع العملية'
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='INFO',
        verbose_name='مستوى الخطورة'
    )
    model_name = models.CharField(
        max_length=100, 
        null=True,
        verbose_name='اسم النموذج'
    )
    object_id = models.PositiveIntegerField(
        null=True,
        verbose_name='معرف الكائن'
    )
    description = models.TextField(
        verbose_name='الوصف'
    )
    old_value = models.JSONField(
        null=True,
        blank=True,
        verbose_name='القيمة القديمة'
    )
    new_value = models.JSONField(
        null=True,
        blank=True,
        verbose_name='القيمة الجديدة'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        verbose_name='عنوان IP'
    )
    user_agent = models.TextField(
        null=True,
        verbose_name='User Agent'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='التاريخ والوقت'
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        verbose_name='مفتاح الجلسة'
    )
    
    class Meta:
        verbose_name = 'سجل تدقيق'
        verbose_name_plural = 'سجلات التدقيق'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['severity', '-timestamp']),
        ]
    
    def __str__(self):
        return f'{self.user} - {self.get_action_display()} - {self.timestamp}'
    
    @classmethod
    def log(cls, user, action, description, **kwargs):
        """
        تسجيل حدث في سجل التدقيق
        
        Args:
            user: المستخدم
            action: نوع العملية
            description: الوصف
            **kwargs: معاملات إضافية
        """
        return cls.objects.create(
            user=user,
            action=action,
            description=description,
            **kwargs
        )


class SecurityEvent(models.Model):
    """
    سجل الأحداث الأمنية
    """
    
    EVENT_TYPES = (
        ('LOGIN_FAILED', 'فشل تسجيل دخول'),
        ('LOGIN_SUCCESS', 'نجاح تسجيل دخول'),
        ('BRUTE_FORCE', 'محاولة Brute Force'),
        ('SQL_INJECTION', 'محاولة SQL Injection'),
        ('XSS_ATTEMPT', 'محاولة XSS'),
        ('CSRF_FAILED', 'فشل CSRF'),
        ('RATE_LIMIT', 'تجاوز Rate Limit'),
        ('SUSPICIOUS_ACTIVITY', 'نشاط مشبوه'),
        ('PERMISSION_DENIED', 'رفض صلاحيات'),
    )
    
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        verbose_name='نوع الحدث'
    )
    ip_address = models.GenericIPAddressField(
        verbose_name='عنوان IP'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='المستخدم'
    )
    details = models.JSONField(
        default=dict,
        verbose_name='التفاصيل'
    )
    user_agent = models.TextField(
        null=True,
        verbose_name='User Agent'
    )
    url = models.URLField(
        max_length=500,
        null=True,
        verbose_name='URL'
    )
    method = models.CharField(
        max_length=10,
        null=True,
        verbose_name='HTTP Method'
    )
    blocked = models.BooleanField(
        default=False,
        verbose_name='تم الحظر'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='التاريخ والوقت'
    )
    
    class Meta:
        verbose_name = 'حدث أمني'
        verbose_name_plural = 'الأحداث الأمنية'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]
    
    def __str__(self):
        return f'{self.get_event_type_display()} - {self.ip_address} - {self.timestamp}'
    
    @classmethod
    def log_event(cls, event_type, ip_address, **kwargs):
        """
        تسجيل حدث أمني
        """
        return cls.objects.create(
            event_type=event_type,
            ip_address=ip_address,
            **kwargs
        )


# Middleware للـ Audit Logging
class AuditLoggingMiddleware:
    """
    Middleware لتسجيل جميع العمليات الحساسة
    """
    
    SENSITIVE_PATHS = [
        '/admin/',
        '/accounts/login/',
        '/accounts/logout/',
        '/api/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # تسجيل قبل المعالجة
        should_log = any(
            request.path.startswith(path) 
            for path in self.SENSITIVE_PATHS
        )
        
        if should_log and request.user.is_authenticated:
            self.log_request(request)
        
        response = self.get_response(request)
        
        return response
    
    def log_request(self, request):
        """تسجيل الطلب"""
        try:
            AuditLog.log(
                user=request.user,
                action='SECURITY_EVENT',
                description=f'وصول إلى: {request.path}',
                severity='INFO',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                session_key=request.session.session_key,
            )
        except:
            pass
    
    def get_client_ip(self, request):
        """الحصول على IP العميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# دالة مساعدة للاستخدام
def log_audit(user, action, description, **kwargs):
    """
    تسجيل سريع في سجل التدقيق
    
    Usage:
        from core.audit import log_audit
        
        log_audit(
            user=request.user,
            action='CREATE',
            description='إنشاء طلب جديد',
            model_name='Order',
            object_id=order.id
        )
    """
    return AuditLog.log(user, action, description, **kwargs)


def log_security_event(event_type, ip_address, **kwargs):
    """
    تسجيل سريع لحدث أمني
    
    Usage:
        from core.audit import log_security_event
        
        log_security_event(
            'SQL_INJECTION',
            request.META.get('REMOTE_ADDR'),
            user=request.user,
            details={'query': bad_query}
        )
    """
    return SecurityEvent.log_event(event_type, ip_address, **kwargs)
