"""
نماذج نظام المحاسبة المتكامل
Integrated Accounting System Models
"""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.db.models import Sum, F, Q


class AccountType(models.Model):
    """أنواع الحسابات المحاسبية"""
    ACCOUNT_CATEGORIES = [
        ('asset', 'أصول'),
        ('liability', 'التزامات'),
        ('equity', 'حقوق ملكية'),
        ('revenue', 'إيرادات'),
        ('expense', 'مصروفات'),
    ]
    
    NORMAL_BALANCE_CHOICES = [
        ('debit', 'مدين'),
        ('credit', 'دائن'),
    ]
    
    name = models.CharField(_('اسم النوع'), max_length=100)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True)
    category = models.CharField(_('التصنيف'), max_length=20, choices=ACCOUNT_CATEGORIES)
    code_prefix = models.CharField(_('بادئة الكود'), max_length=4)
    normal_balance = models.CharField(
        _('الرصيد الطبيعي'),
        max_length=10,
        choices=NORMAL_BALANCE_CHOICES,
        default='debit'
    )
    description = models.TextField(_('الوصف'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('نوع الحساب')
        verbose_name_plural = _('أنواع الحسابات')
        ordering = ['code_prefix']
    
    def __str__(self):
        return f"{self.code_prefix} - {self.name}"


class Account(models.Model):
    """دليل الحسابات - شجرة الحسابات"""
    code = models.CharField(_('كود الحساب'), max_length=20, unique=True, db_index=True)
    name = models.CharField(_('اسم الحساب'), max_length=200, db_index=True)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    account_type = models.ForeignKey(
        AccountType,
        on_delete=models.PROTECT,
        related_name='accounts',
        verbose_name=_('نوع الحساب')
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('الحساب الأب')
    )
    # ربط اختياري بالعميل للحسابات الفردية
    customer = models.OneToOneField(
        'customers.Customer',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='accounting_account',
        verbose_name=_('العميل المرتبط')
    )
    # ربط اختياري بالفرع
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounting_accounts',
        verbose_name=_('الفرع')
    )
    
    is_active = models.BooleanField(_('نشط'), default=True)
    is_system_account = models.BooleanField(_('حساب نظام'), default=False)
    allow_transactions = models.BooleanField(_('يسمح بالقيود'), default=True)
    
    # الأرصدة
    opening_balance = models.DecimalField(
        _('الرصيد الافتتاحي'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    current_balance = models.DecimalField(
        _('الرصيد الحالي'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    description = models.TextField(_('الوصف'), blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_accounts',
        verbose_name=_('تم الإنشاء بواسطة')
    )
    
    class Meta:
        verbose_name = _('حساب')
        verbose_name_plural = _('دليل الحسابات')
        ordering = ['code']
        indexes = [
            models.Index(fields=['code'], name='acc_code_idx'),
            models.Index(fields=['name'], name='acc_name_idx'),
            models.Index(fields=['account_type'], name='acc_type_idx'),
            models.Index(fields=['customer'], name='acc_customer_idx'),
            models.Index(fields=['is_active'], name='acc_active_idx'),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def full_path(self):
        """المسار الكامل للحساب في الشجرة"""
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return ' > '.join(path)
    
    @property
    def level(self):
        """مستوى الحساب في الشجرة"""
        level = 0
        parent = self.parent
        while parent:
            level += 1
            parent = parent.parent
        return level
    
    @property
    def has_children(self):
        """هل للحساب حسابات فرعية"""
        return self.children.exists()
    
    def get_balance(self):
        """حساب الرصيد الفعلي من القيود"""
        from django.db.models import Sum
        
        debits = self.transaction_lines.aggregate(
            total=Sum('debit')
        )['total'] or Decimal('0.00')
        
        credits = self.transaction_lines.aggregate(
            total=Sum('credit')
        )['total'] or Decimal('0.00')
        
        if self.account_type.normal_balance == 'debit':
            return self.opening_balance + debits - credits
        else:
            return self.opening_balance + credits - debits
    
    def update_balance(self):
        """تحديث الرصيد الحالي"""
        self.current_balance = self.get_balance()
        self.save(update_fields=['current_balance', 'updated_at'])
    
    def save(self, *args, **kwargs):
        # التأكد من أن الكود لا يحتوي على مسافات
        if self.code:
            self.code = self.code.strip()
        super().save(*args, **kwargs)


class Transaction(models.Model):
    """القيود المحاسبية"""
    TRANSACTION_TYPES = [
        ('payment', 'دفعة من عميل'),
        ('advance', 'عربون/سلفة'),
        ('invoice', 'فاتورة مبيعات'),
        ('refund', 'استرداد'),
        ('expense', 'مصروف'),
        ('transfer', 'تحويل بين حسابات'),
        ('adjustment', 'تسوية'),
        ('opening', 'رصيد افتتاحي'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('posted', 'مرحّل'),
        ('cancelled', 'ملغي'),
    ]
    
    transaction_number = models.CharField(
        _('رقم القيد'),
        max_length=50,
        unique=True,
        db_index=True
    )
    transaction_type = models.CharField(
        _('نوع القيد'),
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    date = models.DateField(_('التاريخ'), default=timezone.now)
    description = models.TextField(_('البيان'))
    reference = models.CharField(_('المرجع'), max_length=100, blank=True)
    
    # الروابط
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounting_transactions',
        verbose_name=_('العميل')
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounting_transactions',
        verbose_name=_('الطلب')
    )
    payment = models.ForeignKey(
        'orders.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounting_transactions',
        verbose_name=_('الدفعة')
    )
    
    # المبالغ
    total_debit = models.DecimalField(
        _('إجمالي المدين'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_credit = models.DecimalField(
        _('إجمالي الدائن'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accounting_transactions',
        verbose_name=_('الفرع')
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_transactions',
        verbose_name=_('تم الإنشاء بواسطة')
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posted_transactions',
        verbose_name=_('تم الترحيل بواسطة')
    )
    posted_at = models.DateTimeField(_('تاريخ الترحيل'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('قيد محاسبي')
        verbose_name_plural = _('القيود المحاسبية')
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['transaction_number'], name='txn_number_idx'),
            models.Index(fields=['transaction_type'], name='txn_type_idx'),
            models.Index(fields=['date'], name='txn_date_idx'),
            models.Index(fields=['status'], name='txn_status_idx'),
            models.Index(fields=['customer'], name='txn_customer_idx'),
            models.Index(fields=['order'], name='txn_order_idx'),
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
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        self.total_debit = totals['total_debit'] or Decimal('0.00')
        self.total_credit = totals['total_credit'] or Decimal('0.00')
        self.save(update_fields=['total_debit', 'total_credit'])
    
    def post(self, user=None):
        """ترحيل القيد وتحديث أرصدة الحسابات"""
        if not self.is_balanced:
            raise ValueError('القيد غير متوازن - لا يمكن الترحيل')
        
        if self.status == 'posted':
            raise ValueError('القيد مرحّل مسبقاً')
        
        # تحديث أرصدة الحسابات
        for line in self.lines.all():
            line.account.update_balance()
        
        self.status = 'posted'
        self.posted_by = user
        self.posted_at = timezone.now()
        self.save(update_fields=['status', 'posted_by', 'posted_at'])
    
    def save(self, *args, **kwargs):
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_transaction_number(cls):
        """توليد رقم قيد فريد"""
        today = timezone.now()
        prefix = f"TXN-{today.strftime('%Y%m')}-"
        
        last_txn = cls.objects.filter(
            transaction_number__startswith=prefix
        ).order_by('-transaction_number').first()
        
        if last_txn:
            try:
                last_num = int(last_txn.transaction_number.split('-')[-1])
                new_num = last_num + 1
            except (IndexError, ValueError):
                new_num = 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:05d}"


class TransactionLine(models.Model):
    """بنود القيد المحاسبي"""
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('القيد')
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='transaction_lines',
        verbose_name=_('الحساب')
    )
    
    debit = models.DecimalField(
        _('مدين'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    credit = models.DecimalField(
        _('دائن'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    description = models.CharField(_('البيان'), max_length=500, blank=True)
    
    class Meta:
        verbose_name = _('بند القيد')
        verbose_name_plural = _('بنود القيد')
        ordering = ['id']
    
    def __str__(self):
        return f"{self.account.code}: مدين {self.debit} / دائن {self.credit}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.debit > 0 and self.credit > 0:
            raise ValidationError('لا يمكن أن يكون المدين والدائن موجبين في نفس البند')
        if self.debit == 0 and self.credit == 0:
            raise ValidationError('يجب أن يكون أحد المدين أو الدائن موجباً')


class CustomerAdvance(models.Model):
    """سلف وعربون العملاء"""
    ADVANCE_STATUS = [
        ('active', 'نشط'),
        ('partially_used', 'مستخدم جزئياً'),
        ('fully_used', 'مستخدم بالكامل'),
        ('refunded', 'مسترد'),
        ('cancelled', 'ملغي'),
    ]
    
    advance_number = models.CharField(
        _('رقم العربون'),
        max_length=50,
        unique=True,
        db_index=True
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='advances',
        verbose_name=_('العميل')
    )
    
    amount = models.DecimalField(
        _('المبلغ'),
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    remaining_amount = models.DecimalField(
        _('المبلغ المتبقي'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    payment_method = models.CharField(
        _('طريقة الدفع'),
        max_length=20,
        choices=[
            ('cash', 'نقداً'),
            ('bank_transfer', 'تحويل بنكي'),
            ('check', 'شيك'),
        ],
        default='cash'
    )
    receipt_number = models.CharField(_('رقم الإيصال'), max_length=100, blank=True)
    
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=ADVANCE_STATUS,
        default='active'
    )
    
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    branch = models.ForeignKey(
        'accounts.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_advances',
        verbose_name=_('الفرع')
    )
    
    # القيد المحاسبي المرتبط
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='advance',
        verbose_name=_('القيد المحاسبي')
    )
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_advances',
        verbose_name=_('تم الإنشاء بواسطة')
    )
    
    class Meta:
        verbose_name = _('عربون/سلفة')
        verbose_name_plural = _('عربون وسلف العملاء')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer'], name='adv_customer_idx'),
            models.Index(fields=['status'], name='adv_status_idx'),
        ]
    
    def __str__(self):
        return f"{self.advance_number} - {self.customer.name} ({self.amount} ج.م)"
    
    def save(self, *args, **kwargs):
        if not self.advance_number:
            self.advance_number = self.generate_advance_number()
        if not self.pk:  # جديد
            self.remaining_amount = self.amount
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_advance_number(cls):
        """توليد رقم عربون فريد"""
        today = timezone.now()
        prefix = f"ADV-{today.strftime('%Y%m')}-"
        
        last_adv = cls.objects.filter(
            advance_number__startswith=prefix
        ).order_by('-advance_number').first()
        
        if last_adv:
            try:
                last_num = int(last_adv.advance_number.split('-')[-1])
                new_num = last_num + 1
            except (IndexError, ValueError):
                new_num = 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:05d}"
    
    def use_amount(self, amount, order=None):
        """استخدام جزء من العربون"""
        if amount > self.remaining_amount:
            raise ValueError('المبلغ المطلوب أكبر من الرصيد المتبقي')
        
        self.remaining_amount -= amount
        
        if self.remaining_amount == 0:
            self.status = 'fully_used'
        else:
            self.status = 'partially_used'
        
        self.save()
        
        # تسجيل الاستخدام
        AdvanceUsage.objects.create(
            advance=self,
            order=order,
            amount=amount,
            created_by=self.created_by
        )
        
        return self.remaining_amount
    
    @property
    def used_amount(self):
        """حساب المبلغ المستخدم"""
        return self.amount - self.remaining_amount


class AdvanceUsage(models.Model):
    """سجل استخدام العربون"""
    advance = models.ForeignKey(
        CustomerAdvance,
        on_delete=models.CASCADE,
        related_name='usages',
        verbose_name=_('العربون')
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='advance_usages',
        verbose_name=_('الطلب')
    )
    amount = models.DecimalField(
        _('المبلغ المستخدم'),
        max_digits=15,
        decimal_places=2
    )
    created_at = models.DateTimeField(_('تاريخ الاستخدام'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('تم بواسطة')
    )
    
    class Meta:
        verbose_name = _('استخدام عربون')
        verbose_name_plural = _('استخدامات العربون')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.advance.advance_number} - {self.amount} ج.م"


class CustomerFinancialSummary(models.Model):
    """ملخص الوضع المالي للعميل"""
    FINANCIAL_STATUS = [
        ('clear', 'بريء الذمة'),
        ('has_debt', 'عليه مستحقات'),
        ('has_credit', 'له رصيد'),
    ]
    
    customer = models.OneToOneField(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='financial_summary',
        verbose_name=_('العميل')
    )
    
    # إجماليات الطلبات
    total_orders_count = models.PositiveIntegerField(_('عدد الطلبات'), default=0)
    total_orders_amount = models.DecimalField(
        _('إجمالي قيمة الطلبات'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # المدفوعات
    total_paid = models.DecimalField(
        _('إجمالي المدفوع'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # العربون/السلف
    total_advances = models.DecimalField(
        _('إجمالي العربون'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    remaining_advances = models.DecimalField(
        _('رصيد العربون المتبقي'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # المديونية
    total_debt = models.DecimalField(
        _('إجمالي المديونية'),
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # الحالة المالية
    financial_status = models.CharField(
        _('الحالة المالية'),
        max_length=20,
        choices=FINANCIAL_STATUS,
        default='clear'
    )
    
    last_payment_date = models.DateTimeField(_('تاريخ آخر دفعة'), null=True, blank=True)
    last_order_date = models.DateTimeField(_('تاريخ آخر طلب'), null=True, blank=True)
    
    last_updated = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    
    class Meta:
        verbose_name = _('ملخص مالي للعميل')
        verbose_name_plural = _('ملخصات مالية للعملاء')
    
    def __str__(self):
        return f"ملخص مالي: {self.customer.name}"
    
    def refresh(self):
        """تحديث الملخص المالي من البيانات الفعلية"""
        from orders.models import Order, Payment
        from django.db.models import Sum, Count
        
        # إجماليات الطلبات
        orders = Order.objects.filter(customer=self.customer)
        orders_agg = orders.aggregate(
            count=Count('id'),
            total=Sum('final_price')
        )
        self.total_orders_count = orders_agg['count'] or 0
        self.total_orders_amount = orders_agg['total'] or Decimal('0.00')
        
        # إجمالي المدفوع
        payments = Payment.objects.filter(order__customer=self.customer)
        self.total_paid = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # العربون
        advances = CustomerAdvance.objects.filter(
            customer=self.customer,
            status__in=['active', 'partially_used']
        )
        advances_agg = advances.aggregate(
            total=Sum('amount'),
            remaining=Sum('remaining_amount')
        )
        self.total_advances = advances_agg['total'] or Decimal('0.00')
        self.remaining_advances = advances_agg['remaining'] or Decimal('0.00')
        
        # حساب المديونية
        self.total_debt = self.total_orders_amount - self.total_paid
        
        # تحديد الحالة المالية
        if self.total_debt > 0:
            self.financial_status = 'has_debt'
        elif self.total_debt < 0 or self.remaining_advances > 0:
            self.financial_status = 'has_credit'
        else:
            self.financial_status = 'clear'
        
        # آخر دفعة
        last_payment = payments.order_by('-payment_date').first()
        if last_payment:
            self.last_payment_date = last_payment.payment_date
        
        # آخر طلب
        last_order = orders.order_by('-created_at').first()
        if last_order:
            self.last_order_date = last_order.created_at
        
        self.save()
    
    @property
    def status_badge_class(self):
        """CSS class للـ badge"""
        status_classes = {
            'clear': 'bg-success',
            'has_debt': 'bg-danger',
            'has_credit': 'bg-info',
        }
        return status_classes.get(self.financial_status, 'bg-secondary')
    
    @property
    def status_icon(self):
        """أيقونة الحالة"""
        status_icons = {
            'clear': 'fa-check-circle',
            'has_debt': 'fa-exclamation-triangle',
            'has_credit': 'fa-wallet',
        }
        return status_icons.get(self.financial_status, 'fa-question-circle')


class AccountingSettings(models.Model):
    """إعدادات النظام المحاسبي"""
    # الحسابات الافتراضية
    default_cash_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('حساب الصندوق الافتراضي')
    )
    default_bank_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('حساب البنك الافتراضي')
    )
    default_revenue_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('حساب الإيرادات الافتراضي')
    )
    default_receivables_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('حساب المدينين الافتراضي')
    )
    default_advances_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('حساب سلف العملاء الافتراضي')
    )
    
    # إعدادات عامة
    auto_post_transactions = models.BooleanField(
        _('ترحيل القيود تلقائياً'),
        default=True
    )
    require_transaction_approval = models.BooleanField(
        _('تتطلب موافقة على القيود'),
        default=False
    )
    
    fiscal_year_start = models.DateField(
        _('بداية السنة المالية'),
        default=timezone.now
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('إعدادات المحاسبة')
        verbose_name_plural = _('إعدادات المحاسبة')
    
    def __str__(self):
        return 'إعدادات النظام المحاسبي'
    
    @classmethod
    def get_settings(cls):
        """الحصول على الإعدادات أو إنشاؤها"""
        settings_obj, created = cls.objects.get_or_create(pk=1)
        return settings_obj
