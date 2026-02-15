"""
نماذج إضافية وموسعة لقسم المخزون
تتضمن نماذج للفئات، الموردين، المستودعات، طلبات الشراء، والتسويات
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import Branch, User
from core.utils.general import clean_phone_number

from .models import (
    Category,
    InventoryAdjustment,
    Product,
    ProductBatch,
    PurchaseOrder,
    PurchaseOrderItem,
    StockAlert,
    Supplier,
    Warehouse,
    WarehouseLocation,
)


class CategoryForm(forms.ModelForm):
    """نموذج إضافة/تعديل الفئات"""

    class Meta:
        model = Category
        fields = ["name", "description", "parent"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("اسم الفئة"),
                    "required": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("وصف الفئة (اختياري)"),
                }
            ),
            "parent": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "name": _("اسم الفئة"),
            "description": _("الوصف"),
            "parent": _("الفئة الأب"),
        }
        help_texts = {"parent": _("اختياري - يمكن تصنيف هذه الفئة ضمن فئة أكبر")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Category.objects.all().order_by("name")
        self.fields["parent"].required = False
        self.fields["parent"].empty_label = _("بدون فئة أب")
        self.fields["description"].required = False

    def clean_name(self):
        """التحقق من عدم تكرار اسم الفئة"""
        name = self.cleaned_data.get("name")
        if name:
            name = name.strip()
            # التحقق من التكرار (باستثناء الفئة الحالية في حالة التعديل)
            existing = Category.objects.filter(name__iexact=name)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError(_("يوجد فئة بنفس الاسم بالفعل"))
        return name

    def clean(self):
        """التحقق من عدم تعيين الفئة كأب لنفسها"""
        cleaned_data = super().clean()
        parent = cleaned_data.get("parent")

        if parent and self.instance and self.instance.pk:
            if parent.pk == self.instance.pk:
                raise ValidationError(_("لا يمكن تعيين الفئة كأب لنفسها"))

            # التحقق من عدم إنشاء دائرة (الأب -> الابن -> الأب)
            current_parent = parent
            while current_parent:
                if current_parent.pk == self.instance.pk:
                    raise ValidationError(_("لا يمكن إنشاء ارتباط دائري بين الفئات"))
                current_parent = current_parent.parent

        return cleaned_data


class SupplierForm(forms.ModelForm):
    """نموذج إضافة/تعديل الموردين"""

    class Meta:
        model = Supplier
        fields = [
            "name",
            "contact_person",
            "phone",
            "email",
            "address",
            "tax_number",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("اسم المورد"),
                    "required": True,
                }
            ),
            "contact_person": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("اسم الشخص المسؤول")}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("رقم الهاتف")}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": _("البريد الإلكتروني")}
            ),
            "address": forms.Textarea(
                attrs={"class": "form-control", "rows": 2, "placeholder": _("العنوان")}
            ),
            "tax_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": _("الرقم الضريبي")}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("ملاحظات إضافية"),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # جعل جميع الحقول اختيارية ما عدا الاسم
        for field_name in self.fields:
            if field_name != "name":
                self.fields[field_name].required = False

    def clean_phone(self):
        """التحقق من صحة رقم الهاتف"""
        return clean_phone_number(self.cleaned_data.get("phone"))

    def clean_email(self):
        """التحقق من صحة البريد الإلكتروني"""
        email = self.cleaned_data.get("email")
        if email:
            email = email.strip().lower()
        return email


class WarehouseForm(forms.ModelForm):
    """نموذج إضافة/تعديل المستودعات"""

    class Meta:
        model = Warehouse
        fields = [
            "name",
            "code",
            "branch",
            "manager",
            "address",
            "is_active",
            "is_official_fabric_warehouse",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("اسم المستودع"),
                    "required": True,
                }
            ),
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("رمز فريد للمستودع"),
                    "required": True,
                }
            ),
            "branch": forms.Select(attrs={"class": "form-select"}),
            "manager": forms.Select(attrs={"class": "form-select"}),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": _("عنوان المستودع"),
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_official_fabric_warehouse": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": _("ملاحظات")}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = Branch.objects.all().order_by("name")
        self.fields["branch"].required = False
        self.fields["branch"].empty_label = _("بدون فرع")

        self.fields["manager"].queryset = User.objects.filter(is_active=True).order_by(
            "username"
        )
        self.fields["manager"].required = False
        self.fields["manager"].empty_label = _("بدون مدير")

        self.fields["address"].required = False
        self.fields["notes"].required = False

    def clean_code(self):
        """التحقق من عدم تكرار رمز المستودع"""
        code = self.cleaned_data.get("code")
        if code:
            code = code.strip().upper()
            # التحقق من التكرار (باستثناء المستودع الحالي في حالة التعديل)
            existing = Warehouse.objects.filter(code__iexact=code)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError(_("يوجد مستودع بنفس الرمز بالفعل"))
        return code


class WarehouseLocationForm(forms.ModelForm):
    """نموذج إضافة/تعديل مواقع التخزين"""

    class Meta:
        model = WarehouseLocation
        fields = ["name", "code", "warehouse", "description", "capacity", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("اسم الموقع"),
                    "required": True,
                }
            ),
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("رمز الموقع"),
                    "required": True,
                }
            ),
            "warehouse": forms.Select(attrs={"class": "form-select", "required": True}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": _("وصف الموقع"),
                }
            ),
            "capacity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "placeholder": _("السعة القصوى"),
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["warehouse"].queryset = Warehouse.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["description"].required = False

    def clean(self):
        """التحقق من عدم تكرار رمز الموقع في نفس المستودع"""
        cleaned_data = super().clean()
        code = cleaned_data.get("code")
        warehouse = cleaned_data.get("warehouse")

        if code and warehouse:
            code = code.strip().upper()
            cleaned_data["code"] = code

            # التحقق من التكرار
            existing = WarehouseLocation.objects.filter(
                warehouse=warehouse, code__iexact=code
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise ValidationError(
                    {"code": _("يوجد موقع بنفس الرمز في هذا المستودع")}
                )

        return cleaned_data


class InventoryAdjustmentForm(forms.ModelForm):
    """نموذج تسوية المخزون"""

    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        label=_("المستودع"),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = InventoryAdjustment
        fields = ["product", "batch", "adjustment_type", "quantity_after", "reason"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select", "required": True}),
            "batch": forms.Select(attrs={"class": "form-select"}),
            "adjustment_type": forms.Select(
                attrs={"class": "form-select", "required": True}
            ),
            "quantity_after": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "required": True,
                }
            ),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("سبب التسوية بالتفصيل"),
                    "required": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["warehouse"].queryset = Warehouse.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["product"].queryset = Product.objects.all().order_by("name")
        self.fields["batch"].required = False
        self.fields["batch"].empty_label = _("بدون دفعة محددة")

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        warehouse = cleaned_data.get("warehouse")
        quantity_after = cleaned_data.get("quantity_after")

        if product and warehouse:
            # حساب الكمية الحالية
            from .models import StockTransaction

            last_transaction = (
                StockTransaction.objects.filter(product=product, warehouse=warehouse)
                .order_by("-transaction_date", "-id")
                .first()
            )

            quantity_before = (
                last_transaction.running_balance if last_transaction else 0
            )
            cleaned_data["quantity_before"] = quantity_before

            # التحقق من المنطقية
            if quantity_after is not None and quantity_after < 0:
                raise ValidationError(
                    {"quantity_after": _("الكمية بعد التسوية لا يمكن أن تكون سالبة")}
                )

        return cleaned_data


class PurchaseOrderForm(forms.ModelForm):
    """نموذج طلب الشراء"""

    class Meta:
        model = PurchaseOrder
        fields = ["supplier", "warehouse", "status", "expected_date", "notes"]
        widgets = {
            "supplier": forms.Select(attrs={"class": "form-select", "required": True}),
            "warehouse": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "expected_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": _("ملاحظات")}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].queryset = Supplier.objects.all().order_by("name")
        self.fields["warehouse"].queryset = Warehouse.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["warehouse"].required = False
        self.fields["warehouse"].empty_label = _("اختر المستودع")
        self.fields["expected_date"].required = False
        self.fields["notes"].required = False


class StockAlertForm(forms.ModelForm):
    """نموذج تنبيهات المخزون"""

    class Meta:
        model = StockAlert
        fields = [
            "product",
            "alert_type",
            "message",
            "description",
            "priority",
            "is_urgent",
            "is_pinned",
        ]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select", "required": True}),
            "alert_type": forms.Select(
                attrs={"class": "form-select", "required": True}
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": _("رسالة التنبيه المختصرة"),
                    "required": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("تفاصيل إضافية"),
                }
            ),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "is_urgent": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_pinned": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.all().order_by("name")
        self.fields["description"].required = False


class ProductFilterForm(forms.Form):
    """نموذج فلترة وبحث متقدم للمنتجات"""

    search = forms.CharField(
        required=False,
        label=_("بحث"),
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("ابحث بالاسم أو الكود أو الوصف"),
            }
        ),
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label=_("الفئة"),
        empty_label=_("جميع الفئات"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        required=False,
        label=_("المستودع"),
        empty_label=_("جميع المستودعات"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    stock_status = forms.ChoiceField(
        required=False,
        label=_("حالة المخزون"),
        choices=[
            ("", _("الكل")),
            ("in_stock", _("متوفر")),
            ("low_stock", _("مخزون منخفض")),
            ("out_of_stock", _("نفذ من المخزون")),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    price_min = forms.DecimalField(
        required=False,
        label=_("السعر من"),
        min_value=0,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": _("0.00")}
        ),
    )

    price_max = forms.DecimalField(
        required=False,
        label=_("السعر إلى"),
        min_value=0,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": _("0.00")}
        ),
    )

    sort_by = forms.ChoiceField(
        required=False,
        label=_("ترتيب حسب"),
        initial="-created_at",
        choices=[
            ("-created_at", _("الأحدث")),
            ("created_at", _("الأقدم")),
            ("name", _("الاسم (أ-ي)")),
            ("-name", _("الاسم (ي-أ)")),
            ("price", _("السعر (من الأقل)")),
            ("-price", _("السعر (من الأعلى)")),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        price_min = cleaned_data.get("price_min")
        price_max = cleaned_data.get("price_max")

        if price_min and price_max and price_min > price_max:
            raise ValidationError(_("السعر الأدنى يجب أن يكون أقل من السعر الأعلى"))

        return cleaned_data


class StockTransactionFilterForm(forms.Form):
    """نموذج فلترة حركات المخزون"""

    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        required=False,
        label=_("المنتج"),
        empty_label=_("جميع المنتجات"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        required=False,
        label=_("المستودع"),
        empty_label=_("جميع المستودعات"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    transaction_type = forms.ChoiceField(
        required=False,
        label=_("نوع الحركة"),
        choices=[("", _("الكل"))] + list(StockTransaction.TRANSACTION_TYPES),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    reason = forms.ChoiceField(
        required=False,
        label=_("السبب"),
        choices=[("", _("الكل"))] + list(StockTransaction.REASON_CHOICES),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    date_from = forms.DateField(
        required=False,
        label=_("من تاريخ"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    date_to = forms.DateField(
        required=False,
        label=_("إلى تاريخ"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise ValidationError(_("تاريخ البداية يجب أن يكون قبل تاريخ النهاية"))

        return cleaned_data
