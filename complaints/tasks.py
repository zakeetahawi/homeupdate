"""
مهام Celery لنظام الشكاوى
"""

from celery import shared_task
from django.db import connection, connections
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging
import gc

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def cleanup_database_connections(self):
    """
    تنظيف اتصالات قاعدة البيانات الخاملة
    """
    try:
        cleaned_connections = 0
        
        # إغلاق جميع الاتصالات الخاملة
        for alias in connections:
            conn = connections[alias]
            if conn.connection is not None:
                if hasattr(conn.connection, 'get_transaction_status'):
                    # PostgreSQL specific
                    import psycopg2.extensions
                    if conn.connection.get_transaction_status() == psycopg2.extensions.TRANSACTION_STATUS_IDLE:
                        conn.close()
                        cleaned_connections += 1
                else:
                    # عام لجميع قواعد البيانات
                    conn.close()
                    cleaned_connections += 1
        
        # تنظيف الذاكرة
        gc.collect()
        
        logger.info(f"تم تنظيف {cleaned_connections} اتصال خامل")
        
        return {
            'success': True,
            'cleaned_connections': cleaned_connections,
            'message': f'تم تنظيف {cleaned_connections} اتصال خامل'
        }
        
    except Exception as e:
        logger.error(f"خطأ في تنظيف الاتصالات: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'فشل في تنظيف الاتصالات'
        }


@shared_task(bind=True)
def cleanup_expired_cache(self):
    """
    تنظيف التخزين المؤقت المنتهي الصلاحية
    """
    try:
        # تنظيف cache الافتراضي
        cache.clear()
        
        logger.info("تم تنظيف التخزين المؤقت")
        
        return {
            'success': True,
            'message': 'تم تنظيف التخزين المؤقت بنجاح'
        }
        
    except Exception as e:
        logger.error(f"خطأ في تنظيف التخزين المؤقت: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'فشل في تنظيف التخزين المؤقت'
        }


@shared_task(bind=True)
def monitor_database_connections(self):
    """
    مراقبة اتصالات قاعدة البيانات
    """
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # فحص عدد الاتصالات النشطة
            cursor.execute("""
                SELECT count(*) as total_connections,
                       count(*) FILTER (WHERE state = 'active') as active_connections,
                       count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """)
            
            result = cursor.fetchone()
            total_connections = result[0]
            active_connections = result[1]
            idle_connections = result[2]
            
            logger.info(f"اتصالات قاعدة البيانات - المجموع: {total_connections}, النشطة: {active_connections}, الخاملة: {idle_connections}")
            
            # تحذير إذا كان عدد الاتصالات مرتفع
            if total_connections > 50:
                logger.warning(f"عدد الاتصالات مرتفع: {total_connections}")
                
                # تنظيف الاتصالات الخاملة إذا كان العدد مرتفع
                if idle_connections > 20:
                    cleanup_database_connections.delay()
            
            return {
                'success': True,
                'total_connections': total_connections,
                'active_connections': active_connections,
                'idle_connections': idle_connections,
                'message': f'المجموع: {total_connections}, النشطة: {active_connections}, الخاملة: {idle_connections}'
            }
            
    except Exception as e:
        logger.error(f"خطأ في مراقبة الاتصالات: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'فشل في مراقبة الاتصالات'
        }


@shared_task(bind=True)
def restart_celery_workers_if_needed(self):
    """
    إعادة تشغيل عمال Celery إذا لزم الأمر
    """
    try:
        from celery import current_app
        
        # فحص حالة العمال
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        
        if not stats:
            logger.warning("لا يوجد عمال Celery نشطين")
            return {
                'success': False,
                'message': 'لا يوجد عمال Celery نشطين'
            }
        
        # فحص استهلاك الذاكرة
        high_memory_workers = []
        for worker, worker_stats in stats.items():
            memory_usage = worker_stats.get('rusage', {}).get('maxrss', 0)
            # إذا كان استهلاك الذاكرة أكثر من 150MB
            if memory_usage > 150000:
                high_memory_workers.append(worker)
        
        if high_memory_workers:
            logger.info(f"إعادة تشغيل العمال ذوي الاستهلاك العالي للذاكرة: {high_memory_workers}")
            # إرسال أمر إعادة التشغيل
            current_app.control.broadcast('pool_restart', arguments={'reload': True})
            
            return {
                'success': True,
                'restarted_workers': high_memory_workers,
                'message': f'تم إعادة تشغيل {len(high_memory_workers)} عامل'
            }
        
        return {
            'success': True,
            'message': 'جميع العمال يعملون بشكل طبيعي'
        }
        
    except Exception as e:
        logger.error(f"خطأ في فحص العمال: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'فشل في فحص العمال'
        }


@shared_task(bind=True)
def system_health_check(self):
    """
    فحص صحة النظام الشامل
    """
    try:
        results = {}
        
        # فحص قاعدة البيانات
        db_result = monitor_database_connections()
        results['database'] = db_result
        
        # فحص Redis
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            results['redis'] = {'success': True, 'message': 'Redis يعمل بشكل طبيعي'}
        except Exception as e:
            results['redis'] = {'success': False, 'error': str(e)}
        
        # فحص Celery
        celery_result = restart_celery_workers_if_needed()
        results['celery'] = celery_result
        
        # تنظيف إذا لزم الأمر
        if results['database'].get('idle_connections', 0) > 10:
            cleanup_result = cleanup_database_connections()
            results['cleanup'] = cleanup_result
        
        logger.info("تم إجراء فحص صحة النظام")
        
        return {
            'success': True,
            'results': results,
            'message': 'تم إجراء فحص صحة النظام بنجاح'
        }
        
    except Exception as e:
        logger.error(f"خطأ في فحص صحة النظام: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'فشل في فحص صحة النظام'
        }
