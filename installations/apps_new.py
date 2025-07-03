"""
إعدادات تطبيق التركيبات الجديد
"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InstallationsNewConfig(AppConfig):
    """إعدادات تطبيق التركيبات الجديد"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'installations'
    verbose_name = _('نظام التركيبات المتقدم')
    
    def ready(self):
        """تشغيل الإعدادات عند تحميل التطبيق"""
        
        # استيراد الإشارات
        try:
            from . import signals_new
        except ImportError:
            pass
        
        # تسجيل المهام المجدولة
        self.register_scheduled_tasks()
        
        # إعداد نظام الإنذارات
        self.setup_alert_system()
        
        # إعداد نظام التحليلات
        self.setup_analytics()
    
    def register_scheduled_tasks(self):
        """تسجيل المهام المجدولة باستخدام Django فقط"""

        try:
            # إنشاء مهام مجدولة باستخدام Django management commands
            from django.core.management import call_command
            import threading
            import time

            # بدء خيط للمهام المجدولة
            def run_scheduled_tasks():
                while True:
                    try:
                        # فحص الإنذارات كل ساعة
                        call_command('check_alerts')
                        time.sleep(3600)  # ساعة واحدة
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"خطأ في المهام المجدولة: {e}")
                        time.sleep(300)  # 5 دقائق عند الخطأ

            # تشغيل المهام في خيط منفصل
            task_thread = threading.Thread(target=run_scheduled_tasks, daemon=True)
            task_thread.start()

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"فشل في تسجيل المهام المجدولة: {e}")
    
    def setup_alert_system(self):
        """إعداد نظام الإنذارات"""
        
        try:
            from .services.alert_system import AlertSystem
            
            # فحص الإنذارات عند بدء التشغيل
            AlertSystem.check_all_alerts()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"فشل في إعداد نظام الإنذارات: {e}")
    
    def setup_analytics(self):
        """إعداد نظام التحليلات"""
        
        try:
            from .services.analytics_engine import AnalyticsEngine
            
            # يمكن إضافة إعدادات التحليلات هنا
            pass
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"فشل في إعداد نظام التحليلات: {e}")


# إعدادات إضافية للتطبيق
INSTALLATION_SETTINGS = {
    # حدود النظام
    'MAX_DAILY_INSTALLATIONS': 13,
    'MAX_TECHNICIAN_WINDOWS': 20,
    'WARNING_TECHNICIAN_WINDOWS': 18,
    
    # أوقات العمل
    'WORK_START_TIME': '08:00',
    'WORK_END_TIME': '17:00',
    'WORK_DAYS': [5, 6, 0, 1, 2],  # السبت-الأربعاء
    
    # إعدادات الإنذارات
    'ALERT_SETTINGS': {
        'ENABLE_EMAIL_ALERTS': True,
        'ENABLE_SMS_ALERTS': False,
        'CRITICAL_ALERT_RECIPIENTS': [],
        'ALERT_CHECK_INTERVAL': 3600,  # ثانية
    },
    
    # إعدادات التقارير
    'REPORT_SETTINGS': {
        'DEFAULT_EXPORT_FORMAT': 'pdf',
        'INCLUDE_PHOTOS_IN_REPORTS': False,
        'AUTO_GENERATE_DAILY_REPORTS': True,
        'REPORT_RETENTION_DAYS': 365,
    },
    
    # إعدادات الجودة
    'QUALITY_SETTINGS': {
        'REQUIRE_QUALITY_RATING': True,
        'REQUIRE_CUSTOMER_SATISFACTION': True,
        'MIN_QUALITY_THRESHOLD': 3,
        'ENABLE_QUALITY_ALERTS': True,
    },
    
    # إعدادات التحليلات
    'ANALYTICS_SETTINGS': {
        'ENABLE_PREDICTIVE_ANALYTICS': True,
        'ANALYTICS_RETENTION_DAYS': 730,
        'ENABLE_REAL_TIME_ANALYTICS': True,
        'CACHE_ANALYTICS_MINUTES': 15,
    },
    
    # إعدادات التكامل
    'INTEGRATION_SETTINGS': {
        'ENABLE_LEGACY_SYNC': True,
        'SYNC_INTERVAL_MINUTES': 30,
        'ENABLE_API_ACCESS': True,
        'API_RATE_LIMIT': 1000,  # طلبات في الساعة
    },
}


def get_installation_setting(key, default=None):
    """الحصول على إعداد من إعدادات التركيبات"""
    
    from django.conf import settings
    
    # البحث في إعدادات Django أولاً
    django_settings = getattr(settings, 'INSTALLATION_SETTINGS', {})
    if key in django_settings:
        return django_settings[key]
    
    # البحث في الإعدادات الافتراضية
    keys = key.split('.')
    value = INSTALLATION_SETTINGS
    
    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default


def update_installation_setting(key, value):
    """تحديث إعداد في إعدادات التركيبات"""
    
    # يمكن إضافة منطق لحفظ الإعدادات في قاعدة البيانات
    # أو ملف إعدادات منفصل
    pass


# معالج الإشارات للتطبيق
class InstallationSignalHandler:
    """معالج إشارات التطبيق"""
    
    @staticmethod
    def handle_installation_created(sender, instance, created, **kwargs):
        """معالجة إنشاء تركيب جديد"""
        
        if created:
            # إنشاء إنذار إذا كان اليوم مزدحماً
            from .services.alert_system import AlertSystem
            AlertSystem.check_daily_capacity_alerts(instance.scheduled_date)
    
    @staticmethod
    def handle_installation_updated(sender, instance, **kwargs):
        """معالجة تحديث التركيب"""
        
        # فحص الإنذارات عند تغيير الحالة
        if instance.status == 'completed':
            from .services.order_completion import OrderCompletionService
            # يمكن إضافة منطق إضافي هنا
    
    @staticmethod
    def handle_team_updated(sender, instance, **kwargs):
        """معالجة تحديث الفريق"""
        
        # إعادة حساب توزيع الأحمال
        pass


# تسجيل معالجات الإشارات
def register_signal_handlers():
    """تسجيل معالجات الإشارات"""
    
    from django.db.models.signals import post_save, post_delete
    from .models_new import InstallationNew, InstallationTeamNew
    
    post_save.connect(
        InstallationSignalHandler.handle_installation_created,
        sender=InstallationNew
    )
    
    post_save.connect(
        InstallationSignalHandler.handle_installation_updated,
        sender=InstallationNew
    )
    
    post_save.connect(
        InstallationSignalHandler.handle_team_updated,
        sender=InstallationTeamNew
    )
