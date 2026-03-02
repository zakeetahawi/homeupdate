# Django Views Comprehensive Audit Report

**Date**: 2026-02-12  
**Scope**: All view files across 15+ Django apps (~37,700 lines across 52 files)  
**Auditor**: Automated code audit

---

## Executive Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Missing Authentication | 2 | 8 | 3 | 0 | 13 |
| N+1 Query Issues | 5 | 12 | 8 | 0 | 25 |
| CSRF Bypass (@csrf_exempt) | 3 | 6 | 0 | 0 | 9 |
| Bare `except:` Clauses | 0 | 0 | 30+ | 0 | 30+ |
| DB Queries in Loops | 3 | 10 | 15 | 0 | 28 |
| Missing Pagination | 0 | 3 | 5 | 0 | 8 |
| Python-side Aggregation | 2 | 5 | 3 | 0 | 10 |
| In-Memory List Building | 1 | 3 | 2 | 0 | 6 |
| Unoptimized `.objects.all()` | 0 | 2 | 8 | 5 | 15 |
| **Total** | **16** | **49** | **74** | **5** | **144+** |

---

## 1. CRITICAL Issues

### 1.1 Missing Authentication on API Endpoints

#### installations/views.py — `api_upcoming_installations` (Line 3796)
- **Severity**: CRITICAL  
- **Issue**: `@csrf_exempt` used on an API endpoint that returns customer financial data (debt amounts, paid amounts, addresses, phone numbers) WITHOUT `@login_required`. Any unauthenticated user can access sensitive customer financial information.
- **Impact**: Complete data exposure of customer financial records.
- **Fix**: Add `@login_required` decorator and remove `@csrf_exempt` or use DRF with proper authentication.

#### accounts/api_views.py — Multiple endpoints (Lines 30-100)
- **Severity**: CRITICAL  
- **Issue**: `current_user`, `user_info`, `login_api`, `role_list_api` — the first three endpoints (`current_user`, `user_info`) lack `@login_required`. While `login_api` may intentionally be unauthenticated, `current_user` and `user_info` expose user data.
- **Fix**: Add `@login_required` to `current_user` and `user_info`.

#### accounts/api_views.py — `check_device_api` (Line 357-358)
- **Severity**: CRITICAL  
- **Issue**: `@csrf_exempt` decorator on device checking endpoint with no `@login_required`. Allows unauthenticated fingerprinting/enumeration of registered devices.
- **Fix**: Add authentication or rate limiting.

### 1.2 N+1 Query — Full Table Scan in Python

#### manufacturing/views.py — `ManufacturingItemStatusReportView` (~Lines 430-470)
- **Severity**: CRITICAL  
- **Issue**: Iterates ALL manufacturing orders in Python calling `.total_items_count` and `.received_items_count` properties on each, which trigger individual DB queries per order. With thousands of orders, this causes thousands of queries.
- **Fix**: Use `annotate(Count(...))` to compute counts at the database level.

#### inventory/views_stock_analysis.py — Lines 134, 251
- **Severity**: CRITICAL  
- **Issue**: `for product in Product.objects.all():` — iterates ALL products to compute stock analysis in Python. No pagination, no `.only()`, no DB-level aggregation.
- **Fix**: Use database aggregation with `annotate()` and `aggregate()`.

### 1.3 @csrf_exempt on State-Modifying POST Endpoints

#### installations/views.py — `receive_completed_order` (Line 1346)
- **Severity**: CRITICAL  
- **Issue**: `@csrf_exempt` on a POST endpoint that modifies installation/manufacturing order status and creates records. Allows CSRF attacks to modify order states.

---

## 2. HIGH Severity Issues

### 2.1 Missing Authentication Decorators

| File | Function/Class | Line | Issue |
|------|---------------|------|-------|
| manufacturing/views.py | `get_production_lines_api` | ~1460 | No `@login_required` — exposes production line data |
| manufacturing/views.py | `dashboard_data` | ~2630 | No `@login_required` — exposes dashboard statistics |
| manufacturing/views.py | `print_manufacturing_order` | ~2550 | No `@login_required` — prints order details |
| manufacturing/views.py | `create_from_order` | ~2310 | No `@login_required` — creates manufacturing orders |
| manufacturing/views.py | `receive_all_fabric_items` | ~3790 | No `@login_required` — receives fabric items |
| manufacturing/views.py | `recent_fabric_receipts` | ~3820 | No `@login_required` — lists fabric receipts |
| manufacturing/views.py | `ProductReceiptsListView` | ~3890 | Missing `LoginRequiredMixin` — lists product receipts |
| manufacturing/views.py | `update_approval_status` | ~2740 | Manual `if not request.user.is_authenticated` check only |

### 2.2 N+1 Queries in Loops

#### manufacturing/views.py — `ManufacturingOrderDetailView.get_context_data` (~Line 310)
- **Severity**: HIGH  
- **Issue**: Loops through `order_items` calling `cutting_items.all()` per item without prefetch. Each iteration triggers a separate DB query.
- **Fix**: Add `Prefetch('items__cutting_items')` to the queryset.

#### manufacturing/views.py — `PendingItemsReportView.get_all_pending_items` (~Line 500)
- **Severity**: HIGH  
- **Issue**: Calls `ManufacturingOrderItem.objects.filter(has_delivered)` inside a loop for each manufacturing order. Creates N+1 queries.
- **Fix**: Use a single aggregated query with `annotate()`.

#### manufacturing/views.py — `FabricReceiptView.get_pending_items_stats` (~Line 550)
- **Severity**: HIGH  
- **Issue**: Same N+1 pattern as PendingItemsReportView — queries per-item inside a loop.

#### manufacturing/views.py — `export_manufacturing_orders` (~Line 4700)
- **Severity**: HIGH  
- **Issue**: Iterates all orders computing meters in a Python loop. Each order triggers queries for items. No `.only()` or `.defer()`.

#### orders/views.py — `invoice_print` (Lines 1655+)
- **Severity**: HIGH  
- **Issue**: `for item in order.items.all():` inside the invoice rendering — items not prefetched, triggers separate queries per item with `item.product.name`.
- **Fix**: Use `order.items.select_related('product').all()`.

#### cutting/views.py — `CuttingDashboardView.get_user_warehouses_with_stats` (Lines 97-130)
- **Severity**: HIGH  
- **Issue**: Loops through warehouses executing 3 separate `.count()` queries per warehouse (total, pending, completed). With 10 warehouses = 30 queries.
- **Fix**: Use a single query with `annotate(Count('id', filter=Q(status=...)))`.

#### accounts/views.py — `role_update` (Lines 1590-1597)
- **Severity**: HIGH  
- **Issue**: When updating a role, iterates ALL users with that role, then iterates ALL their roles, then iterates ALL permissions. Triple-nested loop creating N×M×P queries.
- **Fix**: Use `user.user_permissions.set(...)` with a single aggregated permissions query.

#### accounts/api_views.py — `role_detail_api` (Lines 179-186)
- **Severity**: HIGH  
- **Issue**: Same triple-nested loop pattern as `role_update` above.

#### reports/views_ranking.py — Line 74
- **Severity**: HIGH  
- **Issue**: `for share in card.shares.all():` — iterates shares without prefetch, N+1 per card.

#### accounting/views_statement.py — Line 62
- **Severity**: HIGH  
- **Issue**: `for line in txn.lines.all():` — iterates transaction lines without prefetch, N+1 per transaction.

### 2.3 Python-side Aggregation Instead of SQL

#### manufacturing/views.py — `DashboardView.get_context_data` (~Line 2630)
- **Severity**: HIGH  
- **Issue**: Computes `total_revenue` by iterating orders in a Python loop instead of using `aggregate(Sum('total_amount'))`.

#### manufacturing/views.py — `VIPOrdersListView.get_context_data` (~Line 1100)
- **Severity**: HIGH  
- **Issue**: Multiple `.count()` calls on the same queryset (e.g., `pending_count`, `approved_count`, `in_progress_count`) instead of one `aggregate()` call.

#### installations/views.py — `installation_stats_api` (Lines 2580-2780)
- **Severity**: HIGH  
- **Issue**: Multiple separate `.count()` queries for different statuses. Uses 10+ separate DB queries where a single `aggregate()` would suffice.
- **Note**: Partially uses `aggregate()` but then adds 8+ additional `.count()` calls outside of it.

#### installations/views.py — `installation_analytics` (Lines 3460-3530)
- **Severity**: HIGH  
- **Issue**: Computes `avg_completion_days` by iterating all completed installations in Python instead of using a DB-level `Avg()` with `F()` expression.

### 2.4 In-Memory Pagination Anti-Pattern

#### installations/views.py — `installation_list` (Lines ~100-450)
- **Severity**: HIGH  
- **Issue**: Builds a full Python list of all installation items with nested loops before paginating. This loads all data into memory first, defeating the purpose of pagination. With thousands of installations, this causes memory pressure.
- **Fix**: Use queryset-based pagination (Django's Paginator with a QuerySet, not a list).

### 2.5 @csrf_exempt on POST Endpoints

| File | Function | Line | Notes |
|------|----------|------|-------|
| installations/views.py | `receive_completed_order` | 1346 | Modifies order/installation data |
| installations/views.py | `api_upcoming_installations` | 3796 | Returns sensitive financial data |
| accounts/api_views.py | `check_device_api` | 357 | Device fingerprinting endpoint |
| whatsapp/views.py | (webhook) | 13 | Intentional for webhook — acceptable |
| odoo_db_manager/views.py | (3 endpoints) | 1938, 1980, 2016 | External integration endpoints |
| odoo_db_manager/google_sync_views.py | (2 endpoints) | 318, 376 | External integration endpoints |

### 2.6 Missing Pagination on Large Querysets

| File | View | Line | Issue |
|------|------|------|-------|
| customers/views.py | `get_customer_notes` | ~830 | Returns ALL notes via JSON without pagination |
| inventory/views_stock_analysis.py | Both analysis views | 62, 134 | Iterates ALL warehouses/products without limit |
| reports/views.py | `Report.objects.all()` | 130, 208, 256, 290, 306 | Multiple places load all reports |

---

## 3. MEDIUM Severity Issues

### 3.1 Bare `except:` Clauses (30+ instances)

Bare `except:` clauses silently swallow all exceptions including `SystemExit`, `KeyboardInterrupt`, making debugging extremely difficult.

**Worst offenders by file:**

| File | Count | Lines |
|------|-------|-------|
| manufacturing/views.py | 6+ | 402, 454, 466, 1559, 1569, 3848, 4005 |
| orders/dashboard_views.py | 4 | 185, 254, 323, 398 |
| orders/wizard_views.py | 4 | 2576, 2592, 2963, 2978 |
| inventory/api_views.py | 7 | 354, 527, 576, 623, 762, 1033, 1120 |
| inventory/views_bulk.py | 3 | 196, 246, 1047 |
| installations/views.py | 2 | 1865, 3810 |
| board_dashboard/api_views.py | 1 | 70 |
| orders/edit_tracking_views.py | 1 | 32 |
| orders/views.py | 1 | 2337 |
| odoo_db_manager/views.py | 1 | 1448 |

**Fix**: Replace all `except:` with `except Exception as e:` and add logging.

### 3.2 DB Queries Inside Loops (Without Prefetch)

| File | Location | Line | Pattern |
|------|----------|------|---------|
| manufacturing/views.py | `create_from_order` | 2336, 2384 | `for item in order.items.all()` — missing prefetch |
| manufacturing/views.py | Multiple views | 3486, 3956, 4348, 4711, 4809 | Iterating items without prefetch |
| orders/wizard_views.py | Multiple locations | 1685-3389 | 10+ instances of `for item/curtain/fabric in X.all()` |
| cutting/views.py | `bulk_update_items` | 614 | `for item in cutting_order.items.filter(status="pending"): item.save()` — should use `.update()` |
| cutting/views.py | `bulk_complete_items` | 702 | Same pattern — loop + individual save |
| inventory/views_warehouse_cleanup.py | cleanup view | 84 | `for warehouse in Warehouse.objects.all()` |
| inventory/views_stock_transfer.py | transfer views | 432, 454 | `for item in transfer.items.all()` |
| notifications/views.py | notification view | 376 | `for v in notification.visibility_records.all()` |

### 3.3 Redundant/Duplicate Queries

#### customers/views.py — `customer_detail_by_code` (Lines 1020-1170)
- **Severity**: MEDIUM  
- **Issue**: Duplicates most of the logic from `customer_detail` — nearly identical code (~150 lines). Should be refactored into a shared helper.

#### orders/views.py — `order_detail_by_number` and `order_detail_by_code` (Lines 1560-1700)
- **Severity**: MEDIUM  
- **Issue**: Two nearly identical views for displaying order detail (by number vs by code). Should share a common helper.

#### installations/views.py — Duplicate `daily_schedule` and `print_daily_schedule`
- **Severity**: MEDIUM  
- **Issue**: These two functions each appear twice in the file (defined at two different locations), with identical query logic duplicated. The print version is a full copy of the regular one plus `print_mode: True`.

### 3.4 Missing `.only()` / `.defer()` on Large Models

| File | View | Line | Issue |
|------|------|------|-------|
| manufacturing/views.py | `export_manufacturing_orders` | ~4700 | Fetches all fields on Order + Customer + ManufacturingOrder for export |
| installations/views.py | `installation_list` | ~100 | Fetches full Order model even though only a few fields are displayed |
| complaints/views.py | Dashboard aggregates | ~50 | Loads full complaint objects for counting |
| inventory/views_stock_analysis.py | Stock analysis | 134 | Loads ALL product fields when only name/stock is needed |

### 3.5 Anti-Patterns

#### installations/views.py — `dashboard` (~Line 50)
- **Severity**: MEDIUM  
- **Issue**: Uses `RequestFactory` to internally call another view function. This is an anti-pattern that adds overhead and makes the code harder to maintain. Should extract shared logic into a utility function.

#### installations/views.py — `check_debt_before_schedule` (~Line 1900)
- **Severity**: LOW  
- **Issue**: Has duplicate `@login_required` decorator (applied twice).

#### customers/views.py — `customer_list` (Lines 115-130)
- **Severity**: MEDIUM  
- **Issue**: Complex page number parsing with regex (handling `[1]` format). This suggests a frontend bug that should be fixed at the source rather than worked around in the backend.

### 3.6 Unvalidated File Uploads

#### accounts/views.py — `register_device_view` (Lines 780-870)
- **Severity**: MEDIUM  
- **Issue**: While no file upload is directly exposed, the `device_info` field accepts arbitrary JSON from POST data (`json.loads(device_info_str)`) without validation or size limits. Could allow injection of large payloads.

#### orders/views.py — `order_create` (Lines 470-670)
- **Severity**: MEDIUM  
- **Issue**: `request.FILES.getlist("additional_invoice_images")` uploads files without validating file type or size. Could allow upload of executable files or extremely large files.

---

## 4. LOW Severity Issues

### 4.1 `print()` Statements in Production Code

| File | Lines |
|------|-------|
| orders/views.py | Multiple `print("POST DATA:", ...)`, `print("selected_products:", ...)` |
| installations/views.py | `print(f"Error in debt calculation: ...")` |
| manufacturing/views.py | Various `print(f"خطأ...")` |
| cutting/views.py | `print(f"خطأ في تسجيل تغيير حالة الطلب: {e}")` |

**Fix**: Replace all `print()` with `logger.debug()` or `logger.error()`.

### 4.2 Hardcoded Values

#### installations/views.py — `installation_analytics` (~Line 3525)
- **Issue**: `years = list(range(2020, 2026))` — hardcoded year range will become outdated.
- **Fix**: Use `range(2020, timezone.now().year + 1)`.

---

## 5. Per-App Summary

### manufacturing/ (5,331 lines)
- **Issues**: 25+ total — 8 missing auth decorators, 5 N+1 queries, 1 @csrf_exempt, 6+ bare except, multiple Python-side aggregations
- **Priority**: HIGH — Most issues in the codebase

### installations/ (4,044 lines)
- **Issues**: 18+ total — 2 @csrf_exempt (1 critical), RequestFactory anti-pattern, in-memory pagination, 10+ separate count queries, duplicate view definitions
- **Priority**: HIGH

### orders/ (2,451 lines + wizard_views, invoice_views, dashboard_views)
- **Issues**: 15+ total — bare except clauses, N+1 in invoice_print, print statements, duplicate detail views
- **Priority**: MEDIUM

### inventory/ (7,000+ lines across 12 files)
- **Issues**: 15+ total — Product.objects.all() full scans, bare except clauses in api_views, queries in loops
- **Priority**: MEDIUM-HIGH

### accounts/ (1,742 lines + api_views)
- **Issues**: 10+ total — missing auth on api endpoints, @csrf_exempt on device check, N+1 in role management, bare except
- **Priority**: HIGH (due to auth issues)

### customers/ (1,356 lines)
- **Issues**: 5 total — duplicate view logic, complex page parsing, mostly well-optimized with select_related
- **Priority**: LOW

### cutting/ (1,421 lines)
- **Issues**: 6 total — N+1 in dashboard stats, .save() in loops (should use .update()), mostly well-structured
- **Priority**: MEDIUM

### complaints/ (2,593 lines + api_views 1,492 lines)
- **Issues**: 5 total — mostly well-optimized, good use of select_related
- **Priority**: LOW

### reports/ (1,221 lines + views_ranking + api_views)
- **Issues**: 5 total — Report.objects.all() without pagination, N+1 in ranking views
- **Priority**: MEDIUM

### notifications/ (473 lines)
- **Issues**: 2 total — .visibility_records.all() in loop, minor
- **Priority**: LOW

### factory_accounting/ (408 lines)
- **Issues**: 1 — splits iteration in loop, minor
- **Priority**: LOW

---

## 6. Top 10 Most Impactful Fixes (Recommended Priority Order)

1. **Add `@login_required` to `api_upcoming_installations`** — installations/views.py:3796 — Exposes all customer financial data to unauthenticated users
2. **Add `@login_required` to all manufacturing API views** — manufacturing/views.py — 8 unprotected endpoints
3. **Remove `@csrf_exempt` from `receive_completed_order`** — installations/views.py:1346 — State-modifying POST without CSRF
4. **Fix N+1 in `ManufacturingItemStatusReportView`** — manufacturing/views.py:~430 — Scans all orders with per-item queries
5. **Fix `product.objects.all()` full table scan** — inventory/views_stock_analysis.py:134,251 — Loads entire product catalog into memory
6. **Fix in-memory pagination in `installation_list`** — installations/views.py:~100 — Builds full list before paginating
7. **Convert 10+ `.count()` calls to single `aggregate()`** — installations/views.py:2580-2780 — `installation_stats_api`
8. **Fix N+1 in `CuttingDashboardView.get_user_warehouses_with_stats`** — cutting/views.py:97-130 — 3 queries per warehouse
9. **Replace all `except:` with `except Exception as e:`** — 30+ instances across all apps
10. **Fix N+1 in `role_update`** — accounts/views.py:1590 — Triple-nested loop updating permissions

---

## 7. Positive Patterns Found

The codebase also demonstrates several good practices:

- **`select_related` / `prefetch_related`** used extensively in customers/, cutting/, and orders/ list views
- **Pagination** consistently applied in list views using `Paginator`
- **Permission decorators** properly used in customers/ views (`@permission_required`, custom permission checks)
- **`@require_POST` / `@require_http_methods`** used properly on state-modifying endpoints
- **`aggregate()`** used correctly in `CustomerDashboardView` (customers/views.py)
- **Caching** applied in accounting dashboard and department list
- **Proper error handling** with user-facing Arabic messages throughout
- **Year filtering** via `apply_default_year_filter` utility
- **Branch-based access control** properly implemented in customers/ and installations/

---

*End of Audit Report*
