"""
API Views for Products Search
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from inventory.models import Product


@login_required
@require_http_methods(["GET"])
def products_search_api(request):
    """
    API endpoint للبحث عن المنتجات
    يستخدم في Select2 للويزارد
    """
    try:
        query = request.GET.get('q', '').strip()
        page = int(request.GET.get('page', 1))
        page_size = 20
        
        # البحث في المنتجات (بدون is_active لأنه غير موجود)
        products = Product.objects.select_related('category')
        
        if query:
            products = products.filter(
                Q(name__icontains=query) |
                Q(code__icontains=query) |
                Q(category__name__icontains=query)
            )
        
        # ترتيب النتائج
        products = products.order_by('name')
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        total_count = products.count()
        products_page = products[start:end]
        
        # تحضير النتائج
        results = []
        for product in products_page:
            results.append({
                'id': product.id,
                'text': product.name,
                'name': product.name,
                'code': product.code,
                'price': float(product.price) if product.price else 0.0,
                'category': product.category.name if product.category else '',
            })
        
        return JsonResponse({
            'results': results,
            'has_more': end < total_count,
            'total': total_count
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in products_search_api: {e}")
        
        return JsonResponse({
            'results': [],
            'has_more': False,
            'total': 0,
            'error': str(e)
        }, status=500)
