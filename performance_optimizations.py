"""
تحسينات الأداء الشاملة للنظام
يوفر هذا الملف مجموعة من التحسينات لتحسين أداء النظام
"""

from django.core.cache import cache
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """
    محسن الاستعلامات
    """
    
    @staticmethod
    def optimize_user_queryset(queryset):
        """
        تحسين استعلام المستخدمين
        """
        return queryset.select_related(
            'branch'
        ).prefetch_related(
            'departments',
            'user_roles__role',
            'groups',
            'user_permissions'
        )
    
    @staticmethod
    def optimize_customer_queryset(queryset):
        """
        تحسين استعلام العملاء
        """
        return queryset.select_related(
            'category', 'branch', 'created_by'
        ).prefetch_related(
            'customer_orders',
            'inspections',
            'notes_history'
        )
    
    @staticmethod
    def optimize_order_queryset(queryset):
        """
        تحسين استعلام الطلبات
        """
        return queryset.select_related(
            'customer', 'salesperson', 'branch', 'created_by'
        ).prefetch_related(
            'items',
            'payments'
        )
    
    @staticmethod
    def optimize_product_queryset(queryset):
        """
        تحسين استعلام المنتجات
        """
        return queryset.select_related(
            'category'
        ).prefetch_related(
            'transactions__created_by'
        ).annotate(
            stock_in=Sum(
                'transactions__quantity',
                filter=Q(transactions__transaction_type='in')
            ),
            stock_out=Sum(
                'transactions__quantity',
                filter=Q(transactions__transaction_type='out')
            )
        ).annotate(
            current_stock_calc=F('stock_in') - F('stock_out')
        )


class CacheManager:
    """
    مدير التخزين المؤقت
    """
    
    CACHE_TIMEOUTS = {
        'short': 300,      # 5 دقائق
        'medium': 1800,    # 30 دقيقة
        'long': 3600,      # ساعة واحدة
        'very_long': 86400 # يوم واحد
    }
    
    @staticmethod
    def get_cache_key(prefix, *args):
        """
        إنشاء مفتاح التخزين المؤقت
        """
        return f"{prefix}_{'_'.join(str(arg) for arg in args)}"
    
    @staticmethod
    def get_cached_data(key, timeout='medium'):
        """
        الحصول على بيانات من التخزين المؤقت
        """
        return cache.get(key, timeout=CacheManager.CACHE_TIMEOUTS[timeout])
    
    @staticmethod
    def set_cached_data(key, data, timeout='medium'):
        """
        حفظ بيانات في التخزين المؤقت
        """
        cache.set(key, data, CacheManager.CACHE_TIMEOUTS[timeout])
    
    @staticmethod
    def invalidate_cache_pattern(pattern):
        """
        مسح التخزين المؤقت حسب النمط
        """
        # ملاحظة: هذا يتطلب Redis أو Memcached مع دعم النمط
        pass


class DashboardOptimizer:
    """
    محسن لوحة التحكم
    """
    
    @staticmethod
    def get_cached_dashboard_stats(user=None):
        """
        الحصول على إحصائيات لوحة التحكم من التخزين المؤقت
        """
        cache_key = f"dashboard_stats_{user.id if user else 'all'}"
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = DashboardOptimizer.calculate_dashboard_stats(user)
            cache.set(cache_key, stats, 300)  # 5 دقائق
        
        return stats
    
    @staticmethod
    def calculate_dashboard_stats(user=None):
        """
        حساب إحصائيات لوحة التحكم
        """
        from customers.models import Customer
        from orders.models import Order
        from inventory.models import Product
        from inspections.models import Inspection
        from manufacturing.models import ManufacturingOrder
        
        # إحصائيات العملاء
        customers = Customer.objects.all()
        if user and not user.is_superuser:
            customers = customers.filter(branch=user.branch)
        
        customer_stats = {
            'total': customers.count(),
            'active': customers.filter(status='active').count(),
            'new_this_month': customers.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count()
        }
        
        # إحصائيات الطلبات
        orders = Order.objects.all()
        if user and not user.is_superuser:
            orders = orders.filter(Q(created_by=user) | Q(branch=user.branch))
        
        order_stats = {
            'total': orders.count(),
            'pending': orders.filter(status='pending').count(),
            'completed': orders.filter(status='completed').count(),
            'recent': list(orders.select_related('customer').order_by('-created_at')[:5])
        }
        
        # إحصائيات المخزون
        products = Product.objects.all()
        inventory_stats = {
            'total_products': products.count(),
            'low_stock': products.filter(
                current_stock__gt=0,
                current_stock__lte=F('minimum_stock')
            ).count(),
            'out_of_stock': products.filter(current_stock__lte=0).count()
        }
        
        # إحصائيات المعاينات
        inspections = Inspection.objects.all()
        if user and not user.is_superuser:
            inspections = inspections.filter(
                Q(inspector=user) | Q(created_by=user)
            )
        
        inspection_stats = {
            'total': inspections.count(),
            'pending': inspections.filter(status='pending').count(),
            'completed': inspections.filter(status='completed').count()
        }
        
        # إحصائيات التصنيع
        manufacturing_orders = ManufacturingOrder.objects.all()
        if user and not user.is_superuser:
            manufacturing_orders = manufacturing_orders.filter(
                Q(created_by=user) | Q(order__branch=user.branch)
            )
        
        manufacturing_stats = {
            'total': manufacturing_orders.count(),
            'active': manufacturing_orders.exclude(
                status__in=['completed', 'cancelled']
            ).count(),
            'completed_today': manufacturing_orders.filter(
                completed_at__date=timezone.now().date()
            ).count()
        }
        
        return {
            'customers': customer_stats,
            'orders': order_stats,
            'inventory': inventory_stats,
            'inspections': inspection_stats,
            'manufacturing': manufacturing_stats,
            'last_updated': timezone.now()
        }


class DatabaseOptimizer:
    """
    محسن قاعدة البيانات
    """
    
    @staticmethod
    def create_indexes():
        """
        إنشاء فهارس مهمة
        """
        from django.db import connection
        
        indexes = [
            # فهارس المستخدمين
            "CREATE INDEX IF NOT EXISTS idx_user_branch ON accounts_user(branch_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_created_at ON accounts_user(created_at);",
            
            # فهارس العملاء
            "CREATE INDEX IF NOT EXISTS idx_customer_branch ON customers_customer(branch_id);",
            "CREATE INDEX IF NOT EXISTS idx_customer_status ON customers_customer(status);",
            "CREATE INDEX IF NOT EXISTS idx_customer_created_at ON customers_customer(created_at);",
            
            # فهارس الطلبات
            "CREATE INDEX IF NOT EXISTS idx_order_customer ON orders_order(customer_id);",
            "CREATE INDEX IF NOT EXISTS idx_order_status ON orders_order(status);",
            "CREATE INDEX IF NOT EXISTS idx_order_created_at ON orders_order(created_at);",
            
            # فهارس المنتجات
            "CREATE INDEX IF NOT EXISTS idx_product_category ON inventory_product(category_id);",
            "CREATE INDEX IF NOT EXISTS idx_product_stock ON inventory_product(current_stock);",
            
            # فهارس المعاينات
            "CREATE INDEX IF NOT EXISTS idx_inspection_customer ON inspections_inspection(customer_id);",
            "CREATE INDEX IF NOT EXISTS idx_inspection_status ON inspections_inspection(status);",
            "CREATE INDEX IF NOT EXISTS idx_inspection_scheduled_date ON inspections_inspection(scheduled_date);",
        ]
        
        with connection.cursor() as cursor:
            for index in indexes:
                try:
                    cursor.execute(index)
                except Exception as e:
                    logger.warning(f"فشل في إنشاء الفهرس: {e}")
    
    @staticmethod
    def analyze_tables():
        """
        تحليل الجداول لتحسين الأداء
        """
        from django.db import connection
        
        tables = [
            'accounts_user',
            'customers_customer',
            'orders_order',
            'inventory_product',
            'inspections_inspection',
            'manufacturing_manufacturingorder'
        ]
        
        with connection.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f"ANALYZE {table};")
                except Exception as e:
                    logger.warning(f"فشل في تحليل الجدول {table}: {e}")


class MiddlewareOptimizer:
    """
    محسن الوسطاء
    """
    
    @staticmethod
    def get_performance_middleware():
        """
        إضافة وسطاء لتحسين الأداء
        """
        return [
            'django.middleware.cache.UpdateCacheMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.cache.FetchFromCacheMiddleware',
        ]
    
    @staticmethod
    def get_cache_settings():
        """
        إعدادات التخزين المؤقت
        """
        return {
            'CACHES': {
                'default': {
                    'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                    'LOCATION': 'redis://127.0.0.1:6379/1',
                    'OPTIONS': {
                        'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    }
                }
            },
            'CACHE_MIDDLEWARE_SECONDS': 300,
            'CACHE_MIDDLEWARE_KEY_PREFIX': 'homeupdate',
        }


class APIOptimizer:
    """
    محسن API
    """
    
    @staticmethod
    def optimize_api_response(data, include_metadata=True):
        """
        تحسين استجابة API
        """
        response = {
            'data': data,
            'success': True
        }
        
        if include_metadata:
            response['metadata'] = {
                'timestamp': timezone.now().isoformat(),
                'version': '1.0.0'
            }
        
        return response
    
    @staticmethod
    def paginate_queryset(queryset, page, page_size=20):
        """
        تقسيم الاستعلام إلى صفحات
        """
        from django.core.paginator import Paginator
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'results': page_obj.object_list,
            'pagination': {
                'page': page_obj.number,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'total_count': paginator.count
            }
        }


class MonitoringOptimizer:
    """
    محسن المراقبة
    """
    
    @staticmethod
    def log_slow_queries(threshold=1.0):
        """
        تسجيل الاستعلامات البطيئة
        """
        from django.db import connection
        from django.conf import settings
        
        if settings.DEBUG:
            for query in connection.queries:
                if float(query['time']) > threshold:
                    logger.warning(f"استعلام بطيء: {query['sql']} - الوقت: {query['time']}s")
    
    @staticmethod
    def get_performance_metrics():
        """
        الحصول على مقاييس الأداء
        """
        from django.db import connection
        
        metrics = {
            'total_queries': len(connection.queries),
            'total_time': sum(float(q['time']) for q in connection.queries),
            'average_time': sum(float(q['time']) for q in connection.queries) / len(connection.queries) if connection.queries else 0,
            'slow_queries': len([q for q in connection.queries if float(q['time']) > 1.0])
        }
        
        return metrics


# وظائف مساعدة للتحسين
def optimize_all():
    """
    تطبيق جميع التحسينات
    """
    try:
        # إنشاء الفهارس
        DatabaseOptimizer.create_indexes()
        
        # تحليل الجداول
        DatabaseOptimizer.analyze_tables()
        
        logger.info("تم تطبيق جميع التحسينات بنجاح")
        
    except Exception as e:
        logger.error(f"فشل في تطبيق التحسينات: {e}")


def clear_all_cache():
    """
    مسح جميع التخزين المؤقت
    """
    try:
        cache.clear()
        logger.info("تم مسح جميع التخزين المؤقت")
    except Exception as e:
        logger.error(f"فشل في مسح التخزين المؤقت: {e}")


def get_system_performance_report():
    """
    الحصول على تقرير أداء النظام
    """
    from django.db import connection
    
    report = {
        'database': {
            'total_queries': len(connection.queries),
            'total_time': sum(float(q['time']) for q in connection.queries),
            'average_time': sum(float(q['time']) for q in connection.queries) / len(connection.queries) if connection.queries else 0,
        },
        'cache': {
            'cache_hits': getattr(cache, '_cache_hits', 0),
            'cache_misses': getattr(cache, '_cache_misses', 0),
        },
        'memory': {
            'memory_usage': 'N/A',  # يتطلب psutil
        },
        'recommendations': []
    }
    
    # توصيات التحسين
    if report['database']['average_time'] > 0.1:
        report['recommendations'].append('تحسين استعلامات قاعدة البيانات')
    
    if report['database']['total_queries'] > 100:
        report['recommendations'].append('إضافة المزيد من التخزين المؤقت')
    
    return report 