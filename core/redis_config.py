"""
🔴 Redis Cluster Configuration - تكوين Redis موحد ومحسّن

التحسينات:
1. دمج 3 قواعد بيانات Redis منفصلة في كاش واحد مع prefixes
2. Connection Pooling محسّن
3. Serialization أسرع باستخدام msgpack
4. Health checks وتسجيل الأخطاء
5. Fallback آمن عند فشل Redis

الإعدادات المقترحة لـ settings.py
"""

# =============================================
# إعدادات Redis المحسّنة - انسخ هذا إلى settings.py
# =============================================

REDIS_OPTIMIZED_CONFIG = """
# ===========================================
# 🔴 Redis Cache Configuration - محسّن
# ===========================================

# استخدام قاعدة بيانات واحدة مع prefixes بدلاً من 3 منفصلة
REDIS_URL = 'redis://localhost:6379/0'

# إعدادات Connection Pool
REDIS_CONNECTION_POOL_OPTIONS = {
    'max_connections': 100,  # زيادة من 50
    'retry_on_timeout': True,
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'socket_keepalive': True,
    'health_check_interval': 30,
}

CACHES = {
    # الكاش الافتراضي - للبيانات العامة
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'TIMEOUT': 300,  # 5 دقائق
        'KEY_PREFIX': 'crm',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': REDIS_CONNECTION_POOL_OPTIONS,
            'SERIALIZER': 'django_redis.serializers.msgpack.MSGPackSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,  # لا يفشل إذا كان Redis غير متاح
        }
    },
    
    # كاش الجلسات - TTL أطول
    'session': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'TIMEOUT': 86400,  # 24 ساعة
        'KEY_PREFIX': 'session',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 30,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'IGNORE_EXCEPTIONS': True,
        }
    },
    
    # كاش الاستعلامات - TTL قصير
    'query': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'TIMEOUT': 60,  # دقيقة واحدة
        'KEY_PREFIX': 'query',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.msgpack.MSGPackSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        }
    },
    
    # كاش الصفحات - للـ views المكثفة
    'page': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'TIMEOUT': 300,  # 5 دقائق
        'KEY_PREFIX': 'page',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 30,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.pickle.PickleSerializer',
            'IGNORE_EXCEPTIONS': True,
        }
    },
    
    # كاش الإحصائيات - للـ Materialized Views
    'stats': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'TIMEOUT': 600,  # 10 دقائق
        'KEY_PREFIX': 'stats',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 20,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.msgpack.MSGPackSerializer',
            'IGNORE_EXCEPTIONS': True,
        }
    },
}

# استخدام Redis للجلسات
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'
SESSION_COOKIE_AGE = 86400  # 24 ساعة
SESSION_COOKIE_SECURE = True  # في الإنتاج فقط
SESSION_SAVE_EVERY_REQUEST = False  # تحسين الأداء

# إعدادات Celery مع Redis (إذا كان مستخدماً)
# CELERY_BROKER_URL = 'redis://localhost:6379/1'
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/2'
"""


# =============================================
# Helper Classes للـ Redis
# =============================================

import functools
import hashlib
import logging
from typing import Any, Callable, Optional

from django.core.cache import caches

logger = logging.getLogger("performance")


class CacheManager:
    """
    مدير الكاش الموحد - يسهل استخدام الكاش المختلف

    الاستخدام:
    cache_manager = CacheManager()

    # كاش عام
    cache_manager.set('key', 'value')

    # كاش للاستعلامات (قصير المدى)
    cache_manager.set_query('orders_list', orders_data)

    # كاش للإحصائيات (طويل المدى)
    cache_manager.set_stats('daily_summary', summary_data)
    """

    def __init__(self):
        self._caches = {
            "default": caches["default"],
            "query": caches.get("query", caches["default"]),
            "page": caches.get("page", caches["default"]),
            "stats": caches.get("stats", caches["default"]),
            "session": caches.get("session", caches["default"]),
        }

    def get_cache(self, cache_type: str = "default"):
        """الحصول على كاش معين"""
        return self._caches.get(cache_type, self._caches["default"])

    # === Default Cache ===
    def get(self, key: str, default=None):
        return self._caches["default"].get(key, default)

    def set(self, key: str, value: Any, timeout: int = 300):
        return self._caches["default"].set(key, value, timeout)

    def delete(self, key: str):
        return self._caches["default"].delete(key)

    # === Query Cache (قصير المدى) ===
    def get_query(self, key: str, default=None):
        return self._caches["query"].get(f"q:{key}", default)

    def set_query(self, key: str, value: Any, timeout: int = 60):
        return self._caches["query"].set(f"q:{key}", value, timeout)

    def delete_query(self, key: str):
        return self._caches["query"].delete(f"q:{key}")

    # === Stats Cache (طويل المدى) ===
    def get_stats(self, key: str, default=None):
        return self._caches["stats"].get(f"s:{key}", default)

    def set_stats(self, key: str, value: Any, timeout: int = 600):
        return self._caches["stats"].set(f"s:{key}", value, timeout)

    def delete_stats(self, key: str):
        return self._caches["stats"].delete(f"s:{key}")

    # === Page Cache ===
    def get_page(self, key: str, default=None):
        return self._caches["page"].get(f"p:{key}", default)

    def set_page(self, key: str, value: Any, timeout: int = 300):
        return self._caches["page"].set(f"p:{key}", value, timeout)

    def delete_page(self, key: str):
        return self._caches["page"].delete(f"p:{key}")

    # === Utility Methods ===
    def clear_all(self):
        """مسح جميع الكاش"""
        for cache in self._caches.values():
            try:
                cache.clear()
            except Exception as e:
                logger.warning(f"Failed to clear cache: {e}")

    def clear_pattern(self, pattern: str, cache_type: str = "default"):
        """مسح مفاتيح تطابق نمط معين"""
        cache = self._caches.get(cache_type, self._caches["default"])
        try:
            if hasattr(cache, "delete_pattern"):
                cache.delete_pattern(f"*{pattern}*")
            else:
                # Fallback للـ caches التي لا تدعم patterns
                logger.warning(f"Cache {cache_type} doesn't support pattern deletion")
        except Exception as e:
            logger.error(f"Failed to clear pattern {pattern}: {e}")

    def get_stats_info(self) -> dict:
        """الحصول على إحصائيات الكاش"""
        stats = {}
        for name, cache in self._caches.items():
            try:
                if hasattr(cache, "client"):
                    client = cache.client.get_client()
                    if hasattr(client, "info"):
                        info = client.info()
                        stats[name] = {
                            "used_memory": info.get("used_memory_human", "N/A"),
                            "connected_clients": info.get("connected_clients", "N/A"),
                            "keyspace_hits": info.get("keyspace_hits", 0),
                            "keyspace_misses": info.get("keyspace_misses", 0),
                        }
            except Exception:
                stats[name] = {"status": "unavailable"}
        return stats


# Global instance
cache_manager = CacheManager()


# =============================================
# Decorators للـ Caching
# =============================================


def cache_result(
    timeout: int = 300,
    cache_type: str = "default",
    key_prefix: str = "",
    vary_on: list = None,
):
    """
    ديكوريتور لتخزين نتائج الدوال في الكاش

    Args:
        timeout: مدة الكاش بالثواني
        cache_type: نوع الكاش (default, query, stats, page)
        key_prefix: بادئة المفتاح
        vary_on: قائمة أسماء المعاملات للتمييز

    الاستخدام:
    @cache_result(timeout=600, cache_type='stats', key_prefix='order_stats')
    def get_order_statistics(branch_id, days=30):
        # ... كود بطيء ...
        return result
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # بناء مفتاح الكاش
            key_parts = [key_prefix or func.__name__]

            # إضافة vary_on parameters
            if vary_on:
                for param in vary_on:
                    if param in kwargs:
                        key_parts.append(f"{param}:{kwargs[param]}")
            else:
                # إضافة hash لكل المعاملات
                all_args = str(args) + str(sorted(kwargs.items()))
                args_hash = hashlib.md5(all_args.encode()).hexdigest()[:8]
                key_parts.append(args_hash)

            cache_key = ":".join(key_parts)

            # محاولة جلب من الكاش
            cache = cache_manager.get_cache(cache_type)
            cached_result = cache.get(cache_key)

            if cached_result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_result

            # تنفيذ الدالة
            result = func(*args, **kwargs)

            # تخزين النتيجة
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cache SET: {cache_key}")

            return result

        # إضافة دالة لإبطال الكاش
        def invalidate(*args, **kwargs):
            key_parts = [key_prefix or func.__name__]
            if args or kwargs:
                all_args = str(args) + str(sorted(kwargs.items()))
                args_hash = hashlib.md5(all_args.encode()).hexdigest()[:8]
                key_parts.append(args_hash)
            cache_key = ":".join(key_parts)
            cache_manager.get_cache(cache_type).delete(cache_key)

        wrapper.invalidate = invalidate
        return wrapper

    return decorator


def cache_queryset(timeout: int = 60, key_prefix: str = "", evaluate: bool = True):
    """
    ديكوريتور لتخزين نتائج QuerySets

    Args:
        timeout: مدة الكاش
        key_prefix: بادئة المفتاح
        evaluate: تحويل QuerySet إلى قائمة قبل التخزين
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key_parts = [key_prefix or func.__name__]
            all_args = str(args) + str(sorted(kwargs.items()))
            key_parts.append(hashlib.md5(all_args.encode()).hexdigest()[:8])
            cache_key = ":".join(key_parts)

            cached = cache_manager.get_query(cache_key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)

            # تحويل QuerySet إلى قائمة للتخزين
            if evaluate and hasattr(result, "__iter__") and hasattr(result, "model"):
                result = list(result)

            cache_manager.set_query(cache_key, result, timeout)
            return result

        return wrapper

    return decorator


# =============================================
# Health Check للـ Redis
# =============================================


def check_redis_health() -> dict:
    """
    فحص صحة اتصال Redis

    Returns:
        dict مع حالة كل cache
    """
    results = {}

    for cache_name in ["default", "query", "stats", "page", "session"]:
        try:
            cache = caches.get(cache_name, caches["default"])

            # اختبار set/get
            test_key = f"health_check_{cache_name}"
            cache.set(test_key, "OK", 10)
            value = cache.get(test_key)
            cache.delete(test_key)

            if value == "OK":
                results[cache_name] = {"status": "healthy", "message": "Connected"}
            else:
                results[cache_name] = {
                    "status": "degraded",
                    "message": "Set/Get mismatch",
                }

        except Exception as e:
            results[cache_name] = {"status": "unhealthy", "message": str(e)}

    return results


def get_redis_info() -> dict:
    """
    الحصول على معلومات تفصيلية عن Redis
    """
    try:
        from django_redis import get_redis_connection

        conn = get_redis_connection("default")
        info = conn.info()

        return {
            "version": info.get("redis_version"),
            "used_memory": info.get("used_memory_human"),
            "used_memory_peak": info.get("used_memory_peak_human"),
            "connected_clients": info.get("connected_clients"),
            "total_connections_received": info.get("total_connections_received"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
            "hit_rate": round(
                info.get("keyspace_hits", 0)
                / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                * 100,
                2,
            ),
            "uptime_in_days": info.get("uptime_in_days"),
        }
    except Exception as e:
        return {"error": str(e)}


# =============================================
# Exports
# =============================================

__all__ = [
    "REDIS_OPTIMIZED_CONFIG",
    "CacheManager",
    "cache_manager",
    "cache_result",
    "cache_queryset",
    "check_redis_health",
    "get_redis_info",
]
