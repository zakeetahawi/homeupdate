"""
Utilidades para el manejo de caché en el módulo de inventario.
"""
from django.core.cache import cache
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import (
    Product, Category, Supplier, Warehouse, StockTransaction,
    PurchaseOrder, StockAlert
)

# Tiempos de caché en segundos
CACHE_TIMEOUT_SHORT = 60 * 5  # 5 minutos
CACHE_TIMEOUT_MEDIUM = 60 * 30  # 30 minutos
CACHE_TIMEOUT_LONG = 60 * 60 * 12  # 12 horas

def get_cached_dashboard_stats():
    """
    Obtiene las estadísticas del dashboard desde la caché o las calcula si no están en caché.
    """
    cache_key = 'inventory_dashboard_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        # Calcular estadísticas
        total_products = Product.objects.count()
        total_categories = Category.objects.count()
        total_suppliers = Supplier.objects.count()
        total_warehouses = Warehouse.objects.count()
        
        # Productos con stock bajo
        low_stock_count = 0
        products = Product.objects.all()
        for product in products:
            current_stock = get_cached_stock_level(product.id)
            if 0 < current_stock <= product.minimum_stock:
                low_stock_count += 1
        
        # Productos sin stock
        out_of_stock_count = 0
        for product in products:
            current_stock = get_cached_stock_level(product.id)
            if current_stock <= 0:
                out_of_stock_count += 1
        
        # Órdenes de compra pendientes
        pending_orders = PurchaseOrder.objects.filter(
            status__in=['draft', 'pending', 'approved', 'partial']
        ).count()
        
        # Alertas activas
        active_alerts = StockAlert.objects.filter(status='active').count()
        
        # Transacciones recientes
        recent_transactions = StockTransaction.objects.select_related(
            'product', 'created_by'
        ).order_by('-date')[:10]
        
        # Productos más vendidos (últimos 30 días)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        top_products = Product.objects.annotate(
            total_out=Sum('transactions__quantity', 
                         filter=Q(transactions__transaction_type='out') & 
                                Q(transactions__date__date__gte=start_date) & 
                                Q(transactions__date__date__lte=end_date))
        ).filter(total_out__gt=0).order_by('-total_out')[:5]
        
        # Guardar estadísticas en caché
        stats = {
            'total_products': total_products,
            'total_categories': total_categories,
            'total_suppliers': total_suppliers,
            'total_warehouses': total_warehouses,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'pending_orders': pending_orders,
            'active_alerts': active_alerts,
            'recent_transactions': list(recent_transactions.values(
                'id', 'product__name', 'transaction_type', 'quantity', 
                'date', 'created_by__first_name', 'created_by__last_name'
            )),
            'top_products': list(top_products.values('id', 'name', 'total_out'))
        }
        
        cache.set(cache_key, stats, CACHE_TIMEOUT_MEDIUM)
    
    return stats

def get_cached_stock_level(product_id):
    """
    Obtiene el nivel de stock de un producto desde la caché o lo calcula si no está en caché.
    """
    cache_key = f'product_stock_{product_id}'
    stock_level = cache.get(cache_key)
    
    if stock_level is None:
        # Calcular nivel de stock
        transactions = StockTransaction.objects.filter(product_id=product_id)
        
        stock_in = transactions.filter(transaction_type='in').aggregate(
            total=Sum('quantity'))['total'] or 0
        stock_out = transactions.filter(transaction_type='out').aggregate(
            total=Sum('quantity'))['total'] or 0
        
        stock_level = stock_in - stock_out
        
        # Guardar en caché
        cache.set(cache_key, stock_level, CACHE_TIMEOUT_SHORT)
    
    return stock_level

def invalidate_product_stock_cache(product_id):
    """
    Invalida la caché de nivel de stock de un producto.
    """
    cache_key = f'product_stock_{product_id}'
    cache.delete(cache_key)
    
    # También invalidar la caché del dashboard
    cache.delete('inventory_dashboard_stats')

def invalidate_product_cache(product_id):
    """
    Invalida la caché de un producto específico y caches relacionadas.
    """
    cache_keys = [
        f'product_detail_{product_id}',
        f'product_stock_{product_id}',
        'product_list_all',
        'inventory_dashboard_stats'
    ]
    
    for key in cache_keys:
        cache.delete(key)
    
    # También invalidar la caché de listas de productos por categoría
    cache.delete_many([
        'product_list_None_False',
        'product_list_None_True',
    ])

def get_cached_product_list(category_id=None, include_stock=False):
    """
    Obtiene la lista de productos desde la caché o la calcula si no está en caché.
    """
    cache_key = f'product_list_{category_id}_{include_stock}'
    products = cache.get(cache_key)
    
    if products is None:
        # Obtener productos
        queryset = Product.objects.select_related('category')
        
        if category_id:
            queryset = queryset.filter(
                Q(category_id=category_id) | 
                Q(category__parent_id=category_id)
            )
        
        products = list(queryset)
        
        # Calcular nivel de stock si es necesario
        if include_stock:
            for product in products:
                product.current_stock_calc = get_cached_stock_level(product.id)
                
                # Calcular porcentaje de stock
                if product.minimum_stock > 0:
                    product.stock_percentage = min(
                        int((product.current_stock_calc / product.minimum_stock) * 100), 
                        100
                    )
                else:
                    product.stock_percentage = 100
        
        # Guardar en caché
        cache.set(cache_key, products, CACHE_TIMEOUT_SHORT)
    
    return products

def get_cached_category_list():
    """
    Obtiene la lista de categorías desde la caché o la calcula si no está en caché.
    """
    cache_key = 'category_list'
    categories = cache.get(cache_key)
    
    if categories is None:
        # Obtener categorías con prefetch de productos y categorías hijas
        categories = list(Category.objects.prefetch_related('children', 'products'))
        
        # Guardar en caché
        cache.set(cache_key, categories, CACHE_TIMEOUT_MEDIUM)
    
    return categories

def invalidate_category_cache():
    """
    Invalida la caché de categorías.
    """
    cache.delete('category_list')
    
    # También invalidar la caché de productos
    for key in cache.keys('product_list_*'):
        cache.delete(key)

def get_cached_supplier_list():
    """
    Obtiene la lista de proveedores desde la caché o la calcula si no está en caché.
    """
    cache_key = 'supplier_list'
    suppliers = cache.get(cache_key)
    
    if suppliers is None:
        # Obtener proveedores
        suppliers = list(Supplier.objects.all())
        
        # Guardar en caché
        cache.set(cache_key, suppliers, CACHE_TIMEOUT_MEDIUM)
    
    return suppliers

def invalidate_supplier_cache():
    """
    Invalida la caché de proveedores.
    """
    cache.delete('supplier_list')

def get_cached_warehouse_list():
    """
    Obtiene la lista de almacenes desde la caché o la calcula si no está en caché.
    """
    cache_key = 'warehouse_list'
    warehouses = cache.get(cache_key)
    
    if warehouses is None:
        # Obtener almacenes
        warehouses = list(Warehouse.objects.select_related('branch', 'manager'))
        
        # Guardar en caché
        cache.set(cache_key, warehouses, CACHE_TIMEOUT_MEDIUM)
    
    return warehouses

def invalidate_warehouse_cache():
    """
    Invalida la caché de almacenes.
    """
    cache.delete('warehouse_list')

def get_cached_alert_count():
    """
    Obtiene el número de alertas activas desde la caché o lo calcula si no está en caché.
    """
    cache_key = 'active_alerts_count'
    count = cache.get(cache_key)
    
    if count is None:
        # Calcular número de alertas activas
        count = StockAlert.objects.filter(status='active').count()
        
        # Guardar en caché
        cache.set(cache_key, count, CACHE_TIMEOUT_SHORT)
    
    return count

def invalidate_alert_cache():
    """
    Invalida la caché de alertas.
    """
    cache.delete('active_alerts_count')
