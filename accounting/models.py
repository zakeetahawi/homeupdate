"""
نماذج نظام المحاسبة المتكامل
Integrated Accounting System Models
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


class AccountType(models.Model):
    """أنواع الحسابات المحاسبية"""

    ACCOUNT_CATEGORIES = [
        ("asset", "أصول"),
        ("liability", "التزامات"),
        ("equity", "حقوق ملكية"),
        ("revenue", "إيرادات"),
        ("expense", "مصروفات"),
    ]

    NORMAL_BALANCE_CHOICES = [
        ("debit", "مدين"),
        ("credit", "دائن"),
    ]

    name = models.CharField(_("اسم النوع"), max_length=100)
    name_en = models.CharField(_("الاسم بالإنجليزية"), max_length=100, blank=True)
    category = models.CharField(_("التصنيف"), max_length=20, choices=ACCOUNT_CATEGORIES)
    code_prefix = models.CharField(_("بادئة الكود"), max_length=4)
    normal_balance = models.CharField(
        _("الرصيد الطبيعي"),
        max_length=10,
        choices=NORMAL_BALANCE_CHOICES,
        default="debit",
    )
    description = models.TextField(_("الوصف"), blank=True)
    is_active = models.BooleanField(_("نشط"), default=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)

    class Meta:
        verbose_name = _("نوع الحساب")
        verbose_name_plural = _("أنواع الحسابات")
        ordering = ["code_prefix"]

    def __str__(self):
        return f"{self.code_prefix} - {self.name}"


class Account(models.Model):
    """دليل الحسابات - شجرة الحسابات"""

    code = models.CharField(_("كود الحساب"), max_length=20, unique=True, db_index=True)
    name = models.CharField(_("اسم الحساب"), max_length=200, db_index=True)
    name_en = models.CharField(_("الاسم بالإنجليزية"), max_length=200, blank=True)
    account_type = models.ForeignKey(
        AccountType,
        on_delete=models.PROTECT,
        related_name="accounts",
        verbose_name=_("نوع الحساب"),
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("الحساب الأب"),
    )
    # ربط اختياري بالعميل للحسابات الفردية
    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounting_account",
        verbose_name=_("العميل المرتبط"),
    )
    # ربط اختياري بالفرع
    branch = models.ForeignKey(
        "accounts.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounting_accounts",
        verbose_name=_("الفرع"),
    )

    is_active = models.BooleanField(_("نشط"), default=True)
    is_system_account = models.BooleanField(_("حساب نظام"), default=False)
    is_customer_account = models.BooleanField(_("حساب عميل"), default=False, db_index=True)
    allow_transactions = models.BooleanField(_("يسمح بالقيود"), default=True)

    # الأرصدة
    opening_balance = models.DecimalField(
        _("الرصيد الافتتاحي"), max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    current_balance = models.DecimalField(
        _("الرصيد الحالي"), max_digits=15, decimal_places=2, default=Decimal("0.00")
    )

    description = models.TextField(_("الوصف"), blank=True)
    notes = models.TextField(_("ملاحظات"), blank=True)

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_accounts",
        verbose_name=_("تم الإنشاء بواسطة"),
    )

    class Meta:
        verbose_name = _("حساب")
        verbose_name_plural = _("دليل الحسابات")
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(is_customer_account=False),
                name="unique_non_customer_account_name",
            ),
        ]
        indexes = [
            models.Index(fields=["code"], name="acc_code_idx"),
            models.Index(fields=["name"], name="acc_name_idx"),
            models.Index(fields=["account_type"], name="acc_type_idx"),
            models.Index(fields=["customer"], name="acc_customer_idx"),
            models.Index(fields=["is_active"], name="acc_active_idx"),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @cached_property
    def full_path(self):
        """المسار الكامل للحساب في الشجرة"""
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return " > ".join(path)

    @property
    def level(self):
        """مستوى الحساب في الشجرة"""
        return self._calculate_level()

    @property
    def has_children(self):
        """هل للحساب حسابات فرعية"""
        return self.children.exists()

    def clean(self):
        """التحقق من صحة بيانات الحساب"""
        from django.core.exceptions import ValidationError
        errors = {}

        # منع الحساب من أن يكون أباً لنفسه
        if self.parent_id and self.pk and self.parent_id == self.pk:
            errors["parent"] = "لا يمكن أن يكون الحساب أباً لنفسه"

        # منع المراجع الدائرية
        if self.parent_id and self.pk:
            visited = set()
            current = self.parent
            while current is not None:
                if current.pk == self.pk:
                    errors["parent"] = "تم اكتشاف مرجع دائري في شجرة الحسابات"
                    break
                if current.pk in visited:
                    break
                visited.add(current.pk)
                current = current.parent

        if errors:
            raise ValidationError(errors)

    def _calculate_level(self):
        """حساب مستوى الحساب في الشجرة"""
        level = 0
        parent = self.parent
        visited = set()
        while parent and parent.pk not in visited:
            level += 1
            visited.add(parent.pk)
            parent = parent.parent
        return level

    def get_balance(self):
        """حساب الرصيد الفعلي من القيود"""
        from django.db.models import Sum

        debits = self.transaction_lines.aggregate(total=Sum("debit"))[
            "total"
        ] or Decimal("0.00")

        credits = self.transaction_lines.aggregate(total=Sum("credit"))[
            "total"
        ] or Decimal("0.00")

        if self.account_type.normal_balance == "debit":
            return self.opening_balance + debits - credits
        else:
            return self.opening_balance + credits - debits

    def update_balance(self):
        """تحديث الرصيد الحالي"""
        self.current_balance = self.get_balance()
        self.save(update_fields=["current_balance", "updated_at"])

    def save(self, *args, **kwargs):
        from core.utils.general import convert_model_arabic_numbers
        
        # تحويل الأرقام العربية إلى إنجليزية
        convert_model_arabic_numbers(self, ['code', 'name', 'name_en'])
        
        # التأكد من أن الكود لا يحتوي على مسافات
        if self.code:
            self.code = self.code.strip()
        super().save(*args, **kwargs)


class Transaction(models.Model):
    """القيود المحاسبية"""

    TRANSACTION_TYPES = [
        ("payment", "دفعة من عميل"),
        ("advance", "عربون"),
        ("invoice", "فاتورة مبيعات"),
        ("refund", "استرداد"),
        ("expense", "مصروف"),
        ("transfer", "تحويل بين حسابات"),
        ("adjustment", "تسوية"),
        ("opening", "رصيد افتتاحي"),
    ]

    STATUS_CHOICES = [
        ("draft", "مسودة"),
        ("posted", "مرحّل"),
        ("cancelled", "ملغي"),
    ]

    transaction_number = models.CharField(
        _("رقم القيد"), max_length=50, unique=True, db_index=True
    )
    transaction_type = models.CharField(
        _("نوع القيد"), max_length=20, choices=TRANSACTION_TYPES
    )
    status = models.CharField(
        _("الحالة"), max_length=20, choices=STATUS_CHOICES, default="draft"
    )

    date = models.DateField(_("التاريخ"), default=timezone.now)
    description = models.TextField(_("البيان"))
    reference = models.CharField(_("المرجع"), max_length=100, blank=True)

    # الروابط
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounting_transactions",
        verbose_name=_("العميل"),
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounting_transactions",
        verbose_name=_("الطلب"),
    )
    payment = models.ForeignKey(
        "orders.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounting_transactions",
        verbose_name=_("الدفعة"),
    )

    # المبالغ
    total_debit = models.DecimalField(
        _("إجمالي المدين"), max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    total_credit = models.DecimalField(
        _("إجمالي الدائن"), max_digits=15, decimal_places=2, default=Decimal("0.00")
    )

    branch = models.ForeignKey(
        "accounts.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounting_transactions",
        verbose_name=_("الفرع"),
    )

    notes = models.TextField(_("ملاحظات"), blank=True)

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_transactions",
        verbose_name=_("تم الإنشاء بواسطة"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_transactions",
        verbose_name=_("آخر تعديل بواسطة"),
        editable=False,
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_transactions",
        verbose_name=_("تم الترحيل بواسطة"),
    )
    posted_at = models.DateTimeField(_("تاريخ الترحيل"), null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_transactions",
        verbose_name=_("تمت الموافقة بواسطة"),
    )
    approved_at = models.DateTimeField(_("تاريخ الموافقة"), null=True, blank=True)

    class Meta:
        verbose_name = _("قيد محاسبي")
        verbose_name_plural = _("القيود المحاسبية")
        ordering = ["-date", "-created_at"]
        permissions = [
            ("can_post_transaction", "يمكنه ترحيل القيود المحاسبية"),
            ("can_void_transaction", "يمكنه إلغاء القيود المحاسبية"),
            ("can_approve_transaction", "يمكنه الموافقة على القيود المحاسبية"),
            ("can_view_reports", "يمكنه عرض التقارير المالية"),
            ("can_export_reports", "يمكنه تصدير التقارير المالية"),
        ]
        indexes = [
            models.Index(fields=["transaction_number"], name="txn_number_idx"),
            models.Index(fields=["transaction_type"], name="txn_type_idx"),
            models.Index(fields=["date"], name="txn_date_idx"),
            models.Index(fields=["status"], name="txn_status_idx"),
            models.Index(fields=["customer"], name="txn_customer_idx"),
            models.Index(fields=["order"], name="txn_order_idx"),
        ]

    def __str__(self):
        return f"{self.transaction_number} - {self.get_transaction_type_display()}"

    @property
    def is_balanced(self):
        """التحقق من توازن القيد"""
        return self.total_debit == self.total_credit

    def calculate_totals(self):
        """حساب إجمالي المدين والدائن"""
        totals = self.lines.aggregate(
            total_debit=Sum("debit"), total_credit=Sum("credit")
        )
        self.total_debit = totals["total_debit"] or Decimal("0.00")
        self.total_credit = totals["total_credit"] or Decimal("0.00")
        self.save(update_fields=["total_debit", "total_credit"])

    def post(self, user=None):
        """ترحيل القيد وتحديث أرصدة الحسابات"""
        from django.db import transaction as db_transaction

        # إعادة حساب الإجماليات قبل التحقق من التوازن
        totals = self.lines.aggregate(
            total_debit=Sum("debit"), total_credit=Sum("credit")
        )
        self.total_debit = totals["total_debit"] or Decimal("0.00")
        self.total_credit = totals["total_credit"] or Decimal("0.00")

        if self.total_debit != self.total_credit:
            raise ValueError("القيد غير متوازن - لا يمكن الترحيل")

        if self.status == "posted":
            raise ValueError("القيد مرحّل مسبقاً")

        if self.status == "cancelled":
            raise ValueError("القيد ملغي - لا يمكن ترحيله")

        if self.lines.count() < 2:
            raise ValueError("يجب أن يحتوي القيد على سطرين على الأقل")

        # التحقق من صلاحية الحسابات
        for line in self.lines.select_related('account'):
            if not line.account.is_active:
                raise ValueError(f"الحساب {line.account.code} - {line.account.name} غير نشط")
            if not line.account.allow_transactions:
                raise ValueError(f"الحساب {line.account.code} - {line.account.name} لا يسمح بالقيود المباشرة")

        with db_transaction.atomic():
            self.status = "posted"
            self.posted_by = user
            self.posted_at = timezone.now()
            self.save(update_fields=["status", "posted_by", "posted_at", "total_debit", "total_credit"])

            # تحديث أرصدة الحسابات
            for line in self.lines.select_related('account'):
                line.account.update_balance()

    def cancel(self, user=None):
        """إلغاء القيد"""
        if self.status == "cancelled":
            raise ValueError("القيد ملغي مسبقاً")

        self.status = "cancelled"
        self.save(update_fields=["status", "updated_at"])

        # إعادة حساب أرصدة الحسابات المتأثرة
        for line in self.lines.select_related('account'):
            line.account.update_balance()

    def create_reversal(self, user=None, description=None):
        """إنشاء قيد عكسي"""
        if self.status != "posted":
            raise ValueError("يمكن عكس القيود المرحّلة فقط")

        reversal = Transaction.objects.create(
            transaction_type=self.transaction_type,
            date=timezone.now().date(),
            description=description or f"قيد عكسي للقيد {self.transaction_number}",
            reference=f"REV-{self.transaction_number}",
            customer=self.customer,
            order=self.order,
            created_by=user,
            status="draft",
        )

        # عكس بنود القيد (المدين يصبح دائن والعكس)
        for line in self.lines.all():
            TransactionLine.objects.create(
                transaction=reversal,
                account=line.account,
                debit=line.credit,
                credit=line.debit,
                description=f"عكس: {line.description}",
            )

        reversal.calculate_totals()
        return reversal

    def save(self, *args, **kwargs):
        # تحويل الأرقام العربية إلى إنجليزية
        from core.utils import convert_model_arabic_numbers

        convert_model_arabic_numbers(self, ["transaction_number"])

        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        super().save(*args, **kwargs)

    @classmethod
    def generate_transaction_number(cls):
        """توليد رقم قيد فريد - يعمل من خلال البحث عن آخر رقم وزيادته"""
        from django.db import connection

        today = timezone.now()
        prefix = f"TXN-{today.strftime('%Y%m')}-"

        with connection.cursor() as cursor:
            # نبحث عن آخر transaction_number يبدأ بالـ prefix ونستخرج الرقم منه
            cursor.execute(
                "SELECT transaction_number FROM accounting_transaction "
                "WHERE transaction_number LIKE %s "
                "ORDER BY CAST(SUBSTRING(transaction_number FROM %s) AS INTEGER) DESC "
                "LIMIT 1",
                [f"{prefix}%", len(prefix) + 1]
            )
            row = cursor.fetchone()
            if row:
                try:
                    last_num = int(row[0].split("-")[-1])
                except (IndexError, ValueError):
                    last_num = 0
            else:
                last_num = 0

        return f"{prefix}{last_num + 1:05d}"


class TransactionLine(models.Model):
    """بنود القيد المحاسبي"""

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="lines",
        verbose_name=_("القيد"),
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="transaction_lines",
        verbose_name=_("الحساب"),
    )

    debit = models.DecimalField(
        _("مدين"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    credit = models.DecimalField(
        _("دائن"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    description = models.CharField(_("البيان"), max_length=500, blank=True)

    class Meta:
        verbose_name = _("بند القيد")
        verbose_name_plural = _("بنود القيد")
        ordering = ["id"]
        indexes = [
            models.Index(fields=['transaction'], name='txnline_txn_idx'),
            models.Index(fields=['account'], name='txnline_acc_idx'),
            models.Index(fields=['transaction', 'account'], name='txnline_txn_acc_idx'),
        ]

    def __str__(self):
        return f"{self.account.code}: مدين {self.debit} / دائن {self.credit}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.debit > 0 and self.credit > 0:
            raise ValidationError("لا يمكن أن يكون المدين والدائن موجبين في نفس البند")
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("يجب أن يكون أحد المدين أو الدائن موجباً")


class TransactionAttachment(models.Model):
    """مرفقات القيد المحاسبي"""

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("القيد"),
    )
    file = models.FileField(
        _("الملف"),
        upload_to="accounting/attachments/%Y/%m/",
    )
    file_name = models.CharField(_("اسم الملف"), max_length=255, blank=True)
    description = models.CharField(_("وصف المرفق"), max_length=500, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_attachments",
        verbose_name=_("تم الرفع بواسطة"),
    )
    uploaded_at = models.DateTimeField(_("تاريخ الرفع"), auto_now_add=True)

    class Meta:
        verbose_name = _("مرفق القيد")
        verbose_name_plural = _("مرفقات القيود")
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"مرفق: {self.file_name or self.file.name} - قيد #{self.transaction_id}"

    def save(self, *args, **kwargs):
        if not self.file_name and self.file:
            self.file_name = self.file.name.split("/")[-1]
        super().save(*args, **kwargs)


class CustomerFinancialSummary(models.Model):
    """ملخص الوضع المالي للعميل"""

    FINANCIAL_STATUS = [
        ("clear", "بريء الذمة"),
        ("has_debt", "عليه مستحقات"),
        ("has_credit", "له رصيد"),
    ]

    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="financial_summary",
        verbose_name=_("العميل"),
    )

    # إجماليات الطلبات
    total_orders_count = models.PositiveIntegerField(_("عدد الطلبات"), default=0)
    total_orders_amount = models.DecimalField(
        _("إجمالي قيمة الطلبات"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # المدفوعات
    total_paid = models.DecimalField(
        _("إجمالي المدفوع"), max_digits=15, decimal_places=2, default=Decimal("0.00")
    )

    # العربون/السلف
    total_advances = models.DecimalField(
        _("إجمالي العربون"), max_digits=15, decimal_places=2, default=Decimal("0.00")
    )
    remaining_advances = models.DecimalField(
        _("رصيد العربون المتبقي"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # المديونية
    total_debt = models.DecimalField(
        _("إجمالي المديونية"), max_digits=15, decimal_places=2, default=Decimal("0.00")
    )

    # الحالة المالية
    financial_status = models.CharField(
        _("الحالة المالية"), max_length=20, choices=FINANCIAL_STATUS, default="clear"
    )

    last_payment_date = models.DateTimeField(_("تاريخ آخر دفعة"), null=True, blank=True)
    last_order_date = models.DateTimeField(_("تاريخ آخر طلب"), null=True, blank=True)

    last_updated = models.DateTimeField(_("آخر تحديث"), auto_now=True)

    class Meta:
        verbose_name = _("ملخص مالي للعميل")
        verbose_name_plural = _("ملخصات مالية للعملاء")
        indexes = [
            # Single-column indexes
            models.Index(fields=['customer'], name='cfs_customer_idx'),
            models.Index(fields=['total_debt'], name='cfs_debt_idx'),
            models.Index(fields=['financial_status'], name='cfs_status_idx'),
            models.Index(fields=['last_updated'], name='cfs_updated_idx'),
            models.Index(fields=['last_payment_date'], name='cfs_last_pay_idx'),
            # Composite indexes للاستعلامات المعقدة
            models.Index(fields=['financial_status', 'total_debt'], name='cfs_status_debt_idx'),
            models.Index(fields=['total_debt', 'last_updated'], name='cfs_debt_upd_idx'),
        ]

    def __str__(self):
        return f"ملخص مالي: {self.customer.name}"

    def refresh(self):
        """تحديث الملخص المالي من البيانات الفعلية — استعلام DB بدلاً من حلقة Python"""
        from django.db.models import (
            Count, DecimalField, F, OuterRef, Subquery, Sum, Value,
        )
        from django.db.models.functions import Coalesce

        from orders.models import Order, OrderItem, Payment
        from accounting.performance_utils import invalidate_customer_cache

        # ── إجماليات الطلبات — استعلام DB واحد ──
        # Subquery: مجموع خصومات العناصر لكل طلب
        item_discount_sq = (
            OrderItem.objects.filter(order=OuterRef("pk"))
            .values("order")
            .annotate(_total=Sum("discount_amount"))
            .values("_total")
        )

        orders_agg = (
            Order.objects.filter(customer=self.customer)
            .annotate(
                _item_disc=Coalesce(
                    Subquery(item_discount_sq, output_field=DecimalField()),
                    Value(Decimal("0.00")),
                ),
                _final_price=(
                    Coalesce(F("total_amount"), Value(Decimal("0.00")))
                    - F("_item_disc")
                    - Coalesce(F("administrative_discount_amount"), Value(Decimal("0.00")))
                    + Coalesce(F("financial_addition"), Value(Decimal("0.00")))
                ),
            )
            .aggregate(
                total_count=Count("id"),
                total_amount=Sum("_final_price"),
                last_order_date=models.Max("created_at"),
            )
        )

        self.total_orders_count = orders_agg["total_count"]
        self.total_orders_amount = orders_agg["total_amount"] or Decimal("0.00")
        last_order_dt = orders_agg["last_order_date"]
        if last_order_dt:
            self.last_order_date = last_order_dt

        # ── إجمالي المدفوع + آخر دفعة + رصيد الدفعات العامة — استعلامان فقط ──
        payment_agg = Payment.objects.filter(customer=self.customer).aggregate(
            total=Sum("amount"),
            last_date=models.Max("payment_date"),
        )
        self.total_paid = payment_agg["total"] or Decimal("0.00")
        if payment_agg["last_date"]:
            self.last_payment_date = payment_agg["last_date"]

        # رصيد الدفعات العامة غير المخصصة بالكامل
        general_agg = (
            Payment.objects.filter(customer=self.customer, payment_type="general")
            .aggregate(total=Sum("amount"), allocated=Sum("allocated_amount"))
        )
        total_general = general_agg["total"] or Decimal("0.00")
        total_allocated = general_agg["allocated"] or Decimal("0.00")
        self.remaining_advances = total_general - total_allocated

        # ── حساب المديونية وتحديد الحالة ──
        self.total_debt = self.total_orders_amount - self.total_paid

        if self.total_debt > 0:
            self.financial_status = "has_debt"
        elif self.total_debt < 0 or self.remaining_advances > 0:
            self.financial_status = "has_credit"
        else:
            self.financial_status = "clear"

        self.save()

        # حذف الـ cache بعد التحديث
        try:
            invalidate_customer_cache(self.customer_id)
        except Exception:
            pass

    @property
    def status_badge_class(self):
        """CSS class للـ badge"""
        status_classes = {
            "clear": "bg-success",
            "has_debt": "bg-danger",
            "has_credit": "bg-info",
        }
        return status_classes.get(self.financial_status, "bg-secondary")

    @property
    def status_icon(self):
        """أيقونة الحالة"""
        status_icons = {
            "clear": "fa-check-circle",
            "has_debt": "fa-exclamation-triangle",
            "has_credit": "fa-wallet",
        }
        return status_icons.get(self.financial_status, "fa-question-circle")
    
    def get_orders_with_debt(self):
        """الحصول على الطلبات التي لديها رصيد متبقي — عبر استعلام DB"""
        from django.db.models import (
            DecimalField, F, OuterRef, Subquery, Sum, Value,
        )
        from django.db.models.functions import Coalesce

        from orders.models import Order, OrderItem

        item_discount_sq = (
            OrderItem.objects.filter(order=OuterRef("pk"))
            .values("order")
            .annotate(_total=Sum("discount_amount"))
            .values("_total")
        )

        return list(
            Order.objects.filter(customer=self.customer)
            .annotate(
                _item_disc=Coalesce(
                    Subquery(item_discount_sq, output_field=DecimalField()),
                    Value(Decimal("0.00")),
                ),
                _final_price=(
                    Coalesce(F("total_amount"), Value(Decimal("0.00")))
                    - F("_item_disc")
                    - Coalesce(F("administrative_discount_amount"), Value(Decimal("0.00")))
                    + Coalesce(F("financial_addition"), Value(Decimal("0.00")))
                ),
                _remaining=(
                    F("_final_price")
                    - Coalesce(F("paid_amount"), Value(Decimal("0.00")))
                ),
            )
            .filter(_remaining__gt=Decimal("0.01"))
        )


class AccountingSettings(models.Model):
    """إعدادات النظام المحاسبي"""

    # الحسابات الافتراضية
    default_cash_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("حساب الصندوق الافتراضي"),
    )
    default_bank_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("حساب البنك الافتراضي"),
    )
    default_revenue_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("حساب الإيرادات الافتراضي"),
    )
    default_receivables_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("حساب المدينين الافتراضي"),
    )

    # إعدادات عامة
    auto_post_transactions = models.BooleanField(
        _("ترحيل القيود تلقائياً"), default=True
    )
    require_transaction_approval = models.BooleanField(
        _("تتطلب موافقة على القيود"), default=False
    )

    fiscal_year_start = models.DateField(_("بداية السنة المالية"), default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("إعدادات المحاسبة")
        verbose_name_plural = _("إعدادات المحاسبة")

    def __str__(self):
        return "إعدادات النظام المحاسبي"

    @classmethod
    def get_settings(cls):
        """الحصول على الإعدادات أو إنشاؤها"""
        settings_obj, created = cls.objects.get_or_create(pk=1)
        return settings_obj


class BankAccount(models.Model):
    """
    نموذج الحسابات البنكية للشركة
    Company Bank Accounts Model
    """

    # معلومات البنك الأساسية
    bank_name = models.CharField(_("اسم البنك"), max_length=200, db_index=True)
    bank_name_en = models.CharField(_("اسم البنك بالإنجليزية"), max_length=200)
    bank_logo = models.ImageField(
        _("شعار البنك"), upload_to="bank_logos/", blank=True, null=True
    )

    # معلومات الحساب
    account_number = models.CharField(_("رقم الحساب"), max_length=100)
    iban = models.CharField(
        _("IBAN"),
        max_length=34,
        blank=True,
        help_text="International Bank Account Number",
    )
    swift_code = models.CharField(
        _("SWIFT Code"), max_length=11, blank=True, help_text="BIC/SWIFT Code"
    )
    branch = models.CharField(_("الفرع"), max_length=200, blank=True)
    branch_en = models.CharField(_("Branch Name"), max_length=200, blank=True)

    # معلومات صاحب الحساب
    account_holder = models.CharField(
        _("اسم صاحب الحساب"), max_length=200, default="الخواجة"
    )
    account_holder_en = models.CharField(
        _("Account Holder"), max_length=200, default="Elkhawaga"
    )

    # العملة والحساب المحاسبي
    currency = models.CharField(_("العملة"), max_length=3, default="EGP")
    linked_account = models.ForeignKey(
        "Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("الحساب المحاسبي المرتبط"),
        help_text="الحساب المحاسبي الذي يمثل هذا الحساب البنكي",
    )

    # QR Code System
    qr_code_base64 = models.TextField(
        _("QR Code Base64"), blank=True, help_text="Cached QR code image"
    )
    unique_code = models.CharField(
        _("الكود الفريد"),
        max_length=20,
        unique=True,
        db_index=True,
        help_text="كود فريد للحساب البنكي (مثال: CIB001, NBE001)",
    )

    # إعدادات العرض
    is_active = models.BooleanField(_("نشط"), default=True, db_index=True)
    is_primary = models.BooleanField(
        _("حساب رئيسي"), default=False, help_text="الحساب الافتراضي للتحصيل"
    )
    display_order = models.IntegerField(
        _("ترتيب العرض"), default=0, help_text="ترتيب عرض الحساب في القوائم"
    )
    show_in_qr = models.BooleanField(
        _("عرض في QR"), default=True, help_text="عرض في صفحة جميع الحسابات"
    )

    # Cloudflare Integration
    cloudflare_synced = models.BooleanField(_("متزامن مع Cloudflare"), default=False)
    last_synced_at = models.DateTimeField(_("آخر مزامنة"), null=True, blank=True)

    # ملاحظات وتفاصيل
    notes = models.TextField(_("ملاحظات"), blank=True)

    # تواريخ
    created_at = models.DateTimeField(_("تاريخ الإضافة"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_bank_accounts",
        verbose_name=_("أضيف بواسطة"),
    )

    class Meta:
        verbose_name = _("حساب بنكي")
        verbose_name_plural = _("الحسابات البنكية")
        ordering = ["display_order", "bank_name"]
        indexes = [
            models.Index(fields=["unique_code"]),
            models.Index(fields=["is_active", "display_order"]),
            models.Index(fields=["is_primary"]),
        ]

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"

    def save(self, *args, **kwargs):
        """حفظ الحساب مع توليد كود فريد تلقائياً"""
        if not self.unique_code:
            # توليد كود فريد من اسم البنك
            import re

            from django.utils.text import slugify

            # استخراج الأحرف الكبيرة من اسم البنك بالإنجليزية
            bank_initials = "".join(
                [c for c in self.bank_name_en.upper() if c.isalpha()]
            )[:3]

            # البحث عن آخر رقم مستخدم
            last_account = (
                BankAccount.objects.filter(unique_code__startswith=bank_initials)
                .order_by("-unique_code")
                .first()
            )

            if last_account:
                # استخراج الرقم وزيادته
                last_number = int(re.findall(r"\d+", last_account.unique_code)[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            self.unique_code = f"{bank_initials}{new_number:03d}"

        # التأكد من وجود حساب رئيسي واحد فقط
        if self.is_primary:
            BankAccount.objects.filter(is_primary=True).exclude(pk=self.pk).update(
                is_primary=False
            )

        super().save(*args, **kwargs)

    def generate_qr_code(self):
        """توليد QR Code للحساب البنكي"""
        import base64
        from io import BytesIO

        import qrcode
        from django.conf import settings

        # الحصول على رابط Cloudflare Worker
        cloudflare_url = getattr(
            settings, "CLOUDFLARE_WORKER_URL", "https://qr.elkhawaga.uk"
        )
        qr_url = f"{cloudflare_url}/bank/{self.unique_code}"

        # إنشاء QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)

        # توليد الصورة
        img = qr.make_image(fill_color="black", back_color="white")

        # تحويل إلى Base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        self.qr_code_base64 = f"data:image/png;base64,{img_str}"
        self.save(update_fields=["qr_code_base64"])

        return self.qr_code_base64

    def get_qr_url(self):
        """الحصول على رابط صفحة QR"""
        from django.conf import settings

        cloudflare_url = getattr(
            settings, "CLOUDFLARE_WORKER_URL", "https://qr.elkhawaga.uk"
        )
        return f"{cloudflare_url}/bank/{self.unique_code}"

    def to_cloudflare_dict(self):
        """تحويل الحساب إلى قاموس للمزامنة مع Cloudflare - مع تحويل شعار البنك إلى Base64"""
        import base64
        import os

        from django.conf import settings

        def image_to_base64(image_field):
            """تحويل ImageField إلى Base64 data URL"""
            if not image_field:
                return ""
            try:
                with image_field.open("rb") as img_file:
                    img_data = img_file.read()
                    img_base64 = base64.b64encode(img_data).decode("utf-8")
                    ext = os.path.splitext(image_field.name)[1].lower()
                    mime_types = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".gif": "image/gif",
                        ".webp": "image/webp",
                        ".svg": "image/svg+xml",
                    }
                    mime_type = mime_types.get(ext, "image/png")
                    return f"data:{mime_type};base64,{img_base64}"
            except Exception as e:
                print(f"خطأ في تحويل شعار البنك إلى Base64: {e}")
                return ""

        # تحويل شعار البنك إلى Base64
        logo_url = image_to_base64(self.bank_logo)

        return {
            "code": self.unique_code,
            "bank_name": self.bank_name,
            "bank_name_en": self.bank_name_en,
            "bank_logo": logo_url,
            "account_number": self.account_number,
            "iban": self.iban or "",
            "swift_code": self.swift_code or "",
            "branch": self.branch or "",
            "branch_en": self.branch_en or "",
            "account_holder": self.account_holder,
            "account_holder_en": self.account_holder_en,
            "currency": self.currency,
            "is_active": self.is_active,
            "is_primary": self.is_primary,
            "display_order": self.display_order,
        }

    @staticmethod
    def get_active_accounts():
        """الحصول على جميع الحسابات النشطة"""
        return BankAccount.objects.filter(is_active=True).order_by(
            "display_order", "bank_name"
        )

    @staticmethod
    def get_primary_account():
        """الحصول على الحساب الرئيسي"""
        return BankAccount.objects.filter(is_primary=True, is_active=True).first()
