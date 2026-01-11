"""
وظائف مساعدة لحساب المخزون بطريقة محسنة
"""

from django.core.cache import cache
from django.db.models import Case, F, IntegerField, Sum, When

from .models import Product


def get_cached_stock_level(product_id):
    """
    الحصول على مستوى المخزون الحالي للمنتج من الذاكرة المؤقتة أو حسابه إذا لم يكن موجوداً
    يستخدم running_balance من آخر حركة لكل مستودع (متوافق مع models.py)
    """
    cache_key = f"product_stock_{product_id}"
    stock_level = cache.get(cache_key)

    if stock_level is None:
        # حساب المخزون باستخدام running_balance من جميع المستودعات
        # هذه الطريقة متوافقة مع current_stock property في Product model
        from .models import StockTransaction, Warehouse

        total_stock = 0
        warehouses = Warehouse.objects.filter(is_active=True)

        for warehouse in warehouses:
            last_trans = (
                StockTransaction.objects.filter(
                    product_id=product_id, warehouse=warehouse
                )
                .order_by("-transaction_date", "-id")
                .first()
            )

            if last_trans and last_trans.running_balance:
                total_stock += float(last_trans.running_balance)

        stock_level = total_stock
        # تخزين في الذاكرة المؤقتة لمدة ساعة
        cache.set(cache_key, stock_level, 3600)

    return stock_level


def invalidate_product_cache(product_id):
    """
    إلغاء صلاحية الذاكرة المؤقتة للمنتج
    """
    # إلغاء صلاحية ذاكرة التخزين المؤقت لمستوى المخزون
    cache_key = f"product_stock_{product_id}"
    cache.delete(cache_key)

    # إلغاء صلاحية ذاكرة التخزين المؤقت لقائمة المنتجات
    cache.delete("product_list_all")

    # إلغاء صلاحية ذاكرة التخزين المؤقت للفئات
    product = Product.objects.get(id=product_id)
    if product and product.category:
        cache.delete(f"product_list_{product.category.id}")

    # إلغاء صلاحية ذاكرة التخزين المؤقت للوحة التحكم
    cache.delete("inventory_dashboard_stats")


def get_cached_product_list(category_id=None, include_stock=True):
    """
    الحصول على قائمة المنتجات من الذاكرة المؤقتة
    """
    cache_key = f'product_list_{category_id or "all"}'
    products = cache.get(cache_key)

    if products is None:
        # استعلام قاعدة البيانات إذا لم تكن البيانات في الذاكرة المؤقتة
        queryset = Product.objects.select_related("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if include_stock:
            queryset = queryset.annotate(
                stock_in=Sum(
                    Case(
                        When(
                            transactions__transaction_type="in",
                            then="transactions__quantity",
                        ),
                        default=0,
                        output_field=IntegerField(),
                    )
                ),
                stock_out=Sum(
                    Case(
                        When(
                            transactions__transaction_type="out",
                            then="transactions__quantity",
                        ),
                        default=0,
                        output_field=IntegerField(),
                    )
                ),
                current_stock_calc=F("stock_in") - F("stock_out"),
            )

        products = list(queryset)
        # تخزين في الذاكرة المؤقتة لمدة 30 دقيقة
        cache.set(cache_key, products, 1800)

    return products


def get_cached_dashboard_stats():
    """
    الحصول على إحصائيات لوحة التحكم من الذاكرة المؤقتة
    """
    cache_key = "inventory_dashboard_stats"
    stats = cache.get(cache_key)

    if stats is None:
        # حساب الإحصائيات إذا لم تكن في الذاكرة المؤقتة
        products = Product.objects.all().annotate(
            stock_in=Sum(
                Case(
                    When(
                        transactions__transaction_type="in",
                        then="transactions__quantity",
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
            stock_out=Sum(
                Case(
                    When(
                        transactions__transaction_type="out",
                        then="transactions__quantity",
                    ),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
            current_stock_calc=F("stock_in") - F("stock_out"),
        )

        stats = {
            "total_products": products.count(),
            "low_stock_count": products.filter(
                current_stock_calc__gt=0, current_stock_calc__lte=F("minimum_stock")
            ).count(),
            "out_of_stock_count": products.filter(current_stock_calc__lte=0).count(),
            "total_value": products.annotate(
                product_value=F("current_stock_calc") * F("price")
            ).aggregate(total_value=Sum("product_value"))["total_value"]
            or 0,
        }

        # تخزين في الذاكرة المؤقتة لمدة 15 دقيقة
        cache.set(cache_key, stats, 900)

    return stats
