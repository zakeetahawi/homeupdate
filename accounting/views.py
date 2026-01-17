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

from .forms import (
    AccountForm,
    AdvanceUsageForm,
    CustomerAdvanceForm,
    DateRangeFilterForm,
    QuickAdvanceForm,
    QuickPaymentForm,
    TransactionForm,
    TransactionLineFormSet,
)
from .models import (
    Account,
    AccountingSettings,
    AccountType,
    AdvanceUsage,
    CustomerAdvance,
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
    لوحة التحكم المحاسبية الرئيسية
    """
    today = timezone.now().date()

    # إحصائيات عامة
    context = {
        "total_accounts": Account.objects.filter(is_active=True).count(),
        "total_transactions": Transaction.objects.filter(status="posted").count(),
        "pending_transactions": Transaction.objects.filter(status="draft").count(),
        "active_advances": CustomerAdvance.objects.filter(status="active").count(),
    }

    # إجمالي السلف النشطة
    context["total_advances_amount"] = CustomerAdvance.objects.filter(
        status="active"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # آخر القيود
    context["recent_transactions"] = Transaction.objects.filter(
        status="posted"
    ).order_by("-date", "-id")[:10]

    # عملاء لديهم مديونية
    context["customers_with_debt"] = CustomerFinancialSummary.objects.filter(
        total_debt__gt=0
    ).order_by("-total_debt")[:10]

    # إجمالي المديونيات
    context["total_receivables"] = CustomerFinancialSummary.objects.filter(
        total_debt__gt=0
    ).aggregate(total=Sum("total_debt"))["total"] or Decimal("0")

    # إضافة سياق العملة
    context.update(get_currency_context())

    return render(request, "accounting/dashboard.html", context)


# ============================================
# شجرة الحسابات
# ============================================


@login_required
def account_list(request):
    """
    قائمة الحسابات
    """
    accounts = (
        Account.objects.filter(is_active=True)
        .select_related("account_type", "parent")
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

    context = {
        "accounts": accounts,
        "account_types": AccountType.objects.all(),
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
        .order_by("-transaction__transaction_date")[:50]
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
    قائمة القيود
    """
    transactions = (
        Transaction.objects.all()
        .select_related("customer", "order", "created_by")
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

                transaction.check_balance()
                transaction.save()

            messages.success(
                request, f"تم إنشاء القيد {transaction.reference_number} بنجاح"
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

    if transaction.post(request.user):
        messages.success(request, "تم ترحيل القيد بنجاح")
    else:
        messages.error(request, "فشل ترحيل القيد - تأكد من توازن القيد")

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
        if transaction.void(request.user, reason):
            messages.success(request, "تم إلغاء القيد بنجاح")
        else:
            messages.error(request, "فشل إلغاء القيد")

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


@login_required
def advance_list(request):
    """
    قائمة العربونات
    """
    advances = (
        CustomerAdvance.objects.all()
        .select_related("customer", "created_by")
        .order_by("-created_at")
    )

    # فلترة
    status = request.GET.get("status")
    if status:
        advances = advances.filter(status=status)

    payment_method = request.GET.get("payment_method")
    if payment_method:
        advances = advances.filter(payment_method=payment_method)

    search = request.GET.get("q")
    if search:
        advances = advances.filter(
            Q(customer__name__icontains=search)
            | Q(customer__phone__icontains=search)
            | Q(receipt_number__icontains=search)
            | Q(advance_number__icontains=search)
        )

    # التصفح
    paginator = Paginator(advances, 30)
    page = request.GET.get("page")
    advances = paginator.get_page(page)

    context = {
        "advances": advances,
    }
    context.update(get_currency_context())
    return render(request, "accounting/advance_list.html", context)


@login_required
def advance_create(request):
    """
    إنشاء عربون جديد
    """
    customer_id = request.GET.get("customer")
    initial_customer = None

    if customer_id:
        try:
            from customers.models import Customer

            initial_customer = Customer.objects.get(pk=customer_id)
        except:
            pass

    if request.method == "POST":
        form = CustomerAdvanceForm(request.POST, customer=initial_customer)
        if form.is_valid():
            advance = form.save(commit=False)
            advance.created_by = request.user
            advance.save()

            messages.success(request, "تم تسجيل العربون بنجاح")
            return redirect("accounting:advance_detail", pk=advance.pk)
    else:
        form = CustomerAdvanceForm(customer=initial_customer)

    context = {
        "form": form,
        "customer": initial_customer,
    }
    context.update(get_currency_context())
    return render(request, "accounting/advance_form.html", context)


@login_required
def advance_detail(request, pk):
    """
    تفاصيل العربون
    """
    advance = get_object_or_404(
        CustomerAdvance.objects.select_related("customer", "created_by", "transaction"),
        pk=pk,
    )

    # استخدامات العربون
    usages = advance.usages.select_related("order", "created_by").order_by(
        "-created_at"
    )

    context = {
        "advance": advance,
        "usages": usages,
    }
    context.update(get_currency_context())
    return render(request, "accounting/advance_detail.html", context)


@login_required
def advance_use(request, pk):
    """
    استخدام العربون على طلب
    """
    advance = get_object_or_404(CustomerAdvance, pk=pk, status="active")

    if request.method == "POST":
        form = AdvanceUsageForm(request.POST, advance=advance)
        if form.is_valid():
            order_id = form.cleaned_data["order"]
            amount = form.cleaned_data["amount"]

            try:
                from orders.models import Order

                order = Order.objects.get(pk=order_id, customer=advance.customer)

                if advance.use_for_order(order, amount, request.user):
                    messages.success(
                        request,
                        f"تم استخدام {amount} من العربون للطلب {order.order_number}",
                    )
                else:
                    messages.error(request, "فشل استخدام العربون")
            except Order.DoesNotExist:
                messages.error(request, "الطلب غير موجود")
        else:
            messages.error(request, "بيانات غير صحيحة")

    return redirect("accounting:advance_detail", pk=pk)


# ============================================
# الملف المالي للعميل
# ============================================


@login_required
def customer_financial_summary(request, customer_id):
    """
    الملخص المالي للعميل
    """
    try:
        from customers.models import Customer

        customer = get_object_or_404(Customer, pk=customer_id)
    except:
        return HttpResponse("خطأ في الوصول للعميل", status=400)

    # الحصول على أو إنشاء الملخص المالي
    summary, created = CustomerFinancialSummary.objects.get_or_create(customer=customer)
    if not created:
        summary.refresh()

    # السلف النشطة
    active_advances = CustomerAdvance.objects.filter(customer=customer, status="active")

    # آخر المدفوعات
    try:
        from orders.models import Payment

        recent_payments = Payment.objects.filter(order__customer=customer).order_by(
            "-payment_date"
        )[:10]
    except:
        recent_payments = []

    # آخر القيود
    recent_transactions = Transaction.objects.filter(
        customer=customer, status="posted"
    ).order_by("-date")[:10]

    context = {
        "customer": customer,
        "summary": summary,
        "active_advances": active_advances,
        "recent_payments": recent_payments,
        "recent_transactions": recent_transactions,
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
    except:
        return HttpResponse("خطأ في الوصول للعميل", status=400)

    # البحث عن حساب العميل
    customer_account = Account.objects.filter(customer=customer).first()

    if customer_account:
        return redirect("accounting:account_statement", pk=customer_account.pk)

    messages.warning(request, "لا يوجد حساب مخصص لهذا العميل")
    return redirect("accounting:customer_financial", customer_id=customer_id)


@login_required
def customer_advances(request, customer_id):
    """
    عربون العميل
    """
    try:
        from customers.models import Customer

        customer = get_object_or_404(Customer, pk=customer_id)
    except:
        return HttpResponse("خطأ في الوصول للعميل", status=400)

    advances = CustomerAdvance.objects.filter(customer=customer).order_by("-created_at")

    context = {
        "customer": customer,
        "advances": advances,
    }
    context.update(get_currency_context())
    return render(request, "accounting/customer_advances.html", context)


@login_required
def customer_payments(request, customer_id):
    """
    مدفوعات العميل
    """
    try:
        from customers.models import Customer

        customer = get_object_or_404(Customer, pk=customer_id)
    except:
        return HttpResponse("خطأ في الوصول للعميل", status=400)

    try:
        from orders.models import Payment

        payments = (
            Payment.objects.filter(order__customer=customer)
            .select_related("order")
            .order_by("-payment_date")
        )
    except:
        payments = []

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
    except:
        return HttpResponse("خطأ في الوصول للعميل", status=400)

    if request.method == "POST":
        form = QuickPaymentForm(request.POST, customer=customer)
        if form.is_valid():
            # إنشاء الدفعة
            try:
                from orders.models import Order, Payment

                order_id = form.cleaned_data.get("order")
                order = None
                if order_id:
                    order = Order.objects.get(pk=order_id, customer=customer)

                # إنشاء الدفعة عبر نظام الطلبات
                # أو إنشاء قيد مباشر
                payment_data = {
                    "amount": form.cleaned_data["amount"],
                    "payment_date": form.cleaned_data["payment_date"],
                    "payment_method": form.cleaned_data["payment_method"],
                    "receipt_number": form.cleaned_data.get("receipt_number", ""),
                    "notes": form.cleaned_data.get("notes", ""),
                }

                if order:
                    payment = Payment.objects.create(order=order, **payment_data)
                    messages.success(
                        request, f"تم تسجيل الدفعة بنجاح للطلب {order.order_number}"
                    )
                else:
                    # إنشاء قيد مباشر بدون طلب
                    messages.success(request, "تم تسجيل الدفعة بنجاح")

            except Exception as e:
                messages.error(request, f"خطأ: {str(e)}")
        else:
            messages.error(request, "بيانات غير صحيحة")

    # العودة للصفحة السابقة أو صفحة العميل
    referer = request.META.get("HTTP_REFERER", "")
    if "customer" in referer and "accounting" not in referer:
        return redirect(
            "customers:customer_detail_by_code", customer_code=customer.code
        )
    return redirect("accounting:customer_financial", customer_id=customer_id)


@login_required
def register_customer_advance(request, customer_id):
    """
    تسجيل سلفة للعميل
    """
    try:
        from customers.models import Customer

        customer = get_object_or_404(Customer, pk=customer_id)
    except:
        return HttpResponse("خطأ في الوصول للعميل", status=400)

    if request.method == "POST":
        form = QuickAdvanceForm(request.POST, customer=customer)
        if form.is_valid():
            advance = CustomerAdvance.objects.create(
                customer=customer,
                amount=form.cleaned_data["amount"],
                payment_method=form.cleaned_data["payment_method"],
                receipt_number=form.cleaned_data.get("receipt_number", ""),
                notes=form.cleaned_data.get("notes", ""),
                created_by=request.user,
                status="active",
            )
            messages.success(
                request, f"تم تسجيل العربون بنجاح - المبلغ: {advance.amount}"
            )
        else:
            messages.error(request, "بيانات غير صحيحة")

    # العودة للصفحة السابقة أو صفحة العميل
    referer = request.META.get("HTTP_REFERER", "")
    if "customer" in referer and "accounting" not in referer:
        return redirect(
            "customers:customer_detail_by_code", customer_code=customer.code
        )
    return redirect("accounting:customer_financial", customer_id=customer_id)


# ============================================
# التقارير
# ============================================


@login_required
def reports_index(request):
    """
    صفحة التقارير الرئيسية - تحويل مباشر لتقارير حسابات المصنع
    """
    return redirect("factory_accounting:reports")


@login_required
def trial_balance(request):
    """
    ميزان المراجعة
    """
    form = DateRangeFilterForm(request.GET)

    accounts = (
        Account.objects.filter(is_active=True)
        .select_related("account_type")
        .order_by("code")
    )

    # حساب الأرصدة
    trial_data = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for account in accounts:
        balance = account.current_balance
        debit = balance if balance > 0 else Decimal("0")
        credit = abs(balance) if balance < 0 else Decimal("0")

        if debit > 0 or credit > 0:
            trial_data.append({"account": account, "debit": debit, "credit": credit})
            total_debit += debit
            total_credit += credit

    context = {
        "trial_data": trial_data,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "form": form,
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/trial_balance.html", context)


@login_required
def income_statement(request):
    """
    قائمة الدخل
    """
    form = DateRangeFilterForm(request.GET)

    # الإيرادات
    revenue_accounts = Account.objects.filter(
        account_type__normal_balance="credit",
        account_type__code_prefix__startswith="4",
        is_active=True,
    )
    total_revenue = sum(abs(a.current_balance) for a in revenue_accounts)

    # المصروفات
    expense_accounts = Account.objects.filter(
        account_type__normal_balance="debit",
        account_type__code_prefix__startswith="5",
        is_active=True,
    )
    total_expenses = sum(a.current_balance for a in expense_accounts)

    # صافي الربح
    net_income = total_revenue - total_expenses

    context = {
        "revenue_accounts": revenue_accounts,
        "expense_accounts": expense_accounts,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_income": net_income,
        "form": form,
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/income_statement.html", context)


@login_required
def balance_sheet(request):
    """
    الميزانية العمومية
    """
    # الأصول
    asset_accounts = Account.objects.filter(
        account_type__normal_balance="debit",
        account_type__code_prefix__startswith="1",
        is_active=True,
    ).order_by("code")
    total_assets = sum(a.current_balance for a in asset_accounts)

    # الخصوم
    liability_accounts = Account.objects.filter(
        account_type__normal_balance="credit",
        account_type__code_prefix__startswith="2",
        is_active=True,
    ).order_by("code")
    total_liabilities = sum(abs(a.current_balance) for a in liability_accounts)

    # حقوق الملكية
    equity_accounts = Account.objects.filter(
        account_type__normal_balance="credit",
        account_type__code_prefix__startswith="3",
        is_active=True,
    ).order_by("code")
    total_equity = sum(abs(a.current_balance) for a in equity_accounts)

    context = {
        "asset_accounts": asset_accounts,
        "liability_accounts": liability_accounts,
        "equity_accounts": equity_accounts,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/balance_sheet.html", context)


@login_required
def customer_balances_report(request):
    """
    تقرير أرصدة العملاء
    """
    summaries = CustomerFinancialSummary.objects.select_related("customer").order_by(
        "-total_debt"
    )

    # فلترة
    status = request.GET.get("status")
    if status == "debit":
        summaries = summaries.filter(total_debt__gt=0)
    elif status == "credit":
        summaries = summaries.filter(total_debt__lt=0)
    elif status == "clear":
        summaries = summaries.filter(total_debt=0)

    # الإجماليات
    totals = summaries.aggregate(
        total_receivables=Sum("total_debt", filter=Q(total_debt__gt=0)),
        total_payables=Sum("total_debt", filter=Q(total_debt__lt=0)),
    )

    context = {
        "summaries": summaries,
        "totals": totals,
    }
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
def advances_report(request):
    """
    تقرير العربون
    """
    advances = CustomerAdvance.objects.select_related("customer").order_by(
        "-created_at"
    )

    # فلترة الحالة
    status = request.GET.get("status")
    if status:
        advances = advances.filter(status=status)

    # الإجماليات
    totals = advances.aggregate(
        total_amount=Sum("amount"),
        total_remaining_sum=Sum("remaining_amount"),
    )
    totals["total_remaining"] = totals["total_remaining_sum"] or 0
    totals["total_used"] = (totals["total_amount"] or 0) - totals["total_remaining"]

    context = {
        "advances": advances,
        "totals": totals,
    }
    context.update(get_currency_context())
    return render(request, "accounting/reports/advances.html", context)


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
    except:
        return JsonResponse({"error": "Customer not found"}, status=404)

    summary, _ = CustomerFinancialSummary.objects.get_or_create(customer=customer)

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
    except:
        return JsonResponse({"error": "Customer not found"}, status=404)

    summary, _ = CustomerFinancialSummary.objects.get_or_create(customer=customer)

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

    data = {
        "total_receivables": float(
            CustomerFinancialSummary.objects.filter(total_debt__gt=0).aggregate(
                total=Sum("total_debt")
            )["total"]
            or 0
        ),
        "active_advances": float(
            CustomerAdvance.objects.filter(status="active").aggregate(
                total=Sum("remaining_amount")
            )["total"]
            or 0
        ),
        "today_transactions": Transaction.objects.filter(
            date=today, status="posted"
        ).count(),
        "pending_transactions": Transaction.objects.filter(status="draft").count(),
    }

    return JsonResponse(data)
