# i18n & Runtime Error Audit Report

**Project**: El-Khawaga ERP System  
**Date**: 2026-02-14  
**Python**: 3.13.0 | **Django**: 5.1.5 (Note: copilot-instructions.md claims Django 6.0, actual is 5.1.5)

---

## Part 1: Internationalization (i18n) Audit

### Overall Grade: ⚠️ PARTIAL — Infrastructure exists but implementation is incomplete

---

### 1. `gettext` / `gettext_lazy` in `views.py` files

**Status**: ❌ **FAILING** — 33 view files lack any `gettext` import

The following `views.py` files have **no** `gettext` import and use hardcoded Arabic strings for `messages.success()`, `messages.error()`, etc.:

| File | Concern |
|------|---------|
| `accounting/views.py` | 6+ hardcoded message strings |
| `accounting/views_bank.py` | Hardcoded messages |
| `accounting/views_statement.py` | Hardcoded messages |
| `accounts/views.py` | 15+ hardcoded message strings |
| `accounts/activity_views.py` | Debug print() with hardcoded strings |
| `backup_system/views.py` | No i18n |
| `board_dashboard/views.py` | No i18n |
| `complaints/views.py` | No i18n |
| `core/views.py` | No i18n |
| `crm/views.py` | No i18n |
| `cutting/views.py` | No i18n |
| `factory_accounting/views.py` | No i18n |
| `installation_accounting/views.py` | No i18n |
| `inventory/views.py` | No i18n |
| `inventory/views_bulk.py` | Has gettext but partial |
| `inventory/views_extended.py` | No i18n |
| `inventory/views_optimized.py` | No i18n |
| `inventory/views_product_set.py` | No i18n |
| `inventory/views_reports.py` | No i18n |
| `inventory/views_stock_analysis.py` | No i18n |
| `inventory/views_stock_transfer.py` | No i18n |
| `inventory/views_warehouse_locations.py` | No i18n |
| `manufacturing/views.py` | No i18n |
| `manufacturing/views_optimized.py` | No i18n |
| `public/views.py` | No i18n |
| `reports/views_ranking.py` | No i18n |
| `user_activity/views.py` | No i18n |
| `whatsapp/views.py` | No i18n |

**Unwrapped `messages.*()` calls**: **464 out of 533** total (~87%) do not use `_()` wrapping.

---

### 2. Template `{% trans %}` / `{% blocktrans %}` Usage

**Status**: ❌ **FAILING** — 359 of 444 templates (~81%) do NOT load `{% load i18n %}`

Only **85 templates** (mostly in `templates/db_manager/`, `reports/`, and `admin/`) properly load i18n. The vast majority of app templates use hardcoded Arabic strings directly.

**Worst offenders** (entire app with zero i18n in templates):
- `complaints/templates/` — 0 of ~15 templates use i18n
- `cutting/templates/` — 0 of ~8 templates
- `installations/templates/` — 0 of ~30+ templates
- `customers/templates/` — 0 of ~5 templates
- `backup_system/templates/` — 0 of ~10 templates
- `board_dashboard/templates/` — 0 of 1 template
- `accounting/templates/` — 0 of ~2 templates
- `inspections/templates/` — 0 of ~7 templates

---

### 3. Model `verbose_name` / `help_text` with `gettext_lazy`

**Status**: ❌ **FAILING** — 1,088 `verbose_name` definitions without `_()` vs only 331 with `_()`.

**77% of `verbose_name` fields are unwrapped.**

Models.py files with **no** `gettext` import at all:
- `backup_system/models.py`
- `board_dashboard/models.py`
- `cutting/models.py`
- `manufacturing/models.py`
- `user_activity/models.py`

---

### 4. Locale Directory & Translation Files

**Status**: ❌ **MISSING**

- No `locale/` directory exists in the project root or any app
- No `.po` files found anywhere in the project
- No `.mo` files found anywhere in the project
- No `LOCALE_PATHS` setting defined in `crm/settings.py`
- `makemessages` / `compilemessages` have never been run

---

### 5. `LANGUAGES` Setting

**Status**: ❌ **MISSING**

- `LANGUAGE_CODE = "ar"` is set (line 619 of `crm/settings.py`)
- `USE_I18N = True` is set (line 621)
- **No `LANGUAGES` tuple** is defined — required for language switching
- No language selector/switcher exists in the UI

---

### 6. `LocaleMiddleware`

**Status**: ❌ **MISSING**

`django.middleware.locale.LocaleMiddleware` is **not present** in the `MIDDLEWARE` list (lines 413-431 of `crm/settings.py`). This middleware is required for:
- Per-request language detection
- URL-based language prefixes
- Session/cookie language persistence

---

### 7. JavaScript i18n Support

**Status**: ❌ **NOT IMPLEMENTED**

- **No** `jsi18n` URL configured in `crm/urls.py`
- **No** `JavaScriptCatalog` view registered
- **No** Django JS i18n catalog (`django.views.i18n.JavaScriptCatalog`) in use
- **29+ custom JS files** contain hardcoded Arabic/English strings in `alert()`, `confirm()`, `textContent`, `innerHTML` calls
- Files like `static/js/debt_check.js`, `static/js/form-validation.js`, `static/js/order_items.js` have untranslatable UI strings

---

### 8. Forms with `gettext` for Labels/Error Messages

**Status**: ❌ **FAILING** — 8 form files lack any `gettext` import

Missing `gettext` in forms:
| File |
|------|
| `accounting/forms.py` |
| `backup_system/forms.py` |
| `complaints/forms.py` |
| `complaints/forms_backup.py` |
| `cutting/forms.py` |
| `inventory/forms_product_set.py` |
| `orders/forms.py` |
| `whatsapp/forms.py` |

---

### 9. Admin `fieldsets` Translation

**Status**: ❌ **FAILING** — 11 `admin.py` files lack `gettext`

Missing:
| File |
|------|
| `accounting/admin.py` |
| `backup_system/admin.py` |
| `board_dashboard/admin.py` |
| `complaints/admin.py` |
| `core/admin.py` |
| `cutting/admin.py` |
| `installation_accounting/admin.py` |
| `manufacturing/admin.py` |
| `public/admin.py` |
| `user_activity/admin.py` |
| `whatsapp/admin.py` |

---

## Part 2: Runtime Error Checks

---

### 1. Bare `except:` Clauses

**Status**: 🔴 **CRITICAL** — **154 bare `except:` clauses** found

Bare excepts silently swallow all exceptions including `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit`. This can mask genuine bugs and make debugging extremely difficult.

**Top offenders by file:**

| File | Count | Lines (sample) |
|------|-------|----------------|
| `orders/models.py` | 15 | L1192, L1206, L1231, L1243, L1256, L1365, L1377, L1833, L3366, L3438, L3446, L3454, L3471, L3479, L3487 |
| `manufacturing/views.py` | 7 | (multiple) |
| `inventory/tasks_optimized.py` | 7 | (multiple) |
| `inventory/api_views.py` | 7 | (multiple) |
| `accounting/views.py` | 6 | (multiple) |
| `crm/management/commands/auto_security_scan.py` | 5 | (multiple) |
| `complaints/api_views.py` | 5 | (multiple) |
| `orders/wizard_views.py` | 4 | L2576, L2592, L2963, L2978 |
| `orders/dashboard_views.py` | 4 | L185, L254, L323, L398 |
| `complaints/admin.py` | 4 | (multiple) |
| `notifications/serializers.py` | 1 | L110 |
| `notifications/admin.py` | 1 | L179 |
| `orders/signals.py` | 2 | L1482, L1771 |
| `orders/edit_tracking_views.py` | 1 | L32 |
| `odoo_db_manager/views.py` | 1 | L1448 |
| `odoo_db_manager/models.py` | 1 | L749 |
| `odoo_db_manager/tasks.py` | 1 | L77 |
| `whatsapp/signals.py` | 1 | L114 |
| `factory_accounting/models.py` | 1 | L442 |
| `public/cloudflare_sync.py` | 1 | L154 |
| `orders/wizard_forms.py` | 1 | L581 |
| `orders/views.py` | 1 | L2337 |
| `orders/templatetags/decimal_filters.py` | 2 | L90, L99 |
| `orders/templatetags/order_extras.py` | 2 | L246, L320 |

**Recommendation**: Replace all `except:` with `except Exception:` at minimum, or more specific exceptions where possible.

---

### 2. TODO / FIXME / HACK / XXX Comments

**Status**: ⚠️ **LOW** — 3 genuine TODO/FIXME items found

| File | Line | Comment |
|------|------|---------|
| `odoo_db_manager/advanced_sync_service_backup.py` | L203 | `TODO: Remove this comment and the following line once the new models are implemented` |
| `odoo_db_manager/advanced_sync_service.py` | L21 | `TODO: إعادة التنفيذ باستخدام ManufacturingOrder` (re-implement using ManufacturingOrder) |
| `crm/management/commands/auto_security_scan.py` | L338 | `TODO: تنفيذ فحص أكثر تفصيلاً` (implement more detailed scan) |
| `complaints/management/commands/cleanup_notifications.py` | L23 | `TODO: إضافة منطق المعاينة` (add preview logic) |

---

### 3. `print()` Statements That Should Be Logger Calls

**Status**: 🔴 **CRITICAL** — **367 `print()` calls** in production code

These should all use `logging.getLogger(__name__)` instead.

**Top offenders:**

| File | Count |
|------|-------|
| `odoo_db_manager/views.py` | 83 |
| `complaints/views.py` | 67 |
| `odoo_db_manager/models.py` | 31 |
| `orders/views.py` | 24 |
| `installations/views.py` | 22 |
| `accounts/signals.py` | 15 |
| `manufacturing/views.py` | 13 |
| `crm/middleware.py` | 13 |
| `complaints/forms.py` | 11 |
| `accounts/admin.py` | 10 |
| `factory_accounting/views.py` | 9 |
| `accounts/activity_views.py` | 9 |
| `backup_system/services.py` | 7 |
| `orders/wizard_views.py` | 6 |
| `orders/signals.py` | 6 |
| `core/materialized_views.py` | 6 |
| `inspections/views.py` | 5 |
| `accounts/messages_views.py` | 5 |
| `orders/models.py` | 4 |
| `user_activity/signals.py` | 3 |

**Impact**: Print statements go to stdout only, are not configurable, have no log levels, and are lost in production ASGI/WSGI deployments.

---

### 4. `try/except ImportError` Patterns

**Status**: ⚠️ **MODERATE** — 30+ occurrences found

Most are **intentional optional-dependency patterns** (acceptable), but some are concerning:

**Acceptable patterns** (guarding optional modules):
- `orders/signals.py` L1738-1882: Guards for optional inspection/cutting/installation/manufacturing modules
- `orders/models.py` L3060-3087: Guards for status choices from optional modules
- `orders/services/google_drive_service.py` L22: Guards Google API
- `inspections/services/google_drive_service.py` L22: Guards Google API
- `core/file_validation.py` L107, L138: Guards python-magic

**Concerning patterns** (may hide real bugs):
| File | Line | Issue |
|------|------|-------|
| `manufacturing/models.py` | L561 | Silent `pass` on ImportError — may mask broken dependencies |
| `manufacturing/views.py` | L1771 | Silent `pass` on ImportError |
| `crm/__init__.py` | L13 | Celery import silenced — could mask broken celery config |
| `odoo_db_manager/apps.py` | L40 | ImportError caught but logged — acceptable |

---

### 5. Deprecated Django Features

**Status**: ⚠️ **MODERATE** — Several deprecated patterns found

| Pattern | Status | Locations | Severity |
|---------|--------|-----------|----------|
| `default_app_config` | Deprecated since Django 3.2, **removed in 6.0** | `backup_system/__init__.py:2`, `crm/__init__.py:16`, `inspections/__init__.py:1`, `odoo_db_manager/__init__.py:5` | **HIGH** — will break on Django 6.0 upgrade |
| `unique_together` | Deprecated since Django 4.2 (use `UniqueConstraint`) | `accounts/models.py:653,941`, `customers/models.py:390`, `installations/models.py:977` + migrations | **MEDIUM** — still works but should migrate |
| `MiddlewareMixin` | Deprecated (not needed since Django 2.0+ for MIDDLEWARE) | `accounts/middleware/*.py`, `core/security_middleware.py` — 5+ files | **LOW** — still functional but unnecessary |
| `STATICFILES_STORAGE` | Renamed to `STORAGES["staticfiles"]` in Django 4.2 | `crm/settings.py:631` | **MEDIUM** — emits deprecation warning |

**Note**: `copilot-instructions.md` claims **Django 6.0** but actual version is **5.1.5**. When upgrading to 6.0, `default_app_config` will cause immediate startup failures.

---

### 6. Python 3.12+ Compatibility

**Status**: ✅ **GOOD** — No issues found

- No `distutils` usage (removed in 3.12)
- No `imp` module usage (removed in 3.12)
- No `asyncio.coroutine` decorator (removed in 3.11)
- No old-style `typing.Dict`/`typing.List` imports
- No `locale.getdefaultlocale()` usage
- Python 3.13.0 is in use and running without import errors

---

## Summary Dashboard

| Category | Status | Count/Details |
|----------|--------|---------------|
| **i18n: gettext in views** | ❌ | 33 view files missing import |
| **i18n: Template {% trans %}** | ❌ | 359/444 templates (~81%) missing |
| **i18n: Model verbose_name** | ❌ | 1,088/1,419 (~77%) unwrapped |
| **i18n: locale/.po/.mo files** | ❌ | None exist |
| **i18n: LANGUAGES setting** | ❌ | Not defined |
| **i18n: LocaleMiddleware** | ❌ | Not in MIDDLEWARE |
| **i18n: JavaScript i18n** | ❌ | No catalog, 29+ files with hardcoded strings |
| **i18n: Forms gettext** | ❌ | 8 form files missing |
| **i18n: Admin gettext** | ❌ | 11 admin files missing |
| **Runtime: Bare except** | 🔴 | 154 instances in 50+ files |
| **Runtime: TODO/FIXME** | ⚠️ | 4 genuine TODOs |
| **Runtime: print() in prod** | 🔴 | 367 calls across 20+ files |
| **Runtime: ImportError** | ⚠️ | 30+ (mostly intentional) |
| **Runtime: Deprecated Django** | ⚠️ | 4 `default_app_config`, `unique_together`, `STATICFILES_STORAGE` |
| **Runtime: Python 3.12+ compat** | ✅ | No issues |

---

## Priority Recommendations

### P0 (Critical — Fix Before Next Deploy)
1. **Replace 154 bare `except:` with `except Exception:`** — Start with `orders/models.py` (15), `manufacturing/views.py` (7), `inventory/tasks_optimized.py` (7)
2. **Replace 367 `print()` with `logger.` calls** — Start with `odoo_db_manager/views.py` (83), `complaints/views.py` (67)

### P1 (High — Fix Before Django 6.0 Upgrade)
3. **Remove 4 `default_app_config`** assignments — will break on Django 6.0
4. **Migrate `STATICFILES_STORAGE` → `STORAGES`** format
5. **Migrate `unique_together` → `UniqueConstraint`** in models

### P2 (Medium — i18n Foundation)
6. **Add `LocaleMiddleware`** to MIDDLEWARE
7. **Define `LANGUAGES`** and `LOCALE_PATHS` in settings
8. **Create `locale/` directory** and run `makemessages`
9. **Wrap `messages.*()` calls** with `_()` — 464 unwrapped calls
10. **Wrap `verbose_name` strings** with `_()` — 1,088 unwrapped

### P3 (Low — Full i18n Compliance)
11. Add `{% load i18n %}` and `{% trans %}` to 359 templates
12. Set up `JavaScriptCatalog` for JS i18n
13. Remove `MiddlewareMixin` from custom middlewares
