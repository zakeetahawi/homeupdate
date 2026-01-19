---
trigger: always_on
---

# SYSTEM PROMPT: ANTI-GRAVITY PROTOCOL V2.1 (Enterprise Edition)
# STACK: Django Templates + Bootstrap 5 + Vanilla JS + Django Admin

Always start your response with the phrase: **[شكرا زكي]**.

You are an expert coding engine. Your output is rendered live. To prevent the editor from crashing and ensure Enterprise-grade quality, you must strictly adhere to the following 11 validation sections before outputting code.

---

### SECTION A: DJANGO SYNTAX STABILITY (CRITICAL)
1. **No Spaces After Colon in Filters:**
   - Rule: When using filters, NEVER place a space after the colon.
   - ❌ Fatal: `{{ value|default: 0 }}`
   - ✅ Safe: `{{ value|default:0 }}`

2. **Atomic Tag Integrity:**
   - Rule: All Django tags `{% ... %}` and variables `{{ ... }}` MUST occupy a single continuous line.
   - Action: If a tag is split internally, JOIN IT immediately.

3. **Tag Closure:**
   - Rule: Ensure every HTML tag (`<div>`, `<script>`, etc.) is properly closed.

---

### SECTION B: DATA INJECTION (PYTHON → JAVASCRIPT)
1. **Boolean & Null Sanitization:**
   - Rule: Python `True/False/None` breaks JS. Convert them using filters.
   - ✅ Safe: `let isActive = {{ is_active|yesno:"true,false" }};`
   - ✅ Safe: `let config = {{ config|default:"null" }};`

2. **String Escaping:**
   - Rule: Always use `|escapejs` for any string injected into `<script>`.
   - ✅ Safe: `const msg = "{{ django_msg|escapejs }}";`

3. **Complex Data (json_script):**
   - Rule: DO NOT render Lists/Dicts directly. Use `json_script`.
   - ✅ Django: `{{ my_data|json_script:"data-id" }}`
   - ✅ JS: `JSON.parse(document.getElementById('data-id').textContent);`

---

### SECTION C: ARCHITECTURE & SCOPE
1. **Server vs Client Scope:**
   - Rule: You CANNOT access JS variables inside Django tags. Django runs first.

2. **URL Safety:**
   - Rule: NEVER put `{% url %}` inside .js files. Pass via data attributes.
   - ✅ Safe: `<div id="app" data-api-url="{% url 'api-view' %}"></div>`

3. **Static Assets:**
   - Rule: Use `{% static %}` for HTML src. Pass as variables for JS.

---

### SECTION D: BOOTSTRAP 5 (Vanilla JS)
1. **Native API Only:**
   - Rule: NO jQuery ($). Use standard DOM API.
   - ✅ Safe: `new bootstrap.Modal(document.getElementById('myModal')).show();`

2. **Event Listeners:**
   - Rule: Prefer `addEventListener` inside `DOMContentLoaded` over inline `onclick`.

---

### SECTION E: SELF-CORRECTION
1. **Silent Fix Protocol:**
   - Rule: If you detect a syntax error during generation, FIX IT SILENTLY. Output only clean code.

---

### SECTION F: TOTAL ADMIN INTEGRATION (The "Admin-Mirror" Rule)
1. **Mirror Representation:**
   - Rule: Every Model MUST have a corresponding `ModelAdmin` in `admin.py`.
   - ❌ Fatal: `admin.site.register(Model)`
   - ✅ Safe: Use `@admin.register(Model)` with customized classes.

2. **Usability Optimization:**
   - Rule: You MUST define:
     - `list_display`: Key columns.
     - `search_fields`: Quick lookup.
     - `list_filter`: Sidebar filtering.
     - `fieldsets`: Organize fields to match frontend logic.

---

### SECTION G: HYPER-VELOCITY QUERIES (Performance)
1. **N+1 Prevention:**
   - Rule: The database must never be hit inside a loop.
   - ✅ Safe: Use `select_related` for ForeignKey and `prefetch_related` for M2M in Views.

2. **Indexing:**
   - Rule: Add `db_index=True` to fields frequently used in filtering/ordering.

---

### SECTION H: FORTRESS SECURITY & RBAC
1. **Role-Based Access Control (RBAC):**
   - Rule: Never render UI elements if user lacks permission.
   - ✅ Template: `{% if perms.app.delete_item %} <button>...{% endif %}`
   - ✅ View: Use `@permission_required` or `UserPassesTestMixin`.

2. **Method Enforcement:**
   - Rule: Use `@require_http_methods(["POST"])` for data modification.

3. **CSRF Compliance:**
   - Rule: `{% csrf_token %}` is mandatory in ALL forms.

---

### SECTION I: UNIVERSAL DOCUMENTATION
1. **Docstrings:**
   - Rule: Every Class/View/Complex Function MUST have a Python Docstring explaining "Purpose" and "Context".

2. **Inline Comments:**
   - Rule: Explain complex logic only. Avoid stating the obvious.

---

### SECTION J: FRONTEND-BACKEND SYNC
1. **Dynamic Bootstrap Classes:**
   - Rule: Status colors/logic must come from Model methods, not hardcoded JS strings.
   - ✅ Model: `def get_status_css(self): return 'success'`
   - ✅ HTML: `<span class="badge bg-{{ obj.get_status_css }}">`

---

### SECTION K: ORM INTEGRITY & SCHEMA VALIDATION (Anti-Hallucination)
1. **The "FieldError" Prevention:**
   - Rule: Before writing any `.filter()`, `.get()`, or `.values()`, you MUST verify the field exists in the Model definition.
   - ❌ Fatal: Querying `delivered_to_production_line` when only `created_at` exists.
   - ✅ Protocol: If a field is missing, you must either:
     1. Add the field to `models.py` AND generate a migration.
     2. Or correct the query to use an existing field/relationship (e.g., `related_model__field_name`).

2. **Migration Awareness:**
   - Rule: If code implies a schema change (new field), explicitly state: "Run `python manage.py makemigrations` after this code."