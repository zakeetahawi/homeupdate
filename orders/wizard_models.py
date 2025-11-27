"""
نماذج الويزارد لإنشاء الطلبات
Draft Order Models for Multi-Step Order Creation Wizard
"""
import json
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class DraftOrder(models.Model):
    """
    مسودة الطلب - تحتفظ بالبيانات أثناء عملية الإنشاء متعددة الخطوات
    """
    WIZARD_STEPS = [
        (1, 'البيانات الأساسية'),
        (2, 'نوع الطلب'),
        (3, 'عناصر الطلب'),
        (4, 'تفاصيل الفاتورة والدفع'),
        (5, 'العقد الإلكتروني'),
        (6, 'المراجعة والتأكيد'),
    ]
    
    # معلومات المستخدم والتتبع
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='draft_orders',
        verbose_name='أنشأ بواسطة'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')
    
    # تتبع الخطوة الحالية
    current_step = models.IntegerField(
        default=1,
        choices=WIZARD_STEPS,
        verbose_name='الخطوة الحالية'
    )
    completed_steps = models.JSONField(
        default=list,
        verbose_name='الخطوات المكتملة',
        help_text='قائمة بأرقام الخطوات التي تم إكمالها'
    )
    
    # الخطوة 1: البيانات الأساسية
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='draft_orders',
        verbose_name='العميل',
        null=True,
        blank=True
    )
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الفرع'
    )
    salesperson = models.ForeignKey(
        'accounts.Salesperson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='البائع'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('normal', 'عادي'),
            ('vip', 'VIP'),
        ],
        default='normal',
        verbose_name='وضع العميل'
    )
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    
    # الخطوة 2: نوع الطلب
    selected_type = models.CharField(
        max_length=30,
        choices=[
            ('accessory', 'إكسسوار'),
            ('installation', 'تركيب'),
            ('inspection', 'معاينة'),
            ('tailoring', 'تسليم'),
            ('products', 'منتجات'),
        ],
        blank=True,
        null=True,
        verbose_name='نوع الطلب'
    )
    related_inspection = models.ForeignKey(
        'inspections.Inspection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='المعاينة المرتبطة'
    )
    related_inspection_type = models.CharField(
        max_length=20,
        choices=[
            ('inspection', 'معاينة محددة'),
            ('customer_side', 'طرف العميل'),
        ],
        blank=True,
        null=True,
        verbose_name='نوع المعاينة المرتبطة'
    )
    
    # مقاسات طرف العميل
    customer_side_measurements = models.BooleanField(
        default=False,
        verbose_name='مقاسات طرف العميل'
    )
    measurement_agreement_file = models.FileField(
        upload_to='measurements/agreements/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='اتفاقية المقاسات (PDF)',
        help_text='يجب رفع ملف PDF لاتفاقية المقاسات'
    )
    
    # الخطوة 4: تفاصيل الفاتورة
    invoice_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='رقم الفاتورة الرئيسي')
    invoice_number_2 = models.CharField(max_length=100, blank=True, null=True, verbose_name='رقم فاتورة إضافي 1')
    invoice_number_3 = models.CharField(max_length=100, blank=True, null=True, verbose_name='رقم فاتورة إضافي 2')
    contract_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='رقم العقد الرئيسي')
    contract_number_2 = models.CharField(max_length=100, blank=True, null=True, verbose_name='رقم عقد إضافي 1')
    contract_number_3 = models.CharField(max_length=100, blank=True, null=True, verbose_name='رقم عقد إضافي 2')
    # صورة الفاتورة (إجبارية)
    invoice_image = models.ImageField(
        upload_to='invoices/images/drafts/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='صورة الفاتورة',
        help_text='يجب إرفاق صورة الفاتورة (JPG, PNG, GIF, WEBP)'
    )
    
    # الخطوة 5: العقد (إما إلكتروني أو ملف PDF)
    contract_type = models.CharField(
        max_length=20,
        choices=[
            ('electronic', 'عقد إلكتروني'),
            ('pdf', 'ملف PDF'),
        ],
        blank=True,
        null=True,
        verbose_name='نوع العقد'
    )
    contract_file = models.FileField(
        upload_to='contracts/drafts/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='ملف العقد'
    )
    
    # معلومات الدفع
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'نقدي'),
            ('card', 'بطاقة'),
            ('bank_transfer', 'تحويل بنكي'),
            ('installment', 'تقسيط'),
        ],
        default='cash',
        verbose_name='طريقة الدفع'
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='المبلغ المدفوع'
    )
    payment_notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات الدفع')
    
    # المجاميع المحسوبة (تُحدث تلقائياً)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='المجموع قبل الخصم'
    )
    total_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='إجمالي الخصم'
    )
    final_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='المجموع النهائي'
    )
    
    # بيانات إضافية مخزنة كـ JSON
    wizard_state = models.JSONField(
        default=dict,
        verbose_name='حالة الويزارد',
        help_text='بيانات مؤقتة إضافية للويزارد'
    )
    
    # حالة المسودة
    is_completed = models.BooleanField(
        default=False,
        verbose_name='مكتملة',
        help_text='تم تحويلها إلى طلب نهائي'
    )
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='تاريخ الإكمال')
    final_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_draft',
        verbose_name='الطلب النهائي'
    )
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'مسودة طلب'
        verbose_name_plural = 'مسودات الطلبات'
        indexes = [
            models.Index(fields=['created_by', 'is_completed']),
            models.Index(fields=['created_at']),
            models.Index(fields=['current_step']),
        ]
    
    def __str__(self):
        return f"مسودة #{self.pk} - {self.get_current_step_display()} - {self.created_by.username}"
    
    def calculate_totals(self):
        """حساب المجاميع من العناصر"""
        items = self.items.all()
        subtotal = Decimal('0.00')
        total_discount = Decimal('0.00')
        
        for item in items:
            item_total = item.quantity * item.unit_price
            item_discount = item_total * (item.discount_percentage / Decimal('100.0'))
            subtotal += item_total
            total_discount += item_discount
        
        self.subtotal = subtotal
        self.total_discount = total_discount
        self.final_total = subtotal - total_discount
        self.save(update_fields=['subtotal', 'total_discount', 'final_total'])
        
        return {
            'subtotal': self.subtotal,
            'total_discount': self.total_discount,
            'final_total': self.final_total,
            'remaining': self.final_total - self.paid_amount
        }
    
    def mark_step_complete(self, step_number):
        """تحديد خطوة كمكتملة"""
        if step_number not in self.completed_steps:
            self.completed_steps.append(step_number)
            self.save(update_fields=['completed_steps'])
    
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
        related_name='items',
        verbose_name='مسودة الطلب'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        verbose_name='المنتج'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name='الكمية'
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='سعر الوحدة'
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[
            MinValueValidator(Decimal('0.00')),
            MaxValueValidator(Decimal('100.00'))
        ],
        verbose_name='نسبة الخصم %'
    )
    item_type = models.CharField(
        max_length=20,
        choices=[
            ('product', 'منتج'),
            ('fabric', 'قماش'),
            ('accessory', 'إكسسوار'),
        ],
        default='product',
        verbose_name='نوع العنصر'
    )
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['id']
        verbose_name = 'عنصر مسودة طلب'
        verbose_name_plural = 'عناصر مسودات الطلبات'
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} × {self.unit_price}"
    
    @property
    def total_price(self):
        """السعر الإجمالي قبل الخصم"""
        return self.quantity * self.unit_price
    
    @property
    def discount_amount(self):
        """مبلغ الخصم"""
        return self.total_price * (self.discount_percentage / Decimal('100.0'))
    
    @property
    def final_price(self):
        """السعر النهائي بعد الخصم"""
        return self.total_price - self.discount_amount

