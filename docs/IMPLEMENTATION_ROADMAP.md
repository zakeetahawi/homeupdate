# خطة التنفيذ المفصلة لتحسين الأداء
# Detailed Implementation Roadmap

**المشروع:** Home Update ERP System  
**التاريخ:** 3 يناير 2026  
**الإجمالي المتوقع:** 25-30 ساعة عمل  
**التحسين المتوقع:** 70-90% في الأداء العام  

---

## 📋 جدول المحتويات

1. [Phase 0: الإصلاحات الفورية](#phase-0-الإصلاحات-الفورية)
2. [Phase 1: قواعد البيانات](#phase-1-قواعد-البيانات)
3. [Phase 2: Caching & APIs](#phase-2-caching--apis)
4. [Phase 3: Frontend & Static](#phase-3-frontend--static)
5. [Phase 4: Celery & Background](#phase-4-celery--background)
6. [استراتيجية الاختبار](#استراتيجية-الاختبار)
7. [خطة Rollback](#خطة-rollback)

---

## Phase 0: الإصلاحات الفورية

**الوقت المتوقع:** 2 ساعة  
**المخاطر:** منخفضة  
**التحسين المتوقع:** 20-30% تحسين فوري  
**يجب التنفيذ:** اليوم  

### المهام:

#### 1. إصلاح DEBUG Mode (10 دقائق) 🔴 CRITICAL

**الملف:** `.env`

```bash
# قبل
DEBUG=True

# بعد
DEBUG=False
```

**الاختبار:**
```bash
# تشغيل السيرفر والتحقق
python manage.py runserver
# يجب ألا تظهر أخطاء Django المفصلة
```

**المخاطر:** منخفضة جداً  
**Rollback:** `DEBUG=True` مؤقتاً للتشخيص

---

#### 2. تفعيل GZIP Compression (15 دقيقة) 🔴 CRITICAL

**الملف:** `crm/settings.py`

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # ← إضافة هذا السطر
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    # ... باقي middleware
]
```

**الاختبار:**
```bash
# التحقق من compression
curl -H "Accept-Encoding: gzip" http://localhost:8000/ -I
# يجب أن تظهر: Content-Encoding: gzip
```

**التحسين:** 70-85% تقليل في حجم الاستجابات  
**المخاطر:** منخفضة

---

#### 3. إصلاح CORS Security (10 دقائق) 🔴 HIGH

**الملف:** `crm/settings.py`

```python
# السطر 825
CORS_ALLOW_ALL_ORIGINS = False  # ← تغيير من True إلى False

# الاعتماد فقط على القائمة الصريحة
CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
    # أضف النطاقات الموثوقة فقط
]
```

**الاختبار:**
```bash
# محاولة الوصول من نطاق غير مصرح به
curl -H "Origin: http://evil.com" http://localhost:8000/api/
# يجب أن يفشل الطلب
```

**المخاطر:** منخفضة - لكن تأكد من إضافة جميع النطاقات الصحيحة

---

#### 4. تنظيف ALLOWED_HOSTS (15 دقائق) 🔴 HIGH

**الملف:** `crm/settings.py` السطور 311-335

```python
# إزالة جميع wildcards وأنماط التطوير
ALLOWED_HOSTS = [
    'yourdomain.com',
    'www.yourdomain.com',
    'api.yourdomain.com',
]

# في بيئة التطوير فقط
if DEBUG:
    ALLOWED_HOSTS += ['localhost', '127.0.0.1']
```

**الاختبار:**
```bash
# محاولة الوصول بـ Host غير مصرح به
curl -H "Host: evil.com" http://yourserver/
# يجب أن يُرجع 400 Bad Request
```

---

#### 5. تعطيل AdvancedActivityLoggerMiddleware (5 دقائق) 🔴 CRITICAL

**الملف:** `crm/settings.py`

```python
MIDDLEWARE = [
    # ... middleware أخرى
    # 'accounts.middleware.log_terminal_activity.AdvancedActivityLoggerMiddleware',  # ← تعليق
    # 'accounts.middleware.log_terminal_activity.TerminalActivityLoggerMiddleware',  # ← تعليق
]
```

**التحسين:** إزالة 200-500ms من كل طلب!  
**الاختبار:** قياس الوقت قبل وبعد باستخدام django-silk

---

#### 6. حذف Duplicate CurrentUserMiddleware (5 دقائق) 🔴 HIGH

**الملف:** `crm/settings.py`

```python
MIDDLEWARE = [
    # ... middleware أخرى
    'accounts.middleware.current_user.CurrentUserMiddleware',  # ← الاحتفاظ بهذا
    # 'orders.middleware.CurrentUserMiddleware',  # ← حذف هذا السطر
]
```

---

#### 7. إضافة Timeout لـ WhatsApp API (20 دقائق) 🔴 CRITICAL

**الملف:** `whatsapp/services.py`

```python
# ابحث عن جميع حالات requests.get/post/put بدون timeout
# واستبدلها بـ:

import requests

# قبل
response = requests.post(url, json=data)

# بعد
response = requests.post(url, json=data, timeout=10)  # 10 seconds

# الأسطر المتأثرة: 84, 155, 221, 332
```

**الاختبار:**
```python
# في Django shell
from whatsapp.services import WhatsAppService
# اختبار إرسال رسالة
```

---

### ✅ Phase 0 Checklist:

- [ ] تغيير DEBUG=False
- [ ] إضافة GZipMiddleware
- [ ] تعيين CORS_ALLOW_ALL_ORIGINS = False
- [ ] تنظيف ALLOWED_HOSTS
- [ ] تعطيل AdvancedActivityLoggerMiddleware
- [ ] حذف duplicate CurrentUserMiddleware
- [ ] إضافة timeout لـ WhatsApp API
- [ ] إعادة تشغيل gunicorn/uwsgi
- [ ] إعادة تشغيل nginx
- [ ] اختبار الصفحات الرئيسية
- [ ] مراقبة logs لمدة ساعة

**الوقت الفعلي:** 1.5-2 ساعة  
**التحسين المتوقع:** 20-30%

---

## Phase 1: قواعد البيانات

**الوقت المتوقع:** 8 ساعات  
**المخاطر:** متوسطة  
**التحسين المتوقع:** 70-85% تقليل في استعلامات DB  
**البدء:** الأسبوع 1  

### المهام:

#### 1.1 إصلاح N+1 في Models (3 ساعات)

##### أ) Order.total_discount_amount

**الملف:** `orders/models.py` السطور 511-525

```python
# الكود الحالي (حذفه)
@property
def total_discount_amount(self):
    total = Decimal('0.00')
    for item in self.items.all():
        total += item.discount_amount
    return total

# الحل البديل (إضافة method جديد)
def get_total_discount(self):
    """حساب مجموع الخصومات - يجب استخدامه مع aggregate"""
    from django.db.models import Sum
    return self.items.aggregate(
        total=Sum('discount_amount')
    )['total'] or Decimal('0.00')
```

**في Views:**
```python
# استخدام annotation
from django.db.models import Sum

orders = Order.objects.annotate(
    total_discount=Sum('items__discount_amount')
)

# الوصول في template
{{ order.total_discount }}
```

**الاختبار:**
```python
# في django-debug-toolbar
# عدد الاستعلامات يجب أن ينخفض من N+1 إلى 1
```

---

##### ب) Account.full_path

**الملف:** `accounting/models.py` السطور 137-145

```python
from django.utils.functional import cached_property

# استبدال @property بـ @cached_property
@cached_property
def full_path(self):
    if self.parent:
        return f"{self.parent.full_path} > {self.name}"
    return self.name
```

**في Queries:**
```python
# إضافة select_related
accounts = Account.objects.select_related('parent')
```

---

##### ج) Product.current_stock

**الملف:** `inventory/models.py` السطور 115-132

```python
# الكود الحالي (استبداله)
@property
def current_stock(self):
    from django.db.models import Sum
    
    # استعلام واحد بدلاً من حلقة
    total = VariantStock.objects.filter(
        variant__product=self
    ).aggregate(total=Sum('quantity'))['total']
    
    return total or 0
```

**أفضل حل:**
```python
# في QuerySet/Manager
class ProductQuerySet(models.QuerySet):
    def with_stock(self):
        from django.db.models import Sum
        return self.annotate(
            stock_total=Sum('variants__variantstock__quantity')
        )

class Product(models.Model):
    objects = ProductQuerySet.as_manager()
    
    # ...

# الاستخدام
products = Product.objects.with_stock()
# الوصول: product.stock_total
```

---

#### 1.2 إضافة Composite Indexes (1 ساعة)

##### أ) Order Model

**الملف:** `orders/models.py`

```python
class Order(models.Model):
    # ... existing fields
    
    class Meta:
        indexes = [
            # للبحث حسب user + status
            models.Index(fields=['user', 'status'], name='order_user_status_idx'),
            
            # لترتيب حسب status + created_at
            models.Index(fields=['status', '-created_at'], name='order_status_date_idx'),
            
            # للبحث حسب branch + تاريخ
            models.Index(fields=['branch', 'created_at'], name='order_branch_date_idx'),
            
            # للبحث حسب customer
            models.Index(fields=['customer', '-created_at'], name='order_customer_idx'),
        ]
```

**إنشاء Migration:**
```bash
python manage.py makemigrations orders --name add_composite_indexes
python manage.py migrate orders
```

---

##### ب) Product Model

**الملف:** `inventory/models.py`

```python
class Product(models.Model):
    # ... existing fields
    
    class Meta:
        indexes = [
            # للبحث حسب category + active
            models.Index(fields=['category', 'is_active'], name='prod_cat_active_idx'),
            
            # للبحث حسب SKU (فريد وسريع)
            models.Index(fields=['sku'], name='prod_sku_idx'),
            
            # للبحث حسب الاسم (مع التطبيقات المستقبلية للبحث)
            models.Index(fields=['name'], name='prod_name_idx'),
        ]
```

---

##### ج) ManufacturingOrder Model

**الملف:** `manufacturing/models.py`

```python
class ManufacturingOrder(models.Model):
    # ... existing fields
    
    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at'], name='mfg_status_date_idx'),
            models.Index(fields=['production_line', 'status'], name='mfg_line_status_idx'),
        ]
```

---

#### 1.3 إضافة select_related/prefetch_related للـ Views (4 ساعات)

##### أ) orders/views.py

```python
# في order_list view
def order_list(request):
    orders = Order.objects.select_related(
        'user',
        'customer',
        'branch',
        'salesperson',
    ).prefetch_related(
        'items__product',
        'items__product__category',
    ).filter(
        # filters...
    )
```

##### ب) manufacturing/views.py

```python
# في ManufacturingOrderListView
class ManufacturingOrderListView(ListView):
    def get_queryset(self):
        return ManufacturingOrder.objects.select_related(
            'order',
            'production_line',
        ).prefetch_related(
            'items__product',
            'items__order_item',
        )
```

##### ج) complaints/views.py

```python
# في ComplaintListView
class ComplaintListView(ListView):
    def get_queryset(self):
        return Complaint.objects.select_related(
            'order',
            'order__customer',
            'complaint_type',
            'assigned_to',
        ).prefetch_related(
            'evaluation_set',
        )
```

---

### ✅ Phase 1 Checklist:

- [ ] إصلاح Order.total_discount_amount
- [ ] إصلاح Account.full_path
- [ ] إصلاح Product.current_stock
- [ ] إنشاء migrations لـ composite indexes
- [ ] تطبيق migrations
- [ ] إضافة select_related لـ orders/views.py
- [ ] إضافة select_related لـ manufacturing/views.py
- [ ] إضافة select_related لـ complaints/views.py
- [ ] إضافة select_related لـ inventory/views.py
- [ ] تشغيل django-debug-toolbar للتحقق
- [ ] قياس عدد الاستعلامات (قبل/بعد)
- [ ] اختبار الوظائف الرئيسية
- [ ] مراقبة استخدام الذاكرة

**الوقت الفعلي:** 7-10 ساعات  
**التحسين المتوقع:** 70-85% تقليل في استعلامات DB

---

## Phase 2: Caching & APIs

**الوقت المتوقع:** 6 ساعات  
**المخاطر:** منخفضة-متوسطة  
**التحسين المتوقع:** 50-70% تحسين في page load  
**البدء:** الأسبوع 2  

### المهام:

#### 2.1 تفعيل Cache Middleware (30 دقيقة)

**الملف:** `crm/settings.py`

```python
MIDDLEWARE = [
    'django.middleware.cache.UpdateCacheMiddleware',  # ← إضافة أولاً
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    # ... middleware أخرى
    'django.middleware.cache.FetchFromCacheMiddleware',  # ← إضافة أخيراً
]

# Cache settings
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 300  # 5 minutes
CACHE_MIDDLEWARE_KEY_PREFIX = 'homeupdate'
```

---

#### 2.2 إضافة Template Fragment Caching (2 ساعات)

##### أ) base.html - Navigation

**الملف:** `templates/base.html`

```django
{% load cache %}

{# Cache navigation per user for 5 minutes #}
{% cache 300 navbar request.user.id %}
<nav class="navbar">
    <!-- محتوى navbar -->
</nav>
{% endcache %}

{# Cache notifications dropdown per user for 1 minute #}
{% cache 60 notifications request.user.id %}
<div class="notifications-dropdown">
    <!-- قائمة الإشعارات -->
</div>
{% endcache %}
```

---

##### ب) admin_dashboard.html - Statistics

**الملف:** `templates/admin_dashboard.html`

```django
{% load cache %}

{# Cache dashboard statistics for 10 minutes #}
{% cache 600 dashboard_stats %}
<div class="statistics-cards">
    <!-- بطاقات الإحصائيات -->
</div>
{% endcache %}

{# Cache charts data for 15 minutes #}
{% cache 900 dashboard_charts %}
<div class="charts-section">
    <!-- الرسوم البيانية -->
</div>
{% endcache %}
```

---

#### 2.3 إضافة API Response Caching (2 ساعات)

**الملف:** `orders/api_views.py`

```python
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

# للـ function-based views
@api_view(['GET'])
@cache_page(60 * 5)  # 5 minutes
def order_list_api(request):
    # ...

# للـ class-based views
class OrderViewSet(viewsets.ModelViewSet):
    @method_decorator(cache_page(60 * 5))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @method_decorator(cache_page(60 * 10))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
```

**الملفات المتأثرة:**
- `accounts/api_views.py`
- `inventory/api_views.py`
- `complaints/api_views.py`
- `reports/api_views.py`

---

#### 2.4 إضافة Rate Limiting (30 دقيقة)

**الملف:** `crm/settings.py`

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',      # 100 طلب/ساعة للمستخدمين غير المسجلين
        'user': '1000/hour',     # 1000 طلب/ساعة للمستخدمين المسجلين
    },
    # ... باقي الإعدادات
}
```

---

#### 2.5 تحسين Odoo Integration (1 ساعة)

**الملف:** `odoo_db_manager/models.py`

```python
from django.utils.functional import cached_property

# استبدال @property بـ @cached_property
@cached_property
def connection_status(self):
    # نفس الكود الحالي
    # ...
```

**الملف:** `odoo_db_manager/services/database_service.py`

```python
# توحيد timeout values
ODOO_CONNECTION_TIMEOUT = 10  # seconds

# في جميع psycopg2.connect calls
conn = psycopg2.connect(
    # ...
    connect_timeout=ODOO_CONNECTION_TIMEOUT,
)
```

---

### ✅ Phase 2 Checklist:

- [ ] إضافة cache middleware
- [ ] إضافة template caching في base.html
- [ ] إضافة template caching في admin_dashboard.html
- [ ] إضافة API caching لـ orders
- [ ] إضافة API caching لـ inventory
- [ ] إضافة API caching لـ complaints
- [ ] تفعيل rate limiting
- [ ] تحسين Odoo connection (cached_property)
- [ ] اختبار cache invalidation
- [ ] مراقبة Redis hit rate
- [ ] اختبار rate limiting

**الوقت الفعلي:** 5-7 ساعات  
**التحسين المتوقع:** 50-70% في page load

---

## Phase 3: Frontend & Static

**الوقت المتوقع:** 5 ساعات  
**المخاطر:** منخفضة  
**التحسين المتوقع:** 40-60% في first load  
**البدء:** الأسبوع 3  

### المهام:

#### 3.1 تثبيت و تهيئة django-compressor (1 ساعة)

```bash
pip install django-compressor
```

**الملف:** `crm/settings.py`

```python
INSTALLED_APPS += [
    'compressor',
]

# Compressor settings
COMPRESS_ENABLED = True
COMPRESS_OFFLINE = True  # للـ production
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.rCSSMinFilter',
]
COMPRESS_JS_FILTERS = [
    'compressor.filters.jsmin.JSMinFilter',
]

STATICFILES_FINDERS += [
    'compressor.finders.CompressorFinder',
]
```

---

#### 3.2 ضغط CSS Files (1.5 ساعة)

**الملف:** `templates/base.html`

```django
{% load compress %}

{# قبل - 23 ملف CSS منفصل #}
{# ... #}

{# بعد - ملف واحد مضغوط #}
{% compress css %}
    <link rel="stylesheet" href="{% static 'css/style.css' %}">
    <link rel="stylesheet" href="{% static 'css/modern-black-theme.css' %}">
    <link rel="stylesheet" href="{% static 'css/custom-theme-enhancements.css' %}">
    <link rel="stylesheet" href="{% static 'css/modern-black-fixes.css' %}">
    <link rel="stylesheet" href="{% static 'css/unified-status-system.css' %}">
    <link rel="stylesheet" href="{% static 'css/responsive-footer.css' %}">
    {# ... باقي الملفات المخصصة #}
{% endcompress %}
```

**التحسين:** من 23 طلب → 3-5 طلبات

---

#### 3.3 ضغط JavaScript Files (1.5 ساعة)

**الملف:** `templates/base.html`

```django
{% load compress %}

{% compress js %}
    <script src="{% static 'js/order_form_simplified.js' %}"></script>
    <script src="{% static 'js/complaints-quick-actions.js' %}"></script>
    <script src="{% static 'js/admin-dashboard.js' %}"></script>
    {# ... باقي الملفات #}
{% endcompress %}
```

**التحسين:** من 400KB → ~120KB (تحسين 70%)

---

#### 3.4 إضافة Lazy Loading للصور (1 ساعة)

**البحث في جميع Templates:**

```bash
# ابحث عن جميع <img> tags
grep -r "<img" templates/
```

**الإصلاح:**

```html
<!-- قبل -->
<img src="{{ user.avatar.url }}" alt="{{ user.name }}">

<!-- بعد -->
<img src="{{ user.avatar.url }}" alt="{{ user.name }}" loading="lazy">
```

**الملفات المتأثرة:**
- `templates/accounts/activity_dashboard.html`
- `templates/accounts/activity_logs_list.html`
- `templates/accounts/profile.html`
- جميع templates تحتوي على صور في loops

---

### ✅ Phase 3 Checklist:

- [ ] تثبيت django-compressor
- [ ] تهيئة compressor في settings
- [ ] تطبيق CSS compression في base.html
- [ ] تطبيق JS compression في base.html
- [ ] إضافة lazy loading لجميع الصور
- [ ] تشغيل `python manage.py compress`
- [ ] جمع الملفات الثابتة `collectstatic`
- [ ] اختبار visual للصفحات
- [ ] قياس حجم الملفات (قبل/بعد)
- [ ] اختبار سرعة التحميل

**الوقت الفعلي:** 4-6 ساعات  
**التحسين المتوقع:** 40-60% في first page load

---

## Phase 4: Celery & Background

**الوقت المتوقع:** 6 ساعات  
**المخاطر:** متوسطة  
**التحسين المتوقع:** 90%+ موثوقية  
**البدء:** الأسبوع 4  

### المهام:

#### 4.1 زيادة Global Timeouts (15 دقيقة)

**الملف:** `crm/celery.py`

```python
# السطور 42-44
app.conf.update(
    task_soft_time_limit=600,    # 10 minutes (كانت 180)
    task_time_limit=660,         # 11 minutes (كانت 300)
    result_expires=3600,         # 1 hour (كانت 1800)
    
    # إعدادات إضافية مهمة
    worker_max_memory_per_child=256000,  # 256MB (كانت 80MB)
    worker_max_tasks_per_child=100,      # (كانت 20)
)
```

---

#### 4.2 إضافة Retry Logic لـ WhatsApp Tasks (30 دقيقة) 🔴 CRITICAL

**الملف:** `whatsapp/tasks.py`

```python
from celery import shared_task
import requests

@shared_task(
    bind=True,
    autoretry_for=(requests.exceptions.RequestException,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    retry_backoff=True,
    retry_backoff_max=600,
)
def send_whatsapp_notification_task(self, message_id):
    try:
        # ... الكود الحالي
        pass
    except Exception as exc:
        # Log the error
        logger.error(f"WhatsApp task failed: {exc}")
        raise self.retry(exc=exc)
```

---

#### 4.3 إضافة Retry Logic لباقي Tasks (3 ساعات)

**القالب العام:**

```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 10},
    retry_backoff=True,
    retry_backoff_max=600,
)
def my_task(self, *args, **kwargs):
    try:
        # task logic
        pass
    except Exception as exc:
        logger.error(f"Task {self.name} failed: {exc}")
        raise self.retry(exc=exc)
```

**الملفات المتأثرة:**
- `orders/tasks.py` - 5 tasks بحاجة لـ retry
- `inventory/tasks.py` - 2 tasks
- `odoo_db_manager/tasks.py` - 5 tasks
- `installations/tasks.py` - 4 tasks
- `complaints/tasks.py` - 5 tasks

---

#### 4.4 نقل Heavy Signals إلى Celery (2 ساعات)

##### أ) Cloudflare Sync Signal

**الملف:** `inventory/signals.py`

```python
from django.db import transaction

@receiver(post_save, sender=Product)
def queue_cloudflare_sync(sender, instance, **kwargs):
    # بدلاً من المزامنة الفورية
    from inventory.tasks import sync_product_cloudflare_task
    
    # تأخير التنفيذ حتى commit
    transaction.on_commit(
        lambda: sync_product_cloudflare_task.delay(instance.id)
    )
```

**إنشاء Task الجديد:**

```python
# في inventory/tasks.py
@shared_task(
    bind=True,
    autoretry_for=(requests.exceptions.RequestException,),
    retry_kwargs={'max_retries': 3},
)
def sync_product_cloudflare_task(self, product_id):
    try:
        from public.cloudflare_sync import sync_single_product
        product = Product.objects.get(id=product_id)
        sync_single_product(product)
    except Exception as exc:
        raise self.retry(exc=exc)
```

---

##### ب) Order Notification Signal

**الملف:** `orders/signals.py`

```python
@receiver(post_save, sender=Order)
def queue_order_notifications(sender, instance, created, **kwargs):
    from orders.tasks import create_order_notifications_task
    
    transaction.on_commit(
        lambda: create_order_notifications_task.delay(instance.id, created)
    )
```

---

### ✅ Phase 4 Checklist:

- [ ] زيادة global timeouts في celery.py
- [ ] إضافة retry لـ WhatsApp tasks
- [ ] إضافة retry لـ Orders tasks
- [ ] إضافة retry لـ Inventory tasks
- [ ] إضافة retry لـ Odoo tasks
- [ ] إضافة retry لـ Installations tasks
- [ ] إضافة retry لـ Complaints tasks
- [ ] نقل Cloudflare sync لـ Celery
- [ ] نقل Order notifications لـ Celery
- [ ] إعادة تشغيل Celery workers
- [ ] مراقبة Celery logs لمدة 24 ساعة
- [ ] اختبار retry logic يدوياً

**الوقت الفعلي:** 5-7 ساعات  
**التحسين المتوقع:** 90%+ موثوقية في background tasks

---

## استراتيجية الاختبار

### قبل البدء:

```bash
# 1. Backup قاعدة البيانات
pg_dump homeupdate_db > backup_$(date +%Y%m%d).sql

# 2. تثبيت أدوات القياس
pip install django-debug-toolbar django-silk locust

# 3. إنشاء فرع Git
git checkout -b performance-optimization
```

---

### أثناء كل Phase:

#### اختبار Development:

```bash
# 1. تشغيل السيرفر
python manage.py runserver

# 2. فتح django-debug-toolbar
# زيارة: http://localhost:8000/__debug__/

# 3. فتح django-silk
# زيارة: http://localhost:8000/silk/

# 4. قياس الـ queries
# في django-debug-toolbar -> SQL panel
# قبل التحسين: XX queries
# بعد التحسين: YY queries
```

---

#### اختبار الأداء:

```python
# locustfile.py
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def index_page(self):
        self.client.get("/")
    
    @task(2)
    def order_list(self):
        self.client.get("/orders/")
    
    @task(1)
    def api_orders(self):
        self.client.get("/api/orders/")

# تشغيل
# locust -f locustfile.py --host http://localhost:8000
```

---

#### قياس التحسين:

```python
# في Django shell
from django.test.utils import override_settings
from django.db import connection, reset_queries
from django.contrib.auth import get_user_model

User = get_user_model()

# قياس عدد الاستعلامات
with override_settings(DEBUG=True):
    reset_queries()
    
    # تنفيذ العملية
    orders = Order.objects.select_related('user').all()[:10]
    for order in orders:
        print(order.user.email)
    
    # عدد الاستعلامات
    print(f"Queries: {len(connection.queries)}")
```

---

### بعد كل Phase:

#### Checklist:

- [ ] جميع الاختبارات الموجودة تعمل
- [ ] لا توجد أخطاء في logs
- [ ] التحقق من عدد الاستعلامات (يجب أن ينخفض)
- [ ] التحقق من وقت الاستجابة (يجب أن يتحسن)
- [ ] التحقق من استخدام الذاكرة (يجب أن يستقر)
- [ ] اختبار يدوي للصفحات الرئيسية
- [ ] جمع feedback من مستخدم اختباري

---

## خطة Rollback

### إذا حدثت مشاكل:

#### Phase 0 (Config):

```bash
# 1. Rollback .env
cp .env.backup .env

# 2. Rollback settings.py
git checkout crm/settings.py

# 3. إعادة تشغيل
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

---

#### Phase 1 (Database):

```bash
# 1. Rollback migrations
python manage.py migrate orders XXXX  # رقم migration السابق
python manage.py migrate inventory XXXX
python manage.py migrate accounting XXXX

# 2. Rollback code
git revert <commit-hash>

# 3. إعادة تشغيل
sudo systemctl restart gunicorn
```

---

#### Phase 2-4 (Features):

```python
# استخدام feature flags في settings.py

# Phase 2
ENABLE_TEMPLATE_CACHING = False
ENABLE_API_CACHING = False
ENABLE_RATE_LIMITING = False

# Phase 3
ENABLE_STATIC_COMPRESSION = False

# Phase 4
ENABLE_ASYNC_SIGNALS = False
```

---

## الملخص النهائي

### الوقت الإجمالي:

| Phase | الوقت المتوقع | المخاطر | التحسين |
|-------|---------------|----------|----------|
| Phase 0 | 2 ساعة | منخفضة | 20-30% |
| Phase 1 | 8 ساعات | متوسطة | 70-85% |
| Phase 2 | 6 ساعات | منخفضة-متوسطة | 50-70% |
| Phase 3 | 5 ساعات | منخفضة | 40-60% |
| Phase 4 | 6 ساعات | متوسطة | 90%+ |
| **الإجمالي** | **27 ساعة** | - | **70-90%** |

---

### التحسين المتوقع النهائي:

| Metric | الحالي | بعد التحسينات | التحسين |
|--------|--------|---------------|----------|
| Page Load Time | 5-8s | 0.5-1s | **85-90%** ↓ |
| DB Queries/Page | 200+ | 15-20 | **90%** ↓ |
| API Response | 2-3s | 200-500ms | **75-85%** ↓ |
| Memory Usage | عالي | متوسط | **40-50%** ↓ |
| Cache Hit Rate | 0% | 70%+ | **∞** ↑ |
| Task Failures | 30% | <2% | **93%** ↓ |
| Static Files Size | 575KB | 150KB | **74%** ↓ |

---

### الأولويات:

**P0 (حرجة - فوري):**
1. Phase 0: إصلاحات الأمان والإعدادات (2 ساعة)

**P1 (مهمة جداً - الأسبوع 1):**
2. Phase 1: قواعد البيانات (8 ساعات)

**P2 (مهمة - الأسبوع 2-3):**
3. Phase 2: Caching & APIs (6 ساعات)
4. Phase 3: Frontend & Static (5 ساعات)

**P3 (تحسينات - الأسبوع 4):**
5. Phase 4: Celery & Background (6 ساعات)

---

**تم الإعداد بواسطة:** Sisyphus AI Agent  
**التاريخ:** 3 يناير 2026  
**الإصدار:** 1.0

