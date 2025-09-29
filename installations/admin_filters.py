"""
فلاتر مخصصة لإدارة المديونيات
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.utils import timezone


class DebtAmountRangeFilter(admin.SimpleListFilter):
    """فلتر نطاق مبلغ المديونية"""
    title = _('نطاق المبلغ')
    parameter_name = 'debt_amount_range'

    def lookups(self, request, model_admin):
        return (
            ('0-100', _('أقل من 100 ج.م')),
            ('100-500', _('100 - 500 ج.م')),
            ('500-1000', _('500 - 1000 ج.م')),
            ('1000-5000', _('1000 - 5000 ج.م')),
            ('5000-10000', _('5000 - 10000 ج.م')),
            ('10000+', _('أكثر من 10000 ج.م')),
        )

    def queryset(self, request, queryset):
        if self.value() == '0-100':
            return queryset.filter(debt_amount__lt=100)
        elif self.value() == '100-500':
            return queryset.filter(debt_amount__gte=100, debt_amount__lt=500)
        elif self.value() == '500-1000':
            return queryset.filter(debt_amount__gte=500, debt_amount__lt=1000)
        elif self.value() == '1000-5000':
            return queryset.filter(debt_amount__gte=1000, debt_amount__lt=5000)
        elif self.value() == '5000-10000':
            return queryset.filter(debt_amount__gte=5000, debt_amount__lt=10000)
        elif self.value() == '10000+':
            return queryset.filter(debt_amount__gte=10000)
        return queryset


class OverdueFilter(admin.SimpleListFilter):
    """فلتر المديونيات المتأخرة"""
    title = _('حالة التأخير')
    parameter_name = 'overdue_status'

    def lookups(self, request, model_admin):
        return (
            ('current', _('حديثة (أقل من 30 يوم)')),
            ('overdue_30', _('متأخرة 30-60 يوم')),
            ('overdue_60', _('متأخرة 60-90 يوم')),
            ('overdue_90', _('متأخرة أكثر من 90 يوم')),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'current':
            return queryset.filter(
                is_paid=False,
                created_at__gte=now - timezone.timedelta(days=30)
            )
        elif self.value() == 'overdue_30':
            return queryset.filter(
                is_paid=False,
                created_at__lt=now - timezone.timedelta(days=30),
                created_at__gte=now - timezone.timedelta(days=60)
            )
        elif self.value() == 'overdue_60':
            return queryset.filter(
                is_paid=False,
                created_at__lt=now - timezone.timedelta(days=60),
                created_at__gte=now - timezone.timedelta(days=90)
            )
        elif self.value() == 'overdue_90':
            return queryset.filter(
                is_paid=False,
                created_at__lt=now - timezone.timedelta(days=90)
            )
        return queryset


class BranchFilter(admin.SimpleListFilter):
    """فلتر الفروع"""
    title = _('الفرع')
    parameter_name = 'branch'

    def lookups(self, request, model_admin):
        from accounts.models import Branch
        branches = Branch.objects.all().order_by('name')
        return [(branch.id, branch.name) for branch in branches]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(order__customer__branch__id=self.value())
        return queryset


class SalespersonFilter(admin.SimpleListFilter):
    """فلتر البائعين"""
    title = _('البائع')
    parameter_name = 'salesperson'

    def lookups(self, request, model_admin):
        from accounts.models import Salesperson
        # البحث عن البائعين الذين لديهم طلبات
        salespersons = Salesperson.objects.filter(
            orders__isnull=False
        ).distinct().order_by('name')

        return [
            (salesperson.id, salesperson.name)
            for salesperson in salespersons
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(order__salesperson__id=self.value())
        return queryset


class PaymentMethodFilter(admin.SimpleListFilter):
    """فلتر طريقة الدفع"""
    title = _('حالة الدفع التفصيلية')
    parameter_name = 'payment_method'

    def lookups(self, request, model_admin):
        return (
            ('paid_today', _('مدفوع اليوم')),
            ('paid_this_week', _('مدفوع هذا الأسبوع')),
            ('paid_this_month', _('مدفوع هذا الشهر')),
            ('unpaid_recent', _('غير مدفوع (حديث)')),
            ('unpaid_overdue', _('غير مدفوع (متأخر)')),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        today = now.date()
        week_ago = now - timezone.timedelta(days=7)
        month_ago = now - timezone.timedelta(days=30)
        
        if self.value() == 'paid_today':
            return queryset.filter(is_paid=True, payment_date__date=today)
        elif self.value() == 'paid_this_week':
            return queryset.filter(is_paid=True, payment_date__gte=week_ago)
        elif self.value() == 'paid_this_month':
            return queryset.filter(is_paid=True, payment_date__gte=month_ago)
        elif self.value() == 'unpaid_recent':
            return queryset.filter(is_paid=False, created_at__gte=month_ago)
        elif self.value() == 'unpaid_overdue':
            return queryset.filter(is_paid=False, created_at__lt=month_ago)
        return queryset


class CustomerTypeFilter(admin.SimpleListFilter):
    """فلتر نوع العميل"""
    title = _('نوع العميل')
    parameter_name = 'customer_type'

    def lookups(self, request, model_admin):
        return (
            ('retail', _('تجزئة')),
            ('wholesale', _('جملة')),
            ('corporate', _('شركة')),
            ('government', _('حكومي')),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(customer__customer_type=self.value())
        return queryset


class OrderTypeFilter(admin.SimpleListFilter):
    """فلتر نوع الطلب"""
    title = _('نوع الطلب')
    parameter_name = 'order_type'

    def lookups(self, request, model_admin):
        return (
            ('installation', _('تركيب')),
            ('tailoring', _('تفصيل')),
            ('accessory', _('إكسسوارات')),
            ('inspection', _('معاينة')),
            ('products', _('منتجات')),
            ('fabric', _('أقمشة')),
        )

    def queryset(self, request, queryset):
        if self.value():
            # البحث في JSON field
            from django.db.models import Q
            return queryset.filter(
                Q(order__selected_types__icontains=f'"{self.value()}"') |
                Q(order__selected_types__icontains=f"'{self.value()}'")
            )
        return queryset


class DebtAgeFilter(admin.SimpleListFilter):
    """فلتر عمر المديونية"""
    title = _('عمر المديونية')
    parameter_name = 'debt_age'

    def lookups(self, request, model_admin):
        return (
            ('new', _('جديدة (أقل من أسبوع)')),
            ('week', _('أسبوع - شهر')),
            ('month', _('شهر - 3 أشهر')),
            ('quarter', _('3 - 6 أشهر')),
            ('old', _('أكثر من 6 أشهر')),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'new':
            return queryset.filter(created_at__gte=now - timezone.timedelta(days=7))
        elif self.value() == 'week':
            return queryset.filter(
                created_at__lt=now - timezone.timedelta(days=7),
                created_at__gte=now - timezone.timedelta(days=30)
            )
        elif self.value() == 'month':
            return queryset.filter(
                created_at__lt=now - timezone.timedelta(days=30),
                created_at__gte=now - timezone.timedelta(days=90)
            )
        elif self.value() == 'quarter':
            return queryset.filter(
                created_at__lt=now - timezone.timedelta(days=90),
                created_at__gte=now - timezone.timedelta(days=180)
            )
        elif self.value() == 'old':
            return queryset.filter(created_at__lt=now - timezone.timedelta(days=180))
        return queryset
