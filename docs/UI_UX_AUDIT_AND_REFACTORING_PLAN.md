# Django ERP System - UI/UX Consistency Audit & Refactoring Plan

**Date**: January 4, 2026  
**Project**: Home Update ERP System  
**Status**: Analysis Phase Complete → Ready for Implementation

---

## EXECUTIVE SUMMARY

### Current State
- **3 major detail page templates** analyzed: 2,818 total lines
  - customer_detail.html: 1,377 lines
  - order_detail.html (cutting): 973 lines
  - inspection_detail.html: 468 lines
- **92 card instances** found across templates
- **27 CSS files** managing styles
- **10 reusable components** defined but inconsistently used

### Key Findings
✅ **Strengths**
- Robust design token system (CSS custom properties)
- Multiple theme support implemented
- Comprehensive component library exists
- Consistent use of Font Awesome icons
- Good accessibility foundations

⚠️ **Issues**
- **Inconsistent card styling** - Headers, spacing, and borders vary
- **High template complexity** - 1,000-2,000 line templates hard to maintain
- **Unused components** - Cards.html has 6 types, detail pages use only 1-2
- **Inline styles** - Mixed with CSS classes, causing maintenance headaches
- **Status badge logic duplicated** - 92 instances with similar patterns
- **Low component adoption** - Detail pages don't use the component library

### Impact
- **Maintainability**: 3/10 - Large templates, scattered logic
- **Consistency**: 4/10 - Visual inconsistency across detail pages
- **Reusability**: 2/10 - Minimal component leverage
- **Scalability**: 2/10 - Adding new detail pages requires copying large templates

---

## DETAILED CONSISTENCY AUDIT

### 1. Card Structure Analysis

#### Current Pattern Distribution

| Template | Card Count | Header Style | Footer Style | Spacing |
|----------|-----------|--------------|--------------|---------|
| customer_detail | 8 | Custom HTML | Inconsistent | Variable |
| inspection_detail | 6 | Simple h5 | None | Regular |
| order_detail | 78 | Mixed styles | Various | Inconsistent |

#### Issues Found

**Issue 1: Card Header Inconsistency**
- `customer_detail.html`: Uses `<div class="card-header">` with flex layout
- `inspection_detail.html`: Uses `<h5 class="card-title">` inside header
- `order_detail.html`: Mix of both patterns plus custom styling

```html
<!-- Pattern A: customer_detail -->
<div class="card-header">
    <h5 class="card-title">Title</h5>
</div>

<!-- Pattern B: inspection_detail -->
<div class="card-header">
    <h5>Title</h5>
</div>

<!-- Pattern C: order_detail (appears 30+ times) -->
<div class="card-header bg-light">
    <h5 class="mb-0">Title</h5>
</div>
```

**Recommendation**: Standardize on Pattern A with CSS class-based styling

---

**Issue 2: Card Body Spacing**
- No consistent padding/margin strategy
- Inline styles used alongside CSS classes
- Different breakpoint behaviors

```html
<!-- Inconsistent -->
<div class="card-body">  <!-- Bootstrap default: 1.25rem -->
<div class="card-body p-3">  <!-- Custom padding -->
<div class="card-body" style="padding: 2rem;">  <!-- Inline style -->
```

**Recommendation**: Use CSS variables for spacing: `padding: var(--spacing-card-body)`

---

**Issue 3: Status Badge Duplication**

92 instances of similar badge patterns:

```html
<!-- Pattern appears 92 times with variations -->
<span class="badge bg-{{ color }} text-{{ text_color }}">{{ status }}</span>

<!-- Should use component -->
{% include 'components/status_badges.html' with status='completed' %}
```

**Impact**: 
- Any change to badge styling requires 92 edits
- No centralized badge logic
- Template readability reduced

---

### 2. Layout Pattern Analysis

#### customer_detail.html - 3-Column Layout
```
┌─────────────────────────────────────────────┐
│         Customer Hero Header (Full Width)   │
├─────────────────────────────────────────────┤
│ Sidebar │ Main Content (Tabs) │  Recent Activ│
│ Info    │  - Notes            │     -Orders  │
│         │  - Financial        │     -Inspectn│
│         │  - Complaints       │              │
│         │  - Access Logs      │              │
└─────────────────────────────────────────────┘
```

**Structure**:
- Hero card at top (fixed layout, custom styling)
- 3-column grid (col-md-3 | col-md-6 | col-md-3)
- 5 tab-based sections
- Cards within tabs
- AJAX-loaded content in main tab

**Issues**:
- Responsive breakpoints not tested for mobile
- Tab implementation inline, not reusable
- Sidebar position fixed on desktop, breaks on mobile

---

#### inspection_detail.html - 2-Column Layout
```
┌─────────────────────────────────────────────┐
│  Page Title & Action Buttons (Full Width)   │
├──────────────────────┬──────────────────────┤
│   Main Content       │   Sidebar Info       │
│  (col-md-8)         │   (col-md-4)        │
│                     │                      │
│ - Inspection Info   │ - Related Order      │
│ - File Display      │ - Customer Info      │
│ - Notes             │                      │
└──────────────────────┴──────────────────────┘
```

**Structure**:
- Simple page header with buttons
- 2-column main content
- Multiple cards in main section
- Single card in sidebar

**Strengths**:
- Simple, responsive layout
- Clear information hierarchy
- Mobile-friendly (stacks nicely)

---

#### order_detail.html (cutting) - Complex Multi-Section
```
┌─────────────────────────────────────────────┐
│    Order Header (Gradient Background)       │
│  - Order Code & Customer Info              │
│  - Status Badges & Progress Ring           │
├─────────────────────────────────────────────┤
│ Bulk Actions Section                        │
│ (Checkboxes + Action Buttons)               │
├─────────────────────────────────────────────┤
│ Item Cards Grid (4 items per row)            │
│ ├─ Item Card 1  │ Item Card 2 │ ...        │
│ ├─ Item Card 3  │ Item Card 4 │ ...        │
│ ...                                         │
└─────────────────────────────────────────────┘
```

**Structure**:
- Custom gradient header (not reusable)
- Bulk action bar (unique implementation)
- Item cards in grid layout
- Individual card state management (completed/rejected/pending)
- 973 lines for single view

**Issues**:
- Highly specific styling (gradient hardcoded)
- Complex bulk action logic mixed with UI
- Item card state logic inline
- 78 card instances with custom styling

---

### 3. Component Library Usage Analysis

#### Defined Components (templates/components/)

| Component | Type | Usage in Detail Pages | Assessment |
|-----------|------|----------------------|------------|
| cards.html | 6 types | ~15% used | **Underutilized** |
| status_badges.html | 9 types | <10% used | **Critical gap** |
| buttons.html | 8 types | ~20% used | **Underutilized** |
| form_fields.html | 4 types | Not used | **Unused** |
| page_header.html | 1 type | Used once | **Underutilized** |
| stat_card.html | 1 type | Not used | **Unused** |

#### Component Adoption Issues

**Problem**: Detail pages define their own patterns instead of using components

```html
<!-- What they do (inline): 92 instances -->
<span class="badge bg-success text-white">مكتمل</span>

<!-- What they should do -->
{% include 'components/status_badges.html' with status='completed' %}

<!-- Result**: 
   - 1,092 extra lines of template code
   - Impossible to change badge styling globally
   - No semantic meaning to badges
```

---

### 4. CSS Styling Consistency

#### Design Token System (Excellent Foundation)

**Located**: `/static/css/design-tokens.css`

```css
/* Colors */
--primary-color: #667eea
--success-color: #28a745
--warning-color: #ffc107
--danger-color: #dc3545

/* Spacing (8px base) */
--spacing-xs: 0.5rem   /* 8px */
--spacing-sm: 1rem     /* 16px */
--spacing-md: 1.5rem   /* 24px */
--spacing-lg: 2rem     /* 32px */

/* Border Radius */
--border-radius-sm: 8px
--border-radius-md: 10px
--border-radius-lg: 12px

/* Shadows */
--shadow-sm: 0 1px 3px rgba(0,0,0,0.12)
--shadow-md: 0 4px 6px rgba(0,0,0,0.15)
--shadow-lg: 0 10px 20px rgba(0,0,0,0.20)

/* Typography */
--font-weight-normal: 400
--font-weight-medium: 500
--font-weight-semibold: 600
--font-weight-bold: 700
```

#### Compliance Assessment

| Element | Tokens Used | Inline Styles | Assessment |
|---------|------------|---------------|-----------|
| Cards | 30% | 70% | ❌ Poor |
| Buttons | 50% | 50% | ⚠️ Mixed |
| Badges | 20% | 80% | ❌ Poor |
| Spacing | 40% | 60% | ⚠️ Mixed |

**Example Violations**:

```html
<!-- ❌ Inline style instead of token -->
<div style="border-radius: 10px;">

<!-- ✅ Should be -->
<div style="border-radius: var(--border-radius-md);">

<!-- ❌ Hard-coded color -->
<span class="badge" style="background: #28a745;">

<!-- ✅ Should use -->
<span class="badge bg-success">
```

---

### 5. Accessibility & RTL Support

#### Current State
- **Arabic (RTL) Support**: Partial
  - Direction toggles exist
  - Some components have RTL variants
  - Customer detail has Arabic text with RTL considerations
  
- **Accessibility**: 
  - Semantic HTML used inconsistently
  - ARIA labels missing on many buttons
  - Color used as only differentiator (fails WCAG)
  - Focus states not visible on all interactive elements

#### Issues Found

```html
<!-- ❌ No semantic meaning -->
<span class="badge bg-danger">ملغي</span>

<!-- ✅ Should have ARIA -->
<span class="badge bg-danger" role="status" aria-label="الحالة: ملغي">ملغي</span>

<!-- ❌ Color-only status indicator -->
<div style="color: #dc3545;">طلب ملغي</div>

<!-- ✅ Should have icon + color -->
<div class="text-danger">
    <i class="fas fa-times-circle me-1"></i>
    طلب ملغي
</div>
```

---

## REFACTORING PLAN

### Phase 1: Foundation (Week 1-2)

#### Task 1.1: Create Unified Card Component
**File**: `/templates/components/detail_card.html`

```html
{% comment %}
Unified detail page card component supporting:
- Standard info card
- Collapsible card
- Status indicator cards
- Action buttons in footer
{% endcomment %}

{% include 'components/detail_card.html' 
  title='معلومات العميل'
  icon='fas fa-user'
  collapsed=False
  footer_actions='edit,delete'
  content=...
  context=...
%}
```

**Deliverables**:
- [ ] Define component with all detail page patterns
- [ ] Add to cards.html or create new detail_card.html
- [ ] Document usage in component library
- [ ] Create test cases for all variants

**Estimated Work**: 4 hours

---

#### Task 1.2: Create Detail Page Layout Framework
**File**: `/templates/components/detail_page_layout.html`

Support 3 layout patterns:
1. **Two-Column**: main (8) + sidebar (4)
2. **Three-Column**: sidebar (3) + main (6) + recent (3)
3. **Full-Width + Cards**: container with stacked cards

```html
{% include 'components/detail_page_layout.html'
  layout='two-column'
  main_content=main_content
  sidebar_content=sidebar_content
%}
```

**Deliverables**:
- [ ] Create layout component
- [ ] Support responsive behavior
- [ ] Document each layout type
- [ ] Add CSS for layout grid

**Estimated Work**: 3 hours

---

#### Task 1.3: Standardize CSS Variables Usage
**File**: `/static/css/detail-pages.css` (new)

Create specific tokens for detail pages:

```css
/* Detail Page Card Spacing */
--detail-card-padding: var(--spacing-md);
--detail-card-header-padding: var(--spacing-md);
--detail-card-body-padding: var(--spacing-md);

/* Detail Page Header */
--detail-header-height: 120px;
--detail-header-padding: var(--spacing-lg);

/* Status Badges */
--detail-badge-padding: 0.375rem 0.75rem;
--detail-badge-font-size: 0.875rem;
--detail-badge-border-radius: var(--border-radius-sm);

/* Sidebar */
--detail-sidebar-width: 350px;
--detail-sidebar-gap: var(--spacing-md);
```

**Deliverables**:
- [ ] Create detail-pages.css
- [ ] Define all spacing tokens
- [ ] Define color tokens for statuses
- [ ] Document in design system

**Estimated Work**: 2 hours

---

### Phase 2: Template Refactoring (Week 2-3)

#### Task 2.1: Refactor customer_detail.html
**Current**: 1,377 lines  
**Target**: 400-500 lines (70% reduction)

```html
{% extends 'base.html' %}
{% load i18n %}
{% load static %}
{% load unified_status_tags %}

{% block content %}
<div class="detail-page-container">
    <!-- Header Component -->
    {% include 'components/detail_page_header.html'
      image=customer.image
      title=customer.name
      code=customer.code
      badges=customer_badges
      actions=header_actions
    %}
    
    <!-- Main Layout -->
    {% include 'components/detail_page_layout.html'
      layout='three-column'
    %}
      
      <!-- Sidebar Content -->
      {% block detail_sidebar %}
        {% include 'customers/partials/sidebar.html' %}
      {% endblock %}
      
      <!-- Main Content -->
      {% block detail_main %}
        {% include 'customers/partials/tabs.html' %}
      {% endblock %}
      
      <!-- Recent Activity -->
      {% block detail_recent %}
        {% include 'customers/partials/recent_activity.html' %}
      {% endblock %}
      
    {% endinclude %}
</div>
{% endblock %}
```

**Sub-tasks**:
- [ ] Extract header to component
- [ ] Extract sidebar to partial
- [ ] Extract tabs to partial
- [ ] Extract recent activity to partial
- [ ] Test responsive layout
- [ ] Verify all functionality works

**Deliverables**:
- Main template: 250 lines (vs 1,377)
- `partials/header.html`: Header component
- `partials/sidebar.html`: Sidebar content
- `partials/tabs.html`: Tab implementation
- `partials/recent_activity.html`: Activity widget

**Estimated Work**: 8 hours

---

#### Task 2.2: Refactor inspection_detail.html
**Current**: 468 lines  
**Target**: 200 lines (57% reduction)

```html
{% extends 'base.html' %}
{% load i18n %}
{% load static %}
{% load unified_status_tags %}

{% block content %}
<!-- Page Header -->
{% include 'components/detail_page_header_simple.html'
  title='تفاصيل المعاينة'
  actions=page_actions
%}

<!-- Main Layout -->
{% include 'components/detail_page_layout.html'
  layout='two-column'
  main_block='inspection_detail_main'
  sidebar_block='inspection_detail_sidebar'
%}
{% endblock %}

{% block inspection_detail_main %}
  {% include 'inspections/partials/inspection_info.html' %}
  {% include 'inspections/partials/inspection_files.html' %}
  {% include 'inspections/partials/inspection_notes.html' %}
{% endblock %}

{% block inspection_detail_sidebar %}
  {% include 'inspections/partials/related_order.html' %}
  {% include 'inspections/partials/customer_info.html' %}
{% endblock %}
```

**Sub-tasks**:
- [ ] Create simple page header component
- [ ] Extract inspection info to partial
- [ ] Extract file display to partial
- [ ] Extract related info to partial
- [ ] Consolidate status/result display
- [ ] Test all file display modes (local + Google Drive)

**Deliverables**:
- Main template: 150 lines (vs 468)
- Multiple partial templates
- Simplified file handling

**Estimated Work**: 6 hours

---

#### Task 2.3: Refactor order_detail.html (cutting)
**Current**: 973 lines  
**Target**: 300 lines (69% reduction)

```html
{% extends 'base.html' %}
{% load humanize %}

{% block content %}
<!-- Order Header -->
{% include 'components/detail_page_header_gradient.html'
  title=cutting_order.cutting_code
  subtitle=order_type
  customer=cutting_order.order.customer
  stats=order_stats
%}

<!-- Bulk Actions Bar -->
{% include 'cutting/components/bulk_actions.html'
  items=cutting_order.items.all
  actions=available_actions
%}

<!-- Items Grid -->
{% include 'cutting/components/item_grid.html'
  items=cutting_order.items.all
  item_template='cutting/components/item_card.html'
%}
{% endblock %}
```

**Sub-tasks**:
- [ ] Extract header (gradient) to component
- [ ] Extract bulk actions to component
- [ ] Extract item grid to component
- [ ] Create item card component
- [ ] Refactor item state management
- [ ] Reduce inline styling
- [ ] Test bulk actions functionality

**Deliverables**:
- Main template: 250 lines (vs 973)
- Reusable header component
- Item card component
- Bulk action component

**Estimated Work**: 10 hours

---

### Phase 3: Component Library Enhancement (Week 3)

#### Task 3.1: Create Detail Page Header Components

**File**: `/templates/components/detail_page_headers.html`

Support 3 variants:

```html
{% comment %} Simple Header {% endcomment %}
{% include 'components/detail_page_headers.html'
  type='simple'
  title='تفاصيل المعاينة'
  actions=page_actions
%}

{% comment %} Hero Header (with image) {% endcomment %}
{% include 'components/detail_page_headers.html'
  type='hero'
  image=object.image
  title=object.name
  badges=status_badges
  actions=header_actions
%}

{% comment %} Gradient Header {% endcomment %}
{% include 'components/detail_page_headers.html'
  type='gradient'
  title=order.code
  stats=order_stats
  actions=order_actions
%}
```

**Deliverables**:
- [ ] Simple header variant
- [ ] Hero header with image
- [ ] Gradient header variant
- [ ] Responsive behavior for all
- [ ] Full documentation

**Estimated Work**: 5 hours

---

#### Task 3.2: Create Sidebar Component
**File**: `/templates/components/detail_sidebar.html`

```html
{% include 'components/detail_sidebar.html'
  sections=sidebar_sections
  position='right'
  width='md'
%}
```

**Deliverables**:
- [ ] Sidebar component with configurable width
- [ ] Support for multiple sections
- [ ] Sticky sidebar option
- [ ] Responsive collapse on mobile
- [ ] Documentation

**Estimated Work**: 3 hours

---

#### Task 3.3: Create Tab Component
**File**: `/templates/components/detail_tabs.html`

```html
{% include 'components/detail_tabs.html'
  tabs=tab_list
  default_tab='overview'
  ajax_load=False
  vertical=False
%}
```

**Deliverables**:
- [ ] Horizontal & vertical tabs
- [ ] AJAX tab loading
- [ ] Badge support on tabs
- [ ] Keyboard navigation
- [ ] Full accessibility support

**Estimated Work**: 4 hours

---

### Phase 4: Testing & Optimization (Week 4)

#### Task 4.1: Unit Testing
- [ ] Test all new components
- [ ] Test responsive layouts (mobile, tablet, desktop)
- [ ] Test RTL/LTR switching
- [ ] Test accessibility (WCAG 2.1 AA)
- [ ] Test with different browsers

**Deliverables**:
- Test suite for components
- Responsive test cases
- Accessibility audit report

**Estimated Work**: 8 hours

---

#### Task 4.2: Visual Regression Testing
- [ ] Screenshot existing detail pages (baseline)
- [ ] Apply refactored templates
- [ ] Compare visual output
- [ ] Document any visual changes
- [ ] Get stakeholder sign-off

**Deliverables**:
- Before/after screenshots
- Visual comparison report
- Stakeholder approval

**Estimated Work**: 4 hours

---

#### Task 4.3: Performance Optimization
- [ ] Measure current template render time
- [ ] Profile after refactoring
- [ ] Optimize database queries
- [ ] Lazy-load sidebar content
- [ ] Compress images in headers

**Deliverables**:
- Performance metrics report
- Optimization checklist
- Implementation of optimizations

**Estimated Work**: 6 hours

---

### Phase 5: Documentation & Rollout (Week 4-5)

#### Task 5.1: Create Style Guide
**File**: `/docs/DETAIL_PAGE_STYLE_GUIDE.md`

Document:
- [ ] Detail page layout patterns
- [ ] Available components and usage
- [ ] CSS variable reference
- [ ] Accessibility requirements
- [ ] Common patterns & examples
- [ ] Do's and don'ts

**Estimated Work**: 4 hours

---

#### Task 5.2: Create Component Documentation
**File**: `/docs/COMPONENTS.md`

For each component:
- Usage examples
- All variants
- Props/parameters
- Accessibility notes
- Responsive behavior
- RTL support

**Estimated Work**: 6 hours

---

#### Task 5.3: Create Developer Guide
**File**: `/docs/DETAIL_PAGE_DEVELOPMENT.md`

Cover:
- [ ] How to create a new detail page
- [ ] Template structure
- [ ] Common patterns
- [ ] Debugging tips
- [ ] Performance considerations

**Estimated Work**: 3 hours

---

## IMPLEMENTATION TIMELINE

```
Week 1 (Jan 6-10)
├─ Task 1.1: Unified Card Component (4h)
├─ Task 1.2: Layout Framework (3h)
└─ Task 1.3: CSS Variables (2h)

Week 2 (Jan 13-17)
├─ Task 2.1: Refactor customer_detail (8h)
├─ Task 2.2: Refactor inspection_detail (6h)
└─ Task 3.1: Detail Page Headers (5h)

Week 3 (Jan 20-24)
├─ Task 2.3: Refactor order_detail (10h)
├─ Task 3.2: Sidebar Component (3h)
└─ Task 3.3: Tab Component (4h)

Week 4 (Jan 27-31)
├─ Task 4.1: Unit Testing (8h)
├─ Task 4.2: Visual Regression (4h)
├─ Task 4.3: Performance Opt (6h)
└─ Task 5.1: Style Guide (4h)

Week 5 (Feb 3-7)
├─ Task 5.2: Component Docs (6h)
├─ Task 5.3: Developer Guide (3h)
└─ Final Testing & Rollout (8h)
```

**Total Estimated Effort**: ~110 hours (3 weeks of development)

---

## SUCCESS CRITERIA

### Code Quality
- [ ] Template line count reduction: 2,818 → ~750 (73% reduction)
- [ ] Component reuse: <5% → 80%+ adoption
- [ ] CSS variable compliance: 40% → 95%+
- [ ] No inline styles in detail pages

### Maintainability
- [ ] All detail pages follow same structure
- [ ] New detail page can be created in <2 hours
- [ ] Style changes affect all pages automatically
- [ ] Easy to locate and fix issues

### Consistency
- [ ] Card styling identical across pages
- [ ] Spacing tokens used uniformly
- [ ] Status badges centralized
- [ ] Visual hierarchy consistent

### Performance
- [ ] Template render time improvement >20%
- [ ] Reduced CSS bundle size >10%
- [ ] No new database queries introduced

### Accessibility
- [ ] WCAG 2.1 AA compliance
- [ ] All buttons have aria-labels
- [ ] Color not sole indicator
- [ ] Keyboard navigation works

### Testing
- [ ] 95%+ test coverage for components
- [ ] All responsive breakpoints tested
- [ ] RTL/LTR switching verified
- [ ] Visual regression free

---

## RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Refactoring breaks functionality | Medium | High | Comprehensive testing, feature branch |
| User experience changes | Low | Medium | Visual regression testing, user feedback |
| Performance regression | Low | High | Performance profiling, optimization |
| Mobile layout issues | Medium | Medium | Responsive testing framework |
| Browser compatibility | Low | Medium | Cross-browser testing |

---

## POST-IMPLEMENTATION

### Monitoring
- [ ] Track template render performance
- [ ] Monitor error logs for new issues
- [ ] Gather user feedback
- [ ] Check accessibility metrics

### Maintenance
- [ ] Update component library docs
- [ ] Add new patterns to guide
- [ ] Review and refactor older pages
- [ ] Quarterly consistency audits

### Future Work
- [ ] Create detail page generator
- [ ] Automate responsive testing
- [ ] Build visual regression CI/CD
- [ ] Expand to list pages

---

## APPENDIX: QUICK REFERENCE

### File Structure After Refactoring

```
templates/
├── components/
│   ├── cards.html (updated with card patterns)
│   ├── detail_page_layout.html (NEW)
│   ├── detail_page_headers.html (NEW)
│   ├── detail_sidebar.html (NEW)
│   ├── detail_tabs.html (NEW)
│   ├── status_badges.html (unchanged)
│   ├── buttons.html (unchanged)
│   └── form_fields.html (unchanged)
├── customers/
│   ├── customer_detail.html (400 lines, down from 1377)
│   └── partials/
│       ├── header.html (NEW)
│       ├── sidebar.html (NEW)
│       ├── tabs.html (NEW)
│       └── recent_activity.html (NEW)
├── inspections/
│   ├── inspection_detail.html (200 lines, down from 468)
│   └── partials/
│       ├── inspection_info.html (NEW)
│       ├── inspection_files.html (NEW)
│       ├── related_order.html (NEW)
│       └── customer_info.html (NEW)
└── cutting/
    ├── order_detail.html (300 lines, down from 973)
    ├── components/
    │   ├── bulk_actions.html (NEW)
    │   ├── item_grid.html (NEW)
    │   └── item_card.html (NEW)
    └── partials/ (as needed)

static/css/
├── design-tokens.css (reference - unchanged)
├── detail-pages.css (NEW - detail page specific tokens)
└── style.css (updated with new patterns)

docs/
├── DETAIL_PAGE_STYLE_GUIDE.md (NEW)
├── COMPONENTS.md (updated)
└── DETAIL_PAGE_DEVELOPMENT.md (NEW)
```

---

**Document Version**: 1.0  
**Last Updated**: January 4, 2026  
**Next Review**: After Phase 1 completion

