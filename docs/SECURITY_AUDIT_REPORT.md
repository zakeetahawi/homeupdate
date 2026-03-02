# 🔒 Security Audit Report — El-Khawaga ERP System

**Date**: February 14, 2026  
**Auditor**: Automated Security Scan  
**Scope**: Full codebase — all `.py`, `.html`, `.js` files, settings, and configs

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 6 |
| 🟠 HIGH | 8 |
| 🟡 MEDIUM | 9 |
| 🔵 LOW | 5 |
| **Total** | **28** |

---

## 🔴 CRITICAL Vulnerabilities

### C1. Hardcoded Database Password in Settings (Committed to Git)

**File**: `crm/settings.py` lines 553, 585  
**Also in**: `db_settings.json` (root)

```python
"PASSWORD": "5525",
```

The PostgreSQL password `5525` is hardcoded in settings **and** committed to git history. Even though `db_settings.json` is now in `.gitignore`, it was previously committed (10+ commits in history).

**Impact**: Anyone with repo access has full database credentials.  
**Fix**:
```python
"PASSWORD": os.environ.get("DB_PASSWORD"),
```
Then run `git filter-repo` or BFG Repo Cleaner to purge `db_settings.json` and `cloudflare-credentials.json` from git history.

---

### C2. Cloudflare Tunnel Secret Committed to Git History

**File**: `cloudflare-credentials.json` (root)

```json
{"AccountTag":"4085f6891221e9884cf399a561d235c0","TunnelSecret":"+R847TVYKlKOCw9aqVLZVN69YcxziW5rQLf0bskBges=","TunnelID":"02d18311-..."}
```

This file contains the **Cloudflare Tunnel secret** and was committed in at least 10 prior git commits. The `.gitignore` entry was added after the fact, so the secret persists in git history.

**Impact**: Tunnel compromise allows traffic interception/redirection.  
**Fix**: Rotate the Cloudflare Tunnel secret immediately. Purge file from git history.

---

### C3. DEBUG Defaults to True in Production

**File**: `crm/settings.py` line 300

```python
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")
```

If the `DEBUG` environment variable is not set, **DEBUG defaults to `True`**. This means a fresh deployment or misconfigured server exposes full stack traces, SQL queries, and settings to end users.

**Impact**: Full information disclosure — stack traces, settings, DB queries leaked.  
**Fix**:
```python
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")
```

---

### C4. DisableCSRFMiddleware Loaded When DEBUG=True

**File**: `crm/settings.py` lines 903-912

```python
if DEBUG:
    class DisableCSRFMiddleware:
        def __init__(self, get_response):
            self.get_response = get_response
        def __call__(self, request):
            if request.path.startswith("/api/"):
                setattr(request, "_dont_enforce_csrf_checks", True)
            return self.get_response(request)
    MIDDLEWARE.insert(0, "crm.settings.DisableCSRFMiddleware")
```

Combined with C3 (DEBUG defaults True), this middleware **disables CSRF protection for all `/api/` endpoints** in production if `DEBUG` env var is not explicitly set to `False`.

**Impact**: CSRF attacks on all API endpoints. Attackers can perform actions on behalf of authenticated users.  
**Fix**: Remove this middleware entirely, or gate it behind `DEVELOPMENT_MODE` env var (not `DEBUG`).

---

### C5. Hardcoded Default Superuser with Weak Password

**File**: `odoo_db_manager/middleware/default_user.py` lines 55-62

```python
User.objects.create_superuser(
    username="admin",
    email="admin@example.com",
    password="admin123",
    ...
)
```

A default superuser `admin` / `admin123` is auto-created if no users exist. This runs as middleware (on every request).

**Also**: `odoo_db_manager/services/database_service.py` line 288 uses `"admin123"` as fallback password.  
**Also**: `odoo_db_manager/views.py` line 1800 uses `make_password("admin123")`.

**Impact**: Trivially guessable admin credentials on any fresh/reset deployment.  
**Fix**: Generate a random password, print it once, and require immediate change. Or remove auto-creation.

---

### C6. File Upload Size Set to 1GB

**File**: `crm/settings.py` lines 1094-1095

```python
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1GB
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1GB
```

This allows uploading files up to **1 gigabyte** in memory. Note: later in the file (lines 1562-1563) it's set to 10MB, but due to Python's sequential execution, the 1GB value defined earlier applies or gets overridden unpredictably.

**Impact**: Denial of Service — a single 1GB upload can exhaust server memory.  
**Fix**: Remove the 1GB setting. Keep only:
```python
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10 MB
```

---

## 🟠 HIGH Vulnerabilities

### H1. WhatsApp Verify Token Hardcoded with Guessable Default

**File**: `crm/settings.py` lines 1803-1804

```python
WHATSAPP_VERIFY_TOKEN = os.getenv(
    "WHATSAPP_VERIFY_TOKEN", "elkhawaga-whatsapp-webhook-2026"
)
```

The fallback token `elkhawaga-whatsapp-webhook-2026` is easily guessable and would allow an attacker to register a malicious webhook.

**Fix**: Remove the default value — require the env var explicitly.

---

### H2. Health Check Endpoints Expose System Information Without Auth

**Files**: `crm/views_health.py`, `crm/health.py`  
**URL**: `/health/`, `/health-check/` — **no authentication required**

These endpoints expose:
- Database engine, connection status
- Memory usage, CPU usage, disk usage percentages
- `DEBUG` status ("development" vs "production")

**Impact**: Information disclosure aids attackers in reconnaissance.  
**Fix**: Restrict the detailed JSON health check to authenticated staff. Keep only `HTTP 200 "OK"` for load balancer probes.

---

### H3. CSRF Debug/Test Views Accessible in Production

**File**: `crm/urls.py` lines 51-53, `crm/csrf_views.py`

```python
path("csrf-token/", get_csrf_token_view, name="csrf_token"),
path("csrf-debug/", csrf_debug_view, name="csrf_debug"),
path("csrf-test/", test_csrf_view, name="csrf_test"),
```

While `csrf_debug_view` checks `settings.DEBUG`, `get_csrf_token_view` and `test_csrf_view` are always accessible. The `csrf-token/` endpoint hands out CSRF tokens to any unauthenticated request.

**Fix**: Wrap all three behind `if settings.DEBUG:` in the URL configuration, or require authentication.

---

### H4. 9 Views Using @csrf_exempt

**Files and Lines**:
- `whatsapp/views.py:13` — `meta_webhook` (legitimate for webhooks, but verify token is weak)
- `accounts/api_views.py:357` — `check_device_api` (no auth required)
- `odoo_db_manager/views.py:1938,1980,2016` — `restore_progress_status`, `generate_temp_token`, `refresh_session`
- `odoo_db_manager/google_sync_views.py:318,376` — `google_sync_advanced_settings`, `reverse_sync_view` (have login_required, lower risk)
- `installations/views.py:1346,3796` — `receive_completed_order`, `api_upcoming_installations`

**Impact**: CSRF-exempt endpoints can be exploited via cross-site requests.  
**Fix**: 
- `check_device_api`: Add rate-limiting. Consider HMAC signature validation.
- `api_upcoming_installations`: This is a GET endpoint — remove `@csrf_exempt` (GET requests are CSRF-exempt by default in Django).
- For AJAX endpoints: use `X-CSRFToken` header instead of `@csrf_exempt`.

---

### H5. Open Redirect in Login View

**File**: `accounts/views.py` line 561

```python
next_url = request.GET.get("next", "home")
return redirect(next_url)
```

The `next` parameter from user input is passed directly to `redirect()` without validation. An attacker can craft: `/accounts/login/?next=https://evil.com` to redirect users after login.

**Impact**: Phishing attacks via trusted domain redirect.  
**Fix**:
```python
from django.utils.http import url_has_allowed_host_and_scheme
next_url = request.GET.get("next", "")
if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
    next_url = "home"
return redirect(next_url)
```

---

### H6. Directory Traversal Risk in Media File Serving

**File**: `crm/views.py` lines 186-218

```python
def serve_media_file(request, path):
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        raise Http404("Media file not found")
    file = open(file_path, "rb")
    ...
```

The `path` comes from the URL regex `(?P<path>.*)`. While `os.path.join` provides some protection, there is **no validation** that the resolved path stays within `MEDIA_ROOT`. A path like `../../etc/passwd` could potentially escape.

**Impact**: Arbitrary file read from the server filesystem.  
**Fix**:
```python
import os
file_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, path))
if not file_path.startswith(os.path.normpath(settings.MEDIA_ROOT)):
    raise Http404("Invalid path")
```

---

### H7. Pickle Serializer for Redis Cache

**File**: `core/redis_config.py` line 99

```python
'SERIALIZER': 'django_redis.serializers.pickle.PickleSerializer',
```

Pickle deserialization of untrusted data enables **remote code execution**. If an attacker can write to Redis (e.g., via SSRF or misconfigured Redis), they can inject a malicious pickle payload.

**Impact**: Remote Code Execution (RCE) if Redis is compromised.  
**Fix**:
```python
'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
```

---

### H8. Public Views Without Authentication (Intentional but Risky)

**File**: `public/views.py` — all views (`product_qr_view`, `generate_product_qr`, `qr_export_page`, `qr_pdf_download`)

These are intentionally public for QR code access, but `qr_export_page` and `qr_pdf_download` generate exports of **all products** without any access control. A competitor could scrape the full product catalog.

**Fix**: Add rate-limiting to public views. Consider requiring authentication for bulk export/PDF downloads.

---

## 🟡 MEDIUM Vulnerabilities

### M1. `|safe` Filter Used 47 Times in Templates

**Multiple template files** use `{{ variable|safe }}`, rendering content without HTML escaping. Key risk areas:

- `templates/components/data_table.html:16` — `{{ cell|safe }}` (table cell content)
- `templates/components/alert.html:6` — `{{ message|safe }}` (alert messages)
- `reports/templates/reports/report_detail.html:153` — `data-result='{{ result.data|safe }}'`
- `inventory/templates/inventory/check_duplicates.html:107` — inline onclick handler with `{{ dup.warehouses|safe }}`

Most uses are for rendering HTML generated server-side (badges, buttons) or JSON data for JavaScript — **lower risk if data is always developer-controlled**. However, any user-supplied data passed through these paths is vulnerable to XSS.

**Fix**: Audit each usage. Replace `|safe` with `|escapejs` for JavaScript contexts. Use `json_script` template tag for JSON data:
```django
{{ data|json_script:"chart-data" }}
```

---

### M2. Raw SQL in user_activity/admin.py (Parameterized — Low Injection Risk)

**File**: `user_activity/admin.py` lines 275-331

Multiple `cursor.execute()` calls with raw SQL. The queries **do use parameterized queries** (`%s` placeholders), which is correct. However, line 315 uses f-string placeholders construction:

```python
placeholders = ",".join(["%s"] * len(session_keys))
cursor.execute(f"DELETE FROM django_session WHERE session_key IN ({placeholders})", session_keys)
```

This pattern is safe (the f-string only contains `%s` placeholders), but it's fragile and could be accidentally made unsafe.

**Fix**: Use Django ORM instead:
```python
Session.objects.filter(session_key__in=session_keys).delete()
```

---

### M3. `mark_safe` Used Extensively in Admin

Multiple files (mostly admin.py files) use `mark_safe()` for rendering status badges. These are **admin-only contexts** with developer-controlled strings — lower risk. But any dynamic/user content passed here would be vulnerable.

Riskier uses:
- Anywhere `mark_safe` includes data from model fields that users can edit.

**Fix**: Use `format_html()` instead of `mark_safe()` where possible.

---

### M4. Debug Print Statements in Production Code

**Files**: `odoo_db_manager/views.py` lines 1943-2060+

```python
print(f"🔍 [DEBUG] generate_temp_token called")
print(f"🔍 [DEBUG] User authenticated: {request.user.is_authenticated}")
print(f"🔍 [DEBUG] Request body: {request.body}")
```

Debug print statements log sensitive information (request bodies, user auth status, tokens) to stdout, which may be captured in server logs.

**Fix**: Replace `print()` with proper `logger.debug()` calls. Remove `request.body` logging.

---

### M5. Test Pages Accessible in Production

**File**: `crm/urls.py` lines 142-152

```python
path("test-clean/", TemplateView.as_view(template_name="test_clean.html"), name="test_clean"),
path("test-minimal/", views.test_minimal_view, name="test_minimal"),
path("test-complaint-type/", TemplateView.as_view(template_name="test_complaint_type_debug.html"), name="test_complaint_type_debug"),
```

These test/debug views are always registered regardless of `DEBUG` setting.

**Fix**: Wrap in `if settings.DEBUG:` block.

---

### M6. Hardcoded Cloudflare KV Namespace ID

**File**: `crm/settings.py` line 689

```python
CLOUDFLARE_KV_NAMESPACE_ID = os.environ.get(
    "CLOUDFLARE_KV_NAMESPACE_ID", "5dad2f4d72b246758bdafa17dfe4eb10"
)
```

The namespace ID is hardcoded as a fallback. While not as critical as an API key, it's still an infrastructure identifier that should be environment-only.

**Fix**: Remove default value.

---

### M7. Hardcoded API Key in Migration File

**File**: `public/migrations/0002_default_cloudflare_settings.py` line 17

```python
sync_api_key="cf_66eed06368ff433b92ac3f80c950038f",
```

An API key is hardcoded in a migration file that lives permanently in git history.

**Fix**: The migration has already run. For future migrations, never include secrets. Rotate this API key.

---

### M8. FILE_UPLOAD_MAX_MEMORY_SIZE Defined Three Times

**File**: `crm/settings.py` lines 1094, 1562, 1707

The setting is defined three times with different values (1GB, 10MB, 10MB). The **last one wins** (10MB), but the 1GB setting at line 1094 suggests confusion and could become active if later settings are commented out.

**Fix**: Remove all duplicate definitions. Keep only one 10MB setting.

---

### M9. CSP Allows `'unsafe-inline'` and `'unsafe-eval'`

**File**: `crm/settings.py` lines 791-798

```python
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "'unsafe-eval'", ...)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
```

`'unsafe-inline'` and `'unsafe-eval'` significantly weaken CSP protection against XSS.

**Fix**: Migrate to nonce-based CSP. Add `{% csp_nonce %}` to inline scripts.

---

## 🔵 LOW Vulnerabilities

### L1. MD5 Used for Cache Key Generation

**Files**: `core/performance_middleware.py:136`, `core/redis_config.py:305,332,358`, `core/performance_optimizer.py:79,106,339`, `accounting/performance_utils.py:31`

MD5 is used to generate cache keys from query strings and arguments. This is **not a security risk** (not used for passwords/auth), but it's a code smell.

**Fix**: No action required for cache keys, but use `hashlib.sha256` for consistency.

---

### L2. Multiple Settings File Fragments and Backups

**File**: `crm/settings_backup.py` exists alongside `crm/settings.py`

This backup file also contains the `DisableCSRFMiddleware` class and database configuration patterns. Having multiple settings files creates confusion.

**Fix**: Remove `settings_backup.py` from the project.

---

### L3. `DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000`

**File**: `crm/settings.py` line 985

The default is 1000. Setting this to 10000 increases the attack surface for hash collision DoS attacks in form parsing.

**Fix**: Reduce to a reasonable limit unless specific forms require it.

---

### L4. Two-Factor Authentication Disabled

**File**: `crm/settings.py` line 1798

```python
TWO_FACTOR_AUTH_ENABLED = False
```

2FA is available but disabled.

**Fix**: Enable 2FA for admin and staff users at minimum.

---

### L5. `sslmode = disable` for PostgreSQL Connection

**File**: `crm/settings.py` line 569

```python
"sslmode": "disable",
```

Database connections don't use SSL. Since DB is on localhost, this is low risk, but if the DB is ever moved to a remote server, credentials would be transmitted in cleartext.

**Fix**: Set to `"prefer"` or `"require"` for non-localhost deployments.

---

## ✅ Positive Security Findings

The following security measures are correctly implemented:

1. **SECRET_KEY from environment** — Properly sourced from `os.environ` with error for production
2. **Password validators** — Four Django validators configured
3. **django-axes** — Brute-force protection enabled
4. **HSTS** — Enabled in production (1 year, subdomains, preload)
5. **Secure cookies** — `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` in production
6. **ALLOWED_HOSTS** — Properly restricted (no `*` wildcard)
7. **File validation utility** — `core/file_validation.py` exists with extension, size, MIME type, and filename sanitization
8. **X-Frame-Options** — Set to `DENY` in production
9. **Password hashers** — PBKDF2 used (strong default)
10. **`.gitignore`** — Covers `db_settings.json`, `cloudflare-credentials.json`, `.env`, `*secret*`, `*key*`

---

## 🎯 Priority Action Items

| Priority | Action | Effort |
|----------|--------|--------|
| 1 | Change DEBUG default to `False` | 1 min |
| 2 | Move DB password to env var | 5 min |
| 3 | Remove `DisableCSRFMiddleware` or gate behind `DEVELOPMENT_MODE` | 5 min |
| 4 | Rotate Cloudflare tunnel secret | 10 min |
| 5 | Purge secrets from git history (BFG/filter-repo) | 30 min |
| 6 | Fix open redirect in login view | 5 min |
| 7 | Add path traversal protection to `serve_media_file` | 5 min |
| 8 | Remove 1GB upload size setting | 1 min |
| 9 | Change PickleSerializer to JSONSerializer | 2 min |
| 10 | Restrict health check endpoints | 10 min |
| 11 | Remove/gate test URLs behind DEBUG | 5 min |
| 12 | Remove hardcoded `admin123` default password | 10 min |
