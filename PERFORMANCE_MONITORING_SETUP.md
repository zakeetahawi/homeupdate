# إعداد مراقبة الأداء
## Performance Monitoring Setup Guide

> **دليل شامل لإعداد أدوات مراقبة أداء قاعدة البيانات**

---

## 🎯 الهدف من المراقبة

### الأهداف الأساسية:
1. **مراقبة عدد الاستعلامات** في كل صفحة
2. **قياس أوقات الاستجابة** للاستعلامات
3. **تحديد الاستعلامات البطيئة** التي تحتاج تحسين
4. **مراقبة استهلاك الذاكرة** والموارد
5. **تتبع التحسن في الأداء** بمرور الوقت

---

## 🛠️ الأدوات المطلوبة

### 1. Django Debug Toolbar
**الغرض**: مراقبة الاستعلامات في بيئة التطوير

#### التثبيت:
```bash
pip install django-debug-toolbar
```

#### الإعداد في `settings.py`:
```python
# إضافة إلى INSTALLED_APPS
INSTALLED_APPS = [
    # ... التطبيقات الموجودة
    'debug_toolbar',
]

# إضافة إلى MIDDLEWARE
MIDDLEWARE = [
    # ... الـ middleware الموجود
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# إعدادات Debug Toolbar
if DEBUG:
    import socket
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2"]
    
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
        'SHOW_COLLAPSED': True,
        'SQL_WARNING_THRESHOLD': 20,  # تحذير عند تجاوز 20 استعلام
    }
```

#### إضافة إلى `urls.py`:
```python
from django.conf import settings
from django.urls import path, include

urlpatterns = [
    # ... الـ URLs الموجودة
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
```

### 2. PostgreSQL Query Logging
**الغرض**: تسجيل الاستعلامات البطيئة في الإنتاج

#### إعداد PostgreSQL:
```sql
-- تفعيل تسجيل الاستعلامات ا��بطيئة
ALTER SYSTEM SET log_min_duration_statement = 1000; -- 1 ثانية
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_duration = on;
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- إعادة تحميل الإعدادات
SELECT pg_reload_conf();
```

### 3. Custom Performance Middleware
**الغرض**: مراقبة مخصصة للأداء

#### إنشاء ملف `middleware/performance.py`:
```python
import time
import logging
from django.db import connection
from django.conf import settings

logger = logging.getLogger('performance')

class PerformanceMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # قياس الوقت قبل المعالجة
        start_time = time.time()
        start_queries = len(connection.queries)
        
        response = self.get_response(request)
        
        # قياس الوقت بعد المعالجة
        end_time = time.time()
        end_queries = len(connection.queries)
        
        # حساب الإحصائيات
        total_time = end_time - start_time
        total_queries = end_queries - start_queries
        
        # تسجيل الإحصائيات
        if settings.DEBUG or total_queries > 50 or total_time > 2:
            logger.warning(
                f"Performance Alert - Path: {request.path} | "
                f"Queries: {total_queries} | "
                f"Time: {total_time:.2f}s | "
                f"Method: {request.method} | "
                f"User: {getattr(request.user, 'username', 'Anonymous')}"
            )
        
        # إضافة headers للاستجابة
        if settings.DEBUG:
            response['X-DB-Queries'] = str(total_queries)
            response['X-Response-Time'] = f"{total_time:.2f}s"
        
        return response
```

#### إضافة إلى `settings.py`:
```python
MIDDLEWARE = [
    # ... الـ middleware الموجود
    'middleware.performance.PerformanceMonitoringMiddleware',
]

# إعداد التسجيل
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'performance_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'logs/performance.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'performance': {
            'handlers': ['performance_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['performance_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

---

## 📊 Dashboard للمراقبة

### إنشاء تطبيق المراقبة:
```bash
python manage.py startapp monitoring
```

### إنشاء نموذج لتخزين الإحصائيات:
```python
# monitoring/models.py
from django.db import models
from django.contrib.auth.models import User

class PerformanceMetric(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    query_count = models.IntegerField()
    response_time = models.FloatField()  # بالثواني
    memory_usage = models.FloatField(null=True, blank=True)  # بالميجابايت
    
    class Meta:
        indexes = [
            models.Index(fields=['timestamp', 'path']),
            models.Index(fields=['query_count']),
            models.Index(fields=['response_time']),
        ]

class SlowQuery(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    query = models.TextField()
    duration = models.FloatField()  # بالثواني
    path = models.CharField(max_length=255)
    
    class Meta:
        indexes = [
            models.Index(fields=['timestamp', 'duration']),
        ]
```

### إنشاء View للـ Dashboard:
```python
# monitoring/views.py
from django.shortcuts import render
from django.db.models import Avg, Count, Max
from django.utils import timezone
from datetime import timedelta
from .models import PerformanceMetric, SlowQuery

def performance_dashboard(request):
    # آخر 24 ساعة
    last_24h = timezone.now() - timedelta(hours=24)
    
    # الإحصائيات العامة
    stats = PerformanceMetric.objects.filter(timestamp__gte=last_24h).aggregate(
        avg_queries=Avg('query_count'),
        max_queries=Max('query_count'),
        avg_response_time=Avg('response_time'),
        max_response_time=Max('response_time'),
        total_requests=Count('id')
    )
    
    # أبطأ الصفحات
    slow_pages = PerformanceMetric.objects.filter(
        timestamp__gte=last_24h
    ).values('path').annotate(
        avg_queries=Avg('query_count'),
        avg_time=Avg('response_time'),
        request_count=Count('id')
    ).order_by('-avg_queries')[:10]
    
    # الاستعلامات الب��يئة
    slow_queries = SlowQuery.objects.filter(
        timestamp__gte=last_24h
    ).order_by('-duration')[:20]
    
    context = {
        'stats': stats,
        'slow_pages': slow_pages,
        'slow_queries': slow_queries,
    }
    
    return render(request, 'monitoring/dashboard.html', context)
```

### إنشاء Template للـ Dashboard:
```html
<!-- monitoring/templates/monitoring/dashboard.html -->
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>مراقبة الأداء</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h1>لوحة مراقبة الأداء</h1>
        
        <!-- الإحصائيات العامة -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">متوسط الاستعلامات</h5>
                        <h2 class="text-primary">{{ stats.avg_queries|floatformat:0 }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">أقصى استعلامات</h5>
                        <h2 class="text-warning">{{ stats.max_queries }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">متوسط وقت الاستجابة</h5>
                        <h2 class="text-info">{{ stats.avg_response_time|floatformat:2 }}s</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h5 class="card-title">إجمالي الطلبات</h5>
                        <h2 class="text-success">{{ stats.total_requests }}</h2>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- أبطأ الصفحات -->
        <div class="row">
            <div class="col-md-6">
                <h3>أبطأ الصفحات (حسب عدد الاستعلامات)</h3>
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>المسار</th>
                            <th>متوسط الاستعلامات</th>
                            <th>متوسط الوقت</th>
                            <th>عدد الطلبات</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for page in slow_pages %}
                        <tr>
                            <td>{{ page.path }}</td>
                            <td>
                                <span class="badge {% if page.avg_queries > 100 %}bg-danger{% elif page.avg_queries > 50 %}bg-warning{% else %}bg-success{% endif %}">
                                    {{ page.avg_queries|floatformat:0 }}
                                </span>
                            </td>
                            <td>{{ page.avg_time|floatformat:2 }}s</td>
                            <td>{{ page.request_count }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            
            <div class="col-md-6">
                <h3>الاستعلامات البطيئة</h3>
                <div style="max-height: 400px; overflow-y: auto;">
                    {% for query in slow_queries %}
                    <div class="card mb-2">
                        <div class="card-body">
                            <h6 class="card-title">
                                {{ query.path }} 
                                <span class="badge bg-danger">{{ query.duration|floatformat:2 }}s</span>
                            </h6>
                            <code style="font-size: 0.8em;">{{ query.query|truncatechars:100 }}</code>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
```

---

## 🔧 إعداد التنبيهات

### إنشاء Management Command للتحقق:
```python
# monitoring/management/commands/check_performance.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from monitoring.models import PerformanceMetric

class Command(BaseCommand):
    help = 'Check performance metrics and send alerts'

    def handle(self, *args, **options):
        # آخر ساعة
        last_hour = timezone.now() - timedelta(hours=1)
        
        # البحث عن الصفحات البطيئة
        slow_pages = PerformanceMetric.objects.filter(
            timestamp__gte=last_hour,
            query_count__gt=100  # أكثر من 100 استعلام
        ).count()
        
        if slow_pages > 0:
            # إرسال تنبيه
            send_mail(
                subject='تنبيه: أداء بطيء في النظام',
                message=f'تم رصد {slow_pages} صفحة بطيئة في آخر ساعة',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['admin@example.com'],
                fail_silently=False,
            )
            
            self.stdout.write(
                self.style.WARNING(f'تم إرسال تنبيه: {slow_pages} صفحة بطيئة')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('الأداء طبيعي')
            )
```

### إعداد Cron Job:
```bash
# إضافة إلى crontab
# تشغيل كل ساعة
0 * * * * cd /path/to/project && python manage.py check_performance
```

---

## 📈 تقارير الأداء

### إنشاء تقرير أسبوعي:
```python
# monitoring/management/commands/weekly_performance_report.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from monitoring.models import PerformanceMetric

class Command(BaseCommand):
    help = 'Generate weekly performance report'

    def handle(self, *args, **options):
        # آخر أسبوع
        last_week = timezone.now() - timedelta(days=7)
        
        # جمع الإحصائيات
        metrics = PerformanceMetric.objects.filter(timestamp__gte=last_week)
        
        stats = metrics.aggregate(
            avg_queries=Avg('query_count'),
            max_queries=Max('query_count'),
            avg_response_time=Avg('response_time'),
            total_requests=Count('id')
        )
        
        # أبطأ الصفحات
        slow_pages = metrics.values('path').annotate(
            avg_queries=Avg('query_count'),
            request_count=Count('id')
        ).order_by('-avg_queries')[:10]
        
        # إنشاء التقرير
        report_html = render_to_string('monitoring/weekly_report.html', {
            'stats': stats,
            'slow_pages': slow_pages,
            'period': 'آخر أسبوع'
        })
        
        # إرسال التقرير
        send_mail(
            subject='تقرير الأداء الأسبوعي',
            message='',
            html_message=report_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['admin@example.com'],
            fail_silently=False,
        )
        
        self.stdout.write(
            self.style.SUCCESS('تم إرسال التقرير الأسبوعي')
        )
```

---

## 🎯 معايير الأد��ء المستهدفة

### المعايير المقبولة:
- **عدد الاستعلامات**: أقل من 50 لكل صفحة
- **وقت الاستجابة**: أقل من 2 ثانية
- **الاستعلامات البطيئة**: أقل من 1 ثانية

### المعايير المثلى:
- **عدد الاستعلامات**: أقل من 20 لكل صفحة
- **وقت الاستجابة**: أقل من 1 ثانية
- **الاستعلامات البطيئة**: أقل من 0.5 ثانية

### إجراءات التنبيه:
- **تحذير**: عند تجاوز المعايير المقبولة
- **خطر**: عند تجاوز ضعف المعايير المقبولة
- **حرج**: عند تجاوز ثلاثة أضعاف المعايير المقبولة

---

**تاريخ الإنشاء**: يناير 2025  
**آخر تحديث**: يناير 2025  
**الحالة**: جاهز للتطبيق ✅