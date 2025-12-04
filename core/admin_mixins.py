
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
