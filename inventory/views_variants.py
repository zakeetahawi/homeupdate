"""
Views لنظام المتغيرات والتسعير
"""

import json
import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from .forms_variants import (
    BaseProductForm,
    BulkPriceUpdateForm,
    ColorAttributeForm,
    MigrateProductsForm,
    ProductVariantForm,
    QuickVariantCreateForm,
    VariantStockTransferForm,
    VariantStockUpdateForm,
)
from .models import (
    BaseProduct,
    Category,
    ColorAttribute,
    PriceHistory,
    Product,
    ProductVariant,
    StockTransaction,
    VariantStock,
    Warehouse,
)
from .variant_services import PricingService, StockService, VariantService

# ==================== Base Products ====================


@login_required
def base_product_list(request):
    """قائمة المنتجات الأساسية"""
    search = request.GET.get("search", "")
    category_id = request.GET.get("category", "")
    status = request.GET.get("status", "")

    # حساب الإحصائيات الإجمالية (قبل التصفية)
    from django.db.models import Count, Sum

    total_base_products = BaseProduct.objects.count()
    total_variants = ProductVariant.objects.filter(is_active=True).count()
    active_base_products = BaseProduct.objects.filter(is_active=True).count()
    inactive_base_products = BaseProduct.objects.filter(is_active=False).count()

    # حساب إجمالي قيمة المخزون
    total_inventory_value = (
        BaseProduct.objects.aggregate(total=Sum("base_price"))["total"] or 0
    )

    queryset = BaseProduct.objects.select_related("category").prefetch_related(
        Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True))
    )

    # البحث
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(code__icontains=search)
        )

    # فلتر الفئة
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    # فلتر الحالة
    if status == "active":
        queryset = queryset.filter(is_active=True)
    elif status == "inactive":
        queryset = queryset.filter(is_active=False)

    queryset = queryset.order_by("-created_at")

    # عدد النتائج المفلترة
    filtered_count = queryset.count()

    # Pagination
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "base_products": page_obj,  # للقالب
        "page_obj": page_obj,  # للـ pagination
        "categories": Category.objects.all(),
        "all_warehouses": Warehouse.objects.filter(is_active=True),
        "search": search,
        "selected_category": category_id,
        "selected_status": status,
        "active_menu": "variants",
        # إحصائيات
        "total_base_products": total_base_products,
        "total_variants": total_variants,
        "active_base_products": active_base_products,
        "inactive_base_products": inactive_base_products,
        "total_inventory_value": total_inventory_value,
        "filtered_count": filtered_count,
        "all_warehouses": Warehouse.objects.all(),
    }

    return render(request, "inventory/variants/base_product_list.html", context)


@login_required
def base_product_detail(request, pk):
    """تفاصيل المنتج الأساسي مع متغيراته"""
    base_product = get_object_or_404(
        BaseProduct.objects.select_related("category", "created_by"), pk=pk
    )

    # المتغيرات مع المخزون
    variants = base_product.variants.filter(is_active=True).select_related("color")
    variants_data = []

    for variant in variants:
        stock_summary = VariantService.get_variant_stock_summary(variant)
        variants_data.append(
            {
                "variant": variant,
                "stock": stock_summary,
                "price_info": PricingService.get_variant_price(variant),
            }
        )

    # إحصائيات
    stats = {
        "total_variants": len(variants_data),
        "total_stock": sum(v["stock"]["total_stock"] for v in variants_data),
        "in_stock": len(
            [v for v in variants_data if v["stock"]["status"] == "in_stock"]
        ),
        "low_stock": len(
            [v for v in variants_data if v["stock"]["status"] == "low_stock"]
        ),
        "out_of_stock": len(
            [v for v in variants_data if v["stock"]["status"] == "out_of_stock"]
        ),
    }

    # سجل الأسعار الأخير
    recent_price_changes = (
        PriceHistory.objects.filter(variant__base_product=base_product)
        .select_related("variant", "changed_by")
        .order_by("-changed_at")[:10]
    )

    context = {
        "base_product": base_product,
        "variants": variants,  # للقالب
        "variants_data": variants_data,
        "variants_count": len(variants_data),
        "total_stock": sum(v["stock"]["total_stock"] for v in variants_data),
        "custom_prices_count": len(
            [v for v in variants_data if v["variant"].has_custom_price]
        ),
        "stats": stats,
        "price_history": recent_price_changes,
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/base_product_detail.html", context)


@login_required
def base_product_create(request):
    """إنشاء منتج أساسي جديد"""
    if request.method == "POST":
        form = BaseProductForm(request.POST)
        if form.is_valid():
            base_product = form.save(commit=False)
            base_product.created_by = request.user
            base_product.save()
            messages.success(request, _("تم إنشاء المنتج الأساسي بنجاح"))
            return redirect("inventory:base_product_detail", pk=base_product.pk)
    else:
        form = BaseProductForm()

    context = {
        "form": form,
        "title": _("إنشاء منتج أساسي"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/base_product_form.html", context)


@login_required
def base_product_update(request, pk):
    """تحديث منتج أساسي"""
    base_product = get_object_or_404(BaseProduct, pk=pk)
    old_base_price = base_product.base_price  # حفظ السعر القديم للمقارنة
    old_wholesale_price = base_product.wholesale_price

    if request.method == "POST":
        form = BaseProductForm(request.POST, instance=base_product)
        if form.is_valid():
            updated_product = form.save()

            # مزامنة السعر مع المنتجات القديمة إذا تغير السعر الأساسي أو سعر الجملة
            if (
                updated_product.base_price != old_base_price
                or updated_product.wholesale_price != old_wholesale_price
            ):
                synced_count = 0
                # تحديث كل المتغيرات التي ليس لها سعر مخصص
                variants = updated_product.variants.filter(
                    price_override__isnull=True, wholesale_price_override__isnull=True
                ).select_related("legacy_product")

                for variant in variants:
                    # تسجيل التغيير في سجل الأسعار
                    PriceHistory.objects.create(
                        variant=variant,
                        old_price=old_base_price,
                        new_price=updated_product.base_price,
                        change_type="base_update",
                        changed_by=request.user,
                        notes=_("تحديث السعر الأساسي للمنتج (قطاعي وجملة)"),
                    )

                    # مزامنة مع المنتج القديم
                    if variant.legacy_product:
                        variant.legacy_product.price = updated_product.base_price
                        variant.legacy_product.wholesale_price = (
                            updated_product.wholesale_price
                        )
                        variant.legacy_product.save(
                            update_fields=["price", "wholesale_price"]
                        )
                        synced_count += 1

                messages.success(
                    request,
                    _("تم تحديث المنتج الأساسي بنجاح (تم مزامنة {} منتج قديم)").format(
                        synced_count
                    ),
                )
            else:
                messages.success(request, _("تم تحديث المنتج الأساسي بنجاح"))

            return redirect("inventory:base_product_detail", pk=base_product.pk)
    else:
        form = BaseProductForm(instance=base_product)

    context = {
        "form": form,
        "base_product": base_product,
        "title": _("تحديث منتج أساسي"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/base_product_form.html", context)


@login_required
@require_POST
def base_product_delete(request, pk):
    """حذف منتج أساسي"""
    base_product = get_object_or_404(BaseProduct, pk=pk)

    # التحقق من عدم وجود متغيرات مرتبطة
    if base_product.variants.exists():
        messages.error(request, _("لا يمكن حذف المنتج لوجود متغيرات مرتبطة"))
        return redirect("inventory:base_product_detail", pk=pk)

    base_product.delete()
    messages.success(request, _("تم حذف المنتج الأساسي بنجاح"))
    return redirect("inventory:base_product_list")


# ==================== Product Variants ====================


@login_required
def variant_create(request, base_product_id):
    """إنشاء متغير جديد"""
    base_product = get_object_or_404(BaseProduct, pk=base_product_id)

    if request.method == "POST":
        form = ProductVariantForm(request.POST, base_product=base_product)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.base_product = base_product
            variant.save()
            messages.success(request, _("تم إنشاء المتغير بنجاح"))
            return redirect("inventory:base_product_detail", pk=base_product.pk)
    else:
        form = ProductVariantForm(base_product=base_product)

    context = {
        "form": form,
        "base_product": base_product,
        "title": _("إنشاء متغير جديد"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/variant_form.html", context)


@login_required
def variant_update(request, pk):
    """تحديث متغير"""
    variant = get_object_or_404(
        ProductVariant.objects.select_related("base_product"), pk=pk
    )

    if request.method == "POST":
        form = ProductVariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث المتغير بنجاح"))
            return redirect("inventory:base_product_detail", pk=variant.base_product.pk)
    else:
        form = ProductVariantForm(instance=variant)

    context = {
        "form": form,
        "variant": variant,
        "base_product": variant.base_product,
        "title": _("تحديث متغير"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/variant_form.html", context)


@login_required
def variant_detail(request, pk):
    """تفاصيل المتغير"""
    variant = get_object_or_404(
        ProductVariant.objects.select_related("base_product", "color"), pk=pk
    )

    stock_summary = VariantService.get_variant_stock_summary(variant)
    price_info = PricingService.get_variant_price(variant, include_history=True)

    context = {
        "variant": variant,
        "stock_summary": stock_summary,
        "price_info": price_info,
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/variant_detail.html", context)


@login_required
@require_POST
def variant_delete(request, pk):
    """حذف متغير"""
    variant = get_object_or_404(ProductVariant, pk=pk)
    base_product_pk = variant.base_product.pk

    # التحقق من عدم وجود مخزون
    if variant.current_stock > 0:
        messages.error(request, _("لا يمكن حذف المتغير لوجود مخزون"))
        return redirect("inventory:base_product_detail", pk=base_product_pk)

    variant.delete()
    messages.success(request, _("تم حذف المتغير بنجاح"))
    return redirect("inventory:base_product_detail", pk=base_product_pk)


@login_required
def quick_variants_create(request, base_product_id):
    """إنشاء متغيرات متعددة بسرعة"""
    base_product = get_object_or_404(BaseProduct, pk=base_product_id)

    if request.method == "POST":
        form = QuickVariantCreateForm(request.POST)
        if form.is_valid():
            codes = form.get_variant_codes_list()
            initial_stock = form.cleaned_data.get("initial_stock") or 0
            warehouse = form.cleaned_data.get("warehouse")

            created_count = 0
            for code in codes:
                variant, created = VariantService.get_or_create_variant(
                    base_product, code
                )
                if created:
                    created_count += 1

                    # إضافة مخزون ابتدائي
                    if initial_stock > 0 and warehouse:
                        StockService.update_variant_stock(
                            variant,
                            warehouse,
                            initial_stock,
                            transaction_type="in",
                            reason="other",
                            user=request.user,
                            notes="مخزون ابتدائي",
                        )

            messages.success(request, _("تم إنشاء {} متغير جديد").format(created_count))
            return redirect("inventory:base_product_detail", pk=base_product.pk)
    else:
        form = QuickVariantCreateForm()

    context = {
        "form": form,
        "base_product": base_product,
        "title": _("إنشاء متغيرات متعددة"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/quick_variants_create.html", context)


# ==================== Pricing ====================


@login_required
def bulk_price_update(request, base_product_id):
    """تحديث الأسعار بالجملة"""
    base_product = get_object_or_404(BaseProduct, pk=base_product_id)

    if request.method == "POST":
        update_type = request.POST.get("update_type", "percentage")
        value_str = request.POST.get("value", "0")
        apply_to_all = request.POST.get("apply_to_all") == "on"
        notes = request.POST.get("notes", "")

        try:
            value = float(value_str) if value_str else 0
        except (ValueError, TypeError):
            value = 0

        # تحديد المتغيرات
        variant_ids = None
        if not apply_to_all:
            variant_ids = request.POST.getlist("variant_ids")
            if variant_ids:
                variant_ids = [int(i) for i in variant_ids if i.strip()]

        result = PricingService.bulk_update_prices(
            base_product,
            update_type,
            value,
            variant_ids=variant_ids,
            user=request.user,
            notes=notes,
            sync_legacy=True,  # مزامنة تلقائية مع المنتجات القديمة
        )

        # رسالة نجاح محسنة
        sync_msg = ""
        if result.get("synced", 0) > 0:
            sync_msg = _(" (تم مزامنة {} منتج قديم)").format(result["synced"])

        messages.success(
            request, _("تم تحديث {} سعر بنجاح{}").format(result["updated"], sync_msg)
        )
        return redirect("inventory:base_product_detail", pk=base_product.pk)

    # المتغيرات للعرض
    variants = base_product.variants.filter(is_active=True).select_related("color")

    context = {
        "base_product": base_product,
        "variants": variants,
        "title": _("تحديث الأسعار بالجملة"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/bulk_price_update.html", context)


# ==================== Global Bulk Pricing ====================


@login_required
@permission_required("inventory.bulk_price_update", raise_exception=True)
def global_bulk_price_update(request):
    """
    تحديث الأسعار الجماعي العالمي - يشمل جميع المنتجات الأساسية
    مع إمكانية التصفية حسب المستودع ونوع السعر والعملية
    """
    warehouses = Warehouse.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        action = request.POST.get("action", "apply")

        # --- Parse form inputs ---
        all_warehouses_flag = request.POST.get("all_warehouses") == "on"
        warehouse_ids = request.POST.getlist("warehouse_ids")
        price_type = request.POST.get("price_type", "retail")   # retail | wholesale
        operation_type = request.POST.get("operation_type", "percentage")  # percentage | fixed
        direction = request.POST.get("direction", "increase")    # increase | decrease
        notes = request.POST.get("notes", "")

        try:
            value = Decimal(request.POST.get("value", "0").replace(",", "."))
        except (InvalidOperation, TypeError):
            value = Decimal("0")

        # --- Identify affected base products by warehouse filter ---
        # نجلب من VariantStock (الجديد) + StockTransaction (القديم) لتغطية جميع المنتجات
        if all_warehouses_flag or not warehouse_ids:
            wh_filter = {}
        else:
            wh_filter = {"warehouse_id__in": warehouse_ids}

        # المصدر 1: VariantStock (النظام الجديد)
        vs_variant_ids = set(
            VariantStock.objects.filter(
                current_quantity__gt=0, **wh_filter
            ).values_list("variant_id", flat=True)
        )

        # المصدر 2: StockTransaction (النظام القديم) - آخر running_balance > 0
        from django.db.models import Max
        latest_txn_ids = (
            StockTransaction.objects.filter(**wh_filter)
            .values("product_id", "warehouse_id")
            .annotate(last_id=Max("id"))
            .values_list("last_id", flat=True)
        )
        legacy_product_ids = set(
            StockTransaction.objects.filter(
                id__in=latest_txn_ids,
                running_balance__gt=0,
            ).values_list("product_id", flat=True)
        )
        legacy_variant_ids = set(
            ProductVariant.objects.filter(
                legacy_product_id__in=legacy_product_ids
            ).values_list("id", flat=True)
        )

        # دمج المصدرين
        all_variant_ids = vs_variant_ids | legacy_variant_ids

        affected_bp_ids = (
            ProductVariant.objects.filter(id__in=all_variant_ids)
            .values_list("base_product_id", flat=True)
            .distinct()
        )

        base_products = BaseProduct.objects.filter(
            id__in=affected_bp_ids, is_active=True
        ).select_related("category").order_by("name")

        # --- فلتر إضافي لسعر الجملة: فقط المنتجات التي لها سعر جملة حقيقي (> 0 وأقل من القطاعي) ---
        if price_type == "wholesale":
            base_products = base_products.filter(
                wholesale_price__gt=0,
                wholesale_price__lt=F("base_price"),
            )

        # --- Helper: compute new price ---
        def compute_new_price(old_price):
            # معالجة None: اعتبره 0
            if old_price is None:
                old_price = Decimal("0")
            old_price = Decimal(str(old_price))
            if operation_type == "percentage":
                change = (old_price * value / Decimal("100")).quantize(Decimal("0.01"))
            else:
                change = value.quantize(Decimal("0.01"))
            if direction == "increase":
                return max(Decimal("0"), old_price + change)
            else:
                return max(Decimal("0"), old_price - change)

        # ---- PREVIEW mode (AJAX) ----
        if action == "preview":
            preview_rows = []
            for bp in base_products:
                if price_type == "retail":
                    old_price = bp.base_price or Decimal("0")
                else:
                    # سعر الجملة: استخدم سعر الأساس كبديل إذا لم يكن محدداً
                    old_price = bp.wholesale_price if bp.wholesale_price is not None else bp.base_price
                new_price = compute_new_price(old_price)
                preview_rows.append(
                    {
                        "id": bp.id,
                        "name": bp.name,
                        "code": bp.code,
                        "category": bp.category.name if bp.category else "—",
                        "old_price": str(old_price),
                        "new_price": str(new_price.quantize(Decimal("0.01"))),
                    }
                )
            return JsonResponse(
                {"success": True, "count": len(preview_rows), "data": preview_rows}
            )

        # ---- APPLY mode ----
        updated_count = 0
        errors = []
        auto_notes = (
            notes
            or f"تحديث جماعي عالمي — {get_price_type_display(price_type)} — {get_direction_display(direction)} {value} ({get_operation_type_display(operation_type)})"
        )

        with transaction.atomic():
            # --- Pre-fetch variants بدلاً من N استعلام لكل منتج ---
            if price_type == "retail":
                variants_prefetch_qs = ProductVariant.objects.filter(
                    is_active=True, price_override__isnull=False
                )
                bp_update_field = "base_price"
                variant_update_field = "price_override"
            else:
                variants_prefetch_qs = ProductVariant.objects.filter(
                    is_active=True, wholesale_price_override__isnull=False
                )
                bp_update_field = "wholesale_price"
                variant_update_field = "wholesale_price_override"

            base_products = base_products.prefetch_related(
                Prefetch("variants", queryset=variants_prefetch_qs, to_attr="_override_variants")
            )

            now = timezone.now()
            bps_to_update = []
            variants_to_update = []
            history_list = []

            for bp in base_products:
                try:
                    bp_old = getattr(bp, bp_update_field)
                    bp_new = compute_new_price(bp_old)
                    setattr(bp, bp_update_field, bp_new)
                    bp.updated_at = now
                    bps_to_update.append(bp)

                    for variant in bp._override_variants:
                        v_old = getattr(variant, variant_update_field)
                        v_new = compute_new_price(v_old)
                        setattr(variant, variant_update_field, v_new)
                        variant.updated_at = now
                        variants_to_update.append(variant)
                        history_list.append(
                            PriceHistory(
                                variant=variant,
                                old_price=v_old,
                                new_price=v_new,
                                change_type="bulk",
                                change_value=value,
                                changed_by=request.user,
                                notes=auto_notes,
                            )
                        )
                    updated_count += 1
                except Exception as exc:
                    errors.append(f"{bp.name}: {exc}")

            # --- دفعة واحدة لكل عملية بدلاً من آلاف الاستعلامات ---
            if bps_to_update:
                BaseProduct.objects.bulk_update(
                    bps_to_update, [bp_update_field, "updated_at"], batch_size=500
                )
            if variants_to_update:
                ProductVariant.objects.bulk_update(
                    variants_to_update, [variant_update_field, "updated_at"], batch_size=500
                )
            if history_list:
                PriceHistory.objects.bulk_create(history_list, batch_size=500)

            # مزامنة الأسعار مع المنتجات القديمة (bulk_update لا يُطلق الإشارات)
            synced_legacy = 0
            for bp in bps_to_update:
                bp_variants = bp.variants.filter(
                    is_active=True,
                    legacy_product__isnull=False,
                ).select_related("legacy_product")
                for variant in bp_variants:
                    try:
                        PricingService._sync_legacy_product_price(variant)
                        synced_legacy += 1
                    except Exception:
                        pass
            if synced_legacy:
                logger.info(f"✅ تم مزامنة {synced_legacy} منتج قديم بعد التحديث الجماعي العالمي")

        if errors:
            messages.warning(
                request,
                f"تم تحديث {updated_count} منتج. أخطاء في {len(errors)} منتج.",
            )
        else:
            op_label = get_operation_type_display(operation_type)
            dir_label = get_direction_display(direction)
            pt_label = get_price_type_display(price_type)
            messages.success(
                request,
                f"✓ تم تحديث أسعار {updated_count} منتج بنجاح — {pt_label} | {dir_label} {value} ({op_label})",
            )
        return redirect("inventory:base_product_list")

    context = {
        "warehouses": warehouses,
        "title": "تحديث الأسعار الجماعي العالمي",
        "active_menu": "variants",
    }
    return render(
        request, "inventory/variants/global_bulk_price_update.html", context
    )


# --- Helper label functions ---
def get_price_type_display(code):
    return {"retail": "قطاعي", "wholesale": "جملة"}.get(code, code)


def get_direction_display(code):
    return {"increase": "زيادة", "decrease": "تخفيض"}.get(code, code)


def get_operation_type_display(code):
    return {"percentage": "نسبة مئوية", "fixed": "قيمة ثابتة"}.get(code, code)


@login_required
@require_POST
def update_variant_price(request, pk):
    """تحديث سعر متغير واحد (AJAX)"""
    variant = get_object_or_404(ProductVariant, pk=pk)

    try:
        data = json.loads(request.body)
        new_price = data.get("price")
        notes = data.get("notes", "")

        if new_price is None:
            return JsonResponse({"success": False, "error": _("السعر مطلوب")})

        result = PricingService.update_variant_price(
            variant, new_price, user=request.user, notes=notes
        )

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@require_POST
def reset_variant_price(request, pk):
    """إعادة سعر المتغير للأساسي (AJAX)"""
    variant = get_object_or_404(ProductVariant, pk=pk)

    try:
        result = PricingService.reset_variant_price(variant, user=request.user)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# ==================== Stock Management ====================


@login_required
def variant_stock_update(request, pk):
    """تحديث مخزون متغير"""
    variant = get_object_or_404(
        ProductVariant.objects.select_related("base_product"), pk=pk
    )

    if request.method == "POST":
        form = VariantStockUpdateForm(request.POST)
        if form.is_valid():
            warehouse = form.cleaned_data["warehouse"]
            transaction_type = form.cleaned_data["transaction_type"]
            quantity = form.cleaned_data["quantity"]
            reason = form.cleaned_data["reason"]
            notes = form.cleaned_data.get("notes", "")

            # تحديد إشارة الكمية
            if transaction_type == "out":
                quantity = -quantity

            try:
                result = StockService.update_variant_stock(
                    variant,
                    warehouse,
                    quantity,
                    transaction_type=transaction_type,
                    reason=reason,
                    user=request.user,
                    notes=notes,
                )
                messages.success(request, _("تم تحديث المخزون بنجاح"))
            except ValueError as e:
                messages.error(request, str(e))

            return redirect("inventory:variant_detail", pk=variant.pk)
    else:
        form = VariantStockUpdateForm()

    # المخزون الحالي
    stock_by_warehouse = variant.get_stock_by_warehouse()

    context = {
        "form": form,
        "variant": variant,
        "stock_by_warehouse": stock_by_warehouse,
        "title": _("تحديث المخزون"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/variant_stock_update.html", context)


@login_required
def variant_stock_transfer(request, pk):
    """نقل مخزون متغير"""
    variant = get_object_or_404(
        ProductVariant.objects.select_related("base_product"), pk=pk
    )

    if request.method == "POST":
        form = VariantStockTransferForm(request.POST)
        if form.is_valid():
            from_warehouse = form.cleaned_data["from_warehouse"]
            to_warehouse = form.cleaned_data["to_warehouse"]
            quantity = form.cleaned_data["quantity"]
            notes = form.cleaned_data.get("notes", "")

            try:
                result = StockService.transfer_variant_stock(
                    variant,
                    from_warehouse,
                    to_warehouse,
                    quantity,
                    user=request.user,
                    notes=notes,
                )
                messages.success(request, _("تم نقل المخزون بنجاح"))
            except ValueError as e:
                messages.error(request, str(e))

            return redirect("inventory:variant_detail", pk=variant.pk)
    else:
        form = VariantStockTransferForm()

    stock_by_warehouse = variant.get_stock_by_warehouse()

    context = {
        "form": form,
        "variant": variant,
        "stock_by_warehouse": stock_by_warehouse,
        "title": _("نقل المخزون"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/variant_stock_transfer.html", context)


# ==================== Colors ====================


@login_required
def color_list(request):
    """قائمة الألوان"""
    colors = ColorAttribute.objects.annotate(variants_count=Count("variants")).order_by(
        "display_order", "name"
    )

    context = {
        "colors": colors,
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/color_list.html", context)


@login_required
def color_create(request):
    """إنشاء لون جديد"""
    if request.method == "POST":
        form = ColorAttributeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم إنشاء اللون بنجاح"))
            return redirect("inventory:color_list")
    else:
        form = ColorAttributeForm()

    context = {
        "form": form,
        "title": _("إنشاء لون جديد"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/color_form.html", context)


@login_required
def color_update(request, pk):
    """تحديث لون"""
    color = get_object_or_404(ColorAttribute, pk=pk)

    if request.method == "POST":
        form = ColorAttributeForm(request.POST, instance=color)
        if form.is_valid():
            form.save()
            messages.success(request, _("تم تحديث اللون بنجاح"))
            return redirect("inventory:color_list")
    else:
        form = ColorAttributeForm(instance=color)

    context = {
        "form": form,
        "color": color,
        "title": _("تحديث لون"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/color_form.html", context)


@login_required
@require_POST
def color_delete(request, pk):
    """حذف لون"""
    color = get_object_or_404(ColorAttribute, pk=pk)

    # التحقق من عدم وجود متغيرات مرتبطة
    if color.variants.exists():
        messages.error(
            request,
            _("لا يمكن حذف هذا اللون لأنه مرتبط بـ {} متغير").format(
                color.variants.count()
            ),
        )
        return redirect("inventory:color_list")

    color_name = color.name
    color.delete()

    messages.success(request, _('تم حذف اللون "{}" بنجاح').format(color_name))
    return redirect("inventory:color_list")


# ==================== Migration ====================


@login_required
def migrate_products(request):
    """ترحيل المنتجات القديمة - يتم التوجيه للنظام التفاعلي الجديد"""
    # توجيه تلقائي للنظام التفاعلي الجديد (3 مراحل)
    return redirect("inventory:migrate_phase1")

    # الكود القديم محفوظ للرجوع إليه إذا لزم الأمر
    preview_results = None
    migration_results = None

    # إحصائيات
    total_products = Product.objects.count()
    linked_products = ProductVariant.objects.filter(
        legacy_product__isnull=False
    ).count()
    unlinked = total_products - linked_products

    # حساب المنتجات القابلة للتحليل (التي تحتوي على /)
    parseable = (
        Product.objects.filter(code__contains="/")
        .exclude(
            id__in=ProductVariant.objects.filter(
                legacy_product__isnull=False
            ).values_list("legacy_product_id", flat=True)
        )
        .count()
    )

    if request.method == "POST":
        form = MigrateProductsForm(request.POST)
        action = request.POST.get("action", "preview")

        if action == "preview":
            # معاينة المنتجات
            preview_results = []
            unlinked_products = Product.objects.exclude(
                id__in=ProductVariant.objects.filter(
                    legacy_product__isnull=False
                ).values_list("legacy_product_id", flat=True)
            )[
                :50
            ]  # أول 50 منتج للمعاينة

            for product in unlinked_products:
                # تحليل اسم المنتج (وليس الكود)
                base_name, variant_code = VariantService.parse_product_code(
                    product.name
                )
                preview_results.append(
                    {
                        "original_code": product.code,
                        "name": product.name,
                        "base_code": base_name if base_name else product.name,
                        "variant_code": variant_code if variant_code else "DEFAULT",
                        "can_migrate": True,
                        "reason": "",
                    }
                )

        elif action == "migrate" and form.is_valid():
            dry_run = form.cleaned_data.get("dry_run", False)

            stats = VariantService.migrate_all_products(dry_run=dry_run)

            if dry_run:
                messages.info(
                    request, _("تجربة: سيتم ترحيل {} منتج").format(stats["total"])
                )
            else:
                migration_results = {
                    "success_count": stats["migrated"],
                    "error_count": len(stats["errors"]),
                    "errors": stats.get("errors", []),  # قائمة الأخطاء مع التفاصيل
                    "skipped": stats.get("skipped", 0),
                }

                if stats["migrated"] > 0:
                    messages.success(
                        request, _("تم ترحيل {} منتج بنجاح").format(stats["migrated"])
                    )

                if len(stats["errors"]) > 0:
                    messages.warning(
                        request,
                        _("فشل ترحيل {} منتج - راجع الأخطاء أدناه").format(
                            len(stats["errors"])
                        ),
                    )

                # تحديث الإحصائيات
                linked_products = ProductVariant.objects.filter(
                    legacy_product__isnull=False
                ).count()
                unlinked = total_products - linked_products
    else:
        form = MigrateProductsForm()

    # إحصائيات للقالب
    stats = {
        "total_products": total_products,
        "migrated": linked_products,
        "pending": unlinked,
        "parseable": parseable,
    }

    context = {
        "form": form,
        "stats": stats,
        "preview_results": preview_results,
        "migration_results": migration_results,
        "title": _("ترحيل المنتجات"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/migrate_products.html", context)


# ==================== Interactive Migration (3 Phases) ====================


@login_required
def migrate_phase1(request):
    """المرحلة 1: ترحيل المنتجات فقط"""
    if request.method == "POST":
        stats = VariantService.phase1_migrate_products()

        # حفظ الإحصائيات في session للعرض
        request.session["migration_completed_stats"] = {
            "total": stats["total"],
            "migrated": stats["migrated"],
            "skipped": stats["skipped"],
            "errors": len(stats["errors"]),
        }

        messages.success(
            request, f"✅ اكتمل الترحيل بنجاح: تم ترحيل {stats['migrated']} منتج"
        )

        # إعادة التوجيه لنفس الصفحة لعرض النتائج
        return redirect("inventory:migrate_phase1")

    # GET request - show confirmation
    total_products = Product.objects.count()
    linked_products = ProductVariant.objects.filter(
        legacy_product__isnull=False
    ).count()
    pending = total_products - linked_products

    # الحصول على نتائج الترحيل المكتمل إن وجدت
    completed_stats = request.session.pop("migration_completed_stats", None)

    context = {
        "pending_count": pending,
        "migrated_count": linked_products,
        "total_count": total_products,
        "completed_stats": completed_stats,
        "title": _("ترحيل المنتجات"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/migrate_phase1.html", context)


@login_required
def migrate_phase2_confirm(request):
    """صفحة تأكيد المرحلة 2"""
    phase1_stats = request.session.get("migration_phase1_stats")

    if not phase1_stats:
        messages.error(request, "يجب تنفيذ المرحلة 1 أولاً")
        return redirect("inventory:migrate_phase1")

    context = {
        "phase1_stats": phase1_stats,
        "title": _("المرحلة 2: توليد QR"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/migrate_phase2_confirm.html", context)


@login_required
def migrate_phase2(request):
    """المرحلة 2: توليد QR"""
    if request.method != "POST":
        return redirect("inventory:migrate_phase2_confirm")

    base_product_ids = request.session.get("migration_base_product_ids", [])

    if not base_product_ids:
        messages.error(request, "لا توجد منتجات لتوليد QR لها")
        return redirect("inventory:migrate_products")

    stats = VariantService.phase2_generate_qr(base_product_ids)

    request.session["migration_phase2_stats"] = {
        "total": stats["total"],
        "generated": stats["generated"],
        "failed": stats["failed"],
    }

    messages.success(request, f"✅ المرحلة 2 اكتملت: تم توليد {stats['generated']} QR")

    return redirect("inventory:migrate_phase3_confirm")


@login_required
def migrate_phase3_confirm(request):
    """صفحة تأكيد المرحلة 3"""
    phase1_stats = request.session.get("migration_phase1_stats")
    phase2_stats = request.session.get("migration_phase2_stats")

    if not phase1_stats or not phase2_stats:
        messages.error(request, "يجب تنفيذ المراحل السابقة أولاً")
        return redirect("inventory:migrate_products")

    context = {
        "phase1_stats": phase1_stats,
        "phase2_stats": phase2_stats,
        "title": _("المرحلة 3: مزامنة Cloudflare"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/migrate_phase3_confirm.html", context)


@login_required
def migrate_phase3(request):
    """المرحلة 3: مزامنة Cloudflare"""
    if request.method != "POST":
        return redirect("inventory:migrate_phase3_confirm")

    base_product_ids = request.session.get("migration_base_product_ids", [])

    if not base_product_ids:
        messages.error(request, "لا توجد منتجات للمزامنة")
        return redirect("inventory:migrate_products")

    stats = VariantService.phase3_sync_cloudflare(base_product_ids)

    # جمع كل الإحصائيات
    all_stats = {
        "phase1": request.session.get("migration_phase1_stats"),
        "phase2": request.session.get("migration_phase2_stats"),
        "phase3": {
            "total": stats["total"],
            "synced": stats["synced"],
            "failed": stats["failed"],
            "skipped": stats["skipped"],
        },
    }

    # تنظيف session
    for key in [
        "migration_base_product_ids",
        "migration_phase1_stats",
        "migration_phase2_stats",
    ]:
        request.session.pop(key, None)

    messages.success(
        request, f"🎉 اكتملت جميع المراحل! تم مزامنة {stats['synced']} منتج"
    )

    context = {
        "all_stats": all_stats,
        "title": _("نتائج الترحيل"),
        "active_menu": "variants",
    }

    return render(request, "inventory/variants/migrate_complete.html", context)


# ==================== API Endpoints ====================


@login_required
@require_GET
def api_base_product_variants(request, pk):
    """API: الحصول على متغيرات منتج أساسي"""
    base_product = get_object_or_404(BaseProduct, pk=pk)

    variants_data = base_product.get_variants_summary()

    return JsonResponse(
        {
            "success": True,
            "base_product": {
                "id": base_product.id,
                "code": base_product.code,
                "name": base_product.name,
                "base_price": float(base_product.base_price),
            },
            "variants": variants_data,
        }
    )


@login_required
@require_GET
def api_variant_stock(request, pk):
    """API: الحصول على مخزون متغير"""
    variant = get_object_or_404(ProductVariant, pk=pk)

    stock_summary = VariantService.get_variant_stock_summary(variant)

    return JsonResponse(
        {
            "success": True,
            "variant": {
                "id": variant.id,
                "code": variant.full_code,
            },
            "stock": stock_summary,
        }
    )


@login_required
@require_GET
def api_search_variants(request):
    """API: البحث في المتغيرات"""
    query = request.GET.get("q", "")
    limit = int(request.GET.get("limit", 20))

    if len(query) < 2:
        return JsonResponse({"results": []})

    variants = ProductVariant.objects.filter(
        Q(variant_code__icontains=query)
        | Q(base_product__code__icontains=query)
        | Q(base_product__name__icontains=query)
        | Q(barcode__icontains=query)
    ).select_related("base_product", "color")[:limit]

    results = []
    for v in variants:
        results.append(
            {
                "id": v.id,
                "code": v.full_code,
                "name": f"{v.base_product.name} - {v.variant_code}",
                "color": v.color.name if v.color else v.color_code,
                "price": float(v.effective_price),
                "stock": v.current_stock,
            }
        )

    return JsonResponse({"results": results})


@login_required
def product_label_card(request, pk):
    """عرض بطاقة صنف قابلة للطباعة (A4)"""
    base_product = get_object_or_404(BaseProduct, pk=pk)
    legacy_code = base_product.get_first_legacy_code()

    context = {
        "base_product": base_product,
        "legacy_code": legacy_code,
        "active_menu": "variants",
    }
    return render(request, "inventory/variants/product_label_card.html", context)


@login_required
def all_products_label_cards(request):
    """عرض بطاقة لكل الأصناف المفعلة (مرة واحدة لكل صنف) مع خيار الفلترة حسب المخزن"""
    warehouse_ids = request.GET.getlist("warehouses")
    products = BaseProduct.objects.filter(is_active=True)

    if warehouse_ids:
        # فلترة الأصناف التي تملك مخزون فعلي في المخازن المختارة
        # نتحقق من النظام الجديد والقديم (Transactions) لضمان عدم ظهور صفحة فارغة
        q_new = Q(
            variants__warehouse_stocks__warehouse_id__in=warehouse_ids,
            variants__warehouse_stocks__current_quantity__gt=0,
        )
        q_old = Q(
            variants__legacy_product__transactions__warehouse_id__in=warehouse_ids,
            variants__legacy_product__transactions__running_balance__gt=0,
        )
        products = products.filter(q_new | q_old).distinct()

    products = products.order_by("-id")

    # نجهز القائمة مع بيانات المخازن لكل صنف للفلترة الديناميكية
    product_list = []
    for p in products:
        # الحصول على أرقام المخازن التي يتوفر فيها الصنف (من كلا النظامين)
        wh_new = p.variants.filter(
            warehouse_stocks__current_quantity__gt=0
        ).values_list("warehouse_stocks__warehouse_id", flat=True)
        wh_old = p.variants.filter(
            legacy_product__transactions__running_balance__gt=0
        ).values_list("legacy_product__transactions__warehouse_id", flat=True)

        available_whs = list(set(list(wh_new) + list(wh_old)))

        product_list.append(
            {
                "base_product": p,
                "legacy_code": p.get_first_legacy_code(),
                "available_warehouses": available_whs,
            }
        )

    # تجهيز محصول الطباعة (8 بطاقات في كل صفحة A4 - مقاس 10.1 سم)
    chunked_list = [product_list[i : i + 8] for i in range(0, len(product_list), 8)]

    context = {
        "product_list": chunked_list,
        "bulk_mode": True,
        "active_menu": "variants",
        "selected_warehouses": [int(idx) for idx in warehouse_ids],
        "all_warehouses": Warehouse.objects.filter(is_active=True),
    }
    return render(request, "inventory/variants/product_label_card.html", context)
