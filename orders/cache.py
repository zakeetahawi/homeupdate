"""
نظام التخزين المؤقت للطلبات
"""

from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

# مفاتيح التخزين المؤقت
CACHE_KEYS = {
    'delivery_settings': 'orders:delivery_settings',
    'customer_data': 'orders:customer:{}',
    'product_search': 'orders:product_search:{}',
    'order_stats': 'orders:stats:{}',
    'branch_data': 'orders:branch:{}',
    'salesperson_data': 'orders:salesperson:{}',
}

# أوقات انتهاء الصلاحية (بالثواني)
CACHE_TIMEOUTS = {
    'delivery_settings': 3600,  # ساعة واحدة
    'customer_data': 1800,      # 30 دقيقة
    'product_search': 300,      # 5 دقائق
    'order_stats': 600,         # 10 دقائق
    'branch_data': 3600,        # ساعة واحدة
    'salesperson_data': 1800,   # 30 دقيقة
}


class OrderCache:
    """فئة إدارة التخزين المؤقت للطلبات"""
    
    @staticmethod
    def get_delivery_settings():
        """الحصول على إعدادات التسليم من التخزين المؤقت"""
        cache_key = CACHE_KEYS['delivery_settings']
        settings_data = cache.get(cache_key)
        
        if settings_data is None:
            try:
                from .models import DeliveryTimeSettings
                settings_data = {}
                
                # جلب جميع إعدادات التسليم
                delivery_settings = DeliveryTimeSettings.objects.all()
                for setting in delivery_settings:
                    settings_data[setting.order_type] = {
                        'days': setting.delivery_days,
                        'description': setting.description,
                        'is_active': setting.is_active
                    }
                
                # تخزين في الكاش
                cache.set(cache_key, settings_data, CACHE_TIMEOUTS['delivery_settings'])
                logger.info("تم تحديث إعدادات التسليم في التخزين المؤقت")
                
            except Exception as e:
                logger.error(f"خطأ في جلب إعدادات التسليم: {str(e)}")
                settings_data = {}
        
        return settings_data
    
    @staticmethod
    def get_customer_data(customer_id):
        """الحصول على بيانات العميل من التخزين المؤقت"""
        cache_key = CACHE_KEYS['customer_data'].format(customer_id)
        customer_data = cache.get(cache_key)
        
        if customer_data is None:
            try:
                from customers.models import Customer
                customer = Customer.objects.get(id=customer_id)
                
                customer_data = {
                    'id': customer.id,
                    'name': customer.name,
                    'phone': customer.phone,
                    'email': customer.email,
                    'address': customer.address,
                    'code': customer.code,
                    'created_at': customer.created_at.isoformat() if customer.created_at else None
                }
                
                # تخزين في الكاش
                cache.set(cache_key, customer_data, CACHE_TIMEOUTS['customer_data'])
                logger.debug(f"تم تحديث بيانات العميل {customer_id} في التخزين المؤقت")
                
            except Exception as e:
                logger.error(f"خطأ في جلب بيانات العميل {customer_id}: {str(e)}")
                customer_data = None
        
        return customer_data
    
    @staticmethod
    def get_product_search_results(query):
        """الحصول على نتائج البحث عن المنتجات من التخزين المؤقت"""
        # تنظيف الاستعلام وإنشاء مفتاح فريد
        clean_query = query.strip().lower()
        cache_key = CACHE_KEYS['product_search'].format(hash(clean_query))
        
        search_results = cache.get(cache_key)
        
        if search_results is None:
            try:
                from inventory.models import Product
                
                # البحث في المنتجات
                products = Product.objects.filter(
                    Q(name__icontains=query) |
                    Q(code__icontains=query) |
                    Q(description__icontains=query)
                ).select_related('category').order_by('name')[:20]  # تحديد عدد النتائج
                
                search_results = []
                for product in products:
                    search_results.append({
                        'id': product.id,
                        'name': product.name,
                        'code': product.code,
                        'price': float(product.price),
                        'current_stock': product.current_stock,
                        'category': product.category.name if product.category else None,
                        'description': product.description
                    })
                
                # تخزين في الكاش
                cache.set(cache_key, search_results, CACHE_TIMEOUTS['product_search'])
                logger.debug(f"تم تحديث نتائج البحث '{query}' في التخزين المؤقت")
                
            except Exception as e:
                logger.error(f"خطأ في البحث عن المنتجات '{query}': {str(e)}")
                search_results = []
        
        return search_results
    
    @staticmethod
    def get_order_statistics(date_range='month'):
        """الحصول على إحصائيات الطلبات من التخزين المؤقت"""
        cache_key = CACHE_KEYS['order_stats'].format(date_range)
        stats_data = cache.get(cache_key)
        
        if stats_data is None:
            try:
                from .services import OrderService
                from datetime import datetime, timedelta
                from django.utils import timezone
                
                # تحديد نطاق التاريخ
                now = timezone.now()
                if date_range == 'week':
                    start_date = now - timedelta(days=7)
                elif date_range == 'month':
                    start_date = now - timedelta(days=30)
                elif date_range == 'year':
                    start_date = now - timedelta(days=365)
                else:
                    start_date = now - timedelta(days=30)
                
                # جلب الإحصائيات
                stats_data = OrderService.get_order_statistics(
                    start_date=start_date,
                    end_date=now
                )
                
                # تخزين في الكاش
                cache.set(cache_key, stats_data, CACHE_TIMEOUTS['order_stats'])
                logger.debug(f"تم تحديث إحصائيات الطلبات '{date_range}' في التخزين المؤقت")
                
            except Exception as e:
                logger.error(f"خطأ في جلب إحصائيات الطلبات '{date_range}': {str(e)}")
                stats_data = {}
        
        return stats_data
    
    @staticmethod
    def get_branch_data(branch_id):
        """الحصول على بيانات الفرع من التخزين المؤقت"""
        cache_key = CACHE_KEYS['branch_data'].format(branch_id)
        branch_data = cache.get(cache_key)
        
        if branch_data is None:
            try:
                from accounts.models import Branch
                branch = Branch.objects.get(id=branch_id)
                
                branch_data = {
                    'id': branch.id,
                    'name': branch.name,
                    'address': branch.address,
                    'phone': branch.phone,
                    'is_active': branch.is_active
                }
                
                # تخزين في الكاش
                cache.set(cache_key, branch_data, CACHE_TIMEOUTS['branch_data'])
                logger.debug(f"تم تحديث بيانات الفرع {branch_id} في التخزين المؤقت")
                
            except Exception as e:
                logger.error(f"خطأ في جلب بيانات الفرع {branch_id}: {str(e)}")
                branch_data = None
        
        return branch_data
    
    @staticmethod
    def get_salesperson_data(salesperson_id):
        """الحصول على بيانات البائع من التخزين المؤقت"""
        cache_key = CACHE_KEYS['salesperson_data'].format(salesperson_id)
        salesperson_data = cache.get(cache_key)
        
        if salesperson_data is None:
            try:
                from accounts.models import Salesperson
                salesperson = Salesperson.objects.select_related('user', 'branch').get(id=salesperson_id)

                salesperson_data = {
                    'id': salesperson.id,
                    'name': salesperson.name,
                    'display_name': salesperson.get_display_name(),
                    'employee_number': salesperson.employee_number,
                    'user_id': salesperson.user.id if salesperson.user else None,
                    'username': salesperson.user.username if salesperson.user else None,
                    'branch_name': salesperson.branch.name if salesperson.branch else None,
                    'is_active': salesperson.is_active
                }
                
                # تخزين في الكاش
                cache.set(cache_key, salesperson_data, CACHE_TIMEOUTS['salesperson_data'])
                logger.debug(f"تم تحديث بيانات البائع {salesperson_id} في التخزين المؤقت")
                
            except Exception as e:
                logger.error(f"خطأ في جلب بيانات البائع {salesperson_id}: {str(e)}")
                salesperson_data = None
        
        return salesperson_data
    
    @staticmethod
    def invalidate_customer_cache(customer_id):
        """إلغاء التخزين المؤقت لبيانات العميل"""
        cache_key = CACHE_KEYS['customer_data'].format(customer_id)
        cache.delete(cache_key)
        logger.debug(f"تم إلغاء التخزين المؤقت لبيانات العميل {customer_id}")
    
    @staticmethod
    def invalidate_delivery_settings_cache():
        """إلغاء التخزين المؤقت لإعدادات التسليم"""
        cache_key = CACHE_KEYS['delivery_settings']
        cache.delete(cache_key)
        logger.debug("تم إلغاء التخزين المؤقت لإعدادات التسليم")
    
    @staticmethod
    def invalidate_product_search_cache():
        """إلغاء جميع نتائج البحث عن المنتجات"""
        # حذف جميع مفاتيح البحث عن المنتجات
        try:
            # استخدام pattern matching لحذف جميع مفاتيح البحث
            pattern = CACHE_KEYS['product_search'].format('*')
            cache.delete_pattern(pattern)
            logger.debug("تم إلغاء التخزين المؤقت لنتائج البحث عن المنتجات")
        except AttributeError:
            # في حالة عدم دعم delete_pattern
            logger.warning("لا يمكن حذف نتائج البحث بالنمط - يرجى تحديث إعدادات الكاش")
    
    @staticmethod
    def invalidate_order_stats_cache():
        """إلغاء التخزين المؤقت لإحصائيات الطلبات"""
        for date_range in ['week', 'month', 'year']:
            cache_key = CACHE_KEYS['order_stats'].format(date_range)
            cache.delete(cache_key)
        logger.debug("تم إلغاء التخزين المؤقت لإحصائيات الطلبات")
    
    @staticmethod
    def clear_all_cache():
        """مسح جميع البيانات المؤقتة للطلبات"""
        try:
            # مسح جميع مفاتيح الطلبات
            for key_pattern in CACHE_KEYS.values():
                if '{}' in key_pattern:
                    # للمفاتيح التي تحتوي على معاملات
                    pattern = key_pattern.replace('{}', '*')
                    try:
                        cache.delete_pattern(pattern)
                    except AttributeError:
                        pass
                else:
                    # للمفاتيح الثابتة
                    cache.delete(key_pattern)
            
            logger.info("تم مسح جميع البيانات المؤقتة للطلبات")
            
        except Exception as e:
            logger.error(f"خطأ في مسح البيانات المؤقتة: {str(e)}")


# دوال مساعدة للاستخدام السريع
def get_cached_delivery_settings():
    """دالة مساعدة للحصول على إعدادات التسليم"""
    return OrderCache.get_delivery_settings()


def get_cached_customer(customer_id):
    """دالة مساعدة للحصول على بيانات العميل"""
    return OrderCache.get_customer_data(customer_id)


def search_products_cached(query):
    """دالة مساعدة للبحث عن المنتجات مع التخزين المؤقت"""
    return OrderCache.get_product_search_results(query)


def get_cached_order_stats(date_range='month'):
    """دالة مساعدة للحصول على إحصائيات الطلبات"""
    return OrderCache.get_order_statistics(date_range)
