from django import forms
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    Customer,
    CustomerCategory,
    CustomerNote,
    CustomerResponsible,
    CustomerType,
    DiscountType,
    get_customer_types,
)


class CustomerTypeAdminForm(forms.ModelForm):
    """نموذج مخصص لـ CustomerType مع مربعات اختيار لأنواع الطلبات"""

    # مربعات اختيار لأنواع الطلبات المتاحة
    allowed_order_types_choices = forms.MultipleChoiceField(
        label=_("أنواع الطلبات المتاحة"),
        choices=CustomerType.ORDER_TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=False,
        help_text=_("اختر أنواع الطلبات المسموحة - اتركها فارغة للسماح بجميع الأنواع"),
    )

    class Meta:
        model = CustomerType
        fields = "__all__"
        exclude = ["allowed_order_types"]  # نستخدم الحقل المخصص بدلاً منه

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تحميل القيم الحالية
        if self.instance and self.instance.pk:
            current_types = self.instance.allowed_order_types or []
            self.fields["allowed_order_types_choices"].initial = current_types

    def save(self, commit=True):
        instance = super().save(commit=False)
        # تحويل الاختيارات إلى قائمة JSON
        instance.allowed_order_types = self.cleaned_data.get(
            "allowed_order_types_choices", []
        )
        if commit:
            instance.save()
            self._save_m2m()
        return instance


class CustomerAdminForm(forms.ModelForm):
    """نموذج مخصص لإدارة العملاء مع قائمة منسدلة ديناميكية لأنواع العملاء"""

    customer_type = forms.ChoiceField(label=_("نوع العميل"), choices=[], required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تحديث خيارات نوع العميل ديناميكياً
        customer_types = get_customer_types()
        self.fields["customer_type"].choices = customer_types

        # إذا كان هناك instance موجود، تعيين القيمة الحالية
        if self.instance and self.instance.pk:
            self.fields["customer_type"].initial = self.instance.customer_type

    def clean_customer_type(self):
        """التحقق من صحة نوع العميل"""
        customer_type = self.cleaned_data.get("customer_type")
        valid_choices = [choice[0] for choice in get_customer_types()]

        if customer_type not in valid_choices:
            raise forms.ValidationError(
                f'نوع العميل "{customer_type}" غير صحيح. الخيارات المتاحة: {valid_choices}'
            )

        return customer_type

    class Meta:
        model = Customer
        fields = "__all__"


@admin.register(CustomerCategory)
class CustomerCategoryAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ["name", "description", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at"]


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ["customer", "note_preview", "created_by", "created_at"]
    list_filter = ["created_at", "created_by"]
    search_fields = ["customer__name", "note", "created_by__username"]
    readonly_fields = ["created_by", "created_at"]

    def note_preview(self, obj):
        return obj.note[:50] + "..." if len(obj.note) > 50 else obj.note

    note_preview.short_description = _("الملاحظة")

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CustomerType)
class CustomerTypeAdmin(admin.ModelAdmin):
    """إدارة أنواع العملاء مع إعدادات التسعير والبادج"""

    form = CustomerTypeAdminForm  # استخدام النموذج المخصص
    change_form_template = "admin/customers/customertype/change_form.html"
    list_per_page = 50
    list_display = [
        "code",
        "name",
        "pricing_type_display",
        "discount_display",
        "allowed_types_display",
        "badge_preview",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "pricing_type", "created_at"]
    search_fields = ["code", "name", "description"]
    readonly_fields = ["created_at"]
    ordering = ["name"]
    filter_horizontal = ["discount_warehouses"]

    fieldsets = (
        (
            _("المعلومات الأساسية"),
            {"fields": ("code", "name", "description", "is_active")},
        ),
        (
            _("إعدادات التسعير"),
            {
                "fields": (
                    "pricing_type",
                    "discount_percentage",
                    "discount_warehouses",
                ),
                "description": _("يُحدد سلوك التسعير لهذا النوع من العملاء"),
            },
        ),
        (
            _("أنواع الطلبات المتاحة"),
            {
                "fields": ("allowed_order_types_choices",),
                "description": _(
                    "حدد أنواع الطلبات المسموحة لهذا النوع من العملاء - اتركها فارغة للسماح بجميع الأنواع"
                ),
            },
        ),
        (
            _("إعدادات البادج"),
            {
                "fields": (
                    "badge_style",
                    "badge_color",
                    "badge_icon",
                ),
                "classes": ("collapse",),  # مُخفي - يستخدم المنتقي التفاعلي
                "description": _("يتم التحكم عبر المنتقي التفاعلي أعلاه"),
            },
        ),
    )

    def pricing_type_display(self, obj):
        """عرض نوع التسعير مع أيقونة"""
        icons = {
            "retail": "🏪",
            "wholesale": "🏭",
            "discount": "💰",
        }
        return format_html(
            "{} {}",
            icons.get(obj.pricing_type, ""),
            obj.get_pricing_type_display(),
        )

    pricing_type_display.short_description = _("نوع التسعير")
    pricing_type_display.admin_order_field = "pricing_type"

    def discount_display(self, obj):
        """عرض نسبة الخصم"""
        if obj.pricing_type == "discount" and obj.discount_percentage:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 2px 8px; '
                'border-radius: 4px; font-weight: bold;">{}%</span>',
                obj.discount_percentage,
            )
        return "-"

    discount_display.short_description = _("الخصم")

    def allowed_types_display(self, obj):
        """عرض أنواع الطلبات المتاحة"""
        from django.utils.safestring import mark_safe

        if obj.allowed_order_types:
            # تحويل الترجمات لنص عادي
            type_names = {k: str(v) for k, v in CustomerType.ORDER_TYPE_CHOICES}
            types = [type_names.get(t, t) for t in obj.allowed_order_types]
            return format_html(
                '<span style="background: #17a2b8; color: white; padding: 2px 8px; '
                'border-radius: 4px; font-size: 11px;">{}</span>',
                "، ".join(types),
            )
        return mark_safe(
            '<span style="color: #6c757d; font-style: italic;">الكل</span>'
        )

    allowed_types_display.short_description = _("أنواع الطلبات")

    def badge_preview(self, obj):
        """معاينة البادج في القائمة"""
        return obj.get_badge_html()

    badge_preview.short_description = _("البادج")

    def badge_styles_preview(self, obj):
        """معاينة مرئية لجميع أنماط البادج"""
        sample_name = obj.name if obj and obj.name else "نوع العميل"
        colors = [
            "#007bff",
            "#28a745",
            "#dc3545",
            "#ffc107",
            "#17a2b8",
            "#6f42c1",
            "#fd7e14",
            "#20c997",
        ]

        html = (
            """
        <div style="padding: 15px; background: #f8f9fa; border-radius: 12px; margin-bottom: 10px;">
            <p style="margin-bottom: 15px; font-weight: bold; font-size: 14px;">💡 اختر الشكل والون من الخيارات أدناه:</p>
            
            <!-- أنماط البادج -->
            <div style="margin-bottom: 20px;">
                <p style="margin-bottom: 10px; color: #666;">الأنماط المتاحة:</p>
                <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                    <div style="text-align: center;">
                        <span style="background-color: #007bff; color: white; padding: 6px 14px; border-radius: 6px; display: inline-block;">"""
            + sample_name
            + """</span>
                        <p style="margin-top: 5px; font-size: 11px; color: #666;">صلب (solid)</p>
                    </div>
                    <div style="text-align: center;">
                        <span style="border: 2px solid #007bff; color: #007bff; background: transparent; padding: 6px 14px; border-radius: 6px; display: inline-block;">"""
            + sample_name
            + """</span>
                        <p style="margin-top: 5px; font-size: 11px; color: #666;">مخطط (outline)</p>
                    </div>
                    <div style="text-align: center;">
                        <span style="background: linear-gradient(135deg, #007bff, #007bffcc); color: white; padding: 6px 14px; border-radius: 6px; display: inline-block;">"""
            + sample_name
            + """</span>
                        <p style="margin-top: 5px; font-size: 11px; color: #666;">متدرج (gradient)</p>
                    </div>
                    <div style="text-align: center;">
                        <span style="background: #007bff33; backdrop-filter: blur(4px); color: #007bff; padding: 6px 14px; border-radius: 6px; display: inline-block;">"""
            + sample_name
            + """</span>
                        <p style="margin-top: 5px; font-size: 11px; color: #666;">زجاجي (glass)</p>
                    </div>
                </div>
            </div>
            
            <!-- ألوان مقترحة -->
            <div>
                <p style="margin-bottom: 10px; color: #666;">ألوان مقترحة (انسخ الكود):</p>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">"""
        )

        for color in colors:
            html += f"""
                    <div style="text-align: center; cursor: pointer;" title="انقر للنسخ: {color}">
                        <div style="width: 40px; height: 40px; background: {color}; border-radius: 8px; border: 2px solid #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.2);"></div>
                        <p style="margin-top: 3px; font-size: 9px; color: #666;">{color}</p>
                    </div>"""

        html += """
                </div>
            </div>
        </div>
        """
        from django.utils.safestring import mark_safe

        return mark_safe(html)

    badge_styles_preview.short_description = _("دليل الأنماط والألوان")

    def badge_preview_live(self, obj):
        """معاينة البادج الحالي"""
        if obj.pk:
            return format_html(
                '<div style="padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
                'border-radius: 12px; text-align: center;">'
                '<p style="color: white; margin-bottom: 10px; font-weight: bold;">✨ المعاينة الحالية:</p>'
                '<div style="background: white; padding: 20px; border-radius: 8px; display: inline-block;">{}</div>'
                "</div>",
                obj.get_badge_html(),
            )
        return format_html(
            '<div style="padding: 15px; background: #fff3cd; border-radius: 8px; text-align: center;">'
            '<p style="color: #856404;">💾 احفظ أولاً لمعاينة البادج</p>'
            "</div>"
        )

    badge_preview_live.short_description = _("معاينة البادج الحالي")


class CustomerResponsibleInline(admin.TabularInline):
    """إدارة مسؤولي العملاء كـ inline"""

    model = CustomerResponsible
    extra = 1
    max_num = 3
    fields = ["name", "position", "phone", "email", "is_primary", "order"]
    ordering = ["order", "name"]

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        # إضافة validation للتأكد من وجود مسؤول رئيسي واحد فقط
        class CustomFormSet(formset):
            def clean(self):
                super().clean()
                if any(self.errors):
                    return

                primary_count = 0
                for form in self.forms:
                    if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                        if form.cleaned_data.get("is_primary", False):
                            primary_count += 1

                if primary_count > 1:
                    raise forms.ValidationError(
                        _("يمكن أن يكون هناك مسؤول رئيسي واحد فقط")
                    )
                elif primary_count == 0 and obj and obj.requires_responsibles():
                    raise forms.ValidationError(
                        _("يجب تحديد مسؤول رئيسي واحد على الأقل")
                    )

        return CustomFormSet


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    form = CustomerAdminForm
    list_per_page = 20  # تقليل من 50 إلى 20 لتحسين الأداء
    list_max_show_all = 50  # تقليل من 100 إلى 50
    show_full_result_count = False  # تعطيل عدد النتائج لتحسين الأداء

    list_display = [
        "customer_code_display",
        "customer_image",
        "name",
        "customer_type_display",
        "branch",
        "phone",
        "phone2",
        "birth_date_display",
        "status",
        "category",
    ]

    # إضافة إمكانية الترتيب لجميع الأعمدة
    sortable_by = [
        "code",
        "name",
        "customer_type",
        "branch__name",
        "phone",
        "phone2",
        "birth_date",
        "status",
        "category__name",
        "created_at",
    ]

    list_filter = [
        "status",
        "customer_type",
        "category",
        "branch",
        "birth_date",
        "created_at",
    ]

    search_fields = [
        "code",
        "name",
        "phone",
        "phone2",
        "email",
        "birth_date",
        "notes",
        "category__name",
    ]

    readonly_fields = ["created_by", "created_at", "updated_at"]
    inlines = [CustomerResponsibleInline]

    fieldsets = (
        (
            _("معلومات أساسية"),
            {
                "fields": (
                    "code",
                    "name",
                    "image",
                    "customer_type",
                    "category",
                    "status",
                )
            },
        ),
        (
            _("معلومات الاتصال"),
            {"fields": ("phone", "phone2", "email", "birth_date", "address")},
        ),
        (
            _("معلومات إضافية"),
            {"fields": ("branch", "interests", "notes", "discount_type")},
        ),
        (
            _("معلومات النظام"),
            {
                "classes": ("collapse",),
                "fields": ("created_by", "created_at", "updated_at"),
            },
        ),
    )

    def customer_type_display(self, obj):
        """عرض نوع العميل بالاسم المقروء"""
        if not obj or not obj.customer_type:
            return "غير محدد"

        # الحصول على قاموس أنواع العملاء
        customer_types_dict = dict(get_customer_types())
        return customer_types_dict.get(obj.customer_type, obj.customer_type)

    customer_type_display.short_description = _("نوع العميل")
    customer_type_display.admin_order_field = "customer_type"

    def customer_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="border-radius: 50%;" />',
                obj.image.url,
            )
        return "-"

    customer_image.short_description = _("الصورة")

    def birth_date_display(self, obj):
        """عرض تاريخ الميلاد بالشكل المطلوب"""
        if obj.birth_date:
            return obj.birth_date.strftime("%d/%m")
        return "-"

    birth_date_display.short_description = _("تاريخ الميلاد")
    birth_date_display.admin_order_field = "birth_date"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("category", "branch", "created_by").only(
            "id",
            "code",
            "name",
            "customer_type",
            "phone",
            "phone2",
            "birth_date",
            "status",
            "category__id",
            "category__name",
            "branch__id",
            "branch__name",
            "created_by__id",
            "created_by__username",
        )

        if request.user.is_superuser:
            return qs
        # فلترة العملاء حسب فرع المستخدم
        if request.user.branch:
            return qs.filter(branch=request.user.branch)
        return qs.none()

    def get_urls(self):
        """إضافة URLs مخصصة للوصول للعملاء باستخدام الكود"""
        urls = super().get_urls()
        custom_urls = [
            path(
                "by-code/<str:customer_code>/",
                self.admin_site.admin_view(self.customer_by_code_view),
                name="customers_customer_by_code",
            ),
        ]
        return custom_urls + urls

    def customer_by_code_view(self, request, customer_code):
        """عرض العميل باستخدام الكود وإعادة التوجيه لصفحة التحرير"""
        try:
            customer = Customer.objects.get(code=customer_code)
            return HttpResponseRedirect(
                reverse("admin:customers_customer_change", args=[customer.pk])
            )
        except Customer.DoesNotExist:
            self.message_user(
                request, f"العميل بكود {customer_code} غير موجود", level="error"
            )
            return HttpResponseRedirect(reverse("admin:customers_customer_changelist"))

    def customer_code_display(self, obj):
        """عرض كود العميل مع روابط للعرض والتحرير - تحديث للاستخدام الكود في admin"""
        if not obj or not obj.code:
            return "-"

        try:
            # رابط عرض العميل في الواجهة
            view_url = reverse(
                "customers:customer_detail_by_code", kwargs={"customer_code": obj.code}
            )
            # رابط تحرير العميل في لوحة التحكم باستخدام الكود
            admin_url = reverse(
                "admin:customers_customer_by_code", kwargs={"customer_code": obj.code}
            )

            return format_html(
                "<strong>{}</strong><br/>"
                '<a href="{}" target="_blank" title="عرض في الواجهة">'
                '<span style="color: #0073aa;">👁️ عرض</span></a> | '
                '<a href="{}" title="تحرير في لوحة التحكم">'
                '<span style="color: #d63638;">✏️ تحرير</span></a>',
                obj.code,
                view_url,
                admin_url,
            )
        except Exception:
            return obj.code

    customer_code_display.short_description = _("كود العميل")
    customer_code_display.admin_order_field = "code"

    def has_change_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        # السماح بالتعديل فقط للعملاء في نفس فرع المستخدم
        return obj.branch == request.user.branch

    def has_delete_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        # السماح بالحذف فقط للعملاء في نفس فرع المستخدم
        return obj.branch == request.user.branch

    def delete_model(self, request, obj):
        """حذف عميل واحد مع حذف السجلات المرتبطة بشكل آمن"""
        from django.db import connection, transaction
        from django.db.models.signals import post_delete

        from orders import signals as order_signals
        from orders.models import OrderItem

        # تعطيل signal حذف عناصر الطلب مؤقتاً
        post_delete.disconnect(order_signals.log_order_item_deletion, sender=OrderItem)

        try:
            with transaction.atomic():
                # حذف سجلات OrderStatusLog لجميع طلبات العميل
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM orders_orderstatuslog
                        WHERE order_id IN (
                            SELECT id FROM orders_order WHERE customer_id = %s
                        )
                    """,
                        [obj.pk],
                    )

                # حذف العميل (سيتم حذف الطلبات تلقائياً بسبب CASCADE)
                obj.delete()
        finally:
            # إعادة تفعيل signal حذف عناصر الطلب
            post_delete.connect(order_signals.log_order_item_deletion, sender=OrderItem)

    def delete_queryset(self, request, queryset):
        """حذف عدة عملاء مع حذف السجلات المرتبطة بشكل آمن"""
        from django.db import connection, transaction
        from django.db.models.signals import post_delete

        from orders import signals as order_signals
        from orders.models import OrderItem

        # تعطيل signal حذف عناصر الطلب مؤقتاً
        post_delete.disconnect(order_signals.log_order_item_deletion, sender=OrderItem)

        try:
            with transaction.atomic():
                # حذف سجلات OrderStatusLog لجميع طلبات العملاء
                customer_ids = list(queryset.values_list("id", flat=True))
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM orders_orderstatuslog
                        WHERE order_id IN (
                            SELECT id FROM orders_order WHERE customer_id = ANY(%s)
                        )
                    """,
                        [customer_ids],
                    )

                # حذف العملاء (سيتم حذف الطلبات تلقائياً بسبب CASCADE)
                queryset.delete()
        finally:
            # إعادة تفعيل signal حذف عناصر الطلب
            post_delete.connect(order_signals.log_order_item_deletion, sender=OrderItem)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            if not request.user.is_superuser and not obj.branch:
                obj.branch = request.user.branch
        super().save_model(request, obj, form, change)

    class Media:
        css = {"all": ("css/admin-extra.css",)}


@admin.register(DiscountType)
class DiscountTypeAdmin(admin.ModelAdmin):
    """إدارة أنواع الخصومات"""

    list_display = [
        "name",
        "percentage",
        "is_active",
        "is_default",
        "customers_count",
        "created_at",
    ]
    list_filter = ["is_active", "is_default", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["-is_default", "percentage", "name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (_("معلومات أساسية"), {"fields": ("name", "percentage", "description")}),
        (_("الإعدادات"), {"fields": ("is_active", "is_default")}),
        (
            _("معلومات النظام"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def customers_count(self, obj):
        """عدد العملاء الذين يستخدمون هذا النوع من الخصم"""
        count = obj.customers.count()
        if count > 0:
            return format_html(
                '<a href="{}?discount_type__id__exact={}">{} عميل</a>',
                reverse("admin:customers_customer_changelist"),
                obj.id,
                count,
            )
        return "0 عميل"

    customers_count.short_description = _("عدد العملاء")

    def save_model(self, request, obj, form, change):
        # التأكد من وجود نوع خصم افتراضي واحد فقط
        if obj.is_default:
            DiscountType.objects.filter(is_default=True).exclude(pk=obj.pk).update(
                is_default=False
            )
        super().save_model(request, obj, form, change)


@admin.register(CustomerResponsible)
class CustomerResponsibleAdmin(admin.ModelAdmin):
    """إدارة مسؤولي العملاء"""

    list_display = ["name", "customer", "position", "phone", "is_primary", "order"]
    list_filter = ["is_primary", "created_at"]
    search_fields = ["name", "customer__name", "position", "phone", "email"]
    ordering = ["customer__name", "order", "name"]
    autocomplete_fields = ["customer"]

    fieldsets = (
        (_("معلومات المسؤول"), {"fields": ("customer", "name", "position")}),
        (_("معلومات الاتصال"), {"fields": ("phone", "email")}),
        (_("الإعدادات"), {"fields": ("is_primary", "order")}),
    )
