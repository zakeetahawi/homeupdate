# AI Agent Instructions - El-Khawaga ERP System

## System Architecture

This is a Django 6.0-based ERP/CRM system for a manufacturing business, primarily serving Arabic-speaking users. The system manages the complete order-to-cash cycle: inspections, manufacturing, cutting, installation, and comprehensive double-entry accounting.

### Core Applications Structure

```
crm/              # Main Django project (settings, celery, asgi)
├── accounts/     # User authentication, roles, permissions
├── customers/    # Customer management, hierarchical accounts
├── orders/       # Order lifecycle, payments, wizards
├── manufacturing/# Manufacturing orders, materials tracking
├── cutting/      # Cutting operations (fabrics, materials)
├── installations/# Installation scheduling, modifications
├── inventory/    # Stock management, transfers, product management
├── accounting/   # Double-entry bookkeeping, financial reports
├── factory_accounting/ # Factory-specific accounting
├── installation_accounting/ # Installation-specific accounting
├── reports/      # Financial and operational reports
├── complaints/   # Customer complaint tracking
├── inspections/  # Pre-order customer inspections
└── notifications/# In-app notification system
```

### Technology Stack

- **Backend**: Django 6.0 with ASGI (Daphne), REST Framework
- **Async Tasks**: Celery 5.5 with Redis broker
- **WebSockets**: Django Channels 4.3+ for real-time features
- **Database**: MySQL (primary), Redis (cache/sessions)
- **Caching**: django-cacheops (ORM-level), Redis
- **Security**: django-axes (brute-force protection), custom middleware
- **Languages**: Bilingual Arabic/English (Arabic primary)

## Critical Patterns & Conventions

### 1. Query Optimization (MANDATORY)

**Always** use `select_related()` and `prefetch_related()` for related objects. The codebase has multiple performance reports documenting N+1 query issues.

```python
# ✅ CORRECT - Optimized queries
customers = CustomerFinancialSummary.objects.filter(
    total_debt__gt=0
).select_related(
    'customer', 'customer__branch', 'customer__category'
).prefetch_related(
    Prefetch('customer__customer_orders', 
        queryset=Order.objects.select_related('branch', 'created_by')
            .prefetch_related(
                Prefetch('payments', 
                    queryset=Payment.objects.select_related('created_by')
                )
            )
    )
)

# ❌ WRONG - Creates N+1 queries
customers = CustomerFinancialSummary.objects.filter(total_debt__gt=0)
for customer in customers:
    orders = customer.customer.customer_orders.all()  # N queries
    for order in orders:
        payments = order.payments.all()  # N² queries
```

**Reference**: See `accounting/views.py` (lines 53-160, 489-585, 842-1020) for production patterns.

### 2. Arabic Number Handling

Arabic-Indic numerals (٠-٩) must be converted to ASCII (0-9) for database storage:

```python
# Use core utilities
from core.utils.general import convert_arabic_to_english_numbers

# In models
def save(self, *args, **kwargs):
    self.customer_id = convert_arabic_to_english_numbers(self.customer_id)
    super().save(*args, **kwargs)

# In templates - use custom tag
{% load accounting_numbers %}
{{ value|arabic_to_english }}
```

Frontend: `/static/js/arabic-numbers-converter.js` auto-converts input fields.

### 3. Accounting Double-Entry System

**Every financial transaction requires balanced journal entries**:

```python
# Creating a payment transaction
from accounting.models import Transaction, TransactionLine

transaction = Transaction.objects.create(
    transaction_type='payment',
    description=f"دفعة من {payment.customer.name}",
    status='posted',  # or 'draft' for pending
    created_by=request.user
)

# Debit: Cash/Bank account
TransactionLine.objects.create(
    transaction=transaction,
    account=cash_account,
    debit_amount=payment.amount,
    credit_amount=0
)

# Credit: Customer account (AR)
TransactionLine.objects.create(
    transaction=transaction,
    account=customer_account,
    debit_amount=0,
    credit_amount=payment.amount
)

# ⚠️ CRITICAL: Total debits MUST equal total credits
```

**Important**: From 2026-01-01 onwards, all transactions are tracked. Historical data before this date uses opening balances.

### 4. Management Commands

The accounting system has extensive maintenance commands:

```bash
# Daily/Weekly maintenance
python manage.py daily_maintenance           # Update balances, check transactions
python manage.py verify_customer_balances --fix  # Verify and fix balance discrepancies
python manage.py check_draft_transactions --auto-post  # Post balanced draft transactions

# Monthly/End-of-period
python manage.py trial_balance              # Generate trial balance report
python manage.py final_accounting_report    # Comprehensive system audit

# Setup/Initialization (one-time)
python manage.py setup_accounting_structure  # Create chart of accounts
python manage.py create_customer_accounts   # Create AR accounts for customers
```

**Reference**: `ACCOUNTING_MAINTENANCE_GUIDE.md` for full command documentation.

### 5. Celery Task Patterns

Tasks use specific queues for organization:

```python
from celery import shared_task

@shared_task(
    bind=True, 
    max_retries=3, 
    default_retry_delay=60,
    queue='file_uploads'  # Dedicated queue for heavy I/O
)
def upload_to_drive(self, file_path):
    try:
        # Implementation
        pass
    except Exception as exc:
        raise self.retry(exc=exc)

# Other queues: 'calculations', 'status_updates', 'default'
```

Start workers: `celery -A crm worker -Q default,file_uploads,calculations -l info`

### 6. Custom Middleware Stack

Order matters! Current production setup:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # Compress responses
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',  # Must be after Auth
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.current_user.CurrentUserMiddleware',  # Track current user
    'user_activity.middleware.UserSessionTrackingMiddleware',
]
```

**Note**: Custom query/performance middleware is disabled in production for performance.

## Development Workflows

### Starting the Development Server

The custom `manage.py` automatically starts Redis/Valkey and Celery:

```bash
# Starts Django + Redis + Celery Worker + Celery Beat
python manage.py runserver

# For ASGI/WebSockets (if needed)
daphne -b 0.0.0.0 -p 8000 crm.asgi:application
```

### Deployment Process

**Never deploy directly** - use the deployment script:

```bash
./deploy_update.sh
```

This script handles:
1. Git pull from main branch
2. Pip install requirements
3. Database migrations (all apps)
4. Accounting structure setup
5. Customer account creation  
6. Historical transaction generation (from 2026-01-01)
7. Static file collection
8. Service restarts (systemd)

### Testing

Run accounting system tests:

```bash
./test_improvements.sh          # Comprehensive accounting tests
python manage.py test accounting  # Django unit tests
python manage.py test tests.test_manufacturing_integration
```

Frontend testing uses standalone scripts in `tests/`:
```bash
python tests/test_notifications.py
python tests/test_inspection_simple.py
```

### Database Migrations

Always create migrations for ALL affected apps:

```bash
# Check what needs migrations
python manage.py showmigrations

# Create migrations
./create_migrations.sh  # Creates for all apps

# Or manually
python manage.py makemigrations accounting orders customers

# Apply
python manage.py migrate
```

## Code Style & Conventions

### Mixed Language Comments

- **Arabic**: Business logic, domain concepts, user-facing messages
- **English**: Technical implementation, Django conventions

```python
def customer_financial_summary(request, customer_id):
    """
    الملخص المالي للعميل - Customer Financial Summary
    
    Displays comprehensive financial data including:
    - الديون والمدفوعات (Debts and payments)
    - القيود المحاسبية (Journal entries)
    """
```

### Template Patterns

Django templates with Bootstrap 5 + custom CSS:

```django
{% extends "base.html" %}
{% load static accounting_numbers %}

{% block title %}{{ customer.name }} - الملخص المالي{% endblock %}

{% block content %}
<div class="container-fluid">
    {# Always convert Arabic numbers #}
    <h2>الرصيد: {{ balance|arabic_to_english|floatformat:2 }} ريال</h2>
</div>
{% endblock %}
```

### Signal Usage

Signals auto-create accounting transactions:

```python
# orders/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Payment)
def create_payment_transaction(sender, instance, created, **kwargs):
    if created and instance.payment_type in ['order', 'general']:
        # Auto-create double-entry transaction
        create_transaction_from_payment(instance)
```

## Key Files to Reference

- **Settings**: `crm/settings.py` (1800+ lines, extensively configured)
- **Deployment**: `deploy_update.sh`, `DEPLOYMENT_GUIDE_CHANNELS.md`
- **Accounting Core**: `accounting/models.py`, `accounting/views.py`
- **Performance Docs**: `PERFORMANCE_IMPROVEMENTS_SUMMARY.md`, `100_PERCENT_OPTIMIZATION_PLAN.md`
- **Maintenance**: `ACCOUNTING_MAINTENANCE_GUIDE.md`
- **API Routing**: `crm/urls.py`, `accounts/routing.py` (WebSockets)

## Common Gotchas

1. **Never bypass CurrentUserMiddleware**: It tracks `created_by`/`updated_by` automatically via thread-local storage
2. **Transaction status**: Draft transactions don't affect balances until `status='posted'`
3. **Customer accounts**: Must exist in accounting.Account before creating transactions
4. **Date ranges**: Accounting reports only include data from 2026-01-01 onwards (opening balances for earlier)
5. **Arabic input**: Forms must handle both Arabic and English numerals
6. **Caching**: Use `@cached_as(ModelName, timeout=300)` from cacheops, not manual Redis
7. **File uploads**: Large files (>5MB) should use Celery tasks (`file_uploads` queue)

## Quick Reference Commands

```bash
# Most frequently used
python manage.py verify_customer_balances --fix
python manage.py trial_balance
python manage.py final_accounting_report
./deploy_update.sh

# Celery monitoring
celery -A crm inspect active
celery -A crm flower  # Web UI on :5555

# Database inspection
python manage.py dbshell
python manage.py shell_plus  # Enhanced shell with models pre-loaded
```

## Getting Help

- **Accounting issues**: Check `ACCOUNTING_MAINTENANCE_GUIDE.md`
- **Performance problems**: See `PERFORMANCE_IMPROVEMENTS_SUMMARY.md`
- **Deployment errors**: Review `DEPLOYMENT_GUIDE_CHANNELS.md`
- **API patterns**: Examine existing views in target app
