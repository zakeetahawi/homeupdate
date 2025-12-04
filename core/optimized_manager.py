
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
