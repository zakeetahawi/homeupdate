import json
from datetime import timedelta

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import Branch, Salesperson
from inspections.models import Inspection

from .models import Order, OrderItem, Payment


class ProductSelectWidget(forms.Select):
    """Widget مخصص لإضافة data-price للمنتجات مع تحسين الأداء"""

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )

        if value:
            try:
                from inventory.models import Product

                # استخدام cache لتجنب استعلامات متكررة
                cache_key = f"product_price_{value}"
                from django.core.cache import cache

                cached_price = cache.get(cache_key)

                if cached_price is None:
                    product = Product.objects.only("price").get(pk=value)
                    cached_price = str(product.price)
                    cache.set(cache_key, cached_price, 300)  # cache for 5 minutes

                option["attrs"]["data-price"] = cached_price
            except Product.DoesNotExist:
                pass

        return option


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity", "unit_price", "notes"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-control product-select"}),
            "quantity": forms.TextInput(
                attrs={
                    "class": "form-control item-quantity",
                    "type": "number",
                    "min": "0.001",
                    "step": "0.001",
                    "placeholder": "مثال: 4.25",
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control item-price", "min": "0", "step": "0.01"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تحسين: لا نقوم بتحميل جميع المنتجات هنا لتجنب N+1 queries
        # سيتم التعامل مع هذا في الـ widget المخصص
        if "product" in self.fields:
            # استخدام ModelChoiceField بدلاً من تحميل جميع المنتجات
            from inventory.models import Product

            self.fields["product"].queryset = Product.objects.select_related(
                "category"
            ).only("id", "name", "price", "category__name")

            # إصلاح مشكلة ModelChoiceIteratorValue
            if hasattr(self.fields["product"], "widget") and hasattr(
                self.fields["product"].widget, "choices"
            ):
                # تأكد من أن الخيارات صحيحة
                try:
                    self.fields["product"].widget.choices = self.fields[
                        "product"
                    ].choices
                except Exception:
                    # إذا فشل، استخدم queryset مباشرة
                    pass

    def clean_quantity(self):
        """تنظيف وتأكد من صحة الكمية"""
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None:
            try:
                # تحويل إلى Decimal للتأكد من الدقة
                from decimal import Decimal

                quantity = Decimal(str(quantity))
                if quantity < 0:
                    raise forms.ValidationError("الكمية لا يمكن أن تكون سالبة")
                return quantity
            except (ValueError, TypeError):
                raise forms.ValidationError("يرجى إدخال قيمة صحيحة للكمية")
        return quantity

    def save(self, commit=True):
        instance = super().save(commit=False)

        # تعيين قيمة افتراضية لـ item_type إذا لم تكن موجودة
        if not instance.item_type:
            instance.item_type = "product"  # أو أي قيمة افتراضية مناسبة

        if commit:
            instance.save()

        return instance


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "payment_method", "reference_number", "notes"]
        labels = {
            "reference_number": "رقم الفاتورة",
        }
        widgets = {
            "amount": forms.NumberInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "payment_method": forms.Select(
                attrs={"class": "form-select form-select-sm"}
            ),
            "reference_number": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
        }


# Formset for managing multiple order items
OrderItemFormSet = forms.inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True,
)


class OrderForm(forms.ModelForm):
    # Override status choices to match requirements
    STATUS_CHOICES = [
        ("normal", "عادي"),
        ("vip", "VIP"),
    ]

    # Override order type choices to match requirements
    ORDER_TYPE_CHOICES = [
        ("product", "منتج"),
        ("service", "خدمة"),
    ]

    # Override status field to use our custom choices
    status = forms.ChoiceField(
        choices=Order.STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
        required=False,
    )

    # This is the correct field definition for the order types.
    selected_types = forms.ChoiceField(
        choices=Order.ORDER_TYPES,
        required=True,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    salesperson = forms.ModelChoiceField(
        queryset=Salesperson.objects.filter(is_active=True),
        label="البائع",
        required=True,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    # The following hidden fields were causing the issue by redefining 'selected_types'.
    # This has been removed.

    # Hidden fields for delivery
    delivery_type = forms.CharField(widget=forms.HiddenInput(), required=False)

    delivery_address = forms.CharField(widget=forms.HiddenInput(), required=False)

    # حقل المعاينة المرتبطة للخدمات الأخرى
    related_inspection = forms.ChoiceField(
        choices=[("customer_side", "طرف العميل"), ("", "اختر العميل أولاً")],
        required=False,
        widget=forms.Select(
            attrs={
                "class": "form-select form-select-sm",
                "data-placeholder": "اختر المعاينة المرتبطة",
            }
        ),
        label="معاينة مرتبطة",
        help_text="اختر المعاينة المرتبطة بهذا الطلب (اختياري)",
    )

    class Meta:
        model = Order
        fields = [
            "customer",
            "status",
            "invoice_number",
            "contract_number",
            "contract_file",
            "branch",
            "tracking_status",
            "notes",
            "selected_types",
            "delivery_type",
            "delivery_address",
            "salesperson",
            "invoice_number_2",
            "invoice_number_3",
            "contract_number_2",
            "contract_number_3",
        ]
        widgets = {
            "customer": forms.Select(
                attrs={
                    "class": "form-select form-select-sm select2-customer",
                    "data-placeholder": "اختر العميل",
                    "data-allow-clear": "true",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-select form-select-sm",
                    "data-help": "حدد وضع العميل (عادي أو VIP)",
                }
            ),
            "tracking_status": forms.Select(
                attrs={"class": "form-select form-select-sm"}
            ),
            "invoice_number": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "invoice_number_2": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "invoice_number_3": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "branch": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "contract_number": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "contract_number_2": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "contract_number_3": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "contract_file": forms.FileInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "accept": ".pdf",
                    "data-help": "يجب أن يكون الملف من نوع PDF وأقل من 50 ميجابايت",
                }
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control notes-field", "rows": 6}
            ),
            "delivery_type": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "delivery_address": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "expected_delivery_date": forms.DateInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "type": "date",
                    "readonly": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        customer = kwargs.pop("customer", None)
        super().__init__(*args, **kwargs)

        # حفظ العميل الأولي للاستخدام في clean_customer
        self.initial_customer = customer

        # تقييد البائعين حسب الفرع إذا لم يكن المستخدم مديراً (محسن)
        if user and not user.is_superuser and user.branch:
            from django.core.cache import cache

            cache_key = f"branch_salespersons_{user.branch.id}"
            salesperson_queryset = cache.get(cache_key)

            if salesperson_queryset is None:
                salesperson_queryset = (
                    Salesperson.objects.filter(is_active=True, branch=user.branch)
                    .select_related("user", "branch")
                    .only(
                        "id",
                        "name",
                        "employee_number",
                        "user__first_name",
                        "user__last_name",
                        "user__username",
                        "branch__name",
                    )
                )

                # تخزين مؤقت لمدة 15 دقيقة
                cache.set(cache_key, salesperson_queryset, 900)

            self.fields["salesperson"].queryset = salesperson_queryset

        # تقييد العملاء حسب دور المستخدم والفرع (محسن)
        if user:
            from django.core.cache import cache

            from customers.models import Customer

            # إنشاء مفتاح تخزين مؤقت بناءً على المستخدم
            cache_key = f'user_customers_{user.id}_{user.branch_id if user.branch else "no_branch"}'
            customer_queryset = cache.get(cache_key)

            if customer_queryset is None:
                if user.is_superuser:
                    # المدير العام يرى جميع العملاء
                    customer_queryset = (
                        Customer.objects.filter(status="active")
                        .select_related("branch")
                        .only("id", "name", "code", "phone", "branch__name")
                    )
                elif user.is_region_manager:
                    # مدير المنطقة يرى عملاء الفروع التي يديرها
                    managed_branches = user.managed_branches.all()
                    customer_queryset = (
                        Customer.objects.filter(
                            status="active", branch__in=managed_branches
                        )
                        .select_related("branch")
                        .only("id", "name", "code", "phone", "branch__name")
                    )
                elif user.is_branch_manager or user.is_salesperson:
                    # مدير الفرع والبائع يرون عملاء فرعهم فقط
                    if user.branch:
                        customer_queryset = (
                            Customer.objects.filter(status="active", branch=user.branch)
                            .select_related("branch")
                            .only("id", "name", "code", "phone", "branch__name")
                        )
                    else:
                        customer_queryset = Customer.objects.none()
                else:
                    # المستخدمون الآخرون لا يرون أي عملاء
                    customer_queryset = Customer.objects.none()

                # تخزين مؤقت لمدة 10 دقائق
                cache.set(cache_key, customer_queryset, 600)

            # إذا تم تمرير عميل محدد (من بطاقة العميل)، إضافته للقائمة حتى لو كان من فرع آخر
            if customer and customer.pk:
                # التحقق من صلاحية المستخدم لإنشاء طلب لهذا العميل
                from customers.permissions import can_user_create_order_for_customer

                if can_user_create_order_for_customer(user, customer):
                    # إضافة العميل المحدد للقائمة إذا لم يكن موجوداً
                    if not customer_queryset.filter(pk=customer.pk).exists():
                        from django.db.models import Q

                        # استخدام OR condition بدلاً من union لتجنب مشاكل QuerySet
                        customer_queryset = Customer.objects.filter(
                            Q(pk__in=customer_queryset.values_list("pk", flat=True))
                            | Q(pk=customer.pk)
                        ).filter(status="active")

            self.fields["customer"].queryset = customer_queryset.order_by("name")

            # تعيين العميل كقيمة أولية إذا تم تمريره
            if customer and customer.pk:
                self.fields["customer"].initial = customer.pk
                # جعل حقل العميل للقراءة فقط إذا تم تمريره من الرابط
                # ملاحظة: لا نستخدم disabled لأنه يمنع إرسال القيمة
                self.fields["customer"].widget.attrs["readonly"] = True

        # تعيين خيارات المعاينة المرتبطة للخدمات الأخرى (محسن مع دوال مساعدة)
        if customer:
            # إضافة خيار "طرف العميل" في بداية القائمة
            inspection_choices = [("customer_side", "طرف العميل")]

            # استخدام دالة التخزين المؤقت المحسنة
            from .cache_utils import get_cached_customer_inspections

            cached_inspections = get_cached_customer_inspections(customer.id, limit=10)

            # إضافة معاينات العميل كروابط
            for inspection_data in cached_inspections:
                inspection_choices.append(
                    (
                        str(inspection_data["id"]),
                        f"{inspection_data['customer_name']} - {inspection_data['contract_number'] or f'معاينة {inspection_data['id']}'} - {inspection_data['created_at']}",
                    )
                )

            self.fields["related_inspection"].choices = inspection_choices
        else:
            # إذا لم يتم تحديد عميل، إظهار رسالة فقط بدون أي معاينات
            self.fields["related_inspection"].choices = [("", "اختر العميل أولاً")]

        # Make all fields optional initially
        for field_name in self.fields:
            self.fields[field_name].required = False

        # Make order_number read-only but visible
        if "order_number" in self.fields:
            self.fields["order_number"].widget.attrs["readonly"] = True
            self.fields["order_number"].widget.attrs[
                "class"
            ] = "form-control form-control-sm"
        else:
            # Add order_number field if it doesn't exist
            self.fields["order_number"] = forms.CharField(
                required=False,
                widget=forms.TextInput(
                    attrs={
                        "class": "form-control form-control-sm",
                        "readonly": True,
                        "placeholder": "سيتم إنشاؤه تلقائياً",
                    }
                ),
                label="رقم الطلب",
            )

        # Make invoice_number and contract_number not required initially
        self.fields["invoice_number"].required = False
        self.fields["contract_number"].required = False
        self.fields["contract_number_2"].required = False
        self.fields["contract_number_3"].required = False

        # Set branch to user's branch if available
        if user and hasattr(user, "branch") and user.branch:
            self.fields["branch"].initial = user.branch
            # If not superuser, limit branch choices to user's branch
            if not user.is_superuser:
                self.fields["branch"].queryset = Branch.objects.filter(
                    id=user.branch.id
                )
                self.fields["branch"].widget.attrs["readonly"] = True

    def clean_customer(self):
        """تنظيف حقل العميل - للتعامل مع العميل المحدد مسبقاً"""
        customer = self.cleaned_data.get("customer")

        # إذا لم يتم إرسال قيمة العميل، استخدم القيمة الأولية المحفوظة
        if not customer and hasattr(self, "initial_customer") and self.initial_customer:
            customer = self.initial_customer
            print(f"DEBUG: استخدام العميل الأولي: {customer}")
        elif not customer and self.initial.get("customer"):
            try:
                from customers.models import Customer

                customer = Customer.objects.get(pk=self.initial["customer"])
                print(f"DEBUG: العثور على العميل من initial: {customer}")
            except Customer.DoesNotExist:
                print("DEBUG: لم يتم العثور على العميل في initial")
                pass

        if not customer:
            raise forms.ValidationError("يجب اختيار عميل للطلب")

        return customer

    def clean_related_inspection(self):
        """تنظيف حقل المعاينة المرتبطة"""
        value = self.cleaned_data.get("related_inspection")

        if value == "customer_side":
            return "customer_side"
        elif value and value != "":
            try:
                # التحقق من وجود المعاينة في قاعدة البيانات
                inspection = Inspection.objects.get(id=value)
                return str(inspection.id)
            except (Inspection.DoesNotExist, ValueError):
                raise forms.ValidationError("معاينة غير صحيحة")
        else:
            return value

    def clean(self):
        cleaned_data = super().clean()
        selected_type = cleaned_data.get("selected_types")

        # رسائل تصحيح (يمكن إزالتها في الإنتاج)
        # print(f"🔍 DEBUG: selected_type = {selected_type}")
        # print(f"🔍 DEBUG: selected_type type = {type(selected_type)}")
        # print(f"🔍 DEBUG: all cleaned_data keys = {list(cleaned_data.keys())}")

        # Required fields validation
        required_fields = ["customer", "salesperson", "branch"]
        for field in required_fields:
            if not cleaned_data.get(field):
                self.add_error(field, f"هذا الحقل مطلوب")

        if not selected_type:
            self.add_error("selected_types", "يجب اختيار نوع للطلب")
            return cleaned_data  # Return early if no type is selected

        # التحقق من رقم الفاتورة (مطلوب لجميع الأنواع عدا المعاينة)
        invoice_number = cleaned_data.get("invoice_number")

        if selected_type != "inspection":  # رقم الفاتورة غير مطلوب للمعاينة
            if not invoice_number or not invoice_number.strip():
                self.add_error(
                    "invoice_number", "رقم الفاتورة مطلوب لهذا النوع من الطلبات"
                )

        # التحقق من رقم العقد وملف العقد للتركيب والتفصيل والإكسسوار
        contract_required_types = ["installation", "tailoring", "accessory"]
        if selected_type in contract_required_types:
            contract_number = cleaned_data.get("contract_number")
            if not contract_number or not contract_number.strip():
                self.add_error(
                    "contract_number", "رقم العقد مطلوب لهذا النوع من الطلبات"
                )

            # contract_file is an in-memory file object, so we check for it directly
            if "contract_file" not in self.files:
                self.add_error("contract_file", "ملف العقد مطلوب لهذا النوع من الطلبات")

        # التحقق من المعاينة المرتبطة للخدمات الأخرى (غير المعاينة) فقط
        if selected_type != "inspection":
            related_inspection_value = cleaned_data.get("related_inspection")
            if related_inspection_value and related_inspection_value != "customer_side":
                try:
                    # التحقق من أن القيمة رقم صحيح
                    inspection_id = int(related_inspection_value)
                    inspection = Inspection.objects.get(id=inspection_id)
                except (ValueError, Inspection.DoesNotExist):
                    self.add_error("related_inspection", "معاينة غير صحيحة")
        else:
            # للمعاينات: إفراغ قيمة المعاينة المرتبطة
            cleaned_data["related_inspection"] = ""
        return cleaned_data

    def save(self, commit=True):
        # Get cleaned values before the instance is saved
        selected_type = self.cleaned_data.get("selected_types")
        status = self.cleaned_data.get("status")

        # Create the instance but don't commit to DB yet
        instance = super().save(commit=False)

        # تعيين وضع الطلب تلقائياً للمعاينة
        if selected_type == "inspection":
            instance.status = "normal"  # تعيين وضع الطلب تلقائياً إلى "عادي" للمعاينة
            status = "normal"  # تحديث المتغير للاستخدام في الحسابات

        # --- Calculate and set Expected Delivery Date using the new system ---
        # تحديد نوع الطلب ونوع الخدمة
        order_type = "vip" if status == "vip" else "normal"
        service_type = selected_type  # نوع الخدمة هو نفس النوع المختار

        # الحصول على عدد الأيام من الإعدادات الجديدة
        from orders.models import DeliveryTimeSettings

        days_to_add = DeliveryTimeSettings.get_delivery_days(
            order_type=order_type, service_type=service_type
        )

        # حساب التاريخ المتوقع
        instance.expected_delivery_date = timezone.now().date() + timedelta(
            days=days_to_add
        )

        # Now, modify the instance with the other transformed data
        if selected_type:
            # Save selected_types as JSON
            instance.selected_types = json.dumps([selected_type])

            # Set order_type for compatibility
            if selected_type in ["accessory", "products"]:
                instance.order_type = "product"
            else:
                instance.order_type = "service"

            # Set delivery options automatically
            if selected_type == "tailoring":
                instance.delivery_type = "branch"
                instance.delivery_address = ""
            elif selected_type == "installation":
                instance.delivery_type = "home"
                if not instance.delivery_address:
                    instance.delivery_address = "سيتم تحديد العنوان لاحقاً"
            elif selected_type == "products":
                # للمنتجات، يمكن التسليم في الفرع أو المنزل حسب الحاجة
                instance.delivery_type = "branch"  # افتراضي
                instance.delivery_address = ""
            else:  # accessory and inspection
                instance.delivery_type = "branch"
                instance.delivery_address = ""

            # معالجة related_inspection للخدمات الأخرى (غير المعاينة)
            if selected_type != "inspection":
                related_inspection_value = self.cleaned_data.get("related_inspection")
                if related_inspection_value == "customer_side":
                    instance.related_inspection = None
                    instance.related_inspection_type = "customer_side"
                elif related_inspection_value and related_inspection_value != "":
                    try:
                        inspection = Inspection.objects.get(id=related_inspection_value)
                        instance.related_inspection = inspection
                        instance.related_inspection_type = "inspection"
                    except (Inspection.DoesNotExist, ValueError):
                        # إذا لم يتم العثور على المعاينة، تعيين كطرف العميل
                        instance.related_inspection = None
                        instance.related_inspection_type = "customer_side"
                else:
                    # إذا لم يتم اختيار معاينة، تعيين كطرف العميل
                    instance.related_inspection = None
                    instance.related_inspection_type = "customer_side"
            else:
                # للمعاينات: لا توجد معاينة مرتبطة
                instance.related_inspection = None
                instance.related_inspection_type = None

        if commit:
            instance.save()
            self.save_m2m()  # Important for inline formsets if any

        return instance


# ==================== نماذج تعديل الطلب المتقدمة 🎯 ====================


class OrderEditForm(forms.ModelForm):
    """نموذج تعديل الطلب الأساسي مع عناصر الطلب"""

    class Meta:
        model = Order
        fields = [
            "customer",
            "branch",
            "salesperson",
            "selected_types",
            "invoice_number",
            "contract_number",
            "invoice_number_2",
            "contract_number_2",
            "notes",
            "total_amount",
            "paid_amount",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-control select2"}),
            "branch": forms.Select(attrs={"class": "form-control"}),
            "salesperson": forms.Select(attrs={"class": "form-control select2"}),
            "selected_types": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "readonly": True,
                }
            ),
            "invoice_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "رقم الفاتورة"}
            ),
            "contract_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "رقم العقد"}
            ),
            "invoice_number_2": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "رقم الفاتورة 2"}
            ),
            "contract_number_2": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "رقم العقد 2"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "ملاحظات الطلب",
                }
            ),
            "total_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "readonly": True,
                }
            ),
            "paid_amount": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "step": "0.01"}
            ),
        }
        labels = {
            "customer": "العميل",
            "branch": "الفرع",
            "salesperson": "البائع",
            "selected_types": "نوع الطلب",
            "invoice_number": "رقم الفاتورة",
            "contract_number": "رقم العقد",
            "invoice_number_2": "رقم الفاتورة 2",
            "contract_number_2": "رقم العقد 2",
            "notes": "ملاحظات الطلب",
            "total_amount": "إجمالي المبلغ",
            "paid_amount": "المبلغ المدفوع",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تخصيص الحقول
        from customers.models import Customer

        self.fields["customer"].queryset = Customer.objects.all()
        self.fields["branch"].queryset = Branch.objects.all()
        self.fields["salesperson"].queryset = Salesperson.objects.all()

        # إضافة help text
        self.fields["selected_types"].help_text = "نوع الطلب لا يمكن تعديله بعد الإنشاء"
        self.fields["total_amount"].help_text = "يتم حساب المبلغ تلقائياً من عناصر الطلب"

        # تعطيل بعض الحقول
        self.fields["selected_types"].widget.attrs["readonly"] = True
        self.fields["total_amount"].widget.attrs["readonly"] = True

        # تحويل selected_types من JSON إلى نص قابل للقراءة
        if self.instance and self.instance.selected_types:
            try:
                import json

                types_list = json.loads(self.instance.selected_types)
                types_display = []
                type_mapping = {
                    "inspection": "معاينة",
                    "installation": "تركيب",
                    "fabric": "أقمشة",
                    "accessory": "إكسسوار",
                    "tailoring": "تفصيل",
                    "transport": "نقل",
                }
                for t in types_list:
                    types_display.append(type_mapping.get(t, t))
                self.fields["selected_types"].initial = " + ".join(types_display)
            except:
                self.fields["selected_types"].initial = self.instance.selected_types

    def clean(self):
        cleaned_data = super().clean()
        total_amount = float(cleaned_data.get("total_amount", 0) or 0)
        paid_amount = float(cleaned_data.get("paid_amount", 0) or 0)

        # السماح بأن يكون المبلغ المدفوع أقل من الإجمالي (مديونية)
        # التحقق فقط من أن المبلغ المدفوع لا يكون سالب
        if paid_amount < 0:
            raise forms.ValidationError("المبلغ المدفوع لا يمكن أن يكون سالباً")

        return cleaned_data


class OrderItemEditForm(OrderItemForm):
    """نموذج مخصص لتعديل عناصر الطلب"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تحسين queryset للمنتجات في التعديل
        if "product" in self.fields:
            from inventory.models import Product

            self.fields["product"].queryset = Product.objects.select_related(
                "category"
            ).only("id", "name", "price", "category__name")

            # إصلاح القيمة الأولية للمنتج
            if self.instance and self.instance.pk and self.instance.product:
                self.fields["product"].initial = self.instance.product.id

            # إصلاح القيمة الأولية للكمية
            if self.instance and self.instance.pk and self.instance.quantity:
                self.fields["quantity"].initial = (
                    self.instance.get_clean_quantity_display()
                )


# تحديث OrderItemFormSet للتعديل
OrderItemEditFormSet = forms.inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemEditForm,
    extra=0,  # لا نريد عناصر إضافية فارغة في التعديل
    can_delete=True,
    min_num=0,  # السماح بحذف جميع العناصر مؤقتاً
    validate_min=False,
    fk_name="order",  # تحديد اسم العلاقة
)
