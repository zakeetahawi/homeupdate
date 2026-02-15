"""
نماذج الويزارد لإنشاء الطلبات
Forms for Multi-Step Order Creation Wizard
"""

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from accounts.models import Branch, Salesperson
from customers.models import Customer
from inspections.models import Inspection
from inventory.models import Product

from .contract_models import ContractCurtain, CurtainAccessory, CurtainFabric
from .wizard_models import DraftOrder, DraftOrderItem


class Step1BasicInfoForm(forms.ModelForm):
    """
    الخطوة 1: البيانات الأساسية
    """

    class Meta:
        model = DraftOrder
        fields = [
            "customer",
            "branch",
            "salesperson",
            "status",
            "delivery_location",
            "notes",
        ]
        widgets = {
            "customer": forms.Select(
                attrs={
                    "class": "form-select select2-customer",
                }
            ),
            "branch": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "salesperson": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "delivery_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "موقع التسليم (مثال: مستودع، فرع، عنوان خاص)",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "ملاحظات حول الطلب (اختياري)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # ⚡ منع تغيير العميل بعد تحديده (حماية من التداخل في أرقام الطلبات)
        if self.instance and self.instance.pk and self.instance.customer:
            # إذا كان العميل محدداً مسبقاً، جعل الحقل للقراءة فقط بدون تعطيله
            # لا نستخدم disabled لأنه يمنع إرسال القيمة
            self.fields["customer"].widget.attrs["readonly"] = True
            self.fields["customer"].widget.attrs["class"] = "form-select bg-light"
            self.fields["customer"].widget.attrs["data-locked"] = "true"
            self.fields["customer"].help_text = (
                '<div class="alert alert-warning mt-2 mb-0">'
                '<i class="bi bi-exclamation-triangle-fill"></i> '
                "<strong>تنبيه:</strong> لا يمكن تغيير العميل بعد تحديده. "
                "رقم الطلب مرتبط بالعميل الأصلي. "
                "احذف المسودة وأنشئ طلباً جديداً لتغيير العميل."
                "</div>"
            )

        # العميل: حقل إجباري بدون اختيار افتراضي
        self.fields["customer"].empty_label = "اختر العميل..."
        self.fields["customer"].required = True  # التحقق من جهة الخادم فقط

        # تحديد ما إذا كان المستخدم من الفرع الرئيسي أو مدير
        is_main_branch_user = False
        is_admin_user = False
        user_branch = None

        if user:
            is_admin_user = (
                user.is_superuser
                or user.groups.filter(name__in=["مدير نظام", "مدير عام"]).exists()
            )

            if hasattr(user, "branch") and user.branch:
                user_branch = user.branch
                # التحقق إذا كان الفرع الرئيسي (بالاسم أو is_main)
                is_main_branch_user = (
                    hasattr(user.branch, "is_main") and user.branch.is_main
                ) or user.branch.name in [
                    "الرئيسي",
                    "الفرع الرئيسي",
                    "Main",
                    "Main Branch",
                ]

        # تحديد الفروع المتاحة
        if is_admin_user or is_main_branch_user:
            # مدير النظام أو مستخدم الفرع الرئيسي - جميع الفروع
            self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
            # جميع البائعين
            self.fields["salesperson"].queryset = Salesperson.objects.filter(
                is_active=True
            )
        elif user and user_branch:
            # موظف عادي - فرعه فقط
            # التحقق من وجود فروع متعددة (مدير منطقة)
            if hasattr(user, "branches") and user.branches.exists():
                user_branches = user.branches.filter(is_active=True)
                self.fields["branch"].queryset = user_branches
                self.fields["salesperson"].queryset = Salesperson.objects.filter(
                    branch__in=user_branches, is_active=True
                )
            else:
                # فرعه فقط
                self.fields["branch"].queryset = Branch.objects.filter(
                    id=user_branch.id, is_active=True
                )
                self.fields["salesperson"].queryset = Salesperson.objects.filter(
                    branch=user_branch, is_active=True
                )
        else:
            # لا يوجد فرع - جميع الفروع والبائعين
            self.fields["branch"].queryset = Branch.objects.filter(is_active=True)
            self.fields["salesperson"].queryset = Salesperson.objects.filter(
                is_active=True
            )

        # تعيين الفرع الافتراضي
        active_branch = None

        if self.instance and self.instance.branch:
            # إذا كان هناك فرع محدد في المسودة
            active_branch = self.instance.branch
        elif user_branch:
            # أو استخدم فرع المستخدم كافتراضي
            active_branch = user_branch
            self.fields["branch"].initial = user_branch

        # تصفية البائعين - المدراء يرون جميع البائعين للسماح باختيار أي بائع
        if is_admin_user or is_main_branch_user:
            # مدير النظام أو الفرع الرئيسي - جميع البائعين النشطين
            # هذا يسمح لهم باختيار أي بائع من أي فرع
            self.fields["salesperson"].queryset = (
                Salesperson.objects.filter(is_active=True)
                .select_related("branch")
                .order_by("branch__name", "name")
            )
        elif active_branch:
            # المستخدمين العاديين - بائعين الفرع المحدد فقط
            self.fields["salesperson"].queryset = Salesperson.objects.filter(
                branch=active_branch, is_active=True
            )

        # حفظ حالة المستخدم للتحقق في clean
        self._is_admin_user = is_admin_user
        self._is_main_branch_user = is_main_branch_user

    def clean_customer(self):
        """
        ⚡ منع تغيير العميل بعد تحديده في المسودة
        """
        customer = self.cleaned_data.get("customer")

        # إذا كانت المسودة موجودة ولها عميل محدد مسبقاً
        if self.instance and self.instance.pk and self.instance.customer:
            # التحقق من محاولة التغيير
            if customer and customer.id != self.instance.customer.id:
                raise ValidationError(
                    "❌ لا يمكن تغيير العميل بعد تحديده. "
                    "رقم الطلب مرتبط بالعميل الأصلي. "
                    "احذف المسودة وأنشئ طلباً جديداً لتغيير العميل."
                )

        return customer

    def clean(self):
        """
        تحقق مخصص للتأكد من صحة العلاقة بين الفرع والبائع
        """
        cleaned_data = super().clean()
        branch = cleaned_data.get("branch")
        salesperson = cleaned_data.get("salesperson")
        customer = cleaned_data.get("customer")

        # ⚡ منع تغيير العميل بعد تحديده
        if self.instance and self.instance.pk and self.instance.customer:
            if customer and customer.id != self.instance.customer.id:
                raise ValidationError(
                    {
                        "customer": "لا يمكن تغيير العميل بعد تحديده. احذف المسودة وأنشئ طلباً جديداً."
                    }
                )

        # للمدراء: السماح باختيار أي بائع بغض النظر عن الفرع
        if getattr(self, "_is_admin_user", False) or getattr(
            self, "_is_main_branch_user", False
        ):
            # مدير النظام يمكنه اختيار أي بائع
            return cleaned_data

        # للمستخدمين العاديين: التحقق من أن البائع ينتمي للفرع المختار
        if branch and salesperson:
            if salesperson.branch_id != branch.id:
                self.add_error("salesperson", "يجب اختيار بائع من الفرع المحدد")

        return cleaned_data


class Step2OrderTypeForm(forms.ModelForm):
    """
    الخطوة 2: نوع الطلب
    """

    class Meta:
        model = DraftOrder
        fields = ["selected_type", "related_inspection", "related_inspection_type"]
        widgets = {
            "selected_type": forms.RadioSelect(
                attrs={"class": "form-check-input", "required": True}
            ),
            "related_inspection": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        customer = kwargs.pop("customer", None)
        super().__init__(*args, **kwargs)

        # ⚡ تصفية أنواع الطلبات لعرض النشطة فقط
        from .wizard_customization_models import WizardFieldOption

        active_order_types = WizardFieldOption.objects.filter(
            field_type="order_type", is_active=True
        ).values_list("value", "display_name")

        if active_order_types:
            # استخدام الأنواع النشطة فقط
            self.fields["selected_type"].choices = list(active_order_types)

        # تحميل المعاينات المرتبطة بالعميل
        if customer:
            self.fields["related_inspection"].queryset = Inspection.objects.filter(
                customer=customer
            ).order_by("-created_at")

            # ⚡ تصفية أنواع الطلبات المتاحة بناءً على نوع العميل
            if customer.customer_type:
                from customers.models import CustomerType

                try:
                    customer_type_obj = CustomerType.objects.get(
                        code=customer.customer_type
                    )
                    allowed_types = customer_type_obj.allowed_order_types or []
                    if allowed_types:  # إذا تم تحديد أنواع معينة (ليست قائمة فارغة)
                        current_choices = list(self.fields["selected_type"].choices)
                        # تصفية الخيارات الموجودة أصلاً في النموذج
                        filtered_choices = [
                            c for c in current_choices if c[0] in allowed_types
                        ]
                        if filtered_choices:
                            self.fields["selected_type"].choices = filtered_choices
                except CustomerType.DoesNotExist:
                    pass  # إذا لم يوجد نوع العميل، السماح بجميع الأنواع
        else:
            self.fields["related_inspection"].queryset = Inspection.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        selected_type = cleaned_data.get("selected_type")
        related_inspection = cleaned_data.get("related_inspection")
        related_inspection_type = cleaned_data.get("related_inspection_type")

        # التحقق من اختيار نوع الطلب
        if not selected_type:
            raise ValidationError("يجب اختيار نوع الطلب")

        # التحقق من اختيار المعاينة عندما تكون متاحة
        # فقط في أنواع الطلبات التي تتطلب معاينة (تركيب، تفصيل، إكسسوار)
        if selected_type in ["installation", "tailoring", "accessory"]:
            # التحقق من وجود معاينات متاحة
            available_inspections = self.fields["related_inspection"].queryset

            if available_inspections.exists():
                # يجب اختيار معاينة فعلية أو اختيار "طرف العميل"
                if (
                    not related_inspection
                    and related_inspection_type != "customer_side"
                ):
                    raise ValidationError(
                        {
                            "related_inspection": 'يجب اختيار معاينة مرتبطة أو تحديد "طرف العميل"'
                        }
                    )

        return cleaned_data


class Step3OrderItemForm(forms.ModelForm):
    """
    نموذج إضافة عنصر طلب
    """

    barcode = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "امسح الباركود أو أدخله يدوياً",
                "id": "barcode-input",
            }
        ),
        label="الباركود",
    )

    class Meta:
        model = DraftOrderItem
        fields = [
            "product",
            "quantity",
            "unit_price",
            "discount_percentage",
            "item_type",
            "notes",
        ]
        widgets = {
            "product": forms.Select(
                attrs={"class": "form-select product-select", "required": True}
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.001",
                    "step": "0.001",
                    "required": True,
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "required": True,
                    "readonly": True,  # السعر من النظام فقط
                    "style": "background-color: #e9ecef;",
                }
            ),
            "discount_percentage": forms.Select(
                choices=[(i, f"{i}%") for i in range(0, 16)],
                attrs={
                    "class": "form-select",
                },
            ),
            "item_type": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إعادة ترتيب الحقول
        self.order_fields(
            [
                "barcode",
                "product",
                "quantity",
                "unit_price",
                "discount_percentage",
                "item_type",
                "notes",
            ]
        )

    def order_fields(self, field_order):
        """إعادة ترتيب الحقول"""
        self.fields = {
            key: self.fields[key] for key in field_order if key in self.fields
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity and quantity <= 0:
            raise ValidationError("الكمية يجب أن تكون أكبر من صفر")
        return quantity

    def clean_unit_price(self):
        unit_price = self.cleaned_data.get("unit_price")
        product = self.cleaned_data.get("product")

        # السعر يأتي من المنتج تلقائياً
        if product and product.price:
            return product.price

        if unit_price and unit_price < 0:
            raise ValidationError("السعر لا يمكن أن يكون سالباً")
        return unit_price


class Step4InvoicePaymentForm(forms.ModelForm):
    """
    الخطوة 4: تفاصيل المرجع والدفع
    """

    class Meta:
        model = DraftOrder
        fields = [
            "invoice_number",
            "invoice_number_2",
            "invoice_number_3",
            "contract_number",
            "contract_number_2",
            "contract_number_3",
            "invoice_image",
            "payment_method",
            "paid_amount",
            "payment_notes",
        ]
        widgets = {
            "invoice_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "رقم المرجع الرئيسي",
                    "id": "invoice_number_field",
                }
            ),
            "invoice_number_2": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "رقم مرجع إضافي (اختياري)",
                }
            ),
            "invoice_number_3": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "رقم مرجع إضافي (اختياري)",
                }
            ),
            "contract_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "رقم العقد الرئيسي"}
            ),
            "contract_number_2": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "رقم عقد إضافي (اختياري)",
                }
            ),
            "contract_number_3": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "رقم عقد إضافي (اختياري)",
                }
            ),
            "invoice_image": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                    "id": "invoice_image_field",
                }
            ),
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "paid_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "value": "0",
                }
            ),
            "payment_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "ملاحظات الدفع (اختياري)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.draft_order = kwargs.pop("draft_order", None)
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # جعل رقم المرجع الرئيسي إجبارياً
        self.fields["invoice_number"].required = True
        self.fields["invoice_number"].widget.attrs["required"] = "required"

        # جعل صورة الفاتورة إجبارية فقط إذا لم توجد صور محفوظة
        if self.draft_order and self.draft_order.selected_type != "inspection":
            # التحقق من وجود صور محفوظة (في المسودة أو الطلب الأصلي)
            has_saved_images = (self.draft_order.invoice_image) or (
                self.draft_order.invoice_images_new.exists()
            )

            # في حالة التعديل، نتحقق من الطلب الأصلي أيضاً
            editing_order_id = None
            if hasattr(self, "request") and self.request:
                editing_order_id = self.request.session.get("editing_order_id")

            if not has_saved_images and editing_order_id:
                from orders.models import Order

                try:
                    original_order = Order.objects.get(pk=editing_order_id)
                    if original_order.invoice_image:
                        has_saved_images = True
                except Order.DoesNotExist:
                    pass

            # إذا لم توجد صور محفوظة، الحقل إجباري
            if not has_saved_images:
                self.fields["invoice_image"].required = True
                self.fields["invoice_image"].widget.attrs["required"] = "required"
            else:
                # إذا وجدت صور، الحقل اختياري
                self.fields["invoice_image"].required = False
                if "required" in self.fields["invoice_image"].widget.attrs:
                    del self.fields["invoice_image"].widget.attrs["required"]

    def clean_invoice_number(self):
        """التحقق من رقم المرجع الرئيسي وعدم تكراره للعميل نفسه مع نفس النوع"""
        invoice_number = self.cleaned_data.get("invoice_number")

        if not invoice_number or not invoice_number.strip():
            raise ValidationError("رقم المرجع الرئيسي إجباري")

        invoice_number = invoice_number.strip()

        # في وضع التعديل: السماح بنفس رقم الفاتورة للطلب الأصلي
        editing_order_id = None
        if hasattr(self, "request") and self.request:
            editing_order_id = self.request.session.get("editing_order_id")

        # التحقق من تكرار رقم المرجع للعميل نفسه مع نفس نوع الطلب
        if (
            self.draft_order
            and self.draft_order.customer
            and self.draft_order.selected_type
        ):
            from django.db.models import Q

            from orders.models import Order

            existing_orders = Order.objects.filter(
                customer=self.draft_order.customer
            ).filter(
                Q(invoice_number=invoice_number)
                | Q(invoice_number_2=invoice_number)
                | Q(invoice_number_3=invoice_number)
            )

            # استبعاد الطلب الذي يتم تعديله
            if editing_order_id:
                existing_orders = existing_orders.exclude(pk=editing_order_id)

            # التحقق من وجود طلب بنفس النوع
            for existing_order in existing_orders:
                try:
                    existing_types = existing_order.get_selected_types_list()
                    if self.draft_order.selected_type in existing_types:
                        raise ValidationError(
                            f'⚠️ رقم المرجع "{invoice_number}" مستخدم مسبقاً لهذا العميل في طلب من نفس النوع (رقم الطلب: {existing_order.order_number})'
                        )
                except ValidationError:
                    raise
                except Exception:
                    pass

        return invoice_number

    def clean_invoice_image(self):
        """التحقق من صورة الفاتورة"""
        invoice_image = self.cleaned_data.get("invoice_image")

        # صورة الفاتورة إجبارية لجميع الأنواع ما عدا المعاينة
        if self.draft_order and self.draft_order.selected_type != "inspection":
            # التحقق من وجود صورة محفوظة أو صورة جديدة
            has_saved_images = (self.draft_order.invoice_image) or (
                self.draft_order.invoice_images_new.exists()
            )

            # في حالة التعديل، نتحقق من الطلب الأصلي أيضاً
            editing_order_id = None
            if hasattr(self, "request") and self.request:
                editing_order_id = self.request.session.get("editing_order_id")

            if not has_saved_images and editing_order_id:
                from orders.models import Order

                try:
                    original_order = Order.objects.get(pk=editing_order_id)
                    if original_order.invoice_image:
                        has_saved_images = True
                except Order.DoesNotExist:
                    pass

            # إذا لم توجد صور محفوظة ولم يتم رفع صورة جديدة
            if not invoice_image and not has_saved_images:
                raise ValidationError("يجب إرفاق صورة الفاتورة على الأقل")

        return invoice_image

    def clean_paid_amount(self):
        paid_amount = self.cleaned_data.get("paid_amount") or Decimal("0")

        # السماح بدفع مبلغ يتجاوز الإجمالي
        if self.draft_order:
            final_total = self.draft_order.final_total or Decimal("0")

            # التحقق من الحد الأدنى للدفع (50%)
            # لعملاء الجملة: يسمح بعدم الدفع (0) أو دفع 50% كحد أدنى
            # لغيرهم: يجب دفع 50% كحد أدنى
            minimum_payment = final_total * Decimal("0.5")

            is_wholesale = False
            if (
                self.draft_order.customer
                and self.draft_order.customer.customer_type == "wholesale"
            ):
                is_wholesale = True

            if is_wholesale:
                # عميل جملة - يسمح بـ 0 أو >= 50%
                if paid_amount > 0 and paid_amount < minimum_payment:
                    raise ValidationError(
                        f"💡 عميل جملة: يجب دفع 50% على الأقل من القيمة الإجمالية في حال الدفع (أو ترك المبلغ 0). "
                        f"المبلغ المطلوب: {minimum_payment:.2f} جنيه (المدفوع: {paid_amount:.2f} جنيه)"
                    )
            else:
                # عميل عادي - يجب دفع >= 50%
                if paid_amount < minimum_payment:
                    raise ValidationError(
                        f"💡 يجب دفع 50% على الأقل من القيمة الإجمالية للمتابعة. "
                        f"المبلغ المطلوب: {minimum_payment:.2f} جنيه (المدفوع: {paid_amount:.2f} جنيه)"
                    )

        return paid_amount


# Note: Forms for curtains, fabrics, and accessories are now handled via AJAX
# and use the contract_models directly
