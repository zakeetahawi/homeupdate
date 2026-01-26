"""
نماذج الويزارد لإنشاء الطلبات
Draft Order Models for Multi-Step Order Creation Wizard
"""

import json
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class DraftOrderInvoiceImage(models.Model):
    """صور الفاتورة المتعددة لمسودة الطلب"""

    draft_order = models.ForeignKey(
        "DraftOrder",
        on_delete=models.CASCADE,
        related_name="invoice_images_new",
        verbose_name="مسودة الطلب",
    )
    image = models.ImageField(
        upload_to="invoices/images/drafts/%Y/%m/", verbose_name="صورة الفاتورة"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الرفع")

    class Meta:
        verbose_name = "صورة فاتورة مسودة"
        verbose_name_plural = "صور فواتير المسودات"
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"صورة فاتورة مسودة {self.draft_order.id} - {self.uploaded_at.strftime('%Y-%m-%d')}"


class DraftOrder(models.Model):
    """
    مسودة الطلب - تحتفظ بالبيانات أثناء عملية الإنشاء متعددة الخطوات
    """

    WIZARD_STEPS = [
        (1, "البيانات الأساسية"),
        (2, "نوع الطلب"),
        (3, "عناصر الطلب"),
        (4, "تفاصيل الفاتورة والدفع"),
        (5, "العقد الإلكتروني"),
        (6, "المراجعة والتأكيد"),
    ]

    # معلومات المستخدم والتتبع
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="draft_orders",
        verbose_name="أنشأ بواسطة",
    )
    last_modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modified_drafts",
        verbose_name="آخر تعديل بواسطة",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    # سجل التعديلات
    edit_history = models.JSONField(
        default=list,
        verbose_name="سجل التعديلات",
        help_text="سجل بجميع التعديلات على المسودة",
    )

    # تتبع الخطوة الحالية
    current_step = models.IntegerField(
        default=1, choices=WIZARD_STEPS, verbose_name="الخطوة الحالية"
    )
    completed_steps = models.JSONField(
        default=list,
        verbose_name="الخطوات المكتملة",
        help_text="قائمة بأرقام الخطوات التي تم إكمالها",
    )

    # الخطوة 1: البيانات الأساسية
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="draft_orders",
        verbose_name="العميل",
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "accounts.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="الفرع",
    )
    original_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edit_drafts",
        verbose_name="الطلب الأصلي المراد تعديله",
    )
    salesperson = models.ForeignKey(
        "accounts.Salesperson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="البائع",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("normal", "عادي"),
            ("vip", "VIP"),
        ],
        default="normal",
        verbose_name="وضع العميل",
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")

    # الخطوة 2: نوع الطلب
    selected_type = models.CharField(
        max_length=30,
        choices=[
            ("accessory", "إكسسوار"),
            ("installation", "تركيب"),
            ("inspection", "معاينة"),
            ("tailoring", "تسليم"),
            ("products", "منتجات"),
        ],
        blank=True,
        null=True,
        verbose_name="نوع الطلب",
    )
    related_inspection = models.ForeignKey(
        "inspections.Inspection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="المعاينة المرتبطة",
    )
    related_inspection_type = models.CharField(
        max_length=20,
        choices=[
            ("inspection", "معاينة محددة"),
            ("customer_side", "طرف العميل"),
        ],
        blank=True,
        null=True,
        verbose_name="نوع المعاينة المرتبطة",
    )

    # مقاسات طرف العميل
    customer_side_measurements = models.BooleanField(
        default=False, verbose_name="مقاسات طرف العميل"
    )
    measurement_agreement_file = models.FileField(
        upload_to="measurements/agreements/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="اتفاقية المقاسات (PDF)",
        help_text="يجب رفع ملف PDF لاتفاقية المقاسات",
    )

    # الخطوة 4: تفاصيل الفاتورة
    invoice_number = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="رقم الفاتورة الرئيسي"
    )
    invoice_number_2 = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="رقم فاتورة إضافي 1"
    )
    invoice_number_3 = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="رقم فاتورة إضافي 2"
    )
    contract_number = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="رقم العقد الرئيسي"
    )
    contract_number_2 = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="رقم عقد إضافي 1"
    )
    contract_number_3 = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="رقم عقد إضافي 2"
    )
    delivery_location = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="موقع التسليم"
    )
    # صورة الفاتورة (إجبارية)
    invoice_image = models.ImageField(
        upload_to="invoices/images/drafts/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="صورة الفاتورة",
        help_text="يجب إرفاق صورة الفاتورة (JPG, PNG, GIF, WEBP)",
    )

    # الخطوة 5: العقد (إما إلكتروني أو ملف PDF)
    contract_type = models.CharField(
        max_length=20,
        choices=[
            ("electronic", "عقد إلكتروني"),
            ("pdf", "ملف PDF"),
        ],
        blank=True,
        null=True,
        verbose_name="نوع العقد",
    )
    contract_file = models.FileField(
        upload_to="contracts/drafts/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="ملف العقد",
    )

    # معلومات الدفع
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("cash", "نقدي"),
            ("card", "بطاقة"),
            ("bank_transfer", "تحويل بنكي"),
            ("installment", "تقسيط"),
        ],
        default="cash",
        verbose_name="طريقة الدفع",
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="المبلغ المدفوع",
    )
    payment_notes = models.TextField(
        blank=True, null=True, verbose_name="ملاحظات الدفع"
    )

    # المجاميع المحسوبة (تُحدث تلقائياً)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="المجموع قبل الخصم",
    )
    total_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="إجمالي الخصم",
    )
    final_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="المجموع النهائي",
    )

    # بيانات إضافية مخزنة كـ JSON
    wizard_state = models.JSONField(
        default=dict,
        verbose_name="حالة الويزارد",
        help_text="بيانات مؤقتة إضافية للويزارد",
    )

    # حالة المسودة
    is_completed = models.BooleanField(
        default=False, verbose_name="مكتملة", help_text="تم تحويلها إلى طلب نهائي"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="تاريخ الإكمال"
    )
    final_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_draft",
        verbose_name="الطلب النهائي",
    )

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "مسودة طلب"
        verbose_name_plural = "مسودات الطلبات"
        indexes = [
            # ⚡ Indexes أساسية محسّنة
            models.Index(
                fields=["created_by", "is_completed"], name="draft_user_complete_idx"
            ),
            models.Index(
                fields=["created_by", "is_completed", "-updated_at"],
                name="draft_user_comp_upd_idx",
            ),
            models.Index(fields=["created_at"], name="draft_created_idx"),
            models.Index(fields=["updated_at"], name="draft_updated_idx"),
            models.Index(fields=["current_step"], name="draft_step_idx"),
            # ⚡ Indexes للعلاقات
            models.Index(
                fields=["customer", "is_completed"], name="draft_customer_comp_idx"
            ),
            models.Index(
                fields=["branch", "is_completed"], name="draft_branch_comp_idx"
            ),
            models.Index(
                fields=["salesperson", "is_completed"], name="draft_sales_comp_idx"
            ),
            # ⚡ Indexes للنوع والحالة
            models.Index(
                fields=["selected_type", "is_completed"], name="draft_type_comp_idx"
            ),
            models.Index(
                fields=["status", "is_completed"], name="draft_status_comp_idx"
            ),
            # ⚡ Index مركّب للبحث السريع
            models.Index(
                fields=["created_by", "is_completed", "current_step", "-updated_at"],
                name="draft_search_idx",
            ),
        ]

    def __str__(self):
        return f"مسودة #{self.pk} - {self.get_current_step_display()} - {self.created_by.username}"

    def calculate_totals(self):
        """
        ⚡ حساب المجاميع من العناصر (OPTIMIZED)
        استخدام aggregation بدلاً من الحلقات
        """
        from django.db.models import DecimalField, F, Sum
        from django.db.models.functions import Coalesce

        # ⚡ حساب المجاميع بـ query واحد بدلاً من N+1
        aggregates = self.items.aggregate(
            total_amount=Coalesce(
                Sum(
                    F("quantity") * F("unit_price"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                Decimal("0.00"),
            ),
            total_discount_amount=Coalesce(
                Sum(
                    "discount_amount",
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                Decimal("0.00"),
            ),
        )

        self.subtotal = aggregates["total_amount"]
        self.total_discount = aggregates["total_discount_amount"]
        self.final_total = self.subtotal - self.total_discount
        self.save(update_fields=["subtotal", "total_discount", "final_total"])

        return {
            "subtotal": self.subtotal,
            "total_discount": self.total_discount,
            "final_total": self.final_total,
            "remaining": self.final_total - self.paid_amount,
        }

    def log_edit(self, user, action, details):
        """تسجيل تعديل على المسودة"""
        if not isinstance(self.edit_history, list):
            self.edit_history = []

        edit_entry = {
            "timestamp": timezone.now().isoformat(),
            "user_id": user.id,
            "user_name": user.get_full_name(),
            "action": action,
            "details": details,
        }
        self.edit_history.append(edit_entry)
        self.last_modified_by = user
        self.save(update_fields=["edit_history", "last_modified_by", "updated_at"])

    def get_edit_summary(self):
        """الحصول على ملخص التعديلات"""
        if not self.edit_history:
            return []

        # تجميع التعديلات حسب المستخدم
        summary = {}
        for edit in self.edit_history:
            user_name = edit.get("user_name", "مستخدم غير معروف")
            if user_name not in summary:
                summary[user_name] = {"user_name": user_name, "actions": [], "count": 0}
            summary[user_name]["actions"].append(edit)
            summary[user_name]["count"] += 1

        return list(summary.values())

    def mark_step_complete(self, step_number):
        """تحديد خطوة كمكتملة"""
        if step_number not in self.completed_steps:
            self.completed_steps.append(step_number)
            self.save(update_fields=["completed_steps"])

    def can_access_step(self, step_number):
        """التحقق من إمكانية الوصول لخطوة معينة"""
        if step_number == 1:
            return True
        # يجب إكمال الخطوة السابقة للوصول للخطوة الحالية
        return (step_number - 1) in self.completed_steps


class DraftOrderItem(models.Model):
    """
    عناصر مسودة الطلب
    """

    draft_order = models.ForeignKey(
        DraftOrder,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="مسودة الطلب",
    )
    product = models.ForeignKey(
        "inventory.Product", on_delete=models.CASCADE, verbose_name="المنتج"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        verbose_name="الكمية",
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="سعر الوحدة",
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        verbose_name="نسبة الخصم %",
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="مبلغ الخصم",
        help_text="يُحسب تلقائياً من الكمية والسعر ونسبة الخصم",
    )
    item_type = models.CharField(
        max_length=20,
        choices=[
            ("product", "منتج"),
            ("fabric", "قماش"),
            ("accessory", "إكسسوار"),
        ],
        default="product",
        verbose_name="نوع العنصر",
    )
    is_manual_price = models.BooleanField(
        default=False,
        verbose_name="سعر يدوي",
        help_text="هل تم تعديل سعر هذا العنصر يدوياً؟",
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")

    # تتبع التعديلات
    original_item_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="معرف العنصر الأصلي",
        help_text="يستخدم عند تعديل الطلب لربط عنصر المسودة بالعنصر الأصلي",
    )

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_draft_items",
        verbose_name="أضيف بواسطة",
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modified_draft_items",
        verbose_name="عُدل بواسطة",
    )
    modification_note = models.TextField(
        blank=True, null=True, verbose_name="ملاحظة التعديل"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "عنصر مسودة طلب"
        verbose_name_plural = "عناصر مسودات الطلبات"
        indexes = [
            # ⚡ Indexes محسّنة لعناصر المسودة
            models.Index(fields=["draft_order"], name="draftitem_draft_idx"),
            models.Index(fields=["product"], name="draftitem_product_idx"),
            models.Index(
                fields=["draft_order", "item_type"], name="draftitem_draft_type_idx"
            ),
            models.Index(
                fields=["draft_order", "product"], name="draftitem_draft_prod_idx"
            ),
            models.Index(fields=["item_type"], name="draftitem_type_idx"),
            models.Index(fields=["created_at"], name="draftitem_created_idx"),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.quantity} × {self.unit_price}"

    @property
    def total_price(self):
        """السعر الإجمالي قبل الخصم"""
        return self.quantity * self.unit_price

    @property
    def final_price(self):
        """السعر النهائي بعد الخصم"""
        return self.total_price - self.discount_amount

    def save(self, *args, **kwargs):
        """حساب مبلغ الخصم تلقائياً قبل الحفظ"""
        if self.discount_percentage and self.discount_percentage > 0:
            if self.quantity and self.unit_price:
                total = self.quantity * self.unit_price
                self.discount_amount = total * (
                    self.discount_percentage / Decimal("100.0")
                )
        else:
            self.discount_amount = Decimal("0.00")
        super().save(*args, **kwargs)
