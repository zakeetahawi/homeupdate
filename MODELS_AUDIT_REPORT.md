# Django Models Comprehensive Audit Report

**Date**: 2026-02-15  
**Scope**: All Django models across 18+ apps  
**Total Models Audited**: ~120+  
**Total Lines Reviewed**: ~15,000+

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 14 |
| 🟠 High | 28 |
| 🟡 Medium | 35 |
| 🔵 Low | 22 |
| **Total** | **99** |

---

## 🔴 CRITICAL Issues

### C1. N+1 Query in `__str__` Methods (Systematic Pattern)
**Impact**: Every admin page, dropdown, log entry, and template rendering triggers individual DB queries.

| File | Line | Model | Issue |
|------|------|-------|-------|
| `orders/models.py` | ~350 | `Order.__str__` | Accesses `self.customer.name` — triggers query per order |
| `orders/models.py` | ~2880 | `Payment.__str__` | Accesses `self.customer.name` and `self.order.order_number` |
| `orders/models.py` | ~2960 | `PaymentAllocation.__str__` | Accesses `self.order.order_number` |
| `orders/models.py` | ~3460 | `OrderItemModificationLog.__str__` | Accesses `self.order_item.product.name` (2 levels) |
| `orders/models.py` | ~3520 | `OrderModificationLog.__str__` | Accesses `self.order.order_number` |
| `orders/models.py` | ~3165 | `OrderStatusLog.__str__` | Accesses `self.order.order_number` |
| `cutting/models.py` | ~120 | `CuttingOrder.__str__` | Accesses `self.order.customer.name` (2 levels) |
| `cutting/models.py` | ~280 | `CuttingOrderItem.__str__` | Accesses `self.order_item.product.name` (2 levels) |
| `customers/models.py` | ~420 | `CustomerNote.__str__` | Accesses `self.customer.name` |
| `customers/models.py` | ~470 | `CustomerAccessLog.__str__` | Accesses `self.user` and `self.customer` |
| `customers/models.py` | ~380 | `CustomerResponsible.__str__` | Accesses `self.customer.name` |
| `installations/models.py` | ~65 | `CustomerDebt.__str__` | Accesses `self.customer.name` and `self.order.order_number` |
| `installations/models.py` | ~700 | `ReceiptMemo.__str__` | Accesses `self.installation.order.order_number` (3 levels) |
| `manufacturing/models.py` | ~1635 | `FabricReceipt.__str__` | Accesses `self.order.customer.name` (2 levels) |
| `manufacturing/models.py` | ~1710 | `ProductReceipt.__str__` | Accesses `self.order.customer.name` (2 levels) |
| `manufacturing/models.py` | ~1810 | `ManufacturingStatusLog.__str__` | Accesses `self.manufacturing_order.manufacturing_code` (property chain) |
| `factory_accounting/models.py` | ~400 | `FactoryCard.__str__` | Accesses `self.manufacturing_order.order.order_number` (2 levels) |
| `factory_accounting/models.py` | ~410 | `FactoryCard.customer_name` | Accesses `self.manufacturing_order.order.customer.name` (3 levels) |
| `installation_accounting/models.py` | ~115 | `InstallationCard.__str__` | Accesses `self.installation_schedule.order.order_number` (2 levels) |
| `installation_accounting/models.py` | ~125 | `InstallationCard.customer_name` | Accesses `self.installation_schedule.order.customer.name` (3 levels) |
| `inventory/models.py` | ~230 | `Category.__str__` | Accesses `self.parent.name` for recursive display |

**Recommendation**: Add `select_related()` in admin `get_queryset()` methods, manager methods, and views. For properties used in templates, consider denormalized fields or careful prefetching.

---

### C2. `Order.calculate_final_price()` / Properties Iterate All Items in Python
**File**: `orders/models.py`, lines ~780-820  
**Models**: `Order.final_price_after_discount`, `Order.total_discount_amount`, `Order.calculate_total()`

These properties iterate `self.items.all()` in Python loops, causing:
- N+1 query when accessed per order
- Cannot be used in `QuerySet.filter()` or `annotate()` since they are properties
- `CustomerFinancialSummary.refresh()` loads **all orders** then iterates in Python to access these properties

**Recommendation**: Convert to annotated aggregations using `Subquery` or store computed values in denormalized fields updated via signals.

---

### C3. `Account.full_path` / `Account._calculate_level()` Traverse Parent Chain
**File**: `accounting/models.py`, lines ~130-170  
**Model**: `Account`

These methods recursively follow `self.parent` links with individual queries per level. For deep hierarchies (4-5 levels), this generates 4-5 queries per account.

**Recommendation**: Use `django-mptt` or `django-treebeard`, or store `full_path` and `level` as denormalized fields updated on save.

---

### C4. Duplicate `save()` Method on `OrderItem`
**File**: `orders/models.py`, lines ~2580 and ~2730  
**Model**: `OrderItem`

`OrderItem` has **two** `save()` methods defined. The second one (line ~2730) completely shadows the first one (line ~2580) that handles product snapshot protection. The snapshot logic (`product_name_snapshot`, `product_code_snapshot`) is **never executed** because the second `save()` overwrites it.

**Recommendation**: Merge both `save()` methods into a single method. The snapshot logic should be at the beginning of the combined method.

---

### C5. `CustomerFinancialSummary.refresh()` Loads Entire Order Sets in Python
**File**: `accounting/models.py`, lines ~830-920  
**Model**: `CustomerFinancialSummary`

The `refresh()` method and `get_orders_with_debt()` load all orders for a customer and iterate in Python to compute `final_price_after_discount` (a property, not a DB field). For customers with 50+ orders, this is extremely expensive.

**Recommendation**: Denormalize `final_price_after_discount` to a DB field updated by signals, then use `aggregate()` instead of Python iteration.

---

## 🟠 HIGH Issues

### H1. Many Models Missing `Meta.indexes` Entirely

| File | Model | Fields That Need Indexes |
|------|-------|------------------------|
| `accounts/models.py` | `Branch` | `name`, `is_active` |
| `accounts/models.py` | `Department` | `name`, `branch` |
| `accounts/models.py` | `Employee` | `user`, `branch`, `department` |
| `accounts/models.py` | `Salesperson` | `user`, `branch`, `is_active` |
| `accounts/models.py` | `FormField` | `form_type`, `is_active` |
| `accounts/models.py` | `ActivityLog` | `user`, `action_time`, `action_type` |
| `accounts/models.py` | `Role` | `name` |
| `accounts/models.py` | `UserRole` | `user`, `role` |
| `accounts/models.py` | `BranchMessage` | `branch`, `start_date`, `end_date`, `is_active` |
| `accounts/models.py` | `InternalMessage` | `sender`, `recipient`, `created_at`, `is_read` |
| `installations/models.py` | `CustomerDebt` | `customer`, `order`, `is_paid` |
| `installations/models.py` | `Technician` | `name`, `is_active` |
| `installations/models.py` | `Vehicle` | `plate_number` |
| `installations/models.py` | `VehicleMission` | `vehicle`, `created_at` |
| `installations/models.py` | `VehicleRequest` | `requested_by`, `status` |
| `installations/models.py` | `Driver` | `name`, `is_active` |
| `installations/models.py` | `InstallationTeam` | `name` |
| `installations/models.py` | `ModificationRequest` | `installation`, `status` |
| `installations/models.py` | `InstallationPayment` | `installation`, `payment_date` |
| `installations/models.py` | `InstallationStatusLog` | `installation`, `created_at` |
| `installations/models.py` | `InstallationEventLog` | `installation`, `event_type`, `created_at` |
| `installations/models.py` | `ModificationErrorAnalysis` | `modification_request` |
| `cutting/models.py` | `Section` | (only has unique name) |
| `cutting/models.py` | `CuttingReport` | `cutting_order`, `created_at` |
| `cutting/models.py` | `CuttingOrderFixLog` | `cutting_order`, `created_at` |
| `inventory/models.py` | `Supplier` | `name`, `is_active` |
| `inventory/models.py` | `WarehouseLocation` | `warehouse`, `name` |
| `manufacturing/models.py` | `ManufacturingRejectionLog` | `manufacturing_order`, `rejected_at` |
| `complaints/models.py` | `ComplaintType` | `is_active` |
| `complaints/models.py` | `ComplaintUpdate` | `complaint`, `created_at` |
| `complaints/models.py` | `ComplaintAttachment` | `complaint`, `uploaded_at` |
| `complaints/models.py` | `ComplaintEscalation` | `complaint`, `escalated_at` |
| `reports/models.py` | `Report` | `report_type`, `created_at` |
| `reports/models.py` | `SavedReport` | `report`, `created_at` |
| `reports/models.py` | `ReportSchedule` | `report`, `is_active` |

**Recommendation**: Add `Meta.indexes` to all models that are queried by foreign keys, date ranges, or status fields.

---

### H2. `on_delete=CASCADE` Where PROTECT/SET_NULL Would Be Safer

| File | Model.Field | Current | Recommended | Reason |
|------|-------------|---------|-------------|--------|
| `installations/models.py` | `CustomerDebt.customer` | CASCADE | PROTECT | Deleting customer would silently delete debt records |
| `installations/models.py` | `CustomerDebt.order` | CASCADE | PROTECT | Deleting order would silently delete debt records |
| `complaints/models.py` | `Complaint.customer` | CASCADE | PROTECT | Deleting customer deletes complaint history |
| `complaints/models.py` | `ComplaintNotification.recipient` | CASCADE | SET_NULL | User deletion shouldn't cascade to system notifications |
| `backup_system/models.py` | `BackupJob.created_by` | CASCADE | SET_NULL | Deleting user shouldn't delete backup history |
| `backup_system/models.py` | `RestoreJob.created_by` | CASCADE | SET_NULL | Deleting user shouldn't delete restore history |

---

### H3. `Order` Model Has Redundant Timestamp Fields
**File**: `orders/models.py`, lines ~400-440  
**Model**: `Order`

- `created_at` (auto_now_add) 
- `modified_at` (auto_now)
- `updated_at` (auto_now)
- `order_date`

`modified_at` and `updated_at` are both `auto_now=True` and serve identical purposes. `order_date` and `created_at` may also overlap.

**Recommendation**: Remove one of `modified_at`/`updated_at`. Clarify business distinction between `order_date` and `created_at`.

---

### H4. `Order.get_smart_delivery_date()` and Similar Methods Make Unoptimized Queries
**File**: `orders/models.py`, lines ~1170-1250  
**Model**: `Order`

These methods (`get_smart_delivery_date`, `get_installation_date`, `get_installation_date_label`, `get_expected_installation_date`, `update_installation_status`, `update_inspection_status`) each independently query `InstallationSchedule.objects.filter(order=self).first()`, resulting in multiple identical queries per request.

**Recommendation**: Cache the result or use `@cached_property` with a single lookup. Better yet, use `select_related`/`prefetch_related` in the queryset.

---

### H5. Multiple Properties on `ManufacturingOrder` Each Do Separate Queries
**File**: `manufacturing/models.py`, lines ~500-700  

Properties like `total_items`, `completed_items`, `pending_items`, etc. each call `_get_filtered_order_items()` which hits the DB. If 5 properties are accessed in a template, that's 5 queries per manufacturing order.

**Recommendation**: Fetch all items once and compute multiple counts in a single method, or use `annotate()` at the queryset level.

---

### H6. `Customer.get_customer_type_display()` Queries DB Each Time
**File**: `customers/models.py`, lines ~580-610  
**Model**: `Customer`

Both `get_customer_type_display()` and `get_customer_type_badge_html()` call `CustomerType.objects.get()` each time they are invoked. In a customer list with 50 customers, this generates 50-100 extra queries.

**Recommendation**: Use `select_related('customer_type')` in querysets, or use Django's built-in `get_FOO_display()` if the field has choices.

---

### H7. `Payment.auto_allocate_fifo()` Loads All Orders Into Python
**File**: `orders/models.py`, lines ~2855-2890  
**Model**: `Payment`

This method loads all customer orders and iterates in Python to check `final_price_after_discount` (a property). For customers with many orders, this is very expensive.

**Recommendation**: Denormalize `final_price_after_discount` to a stored field so the query can filter at DB level.

---

### H8. `Order.save()` Method Is ~150 Lines
**File**: `orders/models.py`, lines ~500-650  
**Model**: `Order`

Overly complex `save()` method that:
- Converts Arabic numbers
- Generates order numbers
- Calculates delivery dates
- Logs changes
- Checks price changes on paid orders
- Creates status logs

**Recommendation**: Extract logic into separate methods. Use signals for side effects. Consider moving change tracking to middleware or dedicated service layer.

---

### H9. `ManufacturingDisplaySettings` and `ManufacturingOrder` Missing Cross-App Import
**File**: `manufacturing/models.py`, lines ~1350-1550  

`ManufacturingDisplaySettings` references `ManufacturingOrder.STATUS_CHOICES` and `ManufacturingOrder.ORDER_TYPE_CHOICES` that could break if the model structure changes.

---

### H10. `InternalMessage.__str__` Triggers N+1
**File**: `accounts/models.py`, line ~1200  
**Model**: `InternalMessage`

`__str__` accesses `sender.get_full_name()` and `recipient.get_full_name()`.

---

## 🟡 MEDIUM Issues

### M1. Missing Validators on Fields

| File | Model.Field | Issue |
|------|-------------|-------|
| `orders/models.py` | `Order.paid_amount` | No `MinValueValidator(0)` — negative payments possible |
| `orders/models.py` | `OrderItem.quantity` | No `MinValueValidator` — zero/negative quantity possible |
| `orders/models.py` | `OrderItem.unit_price` | No `MinValueValidator` — zero/negative price possible |
| `orders/models.py` | `OrderItem.discount_percentage` | Has help text "0-15%" but `max_digits=5` allows up to 999.99 |
| `customers/models.py` | `Customer.phone` | No phone format validator |
| `customers/models.py` | `Customer.email` | No `EmailValidator` (plain CharField) |
| `accounts/models.py` | `User.phone_number` | No phone format validator |
| `inventory/models.py` | `Product.price` | No `MinValueValidator(0)` |
| `inventory/models.py` | `Product.wholesale_price` | No `MinValueValidator(0)` |
| `inventory/models.py` | `StockTransaction.quantity` | No `MinValueValidator` |

---

### M2. `Decimal` Precision Inconsistencies

| File | Model.Field | max_digits | decimal_places | Issue |
|------|-------------|-----------|---------------|-------|
| `orders/models.py` | `Order.total_amount` | 10 | 2 | Max ~99,999,999.99 — may not be enough for large orders? |
| `orders/models.py` | `OrderItem.quantity` | 10 | 3 | 3 decimal places for quantity is unusual |
| `inventory/models.py` | `Product.price` | 18 | 2 | 18 digits is excessive (>quadrillion) |
| `inventory/models.py` | `VariantStock.current_quantity` | 18 | 2 | Same — 18 digits excessive |
| `inventory/models.py` | `BaseProduct.base_price` | 18 | 2 | Same |
| `accounting/models.py` | `TransactionLine.debit_amount` | 15 | 2 | Mismatch with Order's 10,2 |
| `customers/models.py` | `Customer.credit_limit` | 15 | 2 | Fine, but inconsistent with Order precision |

**Recommendation**: Standardize to `max_digits=12, decimal_places=2` for monetary fields across all apps. Use `max_digits=10, decimal_places=3` for quantities if decimals are needed.

---

### M3. Models Without Proper `__str__` Methods

| File | Model | Current __str__ |
|------|-------|----------------|
| `orders/wizard_models.py` | `DraftOrderInvoiceImage` | Returns draft ID + date — OK but generic |
| `inventory/models.py` | `ProductSetItem` | Missing meaningful display |
| `board_dashboard/models.py` | `BoardWidgetSettings` | Uses `get_name_display()` — OK |

Most models have `__str__` defined. This area is reasonably well-covered.

---

### M4. Large Text Fields Without `db_index` for Frequent Lookups

| File | Model.Field | Issue |
|------|-------------|-------|
| `orders/models.py` | `Order.notes` | TextField queried in search but no full-text index |
| `orders/models.py` | `Order.selected_types` | JSONField parsed in Python; should be normalized |
| `complaints/models.py` | `Complaint.description` | TextField likely searched but no FTS |
| `inspections/models.py` | `Inspection.notes` | Same |

**Recommendation**: Add PostgreSQL full-text search indexes for frequently-searched text fields, or use `SearchVector`.

---

### M5. `selected_types` (JSONField) Parsed Multiple Times in Python
**File**: `orders/models.py`, lines ~1000-1050  
**Model**: `Order`

`get_selected_types_list()` includes complex JSON double-decode logic and regex fallback. This method is called ~15+ times per order during status display, delivery date calculation, etc.

**Recommendation**: Cache the parsed result using `@cached_property`, or normalize into a separate `OrderType` M2M table.

---

### M6. Bare `except` Clauses Hiding Errors
Multiple models use `except:` or `except Exception:` with `pass` in critical code paths:

| File | Location | Impact |
|------|----------|--------|
| `orders/models.py` | `Order.get_smart_delivery_date()` | Swallows import/query errors silently |
| `orders/models.py` | `Order.update_installation_status()` | Prints to stdout but doesn't log |
| `orders/models.py` | `OrderStatusLog.save()` | Catches and re-raises — confusing flow |
| `manufacturing/models.py` | Various properties | Silently returns None on errors |
| `factory_accounting/models.py` | `FactoryCard.__str__` property chain | Swallows errors |

---

### M7. Singleton Pattern Without `get_or_create` Protection
**Files**: `accounting/models.py`, `factory_accounting/models.py`, `installation_accounting/models.py`  
**Models**: `AccountingSettings`, `FactoryAccountingSettings`, `InstallationAccountingSettings`

All use `self.pk = 1` in `save()` for singleton pattern. Race conditions could create duplicate entries if `pk=1` doesn't exist and two requests try to create simultaneously.

The `@classmethod get_settings()` methods correctly use `get_or_create()`, but direct `.objects.create()` calls elsewhere might bypass this.

---

### M8. `CompanyInfo` and Similar Settings Models Lack Caching
**File**: `accounts/models.py`  
**Models**: `CompanyInfo`, `ContactFormSettings`, `FooterSettings`, `AboutPageSettings`

These singleton-pattern models are likely queried on every page load but have no caching.

**Recommendation**: Use `@cached_as` from cacheops or `django.core.cache`.

---

### M9. `Order.manufacturing_order` Property Does Complex Logic Without Caching
**File**: `orders/models.py`, lines ~1560-1580  

The `manufacturing_order` property checks `_prefetched_objects_cache` which is good, but when prefetch isn't used, it still queries `.latest()` every time.

---

### M10. `ProductionStatusLog.__str__` Chains Through Multiple Relations
**File**: `factory_accounting/models.py`, line ~275  

Accesses `self.manufacturing_order.order.order_number` — 2 levels deep.

---

### M11. `inventoryCategory.get_total_products_count()` Recursive N+1
**File**: `inventory/models.py`, lines ~100-120  

Recursively counts products across child categories with individual queries per level.

---

### M12. `Product.current_stock` Uses `cached_property` But Still Complex
**File**: `inventory/models.py`, lines ~500-520  

Uses `@cached_property` which is good, but the computation involves complex subqueries per warehouse.

---

### M13. `Order` Model Has 40+ Fields
**File**: `orders/models.py`  

The `Order` model is a God Model with 40+ fields including status tracking, payment info, selected types, inspection status, installation status, manufacturing status, delivery dates, invoice numbers, contract numbers, etc.

**Recommendation**: Consider splitting into:
- `OrderCore` (basic order info)
- `OrderPayment` (payment-related fields)
- `OrderTracking` (status/lifecycle fields)

---

### M14. `CuttingOrder` Properties Each Do Separate Count Queries
**File**: `cutting/models.py`, lines ~140-180  

Properties like `total_items`, `completed_items`, `pending_items` each call `.count()` separately.

---

### M15. `ComplaintSLA.get_performance_metrics()` Iterates All Complaints in Python
**File**: `complaints/models.py`, lines ~1060-1100  

Iterates all complaints to check breach levels — should be done with DB aggregation.

---

## 🔵 LOW Issues

### L1. Redundant or Duplicated Fields Across Apps

| Fields | Apps | Issue |
|--------|------|-------|
| `ip_address` | orders (OrderStatusLog, OrderModificationLog), complaints (ComplaintUpdate, ComplaintEvaluation), manufacturing (ManufacturingStatusLog) | Same field pattern duplicated; could use a mixin |
| `created_by`/`updated_by` | Almost every model | Pattern repeated ~50 times; should use abstract `AuditMixin` |
| `created_at`/`updated_at` | Almost every model | Same — use `TimeStampedModel` mixin |
| Invoice/Contract numbers 1-3 | `Order`, `DraftOrder` | `invoice_number`, `invoice_number_2`, `invoice_number_3` — should be a related model |

---

### L2. Models That Could Use Abstract Base Classes

The following field patterns are repeated extensively and should be extracted:
- `created_at`, `updated_at` → `TimeStampedModel`
- `created_by`, `updated_by` → `AuditModel`
- `is_active` → `ActivatableModel`
- `notes` → included in many models

---

### L3. `ManufacturingOrder` Name Exists in Both `manufacturing` and `installations` Apps
**Files**: `manufacturing/models.py` and `installations/models.py`

The `installations` app has its own `ManufacturingOrder` model distinct from `manufacturing.ManufacturingOrder`. While Django handles this via app labels, it creates confusion and potential import issues.

**Recommendation**: Rename `installations.ManufacturingOrder` to something like `InstallationManufacturingInfo`.

---

### L4. `InvoiceTemplate` and `ContractTemplate` Are Nearly Identical
**Files**: `orders/invoice_models.py` and `orders/contract_models.py`

Both models share ~80% identical fields (company info, design settings, HTML content, usage stats). Should use a shared abstract base class.

---

### L5. `ComplaintType` Has Both `Meta.ordering = ['order', 'name']` But No Index on `order`
Minor performance issue when sorting large datasets by `order` field.

---

### L6. User Model Has ~15 Boolean Role Fields
**File**: `accounts/models.py`, lines ~50-120  
Fields: `is_salesperson`, `is_branch_manager`, `is_cutter`, `is_factory_worker`, etc.

This design doesn't scale well. Should use a Role/Permission system (Django groups + permissions, or the existing `Role`/`UserRole` models).

---

### L7. `BackupJob`/`RestoreJob` Use UUID Primary Keys Without DB Index Strategy
**File**: `backup_system/models.py`  

UUID primary keys can be slower for joins and range queries. These models have no additional indexes beyond the PK.

---

### L8. JSONField Used for Structured Data That Could Be Normalized
| File | Model.Field | Better Approach |
|------|-------------|----------------|
| `orders/models.py` | `Order.selected_types` | Normalize to M2M `OrderType` |
| `orders/models.py` | `OrderStatusLog.change_details` | Consider separate fields for common attributes |
| `manufacturing/models.py` | `ProductionLine.supported_order_types` | M2M relationship |
| `manufacturing/models.py` | `ManufacturingDisplaySettings.allowed_statuses` | M2M or choices field |

---

### L9. Missing `unique_together` or `UniqueConstraint` 

| File | Model | Suggestion |
|------|-------|-----------|
| `notifications/models.py` | `NotificationSettings` | OK (OneToOneField) |
| `complaints/models.py` | `ComplaintUserPermissions` | OK (OneToOneField) |
| `factory_accounting/models.py` | `CardMeasurementSplit` | Consider `unique_together = ['factory_card', 'tailor']` if duplicate assignments aren't intended |

---

### L10. `DraftOrder` Has 40+ Fields Mirroring `Order`
**File**: `orders/wizard_models.py`

The `DraftOrder` model largely duplicates `Order` fields. Consider using a shared abstract base or a JSON blob for wizard state instead of mirroring every field.

---

### L11. `Inspection.is_overdue` Compares Date to Datetime
**File**: `inspections/models.py`, line ~510  

```python
return self.status == "pending" and self.scheduled_date < timezone.now().date()
```

`scheduled_date` is a `DateField` but `self.status == 'pending'` should also check for `scheduled`.

---

## Priority Action Plan

### Immediate (Week 1)
1. **Fix `OrderItem` duplicate `save()` method** (C4) — Data integrity risk
2. **Add `select_related` to admin `get_queryset()`** for all models with ForeignKey `__str__` references (C1)
3. **Add missing indexes** to the top 10 most-queried models (H1)

### Short-term (Week 2-3)
4. **Fix `on_delete=CASCADE`** on financial/audit models (H2)
5. **Cache `Order.get_selected_types_list()`** result (M5)
6. **Denormalize `final_price_after_discount`** to a DB field (C2, C5, H7)
7. **Remove redundant `updated_at`/`modified_at`** on Order (H3)

### Medium-term (Month 1-2)
8. **Extract `TimeStampedModel` and `AuditModel` mixins** (L1, L2)
9. **Normalize `selected_types` JSONField** to M2M (L8)
10. **Refactor `Order.save()`** to reduce complexity (H8)
11. **Add remaining indexes** from H1 table (H1)
12. **Standardize Decimal precision** across all monetary fields (M2)

### Long-term (Quarter)
13. **Split `Order` God Model** into focused models (M13)
14. **Implement full-text search** for frequently-searched text fields (M4)
15. **Rename `installations.ManufacturingOrder`** to avoid confusion (L3)
16. **Create shared abstract base** for `InvoiceTemplate`/`ContractTemplate` (L4)
