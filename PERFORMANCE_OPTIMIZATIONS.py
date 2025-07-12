"""
تحسينات الأداء العامة للنظام
General Performance Optimizations
"""

# =============================================================================
# 1. تحسين استعلامات قاعدة البيانات
# =============================================================================

def optimize_database_queries():
    """
    تحسين استعلامات قاعدة البيانات
    """
    from django.db import models
    from django.db.models import Index, Q
    
    # إضافة فهارس محسنة للنماذج الرئيسية
    class OptimizedUser(models.Model):
        """نموذج مستخدم محسن"""
        
        class Meta:
            indexes = [
                Index(fields=['username']),
                Index(fields=['email']),
                Index(fields=['branch', 'is_active']),
                Index(fields=['created_at']),
                Index(fields=['last_login']),
                Index(fields=['is_staff', 'is_active']),
            ]
    
    class OptimizedCustomer(models.Model):
        """نموذج عميل محسن"""
        
        class Meta:
            indexes = [
                Index(fields=['code']),
                Index(fields=['name']),
                Index(fields=['phone', 'phone2']),
                Index(fields=['email']),
                Index(fields=['status']),
                Index(fields=['customer_type']),
                Index(fields=['branch', 'status']),
                Index(fields=['created_at']),
                Index(fields=['created_by', 'branch']),
            ]
    
    class OptimizedOrder(models.Model):
        """نموذج طلب محسن"""
        
        class Meta:
            indexes = [
                Index(fields=['order_number']),
                Index(fields=['customer']),
                Index(fields=['status']),
                Index(fields=['created_at']),
                Index(fields=['branch', 'status']),
                Index(fields=['created_by', 'branch']),
            ]
    
    class OptimizedProduct(models.Model):
        """نموذج منتج محسن"""
        
        class Meta:
            indexes = [
                Index(fields=['code']),
                Index(fields=['name']),
                Index(fields=['category']),
                Index(fields=['price']),
                Index(fields=['current_stock']),
                Index(fields=['minimum_stock']),
                Index(fields=['is_active']),
            ]

# =============================================================================
# 2. تحسين التخزين المؤقت
# =============================================================================

def create_advanced_cache():
    """
    إنشاء نظام تخزين مؤقت متقدم
    """
    from django.core.cache import cache
    from django.db.models import Sum, Count, Avg
    from datetime import timedelta
    
    class AdvancedCache:
        """نظام تخزين مؤقت متقدم"""
        
        @staticmethod
        def get_cached_dashboard_stats(user=None):
            """الحصول على إحصائيات لوحة التحكم من التخزين المؤقت"""
            cache_key = f'dashboard_stats_{user.id if user else "all"}'
            stats = cache.get(cache_key)
            
            if stats is None:
                from customers.models import Customer
                from orders.models import Order
                from inventory.models import Product
                from django.utils import timezone
                
                today = timezone.now()
                last_month = today - timedelta(days=30)
                
                # إحصائيات العملاء
                customers = Customer.objects.all()
                if user and not user.is_superuser:
                    customers = customers.filter(branch=user.branch)
                
                total_customers = customers.count()
                new_customers_today = customers.filter(
                    created_at__date=today.date()
                ).count()
                new_customers_month = customers.filter(
                    created_at__gte=last_month
                ).count()
                
                # إحصائيات الطلبات
                orders = Order.objects.all()
                if user and not user.is_superuser:
                    orders = orders.filter(branch=user.branch)
                
                total_orders = orders.count()
                orders_today = orders.filter(
                    created_at__date=today.date()
                ).count()
                orders_month = orders.filter(
                    created_at__gte=last_month
                ).count()
                
                # إحصائيات المخزون
                products = Product.objects.all()
                low_stock_products = products.filter(
                    current_stock__lte=models.F('minimum_stock')
                ).count()
                out_of_stock_products = products.filter(
                    current_stock=0
                ).count()
                
                # إحصائيات مالية
                total_revenue = orders.aggregate(
                    total=Sum('final_price')
                )['total'] or 0
                
                monthly_revenue = orders.filter(
                    created_at__gte=last_month
                ).aggregate(
                    total=Sum('final_price')
                )['total'] or 0
                
                stats = {
                    'customers': {
                        'total': total_customers,
                        'new_today': new_customers_today,
                        'new_month': new_customers_month,
                        'growth_rate': calculate_growth_rate(new_customers_month, total_customers)
                    },
                    'orders': {
                        'total': total_orders,
                        'today': orders_today,
                        'month': orders_month,
                        'growth_rate': calculate_growth_rate(orders_month, total_orders)
                    },
                    'inventory': {
                        'low_stock': low_stock_products,
                        'out_of_stock': out_of_stock_products,
                        'total_products': products.count()
                    },
                    'revenue': {
                        'total': total_revenue,
                        'monthly': monthly_revenue,
                        'growth_rate': calculate_growth_rate(monthly_revenue, total_revenue)
                    }
                }
                
                # تخزين لمدة 15 دقيقة
                cache.set(cache_key, stats, 900)
            
            return stats
        
        @staticmethod
        def get_cached_user_data(user):
            """الحصول على بيانات المستخدم من التخزين المؤقت"""
            cache_key = f'user_data_{user.id}'
            user_data = cache.get(cache_key)
            
            if user_data is None:
                user_data = {
                    'departments': list(user.departments.values('id', 'name', 'code')),
                    'permissions': list(user.user_permissions.values_list('codename', flat=True)),
                    'roles': list(user.user_roles.values('role__name', 'role__description')),
                    'branch': {
                        'id': user.branch.id if user.branch else None,
                        'name': user.branch.name if user.branch else None,
                        'code': user.branch.code if user.branch else None
                    } if user.branch else None
                }
                
                # تخزين لمدة ساعة
                cache.set(cache_key, user_data, 3600)
            
            return user_data
        
        @staticmethod
        def get_cached_product_list(filters=None):
            """الحصول على قائمة المنتجات من التخزين المؤقت"""
            cache_key = f'product_list_{hash(str(filters))}'
            products = cache.get(cache_key)
            
            if products is None:
                from inventory.models import Product
                
                queryset = Product.objects.select_related('category')
                
                if filters:
                    if filters.get('category'):
                        queryset = queryset.filter(category_id=filters['category'])
                    if filters.get('search'):
                        queryset = queryset.filter(
                            Q(name__icontains=filters['search']) |
                            Q(code__icontains=filters['search'])
                        )
                    if filters.get('stock_status'):
                        if filters['stock_status'] == 'low':
                            queryset = queryset.filter(
                                current_stock__lte=models.F('minimum_stock')
                            )
                        elif filters['stock_status'] == 'out':
                            queryset = queryset.filter(current_stock=0)
                
                products = list(queryset)
                
                # تخزين لمدة 10 دقائق
                cache.set(cache_key, products, 600)
            
            return products
        
        @staticmethod
        def clear_user_cache(user_id):
            """مسح التخزين المؤقت للمستخدم"""
            cache.delete(f'user_data_{user_id}')
            cache.delete(f'dashboard_stats_{user_id}')
        
        @staticmethod
        def clear_all_cache():
            """مسح جميع التخزين المؤقت"""
            cache.clear()
    
    def calculate_growth_rate(current, total):
        """حساب معدل النمو"""
        if total == 0:
            return 0
        return round((current / total) * 100, 2)

# =============================================================================
# 3. تحسين استعلامات admin.py
# =============================================================================

def optimize_admin_queries():
    """
    تحسين استعلامات لوحة التحكم
    """
    from django.contrib import admin
    
    class OptimizedUserAdmin(admin.ModelAdmin):
        """لوحة تحكم محسنة للمستخدمين"""
        
        def get_queryset(self, request):
            return super().get_queryset(request).select_related(
                'branch'
            ).prefetch_related(
                'departments',
                'user_roles__role',
                'managed_departments',
                'user_permissions'
            )
        
        def get_search_results(self, request, queryset, search_term):
            """تحسين البحث"""
            if search_term:
                queryset = queryset.filter(
                    Q(username__icontains=search_term) |
                    Q(first_name__icontains=search_term) |
                    Q(last_name__icontains=search_term) |
                    Q(email__icontains=search_term) |
                    Q(phone__icontains=search_term)
                )
            return queryset, True
    
    class OptimizedCustomerAdmin(admin.ModelAdmin):
        """لوحة تحكم محسنة للعملاء"""
        
        def get_queryset(self, request):
            return super().get_queryset(request).select_related(
                'category', 'branch', 'created_by'
            ).prefetch_related(
                'customer_orders',
                'inspections'
            )
        
        def get_search_results(self, request, queryset, search_term):
            """تحسين البحث"""
            if search_term:
                queryset = queryset.filter(
                    Q(name__icontains=search_term) |
                    Q(code__icontains=search_term) |
                    Q(phone__icontains=search_term) |
                    Q(phone2__icontains=search_term) |
                    Q(email__icontains=search_term)
                )
            return queryset, True
    
    class OptimizedOrderAdmin(admin.ModelAdmin):
        """لوحة تحكم محسنة للطلبات"""
        
        def get_queryset(self, request):
            return super().get_queryset(request).select_related(
                'customer', 'branch', 'created_by'
            ).prefetch_related(
                'items',
                'payments'
            )
        
        def get_search_results(self, request, queryset, search_term):
            """تحسين البحث"""
            if search_term:
                queryset = queryset.filter(
                    Q(order_number__icontains=search_term) |
                    Q(customer__name__icontains=search_term) |
                    Q(invoice_number__icontains=search_term)
                )
            return queryset, True

# =============================================================================
# 4. تحسين الأداء العام
# =============================================================================

def create_performance_middleware():
    """
    إنشاء وسيط لتحسين الأداء
    """
    import time
    import psutil
    from django.utils.deprecation import MiddlewareMixin
    from django.db import connection
    from django.core.cache import cache
    
    class PerformanceMiddleware(MiddlewareMixin):
        """وسيط لمراقبة وتحسين الأداء"""
        
        def __init__(self, get_response):
            self.get_response = get_response
            self.slow_query_threshold = 0.5  # 500ms
            self.max_queries = 50
        
        def process_request(self, request):
            # تسجيل وقت بداية الطلب
            request.start_time = time.time()
            request.start_queries = len(connection.queries)
            request.start_memory = psutil.Process().memory_info().rss
        
        def process_response(self, request, response):
            # حساب الأداء
            duration = time.time() - request.start_time
            queries = len(connection.queries) - request.start_queries
            memory_used = psutil.Process().memory_info().rss - request.start_memory
            
            # إضافة معلومات الأداء للـ headers
            response['X-Response-Time'] = f'{duration:.3f}s'
            response['X-DB-Queries'] = str(queries)
            response['X-Memory-Used'] = f'{memory_used / 1024 / 1024:.2f}MB'
            
            # تحذير من الأداء البطيء
            if duration > self.slow_query_threshold:
                print(f"⚠️ Slow request: {request.path} took {duration:.3f}s")
            
            if queries > self.max_queries:
                print(f"⚠️ High query count: {request.path} executed {queries} queries")
            
            # تسجيل الأداء في التخزين المؤقت
            self.log_performance(request.path, duration, queries, memory_used)
            
            return response
        
        def log_performance(self, path, duration, queries, memory_used):
            """تسجيل معلومات الأداء"""
            cache_key = f'performance_log_{path}'
            logs = cache.get(cache_key, [])
            
            logs.append({
                'duration': duration,
                'queries': queries,
                'memory_used': memory_used,
                'timestamp': time.time()
            })
            
            # الاحتفاظ بآخر 100 سجل فقط
            if len(logs) > 100:
                logs = logs[-100:]
            
            cache.set(cache_key, logs, 3600)  # ساعة واحدة

# =============================================================================
# 5. تحسين استعلامات النماذج
# =============================================================================

def optimize_model_queries():
    """
    تحسين استعلامات النماذج
    """
    from django.db import models
    from django.db.models import Manager, QuerySet
    
    class OptimizedCustomerQuerySet(QuerySet):
        """QuerySet محسن للعملاء"""
        
        def with_orders(self):
            """تحميل الطلبات مع العملاء"""
            return self.prefetch_related('customer_orders')
        
        def with_inspections(self):
            """تحميل المعاينات مع العملاء"""
            return self.prefetch_related('inspections')
        
        def with_related_data(self):
            """تحميل جميع البيانات المرتبطة"""
            return self.select_related('category', 'branch', 'created_by').prefetch_related(
                'customer_orders',
                'inspections',
                'notes_history'
            )
        
        def active(self):
            """العملاء النشطين فقط"""
            return self.filter(status='active')
        
        def by_branch(self, branch):
            """العملاء حسب الفرع"""
            return self.filter(branch=branch)
        
        def search(self, term):
            """البحث في العملاء"""
            return self.filter(
                Q(name__icontains=term) |
                Q(code__icontains=term) |
                Q(phone__icontains=term) |
                Q(email__icontains=term)
            )
    
    class OptimizedOrderQuerySet(QuerySet):
        """QuerySet محسن للطلبات"""
        
        def with_items(self):
            """تحميل العناصر مع الطلبات"""
            return self.prefetch_related('items')
        
        def with_customer(self):
            """تحميل العميل مع الطلبات"""
            return self.select_related('customer', 'branch', 'created_by')
        
        def with_related_data(self):
            """تحميل جميع البيانات المرتبطة"""
            return self.select_related('customer', 'branch', 'created_by').prefetch_related(
                'items',
                'payments',
                'manufacturing_orders',
                'inspections'
            )
        
        def by_status(self, status):
            """الطلبات حسب الحالة"""
            return self.filter(status=status)
        
        def by_branch(self, branch):
            """الطلبات حسب الفرع"""
            return self.filter(branch=branch)
    
    class OptimizedProductQuerySet(QuerySet):
        """QuerySet محسن للمنتجات"""
        
        def with_stock(self):
            """تحميل معلومات المخزون"""
            return self.annotate(
                stock_in=models.Sum(
                    models.Case(
                        models.When(transactions__transaction_type='in', 
                                   then='transactions__quantity'),
                        default=0,
                        output_field=models.IntegerField()
                    )
                ),
                stock_out=models.Sum(
                    models.Case(
                        models.When(transactions__transaction_type='out', 
                                   then='transactions__quantity'),
                        default=0,
                        output_field=models.IntegerField()
                    )
                )
            ).annotate(
                current_stock=models.F('stock_in') - models.F('stock_out')
            )
        
        def low_stock(self):
            """المنتجات ذات المخزون المنخفض"""
            return self.with_stock().filter(
                current_stock__gt=0,
                current_stock__lte=models.F('minimum_stock')
            )
        
        def out_of_stock(self):
            """المنتجات التي نفدت من المخزون"""
            return self.with_stock().filter(current_stock__lte=0)
        
        def in_stock(self):
            """المنتجات المتوفرة في المخزون"""
            return self.with_stock().filter(current_stock__gt=0)

# =============================================================================
# 6. تحسين التحميل المتأخر
# =============================================================================

def create_lazy_loading():
    """
    إنشاء نظام التحميل المتأخر
    """
    from django.db.models import Manager
    
    class LazyLoadingManager(Manager):
        """مدير للتحميل المتأخر"""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._loaded = False
            self._cache = {}
        
        def get_queryset(self):
            """الحصول على QuerySet مع التحميل المتأخر"""
            if not self._loaded:
                self._loaded = True
                self._cache['queryset'] = super().get_queryset()
            return self._cache['queryset']
        
        def clear_cache(self):
            """مسح التخزين المؤقت"""
            self._loaded = False
            self._cache.clear()

# =============================================================================
# 7. تحسين استعلامات التقارير
# =============================================================================

def optimize_report_queries():
    """
    تحسين استعلامات التقارير
    """
    from django.db.models import Sum, Count, Avg, Q
    from django.utils import timezone
    from datetime import timedelta
    
    class ReportQueryOptimizer:
        """محسن استعلامات التقارير"""
        
        @staticmethod
        def get_sales_report(start_date, end_date, branch=None):
            """تقرير المبيعات"""
            from orders.models import Order
            
            queryset = Order.objects.filter(
                created_at__range=(start_date, end_date)
            ).select_related('customer', 'branch')
            
            if branch:
                queryset = queryset.filter(branch=branch)
            
            return queryset.aggregate(
                total_orders=Count('id'),
                total_revenue=Sum('final_price'),
                avg_order_value=Avg('final_price')
            )
        
        @staticmethod
        def get_customer_report(start_date, end_date, branch=None):
            """تقرير العملاء"""
            from customers.models import Customer
            
            queryset = Customer.objects.filter(
                created_at__range=(start_date, end_date)
            ).select_related('branch', 'category')
            
            if branch:
                queryset = queryset.filter(branch=branch)
            
            return queryset.aggregate(
                total_customers=Count('id'),
                new_customers=Count('id', filter=Q(created_at__date=timezone.now().date())),
                active_customers=Count('id', filter=Q(status='active'))
            )
        
        @staticmethod
        def get_inventory_report():
            """تقرير المخزون"""
            from inventory.models import Product
            
            return Product.objects.aggregate(
                total_products=Count('id'),
                low_stock_products=Count('id', filter=Q(current_stock__lte=models.F('minimum_stock'))),
                out_of_stock_products=Count('id', filter=Q(current_stock=0)),
                total_value=Sum(models.F('current_stock') * models.F('price'))
            )

# =============================================================================
# 8. تطبيق التحسينات
# =============================================================================

def apply_performance_optimizations():
    """
    تطبيق جميع تحسينات الأداء
    """
    print("⚡ بدء تطبيق تحسينات الأداء...")
    
    # 1. تحسين استعلامات قاعدة البيانات
    print("✅ تحسين استعلامات قاعدة البيانات")
    optimize_database_queries()
    
    # 2. إنشاء نظام تخزين مؤقت متقدم
    print("✅ إنشاء نظام تخزين مؤقت متقدم")
    create_advanced_cache()
    
    # 3. تحسين استعلامات admin.py
    print("✅ تحسين استعلامات لوحة التحكم")
    optimize_admin_queries()
    
    # 4. إنشاء وسيط الأداء
    print("✅ إنشاء وسيط مراقبة الأداء")
    create_performance_middleware()
    
    # 5. تحسين استعلامات النماذج
    print("✅ تحسين استعلامات النماذج")
    optimize_model_queries()
    
    # 6. إنشاء التحميل المتأخر
    print("✅ إنشاء نظام التحميل المتأخر")
    create_lazy_loading()
    
    # 7. تحسين استعلامات التقارير
    print("✅ تحسين استعلامات التقارير")
    optimize_report_queries()
    
    print("🎉 تم تطبيق جميع تحسينات الأداء بنجاح!")

if __name__ == "__main__":
    apply_performance_optimizations() 