# دليل قسم المبيعات الخارجية — External Sales Module

> آخر تحديث: مارس 2026

---

## 📋 نظرة عامة

قسم المبيعات الخارجية هو وحدة جديدة في نظام الخواجة ERP مصممة لإدارة العلاقات مع شركاء المبيعات الخارجيين. القسم مبني بهيكل قابل للتوسع يدعم عدة أقسام فرعية، حالياً يعمل "قسم مهندسي الديكور" بالكامل.

### الأقسام الفرعية

| القسم | الحالة | الوصف |
|-------|--------|-------|
| **مهندسي الديكور** | ✅ مكتمل | إدارة مهندسي الديكور، المتابعات، العمولات |
| **البيع بالجملة** | 🔜 قريباً | إدارة عملاء الجملة والتجار |
| **المشاريع** | 🔜 قريباً | إدارة المشاريع الحكومية والخاصة |

---

## 🏗️ البنية التقنية

### الملفات الأساسية

```
external_sales/
├── models.py              # 5 نماذج بيانات
├── views_decorator.py     # 29 View (داشبورد، CRUD، API، تصدير/استيراد)
├── views.py               # صفحة الفهرس الرئيسية
├── urls.py                # 27 URL pattern
├── forms.py               # نماذج الإدخال
├── signals.py             # 6 إشارات (إنشاء تلقائي، تدقيق، كاش)
├── mixins.py              # صلاحيات الوصول
├── utils.py               # أدوات مساعدة
├── admin.py               # إعدادات Django Admin
├── apps.py                # تكوين التطبيق
├── management/
│   └── commands/
│       └── create_decorator_profiles.py  # أمر إنشاء بروفايلات
├── migrations/
│   └── 0001_initial.py
└── templates/
    └── external_sales/
        ├── base_dept.html           # القالب الأساسي للقسم
        ├── index.html               # الصفحة الرئيسية
        ├── decorator/
        │   ├── dashboard.html       # لوحة التحكم الرئيسية
        │   ├── engineer_list.html   # قائمة المهندسين
        │   ├── engineer_detail.html # تفاصيل المهندس
        │   ├── engineer_form.html   # إنشاء/تعديل مهندس
        │   ├── contact_log_form.html    # تسجيل تواصل
        │   ├── contact_log_list.html    # سجل التواصل
        │   ├── commissions.html         # إدارة العمولات
        │   ├── decorator_orders.html    # الطلبات المرتبطة
        │   ├── link_customer_form.html  # ربط عميل (AJAX)
        │   ├── link_order_form.html     # ربط طلب (AJAX)
        │   ├── material_form.html       # إضافة خامة مفضلة
        │   └── import_engineers.html    # استيراد من Excel
        └── partials/
            ├── engineer_card.html       # كارت مهندس
            ├── stats_cards.html         # بطاقات إحصائيات
            └── contact_timeline.html    # خط زمني للتواصل
```

### النماذج (Models)

#### 1. `DecoratorEngineerProfile` — ملف مهندس الديكور
النموذج الأساسي، مرتبط بـ `Customer` (OneToOne) حيث `customer_type='designer'`.

| الحقل | النوع | الوصف |
|-------|-------|-------|
| `customer` | OneToOneField → Customer | العميل (المهندس) |
| `designer_code` | CharField | كود فريد تلقائي `DEC-XXXX` |
| `company_office_name` | CharField | اسم المكتب/الشركة |
| `years_of_experience` | PositiveSmallIntegerField | سنوات الخبرة |
| `area_of_operation` | CharField | منطقة العمل |
| `city` | CharField | المدينة (مفهرس) |
| `instagram_handle` | CharField | حساب Instagram |
| `portfolio_url` | URLField | رابط المعرض |
| `linkedin_url` | URLField | رابط LinkedIn |
| `price_segment` | CharField | الشريحة السعرية: اقتصادي/متوسط/فاخر |
| `design_style` | CharField | أسلوب التصميم |
| `preferred_colors` | TextField | الألوان المفضلة |
| `project_types` | JSONField | أنواع المشاريع (سكني/تجاري/ضيافة/متعدد) |
| `interests_notes` | TextField | اهتمامات وتفضيلات |
| `internal_notes` | TextField | ملاحظات داخلية للقسم فقط |
| `priority` | CharField | الأولوية: VIP/نشط/عادي/فاتر |
| `assigned_staff` | ForeignKey → User | موظف المتابعة |
| `last_contact_date` | DateField | آخر تواصل (يُحدث تلقائياً) |
| `last_order_date` | DateField | آخر طلب (يُحدث تلقائياً) |
| `next_followup_date` | DateField | موعد المتابعة القادمة (تلقائي) |
| `total_clients_count` | PositiveIntegerField | عدد العملاء (cache) |
| `total_orders_count` | PositiveIntegerField | عدد الطلبات (cache) |

**الصلاحيات المخصصة:**
- `view_decorator_profiles` — عرض ملفات المهندسين
- `manage_decorator_profiles` — إدارة ملفات المهندسين
- `view_decorator_commissions` — عرض بيانات العمولات
- `manage_decorator_commissions` — إدارة العمولات

#### 2. `EngineerLinkedCustomer` — العملاء المرتبطون
ربط عملاء أفراد بمهندس الديكور (العملاء الذين أحالهم المهندس).

| الحقل | الوصف |
|-------|-------|
| `engineer` | FK → DecoratorEngineerProfile |
| `customer` | FK → Customer |
| `relationship_type` | عميل أحاله المهندس / مشروع المهندس |
| `default_commission_rate` | نسبة العمولة الافتراضية % |
| `is_active` | حالة الربط |

> **ملاحظة**: عند ربط طلب بمهندس، يتم ربط عميل الطلب تلقائياً بنفس المهندس.

#### 3. `EngineerLinkedOrder` — الطلبات المرتبطة والعمولات
ربط طلبات محددة بمهندس مع نظام إدارة عمولات كامل.

| الحقل | الوصف |
|-------|-------|
| `engineer` | FK → DecoratorEngineerProfile |
| `order` | OneToOneField → Order |
| `link_type` | يدوي / تلقائي |
| `commission_type` | نسبة مئوية / مبلغ ثابت |
| `commission_rate` | نسبة العمولة % |
| `commission_value` | قيمة العمولة (محسوبة أو يدوية) |
| `commission_status` | معلقة → معتمدة → مدفوعة / ملغاة |
| `commission_paid_at` | تاريخ الدفع |
| `commission_paid_by` | دُفعت بواسطة |

**دورة حياة العمولة:**
```
معلقة (pending) → معتمدة (approved) → مدفوعة (paid)
                                      → ملغاة (cancelled)
```

#### 4. `EngineerContactLog` — سجل التواصل
تتبع كل تواصل مع المهندس مع جدولة المتابعات.

| الحقل | الوصف |
|-------|-------|
| `contact_type` | مكالمة/واتساب/اجتماع/موعد/بريد/زيارة/أخرى |
| `outcome` | رد/لم يرد/مشغول/تم حجز موعد/مهتم/غير مهتم/... |
| `next_followup_date` | موعد المتابعة القادمة |
| `appointment_datetime` | تاريخ الموعد (إن وُجد) |
| `appointment_location` | مكان الموعد |
| `appointment_confirmed` | تأكيد الموعد |

#### 5. `EngineerMaterialInterest` — اهتمامات الخامات
الخامات والأقمشة التي يفضلها كل مهندس وعدد مرات طلبها.

---

### الإشارات (Signals)

| الإشارة | المُحفِّز | الوظيفة |
|---------|----------|---------|
| `auto_create_decorator_profile` | حفظ Customer بنوع `designer` | إنشاء بروفايل تلقائي + إشعار للمدراء |
| `audit_decorator_profile` | حفظ DecoratorEngineerProfile | تسجيل في سجل التدقيق |
| `audit_commission_change` | تحديث EngineerLinkedOrder | تسجيل تغيير حالة العمولة |
| `update_profile_contact_cache` | حفظ EngineerContactLog | تحديث `last_contact_date` و `next_followup_date` |
| `update_profile_order_cache` | حفظ EngineerLinkedOrder | تحديث `last_order_date` و `total_orders_count` |
| `update_profile_customer_cache` | حفظ EngineerLinkedCustomer | تحديث `total_clients_count` |

---

### عناوين URL (Routes)

```
/external-sales/                              → الصفحة الرئيسية
/external-sales/decorator/                    → داشبورد مهندسي الديكور
/external-sales/decorator/engineers/          → قائمة المهندسين
/external-sales/decorator/engineers/<pk>/     → تفاصيل مهندس
/external-sales/decorator/engineers/<pk>/edit/ → تعديل مهندس
/external-sales/decorator/create-profile/<code>/ → إنشاء بروفايل
/external-sales/decorator/engineers/<pk>/add-contact/ → تسجيل تواصل
/external-sales/decorator/engineers/<pk>/contacts/    → سجل التواصل
/external-sales/decorator/engineers/<pk>/link-customer/ → ربط عميل
/external-sales/decorator/engineers/<pk>/unlink-customer/<link_pk>/ → فك ربط عميل
/external-sales/decorator/engineers/<pk>/link-order/    → ربط طلب
/external-sales/decorator/engineers/<pk>/unlink-order/<link_pk>/  → فك ربط طلب
/external-sales/decorator/engineers/<pk>/materials/     → إضافة خامة مفضلة
/external-sales/decorator/orders/             → الطلبات المرتبطة
/external-sales/decorator/commissions/        → إدارة العمولات
/external-sales/decorator/commissions/<pk>/approve/ → اعتماد عمولة
/external-sales/decorator/commissions/<pk>/pay/     → دفع عمولة

# API Endpoints (AJAX)
/external-sales/decorator/api/search-engineers/   → بحث مهندسين
/external-sales/decorator/api/search-customers/   → بحث عملاء (Select2)
/external-sales/decorator/api/search-orders/      → بحث طلبات (Select2)
/external-sales/decorator/api/available-orders/<pk>/ → طلبات متاحة لمهندس

# Charts (AJAX JSON)
/external-sales/decorator/api/chart-top-revenue/  → أعلى 10 إيرادات
/external-sales/decorator/api/chart-top-orders/   → أعلى 10 طلبات
/external-sales/decorator/api/chart-materials/    → أكثر الخامات طلباً
/external-sales/decorator/api/chart-monthly/      → النشاط الشهري

# Export / Import
/external-sales/decorator/export/engineers/       → تصدير قائمة المهندسين (Excel)
/external-sales/decorator/export/engineer/<pk>/   → تصدير بيانات مهندس كاملة
/external-sales/decorator/commissions/export/     → تصدير العمولات (Excel)
/external-sales/decorator/import/engineers/       → استيراد مهندسين من Excel
/external-sales/decorator/import/template/        → تحميل قالب الاستيراد
```

---

### الصلاحيات والوصول

```python
# في accounts/models.py — حقول مضافة على User:
is_decorator_dept_manager = BooleanField  # مدير قسم مهندسي الديكور
is_decorator_dept_staff   = BooleanField  # موظف في القسم
```

| الدور | الصلاحيات |
|-------|----------|
| **مدير القسم** (`is_decorator_dept_manager`) | كل شيء: حذف، اعتماد/دفع عمولات، استيراد، فك ربط |
| **موظف القسم** (`is_decorator_dept_staff`) | عرض، إضافة تواصل، ربط عملاء/طلبات، تصدير |
| **سوبر أدمن** (`is_superuser`) | وصول كامل |

---

## 📊 لوحة التحكم (Dashboard)

تحتوي داشبورد مهندسي الديكور (`/external-sales/decorator/`) على:

### 1. روابط التنقل السريع (4 كروت)
- لوحة التحكم
- قائمة المهندسين
- العمولات
- الطلبات المرتبطة

### 2. بطاقات KPI (4 بطاقات)
- إجمالي المهندسين
- المهندسون النشطون
- مهندسون جدد هذا الشهر
- بدون تواصل +60 يوم (تنبيه)

### 3. جداول البيانات
- **متابعات قادمة (7 أيام)**: المهندسون الذين لديهم متابعة مجدولة
- **مهندسون بدون تواصل (+60 يوم)**: تنبيه بالمهندسين الذين يحتاجون تواصل
- **آخر النشاطات**: آخر 10 تواصلات مسجلة

---

## 🔗 التكاملات

### 1. النافبار الديناميكي
- رابط مباشر "مهندسين الديكور" في قائمة المبيعات الخارجية
- يظهر فقط للمستخدمين المصرح لهم

### 2. لوحة الإدارة (Board Dashboard)
- تبويب "المبيعات الخارجية" في `/board-level/`
- إحصائيات سريعة: إجمالي المهندسين، النشطون، عمولات معلقة
- عرض أعلى 5 مهندسين بالإيرادات
- عرض العمولات الأخيرة

### 3. صفحة تفاصيل العميل
- عرض معلومات بروفايل المهندس مباشرة في تفاصيل العميل
- يظهر فقط إذا كان العميل من نوع `designer`

### 4. صفحة تفاصيل الطلب
- عرض بيانات ربط المهندس والعمولة في تفاصيل الطلب
- يظهر فقط إذا كان الطلب مرتبطاً بمهندس

### 5. نظام الإشعارات
- نوع إشعار جديد: `decorator_engineer_added`
- يُرسل تلقائياً لمدراء القسم عند إضافة مهندس جديد

### 6. سجل التدقيق (Audit Log)
- تسجيل تلقائي لكل إنشاء/تعديل بروفايل
- تسجيل تغييرات حالة العمولات

---

## ⚙️ أوامر الإدارة (Management Commands)

```bash
# إنشاء بروفايلات لجميع عملاء designer الذين ليس لديهم بروفايل
python manage.py create_decorator_profiles
# النتيجة: Created 68 decorator profiles.
```

---

## 📈 البيانات الحالية

| البند | العدد |
|-------|-------|
| مهندسو ديكور (بروفايلات) | 68 |
| نوع العميل في قاعدة البيانات | `customer_type = 'designer'` |

---

## 🚀 المراحل القادمة

### المرحلة 1: تحسينات قسم مهندسي الديكور (أولوية عالية)
1. **ربط تلقائي بالطلبات**: عند إنشاء طلب لعميل مرتبط بمهندس، ربط الطلب تلقائياً وحساب العمولة
2. **تقارير العمولات**: تقرير شهري بالعمولات المستحقة/المدفوعة لكل مهندس
3. **تنبيهات المتابعة**: إشعارات تلقائية (in-app + واتساب) عند اقتراب موعد المتابعة
4. **لوحة أداء المهندس**: رسوم بيانية لأداء كل مهندس (إيرادات، طلبات، نمو شهري)
5. **ربط مع المحاسبة**: إنشاء قيود محاسبية تلقائية عند دفع العمولات

### المرحلة 2: قسم البيع بالجملة (مخطط)
1. **`WholesaleClientProfile`**: ملف عميل جملة (حد ائتماني، شروط دفع، تصنيف)
2. **قوائم أسعار خاصة**: أسعار جملة مختلفة حسب فئة العميل والكمية
3. **طلبات بالجملة**: نظام طلبات مخصص بكميات كبيرة وخصومات
4. **متابعة الحسابات**: أرصدة، مستحقات، كشف حساب
5. **تقارير المبيعات**: تحليل مبيعات الجملة بالمنتج والفترة والعميل

### المرحلة 3: قسم المشاريع (مخطط)
1. **`ProjectProfile`**: ملف مشروع (حكومي/خاص، مراحل، ميزانية)
2. **مراحل التنفيذ**: تتبع تقدم المشروع (مناقصة → ترسية → تنفيذ → تسليم)
3. **عروض الأسعار**: نظام عروض أسعار للمشاريع مع بنود تفصيلية
4. **ضمانات وخطابات**: إدارة خطابات الضمان والتأمين
5. **تقارير المشاريع**: تقارير مالية وتنفيذية لكل مشروع

### المرحلة 4: تحسينات عامة (مستقبلي)
1. **Dashboard موحد**: لوحة تحكم واحدة لجميع أقسام المبيعات الخارجية
2. **تطبيق موبايل**: واجهة مبسطة للموظفين الميدانيين
3. **تكامل واتساب**: إرسال رسائل متابعة تلقائية للمهندسين
4. **خريطة العملاء**: عرض جغرافي لمواقع المهندسين والمشاريع
5. **API خارجي**: واجهة برمجية للربط مع أنظمة خارجية

---

## 🔧 ملاحظات تقنية مهمة

1. **البحث AJAX**: نماذج ربط العملاء والطلبات تستخدم Select2 AJAX (لأن النظام يحتوي 14,590+ عميل و 25,027+ طلب)
2. **الربط التلقائي**: عند ربط طلب بمهندس، يتم ربط عميل الطلب تلقائياً بنفس المهندس
3. **حقول الكاش**: الحقول `last_contact_date`, `next_followup_date`, `total_orders_count`, `total_clients_count` تُحدَّث تلقائياً عبر signals
4. **التصدير**: يدعم تصدير Excel (openpyxl) لقوائم المهندسين والعمولات وبيانات مهندس مفرد
5. **الاستيراد**: يدعم استيراد مهندسين من Excel مع قالب جاهز للتحميل
6. **الأداء**: جميع الاستعلامات تستخدم `select_related` و `prefetch_related` لتجنب N+1
