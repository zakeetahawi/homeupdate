from django.core.cache import cache
from django.db import models
from django.db.models import Case, F, IntegerField, Sum, When


class ProductQuerySet(models.QuerySet):
    def with_stock_level(self):
        """
        إضافة حساب مستوى المخزون الحالي للمنتجات
        """
        return self.annotate(
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

    def low_stock(self):
        """
        تصفية المنتجات ذات المخزون المنخفض
        """
        return self.with_stock_level().filter(
            current_stock_calc__gt=0, current_stock_calc__lte=F("minimum_stock")
        )

    def out_of_stock(self):
        """
        تصفية المنتجات التي نفدت من المخزون
        """
        return self.with_stock_level().filter(current_stock_calc__lte=0)

    def in_stock(self):
        """
        تصفية المنتجات المتوفرة في المخزون
        """
        return self.with_stock_level().filter(current_stock_calc__gt=0)

    def with_related(self):
        """
        تحميل البيانات المرتبطة مع المنتجات
        """
        return self.select_related("category").prefetch_related(
            "transactions__created_by"
        )


class ProductManager(models.Manager):
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)

    def with_stock_level(self):
        return self.get_queryset().with_stock_level()

    def low_stock(self):
        return self.get_queryset().low_stock()

    def out_of_stock(self):
        return self.get_queryset().out_of_stock()

    def in_stock(self):
        return self.get_queryset().in_stock()

    def with_related(self):
        return self.get_queryset().with_related()

    def get_cached(self, product_id):
        """
        الحصول على منتج من الذاكرة المؤقتة
        """
        cache_key = f"product_detail_{product_id}"
        product = cache.get(cache_key)

        if product is None:
            product = self.with_related().get(id=product_id)
            cache.set(cache_key, product, 3600)  # تخزين لمدة ساعة

        return product

    def get_category_stats(self, category_id):
        """
        الحصول على إحصائيات فئة معينة
        """
        cache_key = f"category_stats_{category_id}"
        stats = cache.get(cache_key)

        if stats is None:
            products = self.filter(category_id=category_id).with_stock_level()
            stats = {
                "total_products": products.count(),
                "low_stock_count": products.low_stock().count(),
                "out_of_stock_count": products.out_of_stock().count(),
                "total_value": products.aggregate(
                    total=Sum(F("current_stock_calc") * F("price"))
                )["total"]
                or 0,
            }
            cache.set(cache_key, stats, 1800)  # تخزين لمدة 30 دقيقة

        return stats
