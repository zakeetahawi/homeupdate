"""
API Views for Products Search
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from accounts.models import Branch
from inventory.models import Product

from .models import Order

User = get_user_model()


@login_required
@require_http_methods(["GET"])
def products_search_api(request):
    """
    API endpoint للبحث عن المنتجات
    يستخدم في Select2 للويزارد
    يدعم البحث بالباركود
    """
    try:
        query = request.GET.get("q", "").strip()
        barcode = request.GET.get("barcode", "").strip()
        page = int(request.GET.get("page", 1))
        page_size = 20

        # البحث في المنتجات
        products = Product.objects.select_related("category")

        # البحث بالباركود له أولوية (باستخدام code)
        if barcode:
            products = products.filter(code=barcode)
        elif query:
            products = products.filter(
                Q(name__icontains=query)
                | Q(code__icontains=query)
                | Q(category__name__icontains=query)
            )

        # ترتيب النتائج
        products = products.order_by("name")

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        total_count = products.count()
        products_page = products[start:end]

        # تحضير النتائج
        results = []
        for product in products_page:
            results.append(
                {
                    "id": product.id,
                    "text": product.name,
                    "name": product.name,
                    "code": product.code if product.code else "",
                    "price": float(product.price) if product.price else 0.0,
                    "category": product.category.name if product.category else "",
                }
            )

        return JsonResponse(
            {"results": results, "has_more": end < total_count, "total": total_count}
        )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error in products_search_api: {e}")

        return JsonResponse(
            {"results": [], "has_more": False, "total": 0, "error": str(e)}, status=500
        )


@login_required
@require_http_methods(["GET", "POST"])
def check_invoice_number_api(request):
    """
    API endpoint للتحقق من تكرار رقم المرجع للعميل نفسه
    يُرجع تحذيراً إذا كان الرقم مستخدماً مسبقاً مع نفس نوع الطلب
    """
    import json

    try:
        # دعم GET و POST
        if request.method == "POST":
            try:
                data = json.loads(request.body)
                invoice_number = data.get("invoice_number", "").strip()
                customer_id = data.get("customer_id", "")
                order_type = data.get("order_type", "")
                current_order_id = data.get("current_order_id", "")
            except json.JSONDecodeError:
                invoice_number = request.POST.get("invoice_number", "").strip()
                customer_id = request.POST.get("customer_id", "")
                order_type = request.POST.get("order_type", "")
                current_order_id = request.POST.get("current_order_id", "")
        else:
            invoice_number = request.GET.get("invoice_number", "").strip()
            customer_id = request.GET.get("customer_id", "")
            order_type = request.GET.get("order_type", "")
            current_order_id = request.GET.get("current_order_id", "")

        if not invoice_number or not customer_id:
            return JsonResponse({"exists": False, "message": ""})

        # البحث عن طلبات بنفس رقم المرجع للعميل نفسه
        existing_orders = Order.objects.filter(customer_id=customer_id).filter(
            Q(invoice_number=invoice_number)
            | Q(invoice_number_2=invoice_number)
            | Q(invoice_number_3=invoice_number)
        )

        # استثناء الطلب الحالي في حالة التعديل
        if current_order_id:
            existing_orders = existing_orders.exclude(pk=current_order_id)

        # التحقق من وجود طلب بنفس النوع
        duplicate_found = False
        duplicate_order = None
        same_type = False
        existing_order_types = []

        # تحويل order_type إلى lowercase للمقارنة الصحيحة
        order_type_lower = order_type.lower().strip() if order_type else ""

        for existing_order in existing_orders:
            try:
                existing_types = existing_order.get_selected_types_list()
                existing_order_types = existing_types  # للتصحيح

                # تحويل الأنواع المخزنة إلى lowercase
                existing_types_lower = [t.lower().strip() for t in existing_types if t]

                if order_type_lower and order_type_lower in existing_types_lower:
                    duplicate_found = True
                    duplicate_order = existing_order
                    same_type = True
                    break
                elif not duplicate_found:
                    duplicate_found = True
                    duplicate_order = existing_order
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error checking order types: {e}")
                duplicate_found = True
                duplicate_order = existing_order

        if duplicate_found and duplicate_order:
            # الحصول على أسماء الأنواع للعرض
            type_names = {
                "inspection": "معاينة",
                "installation": "تركيب",
                "accessory": "إكسسوار",
                "tailoring": "تسليم",
                "products": "منتجات",
                "fabric": "أقمشة",
                "transport": "نقل",
            }

            existing_types_display = duplicate_order.get_selected_types_list()
            existing_types_arabic = [
                type_names.get(t, t) for t in existing_types_display
            ]
            current_type_arabic = type_names.get(order_type_lower, order_type)

            if same_type:
                return JsonResponse(
                    {
                        "exists": True,
                        "same_type": True,
                        "can_proceed": False,
                        "order_number": duplicate_order.order_number,
                        "existing_types": existing_types_display,
                        "current_type": order_type,
                        "message": f'⚠️ رقم المرجع "{invoice_number}" مستخدم مسبقاً لهذا العميل في طلب من نفس النوع ({current_type_arabic}) - رقم الطلب: {duplicate_order.order_number}. لا يمكن المتابعة.',
                        "title": "رقم المرجع مكرر - نفس النوع",
                    }
                )
            else:
                return JsonResponse(
                    {
                        "exists": True,
                        "same_type": False,
                        "can_proceed": True,
                        "order_number": duplicate_order.order_number,
                        "existing_types": existing_types_display,
                        "current_type": order_type,
                        "message": f'ℹ️ رقم المرجع "{invoice_number}" مستخدم لهذا العميل في طلب آخر ({", ".join(existing_types_arabic)}) - رقم الطلب: {duplicate_order.order_number}. يمكنك المتابعة لأن النوع مختلف ({current_type_arabic}).',
                        "title": "رقم المرجع موجود - نوع مختلف",
                    }
                )

        return JsonResponse({"exists": False, "message": ""})

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error in check_invoice_number_api: {e}")

        return JsonResponse(
            {"exists": False, "message": "", "error": str(e)}, status=500
        )


@login_required
@require_http_methods(["GET"])
def salespersons_by_branch_api(request):
    """
    API endpoint للحصول على البائعين حسب الفرع
    يستخدم في ويزارد إنشاء الطلب

    محسّن لتجنب أخطاء 500 وتحسين الأداء
    """
    from django.core.cache import cache

    from accounts.models import Salesperson

    try:
        branch_id = request.GET.get("branch", "").strip()

        # استخدام الكاش لتحسين الأداء
        cache_key = f'salespersons_branch:{branch_id or "all"}'
        cached_results = cache.get(cache_key)

        if cached_results:
            return JsonResponse(cached_results)

        # استخدام نموذج Salesperson بدلاً من User
        # هذا يحل مشكلة البائعين الذين ليس لديهم حساب مستخدم
        salespersons = Salesperson.objects.filter(is_active=True).select_related(
            "branch", "user"
        )

        # تصفية حسب الفرع إذا تم تحديده
        if branch_id:
            try:
                salespersons = salespersons.filter(branch_id=int(branch_id))
            except (ValueError, TypeError):
                pass

        # ترتيب النتائج
        salespersons = salespersons.order_by("name")

        # تحضير النتائج بطريقة آمنة
        results = []
        for sp in salespersons:
            try:
                # استخدام get_display_name للحصول على أفضل اسم
                name = (
                    sp.get_display_name()
                    if hasattr(sp, "get_display_name")
                    else sp.name
                )
                branch_name = sp.branch.name if sp.branch else ""

                results.append(
                    {
                        "id": sp.id,
                        "name": name,
                        "branch": branch_name,
                        "branch_id": sp.branch_id,
                    }
                )
            except Exception as item_error:
                # تسجيل الخطأ والاستمرار
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Error processing salesperson {sp.id}: {item_error}")
                continue

        response_data = {"results": results, "total": len(results)}

        # تخزين في الكاش لمدة 5 دقائق
        cache.set(cache_key, response_data, 300)

        return JsonResponse(response_data)

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error in salespersons_by_branch_api: {e}", exc_info=True)

        # إرجاع قائمة فارغة بدلاً من خطأ 500
        return JsonResponse(
            {"results": [], "total": 0, "error": "حدث خطأ في جلب البائعين"}
        )
