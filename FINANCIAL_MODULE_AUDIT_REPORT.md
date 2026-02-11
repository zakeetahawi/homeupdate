# 🏦 FINANCIAL MODULE — FULL PROFESSIONAL AUDIT REPORT

**Project:** Elkhawaga ERP System  
**Audit Date:** February 10, 2026  
**Auditor Role:** Senior ERP Financial Systems Architect  
**System Stack:** Django 5.x / PostgreSQL / Redis / Daphne (ASGI)

---

# OUTPUT A: CURRENT STATE REPORT

---

## A1. Architecture Overview

### Modules Detected

| Module | Directory | Purpose | Financial Integration |
|--------|-----------|---------|----------------------|
| `accounting` | `/accounting/` | Core double-entry ledger, chart of accounts, journal entries | **Primary financial module** |
| `orders` | `/orders/` | Sales orders, payments, invoices | ✅ Integrated via signals |
| `customers` | `/customers/` | Customer management | ✅ Partially integrated (no credit_limit) |
| `installations` | `/installations/` | Installation scheduling & tracking | ❌ No accounting integration |
| `inspections` | `/inspections/` | Site visit scheduling | ❌ No accounting integration |
| `factory_accounting` | `/factory_accounting/` | Factory worker cost tracking | ❌ Isolated system |
| `installation_accounting` | `/installation_accounting/` | Installation technician cost tracking | ❌ Isolated system |
| `inventory` | `/inventory/` | Stock management, purchases, transfers | ❌ No accounting integration |
| `manufacturing` | `/manufacturing/` | Production management | ❌ No accounting integration |
| `reports` | `/reports/` | Reporting engine | ⚠️ Siloed reports |
| `accounts` | `/accounts/` | Users, branches, roles | ✅ Provides Branch/User models |
| `core` | `/core/` | Utilities, audit, security middleware | ✅ Provides audit framework |

### Finance Module Structure

```
accounting/
├── models.py          # 903 lines — 7 models (Account, Transaction, TransactionLine, etc.)
├── views.py           # 1240 lines — 20+ views (dashboard, CRUD, reports, APIs)
├── views_bank.py      # 203 lines — QR bank system views
├── views_statement.py # 110 lines — Customer account statement
├── forms.py           # 317 lines — 7 forms
├── admin.py           # 973 lines — Full admin customization
├── signals.py         # 398 lines — Auto journal entries, customer account creation
├── urls.py            # 116 lines — 25 URL patterns
├── performance_utils.py # 323 lines — Caching and query optimization
├── templatetags/      # Arabic number filters
├── management/commands/ # 21 management commands
├── migrations/        # 10 migrations
└── templates/         # 2 standalone templates (bank QR)
    + 18 templates in /templates/accounting/
```

### Database Structure Summary

| Model | Table | Records (est.) | Indexes |
|-------|-------|----------------|---------|
| `AccountType` | `accounting_accounttype` | ~5 | 0 custom |
| `Account` | `accounting_account` | ~14,000+ (13,919 customer accounts) | 5 custom |
| `Transaction` | `accounting_transaction` | Variable | 6 custom |
| `TransactionLine` | `accounting_transactionline` | Variable | 3 custom |
| `CustomerFinancialSummary` | `accounting_customerfinancialsummary` | ~13,919 | 7 custom |
| `AccountingSettings` | `accounting_accountingsettings` | 1 (singleton) | 0 |
| `BankAccount` | `accounting_bankaccount` | Variable | 3 custom |

---

## A2. Detected Problems (Categorized)

---

### 🔴 UI/Template Issues (22 Issues)

| # | Severity | File | Issue |
|---|----------|------|-------|
| T1 | HIGH | `templates/accounting/transaction_form.html` | **No form error display.** `{{ form.errors }}`, `{{ form.non_field_errors }}`, and `{{ formset.errors }}` never rendered. Users see no error messages on validation failure. |
| T2 | HIGH | `templates/accounting/transaction_form.html` | **"Add line" button has no JavaScript handler.** The `#add-line` click handler is undefined. Users cannot add new formset rows dynamically. |
| T3 | HIGH | `templates/accounting/reports/index.html` | **Reports index page is nearly empty.** Only links to factory_accounting reports. Missing links to trial_balance, income_statement, balance_sheet, customer_balances, daily_transactions. |
| T4 | HIGH | `templates/accounting/reports/daily_transactions.html` | **Broken CSS badge.** Uses `bg-{{ transaction.status }}` (e.g., `bg-posted`, `bg-draft`) which are not valid Bootstrap classes. |
| T5 | HIGH | 8 of 20 templates | **Missing pagination.** account_list, account_statement, customer_payments, customer_financial, customer_account_statement, daily_transactions, trial_balance, income_statement have no pagination. |
| T6 | HIGH | 8 templates | **No permission checks in templates.** Admin links, Post/Void/Edit buttons shown to all users regardless of role. Users without permission see buttons that result in 403 errors. |
| T7 | MEDIUM | All report templates | **No Excel/CSV/PDF export buttons.** Only print buttons exist. No data export capability. |
| T8 | MEDIUM | 13 of 20 templates | **Inconsistent number formatting.** Only 4 templates load `accounting_numbers` templatetag for English numeral display. Others show locale-dependent (Arabic) numerals. |
| T9 | MEDIUM | `customer_account_statement.html` | **Hardcoded currency `ج.م`** instead of `{{ currency_symbol }}` context variable. |
| T10 | MEDIUM | `customer_account_statement.html` | **RTL CSS bugs.** Uses `border-left`, `margin-left`, `padding-left` instead of RTL-compatible properties. |
| T11 | MEDIUM | `transaction_detail.html` | **No confirmation on Post action.** Posting is irreversible but lacks "Are you sure?" confirmation dialog. |
| T12 | MEDIUM | `account_tree.html` | **Tree depth limited to 3 levels.** Deeper hierarchies silently truncated. |
| T13 | MEDIUM | `account_detail.html` | **No null guard on `account.account_type.name`.** Will throw NoneType error if account_type is null. |
| T14 | LOW | `all_banks_qr.html`, `bank_qr.html` | **External CDN dependency.** Loads fonts from googleapis/cdnjs while base templates use local files. |
| T15 | LOW | Multiple templates | **Inconsistent table header styling.** Some use `table-dark`, others `table-light`. |
| T16 | LOW | Multiple templates | **Duplicated print CSS.** `@media print` styles repeated inline across templates instead of shared CSS. |
| T17 | LOW | Multiple pages | **Missing breadcrumbs.** Dashboard, transaction_list, customer_payments, all report pages lack navigation breadcrumbs. |
| T18 | LOW | Account tree | **No search/filter on tree view.** |
| T19 | LOW | All list views | **No column sorting controls.** |
| T20 | LOW | Transaction list | **No bulk operations (bulk post/void).** |
| T21 | LOW | Customer pages | **No WhatsApp/share button for statements.** |
| T22 | MEDIUM | Trial balance, Income statement, Balance sheet | **Date range filter not wired.** `DateRangeFilterForm` is in context but reports calculate using `current_balance` which ignores date ranges. |

---

### 🔴 Backend Issues (18 Issues)

| # | Severity | File | Issue |
|---|----------|------|-------|
| B1 | CRITICAL | `accounting/models.py` (Account) | **No unique constraint on `name` field.** `code` is unique but `name` is only indexed. Duplicate account names are allowed by the database. |
| B2 | CRITICAL | `accounting/signals.py:230` | **`advances_account` undefined variable** in `create_advance_transaction()`. References a variable that was never assigned — will raise `NameError` at runtime. |
| B3 | CRITICAL | `accounting/signals.py` | **General payments (order=None) don't create journal entries.** `create_payment_transaction()` at line 39 checks `payment.order and payment.order.customer` — general payments with `order=None` silently skip accounting. |
| B4 | CRITICAL | `accounting/signals.py` | **No reversal journal entry on Payment deletion.** Deleting a Payment doesn't reverse the corresponding journal entry. Accounting entries become orphaned. |
| B5 | CRITICAL | `accounting/signals.py` | **No reversal on Order cancellation.** When an order is cancelled, the original sales invoice journal entry is never reversed. |
| B6 | HIGH | `accounting/views.py:405` | **`transaction.reference_number` and `transaction.check_balance()` don't exist.** `transaction_create` view references methods/properties that aren't on the Transaction model. Will crash at runtime. |
| B7 | HIGH | `accounting/views.py:753-770` | **Trial balance uses `current_balance` sign for debit/credit split.** This is incorrect — positive balance ≠ debit. Should check `account_type.normal_balance` and use absolute values from actual debit/credit aggregates. |
| B8 | HIGH | `accounting/views.py:778-810` | **Income statement sums `current_balance` instead of transaction-based amounts.** Date range filter has no effect — always shows all-time balances. |
| B9 | HIGH | `accounting/views.py:815-850` | **Balance sheet has same problem** — uses stored `current_balance` instead of computing from transaction lines within a period. |
| B10 | HIGH | `accounting/models.py:332` (Transaction.post) | **Post method doesn't verify balance before posting.** Calls `self.is_balanced` but `total_debit`/`total_credit` may not be calculated yet. Should call `calculate_totals()` first. |
| B11 | HIGH | `accounting/apps.py` | **Silent signal failure.** All signal registration wrapped in `try/except` with `print()` — signals can silently fail in production with zero logging/alerting. |
| B12 | MEDIUM | `accounting/models.py` (Account.level, Account.full_path) | **N+1 query problem.** `level` and `full_path` properties traverse parent chain with individual queries per level. |
| B13 | MEDIUM | `accounting/models.py:476` (CustomerFinancialSummary.refresh) | **N+1 on orders.** Iterates all orders in Python to sum `final_price_after_discount` because it's a property — cannot aggregate. |
| B14 | MEDIUM | `accounting/views.py:625` (customer_statement) | **Bare except clause.** `except:` catches all exceptions including SystemExit, KeyboardInterrupt. |
| B15 | MEDIUM | `orders/models.py` | **Dual payment update paths.** `OrderService.add_payment()` increments `paid_amount` manually AND signal recalculates from aggregate — race condition risk. |
| B16 | MEDIUM | `orders/models.py` | **`final_price` vs `final_price_after_discount` divergence.** Stored `final_price` can be stale if `calculate_final_price()` wasn't called after item changes. |
| B17 | LOW | All signal error handlers | **Use `print()` instead of `logging`.** 12+ instances of `print(f"Error...")` instead of `logger.error()`. |
| B18 | LOW | `accounting/views.py` (account_statement) | **Running balance computed in Python loop** instead of using window functions or cumulative sum in DB. |

---

### 🔴 Database Issues (8 Issues)

| # | Severity | File | Issue |
|---|----------|------|-------|
| D1 | CRITICAL | `accounting/models.py` (Account) | **Missing unique constraint on `name`.** Must add unique or unique_together to prevent duplicate account names. |
| D2 | HIGH | `accounting/models.py` (Account) | **`parent` uses `on_delete=CASCADE`.** Deleting a parent account deletes ALL children — should be `PROTECT`. |
| D3 | HIGH | `accounting/models.py` (Account) | **No `currency` field.** Multi-currency support is absent. All amounts assumed to be in a single currency. |
| D4 | HIGH | `accounting/models.py` (Transaction) | **No `approved_by` field.** No transaction approval workflow beyond posting. |
| D5 | HIGH | `accounting/models.py` (TransactionLine) | **No `currency` field.** Cannot track multi-currency entries. |
| D6 | MEDIUM | `accounting/models.py` (TransactionLine) | **Missing `created_by`/`updated_by` audit fields.** No user tracking on individual lines. |
| D7 | MEDIUM | Several models | **Decimal precision.** `max_digits=15, decimal_places=2` is adequate but should be verified for all financial fields for consistency. `OrderItem` uses `max_digits=10` which could overflow for large aggregates. |
| D8 | LOW | `accounting/models.py` (Transaction) | **Missing attachment support.** No `FileField` or `attachments` relation for supporting documents. |

---

### 🔴 Integration Issues (12 Issues)

| # | Severity | Modules | Issue |
|---|----------|---------|-------|
| I1 | CRITICAL | Inventory ↔ Accounting | **Zero integration.** No COGS tracking, no purchase accounting, no inventory valuation account. Stock transactions never create journal entries. |
| I2 | CRITICAL | Factory Accounting ↔ Accounting | **Isolated system.** Tailor/cutter payments (`FactoryCard`, `CardMeasurementSplit`) never create expense journal entries in the main accounting module. Factory labor costs invisible in financial statements. |
| I3 | CRITICAL | Installation Accounting ↔ Accounting | **Isolated system.** Technician payments (`InstallationCard`, `TechnicianShare`) never create expense entries. Installation labor costs invisible in financial statements. |
| I4 | CRITICAL | Installations ↔ Accounting | **`InstallationPayment` and `ReceiptMemo` models record cash collected at installations but never create journal entries.** Cash received on-site is invisible to the accounting system. |
| I5 | HIGH | Installations ↔ Accounting | **`CustomerDebt` in installations module duplicates** the debt tracking in `CustomerFinancialSummary`. Two parallel debt systems that can diverge. |
| I6 | HIGH | Orders ↔ Accounting | **General payments (payment_type='general') don't generate journal entries.** FIFO allocation creates `PaymentAllocation` records but no corresponding accounting entries. |
| I7 | HIGH | Orders ↔ Accounting | **Payment deletion doesn't reverse accounting entries.** No `post_delete` signal registered for Payment in accounting. |
| I8 | HIGH | Orders ↔ Accounting | **Order cancellation doesn't reverse accounting.** No signal to create reversing entry when order status changes to cancelled. |
| I9 | MEDIUM | Customers ↔ Accounting | **Customer model missing `credit_limit` and `payment_terms` fields.** Cannot enforce credit policies or calculate due dates. |
| I10 | MEDIUM | Inspections ↔ Accounting | **No inspection cost tracking.** Inspection has only `payment_status` flag — no monetary amount fields. Cannot track inspection-related revenue/costs. |
| I11 | MEDIUM | Manufacturing ↔ Accounting | **WIP (Work In Progress) accounting absent.** No tracking of raw materials consumed, WIP costs, or finished goods inventory at cost. |
| I12 | LOW | All modules | **Three parallel "accounting" systems** (`accounting/`, `factory_accounting/`, `installation_accounting/`) with no cross-posting mechanism. |

---

### 🔴 Accounting Logic Issues (9 Issues)

| # | Severity | Issue |
|---|----------|-------|
| A1 | CRITICAL | **Duplicate account names allowed.** No database or form-level validation prevents two accounts with the same name but different codes. |
| A2 | CRITICAL | **Financial reports don't filter by date range.** Trial balance, income statement, and balance sheet use stored `current_balance` which represents all-time balances. Period-based reporting is impossible. |
| A3 | CRITICAL | **Trial balance debit/credit logic is wrong.** Uses positive/negative balance sign instead of checking `account_type.normal_balance` and aggregating actual debit/credit movements. |
| A4 | HIGH | **No reversal entry mechanism.** No void/reversal creates a reversing journal entry — the system lacks a way to undo posted transactions properly. |
| A5 | HIGH | **Account balance recalculation iterates all transactions.** `get_balance()` aggregates all TransactionLines for the account every time — no period-based calculation. |
| A6 | HIGH | **Opening balance doesn't respect fiscal year.** `opening_balance` is a static field set once. No mechanism to close a fiscal year and carry forward balances. |
| A7 | MEDIUM | **No journal entry numbering per type.** All transactions use the same `TXN-YYYYMM-NNNNN` format regardless of type. Professional systems use separate sequences (e.g., JV-001, PV-001, RV-001). |
| A8 | MEDIUM | **No closing entries.** No mechanism to close revenue/expense accounts at period end and transfer to retained earnings. |
| A9 | LOW | **No multi-currency support.** All amounts assumed single currency. No exchange rate tracking or currency conversion. |

---

### 🔴 Security Issues (8 Issues)

| # | Severity | Issue |
|---|----------|-------|
| S1 | CRITICAL | **No custom permissions defined on any accounting model.** Views use `@permission_required("accounting.can_post_transaction")` and `@permission_required("accounting.can_void_transaction")` but these permissions are NEVER DEFINED in any model's Meta class. They don't exist in the database. |
| S2 | HIGH | **Most accounting views lack permission decorators.** Only `transaction_post` and `transaction_void` use `@permission_required`. All other views (dashboard, reports, account management, customer financials) only require `@login_required` — any logged-in user can access all financial data. |
| S3 | HIGH | **Role-based permissions not connected to Django's auth framework.** `ROLE_HIERARCHY` uses custom string permissions (`"view_all_orders"`) that have NO correspondence to `auth.Permission` objects. `@permission_required` decorators cannot enforce these. |
| S4 | HIGH | **Bank QR views (`bank_qr_view`, `all_banks_qr_view`) have NO authentication.** Anyone with the URL can view bank account details including account numbers, IBAN, SWIFT codes. |
| S5 | HIGH | **AuditLog not wired into accounting.** `core.audit.AuditLog` and `log_audit()` exist but are never called from any accounting view, signal, or model save. Financial transactions have no audit trail beyond `created_by`/`posted_by`. |
| S6 | MEDIUM | **Signal registration wrapped in bare try/except.** If signals fail to register, the system operates WITHOUT creating journal entries. Only print() notification — no logging/alerting. |
| S7 | MEDIUM | **`count_efficient()` uses f-string SQL.** `performance_utils.py` constructs raw SQL with f-string interpolation. While the input is from `_meta.db_table` (not user input), this is a fragile anti-pattern. |
| S8 | LOW | **`SecureSessionMiddleware` fully disabled.** Session rotation commented out — sessions live indefinitely without rotation. |

---

### 🔴 Missing Features (15 Features)

| # | Priority | Feature | Description |
|---|----------|---------|-------------|
| M1 | CRITICAL | **Supplier/Vendor Module** | No supplier management. `inventory.Supplier` model exists but has no accounting integration (no payables tracking). |
| M2 | CRITICAL | **Accounts Payable** | No AP tracking. Purchases, factory payments, installation payments have no payable ledger. |
| M3 | CRITICAL | **COGS (Cost of Goods Sold)** | No mechanism to record cost of goods when sales are made. |
| M4 | CRITICAL | **Fiscal Year Close** | No period closing, no retained earnings transfer, no opening balance rollover. |
| M5 | HIGH | **General Ledger Report** | No general ledger report exists. Only trial balance, income statement, and balance sheet (all with date-range issues). |
| M6 | HIGH | **Supplier Statement Report** | No supplier statement or AP aging report. |
| M7 | HIGH | **Aging Report (AR)** | No accounts receivable aging (30/60/90/120+ days). |
| M8 | HIGH | **Cash Flow Report** | No cash flow statement. |
| M9 | HIGH | **VAT/Tax Report** | No tax tracking or reporting capability. |
| M10 | HIGH | **Excel/PDF Export** | No data export on any financial page. |
| M11 | MEDIUM | **Journal Entry Edit** | No ability to edit draft journal entries. Only create, post, void. |
| M12 | MEDIUM | **Transaction Attachments** | No file upload for supporting documents. |
| M13 | MEDIUM | **Budget Module** | No budget planning, tracking, or variance analysis. |
| M14 | MEDIUM | **Multi-Currency** | No exchange rates, no currency conversion, no currency on transactions. |
| M15 | LOW | **Bank Reconciliation** | No bank reconciliation module. |

---
---

# OUTPUT B: FIX & DEVELOPMENT PLAN

---

## Phase 1: Critical Fixes (Must Be Done Immediately)

### 1.1 Fix Broken Runtime Errors

**Task 1.1.1:** Fix `transaction_create` view (accounting/views.py:405)
- Replace `transaction.reference_number` → `transaction.transaction_number`
- Replace `transaction.check_balance()` → `transaction.calculate_totals()`
- **File:** `accounting/views.py` lines 400-420

**Task 1.1.2:** Fix `advances_account` NameError (accounting/signals.py:230)
- Add code to look up or create the advances account before using it
- Either fetch from AccountingSettings or create a default_advances_account
- **File:** `accounting/signals.py` line 208-240

**Task 1.1.3:** Add missing permissions to Model Meta
- Add to `Transaction` Meta:
  ```python
  permissions = [
      ("can_post_transaction", "Can post journal entries"),
      ("can_void_transaction", "Can void journal entries"),
      ("can_view_financial_reports", "Can view financial reports"),
      ("can_manage_accounts", "Can manage chart of accounts"),
      ("can_register_payments", "Can register customer payments"),
  ]
  ```
- Create and run migration
- **File:** `accounting/models.py` (Transaction Meta class)

### 1.2 Fix Account Name Uniqueness

**Task 1.2.1:** Add unique constraint to Account.name
- Add `unique=True` to `name` field on `Account` model
- Or add `UniqueConstraint(fields=['name'], name='unique_account_name')` to Meta
- Run migration — first check for existing duplicates and resolve them
- **File:** `accounting/models.py` (Account model)

**Task 1.2.2:** Add form-level validation
- In `AccountForm.clean_name()`, check for existing accounts with same name
- **File:** `accounting/forms.py` (AccountForm)

### 1.3 Fix Parent Account Deletion Cascade

**Task 1.3.1:** Change `parent` FK from `CASCADE` to `PROTECT`
- **File:** `accounting/models.py` (Account.parent field)
- Run migration

### 1.4 Fix Silent Signal Failures

**Task 1.4.1:** Replace all `print()` with `logging.error()` in signals
- Add `import logging` and `logger = logging.getLogger('accounting')`
- Replace 12+ `print(f"Error...")` calls with `logger.error(..., exc_info=True)`
- **File:** `accounting/signals.py` (all error handlers)
- **File:** `accounting/apps.py` (ready method)

### 1.5 Secure Bank QR Endpoints

**Task 1.5.1:** Add `@login_required` to `bank_qr_view` and `all_banks_qr_view`
- Or create a separate public-facing URL if intentionally public, with rate limiting
- **File:** `accounting/views_bank.py`

---

## Phase 2: Accounting Completion

### 2.1 Chart of Accounts Fixes

**Task 2.1.1:** Add `currency` field to Account model
```python
currency = models.CharField(_("العملة"), max_length=3, default="EGP", blank=True)
```
- **File:** `accounting/models.py`

**Task 2.1.2:** Fix N+1 on `level` and `full_path` properties
- Add `level` as a stored field (IntegerField), updated on save
- Use `django-mptt` or `django-treebeard` for proper tree structure, OR
- Store `level` as an integer field calculated on save
- **File:** `accounting/models.py`

**Task 2.1.3:** Add proper parent-child validation
- Prevent account from being its own parent
- Prevent circular parent references
- Validate that parent's account_type matches or is compatible
- **File:** `accounting/models.py` (Account.clean method)

### 2.2 Journal Entry Improvements

**Task 2.2.1:** Fix Transaction.post() method
```python
def post(self, user=None):
    self.calculate_totals()  # Ensure totals are current
    if not self.is_balanced:
        raise ValueError("القيد غير متوازن")
    if self.status == "posted":
        raise ValueError("القيد مرحّل مسبقاً")
    with transaction.atomic():
        self.status = "posted"
        self.posted_by = user
        self.posted_at = timezone.now()
        self.save(update_fields=["status", "posted_by", "posted_at", "total_debit", "total_credit"])
        for line in self.lines.select_related('account'):
            line.account.update_balance()
```
- **File:** `accounting/models.py`

**Task 2.2.2:** Add reversal mechanism
```python
def create_reversal(self, user=None, reason=""):
    """Create a reversing journal entry"""
    # Creates a new transaction with debit/credit swapped
```
- **File:** `accounting/models.py`

**Task 2.2.3:** Add `approved_by` field to Transaction
- **File:** `accounting/models.py`

**Task 2.2.4:** Add attachment support
```python
class TransactionAttachment(models.Model):
    transaction = models.ForeignKey(Transaction, related_name='attachments')
    file = models.FileField(upload_to='transaction_attachments/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL)
    uploaded_at = models.DateTimeField(auto_now_add=True)
```
- **File:** `accounting/models.py`

### 2.3 Fix Financial Reports

**Task 2.3.1:** Rewrite trial balance to use actual debit/credit aggregates
- Query `TransactionLine` grouped by account, filtered by date range
- Compute debit/credit totals from actual posted transactions
- **File:** `accounting/views.py` (trial_balance view)

**Task 2.3.2:** Rewrite income statement with date range support
- Query `TransactionLine` for revenue/expense accounts within date range
- **File:** `accounting/views.py` (income_statement view)

**Task 2.3.3:** Rewrite balance sheet with date range support
- **File:** `accounting/views.py` (balance_sheet view)

**Task 2.3.4:** Add General Ledger report
- Show all transactions for all accounts within date range
- Group by account, show running balance
- **File:** `accounting/views.py` (new view), `accounting/urls.py`

**Task 2.3.5:** Add Aging Report
- 30/60/90/120+ day buckets based on order date vs today
- **File:** `accounting/views.py` (new view)

### 2.4 Posting Rules Enforcement

**Task 2.4.1:** Add pre-post validation
- Check that no line has both debit and credit > 0
- Check that all accounts are active
- Check that all accounts allow transactions
- **File:** `accounting/models.py` (Transaction.post method)

---

## Phase 3: Full Integration with Modules

### 3.1 Orders Integration (Fix Existing)

**Task 3.1.1:** Fix general payment journal entry creation
- In `create_payment_transaction()`, handle `payment.order is None` case
- Debit Cash, Credit Customer Account (lookup by payment.customer)
- **File:** `accounting/signals.py`

**Task 3.1.2:** Add Payment deletion reversal signal
```python
@receiver(post_delete, sender='orders.Payment')
def payment_deleted(sender, instance, **kwargs):
    # Find and reverse the corresponding journal entry
```
- **File:** `accounting/signals.py`

**Task 3.1.3:** Add Order cancellation reversal signal
- Listen for Order status change to 'cancelled'
- Create reversing journal entry
- **File:** `accounting/signals.py`

**Task 3.1.4:** Fix dual paid_amount update race condition
- Remove manual `paid_amount += amount` from `OrderService.add_payment()`
- Rely solely on the signal's aggregate calculation
- **File:** `orders/services.py`

### 3.2 Customers Integration

**Task 3.2.1:** Add financial fields to Customer model
```python
credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0, blank=True)
payment_terms_days = models.IntegerField(default=0, help_text="Net payment terms in days")
```
- **File:** `customers/models.py`

**Task 3.2.2:** Add credit check service
- Before order confirmation, check if customer would exceed credit limit
- **File:** `customers/services.py`

### 3.3 Installations Integration (New)

**Task 3.3.1:** Create accounting signals for InstallationPayment
- When `InstallationPayment` is created:
  - Debit Cash/Bank
  - Credit Customer Account or Revenue
- **File:** `accounting/signals.py`

**Task 3.3.2:** Create accounting signals for ReceiptMemo
- Record cash collection at installation site
- **File:** `accounting/signals.py`

### 3.4 Inspections Integration (New)

**Task 3.4.1:** Add `inspection_cost` field to Inspection model
- **File:** `inspections/models.py`

**Task 3.4.2:** Create journal entries for inspection costs
- **File:** `accounting/signals.py`

### 3.5 Factory Accounting Integration (New)

**Task 3.5.1:** Create bridge signals for FactoryCard payment
- When `FactoryCard.status` changes to `paid`:
  - Debit Manufacturing Expense
  - Credit Cash/Payable
- **File:** `accounting/signals.py` or `factory_accounting/signals.py`

### 3.6 Inventory Integration (New)

**Task 3.6.1:** Create journal entries for PurchaseOrder receipt
- Debit Inventory Asset
- Credit Accounts Payable
- **File:** `accounting/signals.py` or new `inventory/accounting_integration.py`

**Task 3.6.2:** Create COGS entries on sale
- When StockTransaction type=out, reason=sale:
  - Debit COGS
  - Credit Inventory Asset
- **File:** New signal bridging inventory and accounting

**Task 3.6.3:** Add accounting system accounts
- Create system accounts for: Inventory, COGS, Accounts Payable, WIP
- **File:** `accounting/management/commands/setup_accounting_structure.py`

---

## Phase 4: Reports & Export

### 4.1 Report Implementations

| Report | View Function | Template | Query Strategy |
|--------|--------------|----------|----------------|
| General Ledger | `general_ledger()` | `reports/general_ledger.html` | TransactionLine grouped by account, filtered by date |
| Aging Report | `aging_report()` | `reports/aging_report.html` | Orders grouped by age bucket (30/60/90/120+) |
| Cash Flow | `cash_flow()` | `reports/cash_flow.html` | Transactions grouped by type (operating/investing/financing) |
| Supplier Statement | `supplier_statement()` | `reports/supplier_statement.html` | TransactionLine for AP accounts |
| VAT Report | `vat_report()` | `reports/vat_report.html` | Revenue/expense with tax breakdown |

### 4.2 Export Implementation

**Task 4.2.1:** Create export utility
```python
# accounting/export_utils.py
def export_to_excel(queryset, columns, filename)
def export_to_pdf(context, template_name, filename)
```

**Task 4.2.2:** Add export endpoints for each report
- `/accounting/reports/trial-balance/export/excel/`
- `/accounting/reports/trial-balance/export/pdf/`
- (Same pattern for all reports)
- **Files:** `accounting/views.py`, `accounting/urls.py`

**Task 4.2.3:** Add print-friendly layouts
- Ensure all report templates have proper `@media print` CSS
- **Files:** All report templates

### 4.3 Performance Optimizations for Reports

- Use `.values()` and `.annotate()` instead of Python loops for aggregation
- Add date-based composite indexes on `TransactionLine` (transaction__date, account)
- Consider materialized views for frequently-accessed reports (trial balance)

---

## Phase 5: UI/UX Upgrade

### 5.1 Template Refactoring

**Task 5.1.1:** Fix reports index page
- Add cards/links to all reports (trial balance, income statement, balance sheet, customer balances, aging, general ledger, daily)
- **File:** `templates/accounting/reports/index.html`

**Task 5.1.2:** Fix transaction form errors display
- Add `{{ form.non_field_errors }}`, `{{ form.errors }}`, `{{ formset.non_form_errors }}`
- Implement "Add line" JavaScript handler for dynamic formset rows
- **File:** `templates/accounting/transaction_form.html`

**Task 5.1.3:** Add pagination to all list views
- account_statement, customer_payments, customer_financial orders table, customer_account_statement, daily_transactions
- **Files:** All affected templates + views

**Task 5.1.4:** Fix number formatting consistency
- Add `{% load accounting_numbers %}` to all 13 templates that are missing it
- Apply `|en` filter to all number displays
- **Files:** 13 templates listed in T8

### 5.2 Dashboard Integration

**Task 5.2.1:** Add report quick links to dashboard
- Trial balance, income statement, balance sheet, aging report
- **File:** `templates/accounting/dashboard.html`

### 5.3 Filters

**Task 5.3.1:** Add date range filter to financial reports
- Wire up DateRangeFilterForm properly in trial balance, income statement, balance sheet
- **Files:** views.py + report templates

### 5.4 Permissions-Based UI

**Task 5.4.1:** Add template permission checks
```html
{% if perms.accounting.can_post_transaction %}
    <button>Post</button>
{% endif %}
{% if perms.accounting.can_manage_accounts %}
    <a href="{% url 'admin:...' %}">Edit</a>
{% endif %}
```
- **Files:** All 20 templates

### 5.5 RTL Fixes

**Task 5.5.1:** Fix customer_account_statement RTL properties
- Replace `border-left` → `border-inline-start`
- Replace `margin-left` → `margin-inline-start`
- **File:** `templates/accounting/customer_account_statement.html`

**Task 5.5.2:** Fix hardcoded currency
- Replace `ج.م` → `{{ currency_symbol }}`
- **File:** `templates/accounting/customer_account_statement.html`

---

## Phase 6: Testing & Verification

### 6.1 Unit Tests

**File:** `accounting/tests/test_models.py`
```python
class AccountModelTests(TestCase):
    def test_unique_account_name_enforced(self)
    def test_unique_account_code_enforced(self)
    def test_parent_child_hierarchy(self)
    def test_level_calculation(self)
    def test_balance_calculation(self)
    def test_cannot_delete_parent_with_children(self)

class TransactionModelTests(TestCase):
    def test_balanced_transaction_posts(self)
    def test_unbalanced_transaction_rejected(self)
    def test_no_negative_debit_credit(self)
    def test_no_both_debit_and_credit_on_line(self)
    def test_posting_updates_account_balances(self)
    def test_reversal_creates_opposite_entry(self)
    def test_void_prevents_double_void(self)
    def test_transaction_number_generation(self)
```

### 6.2 Integration Tests

**File:** `accounting/tests/test_integration.py`
```python
class OrderAccountingTests(TestCase):
    def test_order_creates_journal_entry(self)
    def test_payment_creates_journal_entry(self)
    def test_general_payment_creates_journal_entry(self)
    def test_payment_deletion_reverses_entry(self)
    def test_order_cancellation_reverses_entry(self)
    def test_customer_creation_creates_account(self)

class ReportTests(TestCase):
    def test_trial_balance_is_balanced(self)
    def test_income_statement_date_range(self)
    def test_balance_sheet_assets_eq_liabilities_plus_equity(self)
```

### 6.3 Sample Data Script

**File:** `accounting/management/commands/create_sample_data.py`
- Create account types, chart of accounts, sample transactions
- Create test orders with payments
- Verify trial balance balances

---
---

# OUTPUT C: PROFESSIONAL FILE-BY-FILE TODO LIST

---

## File: `accounting/models.py`

- [ ] **Add unique constraint on Account.name** — Add `unique=True` or `UniqueConstraint` in Meta
- [ ] **Change Account.parent on_delete from CASCADE to PROTECT** — Prevent cascade deletion of children
- [ ] **Add Account.currency field** — `CharField(max_length=3, default="EGP")`
- [ ] **Add Account.level stored field** — `IntegerField` computed on save, replacing the property
- [ ] **Add Account.clean() validation** — Prevent circular parent references, self-parent
- [ ] **Add TransactionLine.currency field** — For multi-currency support
- [ ] **Add Transaction.approved_by field** — FK to User, nullable
- [ ] **Add Transaction.calculate_totals() call in post()** — Before checking is_balanced
- [ ] **Add reversal method to Transaction** — `create_reversal(user, reason)` method
- [ ] **Add custom permissions in Transaction Meta** — can_post, can_void, can_view_reports, can_manage_accounts, can_register_payments
- [ ] **Add TransactionAttachment model** — File upload for supporting documents
- [ ] **Replace print() with logging** in save methods
- [ ] **Add `__str__` improvements** for better admin display

## File: `accounting/views.py`

- [ ] **Fix transaction_create** — Replace `transaction.reference_number` and `transaction.check_balance()` with correct methods
- [ ] **Fix trial_balance** — Rewrite to use TransactionLine aggregates with date range filter
- [ ] **Fix income_statement** — Query TransactionLine within date range, not current_balance
- [ ] **Fix balance_sheet** — Same as income_statement fix
- [ ] **Add @permission_required to all sensitive views** — dashboard, account_list, reports, customer_financial
- [ ] **Add general_ledger view** — New report view
- [ ] **Add aging_report view** — AR aging 30/60/90/120+
- [ ] **Add cash_flow view** — Cash flow statement
- [ ] **Add export_trial_balance_excel view** — Excel export
- [ ] **Add export_trial_balance_pdf view** — PDF export
- [ ] **Fix bare except clauses** — Replace `except:` with specific exception types
- [ ] **Add pagination** to account_statement, customer_payments
- [ ] **Fix reports_index view** — Should render actual reports page, not redirect
- [ ] **Add atomic transactions** to all write operations

## File: `accounting/forms.py`

- [ ] **Add clean_name() to AccountForm** — Validate unique account name
- [ ] **Add parent hierarchy validation** — Prevent self-parent and circular references
- [ ] **Add TransactionForm.clean()** — Validate total debit == total credit in formset

## File: `accounting/signals.py`

- [ ] **Fix advances_account NameError** — Add account lookup at line 230
- [ ] **Add general payment journal entry** — Handle payment.order=None case
- [ ] **Add Payment post_delete signal** — Reverse journal entry on payment deletion
- [ ] **Add Order cancellation signal** — Create reversing entry on order cancellation
- [ ] **Replace all print() with logging.error()** — 12+ instances
- [ ] **Add Installation payment signal** — Create entries for `InstallationPayment`
- [ ] **Add ReceiptMemo signal** — Create entries for cash collected at installations
- [ ] **Add FactoryCard payment signal** — Create expense entries for factory payments

## File: `accounting/admin.py`

- [ ] **Add duplicate name check** in Account admin
- [ ] **Add balance audit action** — Admin action to recalculate all account balances
- [ ] **Add export action** — Export accounts to CSV/Excel

## File: `accounting/urls.py`

- [ ] **Add general_ledger URL** — `reports/general-ledger/`
- [ ] **Add aging_report URL** — `reports/aging/`
- [ ] **Add cash_flow URL** — `reports/cash-flow/`
- [ ] **Add export URLs** — For each report (excel/pdf)

## File: `accounting/views_bank.py`

- [ ] **Add @login_required** to `bank_qr_view` and `all_banks_qr_view` (or explicit public policy)

## File: `accounting/views_statement.py`

- [ ] **Add pagination** to customer_account_statement
- [ ] **Add date range validation**

## File: `accounting/apps.py`

- [ ] **Replace print() with logging** in ready() error handler
- [ ] **Add proper error alerting** for failed signal registration

## File: `accounting/performance_utils.py`

- [ ] **Fix f-string SQL in count_efficient()** — Use parameterized query
- [ ] **Fix bare except: pass** in invalidate_cache — At minimum log the error

## File: `templates/accounting/transaction_form.html`

- [ ] **Add form error display** — `{{ form.non_field_errors }}`, `{{ form.errors }}`
- [ ] **Implement "Add line" JS handler** — Dynamic formset row addition
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/reports/index.html`

- [ ] **Add links to all reports** — Trial balance, income statement, balance sheet, customer balances, aging, general ledger, daily
- [ ] **Add report descriptions**

## File: `templates/accounting/reports/trial_balance.html`

- [ ] **Wire date range filter** to view
- [ ] **Add Excel/PDF export buttons**
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/reports/income_statement.html`

- [ ] **Wire date range filter** to view
- [ ] **Add Excel/PDF export buttons**
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/reports/balance_sheet.html`

- [ ] **Add date range filter**
- [ ] **Add Excel/PDF export buttons**
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/reports/customer_balances.html`

- [ ] **Add Excel export button**

## File: `templates/accounting/reports/daily_transactions.html`

- [ ] **Fix broken badge CSS** — Replace `bg-{{ transaction.status }}` with conditional classes
- [ ] **Add pagination**
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/account_list.html`

- [ ] **Add Excel export button**
- [ ] **Add permission checks on admin links**

## File: `templates/accounting/account_detail.html`

- [ ] **Add null guard on account_type**
- [ ] **Add permission checks on admin links**
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/account_tree.html`

- [ ] **Support deeper tree levels** (recursive template include)
- [ ] **Add search/filter**
- [ ] **Add permission checks on admin links**
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/account_statement.html`

- [ ] **Add pagination**
- [ ] **Add Excel export**
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/transaction_list.html`

- [ ] **Add export buttons**
- [ ] **Add permission checks** on post/void links
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/transaction_detail.html`

- [ ] **Add confirmation dialog** for Post action
- [ ] **Add permission checks** for Post/Void buttons
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/customer_financial.html`

- [ ] **Add permission check** on register payment button
- [ ] **Add order pagination**
- [ ] **Add Excel export**
- [ ] **Add form error display** in payment modal

## File: `templates/accounting/customer_account_statement.html`

- [ ] **Fix RTL CSS** — Replace border-left, margin-left, padding-left
- [ ] **Fix hardcoded currency** — Replace `ج.م` with `{{ currency_symbol }}`
- [ ] **Add pagination**
- [ ] **Add Excel export**

## File: `templates/accounting/customer_payments.html`

- [ ] **Add pagination**
- [ ] **Add print/export buttons**
- [ ] **Load accounting_numbers templatetag**

## File: `templates/accounting/transaction_print.html`

- [ ] **Load accounting_numbers templatetag**

## File: `customers/models.py`

- [ ] **Add credit_limit field** — DecimalField(max_digits=15, decimal_places=2, default=0)
- [ ] **Add payment_terms_days field** — IntegerField(default=0)
- [ ] **Remove reference to non-existent tax_number/national_id** in save() Arabic conversion

## File: `customers/services.py`

- [ ] **Add check_credit_limit() method** — Validate before order creation
- [ ] **Add get_customer_statement() method** — Retrieve full statement data

## File: `orders/services.py`

- [ ] **Remove manual paid_amount increment** — Rely on signal aggregate

## File: `inspections/models.py`

- [ ] **Add inspection_cost field** — DecimalField for inspection fee

## File: `factory_accounting/signals.py`

- [ ] **Add bridge to main accounting** — Create expense journal entry on FactoryCard payment

## File: `installation_accounting/signals.py`

- [ ] **Add bridge to main accounting** — Create expense journal entry on InstallationCard payment

## File: `accounting/tests/` (New Directory)

- [ ] **Create test_models.py** — Account, Transaction, TransactionLine tests
- [ ] **Create test_views.py** — View response and permission tests
- [ ] **Create test_signals.py** — Signal integration tests
- [ ] **Create test_reports.py** — Report accuracy tests

## File: `accounting/export_utils.py` (New)

- [ ] **Create export_to_excel()** — Generic queryset to Excel
- [ ] **Create export_to_pdf()** — Generic context to PDF

---
---

# OUTPUT D: FINAL RECOMMENDATIONS

---

## Best Practices

1. **Double-Entry Integrity:** Every financial event MUST create a balanced journal entry (debit = credit). Currently, several event types (general payments, installations, factory payments) bypass this. This is the #1 priority to fix.

2. **Immutability of Posted Entries:** Posted journal entries should NEVER be edited. The only way to correct them is through reversing entries. The system partially implements this but needs strengthening.

3. **Period-Based Reporting:** Financial reports MUST support date ranges. The current implementation showing all-time balances is not acceptable for any accounting system. Reports must query from transactions within the specified period.

4. **Audit Trail:** Every financial action must be traceable. Wire `core.audit.AuditLog` into all accounting model saves, posts, and voids.

5. **Separation of Concerns:** The `CustomerFinancialSummary.refresh()` method iterates orders in Python because `final_price_after_discount` is a property. Consider denormalizing this to a stored field updated via signals.

## ERP Accounting Compliance

1. **Chart of Accounts Standard:** The current chart structure follows a reasonable hierarchical pattern (1xxx=Assets, 2xxx=Liabilities, etc.). Enforce this strictly and prevent account creation outside the defined hierarchy.

2. **Fiscal Year Management:** Add fiscal year open/close functionality. At year-end: close revenue/expense accounts → transfer to Retained Earnings → create opening entries for the new year.

3. **Trial Balance Must Balance:** The trial balance view has a logic bug (using balance sign instead of account type). This MUST be fixed — an unbalanced trial balance indicates corruption.

4. **Subsidiary Ledgers:** Customer accounts (under 1121) function as a subsidiary ledger of Accounts Receivable. The sum of all customer account balances should equal the AR control account balance. Add a reconciliation check.

## Recommended Improvements

1. **Adopt django-mptt or django-treebeard** for the chart of accounts tree. The current manual parent traversal causes N+1 queries and limits tree operations.

2. **Add a Reconciliation Module:** Bank reconciliation between BankAccount records and actual bank statements.

3. **Add Budget vs. Actual:** Allow setting budget amounts per account per period and report variance.

4. **Implement Proper Error Handling:** Replace all `print()` error handling with structured logging. Add Sentry or similar for error alerting.

5. **Add Database-Level Constraints:** Add PostgreSQL CHECK constraints for debit/credit non-negativity and balanced transactions (trigger-based).

## Optional Enhancements

1. **Multi-Currency:** Add currency fields to Account, Transaction, TransactionLine. Add exchange rate table. Show both local and foreign currency amounts.

2. **Automated Bank Feeds:** Import bank transaction files (OFX/CSV) and auto-match with accounting entries.

3. **Workflow Engine:** Add approval workflows for large transactions (e.g., transactions over a threshold require manager approval).

4. **Dashboard Charts:** Add Chart.js visualizations for revenue trend, expense breakdown, cash flow trend, receivables aging donut chart.

5. **API Layer:** Add DRF serializers for all accounting endpoints to support mobile app and third-party integrations.

---
---

# OUTPUT E: تقرير ملخص بالعربية

---

## التقرير العربي الشامل لتدقيق النظام المحاسبي

### ١. الحالة الراهنة

النظام المحاسبي الحالي يحتوي على هيكل أساسي جيد يشمل:
- شجرة حسابات (دليل حسابات) مع هيكل شجري
- نظام قيود محاسبية (قيد يومية) مع بنود مدين/دائن
- ملخصات مالية للعملاء
- لوحة تحكم محاسبية
- تقارير أساسية (ميزان مراجعة، قائمة دخل، ميزانية عمومية)
- حسابات بنكية مع نظام QR

### ٢. المشاكل الحرجة المكتشفة

#### أ. مشاكل محاسبية جوهرية
1. **أسماء الحسابات المكررة مسموح بها** — لا يوجد قيد فريد على اسم الحساب. هذا يعد خطأ محاسبياً جسيماً.
2. **التقارير المالية لا تدعم النطاق الزمني** — ميزان المراجعة وقائمة الدخل والميزانية تعرض أرصدة كلية بدون فلترة بالتاريخ.
3. **منطق ميزان المراجعة خاطئ** — يستخدم إشارة الرصيد بدلاً من نوع الحساب لتحديد المدين والدائن.
4. **لا يوجد آلية عكس القيود** — لا توجد طريقة لإلغاء قيد مرحّل بشكل صحيح.

#### ب. مشاكل في التكامل مع الوحدات الأخرى
1. **المخزون منفصل تماماً عن المحاسبة** — لا يوجد تتبع لتكلفة البضاعة المباعة أو محاسبة المشتريات.
2. **محاسبة المصنع منعزلة** — دفعات الخياطين والقصاصين لا تظهر في النظام المحاسبي الرئيسي.
3. **محاسبة التركيبات منعزلة** — دفعات الفنيين لا تُسجل كمصروفات في النظام المحاسبي.
4. **المدفوعات العامة لا تُنشئ قيوداً محاسبية** — الدفعات بدون ربط بطلب محدد لا تُسجل في دفتر اليومية.

#### ج. أخطاء برمجية حرجة
1. **متغير غير معرّف في إنشاء قيد العربون** (`advances_account`) — سيتسبب في خطأ وقت التشغيل.
2. **طريقة عرض إنشاء القيد تستدعي دوال غير موجودة** — `check_balance()` و `reference_number` غير معرّفة على نموذج القيد.
3. **الصلاحيات المستخدمة في الـ views غير معرّفة في قاعدة البيانات** — `can_post_transaction` و `can_void_transaction` ليست مسجلة في أي نموذج.

### ٣. المخاطر

| المخاطرة | مستوى الخطورة | التأثير |
|----------|--------------|---------|
| بيانات مالية غير دقيقة بسبب عدم تسجيل قيود لبعض العمليات | حرج | قرارات مالية خاطئة |
| أخطاء برمجية في إنشاء القيود | حرج | فقدان بيانات مالية |
| عدم وجود ربط المخزون بالمحاسبة | حرج | عدم حساب تكلفة البضاعة المباعة |
| تقارير مالية غير دقيقة | عالي | تقارير مضللة للإدارة |
| عدم وجود صلاحيات حقيقية | عالي | أي مستخدم يمكنه الوصول للبيانات المالية |
| ثلاث أنظمة محاسبية منفصلة | عالي | عدم اتساق البيانات المالية |

### ٤. ملخص خطة الإصلاح

#### المرحلة الأولى: الإصلاحات الحرجة (فورية)
- إصلاح الأخطاء البرمجية التي تمنع النظام من العمل
- إضافة قيد فريد لأسماء الحسابات
- تعريف الصلاحيات المطلوبة
- إصلاح إنشاء قيود الدفعات العامة والعربونات
- تأمين صفحات الحسابات البنكية

#### المرحلة الثانية: اكتمال النظام المحاسبي
- إصلاح التقارير المالية لدعم النطاق الزمني
- إضافة آلية عكس القيود
- إضافة تقرير دفتر الأستاذ العام
- إضافة تقرير أعمار الديون

#### المرحلة الثالثة: تكامل كامل مع جميع الوحدات
- ربط المخزون بالمحاسبة (تكلفة بضاعة مباعة + مشتريات)
- ربط محاسبة المصنع بالنظام الرئيسي
- ربط محاسبة التركيبات بالنظام الرئيسي
- ربط دفعات التركيبات والمعاينات بالمحاسبة

#### المرحلة الرابعة: التقارير والتصدير
- إضافة تقارير جديدة (دفتر أستاذ، أعمار ديون، تدفقات نقدية)
- إضافة تصدير Excel/PDF لجميع التقارير
- تحسين أداء الاستعلامات

#### المرحلة الخامسة: تحسين واجهة المستخدم
- إصلاح نموذج إنشاء القيد (عرض الأخطاء + إضافة سطور ديناميكية)
- إضافة صلاحيات على مستوى القوالب
- إصلاح مشاكل RTL والعملة المشفرة
- توحيد تنسيق الأرقام في جميع الصفحات
- إضافة ترقيم الصفحات للقوائم الطويلة

#### المرحلة السادسة: الاختبار والتحقق
- كتابة اختبارات وحدة لجميع النماذج المحاسبية
- اختبارات تكامل للتأكد من صحة القيود الآلية
- اختبار التقارير المالية (ميزان المراجعة متوازن، الميزانية متوازنة)

### ٥. ما سيتم إصلاحه
- جميع الأخطاء البرمجية الحرجة
- منطق التقارير المالية
- تكامل الدفعات والقيود
- أمن وصلاحيات النظام المحاسبي
- واجهة المستخدم والتصدير

### ٦. ما سيتم إضافته
- تقارير مالية جديدة (دفتر أستاذ، أعمار ديون، تدفقات نقدية)
- تصدير Excel/PDF
- ربط المخزون والمصنع والتركيبات بالمحاسبة
- حد ائتمان وشروط دفع للعملاء
- مرفقات للقيود المحاسبية
- آلية عكس القيود
- تدقيق كامل (Audit Trail)

### ٧. كيف سيصبح النظام احترافياً
بعد تنفيذ الخطة، سيكون النظام المحاسبي:
- ✅ **صحيح محاسبياً** — قيد مزدوج كامل لجميع العمليات
- ✅ **متكامل مع جميع الوحدات** — الطلبات، العملاء، التركيبات، المعاينات، المصنع، المخزون
- ✅ **آمن ومحمي بالصلاحيات** — كل صفحة مالية محمية بصلاحيات محددة
- ✅ **يحتوي على تقارير كاملة** — ميزان مراجعة، قائمة دخل، ميزانية، دفتر أستاذ، أعمار ديون
- ✅ **بدون أسماء حسابات مكررة** — قيود فريدة مطبقة على مستوى قاعدة البيانات
- ✅ **بدون قوالب معطلة** — جميع الصفحات تعمل بشكل صحيح
- ✅ **واجهة مستخدم متسقة** — تنسيق موحد، RTL صحيح، ترقيم صفحات
- ✅ **قابل للتوسع وجاهز للإنتاج** — مفهرس، محسّن الأداء، مع تخزين مؤقت

---

**نهاية التقرير**

*تم إعداده بواسطة: مهندس نظم ERP مالية رئيسي*  
*التاريخ: ١٠ فبراير ٢٠٢٦*
