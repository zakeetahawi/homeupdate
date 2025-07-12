from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, F, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Product, Category, PurchaseOrder, StockTransaction, StockAlert, Supplier
from .inventory_utils import (
    get_cached_stock_level,
    get_cached_product_list,
    get_cached_dashboard_stats,
    invalidate_product_cache
)
from accounts.models import UnifiedSystemSettings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/dashboard_new_icons.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # استخدام التخزين المؤقت للإحصائيات
        stats = get_cached_dashboard_stats()
        context.update(stats)

        # إضافة active_menu للقائمة الجانبية
        context['active_menu'] = 'dashboard'

        # الحصول على المنتجات منخفضة المخزون مع حالة المخزون
        products = get_cached_product_list(include_stock=True)
        low_stock_products = [
            {
                'product': p,
                'status': p.status,
                'is_available': p.is_available
            } 
            for p in products 
            if 0 < p.current_stock_calc <= p.minimum_stock
        ]
        context['low_stock_products'] = low_stock_products[:10]

        # الحصول على آخر حركات المخزون
        from .models import StockTransaction
        context['recent_transactions'] = StockTransaction.objects.select_related(
            'product', 'created_by'
        ).order_by('-date')[:10]

        # الحصول على عدد طلبات الشراء المعلقة
        from .models import PurchaseOrder
        context['pending_purchase_orders'] = PurchaseOrder.objects.filter(
            status__in=['draft', 'pending']
        ).count()

        # بيانات الرسم البياني للمخزون حسب الفئة
        from django.db.models import Sum, Count
        from .models import Category, Product

        stock_by_category = []
        categories = Category.objects.all()

        for category in categories:
            # حساب إجمالي المخزون لكل فئة
            products_in_category = Product.objects.filter(category=category)
            total_stock = 0

            for product in products_in_category:
                total_stock += get_cached_stock_level(product.id)

            stock_by_category.append({
                'name': category.name,
                'stock': total_stock
            })

        context['stock_by_category'] = stock_by_category

        # بيانات الرسم البياني لحركة المخزون
        from django.utils import timezone
        from datetime import timedelta

        # الحصول على تواريخ آخر 30 يوم
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=29)

        dates = []
        stock_in = []
        stock_out = []

        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)

            # حساب إجمالي الوارد والصادر لهذا اليوم
            day_in = StockTransaction.objects.filter(
                date__date=current_date,
                transaction_type='in'
            ).aggregate(total=Sum('quantity'))['total'] or 0

            day_out = StockTransaction.objects.filter(
                date__date=current_date,
                transaction_type='out'
            ).aggregate(total=Sum('quantity'))['total'] or 0

            stock_in.append(day_in)
            stock_out.append(day_out)

            current_date += timedelta(days=1)

        context['stock_movement_dates'] = dates
        context['stock_movement_in'] = stock_in
        context['stock_movement_out'] = stock_out

        # إضافة عدد التنبيهات النشطة
        from .models import StockAlert
        context['alerts_count'] = StockAlert.objects.filter(status='active').count()

        # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
        context['recent_alerts'] = StockAlert.objects.filter(
            status='active'
        ).select_related('product').order_by('-created_at')[:5]

        # إضافة السنة الحالية لشريط التذييل
        from datetime import datetime
        context['current_year'] = datetime.now().year

        return context

@login_required
def product_list(request):
    # البحث والتصفية
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    filter_type = request.GET.get('filter', '')
    sort_by = request.GET.get('sort', '-created_at')

    # الحصول على المنتجات من قاعدة البيانات مع select_related لتحميل العلاقات
    products = Product.objects.all().select_related('category')

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

    # تطبيق فلتر المخزون
    if filter_type == 'low_stock':
        products = products.filter(current_stock_calc__gt=0, current_stock_calc__lte=F('minimum_stock'))
    elif filter_type == 'out_of_stock':
        products = products.filter(current_stock_calc__lte=0)

    # تطبيق الترتيب
    if hasattr(Product, sort_by.lstrip('-')):
        products = products.order_by(sort_by)
    else:
        products = products.order_by('-created_at')

    # الصفحات
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

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

    context = {
        'page_obj': page_obj,
        'categories': Category.objects.all(),
        'search_query': search_query,
        'selected_category': category_id,
        'selected_filter': filter_type,
        'sort_by': sort_by,
        'active_menu': 'products',
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year
    }

    return render(request, 'inventory/product_list_new_icons.html', context)

@login_required
def product_create(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            code = request.POST.get('code')
            category_id = request.POST.get('category')
            description = request.POST.get('description')
            price = request.POST.get('price')
            minimum_stock = request.POST.get('minimum_stock')

            if not all([name, category_id, price, minimum_stock]):
                raise ValueError("جميع الحقول المطلوبة يجب ملؤها")

            category = get_object_or_404(Category, id=category_id)

            product = Product.objects.create(
                name=name,
                code=code,
                category=category,
                description=description,
                price=price,
                minimum_stock=minimum_stock
            )

            # إعادة تحميل الذاكرة المؤقتة للمنتجات
            invalidate_product_cache(product.id)
            messages.success(request, 'تم إضافة المنتج بنجاح.')
            return redirect('inventory:product_list')

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, 'حدث خطأ أثناء إضافة المنتج.')

    categories = Category.objects.all()
    return render(request, 'inventory/product_form.html', {'categories': categories})

@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        try:
            product.name = request.POST.get('name')
            product.code = request.POST.get('code')
            category_id = request.POST.get('category')
            product.category = get_object_or_404(Category, id=category_id)
            product.description = request.POST.get('description')
            product.price = request.POST.get('price')
            product.minimum_stock = request.POST.get('minimum_stock')

            # Validation
            if not all([product.name, product.category, product.price, product.minimum_stock]):
                raise ValueError("جميع الحقول المطلوبة يجب ملؤها")

            product.save()
            # إعادة تحميل الذاكرة المؤقتة للمنتجات
            invalidate_product_cache(product.id)
            messages.success(request, 'تم تحديث المنتج بنجاح.')
            return redirect('inventory:product_list')

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, 'حدث خطأ أثناء تحديث المنتج.')

    categories = Category.objects.all()
    return render(request, 'inventory/product_form.html', {
        'product': product,
        'categories': categories
    })

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

    # الحصول على مستوى المخزون من الذاكرة المؤقتة
    current_stock = get_cached_stock_level(product.id)

    # استخدام select_related للمعاملات
    transactions = product.transactions.select_related(
        'created_by'
    ).order_by('-date')

    # حساب إجمالي الوارد والصادر
    from django.db.models import Sum
    transactions_in = product.transactions.filter(transaction_type='in')
    transactions_out = product.transactions.filter(transaction_type='out')

    transactions_in_total = transactions_in.aggregate(total=Sum('quantity'))['total'] or 0
    transactions_out_total = transactions_out.aggregate(total=Sum('quantity'))['total'] or 0

    # إعداد بيانات الرسم البياني
    from django.utils import timezone
    from datetime import timedelta    # Get dates for last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)

    # Get all transactions up to end_date ordered by transaction_date
    all_transactions = product.transactions.filter(
        transaction_date__date__lte=end_date
    ).order_by('transaction_date')

    # Calculate the running balance for each day in the range
    transaction_dates = []
    transaction_balances = []
    daily_balance = 0

    # Calculate opening balance from transactions before start_date
    opening_transactions = all_transactions.filter(transaction_date__date__lt=start_date)
    for trans in opening_transactions:
        if trans.transaction_type == 'in':
            daily_balance += trans.quantity
        else:
            daily_balance -= trans.quantity

    # إضافة الرصيد لكل يوم    # Iterate through each day in the range
    current_date = start_date
    while current_date <= end_date:
        # Get all transactions for this day
        day_transactions = all_transactions.filter(
            transaction_date__date=current_date
        ).order_by('transaction_date')

        # Update balance with day's transactions
        for trans in day_transactions:
            if trans.transaction_type == 'in':
                daily_balance += trans.quantity
            else:
                daily_balance -= trans.quantity

        # Add date and balance to lists
        transaction_dates.append(current_date)
        transaction_balances.append(daily_balance)

        # Move to next day
        current_date += timedelta(days=1)

    # جلب إعدادات النظام
    system_settings = UnifiedSystemSettings.objects.first()
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

    # الحصول على مستوى المخزون الحالي من الذاكرة المؤقتة
    current_stock = get_cached_stock_level(product.pk)

    if request.method == 'POST':
        try:
            # استخراج البيانات من النموذج
            transaction_type = request.POST.get('transaction_type')
            reason = request.POST.get('reason')
            quantity = request.POST.get('quantity')
            reference = request.POST.get('reference', '')
            notes = request.POST.get('notes', '')

            # التحقق من البيانات المطلوبة
            if not all([transaction_type, reason, quantity]):
                raise ValueError("جميع الحقول المطلوبة يجب ملؤها")

            # التحقق من صحة الكمية
            try:
                quantity = float(quantity)
                if quantity <= 0:
                    raise ValueError("يجب أن تكون الكمية أكبر من صفر")
            except (ValueError, TypeError):
                raise ValueError("الكمية يجب أن تكون رقماً صحيحاً")

            # إعادة فحص المخزون الحالي قبل تسجيل الحركة
            current_stock = get_cached_stock_level(product.pk)

            # التحقق من توفر المخزون للحركات الصادرة
            if transaction_type == 'out':
                if current_stock <= 0:
                    raise ValueError("لا يوجد مخزون متاح للصرف")
                if quantity > current_stock:
                    raise ValueError(f"الكمية المطلوبة ({quantity}) أكبر من المخزون المتاح ({current_stock})")

            # إنشاء حركة المخزون
            transaction = StockTransaction.objects.create(
                product=product,
                transaction_type=transaction_type,
                reason=reason,
                quantity=quantity,
                reference=reference,
                notes=notes,
                created_by=request.user,
                date=timezone.now()
            )

            # إعادة تحميل الذاكرة المؤقتة للمنتج
            invalidate_product_cache(product.id)

            # إضافة رسالة نجاح
            if transaction_type == 'in':
                messages.success(request, f"تم تسجيل حركة وارد بنجاح. الكمية: {quantity}")
            else:
                messages.success(request, f"تم تسجيل حركة صادر بنجاح. الكمية: {quantity}")

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
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year
    }

    return render(request, 'inventory/transaction_form_new.html', context)

@login_required
def transaction_list(request):
    """عرض قائمة حركات المخزون"""
    transactions = StockTransaction.objects.select_related(
        'product', 'created_by'
    ).order_by('-transaction_date')
    
    context = {
        'transactions': transactions,
        'active_menu': 'transactions'
    }
    return render(request, 'inventory/transaction_list.html', context)

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
        'current_stock': p.current_stock_calc,
    } for p in products]

    return JsonResponse(data, safe=False)

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

# Purchase Order Views
@login_required
def purchase_order_list(request):
    """عرض قائمة طلبات الشراء"""
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    supplier_filter = request.GET.get('supplier', '')
    
    purchase_orders = PurchaseOrder.objects.select_related(
        'supplier', 'warehouse', 'created_by'
    ).prefetch_related('items')
    
    # تطبيق البحث
    if search_query:
        purchase_orders = purchase_orders.filter(
            Q(order_number__icontains=search_query) |
            Q(supplier__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # تطبيق فلتر الحالة
    if status_filter:
        purchase_orders = purchase_orders.filter(status=status_filter)
    
    # تطبيق فلتر المورد
    if supplier_filter:
        purchase_orders = purchase_orders.filter(supplier_id=supplier_filter)
    
    # الترتيب
    purchase_orders = purchase_orders.order_by('-order_date')
    
    # الصفحات
    paginator = Paginator(purchase_orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'selected_status': status_filter,
        'selected_supplier': supplier_filter,
        'status_choices': PurchaseOrder.STATUS_CHOICES,
        'suppliers': Supplier.objects.all(),
        'active_menu': 'purchase_orders'
    }
    
    return render(request, 'inventory/purchase_order_list_new.html', context)

@login_required
def purchase_order_detail(request, pk):
    """عرض تفاصيل طلب الشراء"""
    purchase_order = get_object_or_404(PurchaseOrder.objects.select_related(
        'supplier', 'warehouse', 'created_by'
    ).prefetch_related('items__product'), pk=pk)
    
    context = {
        'purchase_order': purchase_order,
        'active_menu': 'purchase_orders'
    }
    
    return render(request, 'inventory/purchase_order_detail.html', context)

@login_required
def purchase_order_create(request):
    """إنشاء طلب شراء جديد"""
    from .forms import PurchaseOrderForm
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            purchase_order = form.save(commit=False)
            purchase_order.created_by = request.user
            purchase_order.save()
            messages.success(request, 'تم إنشاء طلب الشراء بنجاح')
            return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)
    else:
        form = PurchaseOrderForm()
    
    context = {
        'form': form,
        'active_menu': 'purchase_orders'
    }
    
    return render(request, 'inventory/purchase_order_form.html', context)

@login_required
def purchase_order_update(request, pk):
    """تعديل طلب الشراء"""
    from .forms import PurchaseOrderForm
    
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=purchase_order)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث طلب الشراء بنجاح')
            return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)
    else:
        form = PurchaseOrderForm(instance=purchase_order)
    
    context = {
        'form': form,
        'purchase_order': purchase_order,
        'active_menu': 'purchase_orders'
    }
    
    return render(request, 'inventory/purchase_order_form.html', context)

@login_required
def purchase_order_delete(request, pk):
    """حذف طلب الشراء"""
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if request.method == 'POST':
        purchase_order.delete()
        messages.success(request, 'تم حذف طلب الشراء بنجاح')
        return redirect('inventory:purchase_order_list')
    
    context = {
        'purchase_order': purchase_order,
        'active_menu': 'purchase_orders'
    }
    
    return render(request, 'inventory/purchase_order_confirm_delete.html', context)

@login_required
def purchase_order_receive(request, pk):
    """استلام طلب الشراء"""
    purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
    
    if request.method == 'POST':
        # تحديث حالة الطلب إلى مستلم
        purchase_order.status = 'received'
        purchase_order.save()
        
        # إنشاء حركات مخزون للمنتجات المستلمة
        for item in purchase_order.items.all():
            if item.received_quantity > 0:
                StockTransaction.objects.create(
                    product=item.product,
                    transaction_type='in',
                    reason='purchase',
                    quantity=item.received_quantity,
                    reference=f"PO-{purchase_order.order_number}",
                    notes=f"استلام من طلب الشراء {purchase_order.order_number}",
                    created_by=request.user
                )
        
        messages.success(request, 'تم استلام طلب الشراء بنجاح')
        return redirect('inventory:purchase_order_detail', pk=purchase_order.pk)
    
    context = {
        'purchase_order': purchase_order,
        'active_menu': 'purchase_orders'
    }
    
    return render(request, 'inventory/purchase_order_receive.html', context)

@login_required
@require_POST
def validate_product_ajax(request):
    """AJAX validation for product form"""
    try:
        data = json.loads(request.body)
        name = data.get('name')
        code = data.get('code')
        price = data.get('price')
        
        # Validate required fields
        if not name or not name.strip():
            return JsonResponse({'valid': False, 'message': 'اسم المنتج مطلوب'})
        
        if not price or float(price) <= 0:
            return JsonResponse({'valid': False, 'message': 'السعر يجب أن يكون أكبر من صفر'})
        
        # Validate code uniqueness
        if code:
            qs = Product.objects.filter(code=code)
            if request.POST.get('product_id'):  # Update case
                qs = qs.exclude(id=request.POST.get('product_id'))
            if qs.exists():
                return JsonResponse({'valid': False, 'message': 'كود المنتج موجود مسبقاً'})
        
        return JsonResponse({'valid': True})
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)})

@login_required
@require_POST
def validate_transaction_ajax(request):
    """AJAX validation for transaction form"""
    try:
        data = json.loads(request.body)
        quantity = data.get('quantity')
        transaction_type = data.get('transaction_type')
        product_id = data.get('product_id')
        
        if not quantity or int(quantity) <= 0:
            return JsonResponse({'valid': False, 'message': 'الكمية يجب أن تكون أكبر من صفر'})
        
        if not transaction_type:
            return JsonResponse({'valid': False, 'message': 'نوع المعاملة مطلوب'})
        
        if not product_id or not Product.objects.filter(id=product_id).exists():
            return JsonResponse({'valid': False, 'message': 'المنتج غير موجود'})
        
        # Validate stock for outgoing transactions
        if transaction_type == 'out' and product_id:
            product = Product.objects.get(id=product_id)
            if product.current_stock < int(quantity):
                return JsonResponse({'valid': False, 'message': f'الكمية المتوفرة ({product.current_stock}) أقل من المطلوب ({quantity})'})
        
        return JsonResponse({'valid': True})
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)})

@login_required
def get_stock_info_ajax(request, product_id):
    """Get stock information for AJAX requests"""
    try:
        product = Product.objects.get(id=product_id)
        return JsonResponse({
            'name': product.name,
            'current_stock': product.current_stock,
            'minimum_stock': product.minimum_stock,
            'price': str(product.price),
            'category': product.category.name if product.category else None,
            'is_low_stock': product.current_stock <= product.minimum_stock
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'المنتج غير موجود'}, status=404)

@login_required
def category_list(request):
    """عرض قائمة التصنيفات (الفئات)"""
    categories = Category.objects.all().order_by('name')
    context = {
        'categories': categories,
        'active_menu': 'categories',
    }
    return render(request, 'inventory/category_list.html', context)

# Category Views
@login_required
def category_create(request):
    """إنشاء فئة جديدة"""
    if request.method == 'POST':
        name = request.POST.get('name')
        parent_id = request.POST.get('parent')
        description = request.POST.get('description')
        
        parent = None
        if parent_id:
            parent = Category.objects.get(id=parent_id)
        
        Category.objects.create(
            name=name,
            parent=parent,
            description=description
        )
        messages.success(request, 'تم إنشاء الفئة بنجاح')
        return redirect('inventory:category_list')
    
    context = {
        'categories': Category.objects.all(),
        'active_menu': 'categories'
    }
    return render(request, 'inventory/category_form.html', context)

@login_required
def category_update(request, pk):
    """تعديل فئة"""
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name')
        parent_id = request.POST.get('parent')
        description = request.POST.get('description')
        
        parent = None
        if parent_id:
            parent = Category.objects.get(id=parent_id)
        
        category.name = name
        category.parent = parent
        category.description = description
        category.save()
        
        messages.success(request, 'تم تحديث الفئة بنجاح')
        return redirect('inventory:category_list')
    
    context = {
        'category': category,
        'categories': Category.objects.exclude(id=pk),
        'active_menu': 'categories'
    }
    return render(request, 'inventory/category_form.html', context)

@login_required
def category_delete(request, pk):
    """حذف فئة"""
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'تم حذف الفئة بنجاح')
        return redirect('inventory:category_list')
    
    context = {
        'category': category,
        'active_menu': 'categories'
    }
    return render(request, 'inventory/category_confirm_delete.html', context)

# Transaction Views
@login_required
def adjustment_list(request):
    """عرض قائمة تسويات المخزون"""
    from .models import InventoryAdjustment
    adjustments = InventoryAdjustment.objects.select_related(
        'product', 'batch', 'created_by'
    ).order_by('-date')
    
    context = {
        'adjustments': adjustments,
        'active_menu': 'adjustments'
    }
    return render(request, 'inventory/adjustment_list.html', context)

@login_required
def adjustment_create(request):
    """إنشاء تسوية مخزون"""
    from .models import InventoryAdjustment
    if request.method == 'POST':
        product_id = request.POST.get('product')
        adjustment_type = request.POST.get('adjustment_type')
        quantity_before = request.POST.get('quantity_before')
        quantity_after = request.POST.get('quantity_after')
        reason = request.POST.get('reason')
        
        product = Product.objects.get(id=product_id)
        
        InventoryAdjustment.objects.create(
            product=product,
            adjustment_type=adjustment_type,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reason=reason,
            created_by=request.user
        )
        
        messages.success(request, 'تم إنشاء التسوية بنجاح')
        return redirect('inventory:adjustment_list')
    
    context = {
        'products': Product.objects.all(),
        'active_menu': 'adjustments'
    }
    return render(request, 'inventory/adjustment_form.html', context)

@login_required
def adjustment_detail(request, pk):
    """عرض تفاصيل التسوية"""
    from .models import InventoryAdjustment
    adjustment = get_object_or_404(InventoryAdjustment, pk=pk)
    
    context = {
        'adjustment': adjustment,
        'active_menu': 'adjustments'
    }
    return render(request, 'inventory/adjustment_detail.html', context)

@login_required
def adjustment_update(request, pk):
    """تعديل التسوية"""
    from .models import InventoryAdjustment
    adjustment = get_object_or_404(InventoryAdjustment, pk=pk)
    
    if request.method == 'POST':
        adjustment_type = request.POST.get('adjustment_type')
        quantity_before = request.POST.get('quantity_before')
        quantity_after = request.POST.get('quantity_after')
        reason = request.POST.get('reason')
        
        adjustment.adjustment_type = adjustment_type
        adjustment.quantity_before = quantity_before
        adjustment.quantity_after = quantity_after
        adjustment.reason = reason
        adjustment.save()
        
        messages.success(request, 'تم تحديث التسوية بنجاح')
        return redirect('inventory:adjustment_detail', pk=adjustment.pk)
    
    context = {
        'adjustment': adjustment,
        'active_menu': 'adjustments'
    }
    return render(request, 'inventory/adjustment_form.html', context)

@login_required
def adjustment_delete(request, pk):
    """حذف التسوية"""
    from .models import InventoryAdjustment
    adjustment = get_object_or_404(InventoryAdjustment, pk=pk)
    
    if request.method == 'POST':
        adjustment.delete()
        messages.success(request, 'تم حذف التسوية بنجاح')
        return redirect('inventory:adjustment_list')
    
    context = {
        'adjustment': adjustment,
        'active_menu': 'adjustments'
    }
    return render(request, 'inventory/adjustment_confirm_delete.html', context)

# Supplier Views
@login_required
def supplier_list(request):
    """عرض قائمة الموردين"""
    suppliers = Supplier.objects.all().order_by('name')
    
    context = {
        'suppliers': suppliers,
        'active_menu': 'suppliers'
    }
    return render(request, 'inventory/supplier_list_new.html', context)

@login_required
def supplier_create(request):
    """إنشاء مورد جديد"""
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_person = request.POST.get('contact_person')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        tax_number = request.POST.get('tax_number')
        notes = request.POST.get('notes')
        
        Supplier.objects.create(
            name=name,
            contact_person=contact_person,
            phone=phone,
            email=email,
            address=address,
            tax_number=tax_number,
            notes=notes
        )
        
        messages.success(request, 'تم إنشاء المورد بنجاح')
        return redirect('inventory:supplier_list')
    
    context = {
        'active_menu': 'suppliers'
    }
    return render(request, 'inventory/supplier_form.html', context)

@login_required
def supplier_detail(request, pk):
    """عرض تفاصيل المورد"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    context = {
        'supplier': supplier,
        'active_menu': 'suppliers'
    }
    return render(request, 'inventory/supplier_detail.html', context)

@login_required
def supplier_update(request, pk):
    """تعديل المورد"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier.name = request.POST.get('name')
        supplier.contact_person = request.POST.get('contact_person')
        supplier.phone = request.POST.get('phone')
        supplier.email = request.POST.get('email')
        supplier.address = request.POST.get('address')
        supplier.tax_number = request.POST.get('tax_number')
        supplier.notes = request.POST.get('notes')
        supplier.save()
        
        messages.success(request, 'تم تحديث المورد بنجاح')
        return redirect('inventory:supplier_detail', pk=supplier.pk)
    
    context = {
        'supplier': supplier,
        'active_menu': 'suppliers'
    }
    return render(request, 'inventory/supplier_form.html', context)

@login_required
def supplier_delete(request, pk):
    """حذف المورد"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, 'تم حذف المورد بنجاح')
        return redirect('inventory:supplier_list')
    
    context = {
        'supplier': supplier,
        'active_menu': 'suppliers'
    }
    return render(request, 'inventory/supplier_confirm_delete.html', context)

# Warehouse Views
@login_required
def warehouse_list(request):
    """عرض قائمة المستودعات"""
    from .models import Warehouse
    warehouses = Warehouse.objects.select_related('branch', 'manager').all()
    
    context = {
        'warehouses': warehouses,
        'active_menu': 'warehouses'
    }
    return render(request, 'inventory/warehouse_list_new.html', context)

@login_required
def warehouse_create(request):
    """إنشاء مستودع جديد"""
    from .models import Warehouse
    from accounts.models import Branch
    
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        branch_id = request.POST.get('branch')
        manager_id = request.POST.get('manager')
        address = request.POST.get('address')
        notes = request.POST.get('notes')
        
        branch = Branch.objects.get(id=branch_id) if branch_id else None
        manager = None
        if manager_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            manager = User.objects.get(id=manager_id)
        
        Warehouse.objects.create(
            name=name,
            code=code,
            branch=branch,
            manager=manager,
            address=address,
            notes=notes
        )
        
        messages.success(request, 'تم إنشاء المستودع بنجاح')
        return redirect('inventory:warehouse_list')
    
    context = {
        'branches': Branch.objects.all(),
        'active_menu': 'warehouses'
    }
    return render(request, 'inventory/warehouse_form.html', context)

@login_required
def warehouse_detail(request, pk):
    """عرض تفاصيل المستودع"""
    from .models import Warehouse
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    context = {
        'warehouse': warehouse,
        'active_menu': 'warehouses'
    }
    return render(request, 'inventory/warehouse_detail.html', context)

@login_required
def warehouse_update(request, pk):
    """تعديل المستودع"""
    from .models import Warehouse
    from accounts.models import Branch
    
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    if request.method == 'POST':
        warehouse.name = request.POST.get('name')
        warehouse.code = request.POST.get('code')
        branch_id = request.POST.get('branch')
        manager_id = request.POST.get('manager')
        warehouse.address = request.POST.get('address')
        warehouse.notes = request.POST.get('notes')
        
        if branch_id:
            warehouse.branch = Branch.objects.get(id=branch_id)
        else:
            warehouse.branch = None
        
        if manager_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            warehouse.manager = User.objects.get(id=manager_id)
        else:
            warehouse.manager = None
        
        warehouse.save()
        
        messages.success(request, 'تم تحديث المستودع بنجاح')
        return redirect('inventory:warehouse_detail', pk=warehouse.pk)
    
    context = {
        'warehouse': warehouse,
        'branches': Branch.objects.all(),
        'active_menu': 'warehouses'
    }
    return render(request, 'inventory/warehouse_form.html', context)

@login_required
def warehouse_delete(request, pk):
    """حذف المستودع"""
    from .models import Warehouse
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    if request.method == 'POST':
        warehouse.delete()
        messages.success(request, 'تم حذف المستودع بنجاح')
        return redirect('inventory:warehouse_list')
    
    context = {
        'warehouse': warehouse,
        'active_menu': 'warehouses'
    }
    return render(request, 'inventory/warehouse_confirm_delete.html', context)

# Warehouse Location Views
@login_required
def warehouse_location_list(request):
    """عرض قائمة مواقع المستودعات"""
    from .models import WarehouseLocation
    locations = WarehouseLocation.objects.select_related('warehouse').all()
    
    context = {
        'locations': locations,
        'active_menu': 'warehouse_locations'
    }
    return render(request, 'inventory/warehouse_location_list.html', context)

@login_required
def warehouse_location_create(request):
    """إنشاء موقع مستودع جديد"""
    from .models import WarehouseLocation, Warehouse
    
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        warehouse_id = request.POST.get('warehouse')
        description = request.POST.get('description')
        
        warehouse = Warehouse.objects.get(id=warehouse_id)
        
        WarehouseLocation.objects.create(
            name=name,
            code=code,
            warehouse=warehouse,
            description=description
        )
        
        messages.success(request, 'تم إنشاء موقع المستودع بنجاح')
        return redirect('inventory:warehouse_location_list')
    
    context = {
        'warehouses': Warehouse.objects.all(),
        'active_menu': 'warehouse_locations'
    }
    return render(request, 'inventory/warehouse_location_form.html', context)

@login_required
def warehouse_location_update(request, pk):
    """تعديل موقع المستودع"""
    from .models import WarehouseLocation, Warehouse
    
    location = get_object_or_404(WarehouseLocation, pk=pk)
    
    if request.method == 'POST':
        location.name = request.POST.get('name')
        location.code = request.POST.get('code')
        warehouse_id = request.POST.get('warehouse')
        location.description = request.POST.get('description')
        
        location.warehouse = Warehouse.objects.get(id=warehouse_id)
        location.save()
        
        messages.success(request, 'تم تحديث موقع المستودع بنجاح')
        return redirect('inventory:warehouse_location_list')
    
    context = {
        'location': location,
        'warehouses': Warehouse.objects.all(),
        'active_menu': 'warehouse_locations'
    }
    return render(request, 'inventory/warehouse_location_form.html', context)

@login_required
def warehouse_location_delete(request, pk):
    """حذف موقع المستودع"""
    from .models import WarehouseLocation
    location = get_object_or_404(WarehouseLocation, pk=pk)
    
    if request.method == 'POST':
        location.delete()
        messages.success(request, 'تم حذف موقع المستودع بنجاح')
        return redirect('inventory:warehouse_location_list')
    
    context = {
        'location': location,
        'active_menu': 'warehouse_locations'
    }
    return render(request, 'inventory/warehouse_location_confirm_delete.html', context)

# Alert Views
@login_required
def alert_list(request):
    """عرض قائمة التنبيهات"""
    alerts = StockAlert.objects.select_related('product').order_by('-created_at')
    
    context = {
        'alerts': alerts,
        'active_menu': 'alerts'
    }
    return render(request, 'inventory/alert_list_new.html', context)

@login_required
def alert_detail(request, pk):
    """عرض تفاصيل التنبيه"""
    alert = get_object_or_404(StockAlert, pk=pk)
    
    context = {
        'alert': alert,
        'active_menu': 'alerts'
    }
    return render(request, 'inventory/alert_detail.html', context)

@login_required
def alert_resolve(request, pk):
    """حل التنبيه"""
    alert = get_object_or_404(StockAlert, pk=pk)
    
    if request.method == 'POST':
        alert.status = 'resolved'
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.save()
        
        messages.success(request, 'تم حل التنبيه بنجاح')
        return redirect('inventory:alert_list')
    
    context = {
        'alert': alert,
        'active_menu': 'alerts'
    }
    return render(request, 'inventory/alert_resolve.html', context)

@login_required
def alert_delete(request, pk):
    """حذف التنبيه"""
    alert = get_object_or_404(StockAlert, pk=pk)
    
    if request.method == 'POST':
        alert.delete()
        messages.success(request, 'تم حذف التنبيه بنجاح')
        return redirect('inventory:alert_list')
    
    context = {
        'alert': alert,
        'active_menu': 'alerts'
    }
    return render(request, 'inventory/alert_confirm_delete.html', context)

# Report Views
@login_required
def low_stock_report(request):
    """تقرير المخزون المنخفض"""
    low_stock_products = Product.objects.filter(
        current_stock_calc__gt=0,
        current_stock_calc__lte=F('minimum_stock')
    ).select_related('category')
    
    context = {
        'low_stock_products': low_stock_products,
        'active_menu': 'reports'
    }
    return render(request, 'inventory/low_stock_report.html', context)

@login_required
def stock_movement_report(request):
    """تقرير حركة المخزون"""
    from datetime import datetime, timedelta
    
    # الحصول على الفترة المطلوبة
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # الحصول على الحركات في الفترة المحددة
    transactions = StockTransaction.objects.filter(
        transaction_date__date__range=[start_date, end_date]
    ).select_related('product').order_by('-transaction_date')
    
    context = {
        'transactions': transactions,
        'start_date': start_date,
        'end_date': end_date,
        'active_menu': 'reports'
    }
    return render(request, 'inventory/stock_movement_report.html', context)

@login_required
def report_list(request):
    """عرض قائمة التقارير"""
    context = {
        'active_menu': 'reports'
    }
    return render(request, 'inventory/report_list.html', context)
