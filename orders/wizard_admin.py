"""
نظام الإدارة المتقدم للويزارد - إدارة كاملة لنظام الويزارد من لوحة التحكم
Advanced Wizard Admin System - Complete Management from Admin Panel
"""

from django import forms
from django.contrib import admin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from accounts.models import SystemSettings

from .models import Order
from .wizard_models import DraftOrder, DraftOrderItem


class DraftOrderItemInline(admin.TabularInline):
    """إدارة عناصر المسودة"""

    model = DraftOrderItem
    extra = 1
    readonly_fields = ("total_price", "discount_amount", "final_price")
    fields = (
        "product",
        "quantity",
        "unit_price",
        "discount_percentage",
        "item_type",
        "notes",
    )

    def total_price(self, obj):
        if obj.id:
            currency = str(SystemSettings.get_settings().currency_symbol)
            return format_html("{} {}", f"{float(obj.total_price):.2f}", currency)
        return "-"

    total_price.short_description = "السعر الإجمالي"

    def discount_amount(self, obj):
        if obj.id:
            currency = str(SystemSettings.get_settings().currency_symbol)
            return format_html("{} {}", f"{float(obj.discount_amount):.2f}", currency)
        return "-"

    discount_amount.short_description = "الخصم"

    def final_price(self, obj):
        if obj.id:
            currency = str(SystemSettings.get_settings().currency_symbol)
            return format_html("{} {}", f"{float(obj.final_price):.2f}", currency)
        return "-"

    final_price.short_description = "السعر النهائي"


@admin.register(DraftOrder)
class DraftOrderAdmin(admin.ModelAdmin):
    """إدارة متقدمة لمسودات الطلبات (الويزارد)"""

    list_display = (
        "draft_number_display",
        "customer_display",
        "selected_type_display",
        "current_step_progress",
        "status_badge",
        "totals_display",
        "edit_info_display",
        "created_by",
        "created_at",
        "actions_display",
    )
    list_filter = (
        "is_completed",
        "current_step",
        "selected_type",
        "status",
        "contract_type",
        "payment_method",
        "created_at",
        "branch",
    )
    search_fields = (
        "customer__name",
        "customer__phone",
        "created_by__username",
        "invoice_number",
        "contract_number",
        "notes",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "completed_at",
        "final_order",
        "totals_info",
        "wizard_progress",
    )
    inlines = [DraftOrderItemInline]
    date_hierarchy = "created_at"
    ordering = ["-updated_at"]

    fieldsets = (
        (
            _("معلومات المسودة"),
            {
                "fields": (
                    "created_by",
                    "current_step",
                    "completed_steps",
                    "is_completed",
                    "completed_at",
                    "final_order",
                    "wizard_progress",
                )
            },
        ),
        (
            _("البيانات الأساسية (الخطوة 1)"),
            {"fields": ("customer", "branch", "salesperson", "status", "notes")},
        ),
        (
            _("نوع الطلب (الخطوة 2)"),
            {
                "fields": (
                    "selected_type",
                    "related_inspection",
                    "related_inspection_type",
                    "customer_side_measurements",
                    "measurement_agreement_file",
                )
            },
        ),
        (
            _("الفاتورة والدفع (الخطوة 4)"),
            {
                "fields": (
                    "invoice_number",
                    "invoice_number_2",
                    "invoice_number_3",
                    "contract_number",
                    "contract_number_2",
                    "contract_number_3",
                    "payment_method",
                    "paid_amount",
                    "payment_notes",
                    "totals_info",
                )
            },
        ),
        (
            _("العقد (الخطوة 5)"),
            {"fields": ("contract_type", "contract_file"), "classes": ("collapse",)},
        ),
        (
            _("معلومات النظام"),
            {
                "fields": ("created_at", "updated_at", "wizard_state"),
                "classes": ("collapse",),
            },
        ),
    )

    def draft_number_display(self, obj):
        """عرض رقم المسودة مع رابط"""
        if obj.is_completed and obj.final_order:
            order_url = reverse("admin:orders_order_change", args=[obj.final_order.pk])
            return format_html(
                "<strong>مسودة #{}</strong><br/>"
                '<a href="{}" style="color: #28a745;">✓ طلب #{}</a>',
                obj.pk,
                order_url,
                obj.final_order.order_number,
            )
        return format_html("<strong>مسودة #{}</strong>", obj.pk)

    draft_number_display.short_description = "رقم المسودة"

    def customer_display(self, obj):
        """عرض معلومات العميل"""
        if obj.customer:
            return format_html(
                "<strong>{}</strong><br/>" '<small style="color: #666;">{}</small>',
                obj.customer.name,
                obj.customer.phone or "-",
            )
        return "-"

    customer_display.short_description = "العميل"

    def selected_type_display(self, obj):
        """عرض نوع الطلب مع أيقونة"""
        if not obj.selected_type:
            return mark_safe('<span style="color: #999;">غير محدد</span>')

        type_icons = {
            "accessory": "💎",
            "installation": "🔧",
            "inspection": "👁️",
            "tailoring": "✂️",
            "products": "📦",
        }
        type_names = {
            "accessory": "إكسسوار",
            "installation": "تركيب",
            "inspection": "معاينة",
            "tailoring": "تسليم",
            "products": "منتجات",
        }

        icon = type_icons.get(obj.selected_type, "📋")
        name = type_names.get(obj.selected_type, obj.selected_type)

        return format_html('<span style="font-size: 18px;">{}</span> {}', icon, name)

    selected_type_display.short_description = "نوع الطلب"

    def current_step_progress(self, obj):
        """عرض التقدم في الخطوات"""
        total_steps = 6
        current = obj.current_step
        completed = len(obj.completed_steps) if obj.completed_steps else 0

        # حساب نسبة الإكمال
        progress = (completed / total_steps) * 100

        # لون شريط التقدم
        if progress < 40:
            color = "#dc3545"  # أحمر
        elif progress < 70:
            color = "#ffc107"  # أصفر
        else:
            color = "#28a745"  # أخضر

        return format_html(
            '<div style="display: flex; align-items: center; gap: 8px;">'
            '<div style="width: 100px; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden;">'
            '<div style="width: {}%; height: 100%; background: {}; transition: width 0.3s;"></div>'
            "</div>"
            '<span style="font-size: 11px; color: #666;">{}/{}</span>'
            "</div>",
            progress,
            color,
            completed,
            total_steps,
        )

    current_step_progress.short_description = "التقدم"

    def status_badge(self, obj):
        """عرض حالة المسودة"""
        if obj.is_completed:
            return mark_safe(
                '<span style="background: #28a745; color: white; padding: 4px 12px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">✓ مكتملة</span>'
            )
        else:
            return mark_safe(
                '<span style="background: #ffc107; color: #333; padding: 4px 12px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">⏳ قيد العمل</span>'
            )

    status_badge.short_description = "الحالة"

    def totals_display(self, obj):
        """عرض المجاميع المالية"""
        currency = str(SystemSettings.get_settings().currency_symbol)
        return format_html(
            '<div style="font-size: 11px;">'
            '<strong style="color: #007bff;">{} {}</strong><br/>'
            '<span style="color: #666;">خصم: {} {}</span><br/>'
            '<span style="color: #28a745;">مدفوع: {} {}</span>'
            "</div>",
            f"{float(obj.final_total):.2f}",
            currency,
            f"{float(obj.total_discount):.2f}",
            currency,
            f"{float(obj.paid_amount):.2f}",
            currency,
        )

    totals_display.short_description = "المالية"

    def edit_info_display(self, obj):
        """عرض معلومات التعديلات"""
        if (
            not obj.edit_history
            or not isinstance(obj.edit_history, list)
            or len(obj.edit_history) == 0
        ):
            return mark_safe('<span style="color: #999;">-</span>')

        edit_count = len(obj.edit_history)
        last_editor = obj.last_modified_by

        if last_editor and last_editor != obj.created_by:
            return format_html(
                '<div style="font-size: 11px;">'
                '<span style="background: #ffc107; color: #333; padding: 2px 6px; '
                'border-radius: 8px; font-weight: bold;">📝 {0} تعديل</span><br/>'
                '<small style="color: #666;">بواسطة: {1}</small>'
                "</div>",
                edit_count,
                last_editor.get_full_name(),
            )
        return mark_safe('<span style="color: #999;">-</span>')

    edit_info_display.short_description = "التعديلات"

    def actions_display(self, obj):
        """عرض أزرار الإجراءات"""
        if obj.is_completed:
            if obj.final_order:
                order_url = reverse(
                    "admin:orders_order_change", args=[obj.final_order.pk]
                )
                return format_html(
                    '<a href="{}" class="button" style="background: #28a745; color: white; '
                    'padding: 5px 10px; border-radius: 4px; text-decoration: none; font-size: 11px;">'
                    "👁️ عرض الطلب</a>",
                    order_url,
                )
            return "-"
        else:
            continue_url = reverse("orders:wizard_step", args=[obj.current_step])
            return format_html(
                '<a href="{}?draft_id={}" class="button" style="background: #007bff; color: white; '
                'padding: 5px 10px; border-radius: 4px; text-decoration: none; font-size: 11px;">'
                "▶️ متابعة</a>",
                continue_url,
                obj.pk,
            )

    actions_display.short_description = "الإجراءات"

    def wizard_progress(self, obj):
        """عرض تفصيلي للتقدم في الويزارد"""
        steps = [
            (1, "البيانات الأساسية"),
            (2, "نوع الطلب"),
            (3, "عناصر الطلب"),
            (4, "الفاتورة والدفع"),
            (5, "العقد الإلكتروني"),
            (6, "المراجعة والتأكيد"),
        ]

        completed = obj.completed_steps if obj.completed_steps else []
        current = obj.current_step

        html = '<div style="display: flex; flex-direction: column; gap: 8px;">'
        for step_num, step_name in steps:
            if step_num in completed:
                icon = "✅"
                color = "#28a745"
            elif step_num == current:
                icon = "▶️"
                color = "#007bff"
            else:
                icon = "⏳"
                color = "#999"

            html += format_html(
                '<div style="display: flex; align-items: center; gap: 8px;">'
                '<span style="font-size: 16px;">{}</span>'
                '<span style="color: {}; font-size: 12px;">{}</span>'
                "</div>",
                icon,
                color,
                step_name,
            )
        html += "</div>"

        return mark_safe(html)

    wizard_progress.short_description = "تقدم الخطوات"

    def totals_info(self, obj):
        """معلومات مفصلة عن المجاميع"""
        totals = obj.calculate_totals()
        currency = str(SystemSettings.get_settings().currency_symbol)
        return format_html(
            '<table style="width: 100%; font-size: 12px;">'
            "<tr><td><strong>المجموع قبل الخصم:</strong></td><td>{} {}</td></tr>"
            '<tr><td><strong>إجمالي الخصم:</strong></td><td style="color: #dc3545;">{} {}</td></tr>'
            '<tr><td><strong>المجموع النهائي:</strong></td><td style="color: #28a745; font-weight: bold;">{} {}</td></tr>'
            "<tr><td><strong>المبلغ المدفوع:</strong></td><td>{} {}</td></tr>"
            '<tr><td><strong>المتبقي:</strong></td><td style="color: #ffc107;">{} {}</td></tr>'
            "</table>",
            f"{float(totals['subtotal']):.2f}",
            currency,
            f"{float(totals['total_discount']):.2f}",
            currency,
            f"{float(totals['final_total']):.2f}",
            currency,
            f"{float(obj.paid_amount):.2f}",
            currency,
            f"{float(totals['remaining']):.2f}",
            currency,
        )

    totals_info.short_description = "تفاصيل المبالغ"

    def get_urls(self):
        """إضافة URLs مخصصة للإدارة"""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:draft_id>/continue-wizard/",
                self.admin_site.admin_view(self.continue_wizard_view),
                name="wizard_draft_continue",
            ),
            path(
                "<int:draft_id>/convert-to-order/",
                self.admin_site.admin_view(self.convert_to_order_view),
                name="wizard_draft_convert",
            ),
        ]
        return custom_urls + urls

    def continue_wizard_view(self, request, draft_id):
        """متابعة الويزارد من مسودة معينة"""
        draft = get_object_or_404(DraftOrder, pk=draft_id)

        # حفظ معرف المسودة في الجلسة
        request.session["wizard_draft_id"] = draft_id

        # توجيه إلى الخطوة الحالية
        return HttpResponseRedirect(
            reverse("orders:wizard_step", args=[draft.current_step])
        )

    def convert_to_order_view(self, request, draft_id):
        """تحويل المسودة إلى طلب نهائي يدوياً"""
        draft = get_object_or_404(DraftOrder, pk=draft_id)

        if draft.is_completed:
            messages.warning(request, "هذه المسودة تم تحويلها مسبقاً إلى طلب.")
            return HttpResponseRedirect(
                reverse("admin:orders_order_change", args=[draft.final_order.pk])
            )

        try:
            with transaction.atomic():
                # إنشاء الطلب النهائي
                order = self._create_order_from_draft(draft, request.user)

                # تحديث المسودة
                draft.is_completed = True
                draft.completed_at = timezone.now()
                draft.final_order = order
                draft.save()

                messages.success(
                    request,
                    f"تم تحويل المسودة #{draft.pk} إلى طلب #{order.order_number} بنجاح!",
                )

                return HttpResponseRedirect(
                    reverse("admin:orders_order_change", args=[order.pk])
                )

        except Exception as e:
            messages.error(request, f"خطأ في تحويل المسودة: {str(e)}")
            return HttpResponseRedirect(
                reverse("admin:wizard_draftorder_change", args=[draft_id])
            )

    def _create_order_from_draft(self, draft, user):
        """إنشاء طلب نهائي من مسودة"""
        # إنشاء الطلب
        order = Order.objects.create(
            customer=draft.customer,
            branch=draft.branch,
            salesperson=draft.salesperson,
            status=draft.status,
            selected_types=[draft.selected_type],
            notes=draft.notes,
            invoice_number=draft.invoice_number,
            invoice_number_2=draft.invoice_number_2,
            invoice_number_3=draft.invoice_number_3,
            contract_number=draft.contract_number,
            contract_number_2=draft.contract_number_2,
            contract_number_3=draft.contract_number_3,
            contract_file=draft.contract_file,
            payment_verified=draft.paid_amount >= draft.final_total,
            paid_amount=draft.paid_amount,
            created_by=user,
            related_inspection=draft.related_inspection,
            related_inspection_type=draft.related_inspection_type,
        )

        # نسخ العناصر
        for item in draft.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_percentage=item.discount_percentage,
                item_type=item.item_type,
                notes=item.notes,
            )

        # حساب المجاميع
        order.calculate_final_price()
        order.save()

        # إنشاء دفعة إذا كان هناك مبلغ مدفوع
        if draft.paid_amount > 0:
            Payment.objects.create(
                order=order,
                amount=draft.paid_amount,
                payment_method=draft.payment_method,
                notes=draft.payment_notes or "دفعة من الويزارد",
                created_by=user,
            )

        return order

    actions = ["mark_as_completed", "delete_draft_orders"]

    def mark_as_completed(self, request, queryset):
        """تحديد المسودات كمكتملة"""
        updated = 0
        for draft in queryset:
            if not draft.is_completed:
                try:
                    order = self._create_order_from_draft(draft, request.user)
                    draft.is_completed = True
                    draft.completed_at = timezone.now()
                    draft.final_order = order
                    draft.save()
                    updated += 1
                except Exception as e:
                    messages.error(
                        request, f"خطأ في تحويل المسودة #{draft.pk}: {str(e)}"
                    )

        self.message_user(
            request,
            f"تم تحويل {updated} مسودة إلى طلبات نهائية.",
            level="SUCCESS" if updated > 0 else "WARNING",
        )

    mark_as_completed.short_description = "تحويل إلى طلبات نهائية"

    def delete_draft_orders(self, request, queryset):
        """حذف المسودات المحددة"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"تم حذف {count} مسودة.", level="SUCCESS")

    delete_draft_orders.short_description = "حذف المسودات المحددة"


@admin.register(DraftOrderItem)
class DraftOrderItemAdmin(admin.ModelAdmin):
    """إدارة عناصر مسودات الطلبات"""

    list_display = (
        "draft_order",
        "product",
        "quantity",
        "unit_price",
        "discount_percentage",
        "total_price_display",
        "final_price_display",
        "item_type",
    )
    list_filter = ("item_type", "created_at")
    search_fields = ("product__name", "draft_order__customer__name")
    readonly_fields = (
        "created_at",
        "updated_at",
        "total_price",
        "discount_amount",
        "final_price",
    )

    def total_price_display(self, obj):
        return format_html("{} ر.س", f"{float(obj.total_price):.2f}")

    total_price_display.short_description = "السعر الإجمالي"

    def final_price_display(self, obj):
        return format_html("{} ر.س", f"{float(obj.final_price):.2f}")

    final_price_display.short_description = "السعر النهائي"
