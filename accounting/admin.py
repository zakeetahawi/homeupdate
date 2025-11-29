from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from .models import (
    AccountType, Account, Transaction, TransactionLine,
    CustomerAdvance, AdvanceUsage, CustomerFinancialSummary,
    AccountingSettings
)


# ============================================
# Inline Admin Classes
# ============================================

class TransactionLineInline(admin.TabularInline):
    """
    سطور القيد المحاسبي
    """
    model = TransactionLine
    extra = 2
    min_num = 2
    fields = ['account', 'debit', 'credit', 'description']
    autocomplete_fields = ['account']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('account')


class AdvanceUsageInline(admin.TabularInline):
    """
    استخدامات السلفة
    """
    model = AdvanceUsage
    extra = 0
    readonly_fields = ['order', 'amount', 'created_at', 'created_by']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class AccountChildInline(admin.TabularInline):
    """
    الحسابات الفرعية
    """
    model = Account
    fk_name = 'parent'
    extra = 0
    fields = ['code', 'name', 'account_type', 'is_active', 'current_balance']
    readonly_fields = ['current_balance']
    show_change_link = True


# ============================================
# Model Admin Classes
# ============================================

@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):
    """
    إدارة أنواع الحسابات
    """
    list_display = ['code_prefix', 'name', 'name_en', 'category', 'normal_balance', 'accounts_count', 'is_active']
    list_filter = ['category', 'normal_balance', 'is_active']
    search_fields = ['code_prefix', 'name', 'name_en']
    ordering = ['code_prefix']
    list_editable = ['is_active']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('code_prefix', 'name', 'name_en')
        }),
        ('الإعدادات', {
            'fields': ('category', 'normal_balance', 'is_active', 'description')
        }),
    )
    
    def accounts_count(self, obj):
        count = obj.accounts.count()
        url = reverse('admin:accounting_account_changelist') + f'?account_type__id__exact={obj.id}'
        return format_html('<a href="{}">{} حساب</a>', url, count)
    accounts_count.short_description = 'عدد الحسابات'


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    """
    إدارة الحسابات - شجرة الحسابات
    """
    list_display = [
        'code', 'name', 'account_type', 'parent_link', 
        'get_level', 'colored_balance', 'is_active', 'customer_linked'
    ]
    list_filter = ['account_type', 'is_active', 'is_system_account', 'branch']
    search_fields = ['code', 'name', 'name_en', 'customer__name', 'customer__phone']
    ordering = ['code']
    autocomplete_fields = ['parent', 'customer']
    list_per_page = 50
    list_editable = ['is_active']
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('code', 'name', 'name_en', 'account_type', 'parent')
        }),
        ('التفاصيل', {
            'fields': ('description', 'branch', 'is_active', 'is_system_account', 'allow_transactions')
        }),
        ('ربط العميل', {
            'fields': ('customer',),
            'classes': ('collapse',),
            'description': 'لربط الحساب بعميل معين'
        }),
        ('الأرصدة', {
            'fields': ('opening_balance', 'current_balance'),
            'classes': ('collapse',),
        }),
        ('ملاحظات', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['current_balance', 'created_at', 'updated_at', 'created_by']
    inlines = [AccountChildInline]
    
    def parent_link(self, obj):
        if obj.parent:
            url = reverse('admin:accounting_account_change', args=[obj.parent.id])
            return format_html('<a href="{}">{}</a>', url, obj.parent.name)
        return '-'
    parent_link.short_description = 'الحساب الرئيسي'
    
    def get_level(self, obj):
        return obj.level
    get_level.short_description = 'المستوى'
    
    def customer_linked(self, obj):
        if obj.customer:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: gray;">-</span>')
    customer_linked.short_description = 'عميل مرتبط'
    
    def colored_balance(self, obj):
        balance = obj.current_balance
        if balance > 0:
            color = 'green'
        elif balance < 0:
            color = 'red'
        else:
            color = 'gray'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:,.2f}</span>',
            color, balance
        )
    colored_balance.short_description = 'الرصيد'
    colored_balance.admin_order_field = 'current_balance'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'account_type', 'parent', 'customer', 'branch'
        )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    إدارة القيود المحاسبية
    """
    list_display = [
        'transaction_number', 'date', 'transaction_type',
        'total_amount_display', 'status_badge', 'is_balanced_display',
        'created_by', 'created_at'
    ]
    list_filter = ['status', 'transaction_type', 'branch']
    search_fields = ['transaction_number', 'description', 'reference', 'notes']
    date_hierarchy = 'date'
    ordering = ['-date', '-id']
    list_per_page = 30
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('transaction_number', 'date', 'transaction_type', 'status')
        }),
        ('التفاصيل', {
            'fields': ('description', 'reference', 'notes', 'branch')
        }),
        ('المراجع', {
            'fields': ('order', 'customer', 'payment'),
            'classes': ('collapse',),
            'description': 'ربط القيد بطلب أو عميل أو دفعة'
        }),
        ('معلومات النظام', {
            'fields': ('total_debit', 'total_credit', 'created_by', 'posted_by', 'posted_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['transaction_number', 'total_debit', 'total_credit', 'created_by', 'posted_by', 'posted_at']
    autocomplete_fields = ['order', 'customer', 'payment']
    inlines = [TransactionLineInline]
    actions = ['post_transactions', 'void_transactions']
    
    def total_amount_display(self, obj):
        total = obj.lines.aggregate(total=Sum('debit'))['total'] or 0
        return format_html('<strong>{:,.2f}</strong>', total)
    total_amount_display.short_description = 'المبلغ'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'posted': '#28a745',
            'cancelled': '#dc3545'
        }
        labels = {
            'draft': 'مسودة',
            'posted': 'مرحّل',
            'cancelled': 'ملغي'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#000'),
            labels.get(obj.status, obj.status)
        )
    status_badge.short_description = 'الحالة'
    status_badge.admin_order_field = 'status'
    
    def is_balanced_display(self, obj):
        if obj.is_balanced:
            return format_html('<span style="color: green;">✓ متوازن</span>')
        return format_html('<span style="color: red;">✗ غير متوازن</span>')
    is_balanced_display.short_description = 'التوازن'
    is_balanced_display.boolean = True
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def post_transactions(self, request, queryset):
        count = 0
        for transaction in queryset.filter(status='draft'):
            try:
                transaction.post(request.user)
                count += 1
            except ValueError:
                pass
        self.message_user(request, f'تم ترحيل {count} قيد بنجاح')
    post_transactions.short_description = 'ترحيل القيود المحددة'
    
    def void_transactions(self, request, queryset):
        count = queryset.filter(status='posted').update(status='cancelled')
        self.message_user(request, f'تم إلغاء {count} قيد بنجاح')
    void_transactions.short_description = 'إلغاء القيود المحددة'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'branch', 'order', 'customer', 'created_by', 'posted_by'
        ).prefetch_related('lines')


@admin.register(TransactionLine)
class TransactionLineAdmin(admin.ModelAdmin):
    """
    إدارة سطور القيود
    """
    list_display = [
        'transaction_link', 'account', 'debit_display', 
        'credit_display', 'description'
    ]
    list_filter = ['transaction__transaction_type', 'transaction__status', 'account__account_type']
    search_fields = ['transaction__transaction_number', 'account__name', 'description']
    autocomplete_fields = ['transaction', 'account']
    list_per_page = 50
    
    def transaction_link(self, obj):
        url = reverse('admin:accounting_transaction_change', args=[obj.transaction.id])
        return format_html('<a href="{}">{}</a>', url, obj.transaction.transaction_number)
    transaction_link.short_description = 'القيد'
    
    def debit_display(self, obj):
        if obj.debit > 0:
            return format_html('<span style="color: green;">{:,.2f}</span>', obj.debit)
        return '-'
    debit_display.short_description = 'مدين'
    
    def credit_display(self, obj):
        if obj.credit > 0:
            return format_html('<span style="color: red;">{:,.2f}</span>', obj.credit)
        return '-'
    credit_display.short_description = 'دائن'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('transaction', 'account')


@admin.register(CustomerAdvance)
class CustomerAdvanceAdmin(admin.ModelAdmin):
    """
    إدارة سلف العملاء
    """
    list_display = [
        'customer_link', 'advance_number', 'amount', 'remaining_display',
        'payment_method', 'status_badge', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'branch']
    search_fields = ['customer__name', 'customer__phone', 'receipt_number', 'advance_number', 'notes']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    autocomplete_fields = ['customer', 'transaction']
    list_per_page = 30
    inlines = [AdvanceUsageInline]
    
    fieldsets = (
        ('معلومات العميل', {
            'fields': ('customer', 'branch')
        }),
        ('تفاصيل السلفة', {
            'fields': ('advance_number', 'amount', 'remaining_amount', 'payment_method', 'receipt_number')
        }),
        ('الحالة', {
            'fields': ('status', 'notes')
        }),
        ('القيد المحاسبي', {
            'fields': ('transaction',),
            'classes': ('collapse',),
        }),
        ('معلومات النظام', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['advance_number', 'remaining_amount', 'created_by', 'created_at', 'updated_at']
    actions = ['mark_as_used']
    
    def customer_link(self, obj):
        url = reverse('admin:customers_customer_change', args=[obj.customer.id])
        return format_html('<a href="{}">{}</a>', url, obj.customer.name)
    customer_link.short_description = 'العميل'
    
    def remaining_display(self, obj):
        remaining = obj.remaining_amount
        if remaining > 0:
            return format_html('<span style="color: green; font-weight: bold;">{:,.2f}</span>', remaining)
        return format_html('<span style="color: gray;">0.00</span>')
    remaining_display.short_description = 'المتبقي'
    
    def status_badge(self, obj):
        colors = {
            'active': '#28a745',
            'partially_used': '#17a2b8',
            'fully_used': '#6c757d',
            'refunded': '#dc3545',
            'cancelled': '#6c757d'
        }
        labels = {
            'active': 'نشط',
            'partially_used': 'مستخدم جزئياً',
            'fully_used': 'مستخدم بالكامل',
            'refunded': 'مسترد',
            'cancelled': 'ملغي'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#000'),
            labels.get(obj.status, obj.status)
        )
    status_badge.short_description = 'الحالة'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def mark_as_used(self, request, queryset):
        count = queryset.filter(status='active').update(status='fully_used')
        self.message_user(request, f'تم تحديث حالة {count} سلفة إلى "مستخدم"')
    mark_as_used.short_description = 'تحديث الحالة إلى مستخدم'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'branch', 'created_by'
        )


@admin.register(AdvanceUsage)
class AdvanceUsageAdmin(admin.ModelAdmin):
    """
    إدارة استخدامات السلف
    """
    list_display = ['advance_link', 'order_link', 'amount', 'created_at', 'created_by']
    list_filter = ['advance__status']
    search_fields = ['advance__customer__name', 'order__order_number', 'advance__advance_number']
    date_hierarchy = 'created_at'
    readonly_fields = ['advance', 'order', 'amount', 'created_at', 'created_by']
    
    def advance_link(self, obj):
        url = reverse('admin:accounting_customeradvance_change', args=[obj.advance.id])
        return format_html('<a href="{}">{}</a>', url, str(obj.advance))
    advance_link.short_description = 'السلفة'
    
    def order_link(self, obj):
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return '-'
    order_link.short_description = 'الطلب'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'advance', 'advance__customer', 'order', 'created_by'
        )


@admin.register(CustomerFinancialSummary)
class CustomerFinancialSummaryAdmin(admin.ModelAdmin):
    """
    إدارة الملخص المالي للعملاء
    """
    list_display = [
        'customer_link', 'total_orders_count', 'total_orders_amount',
        'total_paid', 'debt_display', 'total_advances', 'remaining_advances_display',
        'status_badge', 'last_updated'
    ]
    list_filter = ['financial_status', 'last_updated']
    search_fields = ['customer__name', 'customer__phone']
    ordering = ['-total_debt']
    readonly_fields = [
        'customer', 'total_orders_count', 'total_orders_amount', 'total_paid',
        'total_debt', 'total_advances', 'remaining_advances', 'financial_status',
        'last_payment_date', 'last_order_date', 'last_updated'
    ]
    list_per_page = 30
    
    fieldsets = (
        ('معلومات العميل', {
            'fields': ('customer',)
        }),
        ('الطلبات', {
            'fields': ('total_orders_count', 'total_orders_amount', 'last_order_date')
        }),
        ('المدفوعات والرصيد', {
            'fields': ('total_paid', 'total_debt', 'last_payment_date')
        }),
        ('السلف', {
            'fields': ('total_advances', 'remaining_advances')
        }),
        ('الحالة', {
            'fields': ('financial_status', 'last_updated'),
        }),
    )
    actions = ['refresh_summaries']
    
    def customer_link(self, obj):
        url = reverse('admin:customers_customer_change', args=[obj.customer.id])
        return format_html('<a href="{}">{}</a>', url, obj.customer.name)
    customer_link.short_description = 'العميل'
    
    def debt_display(self, obj):
        if obj.total_debt > 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">{:,.2f}</span>',
                obj.total_debt
            )
        elif obj.total_debt < 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{:,.2f}</span>',
                abs(obj.total_debt)
            )
        return format_html('<span style="color: gray;">0.00</span>')
    debt_display.short_description = 'المديونية'
    debt_display.admin_order_field = 'total_debt'
    
    def remaining_advances_display(self, obj):
        if obj.remaining_advances > 0:
            return format_html('<span style="color: blue;">{:,.2f}</span>', obj.remaining_advances)
        return format_html('<span style="color: gray;">0.00</span>')
    remaining_advances_display.short_description = 'رصيد العربون'
    
    def status_badge(self, obj):
        colors = {
            'clear': '#28a745',
            'has_debt': '#dc3545',
            'has_credit': '#17a2b8',
        }
        labels = {
            'clear': 'بريء الذمة',
            'has_debt': 'عليه مستحقات',
            'has_credit': 'له رصيد',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.financial_status, '#000'),
            labels.get(obj.financial_status, obj.financial_status)
        )
    status_badge.short_description = 'الحالة المالية'
    
    def refresh_summaries(self, request, queryset):
        for summary in queryset:
            summary.refresh()
        self.message_user(request, f'تم تحديث {queryset.count()} ملخص مالي')
    refresh_summaries.short_description = 'تحديث الملخصات المحددة'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer')


@admin.register(AccountingSettings)
class AccountingSettingsAdmin(admin.ModelAdmin):
    """
    إعدادات النظام المحاسبي
    """
    list_display = ['id', 'fiscal_year_start', 'auto_post_transactions', 'require_transaction_approval', 'updated_at']
    
    fieldsets = (
        ('إعدادات السنة المالية', {
            'fields': ('fiscal_year_start',)
        }),
        ('الحسابات الافتراضية', {
            'fields': (
                'default_cash_account', 'default_bank_account',
                'default_receivables_account', 'default_revenue_account',
                'default_advances_account'
            )
        }),
        ('إعدادات عامة', {
            'fields': ('auto_post_transactions', 'require_transaction_approval')
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = [
        'default_cash_account', 'default_bank_account',
        'default_receivables_account', 'default_revenue_account',
        'default_advances_account'
    ]
    
    def has_add_permission(self, request):
        # السماح بإضافة سجل واحد فقط
        return not AccountingSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
