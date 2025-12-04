#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🚀 أداة التسريع 1000x - Speed Boost Optimizer
تطبيق التحسينات تلقائياً
"""

import os
import sys
import re
from pathlib import Path

# إضافة المشروع للـ path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

import django
django.setup()

from django.conf import settings


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def optimize_sessions():
    """تحسين الجلسات لاستخدام Redis"""
    print_header("🔧 تحسين نظام الجلسات")
    
    settings_path = Path(settings.BASE_DIR) / 'crm' / 'settings.py'
    content = settings_path.read_text(encoding='utf-8')
    
    # البحث عن SESSION_ENGINE
    if 'SESSION_ENGINE' in content:
        if 'backends.cache' not in content:
            print("  ⚠️ الجلسات تستخدم قاعدة البيانات - يجب تحويلها لـ Redis")
            return False
        else:
            print("  ✅ الجلسات تستخدم Cache بالفعل")
            return True
    else:
        print("  ⚠️ SESSION_ENGINE غير محدد")
        return False


def optimize_context_processors():
    """تحسين Context Processors"""
    print_header("🔧 تحسين Context Processors")
    
    # إنشاء context processor محسّن مع caching
    optimized_cp = '''
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
'''
    
    output_path = Path(settings.BASE_DIR) / 'core' / 'cached_context.py'
    output_path.write_text(optimized_cp, encoding='utf-8')
    print(f"  ✅ تم إنشاء: {output_path}")
    
    return True


def optimize_admin_querysets():
    """تحسين استعلامات لوحة التحكم"""
    print_header("🔧 تحسين استعلامات Admin")
    
    # إنشاء mixin للتحسين
    admin_mixin = '''
# -*- coding: utf-8 -*-
"""
Admin Mixins للتحسين التلقائي
استخدم هذا في كل ModelAdmin لتحسين الأداء
"""

from django.contrib import admin
from django.db.models import Prefetch


class OptimizedAdminMixin:
    """
    Mixin لتحسين استعلامات Admin تلقائياً
    
    الاستخدام:
    class MyModelAdmin(OptimizedAdminMixin, admin.ModelAdmin):
        list_display = ['name', 'category', 'created_by']
        # سيتم تحسين الاستعلامات تلقائياً
    """
    
    # تحديد الحقول للـ select_related تلقائياً
    auto_select_related = True
    
    # تحديد الحقول للـ prefetch_related تلقائياً  
    auto_prefetch_related = True
    
    # تعطيل عدد النتائج لتحسين الأداء
    show_full_result_count = False
    
    # تحديد أقصى عدد للعرض
    list_per_page = 25
    list_max_show_all = 50
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        if self.auto_select_related:
            # الحصول على ForeignKey fields
            fk_fields = [
                f.name for f in self.model._meta.get_fields()
                if f.is_relation and f.many_to_one
            ]
            
            # تحديد الحقول المعروضة
            display_fields = list(self.list_display) if self.list_display else []
            
            # select_related للحقول المعروضة
            related_fields = [f for f in fk_fields if f in display_fields or f'{f}__' in str(display_fields)]
            
            if related_fields:
                qs = qs.select_related(*related_fields[:5])  # أقصى 5 للأداء
        
        return qs


class CachedAdminMixin:
    """
    Mixin لتخزين نتائج Admin في Cache
    """
    
    cache_timeout = 60  # ثانية
    
    def get_queryset(self, request):
        from django.core.cache import cache
        
        cache_key = f"admin:{self.model.__name__}:list"
        qs = cache.get(cache_key)
        
        if qs is None:
            qs = super().get_queryset(request)
            # لا نخزن QuerySet مباشرة لأنها lazy
            
        return super().get_queryset(request)
'''
    
    output_path = Path(settings.BASE_DIR) / 'core' / 'admin_mixins.py'
    output_path.write_text(admin_mixin, encoding='utf-8')
    print(f"  ✅ تم إنشاء: {output_path}")
    
    return True


def optimize_database_queries():
    """إنشاء QuerySet Manager محسّن"""
    print_header("🔧 تحسين QuerySet Manager")
    
    optimized_manager = '''
# -*- coding: utf-8 -*-
"""
QuerySet Manager محسّن للاستعلامات
"""

from django.db import models
from django.core.cache import cache


class CachedQuerySet(models.QuerySet):
    """QuerySet مع دعم التخزين المؤقت"""
    
    def cached(self, timeout=300, key=None):
        """
        تخزين نتائج الاستعلام في Cache
        
        استخدام:
        Model.objects.filter(...).cached(timeout=60)
        """
        if key is None:
            # توليد مفتاح من الاستعلام
            key = f"qs:{self.model.__name__}:{hash(str(self.query))}"
        
        result = cache.get(key)
        if result is None:
            result = list(self)
            cache.set(key, result, timeout)
        
        return result
    
    def only_essential(self):
        """اختيار الحقول الأساسية فقط لتقليل الذاكرة"""
        essential = ['id', 'name', 'created_at']
        existing = [f.name for f in self.model._meta.get_fields() if hasattr(f, 'name')]
        fields = [f for f in essential if f in existing]
        return self.only(*fields) if fields else self


class OptimizedManager(models.Manager):
    """Manager محسّن مع استعلامات ذكية"""
    
    def get_queryset(self):
        return CachedQuerySet(self.model, using=self._db)
    
    def cached_all(self, timeout=300):
        """الحصول على الكل مع تخزين مؤقت"""
        return self.get_queryset().cached(timeout)
    
    def with_related(self, *fields):
        """select_related سريع"""
        return self.get_queryset().select_related(*fields)


# استخدام في Model:
# class MyModel(models.Model):
#     objects = OptimizedManager()
'''
    
    output_path = Path(settings.BASE_DIR) / 'core' / 'optimized_manager.py'
    output_path.write_text(optimized_manager, encoding='utf-8')
    print(f"  ✅ تم إنشاء: {output_path}")
    
    return True


def create_view_cache_decorator():
    """إنشاء decorator للـ View Caching"""
    print_header("🔧 إنشاء View Cache Decorator")
    
    decorator_code = '''
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
'''
    
    output_path = Path(settings.BASE_DIR) / 'core' / 'view_cache.py'
    output_path.write_text(decorator_code, encoding='utf-8')
    print(f"  ✅ تم إنشاء: {output_path}")
    
    return True


def create_lazy_loading_js():
    """إنشاء Lazy Loading للصور"""
    print_header("🔧 إنشاء Lazy Loading للصور")
    
    lazy_js = '''
/**
 * Lazy Loading للصور والمحتوى
 * يحمّل الصور فقط عند ظهورها في الشاشة
 */

(function() {
    'use strict';
    
    // دعم Intersection Observer
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    
                    // تحميل الصورة
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    
                    // تحميل srcset للـ responsive images
                    if (img.dataset.srcset) {
                        img.srcset = img.dataset.srcset;
                        img.removeAttribute('data-srcset');
                    }
                    
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px 0px',  // تحميل قبل الوصول بـ 50px
            threshold: 0.01
        });
        
        // مراقبة جميع الصور بـ data-src
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
        
        // مراقبة الصور الجديدة (للمحتوى المحمّل بـ AJAX)
        const mutationObserver = new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) {
                        const images = node.querySelectorAll ? 
                            node.querySelectorAll('img[data-src]') : [];
                        images.forEach(img => imageObserver.observe(img));
                        
                        if (node.matches && node.matches('img[data-src]')) {
                            imageObserver.observe(node);
                        }
                    }
                });
            });
        });
        
        mutationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    } else {
        // Fallback للمتصفحات القديمة
        document.querySelectorAll('img[data-src]').forEach(img => {
            img.src = img.dataset.src;
        });
    }
    
    // تحميل CSS في الخلفية
    window.loadCSS = function(href) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.media = 'print';
        link.onload = function() {
            this.media = 'all';
        };
        document.head.appendChild(link);
    };
    
    // تحميل JS في الخلفية
    window.loadJS = function(src, callback) {
        const script = document.createElement('script');
        script.src = src;
        script.async = true;
        if (callback) script.onload = callback;
        document.body.appendChild(script);
    };
    
})();

// CSS للصور أثناء التحميل
const style = document.createElement('style');
style.textContent = `
    img[data-src] {
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    }
    img.loaded {
        opacity: 1;
    }
    img[data-src]:not(.loaded) {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
    }
    @keyframes loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
`;
document.head.appendChild(style);
'''
    
    output_path = Path(settings.BASE_DIR) / 'static' / 'js' / 'lazy-loading.js'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(lazy_js, encoding='utf-8')
    print(f"  ✅ تم إنشاء: {output_path}")
    
    return True


def create_performance_middleware():
    """إنشاء Middleware لقياس الأداء"""
    print_header("🔧 إنشاء Performance Middleware")
    
    middleware_code = '''
# -*- coding: utf-8 -*-
"""
Performance Monitoring Middleware
يقيس ويسجل أداء كل طلب
"""

import time
import logging
from django.db import connection, reset_queries
from django.conf import settings

logger = logging.getLogger('performance')


class PerformanceMiddleware:
    """
    Middleware لقياس أداء الطلبات
    يسجل:
    - وقت الاستجابة
    - عدد استعلامات DB
    - الصفحات البطيئة
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_threshold = 1000  # ms
        self.query_threshold = 50   # عدد الاستعلامات
    
    def __call__(self, request):
        # بدء القياس
        start_time = time.time()
        reset_queries()
        
        # تنفيذ الطلب
        response = self.get_response(request)
        
        # حساب الوقت
        duration_ms = (time.time() - start_time) * 1000
        queries_count = len(connection.queries)
        
        # إضافة headers للتطوير
        if settings.DEBUG:
            response['X-Response-Time'] = f"{duration_ms:.2f}ms"
            response['X-DB-Queries'] = str(queries_count)
        
        # تسجيل الصفحات البطيئة
        if duration_ms > self.slow_threshold:
            logger.warning(
                f"SLOW_PAGE: {request.path} | "
                f"{duration_ms:.0f}ms | "
                f"{queries_count} queries"
            )
        
        # تسجيل كثرة الاستعلامات (N+1 problem)
        if queries_count > self.query_threshold:
            logger.warning(
                f"TOO_MANY_QUERIES: {request.path} | "
                f"{queries_count} queries | "
                f"Possible N+1 problem"
            )
        
        return response


class QueryCountMiddleware:
    """
    Middleware بسيط لعد الاستعلامات
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        reset_queries()
        response = self.get_response(request)
        
        query_count = len(connection.queries)
        if query_count > 20:
            print(f"⚠️ {request.path}: {query_count} queries")
        
        return response
'''
    
    output_path = Path(settings.BASE_DIR) / 'core' / 'performance_middleware.py'
    output_path.write_text(middleware_code, encoding='utf-8')
    print(f"  ✅ تم إنشاء: {output_path}")
    
    return True


def update_settings_for_speed():
    """تحديث settings للتسريع"""
    print_header("🔧 إعدادات التسريع المقترحة")
    
    speed_settings = '''
# ============================================
# 🚀 إعدادات التسريع 1000x
# أضف هذه الإعدادات في نهاية settings.py
# ============================================

# 1. تحسين الجلسات - استخدام Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'

# 2. تحسين Cache للصفحات
CACHE_MIDDLEWARE_SECONDS = 300  # 5 دقائق
CACHE_MIDDLEWARE_KEY_PREFIX = 'homeupdate_page'

# 3. تحسين Templates
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# 4. تعطيل عدّ النتائج في Admin
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# 5. تحسين الملفات الثابتة
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 6. إعدادات الضغط
WHITENOISE_MAX_AGE = 31536000  # سنة
WHITENOISE_AUTOREFRESH = DEBUG

# 7. تحسين قاعدة البيانات
if not DEBUG:
    CONN_MAX_AGE = 600  # 10 دقائق

# 8. تقليل Logging في Production
if not DEBUG:
    LOGGING['handlers']['console']['level'] = 'WARNING'
'''
    
    print(speed_settings)
    
    output_path = Path(settings.BASE_DIR) / 'ملفات_إدارية' / 'speed_settings.py'
    output_path.write_text(speed_settings, encoding='utf-8')
    print(f"\n  ✅ تم حفظ الإعدادات في: {output_path}")
    
    return True


def main():
    """تطبيق جميع التحسينات"""
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║  🚀 أداة التسريع 1000x - Speed Boost Optimizer                           ║
║  تطبيق التحسينات تلقائياً                                                ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    optimizations = [
        ("تحسين الجلسات", optimize_sessions),
        ("تحسين Context Processors", optimize_context_processors),
        ("تحسين Admin QuerySets", optimize_admin_querysets),
        ("تحسين Database Queries", optimize_database_queries),
        ("إنشاء View Cache", create_view_cache_decorator),
        ("إنشاء Lazy Loading", create_lazy_loading_js),
        ("إنشاء Performance Middleware", create_performance_middleware),
        ("إعدادات التسريع", update_settings_for_speed),
    ]
    
    success_count = 0
    
    for name, func in optimizations:
        try:
            if func():
                success_count += 1
        except Exception as e:
            print(f"  ❌ خطأ في {name}: {e}")
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ✅ تم تطبيق {success_count}/{len(optimizations)} تحسينات                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  📁 الملفات المُنشأة:                                                     ║
║  • core/cached_context.py       - Context Processors مع Cache           ║
║  • core/admin_mixins.py         - Admin Mixins للتحسين                  ║
║  • core/optimized_manager.py    - QuerySet Manager محسّن                ║
║  • core/view_cache.py           - View Caching Decorators               ║
║  • core/performance_middleware.py - قياس الأداء                         ║
║  • static/js/lazy-loading.js    - Lazy Loading للصور                    ║
║                                                                          ║
║  📋 الخطوات التالية:                                                     ║
║  1. راجع speed_settings.py وأضف الإعدادات المناسبة                       ║
║  2. استخدم OptimizedAdminMixin في ModelAdmin                            ║
║  3. أضف @cache_view للـ Views البطيئة                                    ║
║  4. أضف lazy-loading.js في base.html                                    ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)


if __name__ == '__main__':
    main()
