"""
تحسينات الأداء المتقدمة - Caching & Query Optimization
========================================================

هذا الملف يحتوي على utility functions لتحسين الأداء
"""

from decimal import Decimal
from django.core.cache import cache
from django.db.models import Sum, Count, Q, F
from functools import wraps
import hashlib
import json


def cache_query_result(timeout=300, key_prefix='query'):
    """
    Decorator لحفظ نتائج الاستعلامات في الـ cache
    
    Usage:
        @cache_query_result(timeout=600, key_prefix='customer_stats')
        def get_customer_stats(customer_id):
            return CustomerFinancialSummary.objects.get(customer_id=customer_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # إنشاء cache key فريد
            args_str = json.dumps([str(arg) for arg in args], sort_keys=True)
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
            cache_key = f"{key_prefix}_{func.__name__}_{hashlib.md5((args_str + kwargs_str).encode()).hexdigest()}"
            
            # محاولة الحصول من الـ cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # تنفيذ الدالة وحفظ النتيجة
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator


def invalidate_cache(pattern):
    """
    حذف جميع الـ cache keys التي تطابق النمط
    
    Usage:
        invalidate_cache('customer_stats_*')
    """
    import logging
    logger = logging.getLogger('accounting')
    try:
        from django.core.cache import cache
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern(pattern)
    except Exception as e:
        logger.warning('فشل في حذف الـ cache بالنمط %s: %s', pattern, e)


def get_dashboard_stats_cached(timeout=300):
    """
    الحصول على إحصائيات Dashboard مع caching
    """
    from accounting.models import Account, Transaction, CustomerFinancialSummary
    
    cache_key = 'accounting_dashboard_main_stats'
    stats = cache.get(cache_key)
    
    if not stats:
        stats = {
            'total_accounts': Account.objects.filter(is_active=True).count(),
            'total_transactions': Transaction.objects.filter(status='posted').count(),
            'pending_transactions': Transaction.objects.filter(status='draft').count(),
            'total_receivables': CustomerFinancialSummary.objects.filter(
                total_debt__gt=0
            ).aggregate(total=Sum('total_debt'))['total'] or Decimal('0'),
        }
        cache.set(cache_key, stats, timeout)
    
    return stats


def get_customer_summary_cached(customer_id, timeout=600):
    """
    الحصول على ملخص العميل مع caching
    """
    from accounting.models import CustomerFinancialSummary
    
    cache_key = f'customer_summary_{customer_id}'
    summary = cache.get(cache_key)
    
    if not summary:
        try:
            summary = CustomerFinancialSummary.objects.select_related(
                'customer', 'customer__branch', 'customer__category'
            ).get(customer_id=customer_id)
            cache.set(cache_key, summary, timeout)
        except CustomerFinancialSummary.DoesNotExist:
            return None
    
    return summary


def invalidate_customer_cache(customer_id):
    """
    حذف cache العميل عند التحديث
    """
    cache.delete(f'customer_summary_{customer_id}')
    cache.delete(f'customer_financial_{customer_id}')
    invalidate_cache(f'customer_*_{customer_id}')


def get_optimized_customers_with_debt(limit=100, branch_id=None, salesperson_id=None):
    """
    جلب العملاء المديونين بطريقة محسّنة
    """
    from accounting.models import CustomerFinancialSummary
    from django.db.models import Prefetch
    from orders.models import Order
    
    # بناء cache key
    cache_key = f'customers_debt_{limit}_{branch_id}_{salesperson_id}'
    result = cache.get(cache_key)
    
    if not result:
        # بناء الفلاتر
        orders_filter = Q(final_price__gt=F('paid_amount'))
        
        if branch_id:
            try:
                orders_filter &= Q(branch_id=int(branch_id))
            except (ValueError, TypeError):
                pass
        
        if salesperson_id:
            try:
                orders_filter &= Q(created_by_id=int(salesperson_id))
            except (ValueError, TypeError):
                pass
        
        # Prefetch محسّن
        unpaid_orders_prefetch = Prefetch(
            'customer__customer_orders',
            queryset=Order.objects.filter(orders_filter).select_related(
                'branch', 'created_by'
            ).only(
                'id', 'order_number', 'final_price', 'paid_amount',
                'branch__name', 'created_by__first_name', 'created_by__username'
            ).order_by('-created_at')[:10],
            to_attr='prefetched_unpaid_orders'
        )
        
        # جلب البيانات
        result = CustomerFinancialSummary.objects.filter(
            total_debt__gt=0
        ).select_related(
            'customer'
        ).only(
            'total_debt', 'total_paid', 'total_orders_amount', 'financial_status',
            'customer__id', 'customer__name', 'customer__code', 'customer__phone'
        ).prefetch_related(
            unpaid_orders_prefetch
        ).order_by('-total_debt')[:limit]
        
        result = list(result)  # تحويل إلى list للـ cache
        cache.set(cache_key, result, 300)  # 5 دقائق
    
    return result


def optimize_queryset_fields(queryset, model_name, action='list'):
    """
    تحسين الحقول المحمّلة حسب الاستخدام
    
    Usage:
        customers = optimize_queryset_fields(
            Customer.objects.all(), 
            'Customer', 
            action='list'
        )
    """
    
    field_maps = {
        'Customer': {
            'list': ['id', 'name', 'code', 'phone', 'branch__name'],
            'detail': None,  # جميع الحقول
        },
        'Transaction': {
            'list': ['id', 'transaction_number', 'date', 'transaction_type', 
                     'status', 'total_debit', 'total_credit'],
            'detail': None,
        },
        'Order': {
            'list': ['id', 'order_number', 'final_price', 'paid_amount', 
                     'remaining_amount', 'branch__name'],
            'detail': None,
        }
    }
    
    if model_name in field_maps and field_maps[model_name].get(action):
        fields = field_maps[model_name][action]
        return queryset.only(*fields)
    
    return queryset


def bulk_update_customer_summaries(customer_ids=None):
    """
    تحديث ملخصات العملاء بكفاءة
    
    Usage:
        bulk_update_customer_summaries([1, 2, 3])  # عملاء محددين
        bulk_update_customer_summaries()  # جميع العملاء
    """
    from accounting.models import CustomerFinancialSummary
    
    if customer_ids:
        summaries = CustomerFinancialSummary.objects.filter(customer_id__in=customer_ids)
    else:
        summaries = CustomerFinancialSummary.objects.all()
    
    updated_count = 0
    for summary in summaries.select_related('customer').iterator(chunk_size=100):
        summary.refresh()
        summary.save()
        invalidate_customer_cache(summary.customer_id)
        updated_count += 1
    
    return updated_count


# إشارات لتحديث الـ cache تلقائياً
def setup_cache_signals():
    """
    إعداد الإشارات لتحديث الـ cache تلقائياً
    
    يتم استدعاؤها في apps.py
    """
    from django.db.models.signals import post_save, post_delete
    from accounting.models import Transaction, CustomerFinancialSummary
    from orders.models import Order, Payment
    
    def invalidate_dashboard_cache(sender, instance, **kwargs):
        cache.delete('accounting_dashboard_main_stats')
    
    def invalidate_customer_summary_cache(sender, instance, **kwargs):
        if hasattr(instance, 'customer'):
            invalidate_customer_cache(instance.customer_id)
        elif hasattr(instance, 'customer_id'):
            invalidate_customer_cache(instance.customer_id)
    
    # Transaction changes -> invalidate dashboard
    post_save.connect(invalidate_dashboard_cache, sender=Transaction)
    post_delete.connect(invalidate_dashboard_cache, sender=Transaction)
    
    # Order/Payment changes -> invalidate customer cache
    post_save.connect(invalidate_customer_summary_cache, sender=Order)
    post_save.connect(invalidate_customer_summary_cache, sender=Payment)
    post_delete.connect(invalidate_customer_summary_cache, sender=Order)
    post_delete.connect(invalidate_customer_summary_cache, sender=Payment)


# ============================================
# Query Optimization Helpers
# ============================================

def count_efficient(queryset):
    """
    Count محسّن لـ PostgreSQL
    
    Usage:
        count = count_efficient(Customer.objects.all())
    """
    # للجداول الصغيرة، استخدم count() العادي
    # للجداول الكبيرة، استخدم تقدير PostgreSQL
    try:
        count = queryset.count()
        if count > 10000:
            # استخدام تقدير سريع
            from django.db import connection
            table = queryset.model._meta.db_table
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT reltuples::bigint FROM pg_class WHERE relname = %s",
                    [table]
                )
                approximate_count = cursor.fetchone()
                if approximate_count:
                    return int(approximate_count[0])
        return count
    except Exception:
        return queryset.count()


def exists_efficient(queryset):
    """
    exists() محسّن
    
    Usage:
        has_records = exists_efficient(customers)
    """
    return queryset.exists()


def aggregate_with_cache(queryset, aggregations, cache_key, timeout=300):
    """
    aggregate مع caching
    
    Usage:
        result = aggregate_with_cache(
            Customer.objects.all(),
            {'total': Sum('balance')},
            'customers_total_balance',
            timeout=600
        )
    """
    result = cache.get(cache_key)
    if not result:
        result = queryset.aggregate(**aggregations)
        cache.set(cache_key, result, timeout)
    return result
