# إعدادات قسم التركيبات

# إعدادات الوسائط
MEDIA_URL = '/media/'
MEDIA_ROOT = 'media/'

# إعدادات الملفات المرفوعة
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.gif']

# إعدادات الجدولة
DEFAULT_INSTALLATION_TIME = '09:00'
DEFAULT_INSTALLATION_DURATION = 120  # دقائق

# حالات التركيب
INSTALLATION_STATUS_CHOICES = [
    ('pending', 'في الانتظار'),
    ('scheduled', 'مجدول'),
    ('in_progress', 'قيد التنفيذ'),
    ('completed', 'مكتمل'),
    ('cancelled', 'ملغي'),
    ('rescheduled', 'إعادة جدولة'),
]

# أنواع الدفع
PAYMENT_TYPE_CHOICES = [
    ('remaining', 'المتبقي'),
    ('additional', 'إضافي'),
    ('refund', 'استرداد'),
]

# طرق الدفع
PAYMENT_METHOD_CHOICES = [
    ('cash', 'نقداً'),
    ('card', 'بطاقة ائتمان'),
    ('bank_transfer', 'تحويل بنكي'),
    ('check', 'شيك'),
    ('other', 'أخرى'),
]

# إعدادات الإشعارات
NOTIFICATION_ENABLED = True
NOTIFICATION_TYPES = [
    'installation_scheduled',
    'installation_started',
    'installation_completed',
    'payment_received',
    'modification_report',
]

# إعدادات التقارير
REPORT_TYPES = [
    'daily_schedule',
    'team_performance',
    'payment_summary',
    'installation_summary',
]

# إعدادات الأرشيف
ARCHIVE_AFTER_DAYS = 30
AUTO_ARCHIVE_ENABLED = True

# إعدادات البحث
SEARCH_FIELDS = [
    'order__order_number',
    'order__customer__name',
    'order__customer__phone',
    'team__name',
    'notes',
]

# إعدادات الفلترة
FILTER_OPTIONS = {
    'status': INSTALLATION_STATUS_CHOICES,
    'team': 'InstallationTeam',
    'date_range': 30,  # أيام
}

# إعدادات الطباعة
PRINT_TEMPLATES = {
    'daily_schedule': 'installations/print_daily_schedule.html',
    'installation_detail': 'installations/print_installation_detail.html',
    'team_schedule': 'installations/print_team_schedule.html',
}

# إعدادات الأمان
SECURITY_SETTINGS = {
    'require_authentication': True,
    'require_permissions': True,
    'log_all_actions': True,
    'file_upload_validation': True,
}

# إعدادات الأداء
PERFORMANCE_SETTINGS = {
    'cache_enabled': True,
    'cache_timeout': 300,  # ثوان
    'pagination_size': 20,
    'auto_refresh_interval': 30,  # ثوان
}

# إعدادات التكامل
INTEGRATION_SETTINGS = {
    'manufacturing_sync': True,
    'customer_notifications': True,
    'sms_notifications': False,
    'email_notifications': True,
}

# إعدادات التخصيص
CUSTOMIZATION_SETTINGS = {
    'theme_color': '#667eea',
    'secondary_color': '#764ba2',
    'logo_path': 'static/img/logo.png',
    'company_name': 'شركة التركيبات',
}

# إعدادات التطوير
DEBUG_SETTINGS = {
    'debug_mode': False,
    'log_level': 'INFO',
    'show_sql_queries': False,
    'enable_profiling': False,
} 