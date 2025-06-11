from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, F
from .models import Product, Category, PurchaseOrder
from .inventory_utils import (
    get_cached_stock_level,
    get_cached_product_list,
    get_cached_dashboard_stats,
    invalidate_product_cache
)

class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/dashboard_new_icons.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # استخدام التخزين المؤقت للإحصائيات
        stats = get_cached_dashboard_stats()
        context.update(stats)

        # إضافة active_menu للقائمة الجانبية
        context['active_menu'] = 'dashboard'

        # الحصول على المنتجات منخفضة المخزون
        products = get_cached_product_list(include_stock=True)
        low_stock_products = [p for p in products if 0 < p.current_stock_calc <= p.minimum_stock]
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
    from datetime import timedelta

    # الحصول على تواريخ آخر 30 يوم
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)

    # الحصول على المعاملات في الفترة المحددة
    period_transactions = transactions.filter(date__date__gte=start_date, date__date__lte=end_date)

    # إعداد قائمة التواريخ والأرصدة
    transaction_dates = []
    transaction_balances = []

    # حساب الرصيد الافتتاحي
    opening_balance = transactions.filter(date__date__lt=start_date).aggregate(
        in_total=Sum('quantity', filter=Q(transaction_type='in')),
        out_total=Sum('quantity', filter=Q(transaction_type='out'))
    )

    opening_in = opening_balance['in_total'] or 0
    opening_out = opening_balance['out_total'] or 0
    balance = opening_in - opening_out

    # إضافة الرصيد لكل يوم
    current_date = start_date
    while current_date <= end_date:
        # حساب حركات اليوم
        day_transactions = period_transactions.filter(date__date=current_date)
        day_in = day_transactions.filter(transaction_type='in').aggregate(total=Sum('quantity'))['total'] or 0
        day_out = day_transactions.filter(transaction_type='out').aggregate(total=Sum('quantity'))['total'] or 0

        # تحديث الرصيد
        balance += day_in - day_out

        # إضافة اليوم والرصيد إلى القوائم
        transaction_dates.append(current_date)
        transaction_balances.append(balance)

        # الانتقال إلى اليوم التالي
        current_date += timedelta(days=1)

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
        'current_year': current_year
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

            # التحقق من توفر المخزون للحركات الصادرة
            current_stock = get_cached_stock_level(product.id)
            if transaction_type == 'out' and quantity > current_stock:
                raise ValueError(f"الكمية المطلوبة ({quantity}) أكبر من المخزون المتاح ({current_stock})")

            # إنشاء حركة المخزون
            from .models import StockTransaction
            transaction = StockTransaction.objects.create(
                product=product,
                transaction_type=transaction_type,
                reason=reason,
                quantity=quantity,
                reference=reference,
                notes=notes,
                created_by=request.user
            )

            # إعادة تحميل الذاكرة المؤقتة للمنتج
            invalidate_product_cache(product.id)

            # إضافة رسالة نجاح
            messages.success(request, f"تم تسجيل حركة المخزون بنجاح. الكمية: {quantity}")

            # إعادة التوجيه إلى صفحة تفاصيل المنتج
            return redirect('inventory:product_detail', pk=product.pk)

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء تسجيل حركة المخزون: {str(e)}")

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
        'transaction_types': transaction_types,
        'transaction_reasons': transaction_reasons,
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year
    }

    return render(request, 'inventory/transaction_form.html', context)

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
from installations.models import Installation
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
            'pendingInstallations': Installation.objects.filter(
                status='pending').count(),
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
