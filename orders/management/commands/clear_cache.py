"""
أمر Django لتنظيف التخزين المؤقت للطلبات
"""

import logging

from django.core.cache import cache
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "تنظيف التخزين المؤقت للطلبات"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="مسح جميع البيانات المؤقتة",
        )
        parser.add_argument(
            "--orders",
            action="store_true",
            help="مسح بيانات الطلبات المؤقتة فقط",
        )
        parser.add_argument(
            "--products",
            action="store_true",
            help="مسح بيانات المنتجات المؤقتة فقط",
        )
        parser.add_argument(
            "--customers",
            action="store_true",
            help="مسح بيانات العملاء المؤقتة فقط",
        )
        parser.add_argument(
            "--stats",
            action="store_true",
            help="مسح الإحصائيات المؤقتة فقط",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🧹 بدء تنظيف التخزين المؤقت..."))

        try:
            from orders.cache import OrderCache

            if options["all"]:
                # مسح جميع البيانات المؤقتة
                OrderCache.clear_all_cache()
                self.stdout.write(self.style.SUCCESS("✅ تم مسح جميع البيانات المؤقتة"))

            elif options["orders"]:
                # مسح بيانات الطلبات فقط
                OrderCache.invalidate_order_stats_cache()
                self.stdout.write(
                    self.style.SUCCESS("✅ تم مسح بيانات الطلبات المؤقتة")
                )

            elif options["products"]:
                # مسح بيانات المنتجات فقط
                OrderCache.invalidate_product_search_cache()
                self.stdout.write(
                    self.style.SUCCESS("✅ تم مسح بيانات المنتجات المؤقتة")
                )

            elif options["customers"]:
                # مسح بيانات العملاء (يتطلب مسح جميع مفاتيح العملاء)
                try:
                    # محاولة مسح جميع مفاتيح العملاء
                    pattern = "orders:customer:*"
                    cache.delete_pattern(pattern)
                    self.stdout.write(
                        self.style.SUCCESS("✅ تم مسح بيانات العملاء المؤقتة")
                    )
                except AttributeError:
                    self.stdout.write(
                        self.style.WARNING(
                            "⚠️ لا يمكن مسح بيانات العملاء بالنمط - يرجى استخدام --all"
                        )
                    )

            elif options["stats"]:
                # مسح الإحصائيات فقط
                OrderCache.invalidate_order_stats_cache()
                self.stdout.write(self.style.SUCCESS("✅ تم مسح الإحصائيات المؤقتة"))

            else:
                # إذا لم يتم تحديد خيار، اعرض المساعدة
                self.stdout.write(
                    self.style.WARNING("⚠️ يرجى تحديد نوع البيانات المراد مسحها:")
                )
                self.stdout.write("  --all       : مسح جميع البيانات المؤقتة")
                self.stdout.write("  --orders    : مسح بيانات الطلبات فقط")
                self.stdout.write("  --products  : مسح بيانات المنتجات فقط")
                self.stdout.write("  --customers : مسح بيانات العملاء فقط")
                self.stdout.write("  --stats     : مسح الإحصائيات فقط")

            # عرض إحصائيات التخزين المؤقت
            self.show_cache_stats()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ خطأ في تنظيف التخزين المؤقت: {str(e)}")
            )

    def show_cache_stats(self):
        """عرض إحصائيات التخزين المؤقت"""
        try:
            self.stdout.write("\n📊 إحصائيات التخزين المؤقت:")

            # اختبار الاتصال
            cache.set("test_connection", True, 10)
            if cache.get("test_connection"):
                self.stdout.write("  ✅ الاتصال: متصل")
                cache.delete("test_connection")
            else:
                self.stdout.write("  ❌ الاتصال: غير متصل")

            # نوع التخزين المؤقت
            cache_backend = cache.__class__.__name__
            self.stdout.write(f"  🔧 النوع: {cache_backend}")

            # معلومات إضافية إذا كان Redis
            if "Redis" in cache_backend:
                try:
                    # محاولة الحصول على معلومات Redis
                    info = cache._cache.get_client().info()
                    memory_usage = info.get("used_memory_human", "غير معروف")
                    connected_clients = info.get("connected_clients", "غير معروف")

                    self.stdout.write(f"  💾 استخدام الذاكرة: {memory_usage}")
                    self.stdout.write(f"  👥 العملاء المتصلون: {connected_clients}")

                except Exception:
                    self.stdout.write("  ℹ️ لا يمكن الحصول على تفاصيل Redis")

        except Exception as e:
            self.stdout.write(f"  ⚠️ خطأ في عرض الإحصائيات: {str(e)}")


# دالة مساعدة لتشغيل الأمر برمجياً
def clear_cache_programmatically(cache_type="all"):
    """
    تنظيف التخزين المؤقت برمجياً

    Args:
        cache_type (str): نوع البيانات المراد مسحها
                         ('all', 'orders', 'products', 'customers', 'stats')

    Returns:
        bool: True إذا تم المسح بنجاح، False في حالة الخطأ
    """
    try:
        from orders.cache import OrderCache

        if cache_type == "all":
            OrderCache.clear_all_cache()
        elif cache_type == "orders":
            OrderCache.invalidate_order_stats_cache()
        elif cache_type == "products":
            OrderCache.invalidate_product_search_cache()
        elif cache_type == "customers":
            # مسح جميع مفاتيح العملاء
            try:
                pattern = "orders:customer:*"
                cache.delete_pattern(pattern)
            except AttributeError:
                # في حالة عدم دعم delete_pattern
                pass
        elif cache_type == "stats":
            OrderCache.invalidate_order_stats_cache()
        else:
            logger.warning(f"نوع التخزين المؤقت غير معروف: {cache_type}")
            return False

        logger.info(f"تم مسح التخزين المؤقت: {cache_type}")
        return True

    except Exception as e:
        logger.error(f"خطأ في مسح التخزين المؤقت برمجياً: {str(e)}")
        return False


# دالة للتحقق من صحة التخزين المؤقت
def test_cache_functionality():
    """
    اختبار وظائف التخزين المؤقت

    Returns:
        dict: نتائج الاختبار
    """
    results = {
        "connection": False,
        "read_write": False,
        "delete": False,
        "performance": None,
        "errors": [],
    }

    try:
        import time

        # اختبار الاتصال
        cache.set("test_connection", True, 10)
        if cache.get("test_connection"):
            results["connection"] = True
            cache.delete("test_connection")

        # اختبار القراءة والكتابة
        test_data = {"test": True, "timestamp": time.time()}
        cache.set("test_data", test_data, 60)
        retrieved_data = cache.get("test_data")

        if retrieved_data == test_data:
            results["read_write"] = True

        # اختبار الحذف
        cache.delete("test_data")
        if cache.get("test_data") is None:
            results["delete"] = True

        # اختبار الأداء
        start_time = time.time()
        for i in range(100):
            cache.set(f"perf_test_{i}", f"value_{i}", 60)

        for i in range(100):
            cache.get(f"perf_test_{i}")

        for i in range(100):
            cache.delete(f"perf_test_{i}")

        end_time = time.time()
        results["performance"] = round(
            (end_time - start_time) * 1000, 2
        )  # بالميلي ثانية

    except Exception as e:
        results["errors"].append(str(e))

    return results


# دالة لعرض تقرير التخزين المؤقت
def generate_cache_report():
    """
    إنشاء تقرير شامل عن حالة التخزين المؤقت

    Returns:
        dict: تقرير شامل
    """
    report = {
        "timestamp": timezone.now().isoformat(),
        "cache_backend": cache.__class__.__name__,
        "functionality_test": test_cache_functionality(),
        "cache_keys": [],
        "recommendations": [],
    }

    try:
        # محاولة الحصول على قائمة المفاتيح (إذا كان مدعوماً)
        if hasattr(cache, "keys"):
            report["cache_keys"] = list(cache.keys("orders:*"))[
                :10
            ]  # أول 10 مفاتيح فقط
    except:
        report["cache_keys"] = ["غير متاح"]

    # توصيات بناءً على النتائج
    if not report["functionality_test"]["connection"]:
        report["recommendations"].append("تحقق من إعدادات التخزين المؤقت")

    if (
        report["functionality_test"]["performance"]
        and report["functionality_test"]["performance"] > 1000
    ):
        report["recommendations"].append("الأداء بطيء - تحقق من إعدادات الشبكة")

    if not report["functionality_test"]["errors"]:
        report["recommendations"].append("التخزين المؤقت يعمل بشكل طبيعي")

    return report
