
# -*- coding: utf-8 -*-
"""
View Caching Decorators للتسريع
"""

from functools import wraps
from django.core.cache import cache
from django.http import HttpResponse
import hashlib


def cache_view(timeout=300, key_prefix='view'):
    """
    Decorator لتخزين نتائج View في Cache
    
    استخدام:
    @cache_view(timeout=60)
    def my_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # لا تخزن POST requests
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)
            
            # مفتاح فريد
            user_id = getattr(request.user, 'id', 'anon')
            path_hash = hashlib.md5(request.get_full_path().encode()).hexdigest()[:8]
            cache_key = f"{key_prefix}:{view_func.__name__}:{user_id}:{path_hash}"
            
            # محاولة الحصول من Cache
            response = cache.get(cache_key)
            if response is None:
                response = view_func(request, *args, **kwargs)
                
                # تخزين فقط إذا نجح
                if hasattr(response, 'status_code') and response.status_code == 200:
                    cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator


def cache_api(timeout=60):
    """
    Decorator خاص للـ API endpoints
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)
            
            cache_key = f"api:{view_func.__name__}:{request.GET.urlencode()}"
            
            response = cache.get(cache_key)
            if response is None:
                response = view_func(request, *args, **kwargs)
                cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator


def invalidate_cache(pattern):
    """
    حذف Cache بناءً على pattern
    
    استخدام:
    invalidate_cache('view:order_list:*')
    """
    from django_redis import get_redis_connection
    
    try:
        redis = get_redis_connection("default")
        keys = redis.keys(f"homeupdate:{pattern}")
        if keys:
            redis.delete(*keys)
            return len(keys)
    except:
        pass
    return 0
