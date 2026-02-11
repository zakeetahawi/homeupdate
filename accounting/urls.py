"""
مسارات النظام المحاسبي
Accounting URLs
"""

from django.urls import path

from . import views, views_bank, views_statement

app_name = "accounting"

urlpatterns = [
    # ============================================
    # لوحة التحكم المحاسبية
    # ============================================
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard_alt"),
    # ============================================
    # شجرة الحسابات
    # ============================================
    path("accounts/", views.account_list, name="account_list"),
    path("accounts/tree/", views.account_tree, name="account_tree"),
    path("accounts/<int:pk>/", views.account_detail, name="account_detail"),
    path(
        "accounts/<int:pk>/statement/",
        views.account_statement,
        name="account_statement",
    ),
    # ============================================
    # القيود المحاسبية
    # ============================================
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("transactions/create/", views.transaction_create, name="transaction_create"),
    path("transactions/<int:pk>/", views.transaction_detail, name="transaction_detail"),
    path(
        "transactions/<int:pk>/post/", views.transaction_post, name="transaction_post"
    ),
    path(
        "transactions/<int:pk>/void/", views.transaction_void, name="transaction_void"
    ),
    path(
        "transactions/<int:pk>/print/",
        views.transaction_print,
        name="transaction_print",
    ),
    # ============================================
    # الملف المالي للعميل
    # ============================================
    path(
        "customer/<int:customer_id>/financial/",
        views.customer_financial_summary,
        name="customer_financial",
    ),
    path(
        "customer/<int:customer_id>/statement/",
        views.customer_statement,
        name="customer_statement",
    ),
    path(
        "customer/<int:customer_id>/account-statement/",
        views_statement.customer_account_statement,
        name="customer_account_statement",
    ),

    path(
        "customer/<int:customer_id>/payments/",
        views.customer_payments,
        name="customer_payments",
    ),
    path(
        "customer/<int:customer_id>/register-payment/",
        views.register_customer_payment,
        name="register_payment",
    ),

    # ============================================
    # التقارير
    # ============================================
    path("reports/", views.reports_index, name="reports"),
    path("reports/trial-balance/", views.trial_balance, name="trial_balance"),
    path("reports/income-statement/", views.income_statement, name="income_statement"),
    path("reports/balance-sheet/", views.balance_sheet, name="balance_sheet"),
    path(
        "reports/customer-balances/",
        views.customer_balances_report,
        name="customer_balances",
    ),
    path(
        "reports/daily-transactions/",
        views.daily_transactions_report,
        name="daily_transactions",
    ),
    path(
        "reports/general-ledger/",
        views.general_ledger,
        name="general_ledger",
    ),
    path(
        "reports/aging-report/",
        views.aging_report,
        name="aging_report",
    ),
    path(
        "reports/cash-flow/",
        views.cash_flow,
        name="cash_flow",
    ),
    # ============================================
    # التصدير
    # ============================================
    path(
        "export/trial-balance/",
        views.export_trial_balance,
        name="export_trial_balance",
    ),
    path(
        "export/customer-balances/",
        views.export_customer_balances,
        name="export_customer_balances",
    ),
    path(
        "export/general-ledger/",
        views.export_general_ledger_excel_view,
        name="export_general_ledger",
    ),

    # ============================================
    # API للبيانات
    # ============================================
    path(
        "api/customer/<int:customer_id>/summary/",
        views.api_customer_summary,
        name="api_customer_summary",
    ),
    path(
        "api/customer/<int:customer_id>/badge/",
        views.api_customer_badge,
        name="api_customer_badge",
    ),
    path("api/accounts/search/", views.api_accounts_search, name="api_accounts_search"),
    path("api/dashboard-stats/", views.api_dashboard_stats, name="api_dashboard_stats"),
    # ============================================
    # Bank Accounts QR System
    # ============================================
    path("bank-qr/<str:unique_code>/", views_bank.bank_qr_view, name="bank_qr"),
    path("bank-qr-all/", views_bank.all_banks_qr_view, name="all_banks_qr"),
    path("bank-qr-pdf/", views_bank.export_bank_qr_pdf, name="bank_qr_pdf"),
]
