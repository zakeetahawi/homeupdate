"""
إعدادات Celery للمشروع
"""

import os
from celery import Celery
from django.conf import settings

# تعيين إعدادات Django الافتراضية لـ Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

# إنشاء تطبيق Celery
app = Celery('homeupdate')

# استخدام إعدادات Django لـ Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# إعدادات Celery المحسنة
app.conf.update(
    # إعدادات Redis
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    
    # إعدادات المهام
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Cairo',
    enable_utc=True,
    
    # إعدادات الأداء
    task_compression='gzip',
    result_compression='gzip',
    
    # إعدادات إعادة المحاولة
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # إعدادات انتهاء الصلاحية
    task_soft_time_limit=300,  # 5 دقائق
    task_time_limit=600,       # 10 دقائق
    result_expires=3600,       # ساعة واحدة
    
    # إعدادات المراقبة
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # إعدادات التوجيه
    task_routes={
        'orders.tasks.upload_contract_to_drive_async': {'queue': 'file_uploads'},
        'orders.tasks.upload_inspection_to_drive_async': {'queue': 'file_uploads'},
        'orders.tasks.calculate_order_totals_async': {'queue': 'calculations'},
        'orders.tasks.update_order_status_async': {'queue': 'status_updates'},
        'orders.tasks.cleanup_failed_uploads': {'queue': 'maintenance'},
    },
    
    # إعدادات المهام الدورية
    beat_schedule={
        'cleanup-failed-uploads': {
            'task': 'orders.tasks.cleanup_failed_uploads',
            'schedule': 3600.0,  # كل ساعة
            'options': {'queue': 'maintenance'}
        },
        'clear-expired-cache': {
            'task': 'orders.tasks.clear_expired_cache',
            'schedule': 7200.0,  # كل ساعتين
            'options': {'queue': 'maintenance'}
        },
    },
)

# اكتشاف المهام تلقائياً من جميع التطبيقات المثبتة
app.autodiscover_tasks()

# إعدادات إضافية للأمان والأداء
app.conf.update(
    # إعدادات الأمان
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # إعدادات الشبكة
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # إعدادات الذاكرة
    worker_max_memory_per_child=200000,  # 200MB
    worker_disable_rate_limits=False,
    
    # إعدادات التسجيل
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)


@app.task(bind=True)
def debug_task(self):
    """مهمة اختبار للتأكد من عمل Celery"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'


# دالة لاختبار اتصال Celery
def test_celery_connection():
    """اختبار اتصال Celery"""
    try:
        # إرسال مهمة اختبار
        result = debug_task.delay()
        
        # انتظار النتيجة لمدة 10 ثواني
        response = result.get(timeout=10)
        
        return {
            'status': 'success',
            'message': 'Celery يعمل بشكل طبيعي',
            'response': response,
            'task_id': result.id
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'خطأ في اتصال Celery: {str(e)}',
            'response': None,
            'task_id': None
        }


# دالة للحصول على إحصائيات Celery
def get_celery_stats():
    """الحصول على إحصائيات Celery"""
    try:
        from celery import current_app
        
        # الحصول على معلومات العمال
        inspect = current_app.control.inspect()
        
        stats = {
            'workers': {},
            'queues': {},
            'tasks': {}
        }
        
        # معلومات العمال
        active_workers = inspect.active()
        if active_workers:
            stats['workers']['active'] = len(active_workers)
            stats['workers']['details'] = active_workers
        else:
            stats['workers']['active'] = 0
            stats['workers']['details'] = {}
        
        # المهام النشطة
        active_tasks = inspect.active()
        if active_tasks:
            total_active_tasks = sum(len(tasks) for tasks in active_tasks.values())
            stats['tasks']['active'] = total_active_tasks
            stats['tasks']['details'] = active_tasks
        else:
            stats['tasks']['active'] = 0
            stats['tasks']['details'] = {}
        
        # المهام المجدولة
        scheduled_tasks = inspect.scheduled()
        if scheduled_tasks:
            total_scheduled_tasks = sum(len(tasks) for tasks in scheduled_tasks.values())
            stats['tasks']['scheduled'] = total_scheduled_tasks
        else:
            stats['tasks']['scheduled'] = 0
        
        # المهام المحجوزة
        reserved_tasks = inspect.reserved()
        if reserved_tasks:
            total_reserved_tasks = sum(len(tasks) for tasks in reserved_tasks.values())
            stats['tasks']['reserved'] = total_reserved_tasks
        else:
            stats['tasks']['reserved'] = 0
        
        return {
            'status': 'success',
            'stats': stats
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'خطأ في جلب إحصائيات Celery: {str(e)}',
            'stats': {}
        }


# دالة لإعادة تشغيل العمال
def restart_celery_workers():
    """إعادة تشغيل عمال Celery"""
    try:
        from celery import current_app
        
        # إرسال أمر إعادة التشغيل
        current_app.control.broadcast('pool_restart', arguments={'reload': True})
        
        return {
            'status': 'success',
            'message': 'تم إرسال أمر إعادة تشغيل العمال'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'خطأ في إعادة تشغيل العمال: {str(e)}'
        }


# دالة لتنظيف المهام المنتهية الصلاحية
def cleanup_expired_tasks():
    """تنظيف المهام المنتهية الصلاحية"""
    try:
        from celery import current_app
        
        # تنظيف النتائج المنتهية الصلاحية
        current_app.backend.cleanup()
        
        return {
            'status': 'success',
            'message': 'تم تنظيف المهام المنتهية الصلاحية'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'خطأ في تنظيف المهام: {str(e)}'
        }


# إعدادات إضافية للبيئة الإنتاجية
if not settings.DEBUG:
    # في بيئة الإنتاج، استخدم إعدادات أكثر صرامة
    app.conf.update(
        task_soft_time_limit=180,  # 3 دقائق
        task_time_limit=300,       # 5 دقائق
        worker_max_memory_per_child=150000,  # 150MB
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_disable_rate_limits=True,
    )


# تسجيل معلومات التهيئة
import logging
logger = logging.getLogger(__name__)
logger.info("تم تهيئة Celery بنجاح")
logger.info(f"Broker URL: {app.conf.broker_url}")
logger.info(f"Result Backend: {app.conf.result_backend}")
logger.info(f"Task Routes: {len(app.conf.task_routes)} routes configured")
logger.info(f"Beat Schedule: {len(app.conf.beat_schedule)} periodic tasks configured")
