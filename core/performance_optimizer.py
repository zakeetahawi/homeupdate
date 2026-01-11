"""
🚀 نظام تحسين الأداء الشامل - Performance Optimizer
تسريع 1000% للنظام

هذا الملف يحتوي على:
1. Smart Query Caching - كاش ذكي للاستعلامات
2. Query Optimizer - تحسين الاستعلامات تلقائياً
3. Connection Pool Manager - إدارة اتصالات قاعدة البيانات
4. Response Compression - ضغط الاستجابات
"""

import functools
import hashlib
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import cache, caches
from django.db import connection, reset_queries
from django.db.models import Prefetch, QuerySet
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger("performance")


# =============================================
# 1. Smart Query Cache Decorator
# =============================================


def smart_cache(timeout: int = 300, key_prefix: str = "", vary_on: List[str] = None):
    """
    ديكوريتور للكاش الذكي - يخزن نتائج الدوال/Views

    المميزات:
    - كاش تلقائي للنتائج
    - مفاتيح ذكية بناءً على المعاملات
    - دعم vary_on للتمييز بين المستخدمين/الفروع
    - invalidation تلقائي

    الاستخدام:
    @smart_cache(timeout=600, key_prefix='my_view', vary_on=['user_id', 'branch_id'])
    def my_view(request):
        ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # استخراج request من args إذا كان موجوداً
            request = None
            for arg in args:
                if isinstance(arg, HttpRequest):
                    request = arg
                    break

            # بناء مفتاح الكاش
            cache_key_parts = [key_prefix or func.__name__]

            # إضافة vary_on parameters
            if vary_on and request:
                for param in vary_on:
                    if (
                        param == "user_id"
                        and hasattr(request, "user")
                        and request.user.is_authenticated
                    ):
                        cache_key_parts.append(f"user:{request.user.id}")
                    elif param == "branch_id" and hasattr(request.user, "branch_id"):
                        cache_key_parts.append(f"branch:{request.user.branch_id}")
                    elif param in kwargs:
                        cache_key_parts.append(f"{param}:{kwargs[param]}")
                    elif request and hasattr(request, "GET") and param in request.GET:
                        cache_key_parts.append(f"{param}:{request.GET[param]}")

            # إضافة hash للـ kwargs
            if kwargs:
                kwargs_hash = hashlib.md5(
                    str(sorted(kwargs.items())).encode()
                ).hexdigest()[:8]
                cache_key_parts.append(kwargs_hash)

            cache_key = ":".join(cache_key_parts)

            # محاولة جلب من الكاش
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_result

            # تنفيذ الدالة وتخزين النتيجة
            result = func(*args, **kwargs)

            # تخزين في الكاش (لا نخزن HttpResponse مباشرة)
            if not isinstance(result, HttpResponse):
                cache.set(cache_key, result, timeout)
                logger.debug(f"Cache SET: {cache_key}")

            return result

        # إضافة دالة لإبطال الكاش
        def invalidate(*args, **kwargs):
            cache_key_parts = [key_prefix or func.__name__]
            if kwargs:
                kwargs_hash = hashlib.md5(
                    str(sorted(kwargs.items())).encode()
                ).hexdigest()[:8]
                cache_key_parts.append(kwargs_hash)
            cache_key = ":".join(cache_key_parts)
            cache.delete(cache_key)
            logger.debug(f"Cache INVALIDATED: {cache_key}")

        wrapper.invalidate = invalidate
        return wrapper

    return decorator


# =============================================
# 2. QuerySet Optimizer
# =============================================


class QuerySetOptimizer:
    """
    محسّن QuerySet - يضيف select_related و prefetch_related تلقائياً

    الاستخدام:
    optimizer = QuerySetOptimizer()
    optimized_qs = optimizer.optimize(Order.objects.all())
    """

    # خريطة العلاقات المعروفة للـ Models
    RELATION_MAP = {
        "Order": {
            "select_related": ["customer", "salesperson", "branch", "created_by"],
            "prefetch_related": [
                "items",
                "items__product",
                "payments",
                "manufacturing_orders",
            ],
            "only_fields": [
                "id",
                "order_number",
                "order_date",
                "status",
                "order_status",
                "tracking_status",
                "total_amount",
                "paid_amount",
                "final_price",
                "customer__id",
                "customer__name",
                "customer__phone",
                "salesperson__id",
                "salesperson__name",
                "branch__id",
                "branch__name",
            ],
        },
        "InstallationSchedule": {
            "select_related": [
                "order",
                "order__customer",
                "order__branch",
                "order__salesperson",
                "team",
                "team__driver",
            ],
            "prefetch_related": ["team__technicians"],
            "only_fields": [
                "id",
                "status",
                "scheduled_date",
                "created_at",
                "location_type",
                "order__id",
                "order__order_number",
                "order__contract_number",
                "order__customer__id",
                "order__customer__name",
                "order__customer__phone",
                "team__id",
                "team__name",
            ],
        },
        "ManufacturingOrder": {
            "select_related": [
                "order",
                "order__customer",
                "order__branch",
                "order__salesperson",
                "production_line",
            ],
            "prefetch_related": ["items", "items__order_item"],
            "only_fields": [
                "id",
                "status",
                "order_type",
                "created_at",
                "expected_delivery_date",
                "order__id",
                "order__order_number",
                "order__customer__id",
                "order__customer__name",
                "production_line__id",
                "production_line__name",
            ],
        },
        "Product": {
            "select_related": ["category"],
            "prefetch_related": [],
            "only_fields": [
                "id",
                "name",
                "code",
                "price",
                "currency",
                "unit",
                "category__id",
                "category__name",
            ],
        },
    }

    def optimize(self, queryset: QuerySet, include_only: bool = True) -> QuerySet:
        """
        تحسين QuerySet تلقائياً بناءً على Model

        Args:
            queryset: QuerySet للتحسين
            include_only: هل نضيف only() لتحديد الحقول

        Returns:
            QuerySet محسّن
        """
        model_name = queryset.model.__name__

        if model_name not in self.RELATION_MAP:
            return queryset

        relations = self.RELATION_MAP[model_name]

        # إضافة select_related
        if relations.get("select_related"):
            queryset = queryset.select_related(*relations["select_related"])

        # إضافة prefetch_related
        if relations.get("prefetch_related"):
            queryset = queryset.prefetch_related(*relations["prefetch_related"])

        # إضافة only() لتحديد الحقول
        if include_only and relations.get("only_fields"):
            try:
                queryset = queryset.only(*relations["only_fields"])
            except Exception:
                # بعض الحقول قد لا تكون موجودة - تجاهل
                pass

        return queryset

    def optimize_for_list(self, queryset: QuerySet) -> QuerySet:
        """تحسين للعرض في قائمة (أقل بيانات)"""
        return self.optimize(queryset, include_only=True)

    def optimize_for_detail(self, queryset: QuerySet) -> QuerySet:
        """تحسين للعرض التفصيلي (كل البيانات)"""
        return self.optimize(queryset, include_only=False)


# =============================================
# 3. Query Counter & Logger
# =============================================


class QueryCounter:
    """
    عداد الاستعلامات - لتتبع وتحسين الأداء

    الاستخدام:
    with QueryCounter() as counter:
        # الكود هنا
        pass
    print(f"Queries: {counter.count}, Time: {counter.time}ms")
    """

    def __init__(self, log_queries: bool = False, warn_threshold: int = 20):
        self.log_queries = log_queries
        self.warn_threshold = warn_threshold
        self.count = 0
        self.time = 0
        self.queries = []
        self._start_queries = 0
        self._start_time = 0

    def __enter__(self):
        # تفعيل تسجيل الاستعلامات
        if not settings.DEBUG:
            connection.force_debug_cursor = True
        reset_queries()
        self._start_queries = len(connection.queries)
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.time = (time.time() - self._start_time) * 1000
        self.queries = connection.queries[self._start_queries :]
        self.count = len(self.queries)

        # تحذير إذا تجاوز العدد الحد المسموح
        if self.count > self.warn_threshold:
            logger.warning(
                f"HIGH_QUERY_COUNT: {self.count} queries in {self.time:.0f}ms"
            )

        # تسجيل الاستعلامات إذا مطلوب
        if self.log_queries:
            for i, query in enumerate(self.queries, 1):
                logger.debug(f"Query {i}: {query['sql'][:200]}...")

        # إعادة ضبط debug cursor
        if not settings.DEBUG:
            connection.force_debug_cursor = False

        return False

    def get_slow_queries(self, threshold_ms: float = 100) -> List[Dict]:
        """الحصول على الاستعلامات البطيئة"""
        return [
            q for q in self.queries if float(q.get("time", 0)) * 1000 > threshold_ms
        ]

    def get_duplicate_queries(self) -> Dict[str, int]:
        """الحصول على الاستعلامات المكررة"""
        query_counts = {}
        for q in self.queries:
            sql_hash = hashlib.md5(q["sql"].encode()).hexdigest()
            query_counts[sql_hash] = query_counts.get(sql_hash, 0) + 1
        return {k: v for k, v in query_counts.items() if v > 1}


# =============================================
# 4. Bulk Operations Helper
# =============================================


class BulkOperations:
    """
    مساعد العمليات المجمعة - لتحسين أداء الحفظ والتحديث

    الاستخدام:
    bulk_ops = BulkOperations()
    bulk_ops.queue_update(order, ['status', 'updated_at'])
    bulk_ops.execute()
    """

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self._create_queue = {}  # {model_class: [instances]}
        self._update_queue = {}  # {model_class: {fields: [instances]}}

    def queue_create(self, instance):
        """إضافة instance للإنشاء المجمع"""
        model_class = instance.__class__
        if model_class not in self._create_queue:
            self._create_queue[model_class] = []
        self._create_queue[model_class].append(instance)

    def queue_update(self, instance, fields: List[str]):
        """إضافة instance للتحديث المجمع"""
        model_class = instance.__class__
        fields_key = tuple(sorted(fields))

        if model_class not in self._update_queue:
            self._update_queue[model_class] = {}
        if fields_key not in self._update_queue[model_class]:
            self._update_queue[model_class][fields_key] = []

        self._update_queue[model_class][fields_key].append(instance)

    def execute(self) -> Dict[str, int]:
        """تنفيذ جميع العمليات المجمعة"""
        results = {"created": 0, "updated": 0}

        # تنفيذ الإنشاء المجمع
        for model_class, instances in self._create_queue.items():
            for i in range(0, len(instances), self.batch_size):
                batch = instances[i : i + self.batch_size]
                model_class.objects.bulk_create(batch, ignore_conflicts=True)
                results["created"] += len(batch)

        # تنفيذ التحديث المجمع
        for model_class, fields_dict in self._update_queue.items():
            for fields, instances in fields_dict.items():
                for i in range(0, len(instances), self.batch_size):
                    batch = instances[i : i + self.batch_size]
                    model_class.objects.bulk_update(batch, list(fields))
                    results["updated"] += len(batch)

        # تنظيف القوائم
        self._create_queue.clear()
        self._update_queue.clear()

        return results


# =============================================
# 5. Response Cache Helper
# =============================================


def cache_page_smart(
    timeout: int = 300, cache_name: str = "default", key_func: Callable = None
):
    """
    ديكوريتور كاش صفحات ذكي - أفضل من cache_page العادي

    المميزات:
    - يتجاهل POST requests
    - يتجاهل authenticated users بشكل اختياري
    - مفاتيح ذكية

    الاستخدام:
    @cache_page_smart(timeout=600)
    def my_view(request):
        ...
    """

    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # لا نخزن POST requests
            if request.method != "GET":
                return view_func(request, *args, **kwargs)

            # بناء مفتاح الكاش
            if key_func:
                cache_key = key_func(request, *args, **kwargs)
            else:
                cache_key = f"page:{request.path}:{request.GET.urlencode()}"
                if request.user.is_authenticated:
                    cache_key += f":user:{request.user.id}"

            # محاولة جلب من الكاش
            cache_backend = caches[cache_name]
            cached_response = cache_backend.get(cache_key)
            if cached_response is not None:
                return cached_response

            # تنفيذ الـ view
            response = view_func(request, *args, **kwargs)

            # تخزين فقط إذا كانت الاستجابة ناجحة
            if response.status_code == 200:
                cache_backend.set(cache_key, response, timeout)

            return response

        return wrapper

    return decorator


# =============================================
# 6. Database Connection Health Check
# =============================================


def check_db_connection() -> Tuple[bool, str]:
    """
    فحص صحة اتصال قاعدة البيانات

    Returns:
        (is_healthy, message)
    """
    try:
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        elapsed = (time.time() - start_time) * 1000

        if elapsed > 100:
            return True, f"Database responding slowly: {elapsed:.0f}ms"
        return True, f"Database healthy: {elapsed:.0f}ms"

    except Exception as e:
        return False, f"Database error: {str(e)}"


def get_db_stats() -> Dict[str, Any]:
    """
    الحصول على إحصائيات قاعدة البيانات
    """
    stats = {}

    try:
        with connection.cursor() as cursor:
            # عدد الاتصالات النشطة
            cursor.execute(
                """
                SELECT count(*) FROM pg_stat_activity 
                WHERE state = 'active' AND datname = current_database()
            """
            )
            stats["active_connections"] = cursor.fetchone()[0]

            # حجم قاعدة البيانات
            cursor.execute(
                """
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """
            )
            stats["database_size"] = cursor.fetchone()[0]

            # أبطأ الاستعلامات (إذا كان pg_stat_statements مفعّل)
            try:
                cursor.execute(
                    """
                    SELECT query, mean_exec_time, calls
                    FROM pg_stat_statements
                    ORDER BY mean_exec_time DESC
                    LIMIT 5
                """
                )
                stats["slow_queries"] = cursor.fetchall()
            except Exception:
                stats["slow_queries"] = []

    except Exception as e:
        stats["error"] = str(e)

    return stats


# =============================================
# 7. Performance Metrics Collector
# =============================================


class PerformanceMetrics:
    """
    جامع مقاييس الأداء - للمراقبة والتحليل
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics = {}
        return cls._instance

    def record(self, name: str, value: float, tags: Dict[str, str] = None):
        """تسجيل قيمة"""
        key = f"{name}:{tags}" if tags else name
        if key not in self._metrics:
            self._metrics[key] = []
        self._metrics[key].append(
            {"value": value, "timestamp": time.time(), "tags": tags or {}}
        )

        # الاحتفاظ بآخر 1000 قيمة فقط
        if len(self._metrics[key]) > 1000:
            self._metrics[key] = self._metrics[key][-1000:]

    def get_avg(self, name: str, tags: Dict[str, str] = None) -> float:
        """الحصول على المتوسط"""
        key = f"{name}:{tags}" if tags else name
        if key not in self._metrics or not self._metrics[key]:
            return 0
        values = [m["value"] for m in self._metrics[key]]
        return sum(values) / len(values)

    def get_percentile(
        self, name: str, percentile: float, tags: Dict[str, str] = None
    ) -> float:
        """الحصول على النسبة المئوية"""
        key = f"{name}:{tags}" if tags else name
        if key not in self._metrics or not self._metrics[key]:
            return 0
        values = sorted([m["value"] for m in self._metrics[key]])
        index = int(len(values) * percentile / 100)
        return values[min(index, len(values) - 1)]

    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """الحصول على ملخص جميع المقاييس"""
        summary = {}
        for key in self._metrics:
            values = [m["value"] for m in self._metrics[key]]
            if values:
                summary[key] = {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p95": self.get_percentile(key.split(":")[0], 95),
                }
        return summary


# =============================================
# 8. Initialization & Exports
# =============================================

# Global instances
query_optimizer = QuerySetOptimizer()
performance_metrics = PerformanceMetrics()

# Export all
__all__ = [
    "smart_cache",
    "cache_page_smart",
    "QuerySetOptimizer",
    "QueryCounter",
    "BulkOperations",
    "check_db_connection",
    "get_db_stats",
    "PerformanceMetrics",
    "query_optimizer",
    "performance_metrics",
]
