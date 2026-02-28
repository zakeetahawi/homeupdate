"""
تحسينات الأداء للويزارد والطلبات
Performance Optimizations for Wizard and Orders

هذا الملف يحتوي على الدوال المحسنة التي يجب استخدامها
بدلاً من الاستعلامات البطيئة في wizard_views.py و views.py
"""

import logging
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce

logger = logging.getLogger(__name__)


# =============================================================================
# 1. تحسينات استعلامات DraftOrder
# =============================================================================


def get_user_drafts_optimized(user, is_completed=False, limit=None):
    """
    جلب مسودات المستخدم بطريقة محسنة

    بدلاً من:
    DraftOrder.objects.filter(created_by=user, is_completed=False)

    استخدم:
    get_user_drafts_optimized(user, is_completed=False)
    """
    from orders.wizard_models import DraftOrder

    queryset = (
        DraftOrder.objects.select_related(
            "customer",
            "customer__branch",
            "branch",
            "salesperson",
            "salesperson__user",
            "related_inspection",
        )
        .filter(created_by=user, is_completed=is_completed)
        .order_by("-updated_at")
    )

    if limit:
        queryset = queryset[:limit]

    return queryset


def get_draft_with_relations(draft_id, user=None):
    """
    جلب مسودة مع جميع العلاقات المطلوبة

    بدلاً من:
    draft = DraftOrder.objects.get(pk=draft_id)

    استخدم:
    draft = get_draft_with_relations(draft_id, user)
    """
    from orders.wizard_models import DraftOrder

    queryset = DraftOrder.objects.select_related(
        "customer",
        "customer__branch",
        "customer__category",
        "branch",
        "salesperson",
        "salesperson__user",
        "related_inspection",
        "final_order",
    ).prefetch_related(
        "items", "items__product", "items__product__category", "invoice_images_new"
    )

    if user:
        queryset = queryset.filter(created_by=user)

    return queryset.filter(pk=draft_id).first()


def get_draft_items_with_usage(draft):
    """
    جلب عناصر المسودة مع حساب الكميات المستخدمة في استعلام واحد

    بدلاً من الحلقة التي تسبب N+1:
    for item in order_items:
        used_fabrics = CurtainFabric.objects.filter(...).aggregate(...)
        used_accessories = CurtainAccessory.objects.filter(...).aggregate(...)

    استخدم:
    items = get_draft_items_with_usage(draft)
    """
    from django.db.models import Value

    from orders.contract_models import CurtainAccessory, CurtainFabric
    from orders.wizard_models import DraftOrderItem

    # Subquery لحساب الأقمشة المستخدمة
    fabric_usage = (
        CurtainFabric.objects.filter(
            draft_order_item=OuterRef("pk"), curtain__draft_order=draft
        )
        .values("draft_order_item")
        .annotate(total=Sum("meters"))
        .values("total")[:1]
    )

    # Subquery لحساب الإكسسوارات المستخدمة
    accessory_usage = (
        CurtainAccessory.objects.filter(
            draft_order_item=OuterRef("pk"), curtain__draft_order=draft
        )
        .values("draft_order_item")
        .annotate(total=Sum("quantity"))
        .values("total")[:1]
    )

    # جلب العناصر مع الحسابات
    items = (
        draft.items.filter(item_type__in=["fabric", "product"])
        .select_related("product", "product__category")
        .annotate(
            used_fabrics=Coalesce(Subquery(fabric_usage), Value(Decimal("0"))),
            used_accessories=Coalesce(Subquery(accessory_usage), Value(Decimal("0"))),
        )
    )

    # تحويل إلى قائمة مع البيانات المطلوبة
    result = []
    for item in items:
        used = item.used_fabrics + item.used_accessories
        result.append(
            {
                "id": item.id,
                "name": item.product.name,
                "total_quantity": float(item.quantity),
                "used_quantity": float(used),
                "available_quantity": float(item.quantity - used),
                "product": item.product,
            }
        )

    return result


# =============================================================================
# 2. تحسينات استعلامات الستائر والعقود
# =============================================================================


def get_curtains_with_details(draft=None, order=None):
    """
    جلب الستائر مع جميع التفاصيل والعلاقات

    بدلاً من:
    curtains = ContractCurtain.objects.filter(draft_order=draft)

    استخدم:
    curtains = get_curtains_with_details(draft=draft)
    """
    from orders.contract_models import ContractCurtain

    queryset = ContractCurtain.objects.prefetch_related(
        "fabrics",
        "fabrics__draft_order_item",
        "fabrics__draft_order_item__product",
        "fabrics__order_item",
        "fabrics__order_item__product",
        "accessories",
        "accessories__draft_order_item",
        "accessories__draft_order_item__product",
        "accessories__order_item",
        "accessories__order_item__product",
    )

    if draft:
        queryset = queryset.filter(draft_order=draft)
    elif order:
        queryset = queryset.filter(order=order)

    return queryset.order_by("sequence")


# =============================================================================
# 3. تحسينات استعلامات الطلبات
# =============================================================================


def get_order_with_all_relations(order_id_or_number):
    """
    جلب طلب مع جميع العلاقات المطلوبة لصفحة التفاصيل

    بدلاً من استعلامات متعددة في order_detail:
    order = Order.objects.get(pk=pk)
    payments = order.payments.all()
    items = order.items.all()
    inspections = order.inspections.all()

    استخدم:
    order = get_order_with_all_relations(pk)
    """
    from orders.models import Order

    queryset = Order.objects.select_related(
        "customer",
        "customer__branch",
        "customer__category",
        "salesperson",
        "salesperson__user",
        "branch",
        "related_inspection",
        "created_by",
    ).prefetch_related(
        "items",
        "items__product",
        "items__product__category",
        "payments",
        "payments__created_by",
        "inspections",
        "inspections__inspector",
        "invoice_images",
        "contract_curtains",
        "contract_curtains__fabrics",
        "contract_curtains__accessories",
    )

    # التحقق من نوع المعرف
    if isinstance(order_id_or_number, int):
        return queryset.filter(pk=order_id_or_number).first()
    else:
        return queryset.filter(order_number=order_id_or_number).first()


def get_orders_list_optimized(user, filters=None, page_size=25):
    """
    جلب قائمة الطلبات بطريقة محسنة

    بدلاً من:
    orders = Order.objects.select_related('customer', 'salesperson').all()

    استخدم:
    orders = get_orders_list_optimized(user, filters)
    """
    from orders.models import Order
    from orders.permissions import get_user_orders_queryset

    # الحصول على الطلبات حسب صلاحيات المستخدم
    queryset = (
        get_user_orders_queryset(user)
        .select_related(
            "customer", "customer__branch", "salesperson", "salesperson__user", "branch"
        )
        .only(
            "id",
            "order_number",
            "order_date",
            "status",
            "order_status",
            "total_amount",
            "paid_amount",
            "created_at",
            "contract_number",
            "invoice_number",
            "selected_types",
            "customer__id",
            "customer__name",
            "customer__phone",
            "customer__code",
            "salesperson__id",
            "salesperson__name",
            "branch__id",
            "branch__name",
        )
    )

    if filters:
        if filters.get("search"):
            from django.db.models import Q

            search = filters["search"]
            queryset = queryset.filter(
                Q(order_number__icontains=search)
                | Q(customer__name__icontains=search)
                | Q(customer__phone__icontains=search)
                | Q(contract_number__icontains=search)
                | Q(invoice_number__icontains=search)
            )

        if filters.get("status"):
            queryset = queryset.filter(order_status=filters["status"])

        if filters.get("branch"):
            queryset = queryset.filter(branch_id=filters["branch"])

    return queryset.order_by("-created_at")


# =============================================================================
# 4. تحسينات Caching
# =============================================================================


def get_cached_system_settings():
    """
    جلب إعدادات النظام من الذاكرة المؤقتة

    بدلاً من:
    settings = SystemSettings.get_settings()

    استخدم:
    settings = get_cached_system_settings()
    """
    cache_key = "system_settings_v1"
    settings = cache.get(cache_key)

    if settings is None:
        from accounts.models import SystemSettings

        try:
            settings_obj = SystemSettings.get_settings()
            settings = {
                "currency": settings_obj.currency,
                "currency_symbol": settings_obj.currency_symbol,
                "max_draft_orders_per_user": settings_obj.max_draft_orders_per_user,
            }
            cache.set(cache_key, settings, 300)  # 5 دقائق
        except Exception as e:
            logger.warning(f"Error getting system settings: {e}")
            settings = {
                "currency": "EGP",
                "currency_symbol": "ج.م",
                "max_draft_orders_per_user": 5,
            }

    return settings


def get_cached_active_branches():
    """
    جلب الفروع النشطة من الذاكرة المؤقتة

    بدلاً من:
    branches = Branch.objects.filter(is_active=True)

    استخدم:
    branches = get_cached_active_branches()
    """
    cache_key = "active_branches_v1"
    branches = cache.get(cache_key)

    if branches is None:
        from accounts.models import Branch

        branches = list(
            Branch.objects.filter(is_active=True).values(
                "id", "name", "code", "is_main_branch"
            )
        )
        cache.set(cache_key, branches, 600)  # 10 دقائق

    return branches


def get_cached_active_salespersons(branch_id=None):
    """
    جلب البائعين النشطين من الذاكرة المؤقتة
    """
    cache_key = f'active_salespersons_{branch_id or "all"}_v1'
    salespersons = cache.get(cache_key)

    if salespersons is None:
        from accounts.models import Salesperson

        queryset = Salesperson.objects.filter(is_active=True).select_related(
            "user", "branch"
        )

        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        salespersons = list(
            queryset.values("id", "name", "employee_number", "branch_id", "user_id")
        )
        cache.set(cache_key, salespersons, 300)  # 5 دقائق

    return salespersons


def get_cached_wizard_options(field_type):
    """
    جلب خيارات الويزارد من الذاكرة المؤقتة
    """
    cache_key = f"wizard_options_{field_type}_v1"
    options = cache.get(cache_key)

    if options is None:
        from orders.wizard_customization_models import WizardFieldOption

        options = list(
            WizardFieldOption.get_active_options(field_type).values(
                "id", "field_type", "label", "value", "description", "order"
            )
        )
        cache.set(cache_key, options, 600)  # 10 دقائق

    return options


# =============================================================================
# 5. تحسينات العمليات الجماعية
# =============================================================================


def bulk_update_order_items(order, items_data):
    """
    تحديث عناصر الطلب بشكل جماعي بدلاً من حلقات

    بدلاً من:
    for item_data in items_data:
        item = OrderItem.objects.get(id=item_data['id'])
        item.quantity = item_data['quantity']
        item.save()

    استخدم:
    bulk_update_order_items(order, items_data)
    """
    from orders.models import OrderItem

    # جمع المعرفات
    item_ids = [d["id"] for d in items_data if d.get("id")]

    # جلب العناصر دفعة واحدة
    items = {item.id: item for item in OrderItem.objects.filter(id__in=item_ids)}

    # تحديث العناصر
    to_update = []
    for data in items_data:
        if data.get("id") and data["id"] in items:
            item = items[data["id"]]
            item.quantity = data.get("quantity", item.quantity)
            item.unit_price = data.get("unit_price", item.unit_price)
            item.discount_percentage = data.get(
                "discount_percentage", item.discount_percentage
            )
            to_update.append(item)

    # تحديث جماعي
    if to_update:
        OrderItem.objects.bulk_update(
            to_update, ["quantity", "unit_price", "discount_percentage"]
        )

    return len(to_update)


def bulk_create_draft_items(draft, products_data):
    """
    إنشاء عناصر المسودة بشكل جماعي
    """
    from decimal import Decimal

    from inventory.models import Product
    from orders.wizard_models import DraftOrderItem

    # جلب المنتجات دفعة واحدة
    product_ids = [d["product_id"] for d in products_data if d.get("product_id")]
    products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}

    # إنشاء العناصر
    items_to_create = []
    for data in products_data:
        product_id = data.get("product_id")
        if product_id and product_id in products:
            product = products[product_id]
            items_to_create.append(
                DraftOrderItem(
                    draft_order=draft,
                    product=product,
                    quantity=Decimal(str(data.get("quantity", 1))),
                    unit_price=Decimal(str(data.get("unit_price", product.price or 0))),
                    discount_percentage=Decimal(
                        str(data.get("discount_percentage", 0))
                    ),
                    item_type=data.get("item_type", "product"),
                    notes=data.get("notes", ""),
                )
            )

    # إنشاء جماعي
    if items_to_create:
        DraftOrderItem.objects.bulk_create(items_to_create)

    return len(items_to_create)


# =============================================================================
# 6. مساعدات الأداء
# =============================================================================


def invalidate_draft_cache(draft_id):
    """إبطال الذاكرة المؤقتة للمسودة"""
    cache.delete(f"draft_{draft_id}")
    cache.delete(f"draft_items_{draft_id}")
    cache.delete(f"draft_curtains_{draft_id}")


def invalidate_order_cache(order_id):
    """إبطال الذاكرة المؤقتة للطلب"""
    cache.delete(f"order_{order_id}")
    cache.delete(f"order_items_{order_id}")


def invalidate_user_cache(user_id):
    """إبطال الذاكرة المؤقتة للمستخدم"""
    cache.delete(f"user_drafts_{user_id}")
    cache.delete(f"user_permissions_{user_id}")


# =============================================================================
# 7. Debugging وقياس الأداء
# =============================================================================


class QueryCounter:
    """
    عداد للاستعلامات - للاستخدام في التطوير

    استخدام:
    with QueryCounter() as counter:
        # الكود الخاص بك
        pass
    print(f"Queries: {counter.count}")
    """

    def __init__(self):
        self.count = 0
        self.queries = []

    def __enter__(self):
        from django.db import connection

        self.initial_count = len(connection.queries)
        return self

    def __exit__(self, *args):
        from django.db import connection

        self.count = len(connection.queries) - self.initial_count
        self.queries = connection.queries[self.initial_count :]


def log_slow_query(query, duration, threshold=0.5):
    """تسجيل الاستعلامات البطيئة"""
    if duration > threshold:
        logger.warning(f"Slow query ({duration:.2f}s): {query[:200]}")


# =============================================================================
# استخدام هذه التحسينات
# =============================================================================
"""
لاستخدام هذه التحسينات، استورد الدوال المطلوبة في wizard_views.py و views.py:

from orders.performance_optimizations import (
    get_user_drafts_optimized,
    get_draft_with_relations,
    get_draft_items_with_usage,
    get_curtains_with_details,
    get_order_with_all_relations,
    get_orders_list_optimized,
    get_cached_system_settings,
    get_cached_active_branches,
    get_cached_active_salespersons,
    get_cached_wizard_options,
    bulk_update_order_items,
    bulk_create_draft_items,
)

ثم استبدل الاستعلامات البطيئة بالدوال المحسنة.
"""
