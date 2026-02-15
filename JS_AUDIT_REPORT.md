# JavaScript Audit Report — `/static/js/`
**Date**: February 15, 2026  
**Total Files**: 26 (+ 1 in `dashboard/`)  
**Total Lines**: 8,253  
**Total Size**: ~310 KB

---

## 1. Per-File Analysis

### Files Loaded Globally (via `base.html`)
These files load on **every single page** — optimization here has the highest impact.

| File | Lines | KB | Purpose | jQuery? | console.* | DOMContentLoaded |
|------|------:|---:|---------|---------|----------:|-----------------:|
| `main.js` | 111 | 3.9 | Theme switching, chart/table refresh on theme change | No (vanilla) | 0 | 1 |
| `smooth-navigation.js` | 271 | 9.6 | Page transitions, anti-flicker, mobile/tablet adjustments | No | 0 | **2** |
| `custom-theme-animations.js` | 120 | 5.3 | Custom theme scroll animations, icon hover effects | No | 1 | **2** |
| `csrf-handler.js` | 293 | 10.0 | CSRF token management, fetch interceptor, jQuery `ajaxSetup`, periodic refresh | Both | 8 | 1 |
| `internal_messages_dropdown.js` | 207 | 8.8 | Internal messaging dropdown, online users, polling | Vanilla (+manual getCsrfToken) | 3 | 1 |
| `floating-button.js` | 893 | 33.2 | Draggable floating chat button + full mini-chat system (WebSocket) | No | 8 | 1 |
| `arabic-numbers-converter.js` | 115 | 3.7 | Converts Arabic-Indic numerals → ASCII in inputs | No (IIFE) | 1 | 1 |

### Page-Specific Files (loaded on particular pages)

| File | Lines | KB | Purpose | Used By | jQuery? | console.* | DOMContentLoaded |
|------|------:|---:|---------|---------|---------|----------:|-----------------:|
| `order_form_simplified.js` | 2275 | 93.9 | Full order form logic: customer search (Select2), submission, progress, validation | `order_form.html` | **Heavy jQuery + Select2** | **76** | 1 |
| `order_items.js` | 331 | 13.8 | Order items table management (CRUD) | `order_form.html` | No | 4 | 1 |
| `contract_google_drive_upload.js` | 262 | 8.9 | Contract PDF upload to Google Drive | `order_form.html` | **jQuery** ($.ajax) | 2 | `$(document).ready` |
| `contract_upload_status_checker.js` | 221 | 8.8 | Polls upload status for contracts | `order_form.html` | No (fetch) | 12 | 1 |
| `complaints-quick-actions.js` | 709 | 30.2 | Complaints system: status update, escalation, assignment, notes | Complaints pages | No (fetch) | 8 | 1 |
| `debt_check.js` | 135 | 6.8 | Pre-scheduling debt verification dialog | `installations/dashboard.html`, `installation_list.html` | No (fetch + SweetAlert) | 2 | 1 |
| `installations.js` | 314 | 11.3 | Installation CRUD, payments, scheduling, file preview | Installation pages | No (fetch) | 5 | 1 |
| `inventory-dashboard.js` | 250 | 9.4 | Inventory charts (Chart.js), DataTable init | `inventory_base*.html` | **jQuery** (DataTable, fadeOut) | 2 | 1 |
| `download-helper.js` | 347 | 11.5 | Fetch-based file download helper class | Backup pages | No | **19** | 1 |
| `data-tables-config.js` | 177 | 7.0 | Centralized DataTables config + Arabic locale | Global (via `.datatable` class) | **jQuery** | 2 | `$(document).ready` |
| `form-validation.js` | 187 | 7.6 | Client-side form validation (`.needs-validation`) | Any page with validation | No (IIFE) | 0 | 1 |
| `device-manager.js` | 290 | 10.0 | Device fingerprinting (canvas, WebGL, audio), IndexedDB token storage | Auth pages | No | **18** | 0 (auto-init) |
| `apple-dark-icons.js` | 527 | 22.8 | Replace FontAwesome icons with emojis for Apple Dark theme | Triggered by theme | No | 0 | 1 |
| `script.js` | 77 | 2.3 | Bootstrap tooltips/popovers init, jQuery AJAX CSRF, SweetAlert toast helper | **Not included in any template** | **jQuery** | IIFE only |
| `theme-switcher.js` | 65 | 2.0 | Theme load/apply/save to server | **Not included in any template** | **jQuery** ($.ajax) | 2 |
| `animations.js` | 49 | 1.7 | Scroll animations (IntersectionObserver), button ripple, page transitions | **Not included in any template** | No | 0 | 1 |
| `datatables-arabic.js` | 18 | 0.7 | Pure JSON Arabic locale for DataTables | **Not included in any template** | N/A (JSON) | 0 |
| `theme-manager.js` | 0 | 0 | **EMPTY FILE** | None | N/A | 0 |
| `dashboard/core.js` | 11 | 0.4 | Sidebar toggle | `base_dashboard.html` | No | 0 | 1 |

---

## 2. Critical Issues Found

### 🔴 ISSUE #1: Triple Theme-Switching Implementation
Three files implement the **same** theme-switching functionality:

| File | What It Does | Loaded? |
|------|-------------|---------|
| **`main.js`** (111 lines) | Theme selector listener, save to localStorage + DB, chart/table refresh | ✅ `base.html` |
| **`theme-switcher.js`** (65 lines) | Theme selector listener, save to localStorage + DB | ❌ Not loaded |
| **`theme-manager.js`** (0 lines) | **Empty file** | ❌ Not loaded |

**Impact**: `main.js` runs on every page for 111 lines of code. `theme-switcher.js` is dead code. `theme-manager.js` is an empty skeleton.  
**Action**: Delete `theme-switcher.js` and `theme-manager.js`. Keep `main.js`.

---

### 🔴 ISSUE #2: 7× Duplicate `getCookie()` / CSRF Token Functions
The `getCookie('csrftoken')` function is implemented **independently** in 7 files:

1. **`csrf-handler.js`** — Full CSRF manager with fetch interceptor, jQuery ajaxSetup, periodic refresh, retry logic (293 lines)
2. **`script.js`** — `$.ajaxSetup({ headers: { 'X-CSRFToken': getCookie('csrftoken') } })`
3. **`installations.js`** — standalone `getCookie()` function
4. **`floating-button.js`** — standalone `getCookie()` function
5. **`complaints-quick-actions.js`** — `getCookie()` method on object
6. **`order_form_simplified.js`** — `getCSRFToken()` function (different name)
7. **`internal_messages_dropdown.js`** — `getCsrfToken()` method (reads from meta tag + input)

**Impact**: 7 different CSRF implementations across the codebase. `csrf-handler.js` already provides `window.CSRFHandler.getToken()` globally and intercepts both `fetch()` and `$.ajax()` — making all others redundant.  
**Action**: All files should use `CSRFHandler.getToken()` from `csrf-handler.js` instead of their own `getCookie()`.

---

### 🔴 ISSUE #3: Duplicate DataTables Arabic Locale (×3)
Arabic translations for DataTables appear in three places:

1. **`data-tables-config.js`** — Full Arabic locale + default config (177 lines)
2. **`datatables-arabic.js`** — Standalone Arabic JSON locale (18 lines, **not loaded anywhere**)
3. **`inventory-dashboard.js`** — Inline Arabic locale re-definition (within `initDataTables()`)

**Impact**: 3 copies of the same Arabic strings. If one is updated, the others go stale.  
**Action**: Delete `datatables-arabic.js`. Remove inline locale from `inventory-dashboard.js` and use `DataTablesConfig.getDefaultConfig()` from `data-tables-config.js` instead.

---

### 🔴 ISSUE #4: Duplicate Page Transition / Animation Logic
Two files implement competing page-load animations:

1. **`animations.js`** (49 lines) — IntersectionObserver scroll animations, button ripple effects, page transitions with 200ms delay  
2. **`smooth-navigation.js`** (271 lines) — Page transitions with 150ms delay, progressive load, anti-flicker CSS injection  
3. **`custom-theme-animations.js`** (120 lines) — Also adds scroll animations (competing with `animations.js`)

**Conflicts**:
- `animations.js` adds a 200ms page transition delay on link clicks. `smooth-navigation.js` adds a 150ms delay. Both intercept link clicks. If both load, user gets **both delays** (350ms+).
- Both `animations.js` and `smooth-navigation.js` set elements to `opacity: 0` then animate them in — if both run, elements may flash.
- `smooth-navigation.js` sets `document.body.style.opacity = '0'` at load time (line ~177) which causes a **visible flash of blank page**.

**Currently loaded**: Only `smooth-navigation.js` and `custom-theme-animations.js` via `base.html`. `animations.js` is dead code.  
**Action**: Delete `animations.js`. Consider simplifying `smooth-navigation.js` (271 lines is excessive for footer padding and opacity transitions).

---

### 🔴 ISSUE #5: `script.js` Duplicates `main.js` + `csrf-handler.js`
`script.js` (77 lines) provides:
- Bootstrap tooltip/popover init
- jQuery AJAX CSRF setup (duplicates `csrf-handler.js`)
- SweetAlert toast utility (`window.App.showToast`)

**Not loaded in any template**. The Bootstrap init it provides is already handled by Bootstrap's auto-initialization in production. The CSRF setup duplicates `csrf-handler.js`. The toast helper is unused.  
**Action**: Delete `script.js`.

---

### 🟡 ISSUE #6: `order_form_simplified.js` — 2,275 Lines / 94 KB
This is the **largest file** by far and contains:
- **76 console.log/warn/error statements** (largest source of console noise)
- Customer search with Select2 (AJAX)
- Multi-step progress indicator
- Form validation logic
- Order submission with duplicate-click protection
- File upload handling
- ~500 lines of CSS injected via Swal.fire HTML strings

**Problems**:
- Monolithic: mixes UI, validation, AJAX, and business logic
- Console statements are excessive for production (76 statements)
- Has its own `getCSRFToken()` instead of using the global `CSRFHandler`
- Inline CSS in JavaScript (should be in CSS files)

---

### 🟡 ISSUE #7: `smooth-navigation.js` — Anti-Pattern Code

```javascript
// Line ~177: Sets body opacity to 0 on EVERY page load
document.body.style.opacity = '0';

// Line ~155: Progressive load sets ALL containers/cards/tables/rows/cols to opacity 0
// then animates them in with staggered delays — on EVERY page load
const elements = document.querySelectorAll('.container-fluid, .card, .table, .row, .col');
elements.forEach((element, index) => {
    element.style.opacity = '0';  // Causes visible layout flash
    ...
    setTimeout(() => { element.style.opacity = '1'; }, index * 30);
});
```

This file also has a `adjustForMobile()` function that sets the **same CSS** for mobile, tablet, AND desktop:
```javascript
if (isMobile) {
    footer.style.position = 'relative';
    footer.style.bottom = '0';
} else if (isTablet) {
    footer.style.position = 'relative';  // Same!
    footer.style.bottom = '0';           // Same!
} else {
    footer.style.position = 'relative';  // Same!
    footer.style.bottom = '0';           // Same!
}
```

**Plus TWO resize listeners** for the same `adjustForMobile()` function (lines ~83 and ~87).

---

### 🟡 ISSUE #8: `apple-dark-icons.js` — Heavy MutationObserver
- 527 lines / 22.8 KB just to swap FontAwesome icons for emoji
- Uses a **global MutationObserver on `document.body`** that triggers `applyAppleIcons()` on EVERY DOM change (line ~28)
- The `addAppleAnimations()` function adds hover/click listeners to EVERY apple icon's parent, but without cleanup — listeners accumulate
- Only useful when `data-theme === 'apple-dark-mode'`

---

### 🟡 ISSUE #9: `floating-button.js` — 893 Lines of Dense Logic
Contains two completely separate systems:
1. **Draggable floating button** (lines 1–210, position management)
2. **Full mini-chat system** (lines 211–893, WebSocket, message history, typing indicators, read receipts, sound notifications)

These should be separate files. The chat system has its own `getCookie()` function (line ~861).

---

### 🟡 ISSUE #10: Polling on Installation Pages
`installations.js` has `setInterval(updateStats, 30000)` which polls `/installations/stats-api/` every 30 seconds on **every** installations page, even when user is on a detail page that doesn't have stats elements.

---

## 3. Dead / Unused Files

| File | Lines | Reason |
|------|------:|--------|
| **`theme-manager.js`** | 0 | Empty file |
| **`theme-switcher.js`** | 65 | Duplicated by `main.js`; not loaded in any template |
| **`animations.js`** | 49 | Duplicated by `smooth-navigation.js`; not loaded in any template |
| **`script.js`** | 77 | Duplicated by `csrf-handler.js` + `main.js`; not loaded in any template |
| **`datatables-arabic.js`** | 18 | Pure JSON; duplicated by `data-tables-config.js`; not loaded anywhere |

**Total dead code: 209 lines across 5 files**

---

## 4. Global Variable / Namespace Pollution

| File | Globals Created |
|------|----------------|
| `main.js` | `applyTheme()`, `addTransitionEffect()`, `updateComponentsOnThemeChange()`, `updateCharts()`, `updateTables()` |
| `floating-button.js` | `ChatManager`, `window.FloatingChat`, standalone `getCookie()` |
| `order_form_simplified.js` | `window.isSubmitting`, `window.submissionStartTime`, `window.progressInterval`, `window.currentCustomer`, `getCSRFToken()`, `showProgressIndicator()`, `hideProgressIndicator()`, `showSuccessMessage()`, `showErrorMessage()`, `toggleErrorDetails()`, `initializeCustomerSearch()`, many more |
| `order_items.js` | `window.orderItems`, `window.updateLiveOrderItemsTable`, `window.removeOrderItem`, `window.addOrderItem`, `window.calculateTotalAmount`, etc. |
| `installations.js` | `updateInstallationStatus()`, `addPayment()`, `completeInstallation()`, `searchInstallations()`, `refreshDailySchedule()`, `printDailySchedule()`, `showNotification()`, `getCookie()`, `updateStats()`, `previewFile()`, etc. |
| `download-helper.js` | `window.downloadHelper`, `window.downloadFile()`, `window.testDownload()` |
| `device-manager.js` | `window.DeviceManager` |
| `arabic-numbers-converter.js` | `window.convertArabicToEnglish` |
| `apple-dark-icons.js` | `window.AppleDarkIcons` |
| `complaints-quick-actions.js` | `window.ComplaintsQuickActions` (const) |
| `contract_google_drive_upload.js` | `contractUploadInProgress`, `currentOrderId`, `setCurrentOrderId()`, many `function` declarations |
| `csrf-handler.js` | `window.CSRFHandler` |
| `script.js` | `window.App` |

**Particularly bad**: `installations.js`, `order_form_simplified.js`, and `main.js` dump many functions directly into global scope without namespacing.

---

## 5. Console Statements Left in Production

| File | Count | Severity |
|------|------:|----------|
| `order_form_simplified.js` | **76** | 🔴 Very High |
| `download-helper.js` | 19 | 🟡 High |
| `device-manager.js` | 18 | 🟡 High |
| `contract_upload_status_checker.js` | 12 | 🟡 Medium |
| `csrf-handler.js` | 8 | 🟡 Medium |
| `floating-button.js` | 8 | 🟡 Medium |
| `complaints-quick-actions.js` | 8 | 🟡 Medium |
| `installations.js` | 5 | Low |
| `order_items.js` | 4 | Low |
| Others (<3 each) | ~13 | Low |
| **Total** | **~171** | |

---

## 6. jQuery vs Vanilla JS Inconsistency

Files using **jQuery**: `script.js`, `contract_google_drive_upload.js`, `data-tables-config.js`, `inventory-dashboard.js`, `theme-switcher.js`, `order_form_simplified.js` (Select2)

Files using **Vanilla JS only**: `animations.js`, `arabic-numbers-converter.js`, `complaints-quick-actions.js`, `csrf-handler.js` (also sets up jQuery), `custom-theme-animations.js`, `debt_check.js`, `device-manager.js`, `download-helper.js`, `floating-button.js`, `form-validation.js`, `installations.js`, `internal_messages_dropdown.js`, `main.js`, `order_items.js`, `smooth-navigation.js`

jQuery is loaded globally (via `base.html`), so all files CAN use it, but most choose not to — which is good. The inconsistency is primarily in AJAX calls: `$.ajax()` vs `fetch()`.

---

## 7. MutationObserver Overhead

**4 global MutationObservers** running simultaneously on `document.body`:

1. `apple-dark-icons.js` — Watches for ALL child additions, triggers icon re-application
2. `arabic-numbers-converter.js` — Watches for new input elements
3. `custom-theme-animations.js` — Watches ALL DOM changes, triggers animation re-application
4. `debt_check.js` — Watches for new scheduling buttons

These all fire on every DOM modification (e.g., dropdown opening, tooltip appearing, dynamic content loading). Combined with the AJAX polling in `internal_messages_dropdown.js` (every 60s) and `installations.js` (every 30s), this creates unnecessary overhead.

---

## 8. Recommended Actions

### Immediate Deletions (Zero Risk)
```
rm static/js/theme-manager.js      # Empty file
rm static/js/theme-switcher.js     # Dead code, duplicated by main.js
rm static/js/animations.js         # Dead code, duplicated by smooth-navigation.js
rm static/js/script.js             # Dead code, duplicated by csrf-handler.js
rm static/js/datatables-arabic.js  # Dead code, duplicated by data-tables-config.js
```

### High-Priority Fixes
1. **Remove 76 console.log from `order_form_simplified.js`** — Leaks debugging info in production
2. **Remove `document.body.style.opacity = '0'`** from `smooth-navigation.js` — Causes page flash
3. **Remove duplicate `getCookie()`** from `installations.js`, `floating-button.js`, `complaints-quick-actions.js`, `order_form_simplified.js`, `internal_messages_dropdown.js` — Use `CSRFHandler.getToken()` instead
4. **Remove duplicate DataTables Arabic locale** from `inventory-dashboard.js` — Use `DataTablesConfig.getDefaultConfig()`

### Medium-Priority Refactoring
1. **Split `floating-button.js`** into `floating-button.js` (drag logic, ~210 lines) and `mini-chat.js` (chat system, ~680 lines)
2. **Rewrite `smooth-navigation.js`** — Remove no-op `adjustForMobile()`, duplicate resize listeners, aggressive opacity manipulation. Target: <50 lines
3. **Conditionally load `apple-dark-icons.js`** — Only load when Apple Dark theme is selected (it's 23 KB of emoji mappings)
4. **Guard `installations.js` stats polling** — Only run `setInterval(updateStats, 30000)` if stats elements exist on page
5. **Strip all remaining console.* from production** — All 171 statements

### File Merge Candidates
| Merge Into | Files | Reasoning |
|------------|-------|-----------|
| `order-form-bundle.js` | `order_form_simplified.js` + `order_items.js` | Always loaded together, tightly coupled |
| `contract-upload.js` | `contract_google_drive_upload.js` + `contract_upload_status_checker.js` | Always loaded together, same domain |
| Remove `smooth-navigation.js` duties into `main.js` | `main.js` absorbs the 5-10 useful lines | 250+ lines of `smooth-navigation.js` are no-ops or harmful |

---

## 9. Summary Scorecard

| Metric | Value | Rating |
|--------|-------|--------|
| Dead files | 5 / 27 (18%) | 🔴 |
| Duplicate functionality instances | 14+ | 🔴 |
| Console statements in production | 171 | 🔴 |
| Global variable pollution | ~50+ globals | 🟡 |
| getCookie() implementations | 7 | 🔴 |
| Theme switching implementations | 3 | 🔴 |
| DataTables locale copies | 3 | 🟡 |
| MutationObservers on body | 4 | 🟡 |
| Largest file size | 94 KB (order_form) | 🟡 |
| jQuery vs Vanilla consistency | Mixed | 🟡 |
