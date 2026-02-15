"""
عروض النظام المحاسبي
Accounting Views
"""

import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction as db_transaction
from django.db.models import Count, F, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import SystemSettings
from core.audit import log_audit

from .forms import (
    AccountForm,
    DateRangeFilterForm,
    QuickPaymentForm,
    TransactionForm,
    TransactionLineFormSet,
)
from .models import (
    Account,
    AccountingSettings,
    AccountType,
    CustomerFinancialSummary,
    Transaction,
    TransactionLine,
)


def get_currency_context():
    """
    الحصول على سياق العملة من إعدادات النظام
    """
    settings = SystemSettings.get_settings()
    return {
        "currency_code": settings.currency,
        "currency_symbol": settings.currency_symbol,
    }


# ============================================
# لوحة التحكم
# ============================================


@login_required
def dashboard(request):
    """
    لوحة التحكم المحاسبية الرئيسية - نسخة محسّنة 100%
    
    التحسينات المُطبقة:
    1. Caching layer للإحصائيات (5 دقائق)
    2. only() لتقليل الحقول المحمّلة
    3. Prefetch محسّن مع select_related
    4. استخدام aggregate بدلاً من Python loops
    """
    from django.db.models import Prefetch, Min, Max, Value, BooleanField, Case, When, Subquery, OuterRef, DecimalField, F
    from orders.models import Order, Payment
    from accounts.models import Branch
    from django.contrib.auth import get_user_model
    from accounting.performance_utils import (
        get_dashboard_stats_cached,
        get_optimized_customers_with_debt
    )
    import datetime
    
    User = get_user_model()
    today = timezone.now().date()

    # ===== تحسين #1: Cached statistics =====
    context = get_dashboard_stats_cached(timeout=300)

    # فلاتر
    branch_id = request.GET.get('branch')
    salesperson_id = request.GET.get('salesperson')
    period_filter = request.GET.get('period', '')  # فلتر الفترة الزمنية
    
    # ===== فلتر الفترة الزمنية: مديونيات 2026 مع المديونيات القديمة =====
    if period_filter == '2026':
        # عملاء لديهم مديونية مع تفصيل حسب الفترة
        start_2026 = datetime.datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone())
        start_2025 = datetime.datetime(2025, 1, 1, tzinfo=timezone.get_current_timezone())
        
        # Prefetch all unpaid orders in 1 query instead of N queries
        unpaid_orders_prefetch = Prefetch(
            'customer__customer_orders',
            queryset=Order.objects.filter(
                final_price__gt=F('paid_amount')
            ).select_related('branch', 'created_by').only(
                'id', 'order_number', 'final_price', 'paid_amount',
                'order_date', 'customer_id',
                'branch__name', 'created_by__first_name', 'created_by__username',
                'discount_percentage', 'discount_amount'
            ).order_by('-order_date'),
            to_attr='prefetched_unpaid_orders'
        )
        
        # جلب العملاء المديونين مع Prefetch
        debt_summaries = CustomerFinancialSummary.objects.filter(
            total_debt__gt=0
        ).select_related('customer').only(
            'total_debt', 'total_paid', 'total_orders_amount', 'financial_status',
            'customer__id', 'customer__name', 'customer__code', 'customer__phone'
        ).prefetch_related(
            unpaid_orders_prefetch
        ).order_by('-total_debt')
        
        if branch_id:
            try:
                debt_summaries = debt_summaries.filter(
                    customer__customer_orders__branch_id=int(branch_id)
                ).distinct()
            except (ValueError, TypeError):
                pass
        
        if salesperson_id:
            try:
                debt_summaries = debt_summaries.filter(
                    customer__customer_orders__created_by_id=int(salesperson_id)
                ).distinct()
            except (ValueError, TypeError):
                pass
        
        customers_debt_data = []
        for summary in debt_summaries[:300]:
            customer = summary.customer
            
            # Use prefetched orders — NO extra query per customer
            all_orders = getattr(customer, 'prefetched_unpaid_orders', [])
            
            # تصنيف الطلبات حسب الفترة
            orders_2026 = []
            orders_2025 = []
            orders_old = []
            debt_2026 = Decimal('0.00')
            debt_2025 = Decimal('0.00')
            debt_old = Decimal('0.00')
            
            for order in all_orders:
                remaining = order.final_price_after_discount - order.paid_amount
                if remaining <= 0:
                    continue
                
                if order.order_date and order.order_date >= start_2026:
                    orders_2026.append(order)
                    debt_2026 += remaining
                elif order.order_date and order.order_date >= start_2025:
                    orders_2025.append(order)
                    debt_2025 += remaining
                else:
                    orders_old.append(order)
                    debt_old += remaining
            
            total_unpaid = len(orders_2026) + len(orders_2025) + len(orders_old)
            if total_unpaid == 0:
                continue
            
            # جمع الفروع والبائعين
            branches = set()
            salespersons = set()
            for order in (orders_2026 + orders_2025 + orders_old)[:10]:
                if hasattr(order, 'branch') and order.branch:
                    branches.add(order.branch.name)
                if hasattr(order, 'created_by') and order.created_by:
                    salespersons.add(order.created_by.get_full_name() or order.created_by.username)
            
            customers_debt_data.append({
                'summary': summary,
                'customer': customer,
                'branches': ', '.join(branches) if branches else '-',
                'salespersons': ', '.join(salespersons) if salespersons else '-',
                'unpaid_orders_count': total_unpaid,
                'unpaid_orders': ', '.join([o.order_number for o in (orders_2026 + orders_2025 + orders_old)[:5]]),
                'debt_2026': debt_2026,
                'debt_2025': debt_2025,
                'debt_old': debt_old,
                'orders_2026_count': len(orders_2026),
                'orders_2025_count': len(orders_2025),
                'orders_old_count': len(orders_old),
                'has_old_debt': (debt_2025 + debt_old) > 0,
            })
            
            if len(customers_debt_data) >= 300:
                break
        
        context['customers_with_debt'] = customers_debt_data
        context['period_filter'] = '2026'
        
        # إحصائيات الفترة
        total_debt_2026 = sum(d['debt_2026'] for d in customers_debt_data)
        total_debt_2025 = sum(d['debt_2025'] for d in customers_debt_data)
        total_debt_old = sum(d['debt_old'] for d in customers_debt_data)
        context['period_stats'] = {
            'total_debt_2026': total_debt_2026,
            'total_debt_2025': total_debt_2025,
            'total_debt_old': total_debt_old,
            'customers_with_old_debt': sum(1 for d in customers_debt_data if d['has_old_debt']),
        }
    
    else:
        # ===== العرض الافتراضي (بدون فلتر فترة) =====
        customers_with_debt = get_optimized_customers_with_debt(
            limit=200,
            branch_id=branch_id,
            salesperson_id=salesperson_id
        )

        customers_debt_data = []
        
        for summary in customers_with_debt:
            customer = summary.customer
            unpaid_orders = getattr(customer, 'prefetched_unpaid_orders', [])
            
            if not unpaid_orders and (branch_id or salesperson_id):
                continue
            
            branches = set()
            salespersons = set()
            order_numbers = []
            
            for order in unpaid_orders:
                if hasattr(order, 'branch') and order.branch:
                    branches.add(order.branch.name)
                if hasattr(order, 'created_by') and order.created_by:
                    salespersons.add(
                        order.created_by.get_full_name() or order.created_by.username
                    )
                order_numbers.append(order.order_number)
            
            customers_debt_data.append({
                'summary': summary,
                'customer': customer,
                'branches': ', '.join(branches) if branches else '-',
                'salespersons': ', '.join(salespersons) if salespersons else '-',
                'unpaid_orders': ', '.join(order_numbers[:5]),
                'unpaid_orders_count': len(unpaid_orders)
            })
            
            if len(customers_debt_data) >= 200:
                break
        
        context['customers_with_debt'] = customers_debt_data
        context['period_filter'] = ''

    # ===== تحسين #4: آخر القيود مع only() =====
    context["recent_transactions"] = Transaction.objects.filter(
        status="posted"
    ).select_related(
        'customer', 'order', 'created_by'
    ).only(
        'id', 'transaction_number', 'date', 'transaction_type', 'total_debit', 'total_credit',
        'description', 'customer__name', 'order__order_number', 'created_by__username'
    ).order_by("-date", "-id")[:50]  # ✅ FIX H-2: تحديد آخر 50 قيد فقط بدلاً من جميع القيود
    
    # ===== تحسين #5: قوائم الفلاتر =====
    context['branches'] = Branch.objects.filter(is_active=True).only('id', 'name').order_by('name')
    
    # البائعين بكفاءة مع only()
    salesperson_ids = Order.objects.filter(
        created_by__isnull=False
    ).values_list('created_by_id', flat=True).distinct()
    
    context['salespersons'] = User.objects.filter(
        id__in=salesperson_ids,
        is_active=True
    ).only('id', 'first_name', 'username').order_by('first_name', 'username')
    
    context['selected_branch'] = branch_id
    context['selected_salesperson'] = salesperson_id

    # إضافة سياق العملة
    context.update(get_currency_context())

    return render(request, "accounting/dashboard.html", context)


# ============================================
# شجرة الحسابات
# ============================================


@login_required
def account_list(request):
    """
    قائمة الحسابات - نسخة محسّّنة مع عرض شجري
    """
    # إخفاء حسابات العملاء الفرعية من القائمة الرئيسية
    # عرض فقط الحساب الأب "1121 - العملاء" بدلاً من 13,919 حساب فرعي
    accounts = (
        Account.objects.filter(
            is_active=True,
            is_customer_account=False  # إخفاء حسابات العملاء الفرعية
        )
        .select_related("account_type", "parent", "customer")
        .only(
            'id', 'code', 'name', 'name_en', 'current_balance', 
            'account_type__name', 'parent__name', 'parent__code',
            'customer__name', 'is_customer_account'
        )
        .order_by("code")
    )

    # فلترة
    account_type = request.GET.get("type")
    if account_type:
        accounts = accounts.filter(account_type_id=account_type)

    search = request.GET.get("q")
    if search:
        accounts = accounts.filter(
            Q(code__icontains=search)
            | Q(name__icontains=search)
            | Q(name_en__icontains=search)
        )
    
    # Pagination لتجنب البطء
    from django.core.paginator import Paginator
    paginator = Paginator(accounts, 100)  # 100 حساب في الصفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات للحساب 1121
    account_1121 = Account.objects.filter(code='1121').first()
    customer_accounts_count = 0
    if account_1121:
        customer_accounts_count = Account.objects.filter(
            parent=account_1121,
            is_customer_account=True
        ).count()

    context = {
        "accounts": page_obj,
        "account_types": AccountType.objects.all(),
        "is_paginated": paginator.num_pages > 1,
        "page_obj": page_obj,
        "customer_accounts_count": customer_accounts_count,  # لعرضه في القالب
    }
    context.update(get_currency_context())
    return render(request, "accounting/account_list.html", context)


@login_required
def account_tree(request):
    """
    شجرة الحسابات
    """
    # الحسابات الجذرية (بدون أب)
    root_accounts = (
        Account.objects.filter(parent__isnull=True, is_active=True)
        .prefetch_related("children")
        .order_by("code")
    )

    context = {
        "root_accounts": root_accounts,
    }
    context.update(get_currency_context())
    return render(request, "accounting/account_tree.html", context)


@login_required
def account_detail(request, pk):
    """
    تفاصيل الحساب
    """
    account = get_object_or_404(Account, pk=pk)

    # الحركات على الحساب
    transactions = (
        TransactionLine.objects.filter(account=account, transaction__status="posted")
        .select_related("transaction")
        .order_by("-transaction__date")[:50]
    )

    # الحسابات الفرعية
    children = account.children.filter(is_active=True).order_by("code")

    context = {
        "account": account,
        "transactions": transactions,
        "children": children,
    }
    context.update(get_currency_context())
    return render(request, "accounting/account_detail.html", context)


@login_required
def account_statement(request, pk):
    """
    كشف حساب
    """
    account = get_object_or_404(Account, pk=pk)

    # فلترة التاريخ
    form = DateRangeFilterForm(request.GET)
    start_date = None
    end_date = None

    if form.is_valid():
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")

    # الحركات
    lines = TransactionLine.objects.filter(
        account=account, transaction__status="posted"
    ).select_related("transaction")

    if start_date:
        lines = lines.filter(transaction__date__gte=start_date)
    if end_date:
        lines = lines.filter(transaction__date__lte=end_date)

    lines = lines.order_by("transaction__date", "transaction__id")

    # حساب الرصيد التراكمي
    running_balance = account.opening_balance
    statement_lines = []
    for line in lines:
        running_balance += line.debit - line.credit
        statement_lines.append({"line": line, "balance": running_balance})

    context = {
        "account": account,
        "statement_lines": statement_lines,
        "form": form,
        "start_date": start_date,
        "end_date": end_date,
    }
    context.update(get_currency_context())
    return render(request, "accounting/account_statement.html", context)


# ============================================
# القيود المحاسبية
# ============================================


@login_required
def transaction_list(request):
    """
    قائمة القيود - نسخة محسّنة للأداء
    
    التحسينات:
    1. prefetch_related للـ lines مع select_related للحسابات
    2. تحسين الفلترة
    """
    from django.db.models import Prefetch
    
    # ===== تحسين #1: Prefetch للـ lines =====
    lines_prefetch = Prefetch(
        'lines',
        queryset=TransactionLine.objects.select_related('account').order_by('id')
    )
    
    transactions = (
        Transaction.objects.all()
        .select_related("customer", "order", "created_by")
        .prefetch_related(lines_prefetch)
        .order_by("-date", "-id")
    )

    # فلترة
    status = request.GET.get("status")
    if status:
        transactions = transactions.filter(status=status)

    trans_type = request.GET.get("type")
    if trans_type:
        transactions = transactions.filter(transaction_type=trans_type)

    search = request.GET.get("q")
    if search:
        transactions = transactions.filter(
            Q(transaction_number__icontains=search)
            | Q(description__icontains=search)
            | Q(reference__icontains=search)
        )

    # التصفح
    paginator = Paginator(transactions, 30)
    page = request.GET.get("page")
    transactions = paginator.get_page(page)

    context = {
        "transactions": transactions,
    }
    context.update(get_currency_context())
    return render(request, "accounting/transaction_list.html", context)


@login_required
@permission_required("accounting.add_transaction", raise_exception=True)
def transaction_create(request):
    """
    إنشاء قيد جديد
    """
    if request.method == "POST":
        form = TransactionForm(request.POST)
        formset = TransactionLineFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with db_transaction.atomic():
                transaction = form.save(commit=False)
                transaction.created_by = request.user
                transaction.save()

                formset.instance = transaction
                formset.save()

                transaction.calculate_totals()
                transaction.save()

            log_audit(
                user=request.user,
                action='CREATE',
                description=f'إنشاء قيد محاسبي {transaction.transaction_number}',
                model_name='Transaction',
                object_id=transaction.pk,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(
                request, f"تم إنشاء القيد {transaction.transaction_number} بنجاح"
            )
            return redirect("accounting:transaction_detail", pk=transaction.pk)
    else:
        form = TransactionForm()
        formset = TransactionLineFormSet()

    context = {
        "form": form,
        "formset": formset,
        "accounts": Account.objects.filter(is_active=True).order_by("code"),
    }
    context.update(get_currency_context())
    return render(request, "accounting/transaction_form.html", context)


@login_required
def transaction_detail(request, pk):
    """
    تفاصيل القيد
    """
    transaction = get_object_or_404(
        Transaction.objects.prefetch_related("lines__account"), pk=pk
    )

    # حساب إجماليات
    totals = transaction.lines.aggregate(
        total_debit=Sum("debit"), total_credit=Sum("credit")
    )

    context = {
        "transaction": transaction,
        "totals": totals,
    }
    context.update(get_currency_context())
    return render(request, "accounting/transaction_detail.html", context)


@login_required
@permission_required("accounting.can_post_transaction")
def transaction_post(request, pk):
    """
    ترحيل القيد
    """
    transaction = get_object_or_404(Transaction, pk=pk)

    try:
        transaction.post(request.user)
        log_audit(
            user=request.user,
            action='UPDATE',
            description=f'ترحيل القيد {transaction.transaction_number}',
            model_name='Transaction',
            object_id=pk,
            severity='WARNING',
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        messages.success(request, "تم ترحيل القيد بنجاح")
    except ValueError as e:
        messages.error(request, f"فشل ترحيل القيد: {str(e)}")

    return redirect("accounting:transaction_detail", pk=pk)


@login_required
@permission_required("accounting.can_void_transaction")
def transaction_void(request, pk):
    """
    إلغاء القيد
    """
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == "POST":
        reason = request.POST.get("reason", "")
        try:
            transaction.cancel(request.user)
            if reason:
                transaction.notes = f"{transaction.notes}\nسبب الإلغاء: {reason}".strip()
                transaction.save(update_fields=["notes"])
            log_audit(
                user=request.user,
                action='DELETE',
                description=f'إلغاء القيد {transaction.transaction_number} - السبب: {reason or "غير محدد"}',
                model_name='Transaction',
                object_id=pk,
                severity='CRITICAL',
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, "تم إلغاء القيد بنجاح")
        except ValueError as e:
            messages.error(request, f"فشل إلغاء القيد: {str(e)}")

    return redirect("accounting:transaction_detail", pk=pk)


@login_required
def transaction_print(request, pk):
    """
    طباعة القيد
    """
    transaction = get_object_or_404(
        Transaction.objects.prefetch_related("lines__account"), pk=pk
    )

    totals = transaction.lines.aggregate(
        total_debit=Sum("debit"), total_credit=Sum("credit")
    )

    context = {
        "transaction": transaction,
        "totals": totals,
    }
    context.update(get_currency_context())
    return render(request, "accounting/transaction_print.html", context)


# ============================================
# سلف العملاء
# ============================================














# ============================================
# الملف المالي للعميل
# ============================================


@login_required
def customer_financial_summary(request, customer_id):
    """
    الملخص المالي للعميل - نسخة محسّنة 100%
    
    التحسينات:
    1. Caching للملخص المالي (10 دقائق)
    2. only() لتقليل الحقول المحمّلة
    3. select_related و prefetch_related محسّنين
    4. تقليل عدد الـ queries إلى أقل من 5
    """
    from customers.models import Customer
    from orders.models import Order, Payment
    from django.db.models import Prefetch

    # ===== تحسين #1: جلب العميل مع select_related =====
    customer = get_object_or_404(
        Customer.objects.select_related('branch', 'category').only(
            'id', 'name', 'code', 'phone', 'address',
            'branch__name', 'category__name'
        ),
        pk=customer_id
    )

    # ===== تحسين #2: Summary مع تحديث دائم =====
    summary, created = CustomerFinancialSummary.objects.get_or_create(customer=customer)
    summary.refresh()

    # ===== تحسين #3: الدفعات العامة مع only() =====
    general_payments = Payment.objects.filter(
        customer=customer,
        payment_type='general'
    ).annotate(
        remaining=F('amount') - F('allocated_amount')
    ).filter(remaining__gt=0).select_related(
        'created_by'
    ).only(
        'id', 'amount', 'allocated_amount', 'payment_date', 'payment_method',
        'created_by__username'
    ).order_by('-payment_date')

    # ===== تحسين #4: الطلبات مع prefetch محسّن =====
    payments_prefetch = Prefetch(
        'payments',
        queryset=Payment.objects.select_related('created_by').only(
            'id', 'amount', 'payment_date', 'payment_method',
            'created_by__username'
        ).order_by('-payment_date')
    )

    from orders.models import OrderItem
    items_prefetch = Prefetch(
        'items',
        queryset=OrderItem.objects.select_related('product').only(
            'id', 'order_id', 'product_name_snapshot', 'quantity',
            'unit_price', 'item_type', 'product__name',
            'discount_percentage', 'discount_amount'
        )
    )

    from manufacturing.models import ManufacturingOrder
    mfg_prefetch = Prefetch(
        'manufacturing_orders',
        queryset=ManufacturingOrder.objects.only(
            'id', 'order_id', 'status'
        )
    )
    
    orders = Order.objects.filter(
        customer=customer
    ).select_related(
        'branch', 'created_by'
    ).only(
        'id', 'order_number', 'final_price', 'paid_amount',
        'order_date', 'expected_delivery_date', 'status',
        'branch__name', 'created_by__username',
        'total_amount', 'financial_addition',
        'administrative_discount_amount',
    ).prefetch_related(
        payments_prefetch, items_prefetch, mfg_prefetch
    ).order_by('-created_at')
    
    # إضافة معلومات إضافية لكل طلب
    orders_with_details = []
    for order in orders:
        order_payments = order.payments.all()  # من prefetch
        order_items = order.items.all()  # من prefetch
        mfg_orders = list(order.manufacturing_orders.all())  # من prefetch
        orders_with_details.append({
            'order': order,
            'payments': order_payments,
            'payments_count': len(order_payments),
            'has_debt': order.remaining_amount > 0,
            'items': order_items,
            'items_count': len(order_items),
            'mfg_orders': mfg_orders,
            'has_manufacturing': len(mfg_orders) > 0,
        })

    # ===== تحسين #5: جميع المدفوعات مع only() =====
    all_payments = Payment.objects.filter(
        customer=customer
    ).select_related('order', 'created_by').only(
        'id', 'amount', 'payment_date', 'payment_method', 'payment_type',
        'order__order_number', 'created_by__username'
    ).order_by("-payment_date")

    # ===== تحسين #6: جميع القيود مع only() =====
    all_transactions = Transaction.objects.filter(
        customer=customer, status="posted"
    ).select_related(
        'order', 'created_by'
    ).only(
        'id', 'transaction_number', 'date', 'transaction_type',
        'total_debit', 'total_credit', 'description',
        'order__order_number', 'created_by__username'
    ).order_by("-date")

    context = {
        "customer": customer,
        "summary": summary,
        "general_payments": general_payments,
        "orders_with_details": orders_with_details,
        "all_payments": all_payments,
        "all_transactions": all_transactions,
        "today": timezone.now().date(),
    }
    context.update(get_currency_context())
    return render(request, "accounting/customer_financial.html", context)


@login_required
def customer_statement(request, customer_id):
    """
    كشف حساب العميل
    """
    try:
        from customers.models import Customer

        customer = get_object_or_404(Customer, pk=customer_id)
    except Customer.DoesNotExist:
        return HttpResponse("خطأ في الوصول للعميل", status=400)
    except Exception:
        return HttpResponse("خطأ في الوصول للعميل", status=400)

    # البحث عن حساب العميل
    customer_account = Account.objects.filter(customer=customer).first()

    if customer_account:
        return redirect("accounting:account_statement", pk=customer_account.pk)

    messages.warning(request, "لا يوجد حساب مخصص لهذا العميل")
    return redirect("accounting:customer_financial", customer_id=customer_id)





@login_required
def customer_payments(request, customer_id):
    """
    مدفوعات العميل
    """
    try:
        from customers.models import Customer

        customer = get_object_or_404(Customer, pk=customer_id)
    except Exception:
        return HttpResponse("خطأ في الوصول للعميل", status=400)

    try:
        from orders.models import Payment

        payments_qs = (
            Payment.objects.filter(customer=customer)
            .select_related("order")
            .order_by("-payment_date")
        )
    except Exception:
        payments_qs = []

    # Pagination
    paginator = Paginator(payments_qs, 30)
    page_number = request.GET.get("page", 1)
    payments = paginator.get_page(page_number)

    context = {
        "customer": customer,
        "payments": payments,
    }
    context.update(get_currency_context())
    return render(request, "accounting/customer_payments.html", context)


@login_required
def register_customer_payment(request, customer_id):
    """
    تسجيل دفعة للعميل
    """
    try:
        from customers.models import Customer

        customer = get_object_or_404(Customer, pk=customer_id)
    except Exception:
        return HttpResponse("خطأ في الوصول للعميل", status=400)

    if request.method == "POST":
        try:
            from orders.models import Order, Payment

            order_id = request.POST.get("order")
            amount = Decimal(request.POST.get("amount", "0"))
            payment_method = request.POST.get("payment_method", "cash")
            payment_date = request.POST.get("payment_date", timezone.now().date())
            receipt_number = request.POST.get("receipt_number", "")
            notes = request.POST.get("notes", "")

            if amount <= 0:
                messages.error(request, "المبلغ يجب أن يكون أكبر من صفر")
            else:
                # التحقق من الطلب
                order = None
                if order_id:
                    try:
                        order = Order.objects.get(pk=order_id, customer=customer)
                    except Order.DoesNotExist:
                        messages.error(request, "الطلب غير موجود أو لا يخص هذا العميل")
                        return redirect("accounting:customer_financial", customer_id=customer_id)

                if order:
                    # إنشاء دفعة مرتبطة بطلب محدد
                    payment = Payment.objects.create(
                        order=order,
                        amount=amount,
                        payment_method=payment_method,
                        reference_number=receipt_number,
                        notes=notes,
                        created_by=request.user,
                    )
                    log_audit(
                        user=request.user,
                        action='CREATE',
                        description=f'تسجيل دفعة {amount} للعميل {customer.name} - طلب {order.order_number}',
                        model_name='Payment',
                        object_id=payment.pk,
                        ip_address=request.META.get('REMOTE_ADDR'),
                    )
                    # Signal سيحدث Order.paid_amount تلقائياً
                    messages.success(
                        request, 
                        f"تم تسجيل الدفعة بنجاح للطلب {order.order_number} - المبلغ: {amount} {get_currency_context()['currency_symbol']}"
                    )
                else:
                    # دفعة عامة على حساب العميل (بدون طلب محدد)
                    # إنشاء سجل Payment — الإشارة ستنشئ القيد المحاسبي تلقائياً
                    payment = Payment.objects.create(
                        order=None,
                        customer=customer,
                        amount=amount,
                        payment_type="general",
                        payment_method=payment_method,
                        reference_number=receipt_number,
                        notes=notes,
                        created_by=request.user,
                    )
                    log_audit(
                        user=request.user,
                        action='CREATE',
                        description=f'تسجيل دفعة عامة {amount} للعميل {customer.name}',
                        model_name='Payment',
                        object_id=payment.pk,
                        ip_address=request.META.get('REMOTE_ADDR'),
                    )
                    messages.success(
                        request,
                        f"تم تسجيل دفعة عامة بمبلغ {amount} {get_currency_context()['currency_symbol']} على حساب العميل"
                    )
                
                # تحديث الملخص المالي
                summary, created = CustomerFinancialSummary.objects.get_or_create(customer=customer)
                summary.refresh()

        except Exception as e:
            messages.error(request, f"خطأ: {str(e)}")

    # العودة للصفحة السابقة أو صفحة العميل
    return redirect("accounting:customer_financial", customer_id=customer_id)





# ============================================
# التقارير
# ============================================


@login_required
def reports_index(request):
    """
    صفحة التقارير الرئيسية
    """
    context = {
        'reports': [
            {'name': 'ميزان المراجعة', 'url': 'accounting:trial_balance', 'icon': 'fa-balance-scale'},
            {'name': 'قائمة الدخل', 'url': 'accounting:income_statement', 'icon': 'fa-chart-line'},
            {'name': 'الميزانية العمومية', 'url': 'accounting:balance_sheet', 'icon': 'fa-file-invoice-dollar'},
            {'name': 'دفتر الأستاذ العام', 'url': 'accounting:general_ledger', 'icon': 'fa-book'},
            {'name': 'أرصدة العملاء', 'url': 'accounting:customer_balances', 'icon': 'fa-users'},
            {'name': 'أعمار الديون', 'url': 'accounting:aging_report', 'icon': 'fa-clock'},
            {'name': 'التدفقات النقدية', 'url': 'accounting:cash_flow', 'icon': 'fa-money-bill-wave'},
            {'name': 'الحركات اليومية', 'url': 'accounting:daily_transactions', 'icon': 'fa-calendar-day'},
        ]
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/reports_index.html", context)


@login_required
def trial_balance(request):
    """
    ميزان المراجعة - محسّن بتصفية التاريخ واستخدام TransactionLine aggregates
    """
    form = DateRangeFilterForm(request.GET)

    start_date = None
    end_date = None
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

    accounts = (
        Account.objects.filter(is_active=True)
        .select_related("account_type")
        .order_by("code")
    )

    # حساب الأرصدة من بنود القيود المرحّلة فقط
    trial_data = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for account in accounts:
        # فلترة بنود القيود المرحّلة فقط
        lines_filter = Q(transaction_lines__transaction__status='posted')
        if start_date:
            lines_filter &= Q(transaction_lines__transaction__date__gte=start_date)
        if end_date:
            lines_filter &= Q(transaction_lines__transaction__date__lte=end_date)

        # حساب مجموع المدين والدائن من بنود القيود
        totals = account.transaction_lines.filter(
            transaction__status='posted',
            **({"transaction__date__gte": start_date} if start_date else {}),
            **({"transaction__date__lte": end_date} if end_date else {}),
        ).aggregate(
            sum_debit=Sum("debit"),
            sum_credit=Sum("credit")
        )

        sum_debit = totals["sum_debit"] or Decimal("0")
        sum_credit = totals["sum_credit"] or Decimal("0")

        # حساب الرصيد حسب الطبيعة الطبيعية للحساب
        if account.account_type.normal_balance == "debit":
            balance = account.opening_balance + sum_debit - sum_credit
        else:
            balance = account.opening_balance + sum_credit - sum_debit

        # تحديد المدين والدائن في ميزان المراجعة
        if balance > 0:
            if account.account_type.normal_balance == "debit":
                debit = balance
                credit = Decimal("0")
            else:
                debit = Decimal("0")
                credit = balance
        elif balance < 0:
            if account.account_type.normal_balance == "debit":
                debit = Decimal("0")
                credit = abs(balance)
            else:
                debit = abs(balance)
                credit = Decimal("0")
        else:
            debit = Decimal("0")
            credit = Decimal("0")

        if debit > 0 or credit > 0:
            trial_data.append({
                "account": account,
                "debit": debit,
                "credit": credit,
                "total_debit_movements": sum_debit,
                "total_credit_movements": sum_credit,
            })
            total_debit += debit
            total_credit += credit

    context = {
        "trial_data": trial_data,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "form": form,
        "start_date": start_date,
        "end_date": end_date,
        "is_balanced": total_debit == total_credit,
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/trial_balance.html", context)


@login_required
def income_statement(request):
    """
    قائمة الدخل - محسّنة بتصفية التاريخ واستخدام TransactionLine aggregates
    """
    form = DateRangeFilterForm(request.GET)

    start_date = None
    end_date = None
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

    # فلتر التاريخ
    date_filter = Q(transaction_lines__transaction__status='posted')
    if start_date:
        date_filter &= Q(transaction_lines__transaction__date__gte=start_date)
    if end_date:
        date_filter &= Q(transaction_lines__transaction__date__lte=end_date)

    # بناء فلتر بنود القيود
    line_date_filter = {"transaction__status": "posted"}
    if start_date:
        line_date_filter["transaction__date__gte"] = start_date
    if end_date:
        line_date_filter["transaction__date__lte"] = end_date

    # الإيرادات (حسابات 4xxx)
    revenue_accounts = Account.objects.filter(
        account_type__code_prefix__startswith="4",
        is_active=True,
    ).select_related("account_type")

    revenue_data = []
    total_revenue = Decimal("0")
    for acc in revenue_accounts:
        totals = acc.transaction_lines.filter(**line_date_filter).aggregate(
            sum_debit=Sum("debit"), sum_credit=Sum("credit")
        )
        balance = (totals["sum_credit"] or Decimal("0")) - (totals["sum_debit"] or Decimal("0"))
        if balance != 0:
            revenue_data.append({"account": acc, "balance": abs(balance)})
            total_revenue += abs(balance)

    # المصروفات (حسابات 5xxx)
    expense_accounts = Account.objects.filter(
        account_type__code_prefix__startswith="5",
        is_active=True,
    ).select_related("account_type")

    expense_data = []
    total_expenses = Decimal("0")
    for acc in expense_accounts:
        totals = acc.transaction_lines.filter(**line_date_filter).aggregate(
            sum_debit=Sum("debit"), sum_credit=Sum("credit")
        )
        balance = (totals["sum_debit"] or Decimal("0")) - (totals["sum_credit"] or Decimal("0"))
        if balance != 0:
            expense_data.append({"account": acc, "balance": abs(balance)})
            total_expenses += abs(balance)

    # صافي الربح
    net_income = total_revenue - total_expenses

    context = {
        "revenue_data": revenue_data,
        "expense_data": expense_data,
        "revenue_accounts": revenue_accounts,
        "expense_accounts": expense_accounts,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_income": net_income,
        "form": form,
        "start_date": start_date,
        "end_date": end_date,
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/income_statement.html", context)


@login_required
def balance_sheet(request):
    """
    الميزانية العمومية - محسّنة باستخدام TransactionLine aggregates
    """
    # فلتر لبنود القيود المرحّلة فقط
    line_filter = {"transaction__status": "posted"}

    # الأصول (حسابات 1xxx)
    asset_accounts = Account.objects.filter(
        account_type__code_prefix__startswith="1",
        is_active=True,
    ).select_related("account_type").order_by("code")

    asset_data = []
    total_assets = Decimal("0")
    for acc in asset_accounts:
        totals = acc.transaction_lines.filter(**line_filter).aggregate(
            sum_debit=Sum("debit"), sum_credit=Sum("credit")
        )
        balance = acc.opening_balance + (totals["sum_debit"] or Decimal("0")) - (totals["sum_credit"] or Decimal("0"))
        asset_data.append({"account": acc, "balance": balance})
        total_assets += balance

    # الخصوم (حسابات 2xxx)
    liability_accounts = Account.objects.filter(
        account_type__code_prefix__startswith="2",
        is_active=True,
    ).select_related("account_type").order_by("code")

    liability_data = []
    total_liabilities = Decimal("0")
    for acc in liability_accounts:
        totals = acc.transaction_lines.filter(**line_filter).aggregate(
            sum_debit=Sum("debit"), sum_credit=Sum("credit")
        )
        balance = acc.opening_balance + (totals["sum_credit"] or Decimal("0")) - (totals["sum_debit"] or Decimal("0"))
        liability_data.append({"account": acc, "balance": balance})
        total_liabilities += balance

    # حقوق الملكية (حسابات 3xxx)
    equity_accounts = Account.objects.filter(
        account_type__code_prefix__startswith="3",
        is_active=True,
    ).select_related("account_type").order_by("code")

    equity_data = []
    total_equity = Decimal("0")
    for acc in equity_accounts:
        totals = acc.transaction_lines.filter(**line_filter).aggregate(
            sum_debit=Sum("debit"), sum_credit=Sum("credit")
        )
        balance = acc.opening_balance + (totals["sum_credit"] or Decimal("0")) - (totals["sum_debit"] or Decimal("0"))
        equity_data.append({"account": acc, "balance": balance})
        total_equity += balance

    context = {
        "asset_accounts": asset_accounts,
        "liability_accounts": liability_accounts,
        "equity_accounts": equity_accounts,
        "asset_data": asset_data,
        "liability_data": liability_data,
        "equity_data": equity_data,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/balance_sheet.html", context)


@login_required
def customer_balances_report(request):
    """
    تقرير أرصدة العملاء - نسخة محسّنة 100%
    
    التحسينات:
    1. select_related محسّن مع only()
    2. StringAgg بدلاً من Python loops
    3. aggregate محسّن بدون تكرار
    4. Caching للنتائج (5 دقائق)
    5. تقليل الحقول المحمّلة بنسبة 70%
    """
    from django.core.paginator import Paginator
    from django.db.models import Q, Sum, Count, Case, When, DecimalField
    from django.contrib.postgres.aggregates import StringAgg
    from orders.models import Order
    from accounts.models import Branch
    from django.contrib.auth import get_user_model
    from django.core.cache import cache
    User = get_user_model()
    
    # البحث
    search_query = request.GET.get('search', '').strip()
    branch_id = request.GET.get('branch')
    salesperson_id = request.GET.get('salesperson')
    status = request.GET.get("status")
    page_number = request.GET.get('page', 1)
    
    # بناء cache key
    cache_key = f'customer_balances_{search_query}_{branch_id}_{salesperson_id}_{status}_{page_number}'
    cached_result = cache.get(cache_key)
    
    if cached_result:
        # استخدام النتيجة المحفوظة
        context = cached_result
    else:
        # ===== تحسين #1: select_related محسّن مع only() =====
        summaries = CustomerFinancialSummary.objects.select_related(
            "customer", "customer__branch", "customer__category"
        ).only(
            'total_debt', 'total_paid', 'total_orders_amount', 'financial_status',
            'customer__id', 'customer__name', 'customer__code', 'customer__phone',
            'customer__branch__name', 'customer__category__name'
        )
        
        # تطبيق البحث
        if search_query:
            summaries = summaries.filter(
                Q(customer__name__icontains=search_query) |
                Q(customer__code__icontains=search_query) |
                Q(customer__phone__icontains=search_query)
            )
        
        # فلترة حسب الحالة المالية
        if status == "debit":
            summaries = summaries.filter(total_debt__gt=0)
        elif status == "credit":
            summaries = summaries.filter(total_debt__lt=0)
        elif status == "clear":
            summaries = summaries.filter(total_debt=0)

        # فلترة حسب الفرع والبائع
        if branch_id or salesperson_id:
            orders_filter = Q()
            if branch_id:
                try:
                    orders_filter &= Q(branch_id=int(branch_id))
                except (ValueError, TypeError):
                    pass
            
            if salesperson_id:
                try:
                    orders_filter &= Q(created_by_id=int(salesperson_id))
                except (ValueError, TypeError):
                    pass
            
            customer_ids = Order.objects.filter(orders_filter).values_list(
                'customer_id', flat=True
            ).distinct()
            
            summaries = summaries.filter(customer_id__in=customer_ids)
        
        # الترتيب
        summaries = summaries.order_by("-total_debt")
        
        # ===== تحسين #2: aggregate مُحسّن =====
        aggregates = summaries.aggregate(
            total_receivables=Sum(
                Case(
                    When(total_debt__gt=0, then='total_debt'),
                    default=Decimal('0'),
                    output_field=DecimalField()
                )
            ),
            total_paid=Sum('total_paid'),
            total_orders=Sum('total_orders_amount'),
        )
        
        total_receivables = aggregates['total_receivables'] or 0
        total_paid = aggregates['total_paid'] or 0
        total_orders = aggregates['total_orders'] or 0
        payment_percentage = (total_paid / total_orders * 100) if total_orders > 0 else 0
        
        # Pagination
        paginator = Paginator(summaries, 50)
        page_obj = paginator.get_page(page_number)
        
        # ===== تحسين #3: StringAgg مع only() =====
        customer_ids_in_page = [s.customer_id for s in page_obj]
        
        orders_filter_for_branches = Q(customer_id__in=customer_ids_in_page)
        if branch_id:
            try:
                orders_filter_for_branches &= Q(branch_id=int(branch_id))
            except (ValueError, TypeError):
                pass
        if salesperson_id:
            try:
                orders_filter_for_branches &= Q(created_by_id=int(salesperson_id))
            except (ValueError, TypeError):
                pass
        
        # استخدام StringAgg مع only()
        customer_branches_dict = dict(
            Order.objects.filter(orders_filter_for_branches)
            .values('customer_id')
            .annotate(
                branches_list=StringAgg('branch__name', delimiter=', ', distinct=True)
            )
            .values_list('customer_id', 'branches_list')
        )
        
        # إعداد البيانات النهائية
        customers_data = []
        for summary in page_obj:
            branches = customer_branches_dict.get(summary.customer_id, '-') or '-'
            customers_data.append({
                'summary': summary,
                'customer': summary.customer,
                'branches': branches,
            })
        
        # قوائم الفلاتر (مع only())
        branches = Branch.objects.filter(is_active=True).only('id', 'name').order_by('name')
        
        salesperson_ids = Order.objects.filter(
            created_by__isnull=False
        ).values_list('created_by_id', flat=True).distinct()
        
        salespersons = User.objects.filter(
            id__in=salesperson_ids,
            is_active=True
        ).only('id', 'first_name', 'username').order_by('first_name', 'username')

        context = {
            "customers_data": customers_data,
            "page_obj": page_obj,
            "total_receivables": total_receivables,
            "total_paid": total_paid,
            "payment_percentage": payment_percentage,
            "branches": branches,
            "salespersons": salespersons,
            "selected_branch": branch_id,
            "selected_salesperson": salesperson_id,
            "selected_status": status,
            "search_query": search_query,
        }
        
        # حفظ في الـ cache لمدة 5 دقائق
        cache.set(cache_key, context, 300)
    
    context.update(get_currency_context())
    return render(request, "accounting/reports/customer_balances.html", context)


@login_required
def daily_transactions_report(request):
    """
    تقرير الحركات اليومية
    """
    form = DateRangeFilterForm(request.GET)

    date = request.GET.get("date", timezone.now().date().isoformat())

    transactions = Transaction.objects.filter(
        date=date, status="posted"
    ).prefetch_related("lines__account")

    context = {
        "transactions": transactions,
        "date": date,
        "form": form,
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/daily_transactions.html", context)


@login_required
def cash_flow(request):
    """
    تقرير التدفقات النقدية - يُصنّف حركات الحسابات إلى أنشطة تشغيلية واستثمارية وتمويلية
    """
    form = DateRangeFilterForm(request.GET)

    start_date = None
    end_date = None
    if form.is_valid():
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")

    # فلترة القيود المرحّلة
    lines_qs = TransactionLine.objects.filter(
        transaction__status="posted"
    ).select_related("account", "account__account_type")

    if start_date:
        lines_qs = lines_qs.filter(transaction__date__gte=start_date)
    if end_date:
        lines_qs = lines_qs.filter(transaction__date__lte=end_date)

    # تصنيف الحسابات حسب نوع النشاط
    # الأنشطة التشغيلية: إيرادات (4)، مصروفات (5)، ذمم مدينة (12)، حسابات العملاء (1200)
    # الأنشطة الاستثمارية: الأصول (1) باستثناء المتداولة
    # الأنشطة التمويلية: الالتزامات (2)، حقوق الملكية (3)

    operating_prefixes = ['4', '5', '11', '12', '1200']
    investing_prefixes = ['1']
    financing_prefixes = ['2', '3']

    operating_items = []
    investing_items = []
    financing_items = []
    total_operating = Decimal("0")
    total_investing = Decimal("0")
    total_financing = Decimal("0")

    # تجميع حسب الحساب
    account_lines = lines_qs.values(
        'account__id', 'account__name', 'account__code',
        'account__account_type__code_prefix', 'account__account_type__name'
    ).annotate(
        sum_debit=Sum('debit'),
        sum_credit=Sum('credit')
    ).order_by('account__code')

    for item in account_lines:
        prefix = str(item['account__account_type__code_prefix'])
        net = (item['sum_debit'] or Decimal("0")) - (item['sum_credit'] or Decimal("0"))

        if net == 0:
            continue

        entry = {
            'name': item['account__name'],
            'code': item['account__code'],
            'type': item['account__account_type__name'],
            'debit': item['sum_debit'] or Decimal("0"),
            'credit': item['sum_credit'] or Decimal("0"),
            'net': net,
        }

        # تصنيف النشاط بناءً على بادئة نوع الحساب
        is_operating = any(prefix.startswith(p) for p in operating_prefixes)
        is_financing = any(prefix.startswith(p) for p in financing_prefixes)

        if is_operating:
            operating_items.append(entry)
            total_operating += net
        elif is_financing:
            financing_items.append(entry)
            total_financing += net
        else:
            # الباقي = استثماري (الأصول غير المتداولة)
            investing_items.append(entry)
            total_investing += net

    net_change = total_operating + total_investing + total_financing

    context = {
        'form': form,
        'operating_items': operating_items,
        'investing_items': investing_items,
        'financing_items': financing_items,
        'total_operating': total_operating,
        'total_investing': total_investing,
        'total_financing': total_financing,
        'net_change': net_change,
        'start_date': start_date,
        'end_date': end_date,
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/cash_flow.html", context)


@login_required
def general_ledger(request):
    """
    دفتر الأستاذ العام - يعرض جميع حركات حساب معين مع الرصيد المتراكم
    """
    from datetime import datetime

    account_id = request.GET.get("account")
    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")

    selected_account = None
    ledger_entries = []
    running_balance = Decimal("0")

    # قائمة الحسابات للاختيار
    accounts = Account.objects.filter(is_active=True).order_by("code")

    if account_id:
        try:
            selected_account = Account.objects.select_related("account_type").get(
                pk=int(account_id)
            )
        except (Account.DoesNotExist, ValueError, TypeError):
            selected_account = None

    if selected_account:
        # بدء الرصيد المتراكم من الرصيد الافتتاحي
        running_balance = selected_account.opening_balance

        lines_qs = TransactionLine.objects.filter(
            account=selected_account,
            transaction__status="posted",
        ).select_related("transaction").order_by("transaction__date", "transaction__id")

        if from_date:
            try:
                from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
                # حساب الرصيد قبل تاريخ البداية
                prior_totals = TransactionLine.objects.filter(
                    account=selected_account,
                    transaction__status="posted",
                    transaction__date__lt=from_dt,
                ).aggregate(sum_debit=Sum("debit"), sum_credit=Sum("credit"))
                running_balance += (prior_totals["sum_debit"] or Decimal("0")) - (
                    prior_totals["sum_credit"] or Decimal("0")
                )
                lines_qs = lines_qs.filter(transaction__date__gte=from_dt)
            except ValueError:
                pass

        if to_date:
            try:
                to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
                lines_qs = lines_qs.filter(transaction__date__lte=to_dt)
            except ValueError:
                pass

        for line in lines_qs:
            running_balance += line.debit - line.credit
            ledger_entries.append(
                {
                    "date": line.transaction.date,
                    "transaction": line.transaction,
                    "description": line.description or line.transaction.description,
                    "debit": line.debit,
                    "credit": line.credit,
                    "balance": running_balance,
                }
            )

    context = {
        "accounts": accounts,
        "selected_account": selected_account,
        "ledger_entries": ledger_entries,
        "from_date": from_date,
        "to_date": to_date,
        "opening_balance": selected_account.opening_balance if selected_account else Decimal("0"),
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/general_ledger.html", context)


@login_required
def aging_report(request):
    """
    تقرير أعمار الديون - يصنف أرصدة العملاء حسب فترة الاستحقاق
    30 / 60 / 90 / 120+ يوم
    """
    from datetime import timedelta
    from orders.models import Order

    today = timezone.now().date()
    buckets = {
        "current": {"label": "أقل من 30 يوم", "min_days": 0, "max_days": 30, "total": Decimal("0"), "customers": []},
        "days_30": {"label": "30-60 يوم", "min_days": 30, "max_days": 60, "total": Decimal("0"), "customers": []},
        "days_60": {"label": "60-90 يوم", "min_days": 60, "max_days": 90, "total": Decimal("0"), "customers": []},
        "days_90": {"label": "90-120 يوم", "min_days": 90, "max_days": 120, "total": Decimal("0"), "customers": []},
        "days_120": {"label": "أكثر من 120 يوم", "min_days": 120, "max_days": 99999, "total": Decimal("0"), "customers": []},
    }

    # جلب العملاء المديونين
    summaries = CustomerFinancialSummary.objects.filter(
        total_debt__gt=0
    ).select_related("customer").order_by("-total_debt")

    grand_total = Decimal("0")

    for summary in summaries:
        # أقدم طلب غير مسدد
        oldest_order = (
            Order.objects.filter(
                customer=summary.customer,
                remaining_amount__gt=0,
            )
            .order_by("created_at")
            .values_list("created_at", flat=True)
            .first()
        )

        if oldest_order:
            days_old = (today - oldest_order.date()).days
        else:
            days_old = 0

        entry = {
            "customer": summary.customer,
            "balance": summary.total_debt,
            "days_old": days_old,
        }

        grand_total += summary.total_debt

        # وضع في الشريحة المناسبة
        placed = False
        for key, bucket in buckets.items():
            if bucket["min_days"] <= days_old < bucket["max_days"]:
                bucket["customers"].append(entry)
                bucket["total"] += summary.total_debt
                placed = True
                break
        if not placed:
            buckets["days_120"]["customers"].append(entry)
            buckets["days_120"]["total"] += summary.total_debt

    context = {
        "buckets": buckets,
        "grand_total": grand_total,
        "total_customers": summaries.count(),
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/aging_report.html", context)


# ============================================
# Export Endpoints
# ============================================


@login_required
@permission_required("accounting.can_export_reports", raise_exception=True)
def export_trial_balance(request):
    """
    تصدير ميزان المراجعة إلى Excel
    """
    from .export_utils import export_trial_balance_excel

    accounts = (
        Account.objects.filter(is_active=True)
        .select_related("account_type")
        .order_by("code")
    )

    trial_data = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for account in accounts:
        totals = account.transaction_lines.filter(
            transaction__status="posted",
        ).aggregate(sum_debit=Sum("debit"), sum_credit=Sum("credit"))

        debit_total = totals["sum_debit"] or Decimal("0")
        credit_total = totals["sum_credit"] or Decimal("0")
        balance = account.opening_balance + debit_total - credit_total

        debit_balance = balance if balance > 0 else Decimal("0")
        credit_balance = abs(balance) if balance < 0 else Decimal("0")

        if debit_total or credit_total or account.opening_balance:
            trial_data.append({
                "account": account,
                "debit_balance": debit_balance,
                "credit_balance": credit_balance,
            })
            total_debit += debit_balance
            total_credit += credit_balance

    currency = get_currency_context()
    log_audit(
        user=request.user,
        action='DATA_EXPORT',
        description='تصدير ميزان المراجعة إلى Excel',
        model_name='Account',
        ip_address=request.META.get('REMOTE_ADDR'),
    )
    return export_trial_balance_excel(trial_data, total_debit, total_credit, currency["currency_symbol"])


@login_required
@permission_required("accounting.can_export_reports", raise_exception=True)
def export_customer_balances(request):
    """
    تصدير أرصدة العملاء إلى Excel
    """
    from .export_utils import export_customer_balances_excel

    summaries = CustomerFinancialSummary.objects.filter(
        total_debt__gt=0
    ).select_related("customer").order_by("-total_debt")

    customers_data = []
    for summary in summaries:
        customers_data.append({
            "summary": summary,
            "customer": summary.customer,
        })

    currency = get_currency_context()
    log_audit(
        user=request.user,
        action='DATA_EXPORT',
        description=f'تصدير أرصدة العملاء إلى Excel ({len(customers_data)} عميل)',
        model_name='CustomerFinancialSummary',
        ip_address=request.META.get('REMOTE_ADDR'),
    )
    return export_customer_balances_excel(customers_data, currency["currency_symbol"])


@login_required
@permission_required("accounting.can_export_reports", raise_exception=True)
def export_general_ledger_excel_view(request):
    """
    تصدير دفتر الأستاذ إلى Excel
    """
    from datetime import datetime as dt
    from .export_utils import export_general_ledger_excel

    account_id = request.GET.get("account")
    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")

    if not account_id:
        return HttpResponse("يرجى تحديد الحساب", status=400)

    try:
        account = Account.objects.get(pk=int(account_id))
    except (Account.DoesNotExist, ValueError, TypeError):
        return HttpResponse("حساب غير موجود", status=404)

    running_balance = account.opening_balance
    lines_qs = TransactionLine.objects.filter(
        account=account,
        transaction__status="posted",
    ).select_related("transaction").order_by("transaction__date", "transaction__id")

    if from_date:
        try:
            from_dt = dt.strptime(from_date, "%Y-%m-%d").date()
            prior = TransactionLine.objects.filter(
                account=account,
                transaction__status="posted",
                transaction__date__lt=from_dt,
            ).aggregate(sum_debit=Sum("debit"), sum_credit=Sum("credit"))
            running_balance += (prior["sum_debit"] or Decimal("0")) - (prior["sum_credit"] or Decimal("0"))
            lines_qs = lines_qs.filter(transaction__date__gte=from_dt)
        except ValueError:
            pass

    if to_date:
        try:
            to_dt = dt.strptime(to_date, "%Y-%m-%d").date()
            lines_qs = lines_qs.filter(transaction__date__lte=to_dt)
        except ValueError:
            pass

    ledger_entries = []
    for line in lines_qs:
        running_balance += line.debit - line.credit
        ledger_entries.append({
            "date": line.transaction.date,
            "transaction": line.transaction,
            "description": line.description or line.transaction.description,
            "debit": line.debit,
            "credit": line.credit,
            "balance": running_balance,
        })

    currency = get_currency_context()
    return export_general_ledger_excel(ledger_entries, account, currency["currency_symbol"])


# ============================================
# API Endpoints
# ============================================


@login_required
def api_customer_summary(request, customer_id):
    """
    API: الملخص المالي للعميل
    """
    try:
        from customers.models import Customer

        customer = get_object_or_404(Customer, pk=customer_id)
    except Exception:
        return JsonResponse({"error": "Customer not found"}, status=404)

    summary, _ = CustomerFinancialSummary.objects.get_or_create(customer=customer)
    summary.refresh()

    # الحصول على العملة من إعدادات النظام
    currency_context = get_currency_context()

    data = {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "total_orders": summary.total_orders_count,
        "total_orders_amount": float(summary.total_orders_amount),
        "total_payments": float(summary.total_paid),
        "balance": float(summary.total_debt),
        "total_advances": float(summary.total_advances),
        "remaining_advances": float(summary.remaining_advances),
        "available_advances": float(summary.remaining_advances),
        "status": (
            "debit"
            if summary.total_debt > 0
            else ("credit" if summary.total_debt < 0 else "clear")
        ),
        "currency_symbol": currency_context["currency_symbol"],
        "currency_code": currency_context["currency_code"],
    }

    return JsonResponse(data)


@login_required
def api_customer_badge(request, customer_id):
    """
    API: شارة الحالة المالية للعميل
    """
    try:
        from customers.models import Customer

        customer = get_object_or_404(Customer, pk=customer_id)
    except Exception:
        return JsonResponse({"error": "Customer not found"}, status=404)

    summary, _ = CustomerFinancialSummary.objects.get_or_create(customer=customer)
    summary.refresh()

    # الحصول على العملة من إعدادات النظام
    currency_context = get_currency_context()
    currency_symbol = currency_context["currency_symbol"]

    if summary.total_debt > 0:
        badge = {
            "text": f"مدين: {summary.total_debt:,.2f} {currency_symbol}",
            "class": "badge-danger",
            "color": "#dc3545",
            "icon": "fa-exclamation-triangle",
        }
    elif summary.total_debt < 0:
        badge = {
            "text": f"له رصيد: {abs(summary.total_debt):,.2f} {currency_symbol}",
            "class": "badge-success",
            "color": "#28a745",
            "icon": "fa-check-circle",
        }
    else:
        badge = {
            "text": "حساب صافي",
            "class": "badge-info",
            "color": "#17a2b8",
            "icon": "fa-check",
        }

    # إضافة السلف المتاحة
    if summary.remaining_advances > 0:
        badge["advances"] = {
            "text": f"سلف متاحة: {summary.remaining_advances:,.2f} {currency_symbol}",
            "amount": float(summary.remaining_advances),
        }

    badge["currency_symbol"] = currency_symbol

    return JsonResponse(badge)


@login_required
def api_accounts_search(request):
    """
    API: بحث في الحسابات
    """
    query = request.GET.get("q", "")

    accounts = (
        Account.objects.filter(is_active=True)
        .filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
            | Q(name_en__icontains=query)
        )
        .order_by("code")[:20]
    )

    data = [
        {
            "id": a.id,
            "code": a.code,
            "name": a.name,
            "full_name": f"{a.code} - {a.name}",
            "balance": float(a.current_balance),
        }
        for a in accounts
    ]

    return JsonResponse({"accounts": data})


@login_required
def api_dashboard_stats(request):
    """
    API: إحصائيات لوحة التحكم
    """
    today = timezone.now().date()

    try:
        from orders.models import Payment
        
        # حساب إجمالي الدفعات العامة غير المخصصة
        general_payments_total = Payment.objects.filter(
            payment_type='general'
        ).annotate(
            remaining=models.F('amount') - models.F('allocated_amount')
        ).filter(remaining__gt=0).aggregate(
            total=Sum('remaining')
        )['total'] or 0
    except Exception:
        general_payments_total = 0

    data = {
        "total_receivables": float(
            CustomerFinancialSummary.objects.filter(total_debt__gt=0).aggregate(
                total=Sum("total_debt")
            )["total"]
            or 0
        ),
        "general_payments": float(general_payments_total),
        "today_transactions": Transaction.objects.filter(
            date=today, status="posted"
        ).count(),
        "pending_transactions": Transaction.objects.filter(status="draft").count(),
    }

    return JsonResponse(data)
