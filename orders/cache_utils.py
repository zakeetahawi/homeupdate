"""
أدوات التخزين المؤقت لتحسين أداء النماذج
"""

from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


def clear_customer_related_cache(customer_id):
    """تنظيف التخزين المؤقت المرتبط بعميل معين"""
    cache_keys = [
        f'customer_inspections_{customer_id}',
        f'customer_orders_{customer_id}',
        f'customer_data_{customer_id}',
    ]
    
    for key in cache_keys:
        cache.delete(key)


def clear_user_related_cache(user_id, branch_id=None):
    """تنظيف التخزين المؤقت المرتبط بمستخدم معين"""
    cache_keys = [
        f'user_customers_{user_id}_{branch_id or "no_branch"}',
        f'user_permissions_{user_id}',
    ]
    
    if branch_id:
        cache_keys.append(f'branch_salespersons_{branch_id}')
    
    for key in cache_keys:
        cache.delete(key)


def clear_branch_related_cache(branch_id):
    """تنظيف التخزين المؤقت المرتبط بفرع معين"""
    cache_keys = [
        f'branch_salespersons_{branch_id}',
        f'branch_customers_{branch_id}',
        f'branch_stats_{branch_id}',
    ]
    
    for key in cache_keys:
        cache.delete(key)


# إشارات لتنظيف التخزين المؤقت عند تحديث البيانات
@receiver(post_save, sender='customers.Customer')
@receiver(post_delete, sender='customers.Customer')
def clear_customer_cache(sender, instance, **kwargs):
    """تنظيف التخزين المؤقت عند تحديث أو حذف عميل"""
    clear_customer_related_cache(instance.id)
    
    # تنظيف تخزين مؤقت الفرع أيضاً
    if instance.branch_id:
        clear_branch_related_cache(instance.branch_id)


@receiver(post_save, sender='inspections.Inspection')
@receiver(post_delete, sender='inspections.Inspection')
def clear_inspection_cache(sender, instance, **kwargs):
    """تنظيف التخزين المؤقت عند تحديث أو حذف معاينة"""
    if instance.customer_id:
        clear_customer_related_cache(instance.customer_id)


@receiver(post_save, sender='accounts.Salesperson')
@receiver(post_delete, sender='accounts.Salesperson')
def clear_salesperson_cache(sender, instance, **kwargs):
    """تنظيف التخزين المؤقت عند تحديث أو حذف بائع"""
    if instance.branch_id:
        clear_branch_related_cache(instance.branch_id)


@receiver(post_save, sender='accounts.User')
def clear_user_cache(sender, instance, **kwargs):
    """تنظيف التخزين المؤقت عند تحديث مستخدم"""
    clear_user_related_cache(instance.id, instance.branch_id if instance.branch else None)


def get_cached_customer_data(customer_id):
    """جلب بيانات العميل من التخزين المؤقت أو قاعدة البيانات"""
    cache_key = f'customer_data_{customer_id}'
    customer_data = cache.get(cache_key)
    
    if customer_data is None:
        from customers.models import Customer
        try:
            customer = Customer.objects.select_related('branch', 'category').get(id=customer_id)
            customer_data = {
                'id': customer.id,
                'name': customer.name,
                'code': customer.code,
                'phone': customer.phone,
                'email': customer.email,
                'branch_name': customer.branch.name if customer.branch else '',
                'category_name': customer.category.name if customer.category else '',
                'customer_type': customer.customer_type,
            }
            # تخزين مؤقت لمدة 30 دقيقة
            cache.set(cache_key, customer_data, 1800)
        except Customer.DoesNotExist:
            return None
    
    return customer_data


def get_cached_user_customers(user):
    """جلب عملاء المستخدم من التخزين المؤقت"""
    cache_key = f'user_customers_{user.id}_{user.branch_id if user.branch else "no_branch"}'
    return cache.get(cache_key)


def get_cached_customer_inspections(customer_id, limit=10):
    """جلب معاينات العميل من التخزين المؤقت"""
    cache_key = f'customer_inspections_{customer_id}'
    cached_inspections = cache.get(cache_key)
    
    if cached_inspections is None:
        from inspections.models import Inspection
        inspections = Inspection.objects.filter(
            customer_id=customer_id
        ).select_related('customer').only(
            'id', 'contract_number', 'created_at', 'customer__name'
        ).order_by('-created_at')[:limit]
        
        cached_inspections = [
            {
                'id': insp.id,
                'contract_number': insp.contract_number,
                'created_at': insp.created_at.strftime('%Y-%m-%d'),
                'customer_name': insp.customer.name if insp.customer else 'عميل غير محدد'
            }
            for insp in inspections
        ]
        
        # تخزين مؤقت لمدة 5 دقائق
        cache.set(cache_key, cached_inspections, 300)
    
    return cached_inspections


def warm_up_cache():
    """تسخين التخزين المؤقت بالبيانات الأساسية"""
    from customers.models import Customer
    from accounts.models import User, Salesperson
    from inspections.models import Inspection
    
    # تسخين بيانات العملاء النشطين
    active_customers = Customer.objects.filter(status='active').select_related('branch')[:100]
    for customer in active_customers:
        get_cached_customer_data(customer.id)
    
    # تسخين بيانات المستخدمين النشطين
    active_users = User.objects.filter(is_active=True).select_related('branch')[:50]
    for user in active_users:
        cache_key = f'user_customers_{user.id}_{user.branch_id if user.branch else "no_branch"}'
        # سيتم ملء هذا عند أول استخدام
    
    print("تم تسخين التخزين المؤقت بنجاح")


def clear_all_form_cache():
    """تنظيف جميع التخزين المؤقت المرتبط بالنماذج"""
    from django.core.cache import cache
    
    # قائمة بأنماط المفاتيح المختلفة
    patterns = [
        'customer_inspections_*',
        'user_customers_*',
        'branch_salespersons_*',
        'customer_data_*',
        'user_permissions_*',
        'branch_stats_*',
    ]
    
    # في Redis، يمكن استخدام KEYS pattern لحذف مفاتيح متعددة
    # لكن هنا سنستخدم طريقة أبسط
    cache.clear()
    print("تم تنظيف جميع التخزين المؤقت")


def get_cache_stats():
    """إحصائيات التخزين المؤقت"""
    try:
        from django.core.cache import cache
        from django.core.cache.backends.redis import RedisCache
        
        if isinstance(cache, RedisCache):
            # إحصائيات Redis
            redis_client = cache._cache.get_client(write=True)
            info = redis_client.info()
            
            return {
                'type': 'Redis',
                'used_memory': info.get('used_memory_human', 'غير معروف'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': round(info.get('keyspace_hits', 0) / max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100, 2)
            }
        else:
            return {
                'type': 'Other',
                'message': 'إحصائيات غير متاحة لهذا النوع من التخزين المؤقت'
            }
    except Exception as e:
        return {
            'type': 'Error',
            'message': f'خطأ في جلب الإحصائيات: {str(e)}'
        }
