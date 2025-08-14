"""
نماذج نشاط المستخدمين
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from datetime import timedelta
import json

User = get_user_model()


class UserSession(models.Model):
    """نموذج لتتبع جلسات المستخدمين"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_user_sessions',
        verbose_name='المستخدم'
    )
    session_key = models.CharField(
        max_length=40,
        unique=True,
        verbose_name='مفتاح الجلسة'
    )
    ip_address = models.GenericIPAddressField(
        verbose_name='عنوان IP'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='معلومات المتصفح'
    )
    login_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='وقت الدخول'
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر نشاط'
    )
    logout_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='وقت الخروج'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )

    # معلومات إضافية عن الجلسة
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('desktop', 'سطح المكتب'),
            ('mobile', 'هاتف محمول'),
            ('tablet', 'جهاز لوحي'),
            ('unknown', 'غير معروف'),
        ],
        default='unknown',
        verbose_name='نوع الجهاز'
    )

    browser = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='المتصفح'
    )

    operating_system = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='نظام التشغيل'
    )

    class Meta:
        verbose_name = '💻 جلسة مستخدم'
        verbose_name_plural = '💻 جلسات المستخدمين'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', '-last_activity']),
            models.Index(fields=['is_active']),
            models.Index(fields=['session_key']),
            models.Index(fields=['login_time']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.login_time.strftime('%Y-%m-%d %H:%M')}"

    @property
    def duration(self):
        """مدة الجلسة"""
        end_time = self.logout_time or timezone.now()
        return end_time - self.login_time

    @property
    def is_online(self):
        """فحص ما إذا كان المستخدم متصل حالياً"""
        if not self.is_active:
            return False
        # اعتبار المستخدم متصل إذا كان آخر نشاط خلال آخر 5 دقائق
        return (timezone.now() - self.last_activity).total_seconds() < 300

    def end_session(self):
        """إنهاء الجلسة"""
        self.logout_time = timezone.now()
        self.is_active = False
        self.save(update_fields=['logout_time', 'is_active'])


class UserActivityLog(models.Model):
    """نموذج مفصل لتسجيل جميع أنشطة المستخدمين"""

    ACTION_TYPES = [
        ('login', 'تسجيل دخول'),
        ('logout', 'تسجيل خروج'),
        ('view', 'عرض صفحة'),
        ('create', 'إنشاء'),
        ('update', 'تحديث'),
        ('delete', 'حذف'),
        ('search', 'بحث'),
        ('export', 'تصدير'),
        ('import', 'استيراد'),
        ('download', 'تحميل'),
        ('upload', 'رفع ملف'),
        ('print', 'طباعة'),
        ('email', 'إرسال بريد إلكتروني'),
        ('api_call', 'استدعاء API'),
        ('error', 'خطأ'),
        ('security', 'أمان'),
        ('admin', 'إدارة'),
        ('report', 'تقرير'),
        ('backup', 'نسخ احتياطي'),
        ('restore', 'استعادة'),
        ('maintenance', 'صيانة'),
        ('other', 'أخرى'),
    ]

    ENTITY_TYPES = [
        ('user', 'مستخدم'),
        ('customer', 'عميل'),
        ('order', 'طلب'),
        ('product', 'منتج'),
        ('inspection', 'معاينة'),
        ('manufacturing', 'تصنيع'),
        ('installation', 'تركيب'),
        ('complaint', 'شكوى'),
        ('report', 'تقرير'),
        ('system', 'نظام'),
        ('file', 'ملف'),
        ('page', 'صفحة'),
        ('api', 'واجهة برمجية'),
        ('database', 'قاعدة بيانات'),
        ('other', 'أخرى'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_activity_logs',
        verbose_name='المستخدم'
    )

    session = models.ForeignKey(
        UserSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name='الجلسة'
    )

    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        verbose_name='نوع العملية'
    )

    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPES,
        default='other',
        verbose_name='نوع الكائن'
    )

    entity_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='معرف الكائن'
    )

    entity_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='اسم الكائن'
    )

    description = models.TextField(
        verbose_name='الوصف'
    )

    url_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='مسار الصفحة'
    )

    http_method = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='طريقة HTTP'
    )

    ip_address = models.GenericIPAddressField(
        verbose_name='عنوان IP'
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name='معلومات المتصفح'
    )

    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='بيانات إضافية'
    )

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='الوقت'
    )

    success = models.BooleanField(
        default=True,
        verbose_name='نجح'
    )

    error_message = models.TextField(
        blank=True,
        verbose_name='رسالة الخطأ'
    )

    class Meta:
        verbose_name = '📋 سجل نشاط'
        verbose_name_plural = '📋 سجلات النشاط'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action_type']),
            models.Index(fields=['entity_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['success']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    def get_icon(self):
        """إرجاع أيقونة حسب نوع العملية"""
        icons = {
            'login': '🔑',
            'logout': '🚪',
            'view': '👁️',
            'create': '➕',
            'update': '✏️',
            'delete': '🗑️',
            'search': '🔍',
            'export': '📤',
            'import': '📥',
            'download': '⬇️',
            'upload': '⬆️',
            'print': '🖨️',
            'email': '📧',
            'api_call': '🔌',
            'error': '❌',
            'security': '🔒',
            'admin': '⚙️',
            'report': '📊',
            'backup': '💾',
            'restore': '🔄',
            'maintenance': '🔧',
            'other': '📝',
        }
        return icons.get(self.action_type, '📝')

    @classmethod
    def log_activity(cls, user, action_type, description, **kwargs):
        """طريقة مساعدة لتسجيل النشاط"""
        try:
            # الحصول على الجلسة الحالية إن وجدت
            session = None
            if hasattr(user, '_current_session'):
                session = user._current_session

            # إنشاء سجل النشاط
            activity = cls.objects.create(
                user=user,
                session=session,
                action_type=action_type,
                description=description,
                **kwargs
            )
            return activity
        except Exception as e:
            # في حالة فشل التسجيل، لا نريد أن نعطل العملية الأساسية
            print(f"خطأ في تسجيل النشاط: {e}")
            return None


class OnlineUser(models.Model):
    """نموذج لتتبع المستخدمين المتصلين حالياً"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='activity_online_status',
        verbose_name='المستخدم'
    )

    last_seen = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر ظهور'
    )

    current_page = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='الصفحة الحالية'
    )

    current_page_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='عنوان الصفحة الحالية'
    )

    ip_address = models.GenericIPAddressField(
        verbose_name='عنوان IP'
    )

    session_key = models.CharField(
        max_length=40,
        verbose_name='مفتاح الجلسة'
    )

    # معلومات الجهاز
    device_info = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='معلومات الجهاز'
    )

    # إحصائيات الجلسة الحالية
    pages_visited = models.PositiveIntegerField(
        default=0,
        verbose_name='عدد الصفحات المزارة'
    )

    actions_performed = models.PositiveIntegerField(
        default=0,
        verbose_name='عدد العمليات المنجزة'
    )

    login_time = models.DateTimeField(
        verbose_name='وقت الدخول'
    )

    class Meta:
        verbose_name = '🟢 مستخدم نشط'
        verbose_name_plural = '🟢 المستخدمون النشطون'
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['-last_seen']),
            models.Index(fields=['session_key']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.username} - متصل"

    @property
    def is_online(self):
        """فحص ما إذا كان المستخدم متصل حالياً"""
        # اعتبار المستخدم متصل إذا كان آخر نشاط خلال آخر 5 دقائق
        return (timezone.now() - self.last_seen).total_seconds() < 300

    @property
    def online_duration(self):
        """مدة الاتصال الحالية"""
        return timezone.now() - self.login_time

    @property
    def online_duration_formatted(self):
        """مدة الاتصال منسقة"""
        duration = self.online_duration
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60

        if hours > 0:
            return f"{hours} ساعة و {minutes} دقيقة"
        else:
            return f"{minutes} دقيقة"

    def update_activity(self, page_path=None, page_title=None, action_performed=False):
        """تحديث نشاط المستخدم"""
        self.last_seen = timezone.now()

        if page_path:
            self.current_page = page_path
            self.pages_visited += 1

        if page_title:
            self.current_page_title = page_title

        if action_performed:
            self.actions_performed += 1

        self.save(update_fields=['last_seen', 'current_page', 'current_page_title', 'pages_visited', 'actions_performed'])

    @classmethod
    def get_online_users(cls):
        """الحصول على المستخدمين المتصلين حالياً"""
        # تنظيف المستخدمين غير المتصلين أولاً
        cls.cleanup_offline_users()

        # إرجاع المستخدمين النشطين
        return cls.objects.filter(
            last_seen__gte=timezone.now() - timedelta(minutes=5)
        ).select_related('user')

    @classmethod
    def cleanup_offline_users(cls):
        """تنظيف المستخدمين غير المتصلين"""
        offline_threshold = timezone.now() - timedelta(minutes=5)
        cls.objects.filter(last_seen__lt=offline_threshold).delete()

    @classmethod
    def update_user_activity(cls, user, request, page_title=None, action_performed=False):
        """تحديث أو إنشاء سجل المستخدم النشط"""
        try:
            online_user, created = cls.objects.get_or_create(
                user=user,
                defaults={
                    'ip_address': cls.get_client_ip(request),
                    'session_key': request.session.session_key or '',
                    'login_time': timezone.now(),
                    'current_page': request.path,
                    'current_page_title': page_title or '',
                    'device_info': cls.get_device_info(request),
                }
            )

            if not created:
                online_user.update_activity(
                    page_path=request.path,
                    page_title=page_title,
                    action_performed=action_performed
                )

            return online_user
        except Exception as e:
            print(f"خطأ في تحديث نشاط المستخدم: {e}")
            return None

    @staticmethod
    def get_client_ip(request):
        """الحصول على عنوان IP الحقيقي للعميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def get_device_info(request):
        """الحصول على معلومات الجهاز"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        return {
            'user_agent': user_agent,
            'accept_language': request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            'accept_encoding': request.META.get('HTTP_ACCEPT_ENCODING', ''),
        }


class UserLoginHistory(models.Model):
    """نموذج لتسجيل تاريخ تسجيل الدخول"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_login_history',
        verbose_name='المستخدم'
    )

    login_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='وقت الدخول'
    )

    logout_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='وقت الخروج'
    )

    ip_address = models.GenericIPAddressField(
        verbose_name='عنوان IP'
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name='معلومات المتصفح'
    )

    session_key = models.CharField(
        max_length=40,
        verbose_name='مفتاح الجلسة'
    )

    # معلومات الجهاز والمتصفح
    browser = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='المتصفح'
    )

    operating_system = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='نظام التشغيل'
    )

    device_type = models.CharField(
        max_length=20,
        choices=[
            ('desktop', 'سطح المكتب'),
            ('mobile', 'هاتف محمول'),
            ('tablet', 'جهاز لوحي'),
            ('unknown', 'غير معروف'),
        ],
        default='unknown',
        verbose_name='نوع الجهاز'
    )

    # إحصائيات الجلسة
    pages_visited = models.PositiveIntegerField(
        default=0,
        verbose_name='عدد الصفحات المزارة'
    )

    actions_performed = models.PositiveIntegerField(
        default=0,
        verbose_name='عدد العمليات المنجزة'
    )

    # حالة الجلسة
    is_successful_login = models.BooleanField(
        default=True,
        verbose_name='تسجيل دخول ناجح'
    )

    logout_reason = models.CharField(
        max_length=50,
        choices=[
            ('manual', 'خروج يدوي'),
            ('timeout', 'انتهاء المهلة'),
            ('forced', 'خروج قسري'),
            ('system', 'خروج النظام'),
            ('unknown', 'غير معروف'),
        ],
        default='unknown',
        blank=True,
        verbose_name='سبب الخروج'
    )

    class Meta:
        verbose_name = '🔐 سجل دخول'
        verbose_name_plural = '🔐 سجلات الدخول'
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', '-login_time']),
            models.Index(fields=['login_time']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['is_successful_login']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.login_time.strftime('%Y-%m-%d %H:%M')}"

    @property
    def session_duration(self):
        """مدة الجلسة"""
        if self.logout_time:
            return self.logout_time - self.login_time
        return timezone.now() - self.login_time

    @property
    def session_duration_formatted(self):
        """مدة الجلسة منسقة"""
        duration = self.session_duration
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60

        if duration.days > 0:
            return f"{duration.days} يوم و {hours} ساعة"
        elif hours > 0:
            return f"{hours} ساعة و {minutes} دقيقة"
        else:
            return f"{minutes} دقيقة"

    def end_session(self, reason='manual'):
        """إنهاء الجلسة"""
        self.logout_time = timezone.now()
        self.logout_reason = reason
        self.save(update_fields=['logout_time', 'logout_reason'])

    @classmethod
    def create_login_record(cls, user, request, is_successful=True):
        """إنشاء سجل تسجيل دخول جديد"""
        try:
            return cls.objects.create(
                user=user,
                ip_address=OnlineUser.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_key=request.session.session_key or '',
                browser=cls.extract_browser(request.META.get('HTTP_USER_AGENT', '')),
                operating_system=cls.extract_os(request.META.get('HTTP_USER_AGENT', '')),
                device_type=cls.extract_device_type(request.META.get('HTTP_USER_AGENT', '')),
                is_successful_login=is_successful,
            )
        except Exception as e:
            print(f"خطأ في إنشاء سجل تسجيل الدخول: {e}")
            return None

    @staticmethod
    def extract_browser(user_agent):
        """استخراج اسم المتصفح من user agent"""
        user_agent = user_agent.lower()
        if 'chrome' in user_agent:
            return 'Chrome'
        elif 'firefox' in user_agent:
            return 'Firefox'
        elif 'safari' in user_agent:
            return 'Safari'
        elif 'edge' in user_agent:
            return 'Edge'
        elif 'opera' in user_agent:
            return 'Opera'
        else:
            return 'Unknown'

    @staticmethod
    def extract_os(user_agent):
        """استخراج نظام التشغيل من user agent"""
        user_agent = user_agent.lower()
        if 'windows' in user_agent:
            return 'Windows'
        elif 'mac' in user_agent:
            return 'macOS'
        elif 'linux' in user_agent:
            return 'Linux'
        elif 'android' in user_agent:
            return 'Android'
        elif 'ios' in user_agent:
            return 'iOS'
        else:
            return 'Unknown'

    @staticmethod
    def extract_device_type(user_agent):
        """استخراج نوع الجهاز من user agent"""
        user_agent = user_agent.lower()
        if 'mobile' in user_agent or 'android' in user_agent:
            return 'mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            return 'tablet'
        else:
            return 'desktop'
