"""
التحسينات الفورية للنظام
Immediate System Improvements
"""

# =============================================================================
# 1. دمج إعدادات الشركة والنظام
# =============================================================================

def create_unified_settings_model():
    """
    إنشاء نموذج موحد للإعدادات
    """
    from django.db import models
    from django.utils.translation import gettext_lazy as _
    
    class SystemConfiguration(models.Model):
        """إعدادات شاملة للنظام والشركة"""
        
        # معلومات الشركة
        company_name = models.CharField(
            max_length=200, 
            default='Elkhawaga',
            verbose_name=_('اسم الشركة')
        )
        company_logo = models.ImageField(
            upload_to='company_logos/',
            null=True, blank=True,
            verbose_name=_('شعار الشركة')
        )
        company_address = models.TextField(
            blank=True, null=True,
            verbose_name=_('عنوان الشركة')
        )
        company_phone = models.CharField(
            max_length=20,
            blank=True, null=True,
            verbose_name=_('هاتف الشركة')
        )
        company_email = models.EmailField(
            blank=True, null=True,
            verbose_name=_('بريد الشركة')
        )
        company_website = models.URLField(
            blank=True, null=True,
            verbose_name=_('موقع الشركة')
        )
        
        # إعدادات النظام
        system_name = models.CharField(
            max_length=100,
            default='نظام الخواجه',
            verbose_name=_('اسم النظام')
        )
        system_version = models.CharField(
            max_length=20,
            default='1.0.0',
            verbose_name=_('إصدار النظام')
        )
        system_currency = models.CharField(
            max_length=3,
            default='SAR',
            verbose_name=_('عملة النظام')
        )
        
        # إعدادات الإشعارات
        enable_notifications = models.BooleanField(
            default=True,
            verbose_name=_('تفعيل الإشعارات')
        )
        enable_email_notifications = models.BooleanField(
            default=False,
            verbose_name=_('تفعيل إشعارات البريد الإلكتروني')
        )
        
        # إعدادات الأداء
        items_per_page = models.PositiveIntegerField(
            default=20,
            verbose_name=_('عدد العناصر في الصفحة')
        )
        enable_analytics = models.BooleanField(
            default=True,
            verbose_name=_('تفعيل التحليلات')
        )
        
        # إعدادات الصيانة
        maintenance_mode = models.BooleanField(
            default=False,
            verbose_name=_('وضع الصيانة')
        )
        maintenance_message = models.TextField(
            blank=True,
            verbose_name=_('رسالة الصيانة')
        )
        
        # معلومات إضافية
        working_hours = models.CharField(
            max_length=100,
            blank=True,
            default='9 صباحاً - 5 مساءً',
            verbose_name=_('ساعات العمل')
        )
        copyright_text = models.CharField(
            max_length=255,
            blank=True,
            default='جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات',
            verbose_name=_('نص حقوق النشر')
        )
        
        created_at = models.DateTimeField(
            auto_now_add=True,
            verbose_name=_('تاريخ الإنشاء')
        )
        updated_at = models.DateTimeField(
            auto_now=True,
            verbose_name=_('تاريخ التحديث')
        )
        
        class Meta:
            verbose_name = _('إعدادات النظام')
            verbose_name_plural = _('إعدادات النظام')
        
        def __str__(self):
            return f"{self.system_name} - {self.company_name}"
        
        @classmethod
        def get_config(cls):
            """الحصول على إعدادات النظام (إنشاء إذا لم تكن موجودة)"""
            config, created = cls.objects.get_or_create(pk=1)
            return config

# =============================================================================
# 2. تحسين استعلامات admin.py
# =============================================================================

def optimize_admin_queries():
    """
    تحسين استعلامات لوحة التحكم
    """
    from django.contrib import admin
    from accounts.models import User, Department, Branch, Notification
    from customers.models import Customer
    from orders.models import Order
    from inventory.models import Product
    
    # تحسين CustomUserAdmin
    class OptimizedUserAdmin(admin.ModelAdmin):
        def get_queryset(self, request):
            return super().get_queryset(request).select_related(
                'branch'
            ).prefetch_related(
                'departments',
                'user_roles__role',
                'managed_departments'
            )
    
    # تحسين CustomerAdmin
    class OptimizedCustomerAdmin(admin.ModelAdmin):
        def get_queryset(self, request):
            return super().get_queryset(request).select_related(
                'category', 'branch', 'created_by'
            ).prefetch_related('customer_orders')
    
    # تحسين OrderAdmin
    class OptimizedOrderAdmin(admin.ModelAdmin):
        def get_queryset(self, request):
            return super().get_queryset(request).select_related(
                'customer', 'branch', 'created_by'
            ).prefetch_related('items')
    
    # تحسين ProductAdmin
    class OptimizedProductAdmin(admin.ModelAdmin):
        def get_queryset(self, request):
            return super().get_queryset(request).select_related(
                'category'
            ).prefetch_related('transactions')

# =============================================================================
# 3. إضافة AJAX لجميع النماذج
# =============================================================================

def create_ajax_form_handler():
    """
    إنشاء معالج AJAX للنماذج
    """
    from django.http import JsonResponse
    from django.views.decorators.http import require_http_methods
    from django.contrib.auth.decorators import login_required
    
    @login_required
    @require_http_methods(["POST"])
    def ajax_form_handler(request, model_name, action):
        """
        معالج عام للنماذج باستخدام AJAX
        """
        try:
            # تحديد النموذج حسب model_name
            models_map = {
                'customer': Customer,
                'order': Order,
                'product': Product,
                'inspection': Inspection,
                'manufacturing': ManufacturingOrder,
            }
            
            model_class = models_map.get(model_name)
            if not model_class:
                return JsonResponse({
                    'success': False,
                    'errors': ['نموذج غير معروف']
                })
            
            # معالجة الإجراء
            if action == 'create':
                form_class = get_form_class(model_name)
                form = form_class(request.POST, request.FILES)
                
                if form.is_valid():
                    instance = form.save(commit=False)
                    instance.created_by = request.user
                    instance.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'تم الحفظ بنجاح',
                        'data': {
                            'id': instance.id,
                            'name': str(instance),
                            'redirect_url': get_detail_url(model_name, instance.id)
                        }
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'errors': form.errors
                    })
            
            elif action == 'update':
                instance_id = request.POST.get('id')
                instance = model_class.objects.get(id=instance_id)
                form_class = get_form_class(model_name)
                form = form_class(request.POST, request.FILES, instance=instance)
                
                if form.is_valid():
                    form.save()
                    return JsonResponse({
                        'success': True,
                        'message': 'تم التحديث بنجاح'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'errors': form.errors
                    })
            
            elif action == 'delete':
                instance_id = request.POST.get('id')
                instance = model_class.objects.get(id=instance_id)
                instance.delete()
                
                return JsonResponse({
                    'success': True,
                    'message': 'تم الحذف بنجاح'
                })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'errors': [str(e)]
            })

# =============================================================================
# 4. تحسين نظام الإشعارات
# =============================================================================

def create_notification_signals():
    """
    إنشاء إشعارات تلقائية
    """
    from django.db.models.signals import post_save
    from django.dispatch import receiver
    from accounts.utils import send_notification
    
    @receiver(post_save, sender=Order)
    def notify_new_order(sender, instance, created, **kwargs):
        """إشعار عند إنشاء طلب جديد"""
        if created:
            send_notification(
                title='طلب جديد',
                message=f'تم إنشاء طلب جديد للعميل {instance.customer.name}',
                sender=instance.created_by,
                sender_department_code='orders',
                target_department_code='manufacturing',
                priority='high',
                related_object=instance
            )
    
    @receiver(post_save, sender=Inspection)
    def notify_new_inspection(sender, instance, created, **kwargs):
        """إشعار عند إنشاء معاينة جديدة"""
        if created:
            send_notification(
                title='معاينة جديدة',
                message=f'تم إنشاء معاينة جديدة للعميل {instance.customer.name}',
                sender=instance.created_by,
                sender_department_code='inspections',
                target_department_code='manufacturing',
                priority='medium',
                related_object=instance
            )
    
    @receiver(post_save, sender=ManufacturingOrder)
    def notify_manufacturing_status(sender, instance, **kwargs):
        """إشعار عند تغيير حالة التصنيع"""
        if instance.status == 'completed':
            send_notification(
                title='اكتمال التصنيع',
                message=f'تم اكتمال تصنيع الطلب {instance.order.order_number}',
                sender=instance.created_by,
                sender_department_code='manufacturing',
                target_department_code='installations',
                priority='high',
                related_object=instance
            )

# =============================================================================
# 5. تحسين التخزين المؤقت
# =============================================================================

def create_cache_utils():
    """
    إنشاء أدوات التخزين المؤقت
    """
    from django.core.cache import cache
    from django.db.models import Sum, Count
    from datetime import timedelta
    
    def get_cached_dashboard_stats(user=None):
        """الحصول على إحصائيات لوحة التحكم من التخزين المؤقت"""
        cache_key = f'dashboard_stats_{user.id if user else "all"}'
        stats = cache.get(cache_key)
        
        if stats is None:
            # حساب الإحصائيات
            from customers.models import Customer
            from orders.models import Order
            from inventory.models import Product
            
            # إحصائيات العملاء
            customers = Customer.objects.all()
            if user and not user.is_superuser:
                customers = customers.filter(branch=user.branch)
            
            total_customers = customers.count()
            new_customers_today = customers.filter(
                created_at__date=timezone.now().date()
            ).count()
            
            # إحصائيات الطلبات
            orders = Order.objects.all()
            if user and not user.is_superuser:
                orders = orders.filter(branch=user.branch)
            
            total_orders = orders.count()
            orders_today = orders.filter(
                created_at__date=timezone.now().date()
            ).count()
            
            # إحصائيات المخزون
            products = Product.objects.all()
            low_stock_products = products.filter(
                current_stock__lte=F('minimum_stock')
            ).count()
            
            stats = {
                'total_customers': total_customers,
                'new_customers_today': new_customers_today,
                'total_orders': total_orders,
                'orders_today': orders_today,
                'low_stock_products': low_stock_products,
            }
            
            # تخزين لمدة 15 دقيقة
            cache.set(cache_key, stats, 900)
        
        return stats
    
    def get_cached_user_notifications(user, limit=10):
        """الحصول على إشعارات المستخدم من التخزين المؤقت"""
        cache_key = f'user_notifications_{user.id}_{limit}'
        notifications = cache.get(cache_key)
        
        if notifications is None:
            from accounts.utils import get_user_notifications
            notifications = list(get_user_notifications(user, limit=limit))
            cache.set(cache_key, notifications, 300)  # 5 دقائق
        
        return notifications

# =============================================================================
# 6. إضافة فهارس محسنة
# =============================================================================

def create_optimized_indexes():
    """
    إنشاء فهارس محسنة للنماذج
    """
    from django.db import models
    
    class OptimizedUser(models.Model):
        """نموذج مستخدم محسن مع فهارس"""
        
        class Meta:
            indexes = [
                models.Index(fields=['username']),
                models.Index(fields=['email']),
                models.Index(fields=['branch', 'is_active']),
                models.Index(fields=['created_at']),
                models.Index(fields=['last_login']),
            ]
    
    class OptimizedCustomer(models.Model):
        """نموذج عميل محسن مع فهارس"""
        
        class Meta:
            indexes = [
                models.Index(fields=['code']),
                models.Index(fields=['name']),
                models.Index(fields=['phone', 'phone2']),
                models.Index(fields=['email']),
                models.Index(fields=['status']),
                models.Index(fields=['customer_type']),
                models.Index(fields=['branch', 'status']),
                models.Index(fields=['created_at']),
            ]
    
    class OptimizedOrder(models.Model):
        """نموذج طلب محسن مع فهارس"""
        
        class Meta:
            indexes = [
                models.Index(fields=['order_number']),
                models.Index(fields=['customer']),
                models.Index(fields=['status']),
                models.Index(fields=['created_at']),
                models.Index(fields=['branch', 'status']),
            ]

# =============================================================================
# 7. تحسين واجهة المستخدم
# =============================================================================

def create_ajax_js_utils():
    """
    إنشاء أدوات JavaScript لـ AJAX
    """
    js_code = """
    // أدوات AJAX للنماذج
    const AjaxFormHandler = {
        // إعداد النماذج لاستخدام AJAX
        setupForm: function(formSelector) {
            $(formSelector).on('submit', function(e) {
                e.preventDefault();
                
                const form = $(this);
                const submitBtn = form.find('button[type="submit"]');
                const originalText = submitBtn.text();
                
                // إظهار مؤشر التحميل
                submitBtn.prop('disabled', true);
                submitBtn.html('<i class="fas fa-spinner fa-spin"></i> جاري الحفظ...');
                
                $.ajax({
                    url: form.attr('action'),
                    method: 'POST',
                    data: form.serialize(),
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    success: function(response) {
                        if (response.success) {
                            // إظهار رسالة نجاح
                            Swal.fire({
                                icon: 'success',
                                title: 'تم بنجاح!',
                                text: response.message,
                                timer: 2000,
                                showConfirmButton: false
                            });
                            
                            // تحديث الصفحة أو إعادة التوجيه
                            if (response.data && response.data.redirect_url) {
                                setTimeout(() => {
                                    window.location.href = response.data.redirect_url;
                                }, 2000);
                            } else {
                                // تحديث جزئي للصفحة
                                updatePageContent(response.data);
                            }
                        } else {
                            // إظهار رسائل الخطأ
                            showFormErrors(response.errors);
                        }
                    },
                    error: function(xhr) {
                        Swal.fire({
                            icon: 'error',
                            title: 'خطأ!',
                            text: 'حدث خطأ في الاتصال بالخادم'
                        });
                    },
                    complete: function() {
                        // إعادة تعيين الزر
                        submitBtn.prop('disabled', false);
                        submitBtn.text(originalText);
                    }
                });
            });
        },
        
        // إظهار أخطاء النموذج
        showFormErrors: function(errors) {
            // مسح الأخطاء السابقة
            $('.error-message').remove();
            $('.is-invalid').removeClass('is-invalid');
            
            // إظهار الأخطاء الجديدة
            for (const field in errors) {
                const fieldElement = $(`[name="${field}"]`);
                if (fieldElement.length) {
                    fieldElement.addClass('is-invalid');
                    fieldElement.after(`<div class="error-message text-danger">${errors[field].join(', ')}</div>`);
                }
            }
        },
        
        // تحديث محتوى الصفحة
        updatePageContent: function(data) {
            if (data && data.html) {
                $('#main-content').html(data.html);
            }
        }
    };
    
    // تهيئة جميع النماذج
    $(document).ready(function() {
        AjaxFormHandler.setupForm('form.ajax-form');
    });
    """
    
    return js_code

# =============================================================================
# 8. تحسين الأداء العام
# =============================================================================

def create_performance_middleware():
    """
    إنشاء وسيط لتحسين الأداء
    """
    import time
    from django.utils.deprecation import MiddlewareMixin
    from django.db import connection
    
    class PerformanceMiddleware(MiddlewareMixin):
        """وسيط لمراقبة وتحسين الأداء"""
        
        def process_request(self, request):
            # تسجيل وقت بداية الطلب
            request.start_time = time.time()
            request.start_queries = len(connection.queries)
        
        def process_response(self, request, response):
            # حساب الوقت المستغرق
            if hasattr(request, 'start_time'):
                duration = time.time() - request.start_time
                queries = len(connection.queries) - getattr(request, 'start_queries', 0)
                
                # إضافة معلومات الأداء للـ headers
                response['X-Response-Time'] = f'{duration:.3f}s'
                response['X-DB-Queries'] = str(queries)
                
                # تحذير من الاستعلامات الكثيرة
                if queries > 20:
                    print(f"Warning: {request.path} executed {queries} queries in {duration:.3f}s")
            
            return response

# =============================================================================
# 9. تطبيق التحسينات
# =============================================================================

def apply_immediate_improvements():
    """
    تطبيق جميع التحسينات الفورية
    """
    print("🔧 بدء تطبيق التحسينات الفورية...")
    
    # 1. إنشاء نموذج الإعدادات الموحد
    print("✅ إنشاء نموذج الإعدادات الموحد")
    create_unified_settings_model()
    
    # 2. تحسين استعلامات admin.py
    print("✅ تحسين استعلامات لوحة التحكم")
    optimize_admin_queries()
    
    # 3. إضافة معالج AJAX
    print("✅ إضافة معالج AJAX للنماذج")
    create_ajax_form_handler()
    
    # 4. إنشاء إشعارات تلقائية
    print("✅ إنشاء إشعارات تلقائية")
    create_notification_signals()
    
    # 5. تحسين التخزين المؤقت
    print("✅ تحسين نظام التخزين المؤقت")
    create_cache_utils()
    
    # 6. إضافة فهارس محسنة
    print("✅ إضافة فهارس محسنة")
    create_optimized_indexes()
    
    # 7. تحسين واجهة المستخدم
    print("✅ تحسين واجهة المستخدم")
    create_ajax_js_utils()
    
    # 8. إضافة وسيط الأداء
    print("✅ إضافة وسيط مراقبة الأداء")
    create_performance_middleware()
    
    print("🎉 تم تطبيق جميع التحسينات الفورية بنجاح!")

if __name__ == "__main__":
    apply_immediate_improvements() 