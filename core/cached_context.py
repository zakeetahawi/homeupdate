
# -*- coding: utf-8 -*-
"""
Context Processors محسّنة مع Caching
"""

from django.core.cache import cache
from functools import wraps


def cached_context(timeout=300, key_prefix='ctx'):
    """Decorator لتخزين نتائج Context Processor في Cache"""
    def decorator(func):
        @wraps(func)
        def wrapper(request):
            # مفتاح فريد لكل مستخدم
            user_id = getattr(request.user, 'id', 'anon')
            cache_key = f"{key_prefix}:{func.__name__}:{user_id}"
            
            # محاولة الحصول من Cache
            result = cache.get(cache_key)
            if result is None:
                result = func(request)
                cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


# استخدام: @cached_context(timeout=60)
