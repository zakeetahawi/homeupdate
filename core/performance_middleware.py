
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
