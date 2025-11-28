from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, F, Sum, Count, OuterRef, Subquery, Case, When
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Product, Category, PurchaseOrder, StockTransaction, StockAlert
from .forms import ProductForm
from .inventory_utils import (
    get_cached_stock_level,
    get_cached_product_list,
    get_cached_dashboard_stats,
    invalidate_product_cache
)
from accounts.models import SystemSettings

class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # استخدام التخزين المؤقت للإحصائيات - محسن للغاية
        stats = get_cached_dashboard_stats()
        context.update(stats)

        # إضافة active_menu للقائمة الجانبية
        context['active_menu'] = 'dashboard'

        # الحصول على المنتجات منخفضة المخزون - محسن جداً
        # استخدام only() وتحديد 5 فقط بدلاً من 10
        latest_balance = StockTransaction.objects.filter(
            product=OuterRef('pk')
        ).order_by('-transaction_date').values('running_balance')[:1]
        
        low_stock_products = Product.objects.annotate(
            current_stock_level=Subquery(latest_balance)
        ).filter(
            current_stock_level__gt=0,
            current_stock_level__lte=F('minimum_stock')
        ).select_related('category').only(
            'id', 'name', 'code', 'minimum_stock', 'category__name'
        )[:5]  # من 10 إلى 5
        
        context['low_stock_products'] = [
            {
                'product': p,
                'current_stock': p.current_stock_level or 0,
                'status': 'مخزون منخفض',
                'is_available': (p.current_stock_level or 0) > 0
            } 
            for p in low_stock_products
        ]

        # آخر حركات المخزون - محسّن
        recent_transactions = StockTransaction.objects.select_related(
            'product', 'created_by'
        ).only(
            'id', 'product__name', 'transaction_type', 'quantity', 
            'date', 'created_by__username'
        ).order_by('-date')[:5]  # من 10 إلى 5

        context['recent_transactions'] = recent_transactions

        # عدد طلبات الشراء المعلقة - استخدام count فقط
        context['pending_purchase_orders'] = PurchaseOrder.objects.filter(
            status__in=['draft', 'pending']
        ).count()

        # بيانات الرسم البياني - محسّن جداً
        category_stats = Category.objects.annotate(
            product_count=Count('products')
        ).filter(product_count__gt=0).only('id', 'name').order_by('-product_count')[:5]  # من 10 إلى 5
        
        stock_by_category = []
        for cat in category_stats:
            # حساب مبسّط باستخدام aggregate فقط
            total_stock = StockTransaction.objects.filter(
                product__category=cat
            ).aggregate(total=Sum('running_balance'))['total'] or 0
            
            stock_by_category.append({
                'name': cat.name,
                'stock': int(total_stock),
                'product_count': cat.product_count
            })
        
        context['stock_by_category'] = stock_by_category

        # بيانات حركة المخزون - محسّن (3 أيام فقط)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=2)  # من 6 إلى 2

        from django.db.models.functions import TruncDate
        stock_movements = StockTransaction.objects.filter(
            date__date__range=[start_date, end_date]
        ).annotate(
            date_only=TruncDate('date')
        ).values('date_only', 'transaction_type').annotate(
            total=Sum('quantity')
        ).order_by('date_only', 'transaction_type')

        # تنظيم البيانات
        dates = []
        stock_in = []
        stock_out = []
        
        movement_data = {}
        for movement in stock_movements:
            date_str = str(movement['date_only'])
            if date_str not in movement_data:
                movement_data[date_str] = {'in': 0, 'out': 0}
            movement_data[date_str][movement['transaction_type']] = movement['total']

        current_date = start_date
        while current_date <= end_date:
            date_str = str(current_date)
            dates.append(current_date)
            stock_in.append(movement_data.get(date_str, {}).get('in', 0))
            stock_out.append(movement_data.get(date_str, {}).get('out', 0))
            current_date += timedelta(days=1)

        context['stock_movement_dates'] = dates
        context['stock_movement_in'] = stock_in
        context['stock_movement_out'] = stock_out

        # التنبيهات - محسّن
        context['alerts_count'] = StockAlert.objects.filter(status='active').count()
        context['recent_alerts'] = StockAlert.objects.filter(
            status='active'
        ).select_related('product').only(
            'id', 'product__name', 'alert_type', 'created_at'
        ).order_by('-created_at')[:3]  # من 5 إلى 3

        context['current_year'] = timezone.now().year

        return context
@login_required
def product_list(request):
    # البحث والتصفية
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    filter_type = request.GET.get('filter', '')
    sort_by = request.GET.get('sort', '-created_at')

    # الحصول على المنتجات مع حساب المخزون الحالي
    # استخدام Subquery للحصول على آخر رصيد من جدول StockTransaction
    from django.db.models import OuterRef, Subquery, IntegerField
    from django.db.models.functions import Coalesce
    
    latest_balance = StockTransaction.objects.filter(
        product=OuterRef('pk')
    ).order_by('-transaction_date', '-id').values('running_balance')[:1]
    
    products = Product.objects.select_related('category').annotate(
        current_stock_calc=Coalesce(
            Subquery(latest_balance, output_field=IntegerField()),
            0
        )
    ).only(
        'id', 'name', 'code', 'price', 'category', 'created_at', 'minimum_stock'
    )

    # تطبيق فلتر السنة
    from accounts.utils import apply_default_year_filter
    products = apply_default_year_filter(products, request, 'created_at', 'inventory')

    # تطبيق البحث
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # تطبيق فلتر الفئة
    if category_id:
        products = products.filter(category_id=category_id)

    # تطبيق الترتيب
    if hasattr(Product, sort_by.lstrip('-')):
        products = products.order_by(sort_by)
    else:
        products = products.order_by('-created_at')

    # الصفحات - زيادة الحجم الافتراضي
    page_size = request.GET.get('page_size', '50')  # من 20 إلى 50
    try:
        page_size = int(page_size)
        if page_size > 200:  # من 100 إلى 200
            page_size = 200
        elif page_size < 1:
            page_size = 50
    except Exception:
        page_size = 50
    
    paginator = Paginator(products, page_size)
    page_number = request.GET.get('page')
    
    # إصلاح مشكلة pagination
    if page_number and isinstance(page_number, (list, tuple)):
        page_number = page_number[0] if page_number else '1'
    elif page_number and str(page_number).startswith('[') and str(page_number).endswith(']'):
        try:
            import re
            match = re.search(r'\[(\d+)\]', str(page_number))
            if match:
                page_number = match.group(1)
        except:
            page_number = '1'
    
    page_obj = paginator.get_page(page_number)

    # التنبيهات - محسّن
    from .models import StockAlert
    alerts_count = StockAlert.objects.filter(status='active').count()
    recent_alerts = StockAlert.objects.filter(
        status='active'
    ).select_related('product').only(
        'id', 'product__name', 'alert_type', 'created_at'
    ).order_by('-created_at')[:5]

    from datetime import datetime
    current_year = datetime.now().year

    context = {
        'page_obj': page_obj,
        'categories': Category.objects.only('id', 'name'),
        'search_query': search_query,
        'selected_category': category_id,
        'selected_filter': filter_type,
        'sort_by': sort_by,
        'active_menu': 'products',
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year,
        'page_size': page_size,
        'paginator': paginator,
        'page_number': page_number,
    }

    return render(request, 'inventory/product_list_new_icons.html', context)

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            try:
                # حفظ المنتج
                product = form.save()

                # إضافة الكمية الحالية إذا تم تحديدها
                initial_quantity = form.cleaned_data.get('initial_quantity', 0)
                warehouse = form.cleaned_data.get('warehouse')

                if initial_quantity > 0 and warehouse:
                    StockTransaction.objects.create(
                        product=product,
                        warehouse=warehouse,
                        transaction_type='in',
                        reason='initial_stock',
                        quantity=initial_quantity,
                        reference='إضافة منتج جديد',
                        notes='الكمية الابتدائية عند إضافة المنتج',
                        created_by=request.user,
                        transaction_date=timezone.now()
                    )

                # إعادة تحميل الذاكرة المؤقتة للمنتجات
                invalidate_product_cache(product.id)

                success_msg = 'تم إضافة المنتج بنجاح.'
                if initial_quantity > 0:
                    success_msg += f' تم إضافة {initial_quantity} وحدة إلى مستودع {warehouse.name}.'

                messages.success(request, success_msg)
                return redirect('inventory:product_list')

            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء إضافة المنتج: {str(e)}')
    else:
        form = ProductForm()

    return render(request, 'inventory/product_form.html', {'form': form})

@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            try:
                # حفظ المنتج
                product = form.save()

                # ملاحظة: في التعديل، لا نضيف كمية جديدة تلقائياً
                # يمكن للمستخدم إضافة كمية من خلال صفحة حركات المخزون

                # إعادة تحميل الذاكرة المؤقتة للمنتجات
                invalidate_product_cache(product.id)
                messages.success(request, 'تم تحديث المنتج بنجاح.')
                return redirect('inventory:product_list')

            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء تحديث المنتج: {str(e)}')
    else:
        form = ProductForm(instance=product)

    return render(request, 'inventory/product_form.html', {'form': form, 'product': product})

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        try:
            product.delete()
            # إعادة تحميل الذاكرة المؤقتة للمنتجات
            invalidate_product_cache(product.id)
            messages.success(request, 'تم حذف المنتج بنجاح.')
        except Exception as e:
            messages.error(request, 'حدث خطأ أثناء حذف المنتج.')
        return redirect('inventory:product_list')

    return render(request, 'inventory/product_confirm_delete.html', {'product': product})

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # الحصول على المخزون الحالي من property (يحسب من جميع المستودعات)
    current_stock = product.current_stock

    # استخدام select_related للمعاملات
    transactions = product.transactions.select_related(
        'created_by', 'warehouse'
    ).order_by('-transaction_date', '-id')

    # حساب إجمالي الوارد والصادر
    from django.db.models import Sum
    transactions_in = product.transactions.filter(transaction_type='in')
    transactions_out = product.transactions.filter(transaction_type='out')

    transactions_in_total = transactions_in.aggregate(total=Sum('quantity'))['total'] or 0
    transactions_out_total = transactions_out.aggregate(total=Sum('quantity'))['total'] or 0

    # إعداد بيانات الرسم البياني - استخدام running_balance
    from django.utils import timezone
    from datetime import timedelta
    from .models import Warehouse

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)

    # حساب الرصيد لكل يوم باستخدام running_balance من جميع المستودعات
    transaction_dates = []
    transaction_balances = []

    # الحصول على جميع المستودعات النشطة
    warehouses = Warehouse.objects.filter(is_active=True)

    # لكل يوم، احسب مجموع الرصيد من جميع المستودعات
    current_date = start_date
    while current_date <= end_date:
        daily_total = 0

        # لكل مستودع، احصل على آخر رصيد حتى هذا اليوم
        for warehouse in warehouses:
            last_trans = product.transactions.filter(
                warehouse=warehouse,
                transaction_date__date__lte=current_date
            ).order_by('-transaction_date', '-id').first()

            if last_trans:
                daily_total += last_trans.running_balance

        transaction_dates.append(current_date)
        transaction_balances.append(float(daily_total))

        current_date += timedelta(days=1)

    # جلب إعدادات النظام
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ر.س'

    # إضافة عدد التنبيهات النشطة
    from .models import StockAlert
    alerts_count = StockAlert.objects.filter(status='active').count()

    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = StockAlert.objects.filter(
        status='active'
    ).select_related('product').order_by('-created_at')[:5]

    # إضافة السنة الحالية لشريط التذييل
    from datetime import datetime
    current_year = datetime.now().year

    # الحصول على المخزون حسب المستودع
    from .models import Warehouse, StockTransaction
    from django.db.models import Max

    warehouses_stock = []
    warehouses = Warehouse.objects.filter(is_active=True)

    for warehouse in warehouses:
        # الحصول على آخر حركة للمنتج في هذا المستودع
        last_transaction = StockTransaction.objects.filter(
            product=product,
            warehouse=warehouse
        ).order_by('-transaction_date', '-id').first()

        if last_transaction:
            warehouses_stock.append({
                'warehouse': warehouse,
                'stock': last_transaction.running_balance,
                'last_update': last_transaction.transaction_date
            })

    context = {
        'product': product,
        'current_stock': current_stock,
        'stock_status': (
            'نفذ من المخزون' if current_stock == 0
            else 'مخزون منخفض' if current_stock <= product.minimum_stock
            else 'متوفر'
        ),
        'transactions': transactions,
        'transactions_in_total': transactions_in_total,
        'transactions_out_total': transactions_out_total,
        'transaction_dates': transaction_dates,
        'transaction_balances': transaction_balances,
        'active_menu': 'products',
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year,
        'currency_symbol': currency_symbol,
        'warehouses_stock': warehouses_stock,
    }
    return render(request, 'inventory/product_detail_new_icons.html', context)

@login_required
def transaction_create(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk)

    # إضافة أنواع المعاملات وأسبابها للقالب
    transaction_types = [
        ('in', 'وارد'),
        ('out', 'صادر'),
    ]

    transaction_reasons = [
        ('purchase', 'شراء'),
        ('return', 'مرتجع'),
        ('adjustment', 'تسوية'),
        ('transfer', 'نقل'),
        ('sale', 'بيع'),
        ('damage', 'تالف'),
        ('other', 'أخرى'),
    ]

    # الحصول على مستوى المخزون الحالي من property
    current_stock = product.current_stock

    # الحصول على المستودعات النشطة مع مخزونها
    from .models import Warehouse
    warehouses_list = []
    for warehouse in Warehouse.objects.filter(is_active=True):
        last_trans = StockTransaction.objects.filter(
            product=product,
            warehouse=warehouse
        ).order_by('-transaction_date', '-id').first()

        warehouses_list.append({
            'id': warehouse.id,
            'name': warehouse.name,
            'stock': last_trans.running_balance if last_trans else 0
        })

    if request.method == 'POST':
        try:
            # استخراج البيانات من النموذج
            transaction_type = request.POST.get('transaction_type')
            reason = request.POST.get('reason')
            quantity = request.POST.get('quantity')
            warehouse_id = request.POST.get('warehouse')
            reference = request.POST.get('reference', '')
            notes = request.POST.get('notes', '')

            # التحقق من البيانات المطلوبة
            if not all([transaction_type, reason, quantity, warehouse_id]):
                raise ValueError("جميع الحقول المطلوبة يجب ملؤها")

            # التحقق من صحة الكمية
            try:
                quantity = float(quantity)
                if quantity <= 0:
                    raise ValueError("يجب أن تكون الكمية أكبر من صفر")
            except (ValueError, TypeError):
                raise ValueError("الكمية يجب أن تكون رقماً صحيحاً")

            # الحصول على المستودع
            warehouse = get_object_or_404(Warehouse, pk=warehouse_id)

            # إعادة فحص المخزون الحالي قبل تسجيل الحركة
            current_stock = product.current_stock

            # الحصول على مخزون المستودع المحدد
            warehouse_stock = 0
            last_trans = StockTransaction.objects.filter(
                product=product,
                warehouse=warehouse
            ).order_by('-transaction_date', '-id').first()

            if last_trans:
                warehouse_stock = last_trans.running_balance

            # التحقق من توفر المخزون للحركات الصادرة
            if transaction_type == 'out':
                if warehouse_stock <= 0:
                    raise ValueError(f"لا يوجد مخزون متاح للصرف من مستودع {warehouse.name}")
                if quantity > warehouse_stock:
                    raise ValueError(f"الكمية المطلوبة ({quantity}) أكبر من المخزون المتاح في {warehouse.name} ({warehouse_stock})")

            # حساب running_balance
            if last_trans:
                previous_balance = last_trans.running_balance
            else:
                previous_balance = 0

            if transaction_type == 'in':
                new_balance = previous_balance + quantity
            else:
                new_balance = previous_balance - quantity

            # إنشاء حركة المخزون
            transaction = StockTransaction.objects.create(
                product=product,
                warehouse=warehouse,
                transaction_type=transaction_type,
                reason=reason,
                quantity=quantity,
                running_balance=new_balance,
                reference=reference,
                notes=notes,
                created_by=request.user,
                transaction_date=timezone.now()
            )

            # إعادة تحميل الذاكرة المؤقتة للمنتج
            invalidate_product_cache(product.id)

            # إضافة رسالة نجاح
            if transaction_type == 'in':
                messages.success(request, f"تم تسجيل حركة وارد بنجاح إلى {warehouse.name}. الكمية: {quantity}")
            else:
                messages.success(request, f"تم تسجيل حركة صادر بنجاح من {warehouse.name}. الكمية: {quantity}")

            return redirect('inventory:product_detail', pk=product.pk)

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء تسجيل حركة المخزون: {str(e)}")

    # إضافة عدد التنبيهات النشطة
    alerts_count = StockAlert.objects.filter(status='active').count()

    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = StockAlert.objects.filter(
        status='active'
    ).select_related('product').order_by('-created_at')[:5]

    # إضافة السنة الحالية لشريط التذييل
    current_year = datetime.now().year

    context = {
        'product': product,
        'transaction_types': transaction_types,
        'transaction_reasons': transaction_reasons,
        'current_stock': current_stock,
        'warehouses': warehouses_list,
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year
    }

    return render(request, 'inventory/transaction_form_new.html', context)

# API Endpoints
from django.http import JsonResponse

@login_required
def product_api_detail(request, pk):
    try:
        product = get_object_or_404(Product, pk=pk)
        current_stock = get_cached_stock_level(product.id)

        data = {
            'id': product.id,
            'name': product.name,
            'code': product.code,
            'category': str(product.category),
            'description': product.description,
            'price': product.price,
            'minimum_stock': product.minimum_stock,
            'current_stock': current_stock,
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'المنتج غير موجود'}, status=404)

@login_required
def product_api_list(request):
    product_type = request.GET.get('type')

    # الحصول على المنتجات من الذاكرة المؤقتة
    products = get_cached_product_list(include_stock=True)

    # تطبيق الفلتر حسب النوع
    if product_type:
        if product_type == 'fabric':
            products = [p for p in products if p.category.name == 'أقمشة']
        elif product_type == 'accessory':
            products = [p for p in products if p.category.name == 'اكسسوارات']

    # تحويل إلى JSON
    data = [{
        'id': p.id,
        'name': p.name,
        'code': p.code,
        'category': str(p.category),
        'description': p.description,
        'price': p.price,
        'minimum_stock': p.minimum_stock,
        'current_stock': p.current_stock,
    } for p in products]

    return JsonResponse(data, safe=False)

def product_api_autocomplete(request):
    """
    API للبحث السريع عن المنتجات (autocomplete) مع التخزين المؤقت
    يقبل باراميتر ?query= ويعيد قائمة مختصرة (id, name, code, price, current_stock)
    """
    query = request.GET.get('query', '').strip()

    # إذا كان هناك استعلام، استخدم التخزين المؤقت
    if query and len(query) >= 2:
        try:
            from orders.cache import search_products_cached
            results = search_products_cached(query)

            # تحديد النتائج إلى 10 عناصر فقط
            results = results[:10]

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في البحث المؤقت عن المنتجات: {str(e)}")

            # العودة للطريقة التقليدية في حالة الخطأ
            results = []
            products = Product.objects.filter(
                Q(name__icontains=query) | Q(code__icontains=query)
            ).select_related('category')[:10]

            for p in products:
                results.append({
                    'id': p.id,
                    'name': p.name,
                    'code': p.code,
                    'price': float(p.price),
                    'current_stock': p.current_stock,
                    'category': p.category.name if p.category else None,
                    'description': p.description
                })
    else:
        # للاستعلامات الفارغة أو القصيرة، عرض المنتجات الأكثر شيوعاً
        results = []
        products = Product.objects.select_related('category').order_by('-id')[:10]

        for p in products:
            results.append({
                'id': p.id,
                'name': p.name,
                'code': p.code,
                'price': float(p.price),
                'current_stock': p.current_stock,
                'category': p.category.name if p.category else None,
                'description': p.description
            })

    return JsonResponse(results, safe=False)

# New API View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count
from .models import Product
from orders.models import Order
from customers.models import Customer
from accounts.models import ActivityLog

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_view(request):
    try:
        # Calculate statistics
        stats = {
            'totalCustomers': Customer.objects.count(),
            'totalOrders': Order.objects.count(),
            'inventoryValue': Product.objects.aggregate(
                total=Sum('price', default=0))['total'],
            'pendingInstallations': 0,
        }

        # Get recent activities
        activities = ActivityLog.objects.select_related('user')\
            .order_by('-timestamp')[:10]\
            .values('id', 'type', 'description', 'timestamp')

        return Response({
            'stats': stats,
            'activities': list(activities)
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=500
        )


@login_required
def product_search_api(request):
    """API للبحث عن المنتجات لـ Select2"""
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = 30

    # البحث في المنتجات
    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(description__icontains=query)
        )

    # حساب العدد الإجمالي
    total_count = products.count()

    # تطبيق الصفحات
    start = (page - 1) * page_size
    end = start + page_size
    products = products[start:end]

    # تحضير النتائج
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'text': f"{product.name} - {product.price} ج.م",
            'name': product.name,
            'price': float(product.price),
            'code': product.code or '',
            'current_stock': get_cached_stock_level(product.id)
        })

    return JsonResponse({
        'results': results,
        'pagination': {
            'more': end < total_count
        },
        'total_count': total_count
    })


@login_required
def barcode_scan_api(request):
    """
    API لفحص الباركود والحصول على معلومات المنتج
    يستقبل كود المنتج ويرجع كل المعلومات
    """
    barcode = request.GET.get('barcode', '').strip()
    
    if not barcode:
        return JsonResponse({
            'success': False,
            'error': 'لم يتم توفير رمز الباركود'
        }, status=400)
    
    try:
        # البحث عن المنتج بواسطة الكود (الباركود = كود الصنف)
        product = Product.objects.select_related('category').get(code=barcode)
        
        # حساب المخزون الحالي من جميع المستودعات
        current_stock = product.current_stock
        
        # الحصول على المخزون حسب المستودع
        from .models import Warehouse
        warehouses_stock = []
        warehouses = Warehouse.objects.filter(is_active=True)
        
        for warehouse in warehouses:
            last_transaction = StockTransaction.objects.filter(
                product=product,
                warehouse=warehouse
            ).order_by('-transaction_date', '-id').first()
            
            if last_transaction and last_transaction.running_balance > 0:
                warehouses_stock.append({
                    'warehouse_id': warehouse.id,
                    'warehouse_name': warehouse.name,
                    'warehouse_code': warehouse.code,
                    'stock': float(last_transaction.running_balance),
                    'last_update': last_transaction.transaction_date.strftime('%Y-%m-%d %H:%M')
                })
        
        # جلب إعدادات النظام للعملة
        system_settings = SystemSettings.get_settings()
        currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'
        
        # تجهيز البيانات
        data = {
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'code': product.code,
                'price': float(product.price),
                'currency': product.currency,
                'currency_symbol': currency_symbol,
                'unit': product.unit,
                'unit_display': product.get_unit_display(),
                'category': product.category.name if product.category else 'غير مصنف',
                'description': product.description,
                'current_stock': float(current_stock),
                'minimum_stock': product.minimum_stock,
                'stock_status': product.stock_status,
                'is_available': product.is_available,
                'warehouses': warehouses_stock,
                'created_at': product.created_at.strftime('%Y-%m-%d'),
            }
        }
        
        return JsonResponse(data)
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'المنتج غير موجود',
            'message': f'لا يوجد منتج بكود الباركود: {barcode}'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'حدث خطأ أثناء البحث عن المنتج',
            'message': str(e)
        }, status=500)
