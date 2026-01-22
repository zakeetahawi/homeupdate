import uuid
from datetime import datetime

from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from accounts.models import Branch, User
from core.soft_delete import SoftDeleteMixin

from .managers import ProductManager


class Category(models.Model):
    """
    Model for product categories
    """

    name = models.CharField(_("اسم الفئة"), max_length=100)
    description = models.TextField(_("الوصف"), blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("الفئة الأب"),
    )

    class Meta:
        verbose_name = _("فئة")
        verbose_name_plural = _("الفئات")
        ordering = ["name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} - {self.name}"
        return self.name

    def get_ancestors(self, include_self=False):
        """الحصول على جميع أسلاف الفئة"""
        ancestors = []
        current = self
        if include_self:
            ancestors.append(current)
        while current.parent:
            ancestors.append(current.parent)
            current = current.parent
        return ancestors

    def get_total_products_count(self):
        """الحصول على العدد الإجمالي للمنتجات في الفئة وجميع فئاتها الفرعية"""
        total_count = self.products.count()

        # إضافة عدد المنتجات في الفئات الفرعية
        for child in self.children.all():
            total_count += child.get_total_products_count()

        return total_count


class Product(SoftDeleteMixin, models.Model):
    """
    Model for products
    """

    UNIT_CHOICES = [
        ("piece", _("قطعة")),
        ("kg", _("كيلوجرام")),
        ("gram", _("جرام")),
        ("liter", _("لتر")),
        ("meter", _("متر")),
        ("box", _("علبة")),
        ("pack", _("عبوة")),
        ("dozen", _("دستة")),
        ("roll", _("لفة")),
        ("sheet", _("ورقة")),
    ]

    CURRENCY_CHOICES = [
        ("EGP", _("جنيه مصري")),
        ("SAR", _("ريال سعودي")),
        ("USD", _("دولار أمريكي")),
        ("EUR", _("يورو")),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )  # زيادة من 50 إلى 100 حرف
    price = models.DecimalField(
        _("السعر القطاعي"),
        max_digits=10,
        decimal_places=2,
        help_text=_("سعر التجزئة للمنتج"),
    )
    wholesale_price = models.DecimalField(
        _("سعر الجملة"),
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("سعر الجملة للمنتج"),
    )
    currency = models.CharField(
        _("العملة"), max_length=3, choices=CURRENCY_CHOICES, default="EGP"
    )
    unit = models.CharField(
        _("الوحدة"), max_length=10, choices=UNIT_CHOICES, default="piece"
    )
    category = models.ForeignKey(
        "Category",
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name=_("الفئة"),
        null=True,
    )
    description = models.TextField(_("الوصف"), blank=True)
    minimum_stock = models.PositiveIntegerField(_("الحد الأدنى للمخزون"), default=0)
    # نوع القماش والعرض
    material = models.CharField(
        _("Material"),
        max_length=100,
        blank=True,
        default="",
        help_text=_("نوع الخامة مثل: Linen, Cotton, Polyester"),
    )
    width = models.CharField(
        _("Width"),
        max_length=50,
        blank=True,
        default="",
        help_text=_("عرض القماش مثل: 280 cm, 140 cm"),
    )
    # QR Code Cache - تخزين رمز QR لتحسين الأداء
    qr_code_base64 = models.TextField(_("رمز QR (مخزن)"), blank=True, null=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    objects = ProductManager()

    class Meta:
        verbose_name = _("منتج")
        verbose_name_plural = _("منتجات")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name", "code"]),
            models.Index(fields=["category"]),
            models.Index(fields=["created_at"]),
            # NEW Performance Indexes
            models.Index(fields=["code"], name="product_code_idx"),
            models.Index(fields=["name"], name="product_name_idx"),
            models.Index(fields=["category", "created_at"], name="product_cat_crt_idx"),
            models.Index(fields=["price"], name="product_price_idx"),
        ]

    def __str__(self):
        return self.name

    @cached_property
    def current_stock(self):
        """الحصول على مستوى المخزون الحالي (مجموع جميع المستودعات)"""
        from django.db.models import OuterRef, Subquery

        warehouses = Warehouse.objects.filter(is_active=True)

        total_stock = 0
        latest_transactions = StockTransaction.objects.filter(
            product=self, warehouse=OuterRef("pk")
        ).order_by("-transaction_date", "-id")

        for warehouse in warehouses.annotate(
            latest_balance=Subquery(latest_transactions.values("running_balance")[:1])
        ):
            if warehouse.latest_balance is not None:
                total_stock += warehouse.latest_balance

        return total_stock

    @property
    def is_available(self):
        """التحقق مما إذا كان المنتج متوفراً"""
        return self.current_stock > 0

    @property
    def stock_status(self):
        """الحصول على حالة المخزون"""
        current = self.current_stock
        if current <= 0:
            return _("غير متوفر")
        elif current <= self.minimum_stock:
            return _("مخزون منخفض")
        return _("متوفر")

    @property
    def warehouses_with_stock(self):
        """الحصول على أسماء المستودعات التي تحتوي على المنتج"""
        from django.db.models import Max

        # الحصول على المستودعات النشطة
        warehouses = []
        from .models import Warehouse

        for warehouse in Warehouse.objects.filter(is_active=True):
            last_trans = (
                self.transactions.filter(warehouse=warehouse)
                .order_by("-transaction_date", "-id")
                .first()
            )

            if last_trans and last_trans.running_balance > 0:
                warehouses.append(warehouse.name)

        if warehouses:
            return ", ".join(warehouses[:3]) + ("..." if len(warehouses) > 3 else "")
        return ""

    def get_unit_display(self):
        """إرجاع عرض الوحدة"""
        return dict(self.UNIT_CHOICES).get(self.unit, self.unit)

    def generate_qr(self, force=False):
        """
        توليد رمز QR وتخزينه في الحقل qr_code_base64
        يعيد True إذا تم التوليد، False إذا لم يكن مطلوباً
        """
        if not self.code:
            return False

        if self.qr_code_base64 and not force:
            return False  # QR موجود مسبقاً ولا يوجد إجبار

        try:
            import base64
            from io import BytesIO

            import qrcode
            from django.conf import settings

            # Use Cloudflare Worker URL for fast QR access
            base_url = getattr(
                settings, "CLOUDFLARE_WORKER_URL", "https://qr.elkhawaga.uk"
            )
            qr_url = f"{base_url}/{self.code}"

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            qr_img.save(buffer, format="PNG")
            self.qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            return True
        except Exception:
            return False

    def save(self, *args, **kwargs):
        # توليد QR تلقائياً إذا كان هناك كود ولم يكن موجوداً
        if self.code and not self.qr_code_base64:
            self.generate_qr()

        # تنظيف ذاكرة التخزين المؤقت عند حفظ المنتج
        from django.core.cache import cache

        cache_keys = [
            f"product_detail_{self.id}",
            "product_list_all",
            "inventory_dashboard_stats",
        ]
        if self.category_id:
            cache_keys.extend(
                [
                    f"category_stats_{self.category_id}",
                    f"product_list_{self.category_id}",
                ]
            )
        super().save(*args, **kwargs)
        cache.delete_many(cache_keys)


class Supplier(SoftDeleteMixin, models.Model):
    """
    Model for suppliers
    """

    name = models.CharField(_("اسم المورد"), max_length=200)
    contact_person = models.CharField(_("جهة الاتصال"), max_length=100, blank=True)
    phone = models.CharField(_("رقم الهاتف"), max_length=20, blank=True)
    email = models.EmailField(_("البريد الإلكتروني"), blank=True)
    address = models.TextField(_("العنوان"), blank=True)
    tax_number = models.CharField(_("الرقم الضريبي"), max_length=50, blank=True)
    notes = models.TextField(_("ملاحظات"), blank=True)

    class Meta:
        verbose_name = _("مورد")
        verbose_name_plural = _("الموردين")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Warehouse(SoftDeleteMixin, models.Model):
    """
    Model for warehouses
    """

    name = models.CharField(_("اسم المستودع"), max_length=100)
    code = models.CharField(_("رمز المستودع"), max_length=20, unique=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="warehouses",
        verbose_name=_("الفرع"),
        null=True,
        blank=True,
    )
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_warehouses",
        verbose_name=_("المدير"),
    )
    address = models.TextField(_("العنوان"), blank=True)
    is_active = models.BooleanField(_("نشط"), default=True)
    is_official_fabric_warehouse = models.BooleanField(
        _("مستودع رسمي للأقمشة"),
        default=False,
        help_text=_("تحديد إذا كان هذا المستودع معتمد رسمياً لتخزين الأقمشة"),
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_warehouses",
        verbose_name=_("تم الإنشاء بواسطة"),
    )

    class Meta:
        verbose_name = _("مستودع")
        verbose_name_plural = _("المستودعات")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name", "code"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def created_by_name(self):
        """الحصول على اسم منشئ المستودع"""
        if self.created_by:
            return self.created_by.get_full_name() or self.created_by.username
        return "غير محدد"

    @property
    def created_date_display(self):
        """الحصول على تاريخ الإنشاء بصيغة مقروءة"""
        if self.created_at:
            return self.created_at.strftime("%Y-%m-%d %H:%M")
        return "غير متوفر"

    @property
    def updated_date_display(self):
        """الحصول على تاريخ التحديث بصيغة مقروءة"""
        if self.updated_at:
            return self.updated_at.strftime("%Y-%m-%d %H:%M")
        return "غير متوفر"


class WarehouseLocation(SoftDeleteMixin, models.Model):
    """
    Model for specific locations within warehouses
    """

    name = models.CharField(_("اسم الموقع"), max_length=100)
    code = models.CharField(_("رمز الموقع"), max_length=30)
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="locations",
        verbose_name=_("المستودع"),
    )
    description = models.TextField(_("الوصف"), blank=True)
    capacity = models.PositiveIntegerField(
        _("السعة"), default=1000, help_text=_("السعة القصوى للموقع")
    )
    is_active = models.BooleanField(_("نشط"), default=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("موقع مستودع")
        verbose_name_plural = _("مواقع المستودعات")
        ordering = ["warehouse", "name"]
        unique_together = ["warehouse", "code"]

    def __str__(self):
        return f"{self.warehouse.name} - {self.name} ({self.code})"

    @property
    def used_capacity(self):
        """حساب السعة المستخدمة"""
        from django.db.models import Sum

        total = (
            ProductBatch.objects.filter(location=self).aggregate(total=Sum("quantity"))[
                "total"
            ]
            or 0
        )
        return total

    @property
    def available_capacity(self):
        """حساب السعة المتاحة"""
        return self.capacity - self.used_capacity

    @property
    def occupancy_rate(self):
        """نسبة الإشغال"""
        if self.capacity > 0:
            return int((self.used_capacity / self.capacity) * 100)
        return 0


class ProductBatch(SoftDeleteMixin, models.Model):
    """
    Model for tracking product batches
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="batches",
        verbose_name=_("المنتج"),
    )
    batch_number = models.CharField(_("رقم الدفعة"), max_length=50)
    location = models.ForeignKey(
        WarehouseLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_batches",
        verbose_name=_("الموقع"),
    )
    quantity = models.PositiveIntegerField(_("الكمية"))
    manufacturing_date = models.DateField(_("تاريخ التصنيع"), null=True, blank=True)
    expiry_date = models.DateField(_("تاريخ الصلاحية"), null=True, blank=True)
    barcode = models.CharField(_("الباركود"), max_length=100, blank=True)
    cost_price = models.DecimalField(
        _("سعر التكلفة"), max_digits=10, decimal_places=2, default=0
    )
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    class Meta:
        verbose_name = _("دفعة منتج")
        verbose_name_plural = _("دفعات المنتجات")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product"], name="batch_product_idx"),
            models.Index(fields=["batch_number"], name="batch_number_idx"),
            models.Index(fields=["expiry_date"], name="batch_expiry_idx"),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.batch_number} ({self.quantity})"

    def save(self, *args, **kwargs):
        # Generate barcode if not provided
        if not self.barcode:
            self.barcode = f"B-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)


class StockTransaction(models.Model):
    """
    Model for tracking stock transactions
    """

    TRANSACTION_TYPES = [
        ("in", _("وارد")),
        ("out", _("صادر")),
        ("transfer", _("نقل")),
        ("adjustment", _("تسوية")),
    ]
    REASON_CHOICES = [
        ("purchase", _("شراء")),
        ("sale", _("بيع")),
        ("return", _("مرتجع")),
        ("transfer", _("نقل")),
        ("inventory_check", _("جرد")),
        ("damage", _("تلف")),
        ("production", _("إنتاج")),
        ("other", _("أخرى")),
    ]
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("المنتج"),
    )
    warehouse = models.ForeignKey(
        "Warehouse",
        on_delete=models.CASCADE,
        related_name="stock_transactions",
        verbose_name=_("المستودع"),
        null=True,  # للسماح بالقيم الفارغة للبيانات الموجودة
        blank=True,
    )
    transaction_type = models.CharField(
        _("نوع الحركة"), max_length=10, choices=TRANSACTION_TYPES
    )
    reason = models.CharField(
        _("السبب"), max_length=20, choices=REASON_CHOICES, default="other"
    )
    quantity = models.DecimalField(_("الكمية"), max_digits=10, decimal_places=2)
    reference = models.CharField(_("المرجع"), max_length=100, blank=True)
    transaction_date = models.DateTimeField(_("تاريخ العملية"), default=timezone.now)
    date = models.DateTimeField(_("تاريخ التسجيل"), auto_now_add=True)
    notes = models.TextField(_("ملاحظات"), blank=True)
    running_balance = models.DecimalField(
        _("الرصيد المتحرك"), max_digits=10, decimal_places=2, default=0
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="stock_transactions",
        verbose_name=_("تم بواسطة"),
    )

    class Meta:
        verbose_name = _("حركة مخزون")
        verbose_name_plural = _("حركات المخزون")
        ordering = ["-transaction_date", "-date"]
        indexes = [
            models.Index(fields=["product"], name="stock_product_idx"),
            models.Index(fields=["warehouse"], name="stock_warehouse_idx"),
            models.Index(fields=["transaction_type"], name="stock_type_idx"),
            models.Index(fields=["transaction_date"], name="stock_date_idx"),
            models.Index(fields=["product", "warehouse"], name="stock_prod_wareh_idx"),
            # NEW Performance Indexes
            models.Index(
                fields=["product", "warehouse", "transaction_date"],
                name="stock_prd_wrh_dt_idx",
            ),
            models.Index(
                fields=["warehouse", "transaction_date"], name="stock_wrh_date_idx"
            ),
            models.Index(
                fields=["transaction_type", "transaction_date"],
                name="stock_type_date_idx",
            ),
            models.Index(
                fields=["reason", "transaction_date"], name="stock_reason_date_idx"
            ),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.product.name} ({self.quantity})"

    def save(self, *args, **kwargs):
        from decimal import Decimal

        from django.db import transaction

        with transaction.atomic():
            # Get previous balance from the transaction immediately before this one
            # إضافة warehouse للفلتر لحساب الرصيد الصحيح لكل مستودع
            previous_balance = (
                StockTransaction.objects.filter(
                    product=self.product,
                    warehouse=self.warehouse,
                    transaction_date__lt=self.transaction_date,
                )
                .order_by("-transaction_date", "-id")
                .first()
            )

            # Calculate current balance based on previous balance
            # تحويل إلى Decimal لتجنب خطأ الجمع
            if previous_balance and previous_balance.running_balance is not None:
                current_balance = Decimal(str(previous_balance.running_balance))
            else:
                current_balance = Decimal("0")

            # تحويل الكمية إلى Decimal بشكل آمن
            quantity_decimal = Decimal(str(self.quantity))

            # Update running balance for this transaction
            if self.transaction_type == "in":
                self.running_balance = current_balance + quantity_decimal
            else:  # out, transfer, or adjustment
                self.running_balance = current_balance - quantity_decimal

            # Save this transaction
            super().save(*args, **kwargs)

            # Update all subsequent transactions' running balances
            # إضافة warehouse للفلتر لتحديث أرصدة نفس المستودع فقط
            next_transactions = (
                StockTransaction.objects.filter(
                    product=self.product,
                    warehouse=self.warehouse,
                    transaction_date__gt=self.transaction_date,
                )
                .order_by("transaction_date", "id")
                .select_for_update()
            )

            # Recalculate running balances for all subsequent transactions
            current_balance = Decimal(str(self.running_balance))
            for trans in next_transactions:
                trans_quantity = Decimal(str(trans.quantity))
                if trans.transaction_type == "in":
                    current_balance += trans_quantity
                else:  # out, transfer, or adjustment
                    current_balance -= trans_quantity

                # Only update if balance has changed
                if trans.running_balance != current_balance:
                    trans.running_balance = current_balance
                    super(StockTransaction, trans).save()


class PurchaseOrder(SoftDeleteMixin, models.Model):
    """
    Model for purchase orders
    """

    STATUS_CHOICES = [
        ("draft", _("مسودة")),
        ("pending", _("قيد الانتظار")),
        ("approved", _("تمت الموافقة")),
        ("partial", _("استلام جزئي")),
        ("received", _("تم الاستلام")),
        ("cancelled", _("ملغي")),
    ]
    order_number = models.CharField(_("رقم الطلب"), max_length=50, unique=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="purchase_orders",
        verbose_name=_("المورد"),
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        related_name="purchase_orders",
        verbose_name=_("المستودع"),
    )
    status = models.CharField(
        _("الحالة"), max_length=10, choices=STATUS_CHOICES, default="draft"
    )
    order_date = models.DateField(_("تاريخ الطلب"), auto_now_add=True)
    expected_date = models.DateField(_("تاريخ التسليم المتوقع"), null=True, blank=True)
    total_amount = models.DecimalField(
        _("إجمالي المبلغ"), max_digits=12, decimal_places=2, default=0
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_purchase_orders",
        verbose_name=_("تم بواسطة"),
    )

    class Meta:
        verbose_name = _("طلب شراء")
        verbose_name_plural = _("طلبات الشراء")
        ordering = ["-order_date"]
        indexes = [
            models.Index(fields=["order_number"], name="po_number_idx"),
            models.Index(fields=["supplier"], name="po_supplier_idx"),
            models.Index(fields=["status"], name="po_status_idx"),
            models.Index(fields=["order_date"], name="po_date_idx"),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        # Generate order number if not provided
        if not self.order_number:
            year = datetime.now().year
            month = datetime.now().month
            self.order_number = f"PO-{year}{month:02d}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class PurchaseOrderItem(SoftDeleteMixin, models.Model):
    """
    Model for items in a purchase order
    """

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("طلب الشراء"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="purchase_order_items",
        verbose_name=_("المنتج"),
    )
    quantity = models.PositiveIntegerField(_("الكمية"))
    unit_price = models.DecimalField(_("سعر الوحدة"), max_digits=10, decimal_places=2)
    received_quantity = models.PositiveIntegerField(_("الكمية المستلمة"), default=0)
    notes = models.TextField(_("ملاحظات"), blank=True)

    class Meta:
        verbose_name = _("عنصر طلب الشراء")
        verbose_name_plural = _("عناصر طلب الشراء")
        ordering = ["purchase_order", "product"]

    def __str__(self):
        return f"{self.purchase_order.order_number} - {self.product.name} ({self.quantity})"


class InventoryAdjustment(models.Model):
    """
    Model for inventory adjustments
    """

    ADJUSTMENT_TYPES = [
        ("increase", _("زيادة")),
        ("decrease", _("نقص")),
    ]
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="adjustments",
        verbose_name=_("المنتج"),
    )
    batch = models.ForeignKey(
        ProductBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="adjustments",
        verbose_name=_("الدفعة"),
    )
    adjustment_type = models.CharField(
        _("نوع التسوية"), max_length=10, choices=ADJUSTMENT_TYPES
    )
    quantity_before = models.DecimalField(
        _("الكمية قبل"), max_digits=10, decimal_places=2
    )
    quantity_after = models.DecimalField(
        _("الكمية بعد"), max_digits=10, decimal_places=2
    )
    reason = models.TextField(_("سبب التسوية"))
    date = models.DateTimeField(_("تاريخ التسوية"), auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inventory_adjustments",
        verbose_name=_("تم بواسطة"),
    )

    class Meta:
        verbose_name = _("تسوية مخزون")
        verbose_name_plural = _("تسويات المخزون")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["product"], name="adjustment_product_idx"),
            models.Index(fields=["adjustment_type"], name="adjustment_type_idx"),
            models.Index(fields=["date"], name="adjustment_date_idx"),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.get_adjustment_type_display()} ({self.quantity_before} -> {self.quantity_after})"

    @property
    def adjustment_quantity(self):
        return self.quantity_after - self.quantity_before


class StockAlert(models.Model):
    """
    Model for stock alerts
    """

    ALERT_TYPES = [
        ("low_stock", _("مخزون منخفض")),
        ("expiry", _("قرب انتهاء الصلاحية")),
        ("out_of_stock", _("نفاد المخزون")),
        ("overstock", _("فائض في المخزون")),
        ("price_change", _("تغير في السعر")),
    ]
    STATUS_CHOICES = [
        ("active", _("نشط")),
        ("resolved", _("تمت المعالجة")),
        ("ignored", _("تم تجاهله")),
    ]
    PRIORITY_CHOICES = [
        ("high", _("عالية")),
        ("medium", _("متوسطة")),
        ("low", _("منخفضة")),
    ]
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_alerts",
        verbose_name=_("المنتج"),
    )
    alert_type = models.CharField(_("نوع التنبيه"), max_length=15, choices=ALERT_TYPES)
    title = models.CharField(_("عنوان التنبيه"), max_length=200, blank=True)
    message = models.TextField(_("رسالة التنبيه"))
    description = models.TextField(_("الوصف"), blank=True)
    priority = models.CharField(
        _("الأولوية"), max_length=10, choices=PRIORITY_CHOICES, default="medium"
    )
    status = models.CharField(
        _("الحالة"), max_length=10, choices=STATUS_CHOICES, default="active"
    )
    quantity_before = models.DecimalField(
        _("الكمية السابقة"), max_digits=10, decimal_places=2, default=0
    )
    quantity_after = models.DecimalField(
        _("الكمية الحالية"), max_digits=10, decimal_places=2, default=0
    )
    threshold_limit = models.DecimalField(
        _("حد التنبيه"), max_digits=10, decimal_places=2, default=0
    )
    is_urgent = models.BooleanField(_("عاجل"), default=False)
    is_pinned = models.BooleanField(_("مثبت"), default=False)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    resolved_at = models.DateTimeField(_("تاريخ المعالجة"), null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_stock_alerts",
        verbose_name=_("تم الإنشاء بواسطة"),
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_stock_alerts",
        verbose_name=_("تمت المعالجة بواسطة"),
    )

    class Meta:
        verbose_name = _("تنبيه مخزون")
        verbose_name_plural = _("تنبيهات المخزون")
        ordering = ["-is_pinned", "-is_urgent", "-created_at"]
        indexes = [
            models.Index(fields=["product"], name="alert_product_idx"),
            models.Index(fields=["alert_type"], name="alert_type_idx"),
            models.Index(fields=["status"], name="alert_status_idx"),
            models.Index(fields=["priority"], name="alert_priority_idx"),
            models.Index(fields=["created_at"], name="alert_created_at_idx"),
        ]

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.product.name}"

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"{self.get_alert_type_display()} - {self.product.name}"
        super().save(*args, **kwargs)


class StockTransfer(models.Model):
    """
    نموذج التحويل المخزني - لنقل المنتجات بين المستودعات
    """

    STATUS_CHOICES = [
        ("draft", _("مسودة")),
        ("pending", _("قيد الانتظار")),
        ("approved", _("تمت الموافقة")),
        ("in_transit", _("قيد النقل")),
        ("completed", _("مكتمل")),
        ("cancelled", _("ملغي")),
        ("rejected", _("مرفوض")),
    ]

    transfer_number = models.CharField(
        _("رقم التحويل"), max_length=50, unique=True, editable=False
    )
    from_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
        verbose_name=_("من مستودع"),
    )
    to_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        verbose_name=_("إلى مستودع"),
    )
    status = models.CharField(
        _("الحالة"), max_length=15, choices=STATUS_CHOICES, default="draft"
    )
    transfer_date = models.DateTimeField(_("تاريخ التحويل"), default=timezone.now)
    expected_arrival_date = models.DateTimeField(
        _("تاريخ الوصول المتوقع"), null=True, blank=True
    )
    actual_arrival_date = models.DateTimeField(
        _("تاريخ الوصول الفعلي"), null=True, blank=True
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    reason = models.TextField(_("سبب التحويل"), blank=True)

    # Tracking fields
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_transfers",
        verbose_name=_("تم الإنشاء بواسطة"),
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_transfers",
        verbose_name=_("تمت الموافقة بواسطة"),
    )
    approved_at = models.DateTimeField(_("تاريخ الموافقة"), null=True, blank=True)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_transfers",
        verbose_name=_("تم الإكمال بواسطة"),
    )
    completed_at = models.DateTimeField(_("تاريخ الإكمال"), null=True, blank=True)

    class Meta:
        verbose_name = _("تحويل مخزني")
        verbose_name_plural = _("التحويلات المخزنية")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transfer_number"], name="transfer_number_idx"),
            models.Index(fields=["from_warehouse"], name="transfer_from_wh_idx"),
            models.Index(fields=["to_warehouse"], name="transfer_to_wh_idx"),
            models.Index(fields=["status"], name="transfer_status_idx"),
            models.Index(fields=["transfer_date"], name="transfer_date_idx"),
            models.Index(fields=["created_at"], name="transfer_created_idx"),
        ]

    def __str__(self):
        return f"{self.transfer_number} - {self.from_warehouse.name} → {self.to_warehouse.name}"

    def save(self, *args, **kwargs):
        # توليد رقم التحويل تلقائياً
        if not self.transfer_number:
            from datetime import datetime

            date_str = datetime.now().strftime("%Y%m%d")
            last_transfer = (
                StockTransfer.objects.filter(
                    transfer_number__startswith=f"TRF-{date_str}"
                )
                .order_by("-transfer_number")
                .first()
            )

            if last_transfer:
                last_number = int(last_transfer.transfer_number.split("-")[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.transfer_number = f"TRF-{date_str}-{new_number:04d}"

        super().save(*args, **kwargs)

    @property
    def total_items(self):
        """إجمالي عدد الأصناف"""
        return self.items.count()

    @property
    def total_quantity(self):
        """إجمالي الكمية"""
        return self.items.aggregate(total=Sum("quantity"))["total"] or 0

    @property
    def can_approve(self):
        """هل يمكن الموافقة على التحويل"""
        return self.status == "pending" and self.items.exists()

    @property
    def can_complete(self):
        """هل يمكن إكمال التحويل"""
        return self.status in ["approved", "in_transit"]

    @property
    def can_cancel(self):
        """هل يمكن إلغاء التحويل"""
        return self.status in ["draft", "pending", "approved"]

    def approve(self, user):
        """الموافقة على التحويل"""
        if not self.can_approve:
            raise ValueError(_("لا يمكن الموافقة على هذا التحويل"))

        self.status = "approved"
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

        # إنشاء حركات مخزون للخروج من المستودع المصدر
        for item in self.items.all():
            # الحصول على آخر رصيد في المستودع المصدر
            last_transaction = (
                StockTransaction.objects.filter(
                    product=item.product, warehouse=self.from_warehouse
                )
                .order_by("-transaction_date", "-id")
                .first()
            )

            previous_balance = (
                last_transaction.running_balance if last_transaction else 0
            )
            new_balance = previous_balance - item.quantity

            StockTransaction.objects.create(
                product=item.product,
                warehouse=self.from_warehouse,
                transaction_type="out",
                reason="transfer",
                quantity=item.quantity,
                reference=self.transfer_number,
                transaction_date=self.transfer_date,
                notes=f"تحويل إلى {self.to_warehouse.name}",
                running_balance=new_balance,
                created_by=user,
            )

    def complete(self, user):
        """إكمال التحويل"""
        if not self.can_complete:
            raise ValueError(_("لا يمكن إكمال هذا التحويل"))

        self.status = "completed"
        self.completed_by = user
        self.completed_at = timezone.now()
        self.actual_arrival_date = timezone.now()
        self.save()

        # إنشاء حركات مخزون للدخول إلى المستودع المستهدف
        for item in self.items.all():
            qty = item.received_quantity or item.quantity

            # الحصول على آخر رصيد في المستودع المستهدف
            last_transaction = (
                StockTransaction.objects.filter(
                    product=item.product, warehouse=self.to_warehouse
                )
                .order_by("-transaction_date", "-id")
                .first()
            )

            previous_balance = (
                last_transaction.running_balance if last_transaction else 0
            )
            new_balance = previous_balance + qty

            StockTransaction.objects.create(
                product=item.product,
                warehouse=self.to_warehouse,
                transaction_type="in",
                reason="transfer",
                quantity=qty,
                reference=self.transfer_number,
                transaction_date=timezone.now(),
                notes=f"تحويل من {self.from_warehouse.name}",
                running_balance=new_balance,
                created_by=user,
            )

    def cancel(self, user, reason=""):
        """إلغاء التحويل"""
        if not self.can_cancel:
            raise ValueError(_("لا يمكن إلغاء هذا التحويل"))

        self.status = "cancelled"
        if reason:
            self.notes = (
                f"{self.notes}\n\nسبب الإلغاء: {reason}"
                if self.notes
                else f"سبب الإلغاء: {reason}"
            )
        self.save()


class StockTransferItem(models.Model):
    """
    نموذج عنصر التحويل المخزني
    """

    transfer = models.ForeignKey(
        StockTransfer,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("التحويل"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="transfer_items",
        verbose_name=_("المنتج"),
    )
    quantity = models.DecimalField(
        _("الكمية المطلوبة"), max_digits=10, decimal_places=2
    )
    received_quantity = models.DecimalField(
        _("الكمية المستلمة"), max_digits=10, decimal_places=2, default=0
    )
    notes = models.TextField(_("ملاحظات"), blank=True)

    class Meta:
        verbose_name = _("عنصر تحويل مخزني")
        verbose_name_plural = _("عناصر التحويل المخزني")
        ordering = ["transfer", "product"]
        unique_together = ["transfer", "product"]
        indexes = [
            models.Index(fields=["transfer"], name="transfer_item_transfer_idx"),
            models.Index(fields=["product"], name="transfer_item_product_idx"),
        ]

    def __str__(self):
        return (
            f"{self.transfer.transfer_number} - {self.product.name} ({self.quantity})"
        )

    @property
    def is_fully_received(self):
        """هل تم استلام الكمية كاملة"""
        return self.received_quantity >= self.quantity

    @property
    def remaining_quantity(self):
        """الكمية المتبقية"""
        return self.quantity - self.received_quantity


class BulkUploadLog(models.Model):
    """
    نموذج لتسجيل عمليات رفع المنتجات بالجملة
    """

    UPLOAD_TYPE_CHOICES = [
        ("products", _("رفع منتجات")),
        ("stock_update", _("تحديث مخزون")),
    ]

    STATUS_CHOICES = [
        ("processing", _("قيد المعالجة")),
        ("completed", _("مكتمل")),
        ("completed_with_errors", _("مكتمل مع أخطاء")),
        ("failed", _("فشل")),
    ]

    upload_type = models.CharField(
        _("نوع العملية"), max_length=20, choices=UPLOAD_TYPE_CHOICES
    )
    status = models.CharField(
        _("الحالة"), max_length=30, choices=STATUS_CHOICES, default="processing"
    )
    file_name = models.CharField(_("اسم الملف"), max_length=255)
    task_id = models.CharField(_("معرّف المهمة"), max_length=255, blank=True, null=True)
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="upload_logs",
        verbose_name=_("المستودع"),
    )

    # إحصائيات
    total_rows = models.PositiveIntegerField(_("إجمالي الصفوف"), default=0)
    processed_count = models.PositiveIntegerField(_("عدد المعالج"), default=0)
    created_count = models.PositiveIntegerField(_("عدد المنشأ"), default=0)
    updated_count = models.PositiveIntegerField(_("عدد المحدث"), default=0)
    skipped_count = models.PositiveIntegerField(
        _("عدد المتخطى"), default=0, help_text=_("صفوف موجودة ولم تتغير")
    )
    error_count = models.PositiveIntegerField(_("عدد الأخطاء"), default=0)

    # معلومات إضافية
    options = models.JSONField(_("خيارات العملية"), default=dict, blank=True)
    created_warehouses = models.JSONField(
        _("المستودعات المنشأة"), default=list, blank=True
    )
    summary = models.TextField(_("ملخص العملية"), blank=True)

    # التتبع
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    completed_at = models.DateTimeField(_("تاريخ الإكمال"), null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="upload_logs",
        verbose_name=_("تم بواسطة"),
    )

    class Meta:
        verbose_name = _("سجل رفع جماعي")
        verbose_name_plural = _("سجلات الرفع الجماعي")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["upload_type"], name="upload_log_type_idx"),
            models.Index(fields=["status"], name="upload_log_status_idx"),
            models.Index(fields=["created_at"], name="upload_log_created_idx"),
            models.Index(fields=["created_by"], name="upload_log_user_idx"),
        ]

    def __str__(self):
        return f"{self.get_upload_type_display()} - {self.file_name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @property
    def duration(self):
        """مدة العملية"""
        if self.completed_at:
            delta = self.completed_at - self.created_at
            return delta.total_seconds()
        return None

    @property
    def success_rate(self):
        """نسبة النجاح"""
        if self.total_rows > 0:
            success_count = self.created_count + self.updated_count
            return round((success_count / self.total_rows) * 100, 2)
        return 0

    @property
    def has_errors(self):
        """هل توجد أخطاء"""
        return self.error_count > 0

    def complete(self, summary=""):
        """إكمال العملية"""
        self.completed_at = timezone.now()
        if self.error_count > 0:
            self.status = "completed_with_errors"
        else:
            self.status = "completed"
        if summary:
            self.summary = summary
        self.save()

    def fail(self, error_message=""):
        """فشل العملية"""
        self.completed_at = timezone.now()
        self.status = "failed"
        self.summary = error_message
        self.save()


class BulkUploadError(models.Model):
    """
    نموذج لتسجيل أخطاء رفع المنتجات بالجملة
    """

    ERROR_TYPE_CHOICES = [
        ("validation", _("خطأ في التحقق")),
        ("duplicate", _("تكرار")),
        ("missing_data", _("بيانات ناقصة")),
        ("invalid_data", _("بيانات غير صالحة")),
        ("database", _("خطأ في قاعدة البيانات")),
        ("processing", _("خطأ في المعالجة")),
        ("other", _("خطأ آخر")),
    ]

    RESULT_STATUS_CHOICES = [
        ("created", _("تم الإنشاء")),
        ("updated", _("تم التحديث")),
        ("skipped", _("تم التخطي")),
        ("failed", _("فشل")),
    ]

    upload_log = models.ForeignKey(
        BulkUploadLog,
        on_delete=models.CASCADE,
        related_name="errors",
        verbose_name=_("سجل الرفع"),
    )
    row_number = models.PositiveIntegerField(_("رقم الصف"))
    error_type = models.CharField(
        _("نوع الخطأ"), max_length=20, choices=ERROR_TYPE_CHOICES, default="other"
    )
    result_status = models.CharField(
        _("حالة النتيجة"),
        max_length=20,
        choices=RESULT_STATUS_CHOICES,
        default="failed",
        help_text=_("حالة معالجة الصف"),
    )
    error_message = models.TextField(_("رسالة الخطأ"))
    row_data = models.JSONField(_("بيانات الصف"), default=dict, blank=True)

    created_at = models.DateTimeField(_("تاريخ التسجيل"), auto_now_add=True)

    class Meta:
        verbose_name = _("خطأ رفع جماعي")
        verbose_name_plural = _("أخطاء الرفع الجماعي")
        ordering = ["upload_log", "row_number"]
        indexes = [
            models.Index(fields=["upload_log"], name="upload_error_log_idx"),
            models.Index(fields=["error_type"], name="upload_error_type_idx"),
            models.Index(fields=["row_number"], name="upload_error_row_idx"),
        ]

    def __str__(self):
        return f"الصف {self.row_number}: {self.error_message[:50]}"

    @property
    def product_name(self):
        """الحصول على اسم المنتج من بيانات الصف"""
        if self.row_data:
            return self.row_data.get(
                "اسم المنتج", self.row_data.get("name", "غير محدد")
            )
        return "غير محدد"

    @property
    def product_code(self):
        """الحصول على كود المنتج من بيانات الصف"""
        if self.row_data:
            return self.row_data.get("الكود", self.row_data.get("code", ""))
        return ""


# ==================== نظام المنتجات الأساسية والمتغيرات ====================


class BaseProduct(models.Model):
    """
    المنتج الأساسي - يمثل مجموعة من المتغيرات (مثل ORION, HARMONY)
    Product variants will reference this as their parent
    """

    name = models.CharField(_("اسم المنتج الأساسي"), max_length=255)
    code = models.CharField(_("الكود الأساسي"), max_length=255, unique=True)
    description = models.TextField(_("الوصف"), blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="base_products",
        verbose_name=_("الفئة"),
    )

    # السعر الأساسي (القطاعي) - يُطبق على جميع المتغيرات افتراضياً
    base_price = models.DecimalField(
        _("السعر القطاعي"),
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("السعر الافتراضي لعملاء التجزئة"),
    )

    # سعر الجملة
    wholesale_price = models.DecimalField(
        _("سعر الجملة"),
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("السعر لعملاء الجملة"),
    )

    currency = models.CharField(
        _("العملة"), max_length=3, choices=Product.CURRENCY_CHOICES, default="EGP"
    )
    unit = models.CharField(
        _("الوحدة"), max_length=10, choices=Product.UNIT_CHOICES, default="piece"
    )

    # الحد الأدنى للمخزون (يُطبق على كل متغير)
    minimum_stock = models.PositiveIntegerField(_("الحد الأدنى للمخزون"), default=0)

    # QR Code Field
    qr_code_base64 = models.TextField(_("رمز QR (مخزن)"), blank=True, null=True)

    # Cloudflare Sync Tracking
    cloudflare_synced = models.BooleanField(
        _("تم المزامنة مع Cloudflare"),
        default=False,
        help_text=_("هل تم مزامنة هذا المنتج مع Cloudflare KV؟"),
    )
    last_synced_at = models.DateTimeField(
        _("تاريخ آخر مزامنة"),
        null=True,
        blank=True,
        help_text=_("آخر مرة تم فيها مزامنة المنتج مع Cloudflare"),
    )

    # نوع القماش والعرض
    material = models.CharField(
        _("نوع القماش (Material)"),
        max_length=100,
        default="Linen",
        blank=True,
    )
    width = models.CharField(
        _("العرض (Width)"),
        max_length=50,
        default="280 cm",
        blank=True,
    )

    is_active = models.BooleanField(_("نشط"), default=True)

    def generate_qr(self, force=False):
        """
        توليد رمز QR للمنتج الأساسي
        """
        if not self.code:
            return False

        if self.qr_code_base64 and not force:
            return False

        try:
            import base64
            from io import BytesIO

            import qrcode
            from django.conf import settings

            # الرابط يوجه لصفحة المنتج الأساسي التي تعرض كل المتغيرات
            base_url = getattr(
                settings, "CLOUDFLARE_WORKER_URL", "https://qr.elkhawaga.uk"
            )
            qr_url = f"{base_url}/{self.code}"

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            qr_img.save(buffer, format="PNG")
            self.qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            return True
        except Exception:
            return False

    def get_qr_url(self):
        """الحصول على رابط QR"""
        from django.conf import settings

        base_url = getattr(settings, "CLOUDFLARE_WORKER_URL", "https://qr.elkhawaga.uk")
        return f"{base_url}/{self.code}"

    def save(self, *args, **kwargs):
        # توليد QR عند الحفظ إذا لم يكن موجوداً
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # تخطي توليد QR أثناء عمليات الترحيل (سيتم في المرحلة 2)
        if getattr(self, "_skip_qr_generation", False):
            return

        if not self.qr_code_base64 and self.code:
            if self.generate_qr():
                # حفظ الحقل فقط لتجنب التكرار اللانهائي
                BaseProduct.objects.filter(pk=self.pk).update(
                    qr_code_base64=self.qr_code_base64
                )

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_base_products",
        verbose_name=_("تم الإنشاء بواسطة"),
    )

    class Meta:
        verbose_name = _("منتج أساسي")
        verbose_name_plural = _("المنتجات الأساسية")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"], name="base_product_code_idx"),
            models.Index(fields=["name"], name="base_product_name_idx"),
            models.Index(fields=["category"], name="base_product_cat_idx"),
            models.Index(fields=["is_active"], name="base_product_active_idx"),
        ]
        permissions = [
            ("manage_base_products", _("إدارة المنتجات الأساسية")),
            ("bulk_price_update", _("تحديث الأسعار بالجملة")),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_first_legacy_code(self):
        """الحصول على أول كود Onyx من المتغيرات المرتبطة بالنظام القديم"""
        variant = (
            self.variants.filter(legacy_product__isnull=False)
            .select_related("legacy_product")
            .first()
        )
        if variant and variant.legacy_product:
            return variant.legacy_product.code
        return None

    def get_price_for_customer_type(self, customer_type_code):
        """الحصول على السعر المناسب حسب نوع العميل"""
        from customers.models import CustomerType

        try:
            ct = CustomerType.objects.get(code=customer_type_code)
        except CustomerType.DoesNotExist:
            return self.base_price

        if ct.pricing_type == "wholesale":
            return self.wholesale_price or self.base_price
        return self.base_price

    @property
    def variants_count(self):
        """عدد المتغيرات"""
        return self.variants.count()

    @property
    def total_stock(self):
        """إجمالي المخزون من جميع المتغيرات"""
        total = 0
        for variant in self.variants.filter(is_active=True):
            total += variant.current_stock
        return total

    @property
    def available_variants(self):
        """المتغيرات المتوفرة في المخزون"""
        return self.variants.filter(is_active=True).exclude(
            id__in=[v.id for v in self.variants.all() if v.current_stock <= 0]
        )

    def get_variants_summary(self):
        """ملخص المتغيرات مع المخزون والأسعار"""
        summary = []
        for variant in self.variants.filter(is_active=True).select_related("color"):
            summary.append(
                {
                    "id": variant.id,
                    "code": variant.variant_code,
                    "full_code": variant.full_code,
                    "color": (
                        variant.color.name if variant.color else variant.color_code
                    ),
                    "color_hex": variant.color.hex_code if variant.color else None,
                    "price": float(variant.effective_price),
                    "has_custom_price": variant.has_custom_price,
                    "stock": variant.current_stock,
                    "status": variant.stock_status,
                }
            )
        return summary

    def apply_bulk_price_update(self, update_type, value, variant_ids=None, user=None):
        """
        تطبيق تحديث سعر جماعي على المتغيرات

        Args:
            update_type: 'percentage' أو 'fixed' أو 'reset'
            value: القيمة (نسبة مئوية أو مبلغ ثابت)
            variant_ids: قائمة معرفات المتغيرات (None = الكل)
            user: المستخدم الذي قام بالتحديث
        """
        from decimal import Decimal

        variants = self.variants.filter(is_active=True)
        if variant_ids:
            variants = variants.filter(id__in=variant_ids)

        updated_count = 0
        for variant in variants:
            if update_type == "percentage":
                # زيادة/نقصان بنسبة مئوية من السعر الأساسي
                percentage = Decimal(str(value))
                variant.price_override = self.base_price * (1 + percentage / 100)
            elif update_type == "fixed":
                # تعيين سعر ثابت
                variant.price_override = Decimal(str(value))
            elif update_type == "reset":
                # إعادة إلى السعر الأساسي
                variant.price_override = None

            variant.save()
            updated_count += 1

            # تسجيل التغيير
            PriceHistory.objects.create(
                variant=variant,
                old_price=variant.effective_price,
                new_price=variant.price_override or self.base_price,
                change_type=update_type,
                change_value=value,
                changed_by=user,
            )

        return updated_count


class ColorAttribute(models.Model):
    """
    سمة اللون - لتصنيف ألوان المتغيرات
    """

    name = models.CharField(_("اسم اللون"), max_length=100)
    code = models.CharField(_("رمز اللون"), max_length=100, unique=True)
    hex_code = models.CharField(
        _("كود اللون HEX"), max_length=7, blank=True, help_text=_("مثال: #FF5733")
    )
    description = models.TextField(_("الوصف"), blank=True)
    is_active = models.BooleanField(_("نشط"), default=True)
    display_order = models.PositiveIntegerField(_("ترتيب العرض"), default=0)

    class Meta:
        verbose_name = _("لون")
        verbose_name_plural = _("الألوان")
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["code"], name="color_code_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class ProductVariant(models.Model):
    """
    متغير المنتج - يمثل نسخة محددة من المنتج الأساسي (مثل ORION/C 004)
    """

    base_product = models.ForeignKey(
        BaseProduct,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name=_("المنتج الأساسي"),
    )

    # ربط بالمنتج القديم للتوافق
    legacy_product = models.OneToOneField(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variant_link",
        verbose_name=_("المنتج القديم"),
        help_text=_("للتوافق مع النظام القديم"),
    )

    # كود المتغير (الجزء بعد /)
    variant_code = models.CharField(
        _("كود المتغير"), max_length=50, help_text=_("مثال: C 004, C1, OFF WHITE")
    )

    # اللون (اختياري - للربط بجدول الألوان)
    color = models.ForeignKey(
        ColorAttribute,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variants",
        verbose_name=_("اللون"),
    )

    # كود اللون (للحالات التي لا يوجد فيها لون في الجدول)
    color_code = models.CharField(
        _("كود اللون"),
        max_length=30,
        blank=True,
        help_text=_("يُستخدم إذا لم يكن اللون موجوداً في جدول الألوان"),
    )

    # تجاوز السعر القطاعي (اختياري)
    price_override = models.DecimalField(
        _("تجاوز السعر القطاعي"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("اتركه فارغاً لاستخدام السعر القطاعي الأساسي"),
    )

    # تجاوز سعر الجملة (اختياري)
    wholesale_price_override = models.DecimalField(
        _("تجاوز سعر الجملة"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("اتركه فارغاً لاستخدام سعر الجملة الأساسي"),
    )

    # الباركود الخاص بالمتغير
    barcode = models.CharField(
        _("الباركود"), max_length=100, blank=True, unique=True, null=True
    )

    description = models.TextField(_("الوصف"), blank=True)
    is_active = models.BooleanField(_("نشط"), default=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)

    class Meta:
        verbose_name = _("متغير منتج")
        verbose_name_plural = _("متغيرات المنتجات")
        ordering = ["base_product", "variant_code"]
        unique_together = ["base_product", "variant_code"]
        indexes = [
            models.Index(fields=["base_product"], name="variant_base_idx"),
            models.Index(fields=["variant_code"], name="variant_code_idx"),
            models.Index(fields=["color"], name="variant_color_idx"),
            models.Index(fields=["is_active"], name="variant_active_idx"),
            models.Index(fields=["barcode"], name="variant_barcode_idx"),
        ]
        permissions = [
            ("manage_variants", _("إدارة المتغيرات")),
            ("override_variant_price", _("تجاوز سعر المتغير")),
        ]

    def __str__(self):
        return self.full_code

    @property
    def full_code(self):
        """الكود الكامل (المنتج الأساسي + المتغير)"""
        return f"{self.base_product.code}/{self.variant_code}"

    @property
    def effective_price(self):
        """السعر القطاعي الفعلي (تجاوز أو أساسي)"""
        if self.price_override is not None:
            return self.price_override
        return self.base_product.base_price

    @property
    def effective_wholesale_price(self):
        """سعر الجملة الفعلي (تجاوز أو أساسي)"""
        if self.wholesale_price_override is not None:
            return self.wholesale_price_override
        return self.base_product.wholesale_price or self.base_product.base_price

    def get_price_for_customer_type(self, customer_type_code):
        """الحصول على السعر المناسب حسب نوع العميل"""
        from customers.models import CustomerType

        try:
            ct = CustomerType.objects.get(code=customer_type_code)
        except CustomerType.DoesNotExist:
            return self.effective_price

        if ct.pricing_type == "wholesale":
            return self.effective_wholesale_price
        return self.effective_price

    @property
    def has_custom_price(self):
        """هل لديه سعر مخصص"""
        return self.price_override is not None

    def get_total_stock(self):
        """المخزون الإجمالي - للاستخدام في القوالب"""
        return self.current_stock

    @property
    def current_stock(self):
        """المخزون الحالي من جميع المستودعات"""
        if self.legacy_product:
            return self.legacy_product.current_stock

        # حساب من VariantStock
        total = 0
        for stock in self.warehouse_stocks.all():
            total += stock.current_quantity
        return total

    @property
    def stock_status(self):
        """حالة المخزون"""
        current = self.current_stock
        min_stock = self.base_product.minimum_stock

        if current <= 0:
            return _("غير متوفر")
        elif current <= min_stock:
            return _("مخزون منخفض")
        return _("متوفر")

    def get_stock_by_warehouse(self):
        """المخزون حسب المستودع"""
        stocks = {}

        if self.legacy_product:
            # استخدام النظام القديم
            for warehouse in Warehouse.objects.filter(is_active=True):
                last_trans = (
                    self.legacy_product.transactions.filter(warehouse=warehouse)
                    .order_by("-transaction_date", "-id")
                    .first()
                )

                if last_trans and last_trans.running_balance > 0:
                    stocks[warehouse.id] = {
                        "warehouse": warehouse,
                        "quantity": float(last_trans.running_balance),
                    }
        else:
            # استخدام النظام الجديد
            for stock in self.warehouse_stocks.select_related("warehouse"):
                if stock.current_quantity > 0:
                    stocks[stock.warehouse.id] = {
                        "warehouse": stock.warehouse,
                        "quantity": stock.current_quantity,
                    }

        return stocks

    def save(self, *args, **kwargs):
        # توليد باركود تلقائي إذا لم يكن موجوداً
        if not self.barcode:
            self.barcode = f"V-{self.base_product.code}-{self.variant_code}".replace(
                " ", ""
            ).replace("/", "-")
        super().save(*args, **kwargs)


class VariantStock(models.Model):
    """
    مخزون المتغير حسب المستودع
    يتيح تتبع المخزون على مستوى المتغير + المستودع
    """

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="warehouse_stocks",
        verbose_name=_("المتغير"),
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="variant_stocks",
        verbose_name=_("المستودع"),
    )
    current_quantity = models.DecimalField(
        _("الكمية الحالية"), max_digits=10, decimal_places=2, default=0
    )
    reserved_quantity = models.DecimalField(
        _("الكمية المحجوزة"),
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("الكمية المحجوزة للطلبات غير المكتملة"),
    )
    last_updated = models.DateTimeField(_("آخر تحديث"), auto_now=True)

    class Meta:
        verbose_name = _("مخزون متغير")
        verbose_name_plural = _("مخزونات المتغيرات")
        unique_together = ["variant", "warehouse"]
        indexes = [
            models.Index(fields=["variant", "warehouse"], name="var_stock_var_wh_idx"),
            models.Index(fields=["current_quantity"], name="var_stock_qty_idx"),
        ]

    def __str__(self):
        return (
            f"{self.variant.full_code} @ {self.warehouse.name}: {self.current_quantity}"
        )

    @property
    def available_quantity(self):
        """الكمية المتاحة (الحالية - المحجوزة)"""
        return self.current_quantity - self.reserved_quantity


class PriceHistory(models.Model):
    """
    سجل تغييرات الأسعار
    """

    CHANGE_TYPES = [
        ("manual", _("يدوي")),
        ("percentage", _("نسبة مئوية")),
        ("fixed", _("قيمة ثابتة")),
        ("reset", _("إعادة للأساسي")),
        ("bulk", _("تحديث جماعي")),
        ("base_update", _("تحديث السعر الأساسي")),
    ]

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="price_history",
        verbose_name=_("المتغير"),
    )
    old_price = models.DecimalField(_("السعر القديم"), max_digits=10, decimal_places=2)
    new_price = models.DecimalField(_("السعر الجديد"), max_digits=10, decimal_places=2)
    change_type = models.CharField(
        _("نوع التغيير"), max_length=20, choices=CHANGE_TYPES, default="manual"
    )
    change_value = models.DecimalField(
        _("قيمة التغيير"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("النسبة أو القيمة المطبقة"),
    )
    changed_at = models.DateTimeField(_("تاريخ التغيير"), auto_now_add=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="price_changes",
        verbose_name=_("تم التغيير بواسطة"),
    )
    notes = models.TextField(_("ملاحظات"), blank=True)

    class Meta:
        verbose_name = _("سجل سعر")
        verbose_name_plural = _("سجل الأسعار")
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["variant"], name="price_hist_variant_idx"),
            models.Index(fields=["changed_at"], name="price_hist_date_idx"),
        ]

    def __str__(self):
        return f"{self.variant.full_code}: {self.old_price} → {self.new_price}"
