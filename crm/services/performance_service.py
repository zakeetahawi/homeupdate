"""
خدمة تحسين الأداء المتقدمة
"""

import time
import logging
import json
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

class PerformanceService:
    """
    خدمة متقدمة لتحسين الأداء
    """
    
    @staticmethod
    def cache_key_generator(prefix, *args, **kwargs):
        """إنشاء مفتاح cache ديناميكي"""
        key_parts = [prefix]
        
        for arg in args:
            key_parts.append(str(arg))
        
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")
        
        return ":".join(key_parts)
    
    @staticmethod
    def get_cached_data(cache_key, timeout=300):
        """استرجاع بيانات من cache"""
        try:
            return cache.get(cache_key)
        except Exception as e:
            logger.error(f"خطأ في استرجاع cache: {e}")
            return None
    
    @staticmethod
    def set_cached_data(cache_key, data, timeout=300):
        """حفظ بيانات في cache"""
        try:
            cache.set(cache_key, data, timeout)
            return True
        except Exception as e:
            logger.error(f"خطأ في حفظ cache: {e}")
            return False
    
    @staticmethod
    def invalidate_cache_pattern(pattern):
        """حذف cache بنمط معين"""
        try:
            # في الإنتاج، استخدم Redis أو Memcached مع دعم patterns
            # هنا نستخدم طريقة بسيطة
            cache.clear()
            return True
        except Exception as e:
            logger.error(f"خطأ في حذف cache: {e}")
            return False


class QueryOptimizer:
    """
    محسن الاستعلامات
    """
    
    @staticmethod
    def optimize_queryset(queryset, select_related=None, prefetch_related=None):
        """تحسين queryset"""
        if select_related:
            queryset = queryset.select_related(*select_related)
        
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        return queryset
    
    @staticmethod
    def get_optimized_list(queryset, page=1, per_page=20, **kwargs):
        """الحصول على قائمة محسنة مع pagination"""
        # تحسين الاستعلام
        optimized_qs = QueryOptimizer.optimize_queryset(queryset, **kwargs)
        
        # إضافة pagination
        paginator = Paginator(optimized_qs, per_page)
        page_obj = paginator.get_page(page)
        
        return {
            'objects': page_obj,
            'total_count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
        }
    
    @staticmethod
    def monitor_query_performance(func):
        """decorator لمراقبة أداء الاستعلامات"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            initial_queries = len(connection.queries)
            
            try:
                result = func(*args, **kwargs)
                
                end_time = time.time()
                final_queries = len(connection.queries)
                query_count = final_queries - initial_queries
                duration = end_time - start_time
                
                # تسجيل الأداء
                if duration > 0.5 or query_count > 10:
                    logger.warning(
                        f"أداء بطيء في {func.__name__}: "
                        f"{duration:.3f}s, {query_count} استعلام"
                    )
                
                return result
                
            except Exception as e:
                logger.error(f"خطأ في {func.__name__}: {e}")
                raise
        
        return wrapper


class CacheManager:
    """
    مدير Cache المتقدم
    """
    
    CACHE_TIMEOUTS = {
        'short': 60,      # دقيقة واحدة
        'medium': 300,    # 5 دقائق
        'long': 1800,     # 30 دقيقة
        'day': 86400,     # يوم واحد
    }
    
    @staticmethod
    def get_cache_key(model_name, action, **kwargs):
        """إنشاء مفتاح cache موحد"""
        key_parts = [model_name, action]
        
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}_{value}")
        
        return "_".join(key_parts)
    
    @staticmethod
    def cache_model_data(model_name, action, data, timeout='medium', **kwargs):
        """cache بيانات النموذج"""
        cache_key = CacheManager.get_cache_key(model_name, action, **kwargs)
        return PerformanceService.set_cached_data(cache_key, data, CacheManager.CACHE_TIMEOUTS[timeout])
    
    @staticmethod
    def get_cached_model_data(model_name, action, **kwargs):
        """استرجاع بيانات النموذج من cache"""
        cache_key = CacheManager.get_cache_key(model_name, action, **kwargs)
        return PerformanceService.get_cached_data(cache_key)
    
    @staticmethod
    def invalidate_model_cache(model_name, **kwargs):
        """حذف cache النموذج"""
        pattern = f"{model_name}_*"
        return PerformanceService.invalidate_cache_pattern(pattern)


class PerformanceMonitor:
    """
    مراقب الأداء
    """
    
    @staticmethod
    def get_performance_metrics():
        """الحصول على مقاييس الأداء"""
        metrics = {
            'timestamp': timezone.now(),
            'cache_hits': cache.get('cache_hits', 0),
            'cache_misses': cache.get('cache_misses', 0),
            'slow_queries': cache.get('slow_queries', 0),
            'error_count': cache.get('error_count', 0),
        }
        
        # حساب نسبة نجاح cache
        total_cache_requests = metrics['cache_hits'] + metrics['cache_misses']
        if total_cache_requests > 0:
            metrics['cache_hit_rate'] = (metrics['cache_hits'] / total_cache_requests) * 100
        else:
            metrics['cache_hit_rate'] = 0
        
        return metrics
    
    @staticmethod
    def record_cache_hit():
        """تسجيل cache hit"""
        cache.incr('cache_hits', 1)
    
    @staticmethod
    def record_cache_miss():
        """تسجيل cache miss"""
        cache.incr('cache_misses', 1)
    
    @staticmethod
    def record_slow_query(duration, query_count):
        """تسجيل استعلام بطيء"""
        slow_queries = cache.get('slow_queries', [])
        slow_queries.append({
            'timestamp': timezone.now(),
            'duration': duration,
            'query_count': query_count,
        })
        
        # الاحتفاظ بآخر 100 استعلام بطيء فقط
        if len(slow_queries) > 100:
            slow_queries = slow_queries[-100:]
        
        cache.set('slow_queries', slow_queries, 3600)  # ساعة واحدة
        cache.incr('slow_queries_count', 1)
    
    @staticmethod
    def record_error(error_type, error_message):
        """تسجيل خطأ"""
        errors = cache.get('recent_errors', [])
        errors.append({
            'timestamp': timezone.now(),
            'type': error_type,
            'message': error_message,
        })
        
        # الاحتفاظ بآخر 50 خطأ فقط
        if len(errors) > 50:
            errors = errors[-50:]
        
        cache.set('recent_errors', errors, 3600)  # ساعة واحدة
        cache.incr('error_count', 1)


class DatabaseOptimizer:
    """
    محسن قاعدة البيانات
    """
    
    @staticmethod
    def get_table_stats():
        """الحصول على إحصائيات الجداول"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables
                ORDER BY n_live_tup DESC
            """)
            
            return cursor.fetchall()
    
    @staticmethod
    def get_index_usage():
        """الحصول على استخدام الفهارس"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC
            """)
            
            return cursor.fetchall()
    
    @staticmethod
    def suggest_indexes():
        """اقتراح فهارس جديدة"""
        suggestions = []
        
        # تحليل الاستعلامات البطيئة
        slow_queries = cache.get('slow_queries', [])
        
        for query_info in slow_queries:
            if query_info['duration'] > 1.0:  # أكثر من ثانية
                suggestions.append({
                    'type': 'slow_query',
                    'duration': query_info['duration'],
                    'query_count': query_info['query_count'],
                    'recommendation': 'تحليل الاستعلام وإضافة فهارس مناسبة'
                })
        
        return suggestions 