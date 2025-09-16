import os
import psutil
import time
import logging
from django.conf import settings
from django.core.cache import cache
from threading import Thread
from functools import wraps

logger = logging.getLogger('resource_tracker')

class ResourceTracker:
    """
    متتبع موارد النظام للمساعدة في تحسين الأداء
    """
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self._start_monitoring()

    def _start_monitoring(self):
        """
        بدء مراقبة موارد النظام في خيط منفصل
        """
        self.monitoring = True
        self.monitor_thread = Thread(target=self._monitor_resources)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def _monitor_resources(self):
        """
        مراقبة موارد النظام وتسجيل التحذيرات عند تجاوز الحدود
        """
        while self.monitoring:
            try:
                # مراقبة استخدام الذاكرة
                memory_percent = self.process.memory_percent()
                if memory_percent > 80:  # تحذير عند تجاوز 80%
                    logger.warning(f'High memory usage: {memory_percent:.1f}%')

                # مراقبة استخدام المعالج
                cpu_percent = self.process.cpu_percent(interval=1)
                if cpu_percent > 80:  # تحذير عند تجاوز 80%
                    logger.warning(f'High CPU usage: {cpu_percent:.1f}%')

                # مراقبة عدد الاتصالات النشطة
                connections = len(self.process.connections())
                if connections > 500:  # تحذير عند تجاوز 500 اتصال
                    logger.warning(f'High number of connections: {connections}')

                # تخزين القياسات في الذاكرة المؤقتة
                stats = {
                    'memory_percent': memory_percent,
                    'cpu_percent': cpu_percent,
                    'connections': connections,
                    'timestamp': time.time()
                }
                cache.set('system_resources', stats, 300)  # تخزين لمدة 5 دقائق

            except Exception as e:
                logger.error(f'Error monitoring resources: {str(e)}')

            time.sleep(60)  # انتظار دقيقة قبل القياس التالي

    def stop_monitoring(self):
        """
        إيقاف مراقبة الموارد
        """
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join()

def track_resource_usage(func):
    """
    مزخرف لتتبع استخدام الموارد في الدوال
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process(os.getpid()).memory_info().rss

        result = func(*args, **kwargs)

        end_time = time.time()
        end_memory = psutil.Process(os.getpid()).memory_info().rss
        duration = end_time - start_time
        memory_diff = end_memory - start_memory

        # تسجيل العمليات التي تستغرق وقتاً طويلاً أو تستهلك ذاكرة كبيرة
        if duration > 1.0 or memory_diff > 10 * 1024 * 1024:  # أكثر من ثانية أو 10 ميجابايت
            logger.warning(
                f'Resource intensive operation - Function: {func.__name__}, '
                f'Duration: {duration:.2f}s, Memory diff: {memory_diff/1024/1024:.2f}MB'
            )

        return result
    return wrapper

# إنشاء نسخة عامة من متتبع الموارد
resource_tracker = ResourceTracker()

def cleanup_resources():
    """
    تنظيف الموارد عند إيقاف التطبيق
    """
    resource_tracker.stop_monitoring()
    logger.info('Resource tracking stopped')