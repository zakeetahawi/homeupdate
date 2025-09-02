from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Product, PurchaseOrder

class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_products'] = Product.objects.count()
        context['low_stock_count'] = sum(1 for p in Product.objects.all() if p.current_stock <= p.minimum_stock and p.current_stock > 0)
        context['purchase_orders_count'] = PurchaseOrder.objects.filter(status='ordered').count()
        context['inventory_value'] = sum(p.current_stock * p.price for p in Product.objects.all())
        context['recent_products'] = Product.objects.order_by('-created_at')[:10]
        return context

"""
طرق عرض محسنة إضافية للوحة التحكم ومراقبة أداء المخزون
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Case, When, IntegerField, F, Count, Value
from .models import Product, Category, StockTransaction
from .inventory_utils import get_cached_stock_level

@login_required
def optimized_product_detail(request, product_id):
    """
    نسخة محسنة من صفحة تفاصيل المنتج التي تستخدم التخزين المؤقت وتقلل استعلامات قاعدة البيانات
    """
    from django.shortcuts import get_object_or_404
    
    product = get_object_or_404(Product, pk=product_id)
    
    # استخدام التخزين المؤقت
    current_stock = get_cached_stock_level(product_id)
    
    # استعلام أكثر كفاءة للمعاملات مع البيانات المرتبطة
    transactions = StockTransaction.objects.filter(
        product_id=product_id
    ).select_related(
        'created_by', 'reason'
    ).order_by('-date')[:20]
    
    context = {
        'product': product,
        'current_stock': current_stock,
        'stock_status': (
            'نفذ من المخزون' if current_stock == 0
            else 'مخزون منخفض' if current_stock <= product.minimum_stock
            else 'متوفر'
        ),
        'transactions': transactions
    }
    
    return render(request, 'inventory/product_detail.html', context)

@login_required
def low_stock_report(request):
    """
    تقرير محسن للمنتجات منخفضة المخزون
    """
    # استعلام محسن لحساب المخزون في استعلام واحد
    products = Product.objects.select_related('category').annotate(
        stock_in=Sum(
            Case(
                When(stock_transactions__transaction_type='in', then='stock_transactions__quantity'),
                default=0,
                output_field=IntegerField()
            )
        ),
        stock_out=Sum(
            Case(
                When(stock_transactions__transaction_type='out', then='stock_transactions__quantity'),
                default=0,
                output_field=IntegerField()
            )
        ),
        current_stock_calc=F('stock_in') - F('stock_out')
    ).filter(
        current_stock_calc__gt=0,  # أكبر من صفر
        current_stock_calc__lte=F('minimum_stock')  # أقل من أو يساوي الحد الأدنى
    ).order_by('category__name', 'name')
    
    # تقسيم الصفحات
    paginator = Paginator(products, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'title': 'تقرير المنتجات منخفضة المخزون',
        'total_count': products.count()
    }
    
    return render(request, 'inventory/stock_report.html', context)

@login_required
def stock_movement_report(request):
    """
    تقرير محسن لحركة المخزون
    """
    from django.utils import timezone
    import datetime
    
    # الفترة الزمنية الافتراضية: آخر 30 يوم
    end_date = timezone.now().date()
    start_date = end_date - datetime.timedelta(days=30)
    
    # التاريخ المحدد من المستخدم (إن وجد)
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')
    
    if start_date_param:
        try:
            start_date = datetime.datetime.strptime(start_date_param, '%Y-%m-%d').date()
        except ValueError:
            pass
            
    if end_date_param:
        try:
            end_date = datetime.datetime.strptime(end_date_param, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # استعلام محسن للحصول على حركات المخزون في الفترة المحددة
    transactions = StockTransaction.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date
    ).select_related(
        'product', 'reason', 'created_by'
    ).order_by('-date')
    
    # تحليل البيانات للحصول على ملخصات
    product_movements = transactions.values(
        'product__name'
    ).annotate(
        stock_in=Sum(
            Case(
                When(transaction_type='in', then='quantity'),
                default=0,
                output_field=IntegerField()
            )
        ),
        stock_out=Sum(
            Case(
                When(transaction_type='out', then='quantity'),
                default=0,
                output_field=IntegerField()
            )
        ),
        net_change=Sum(
            Case(
                When(transaction_type='in', then='quantity'),
                When(transaction_type='out', then=-F('quantity')),
                default=0,
                output_field=IntegerField()
            )
        )
    ).order_by('-net_change')
    
    context = {
        'transactions': transactions[:100],  # عرض أحدث 100 حركة فقط
        'product_movements': product_movements,
        'start_date': start_date,
        'end_date': end_date,
        'total_movements': transactions.count()
    }
    
    return render(request, 'inventory/stock_movement_report.html', context)
