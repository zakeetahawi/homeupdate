"""
Views for ProductSet Management
مجموعات المنتجات المتناسقة
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms_product_set import ProductSetForm
from .models import ProductSet, ProductSetItem


class ProductSetListView(LoginRequiredMixin, ListView):
    """قائمة مجموعات المنتجات"""

    model = ProductSet
    template_name = "inventory/product_sets/product_set_list.html"
    context_object_name = "product_sets"
    paginate_by = 20

    def get_queryset(self):
        qs = ProductSet.objects.prefetch_related("base_products").order_by(
            "-created_at"
        )
        # البحث
        search = self.request.GET.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        # الفلترة حسب الحالة
        is_active = self.request.GET.get("is_active")
        if is_active == "1":
            qs = qs.filter(is_active=True)
        elif is_active == "0":
            qs = qs.filter(is_active=False)
        return qs


class ProductSetDetailView(LoginRequiredMixin, DetailView):
    """تفاصيل مجموعة منتجات"""

    model = ProductSet
    template_name = "inventory/product_sets/product_set_detail.html"
    context_object_name = "product_set"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ordered_products"] = self.object.get_ordered_products()
        return context


class ProductSetCreateView(LoginRequiredMixin, CreateView):
    """إنشاء مجموعة منتجات جديدة"""

    model = ProductSet
    form_class = ProductSetForm
    template_name = "inventory/product_sets/product_set_form.html"
    success_url = reverse_lazy("inventory:product_set_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f"تم إنشاء مجموعة '{form.instance.name}' بنجاح")
        return super().form_valid(form)


class ProductSetUpdateView(LoginRequiredMixin, UpdateView):
    """تعديل مجموعة منتجات"""

    model = ProductSet
    form_class = ProductSetForm
    template_name = "inventory/product_sets/product_set_form.html"
    success_url = reverse_lazy("inventory:product_set_list")

    def form_valid(self, form):
        messages.success(self.request, f"تم تحديث مجموعة '{form.instance.name}' بنجاح")
        return super().form_valid(form)


class ProductSetDeleteView(LoginRequiredMixin, DeleteView):
    """حذف مجموعة منتجات"""

    model = ProductSet
    template_name = "inventory/product_sets/product_set_confirm_delete.html"
    success_url = reverse_lazy("inventory:product_set_list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f"تم حذف مجموعة '{self.object.name}' بنجاح")
        return super().delete(request, *args, **kwargs)


# ═══════════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════════


@require_http_methods(["GET"])
def product_set_api(request, pk):
    """
    API للحصول على معلومات ProductSet
    GET /inventory/api/product-set/<int:pk>/
    """
    product_set = get_object_or_404(
        ProductSet.objects.prefetch_related("base_products"), pk=pk
    )

    products_data = []
    for item in product_set.productsetitem_set.select_related(
        "base_product", "base_product__category"
    ).order_by("display_order"):
        bp = item.base_product
        products_data.append(
            {
                "code": bp.code,
                "name": bp.name,
                "name_en": bp.name_en or bp.name,
                "price": float(bp.base_price),
                "currency": "EGP",
                "category": bp.category.name if bp.category else "",
                "material": bp.material,
                "width": bp.width,
                "unit": "متر",
                "display_order": item.display_order,
            }
        )

    data = {
        "id": product_set.id,
        "name": product_set.name,
        "description": product_set.description,
        "is_active": product_set.is_active,
        "products": products_data,
    }

    return JsonResponse(data)


@login_required
@require_http_methods(["POST"])
def reorder_products(request, pk):
    """
    إعادة ترتيب المنتجات في المجموعة
    POST /inventory/product-set/<pk>/reorder/
    Body: {"orders": [{"id": 1, "order": 1}, ...]}
    """
    product_set = get_object_or_404(ProductSet, pk=pk)

    try:
        import json

        data = json.loads(request.body)
        orders = data.get("orders", [])

        for order_data in orders:
            item_id = order_data.get("id")
            new_order = order_data.get("order")
            ProductSetItem.objects.filter(
                id=item_id, product_set=product_set
            ).update(display_order=new_order)

        product_set.cloudflare_synced = False
        product_set.save(update_fields=["cloudflare_synced"])

        return JsonResponse({"success": True, "message": "تم إعادة الترتيب بنجاح"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
