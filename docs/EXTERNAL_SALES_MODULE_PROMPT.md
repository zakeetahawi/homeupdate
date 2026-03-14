# External Sales Management Module — Implementation Prompt
## (إدارة المبيعات الخارجية — برومبت التنفيذ الكامل)

---

> **الشرح بالعربية في نهاية كل قسم لسهولة القراءة**

---

## 1. Overview & Scope

Build a new Django app called **`external_sales`** inside the existing El-Khawaga ERP project.
This module manages three external sales departments:

| Department (EN) | Department (AR) | Phase |
|---|---|---|
| Decorator Engineers | مهندسي الديكور | **Phase 1 — This prompt** |
| Wholesale | الجملة | Phase 2 |
| Projects | المشاريع | Phase 3 |

**Phase 1 deliverable**: A fully integrated Decorator Engineers Department sub-system.

> **الشرح**: هنبني تطبيق Django جديد اسمه `external_sales` يضم 3 أقسام للمبيعات الخارجية. هنبدأ اليوم بقسم مهندسي الديكور فقط.

---

## 2. App Skeleton

```
external_sales/
├── __init__.py
├── apps.py                    # AppConfig, verbose_name="المبيعات الخارجية"
├── admin.py
├── models.py
├── views.py
├── views_decorator.py         # All decorator-department views
├── forms.py
├── signals.py
├── urls.py
├── mixins.py                  # Permission mixins
├── utils.py                   # Analytics helpers
├── migrations/
│   └── 0001_initial.py
└── templates/
    └── external_sales/
        ├── base_dept.html               # Department layout base
        ├── decorator/
        │   ├── dashboard.html           # Decorator dept dashboard
        │   ├── engineer_list.html       # Paginated engineer list
        │   ├── engineer_detail.html     # Full profile + tabs
        │   ├── engineer_form.html       # Create/edit profile
        │   ├── link_customer_modal.html # Ajax modal
        │   ├── link_order_modal.html    # Ajax modal
        │   ├── contact_log_form.html    # Add contact entry
        │   ├── contact_log_list.html    # Timeline of contacts
        │   ├── commissions.html         # Commission management
        │   └── orders.html             # Filtered orders view
        └── partials/
            ├── engineer_card.html
            ├── stats_cards.html
            └── contact_timeline.html
```

> **الشرح**: هيكل الملفات الكامل للتطبيق — من النماذج للقوالب.

---

## 3. Database Models

### 3.1 `DecoratorEngineerProfile`

An **extension profile** for any `customers.Customer` whose `customer_type` code equals
`'decorator_engineer'`. One-to-one with Customer. Creates the "department-visible" layer of data.

```python
class DecoratorEngineerProfile(models.Model):
    """
    ملف مهندس الديكور — بيانات مرئية لقسم المبيعات الخارجية فقط
    """

    PRIORITY_CHOICES = [
        ('vip',     'VIP — أولوية قصوى'),
        ('active',  'نشط'),
        ('regular', 'عادي'),
        ('cold',    'فاتر — يحتاج إعادة تفعيل'),
    ]

    # Core link
    customer = models.OneToOneField(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='decorator_profile',
        verbose_name='العميل (المهندس)',
        limit_choices_to={'customer_type': 'decorator_engineer'},
    )

    # Business card info
    company_office_name = models.CharField('اسم المكتب / الشركة', max_length=200, blank=True)
    years_of_experience = models.PositiveSmallIntegerField('سنوات الخبرة', null=True, blank=True)
    area_of_operation   = models.CharField('منطقة العمل', max_length=300, blank=True,
                                            help_text='المدن / المناطق التي يعمل فيها المهندس')

    # Social / portfolio
    instagram_handle = models.CharField('Instagram', max_length=100, blank=True)
    portfolio_url    = models.URLField('Portfolio URL', blank=True)
    linkedin_url     = models.URLField('LinkedIn URL', blank=True)

    # Department-private notes & interests
    interests_notes  = models.TextField('اهتمامات المهندس وتفضيلاته', blank=True,
                                         help_text='أنواع الخامات والأقمشة المفضلة')
    internal_notes   = models.TextField('ملاحظات داخلية (للقسم فقط)', blank=True)

    # Priority & assignment
    priority         = models.CharField('الأولوية', max_length=10,
                                         choices=PRIORITY_CHOICES, default='regular', db_index=True)
    assigned_staff   = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_decorator_engineers',
        verbose_name='موظف المتابعة',
        limit_choices_to={'is_active': True},
    )

    # Timestamps & audit
    created_by  = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True,
                                     related_name='decorator_profiles_created', editable=False)
    updated_by  = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True,
                                     related_name='decorator_profiles_updated', editable=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ملف مهندس ديكور'
        verbose_name_plural = 'ملفات مهندسي الديكور'
        indexes = [
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['assigned_staff']),
        ]
        permissions = [
            ('view_decorator_profiles',   'Can view decorator engineer profiles'),
            ('manage_decorator_profiles', 'Can manage decorator engineer profiles'),
            ('view_decorator_commissions','Can view commission data'),
            ('manage_decorator_commissions','Can manage commissions'),
        ]
```

---

### 3.2 `EngineerLinkedCustomer`

Manually link a **retail/individual customer** (`customer_type != 'decorator_engineer'`) to an engineer's profile — this represents customers who came through that engineer's referral.

```python
class EngineerLinkedCustomer(models.Model):
    """
    ربط عميل أفراد بمهندس الديكور يدوياً
    يمثل العملاء الذين جاء بهم المهندس أو تتم متابعتهم من خلاله
    """
    engineer  = models.ForeignKey(DecoratorEngineerProfile, on_delete=models.CASCADE,
                                   related_name='linked_customers', verbose_name='المهندس')
    customer  = models.ForeignKey('customers.Customer', on_delete=models.CASCADE,
                                   related_name='engineer_links', verbose_name='العميل')
    linked_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True,
                                   related_name='customer_links_created', verbose_name='ربط بواسطة')
    linked_at = models.DateTimeField(auto_now_add=True)

    # Commission defaults that apply to all orders of this customer via this engineer
    default_commission_rate  = models.DecimalField(
        'نسبة العمولة الافتراضية %', max_digits=5, decimal_places=2, default=0,
        help_text='تُطبق تلقائياً على الطلبات الجديدة إذا لم تُحدَّد قيمة خاصة')
    notes = models.TextField('ملاحظات', blank=True)
    is_active = models.BooleanField('نشط', default=True, db_index=True)

    class Meta:
        verbose_name = 'عميل مرتبط بمهندس'
        verbose_name_plural = 'العملاء المرتبطون بمهندسين'
        unique_together = [('engineer', 'customer')]
        indexes = [models.Index(fields=['engineer', 'is_active'])]
```

---

### 3.3 `EngineerLinkedOrder`

Link a specific `orders.Order` to an engineer, track the commission per order.

```python
class EngineerLinkedOrder(models.Model):
    """
    ربط طلب محدد بملف مهندس الديكور مع إدارة العمولة
    """
    COMMISSION_STATUS = [
        ('pending',  'معلقة'),
        ('approved', 'معتمدة'),
        ('paid',     'مدفوعة'),
        ('cancelled','ملغاة'),
    ]
    LINK_TYPE = [
        ('manual', 'يدوي'),
        ('auto',   'تلقائي عبر العميل المرتبط'),
    ]

    engineer         = models.ForeignKey(DecoratorEngineerProfile, on_delete=models.CASCADE,
                                          related_name='linked_orders', verbose_name='المهندس')
    order            = models.OneToOneField('orders.Order', on_delete=models.CASCADE,
                                             related_name='engineer_link', verbose_name='الطلب')
    link_type        = models.CharField('نوع الربط', max_length=10, choices=LINK_TYPE, default='manual')
    linked_by        = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True,
                                          related_name='order_links_created', verbose_name='ربط بواسطة')
    linked_at        = models.DateTimeField(auto_now_add=True)

    # Commission
    commission_rate  = models.DecimalField('نسبة العمولة %', max_digits=5, decimal_places=2, default=0)
    commission_value = models.DecimalField('قيمة العمولة', max_digits=12, decimal_places=2, default=0,
                                            help_text='يُحسب تلقائياً أو يُدخل يدوياً')
    commission_status = models.CharField('حالة العمولة', max_length=10,
                                          choices=COMMISSION_STATUS, default='pending', db_index=True)
    commission_paid_at = models.DateTimeField('تاريخ دفع العمولة', null=True, blank=True)
    commission_paid_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True,
                                            blank=True, related_name='commissions_paid')
    notes            = models.TextField('ملاحظات العمولة', blank=True)

    class Meta:
        verbose_name = 'طلب مرتبط بمهندس'
        verbose_name_plural = 'الطلبات المرتبطة بمهندسين'
        indexes = [
            models.Index(fields=['engineer', 'commission_status']),
            models.Index(fields=['engineer', '-linked_at']),
        ]

    def calculate_commission(self):
        """احسب قيمة العمولة تلقائياً من مجموع الطلب"""
        if self.commission_rate and self.order_id:
            total = getattr(self.order, 'total_amount', 0) or 0
            self.commission_value = (self.commission_rate / 100) * total
        return self.commission_value
```

---

### 3.4 `EngineerContactLog`

Full contact history — calls, appointments, WhatsApp, visits. Drives the follow-up workflow.

```python
class EngineerContactLog(models.Model):
    """
    سجل المتابعة والتواصل مع مهندس الديكور
    """
    CONTACT_TYPES = [
        ('call',        'مكالمة هاتفية'),
        ('whatsapp',    'رسالة واتساب'),
        ('meeting',     'اجتماع'),
        ('appointment', 'حجز موعد زيارة'),
        ('email',       'بريد إلكتروني'),
        ('visit',       'زيارة ميدانية'),
        ('other',       'أخرى'),
    ]
    OUTCOME_CHOICES = [
        ('answered',           'رد على المكالمة'),
        ('no_answer',          'لم يرد'),
        ('busy',               'مشغول'),
        ('appointment_booked', 'تم حجز موعد'),
        ('interested',         'مهتم'),
        ('not_interested',     'غير مهتم'),
        ('callback_requested', 'طلب معاودة الاتصال'),
        ('completed',          'اكتملت المتابعة'),
    ]

    engineer          = models.ForeignKey(DecoratorEngineerProfile, on_delete=models.CASCADE,
                                           related_name='contact_logs', verbose_name='المهندس')
    contact_type      = models.CharField('نوع التواصل', max_length=15, choices=CONTACT_TYPES, db_index=True)
    contact_date      = models.DateTimeField('تاريخ ووقت التواصل', db_index=True)
    outcome           = models.CharField('نتيجة التواصل', max_length=25, choices=OUTCOME_CHOICES)
    notes             = models.TextField('تفاصيل / ملاحظات')

    # Follow-up scheduling
    next_followup_date  = models.DateField('موعد المتابعة القادمة', null=True, blank=True, db_index=True)
    next_followup_notes = models.TextField('تفاصيل المتابعة القادمة', blank=True)

    # Appointment details (if outcome == appointment_booked)
    appointment_datetime = models.DateTimeField('تاريخ ووقت الموعد', null=True, blank=True)
    appointment_location = models.CharField('مكان الموعد', max_length=300, blank=True)
    appointment_confirmed = models.BooleanField('تأكيد الموعد', default=False)

    # Audit
    created_by  = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True,
                                     related_name='contact_logs_created', verbose_name='سُجِّل بواسطة')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'سجل تواصل'
        verbose_name_plural = 'سجلات التواصل'
        ordering = ['-contact_date']
        indexes = [
            models.Index(fields=['engineer', '-contact_date']),
            models.Index(fields=['next_followup_date']),
            models.Index(fields=['outcome']),
        ]
```

---

### 3.5 `EngineerMaterialInterest`

Tracks which material/fabric categories the engineer frequently requests — used for analytics and targeted marketing.

```python
class EngineerMaterialInterest(models.Model):
    """
    الخامات والأقمشة التي يفضلها مهندس الديكور
    """
    INTEREST_LEVELS = [
        ('high',   'مرتفع'),
        ('medium', 'متوسط'),
        ('low',    'منخفض'),
    ]

    engineer       = models.ForeignKey(DecoratorEngineerProfile, on_delete=models.CASCADE,
                                        related_name='material_interests', verbose_name='المهندس')
    material_name  = models.CharField('اسم الخامة / القماش', max_length=200)
    # Optional: link to inventory category if available
    inventory_category = models.ForeignKey(
        'inventory.Category', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='engineer_interests', verbose_name='تصنيف المخزون'
    )
    interest_level = models.CharField('درجة الاهتمام', max_length=10,
                                       choices=INTEREST_LEVELS, default='medium')
    request_count  = models.PositiveIntegerField('عدد مرات الطلب', default=1,
                                                  help_text='كم مرة طلب المهندس هذه الخامة')
    notes          = models.TextField('ملاحظات', blank=True)
    added_by       = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    added_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'اهتمام بخامة'
        verbose_name_plural = 'اهتمامات الخامات'
        ordering = ['-request_count']
        unique_together = [('engineer', 'material_name')]
```

---

## 4. User Roles & Permissions

Add **two new boolean flags** to `accounts.User` (mirror the existing pattern — e.g. `is_inspection_manager`):

```python
# accounts/models.py — inside User class, with the other is_* fields:
is_decorator_dept_manager = models.BooleanField(
    default=False, verbose_name='مدير قسم مهندسي الديكور'
)
is_decorator_dept_staff = models.BooleanField(
    default=False, verbose_name='موظف قسم مهندسي الديكور'
)
```

Also update `ROLE_HIERARCHY` dict:

```python
'decorator_dept_manager': {
    'level': 3,
    'display': 'مدير قسم مهندسي الديكور',
    'inherits_from': ['decorator_dept_staff'],
    'permissions': [
        'view_decorator_profiles', 'manage_decorator_profiles',
        'view_decorator_commissions', 'manage_decorator_commissions',
        'view_all_customers', 'view_all_orders'
    ],
},
'decorator_dept_staff': {
    'level': 4,
    'display': 'موظف قسم مهندسي الديكور',
    'inherits_from': [],
    'permissions': [
        'view_decorator_profiles', 'manage_decorator_profiles',
    ],
},
```

> **الشرح**: هنضيف حقلين جديدين على موديل User: مدير القسم وموظف القسم، بنفس نمط الأدوار الموجودة.

---

## 5. Signal: Notify Manager on New Decorator Engineer Customer

In `external_sales/signals.py`:

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from customers.models import Customer
from notifications.models import Notification, NotificationVisibility
from accounts.models import User

@receiver(post_save, sender=Customer)
def notify_decorator_dept_on_new_engineer(sender, instance, created, **kwargs):
    """
    عند إضافة عميل جديد من نوع 'مهندس ديكور'،
    أرسل إشعاراً عاجلاً لجميع مدراء قسم مهندسي الديكور
    """
    if not created:
        return
    if instance.customer_type != 'decorator_engineer':
        return

    managers = User.objects.filter(
        is_decorator_dept_manager=True,
        is_active=True
    )
    if not managers.exists():
        return

    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(Customer)

    notification = Notification.objects.create(
        title=f'مهندس ديكور جديد: {instance.name}',
        message=(
            f'تم إضافة مهندس ديكور جديد "{instance.name}" '
            f'من فرع {instance.branch.name if instance.branch else "غير محدد"}. '
            f'يرجى مراجعة الملف وإسناد موظف متابعة.'
        ),
        notification_type='decorator_engineer_added',  # add to NOTIFICATION_TYPES list
        priority='high',
        content_type=ct,
        object_id=instance.pk,
        extra_data={
            'customer_code': instance.code,
            'customer_name': instance.name,
            'branch': instance.branch.name if instance.branch else None,
            'url': f'/external-sales/decorator/create-profile/{instance.code}/',
        }
    )
    for manager in managers:
        NotificationVisibility.objects.create(notification=notification, user=manager)
```

Also add `'decorator_engineer_added'` to `Notification.NOTIFICATION_TYPES` in `notifications/models.py`.

> **الشرح**: كل ما يُضاف عميل من نوع "مهندس ديكور" من أي فرع، يصل إشعار عاجل لجميع مدراء القسم فوراً مع رابط مباشر لإنشاء ملف المهندس.

---

## 6. URL Structure

In `crm/urls.py`, add:
```python
path('external-sales/', include('external_sales.urls', namespace='external_sales')),
```

`external_sales/urls.py`:
```python
urlpatterns = [
    # Department index
    path('', views.ExternalSalesIndexView.as_view(), name='index'),

    # ── Decorator Engineers Department ──────────────────────
    path('decorator/', views_decorator.DecoratorDashboardView.as_view(), name='decorator_dashboard'),
    path('decorator/engineers/', views_decorator.EngineerListView.as_view(), name='engineer_list'),
    path('decorator/engineers/<int:pk>/', views_decorator.EngineerDetailView.as_view(), name='engineer_detail'),
    path('decorator/engineers/<int:pk>/edit/', views_decorator.EngineerProfileEditView.as_view(), name='engineer_edit'),
    path('decorator/create-profile/<str:customer_code>/', views_decorator.CreateEngineerProfileView.as_view(), name='create_profile'),

    # Contact log
    path('decorator/engineers/<int:pk>/contact/add/', views_decorator.AddContactLogView.as_view(), name='add_contact'),
    path('decorator/engineers/<int:pk>/contact/', views_decorator.ContactLogListView.as_view(), name='contact_list'),

    # Linking
    path('decorator/engineers/<int:pk>/link-customer/', views_decorator.LinkCustomerView.as_view(), name='link_customer'),
    path('decorator/engineers/<int:pk>/unlink-customer/<int:link_id>/', views_decorator.UnlinkCustomerView.as_view(), name='unlink_customer'),
    path('decorator/engineers/<int:pk>/link-order/', views_decorator.LinkOrderView.as_view(), name='link_order'),
    path('decorator/engineers/<int:pk>/unlink-order/<int:link_id>/', views_decorator.UnlinkOrderView.as_view(), name='unlink_order'),

    # Materials
    path('decorator/engineers/<int:pk>/materials/', views_decorator.MaterialInterestView.as_view(), name='materials'),

    # Orders filtered view
    path('decorator/orders/', views_decorator.DecoratorOrdersView.as_view(), name='decorator_orders'),

    # Commission management
    path('decorator/commissions/', views_decorator.CommissionsView.as_view(), name='commissions'),
    path('decorator/commissions/<int:pk>/approve/', views_decorator.ApproveCommissionView.as_view(), name='approve_commission'),
    path('decorator/commissions/<int:pk>/pay/', views_decorator.MarkCommissionPaidView.as_view(), name='pay_commission'),

    # AJAX endpoints
    path('decorator/api/engineer-search/', views_decorator.EngineerSearchAjax.as_view(), name='api_engineer_search'),
    path('decorator/api/available-orders/<str:customer_code>/', views_decorator.AvailableOrdersAjax.as_view(), name='api_available_orders'),
]
```

> **الشرح**: هيكل الروابط الكامل — لوحة التحكم، قائمة المهندسين، صفحة التفاصيل، سجل التواصل، ربط العملاء والطلبات، وإدارة العمولات.

---

## 7. Permission Mixin

```python
# external_sales/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

class DecoratorDeptRequiredMixin(LoginRequiredMixin):
    """Allow only decorator dept staff, managers, and superusers"""
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_superuser or user.is_decorator_dept_manager
                or user.is_decorator_dept_staff or user.is_sales_manager):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

class DecoratorManagerRequiredMixin(LoginRequiredMixin):
    """Allow only decorator dept managers and superusers"""
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not (user.is_superuser or user.is_decorator_dept_manager or user.is_sales_manager):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
```

---

## 8. Core Views

### 8.1 Engineer Detail View (most important view)

`views_decorator.py — EngineerDetailView`:

```python
class EngineerDetailView(DecoratorDeptRequiredMixin, DetailView):
    model = DecoratorEngineerProfile
    template_name = 'external_sales/decorator/engineer_detail.html'
    context_object_name = 'profile'

    def get_queryset(self):
        return DecoratorEngineerProfile.objects.select_related(
            'customer', 'customer__branch', 'customer__category',
            'assigned_staff'
        ).prefetch_related(
            Prefetch('linked_customers',
                queryset=EngineerLinkedCustomer.objects.filter(is_active=True)
                    .select_related('customer', 'customer__branch', 'linked_by')),
            Prefetch('linked_orders',
                queryset=EngineerLinkedOrder.objects.select_related(
                    'order', 'order__customer', 'linked_by'
                ).order_by('-linked_at')),
            Prefetch('contact_logs',
                queryset=EngineerContactLog.objects.select_related('created_by')
                    .order_by('-contact_date')[:20]),
            'material_interests',
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.object
        ctx['analytics'] = compute_engineer_analytics(profile)
        ctx['recent_contacts'] = profile.contact_logs.all()[:10]
        ctx['pending_commissions'] = profile.linked_orders.filter(
            commission_status='pending'
        ).select_related('order')
        ctx['upcoming_followups'] = EngineerContactLog.objects.filter(
            engineer=profile,
            next_followup_date__gte=date.today()
        ).order_by('next_followup_date')[:5]
        return ctx
```

---

### 8.2 Analytics Helper (`utils.py`)

```python
def compute_engineer_analytics(profile):
    """
    كل الإحصائيات المطلوبة لصفحة تفاصيل المهندس
    """
    from django.db.models import Sum, Count, Max, Avg
    from django.db.models.functions import TruncMonth
    from datetime import date

    orders_qs = profile.linked_orders.select_related('order')
    customers_qs = profile.linked_customers.filter(is_active=True)

    # Basic counts
    total_linked_customers = customers_qs.count()
    total_linked_orders    = orders_qs.count()
    total_orders_value     = orders_qs.aggregate(
        total=Sum('order__total_amount'))['total'] or 0

    # Commission summary
    commissions = orders_qs.aggregate(
        pending  = Sum('commission_value', filter=Q(commission_status='pending')),
        approved = Sum('commission_value', filter=Q(commission_status='approved')),
        paid     = Sum('commission_value', filter=Q(commission_status='paid')),
    )

    # Last activity
    last_order_date   = orders_qs.aggregate(last=Max('linked_at'))['last']
    last_contact_date = profile.contact_logs.aggregate(last=Max('contact_date'))['last']
    last_activity     = max(filter(None, [last_order_date, last_contact_date]), default=None)

    # Monthly averages (last 6 months)
    six_months_ago = date.today() - timedelta(days=180)
    monthly_orders = (
        orders_qs.filter(linked_at__date__gte=six_months_ago)
        .annotate(month=TruncMonth('linked_at'))
        .values('month').annotate(cnt=Count('id'))
    )
    avg_monthly_orders = (
        sum(m['cnt'] for m in monthly_orders) / 6
        if monthly_orders else 0
    )

    # Top materials requested (from order items via linked orders)
    top_materials = (
        profile.material_interests.order_by('-request_count')[:5]
    )

    return {
        'total_linked_customers': total_linked_customers,
        'total_linked_orders':    total_linked_orders,
        'total_orders_value':     total_orders_value,
        'commission_pending':     commissions['pending'] or 0,
        'commission_approved':    commissions['approved'] or 0,
        'commission_paid':        commissions['paid'] or 0,
        'last_activity':          last_activity,
        'avg_monthly_orders':     round(avg_monthly_orders, 1),
        'top_materials':          top_materials,
    }
```

---

## 9. Template — Engineer Detail Page

The `engineer_detail.html` template must use **Bootstrap 5** (matching the project theme) and include:

### Layout: Tabs

```
┌─────────────────────────────────────────────────────────────┐
│  [Avatar]  Engineer Name   Priority Badge   Assigned Staff  │
│  Company | Area | Experience | Instagram ↗  LinkedIn ↗      │
├──────────┬────────────┬──────────┬──────────┬──────────────-┤
│ Overview │ Customers  │  Orders  │ Contact  │  Commissions  │
│ Tab      │  Tab       │   Tab    │ Log Tab  │    Tab        │
└──────────┴────────────┴──────────┴──────────┴───────────────┘
```

### Tab 1 — Overview
- 5 stat cards (KPI cards matching existing dashboard style):
  - Total Linked Customers
  - Total Linked Orders
  - Orders Value
  - Pending Commission
  - Average Monthly Orders
- Top 5 Materials chart (horizontal bar, Chart.js — already in project)
- Upcoming follow-ups timeline (next_followup_date)
- Internal notes section (edit inline via AJAX)

### Tab 2 — Linked Customers
- Table: Customer Name | Branch | Phone | Orders Count | Last Order | Commission Rate | Actions
- "Link Customer" button → opens search modal → confirm → POST

### Tab 3 — Linked Orders
- Table: Order # | Customer | Date | Total | Commission % | Commission Value | Status | Actions
- Filter: commission_status (pending / approved / paid)
- "Link Order" button → opens modal (search by order number or customer)

### Tab 4 — Contact Log
- Vertical timeline (newest first) with icon per contact type
- Each entry shows: type icon | date | outcome badge | notes | follow-up date
- "Add Contact" button → inline form (contact_type, contact_date, outcome, notes, next_followup_date, appointment fields)
- Upcoming follow-ups highlighted with alert color if overdue

### Tab 5 — Commissions
- Summary cards: Pending / Approved / Paid
- Table: Order # | Order Date | Order Total | Rate % | Commission Value | Status | Actions
- Department manager can "Approve" → "Mark Paid"

> **الشرح**: صفحة تفاصيل المهندس مقسمة لـ 5 تبويبات: نظرة عامة (KPIs)، العملاء المرتبطين، الطلبات، سجل التواصل، والعمولات — كل شيء في صفحة واحدة متكاملة.

---

## 10. Decorator Orders Page (`decorator/orders.html`)

A filtered version of the standard orders list accessible at `/external-sales/decorator/orders/` showing:
- Orders where `customer__customer_type = 'decorator_engineer'` **OR** `order__engineer_link` exists
- Same Bootstrap table design as `orders/order_list.html`
- Extra column: "Linked Engineer" with badge
- Filter bar: by engineer, by commission status, by order status, by date range
- Quick-link to link unlinked decorator-engineer orders

---

## 11. Dashboard (`decorator/dashboard.html`)

At `/external-sales/decorator/`:

```
┌──────────────────────────────────────────────────────┐
│  قسم مهندسي الديكور   │  [+ Add Profile]  [Orders]   │
├───────────┬────────────┬──────────────────────────────┤
│Total Engs │ Active     │ New this month  │ Follow-ups │
│    42     │  38        │      5          │   Today: 3  │
├───────────┴────────────┴─────────────────────────────-┤
│  Engineers needing follow-up (next_followup_date <=  │
│  today + 2 days) — Highlighted alert cards           │
├──────────────────────────────────────────────────────-┤
│  Recent Activity Feed (last 10 contact logs)         │
├──────────────────────────────────────────────────────-┤
│  Top Engineers by Order Value (this month) — Table   │
└──────────────────────────────────────────────────────-┘
```

---

## 12. Integration with Existing Apps

### 12.1 `customers` app
- In `customers/templates/customers/customer_detail.html`: add a **card** (visible only to `is_decorator_dept_manager` or `is_decorator_dept_staff`) showing:
  - Whether a `DecoratorEngineerProfile` exists for this customer
  - Link: "View Decorator Profile" or "Create Profile"
- In customer list filters: add quick-filter button "مهندسو الديكور"

### 12.2 `orders` app
- In `orders/templates/orders/order_detail.html`: add a section (for dept staff only):
  - "Linked Engineer": show name if linked, or "Not linked" + "Link to Engineer" button
  - Commission badge (pending/approved/paid)
- In the existing orders list: add column "eng" with initials badge if linked

### 12.3 `notifications` app
- Add `'decorator_engineer_added'` to `Notification.NOTIFICATION_TYPES`
- The signal (§5) fires on new decorator-engineer customer creation

### 12.4 `accounts` app
- Add `is_decorator_dept_manager` and `is_decorator_dept_staff` bool fields to `User`
- Update `get_user_role()` to return `'decorator_dept_manager'` / `'decorator_dept_staff'`
- Update `ROLE_HIERARCHY` dict

### 12.5 `whatsapp` app (optional, Phase 1.5)
- When `appointment_datetime` is set in `EngineerContactLog`, optionally send WhatsApp confirmation to the engineer's phone (from `customer.phone`) via existing `whatsapp.tasks`

---

## 13. Admin Registration

```python
# external_sales/admin.py
from django.contrib import admin
from .models import DecoratorEngineerProfile, EngineerLinkedCustomer, EngineerLinkedOrder, EngineerContactLog, EngineerMaterialInterest

class LinkedCustomerInline(admin.TabularInline):
    model = EngineerLinkedCustomer
    extra = 0

class LinkedOrderInline(admin.TabularInline):
    model = EngineerLinkedOrder
    extra = 0
    readonly_fields = ['commission_value']

class ContactLogInline(admin.TabularInline):
    model = EngineerContactLog
    extra = 0
    ordering = ['-contact_date']

@admin.register(DecoratorEngineerProfile)
class DecoratorEngineerProfileAdmin(admin.ModelAdmin):
    list_display = ['customer', 'priority', 'assigned_staff', 'company_office_name', 'created_at']
    list_filter = ['priority', 'assigned_staff']
    search_fields = ['customer__name', 'customer__code', 'company_office_name']
    inlines = [LinkedCustomerInline, LinkedOrderInline, ContactLogInline]
    readonly_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']
```

---

## 14. Migrations Checklist

After implementation, run:

```bash
python manage.py makemigrations accounts         # new is_decorator_dept_* fields
python manage.py makemigrations external_sales   # all new models
python manage.py makemigrations notifications    # new notification type (if stored in choices)
python manage.py migrate
```

---

## 15. Implementation Order (Step by Step)

1. **`accounts/models.py`** — Add `is_decorator_dept_manager`, `is_decorator_dept_staff` fields + ROLE_HIERARCHY entries
2. **`accounts/migrations/`** — `makemigrations accounts`
3. **`external_sales/`** — Create app skeleton (`apps.py`, `__init__.py`)
4. **`crm/settings.py`** — Add `'external_sales'` to `INSTALLED_APPS`
5. **`external_sales/models.py`** — All 5 models above
6. **`external_sales/migrations/`** — `makemigrations external_sales`
7. **`notifications/models.py`** — Add `'decorator_engineer_added'` to `NOTIFICATION_TYPES`
8. **`external_sales/signals.py`** — Notification signal
9. **`external_sales/apps.py`** — `ready()` method to connect signals
10. **`external_sales/mixins.py`** — Permission mixins
11. **`external_sales/forms.py`** — Forms for all models
12. **`external_sales/utils.py`** — `compute_engineer_analytics()`
13. **`external_sales/views_decorator.py`** — All views
14. **`external_sales/urls.py`** — URL patterns
15. **`crm/urls.py`** — Include `external_sales.urls`
16. **Templates** — All HTML templates using Bootstrap 5 + project theme
17. **Integration patches** — Add sections to `customer_detail.html` and `order_detail.html`
18. **`external_sales/admin.py`** — Admin registration
19. **`migrate`** — Apply all migrations

---

## 16. Constraints & Must-Follow Rules

- Use `select_related()` / `prefetch_related()` on **every** queryset (see §8.1 for pattern)
- `CurrentUserMiddleware` handles `created_by`/`updated_by` — do NOT set manually
- Use `convert_arabic_numbers_to_english()` from `core.utils.general` for any user-entered numeric fields
- All templates must `{% extend "base.html" %}` and use Bootstrap 5 classes only
- Commission display: use `{{ value|floatformat:2 }}` with `{% load accounting_numbers %}`
- New customer type code `'decorator_engineer'` must be created via `CustomerType` admin (or a data migration), NOT hardcoded as a string choice
- Soft-delete: if using SoftDeleteMixin, filter with `.active()` manager
- For large exports (commission reports), use Celery `default` queue

---

## 17. What's Deferred to Phase 2 & 3

| Feature | Phase |
|---|---|
| Wholesale Department (`قسم الجملة`) | 2 |
| Projects Department (`قسم المشاريع`) | 3 |
| Commission → `accounting` journal entry (debit/credit) | 2 |
| WhatsApp auto-appointment confirmation | 1.5 |
| Mobile-optimized engineer card for field staff | 2 |

---

## 18. Additional Model Fields (v2 Enhancements)

### 18.1 `DecoratorEngineerProfile` — Extra Fields

Add the following fields to the model in §3.1:

```python
# Auto-generated unique code  (e.g. DEC-0042)
designer_code = models.CharField(
    'كود المهندس', max_length=20, unique=True, blank=True, db_index=True,
    help_text='يُولَّد تلقائياً عند الإنشاء'
)

# Location
city = models.CharField('المدينة', max_length=100, blank=True, db_index=True)

# Design preferences (visible to dept only)
PRICE_SEGMENT_CHOICES = [
    ('low',     'اقتصادي'),
    ('medium',  'متوسط'),
    ('luxury',  'فاخر'),
]
price_segment = models.CharField(
    'الشريحة السعرية', max_length=10,
    choices=PRICE_SEGMENT_CHOICES, blank=True, db_index=True
)
design_style     = models.CharField('أسلوب التصميم', max_length=200, blank=True,
                                     help_text='مثال: كلاسيك، مودرن، كونتمبوراري')
preferred_colors = models.TextField('الألوان المفضلة', blank=True)

PROJECT_TYPE_CHOICES = [
    ('residential',  'سكني'),
    ('commercial',   'تجاري'),
    ('hospitality',  'ضيافة / فنادق'),
    ('mixed',        'متعدد'),
]
project_types = models.JSONField(
    'أنواع المشاريع', default=list, blank=True,
    help_text='اختر أنواع المشاريع التي يتخصص فيها المهندس'
)
```

**Auto-generate `designer_code` in `save()`:**

```python
def save(self, *args, **kwargs):
    if not self.designer_code:
        from django.db.models import Max
        last = DecoratorEngineerProfile.objects.aggregate(
            last_id=Max('id'))['last_id'] or 0
        self.designer_code = f'DEC-{(last + 1):04d}'
    super().save(*args, **kwargs)
```

> **الشرح**: هنضيف كود تلقائي لكل مهندس (DEC-0001، DEC-0002...)، حقل المدينة للفلترة، الشريحة السعرية، أسلوب التصميم، الألوان المفضلة، وأنواع المشاريع.

---

### 18.2 `EngineerLinkedCustomer` — Add `relationship_type`

```python
RELATIONSHIP_TYPE_CHOICES = [
    ('referred_client',  'عميل أحاله المهندس'),
    ('designer_project', 'مشروع المهندس نفسه'),
]
relationship_type = models.CharField(
    'نوع العلاقة', max_length=20,
    choices=RELATIONSHIP_TYPE_CHOICES, default='referred_client'
)
```

> **الشرح**: نفرق بين العميل اللي المهندس حوّله (عمولة) والمشروع اللي المهندس نفسه طالبه.

---

### 18.3 `EngineerLinkedOrder` — Add `commission_type`

```python
COMMISSION_TYPE_CHOICES = [
    ('percentage',    'نسبة مئوية من قيمة الطلب'),
    ('fixed_amount',  'مبلغ ثابت'),
]
commission_type = models.CharField(
    'نوع العمولة', max_length=15,
    choices=COMMISSION_TYPE_CHOICES, default='percentage'
)
```

**Update `calculate_commission()`:**

```python
def calculate_commission(self):
    if self.commission_type == 'fixed_amount':
        # commission_value is entered directly, no calculation needed
        return self.commission_value
    # percentage
    if self.commission_rate and self.order_id:
        total = getattr(self.order, 'total_amount', 0) or 0
        self.commission_value = (self.commission_rate / 100) * total
    return self.commission_value
```

> **الشرح**: العمولة إما نسبة مئوية من الطلب أو مبلغ ثابت يُدخل يدوياً.

---

### 18.4 `EngineerMaterialInterest` — Add `last_requested_date`

```python
last_requested_date = models.DateField(
    'آخر مرة طُلبت', null=True, blank=True, db_index=True
)
```

Update `request_count` increment logic to also set `last_requested_date = date.today()`.

---

## 19. Audit Log Integration

Every CREATE, UPDATE, DELETE on `DecoratorEngineerProfile`, `EngineerLinkedOrder`, and commission status changes must be logged using `core.audit.AuditLog`:

```python
# external_sales/signals.py  — add alongside the notification signal

from core.audit import AuditLog
from django.db.models.signals import post_save, pre_save
from .models import DecoratorEngineerProfile, EngineerLinkedOrder

@receiver(post_save, sender=DecoratorEngineerProfile)
def audit_decorator_profile(sender, instance, created, **kwargs):
    from accounts.middleware.current_user import get_current_user
    user = get_current_user()
    AuditLog.log(
        user=user,
        action='CREATE' if created else 'UPDATE',
        description=f'{"إنشاء" if created else "تعديل"} ملف مهندس ديكور: {instance.customer}',
        app_label='external_sales',
        model_name='DecoratorEngineerProfile',
        object_id=str(instance.pk),
        object_repr=str(instance.customer),
        severity='INFO',
    )

@receiver(post_save, sender=EngineerLinkedOrder)
def audit_commission_change(sender, instance, created, **kwargs):
    from accounts.middleware.current_user import get_current_user
    user = get_current_user()
    if not created:
        AuditLog.log(
            user=user,
            action='UPDATE',
            description=f'تغيير حالة عمولة: طلب {instance.order_id} → {instance.commission_status}',
            app_label='external_sales',
            model_name='EngineerLinkedOrder',
            object_id=str(instance.pk),
            severity='INFO',
        )
```

> **الشرح**: كل إنشاء أو تعديل لملف مهندس أو تغيير حالة عمولة يُسجَّل تلقائياً في سجل التدقيق (`core.AuditLog`) بنفس النمط المستخدم في باقي المشروع.

---

## 20. Enhanced Engineers List Page

The list view (`engineer_list.html`) must include:

**Columns:**
| # | Engineer Name | Designer Code | City | Phone | Total Clients | Total Orders | Last Activity | Status | Actions |
|---|---|---|---|---|---|---|---|---|---|

**Filters sidebar / filter bar:**
- City (dropdown of distinct cities)
- Status (active / inactive)
- Priority / Relationship Status
- Price Segment (low / medium / luxury)
- Material Preferences (text search)

**Quick-action buttons per row (without leaving the list):**
- `+ عميل` → opens `LinkCustomerView` modal pre-filled with engineer
- `+ تواصل` → opens `AddContactLogView` modal pre-filled
- `ربط طلب` → opens `LinkOrderView` modal pre-filled

**Search bar** (top of page) — searches across:
- `customer__name`
- `customer__phone`
- `city`
- `material_interests__material_name`

> **الشرح**: جدول المهندسين يحتوي على كود المهندس، المدينة، آخر نشاط، وأزرار سريعة لإضافة عميل أو تسجيل تواصل أو ربط طلب مباشرة من الجدول بدون الدخول للملف.

---

## 21. Activity Summary Fields (computed / cached)

Add the following **cached computed fields** on `DecoratorEngineerProfile` for fast list rendering (update via signal after each related record save):

```python
# Denormalized for performance — updated by signals
last_contact_date = models.DateField('آخر تواصل', null=True, blank=True, db_index=True)
last_order_date   = models.DateField('آخر طلب', null=True, blank=True, db_index=True)
next_followup_date = models.DateField('موعد المتابعة القادمة', null=True, blank=True, db_index=True)
total_clients_count = models.PositiveIntegerField('عدد العملاء', default=0)
total_orders_count  = models.PositiveIntegerField('عدد الطلبات', default=0)
```

**Signal to keep them in sync:**

```python
@receiver(post_save, sender=EngineerContactLog)
def update_profile_contact_cache(sender, instance, **kwargs):
    from django.db.models import Max
    profile = instance.engineer
    # Always query the actual max — do not assume the just-saved log is the latest
    actual_last = EngineerContactLog.objects.filter(
        engineer=profile
    ).aggregate(last=Max('contact_date'))['last']
    profile.last_contact_date = actual_last.date() if actual_last else None
    if instance.next_followup_date:
        # Take the earliest upcoming follow-up
        earliest = EngineerContactLog.objects.filter(
            engineer=profile,
            next_followup_date__gte=date.today()
        ).order_by('next_followup_date').values_list('next_followup_date', flat=True).first()
        profile.next_followup_date = earliest
    profile.save(update_fields=['last_contact_date', 'next_followup_date'])

@receiver(post_save, sender=EngineerLinkedOrder)
def update_profile_order_cache(sender, instance, **kwargs):
    profile = instance.engineer
    profile.last_order_date   = instance.linked_at.date()
    profile.total_orders_count = profile.linked_orders.count()
    profile.save(update_fields=['last_order_date', 'total_orders_count'])

@receiver(post_save, sender=EngineerLinkedCustomer)
def update_profile_customer_cache(sender, instance, **kwargs):
    profile = instance.engineer
    profile.total_clients_count = profile.linked_customers.filter(is_active=True).count()
    profile.save(update_fields=['total_clients_count'])
```

> **الشرح**: بدل ما نحسب آخر تواصل وعدد العملاء والطلبات في كل مرة من قاعدة البيانات، نخزنها في حقول مباشرة على ملف المهندس ونحدثها تلقائياً عبر signals — أسرع بكثير للقوائم.

---

## 22. Decorator Dept Dashboard — Charts

The dashboard (`decorator/dashboard.html`) must include **4 Chart.js charts**:

### Chart 1 — Top 10 Designers by Orders Value (Bar Chart)
```python
# AJAX endpoint: /external-sales/decorator/api/charts/top-by-revenue/
# Returns: [{label: 'Ahmed Eng.', value: 145200}, ...]
data = (
    DecoratorEngineerProfile.objects
    .annotate(total_value=Sum('linked_orders__order__total_amount'))
    .order_by('-total_value')[:10]
    .values('customer__name', 'designer_code', 'total_value')
)
```

### Chart 2 — Top 10 Designers by Order Count (Horizontal Bar)
```python
# AJAX endpoint: /external-sales/decorator/api/charts/top-by-orders/
data = (
    DecoratorEngineerProfile.objects
    .annotate(order_cnt=Count('linked_orders'))
    .order_by('-order_cnt')[:10]
    .values('customer__name', 'designer_code', 'order_cnt')
)
```

### Chart 3 — Most Requested Materials (Horizontal Bar)
```python
# AJAX endpoint: /external-sales/decorator/api/charts/top-materials/
data = (
    EngineerMaterialInterest.objects
    .values('material_name')
    .annotate(total=Sum('request_count'))
    .order_by('-total')[:10]
)
```

### Chart 4 — Monthly Activity (Line Chart — last 6 months)
```python
# AJAX endpoint: /external-sales/decorator/api/charts/monthly-activity/
# Returns: {months: ['Oct','Nov',...], contacts: [12,8,...], orders: [5,3,...]}
from django.db.models.functions import TruncMonth

contacts_by_month = (
    EngineerContactLog.objects
    .filter(contact_date__gte=six_months_ago)
    .annotate(month=TruncMonth('contact_date'))
    .values('month').annotate(cnt=Count('id'))
    .order_by('month')
)
orders_by_month = (
    EngineerLinkedOrder.objects
    .filter(linked_at__gte=six_months_ago)
    .annotate(month=TruncMonth('linked_at'))
    .values('month').annotate(cnt=Count('id'))
    .order_by('month')
)
```

Add corresponding URL patterns in `urls.py`:
```python
path('decorator/api/charts/top-by-revenue/', views_decorator.ChartTopByRevenueAjax.as_view(), name='chart_top_revenue'),
path('decorator/api/charts/top-by-orders/',  views_decorator.ChartTopByOrdersAjax.as_view(), name='chart_top_orders'),
path('decorator/api/charts/top-materials/',  views_decorator.ChartTopMaterialsAjax.as_view(), name='chart_materials'),
path('decorator/api/charts/monthly-activity/', views_decorator.ChartMonthlyActivityAjax.as_view(), name='chart_monthly'),
```

> **الشرح**: لوحة تحكم القسم تحتوي على 4 رسوم بيانية: أفضل المهندسين بالإيرادات، أفضلهم بعدد الطلبات، أكثر الخامات طلباً، والنشاط الشهري — كلها تُحمَّل عبر AJAX.

---

## 23. Inactivity Tracking & Alerts

### 23.1 Dashboard Alert Cards (dept dashboard)

Show engineers with **no activity ≥ 60 days** as highlighted alert cards:

```python
# views_decorator.py — DecoratorDashboardView.get_context_data()
from datetime import date, timedelta

inactive_threshold = date.today() - timedelta(days=60)
ctx['inactive_engineers'] = DecoratorEngineerProfile.objects.filter(
    last_contact_date__lt=inactive_threshold
).select_related('customer', 'assigned_staff').order_by('last_contact_date')[:10]
```

Template renders these as `alert-warning` Bootstrap cards with a "تواصل الآن" CTA button.

### 23.2 Management Dashboard Widget (`board_dashboard`)

Add three new widget entries to `BoardWidgetSettings` (via data migration or admin):

| Widget Key | Arabic Label | Description |
|---|---|---|
| `decorator_top_performers` | أفضل مهندسي الديكور | Top 5 by order value this month |
| `decorator_inactive_60d` | مهندسو الديكور غير النشطين | No contact in 60+ days |
| `decorator_top_commissions` | أعلى عمولات معلقة | Top unpaid commissions |

```python
# board_dashboard/api_views.py — add these JSON endpoints

class DecoratorTopPerformersWidget(BoardAccessMixin, View):
    def get(self, request):
        month_start = date.today().replace(day=1)
        data = (
            DecoratorEngineerProfile.objects
            .filter(linked_orders__linked_at__date__gte=month_start)
            .annotate(month_value=Sum('linked_orders__order__total_amount'))
            .order_by('-month_value')[:5]
            .values('customer__name', 'designer_code', 'month_value')
        )
        return JsonResponse({'results': list(data)})

class DecoratorInactive60DaysWidget(BoardAccessMixin, View):
    def get(self, request):
        threshold = date.today() - timedelta(days=60)
        data = (
            DecoratorEngineerProfile.objects
            .filter(last_contact_date__lt=threshold)
            .select_related('customer', 'assigned_staff')
            .order_by('last_contact_date')
            .values('customer__name', 'designer_code', 'last_contact_date',
                    'assigned_staff__first_name')[:10]
        )
        return JsonResponse({'results': list(data)})

class DecoratorTopCommissionsWidget(BoardAccessMixin, View):
    def get(self, request):
        data = (
            DecoratorEngineerProfile.objects
            .annotate(pending=Sum(
                'linked_orders__commission_value',
                filter=Q(linked_orders__commission_status='pending')
            ))
            .filter(pending__gt=0)
            .order_by('-pending')[:5]
            .values('customer__name', 'designer_code', 'pending')
        )
        return JsonResponse({'results': list(data)})
```

> **الشرح**: هنضيف 3 ويدجت للداشبورد الرئيسي للمدراء: أفضل مهندسي الديكور هذا الشهر، المهندسين اللي ما فيه تواصل 60 يوم، وأعلى العمولات المعلقة.

---

## 24. Performance Analytics — Profile Page Section

Add a "Performance Analytics" section as **Tab 6** on `engineer_detail.html`:

```
┌──────────────────────────────────────────────────────────┐
│  Performance Analytics                                    │
├──────────────────────────────────────────────────────────┤
│  [Monthly Orders Trend — 6 months line chart]            │
│  [Monthly Clients Growth — 6 months line chart]          │
├──────────────────────────────────────────────────────────┤
│  Totals:                                                  │
│  Total Clients | Total Orders | Total Revenue            │
│  Total Commission Paid | Last Order Date | Last Contact  │
└──────────────────────────────────────────────────────────┘
```

> **الشرح**: تبويب سادس في صفحة ملف المهندس يعرض منحنى الطلبات والعملاء الشهري ومجاميع الأداء الكاملة.

---

## 25. Notification Enhancement — Include `created_by`

Update the signal in §5 to include the user who added the engineer:

```python
notification = Notification.objects.create(
    title=f'مهندس ديكور جديد: {instance.name}',
    message=(
        f'تم إضافة مهندس ديكور جديد:\n'
        f'• الاسم: {instance.name}\n'
        f'• الكود: {instance.code}\n'
        f'• الفرع: {instance.branch.name if instance.branch else "غير محدد"}\n'
        f'• أضيف بواسطة: {instance.created_by.get_full_name() if instance.created_by else "غير معروف"}\n'
        f'• التاريخ: {timezone.now().strftime("%Y-%m-%d %H:%M")}\n\n'
        f'يرجى مراجعة الملف وإسناد موظف متابعة في أقرب وقت.'
    ),
    ...
)
```

---

## 26. Excel Import & Export (Bulk Data Management)

> **الشرح العام**: إضافة ميزة استيراد بيانات المهندسين بالجملة من ملف Excel، وتصدير بياناتهم + عملاؤهم + طلباتهم + عموالتهم إلى Excel — باستخدام `openpyxl` المثبتة مسبقاً في المشروع ونمط `export_to_excel()` الموجود في `accounting/export_utils.py`.

---

### 26.1 Export Views

#### Export Engineers List

```python
# views_decorator.py
from accounting.export_utils import export_to_excel
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

class ExportEngineersExcelView(DecoratorDeptRequiredMixin, View):
    """
    تصدير قائمة المهندسين إلى Excel
    GET /external-sales/decorator/export/engineers/
    يدعم نفس فلاتر قائمة المهندسين (city, priority, status)
    """
    def get(self, request):
        # الصلاحية: can_export على المستخدم أو مدير القسم
        if not (request.user.can_export or request.user.is_decorator_dept_manager
                or request.user.is_superuser):
            raise PermissionDenied

        qs = DecoratorEngineerProfile.objects.select_related(
            'customer', 'customer__branch', 'assigned_staff'
        ).order_by('-created_at')

        # تطبيق نفس فلاتر القائمة
        city     = request.GET.get('city')
        priority = request.GET.get('priority')
        status   = request.GET.get('status')
        if city:     qs = qs.filter(city=city)
        if priority: qs = qs.filter(priority=priority)
        if status:   qs = qs.filter(customer__status=status)

        columns = [
            {'header': 'كود المهندس',       'key': 'designer_code',      'width': 15},
            {'header': 'اسم المهندس',        'key': 'customer_name',      'width': 30},
            {'header': 'الهاتف',             'key': 'phone',              'width': 18},
            {'header': 'الهاتف 2',           'key': 'phone2',             'width': 18},
            {'header': 'البريد الإلكتروني',  'key': 'email',              'width': 30},
            {'header': 'المدينة',            'key': 'city',               'width': 20},
            {'header': 'اسم المكتب / الشركة','key': 'company_office_name','width': 30},
            {'header': 'منطقة العمل',        'key': 'area_of_operation',  'width': 25},
            {'header': 'سنوات الخبرة',       'key': 'years_of_experience','width': 15},
            {'header': 'الشريحة السعرية',    'key': 'price_segment',      'width': 18},
            {'header': 'أسلوب التصميم',      'key': 'design_style',       'width': 25},
            {'header': 'Instagram',          'key': 'instagram_handle',   'width': 25},
            {'header': 'Portfolio',          'key': 'portfolio_url',      'width': 30},
            {'header': 'الأولوية',           'key': 'priority',           'width': 15},
            {'header': 'موظف المتابعة',      'key': 'assigned_staff',     'width': 25},
            {'header': 'الفرع',              'key': 'branch',             'width': 20},
            {'header': 'عدد العملاء',        'key': 'total_clients_count','width': 15},
            {'header': 'عدد الطلبات',        'key': 'total_orders_count', 'width': 15},
            {'header': 'آخر تواصل',          'key': 'last_contact_date',  'width': 18},
            {'header': 'آخر طلب',            'key': 'last_order_date',    'width': 18},
            {'header': 'تاريخ الإنشاء',      'key': 'created_at',         'width': 20},
        ]

        data = []
        for p in qs:
            data.append({
                'designer_code':       p.designer_code,
                'customer_name':       p.customer.name,
                'phone':               p.customer.phone,
                'phone2':              p.customer.phone2 or '',
                'email':               p.customer.email or '',
                'city':                p.city,
                'company_office_name': p.company_office_name,
                'area_of_operation':   p.area_of_operation,
                'years_of_experience': p.years_of_experience or '',
                'price_segment':       p.get_price_segment_display(),
                'design_style':        p.design_style,
                'instagram_handle':    p.instagram_handle,
                'portfolio_url':       p.portfolio_url,
                'priority':            p.get_priority_display(),
                'assigned_staff':      p.assigned_staff.get_full_name() if p.assigned_staff else '',
                'branch':              p.customer.branch.name if p.customer.branch else '',
                'total_clients_count': p.total_clients_count,
                'total_orders_count':  p.total_orders_count,
                'last_contact_date':   str(p.last_contact_date) if p.last_contact_date else '',
                'last_order_date':     str(p.last_order_date) if p.last_order_date else '',
                'created_at':          p.created_at.strftime('%Y-%m-%d'),
            })

        return export_to_excel(
            data=data,
            columns=columns,
            filename=f'مهندسو_الديكور_{date.today()}',
            sheet_name='مهندسو الديكور',
        )
```

#### Export Single Engineer — Full Data (multi-sheet)

```python
class ExportEngineerFullDataView(DecoratorDeptRequiredMixin, View):
    """
    تصدير ملف مهندس واحد كاملاً (4 أوراق: ملف + عملاء + طلبات/عمولات + تواصل)
    GET /external-sales/decorator/engineers/<pk>/export/
    """
    def get(self, request, pk):
        profile = get_object_or_404(
            DecoratorEngineerProfile.objects.select_related('customer', 'customer__branch'),
            pk=pk
        )
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()

        # ── Sheet 1: Engineer Profile ──────────────────────
        ws1 = wb.active
        ws1.title = 'ملف المهندس'
        ws1.sheet_view.rightToLeft = True
        header_fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')

        profile_fields = [
            ('كود المهندس', profile.designer_code),
            ('الاسم', profile.customer.name),
            ('الهاتف', profile.customer.phone),
            ('الهاتف 2', profile.customer.phone2 or ''),
            ('البريد الإلكتروني', profile.customer.email or ''),
            ('المدينة', profile.city),
            ('اسم المكتب', profile.company_office_name),
            ('منطقة العمل', profile.area_of_operation),
            ('سنوات الخبرة', profile.years_of_experience or ''),
            ('الشريحة السعرية', profile.get_price_segment_display()),
            ('أسلوب التصميم', profile.design_style),
            ('Instagram', profile.instagram_handle),
            ('Portfolio', profile.portfolio_url),
            ('الأولوية', profile.get_priority_display()),
            ('اهتمامات', profile.interests_notes),
            ('عدد العملاء', profile.total_clients_count),
            ('عدد الطلبات', profile.total_orders_count),
            ('آخر تواصل', str(profile.last_contact_date) if profile.last_contact_date else ''),
        ]
        for row_idx, (label, value) in enumerate(profile_fields, 1):
            ws1.cell(row=row_idx, column=1, value=label).font = Font(bold=True)
            ws1.cell(row=row_idx, column=2, value=str(value) if value is not None else '')
        ws1.column_dimensions['A'].width = 25
        ws1.column_dimensions['B'].width = 40

        # ── Sheet 2: Linked Customers ──────────────────────
        ws2 = wb.create_sheet('العملاء المرتبطون')
        ws2.sheet_view.rightToLeft = True
        headers2 = ['اسم العميل', 'الهاتف', 'الفرع', 'نوع العلاقة', 'عمولة %', 'تاريخ الربط', 'ملاحظات']
        for i, h in enumerate(headers2, 1):
            c = ws2.cell(row=1, column=i, value=h)
            c.font = header_font; c.fill = header_fill
        for r, lc in enumerate(profile.linked_customers.filter(is_active=True).select_related('customer','customer__branch'), 2):
            ws2.cell(row=r, column=1, value=lc.customer.name)
            ws2.cell(row=r, column=2, value=lc.customer.phone)
            ws2.cell(row=r, column=3, value=lc.customer.branch.name if lc.customer.branch else '')
            ws2.cell(row=r, column=4, value=lc.get_relationship_type_display())
            ws2.cell(row=r, column=5, value=float(lc.default_commission_rate))
            ws2.cell(row=r, column=6, value=str(lc.linked_at.date()))
            ws2.cell(row=r, column=7, value=lc.notes)

        # ── Sheet 3: Linked Orders & Commission ────────────
        ws3 = wb.create_sheet('الطلبات والعمولات')
        ws3.sheet_view.rightToLeft = True
        headers3 = ['رقم الطلب', 'العميل', 'تاريخ الطلب', 'قيمة الطلب', 'نوع العمولة', 'نسبة %', 'قيمة العمولة', 'حالة العمولة', 'تاريخ الربط']
        for i, h in enumerate(headers3, 1):
            c = ws3.cell(row=1, column=i, value=h)
            c.font = header_font; c.fill = header_fill
        for r, lo in enumerate(profile.linked_orders.select_related('order','order__customer').order_by('-linked_at'), 2):
            ws3.cell(row=r, column=1, value=lo.order.order_number)
            ws3.cell(row=r, column=2, value=lo.order.customer.name)
            ws3.cell(row=r, column=3, value=str(lo.order.order_date.date()))
            ws3.cell(row=r, column=4, value=float(getattr(lo.order, 'total_amount', 0) or 0))
            ws3.cell(row=r, column=5, value=lo.get_commission_type_display())
            ws3.cell(row=r, column=6, value=float(lo.commission_rate))
            ws3.cell(row=r, column=7, value=float(lo.commission_value))
            ws3.cell(row=r, column=8, value=lo.get_commission_status_display())
            ws3.cell(row=r, column=9, value=str(lo.linked_at.date()))

        # ── Sheet 4: Communication Log ─────────────────────
        ws4 = wb.create_sheet('سجل التواصل')
        ws4.sheet_view.rightToLeft = True
        headers4 = ['نوع التواصل', 'التاريخ', 'النتيجة', 'ملاحظات', 'موعد المتابعة', 'سُجِّل بواسطة']
        for i, h in enumerate(headers4, 1):
            c = ws4.cell(row=1, column=i, value=h)
            c.font = header_font; c.fill = header_fill
        for r, log in enumerate(profile.contact_logs.select_related('created_by').order_by('-contact_date'), 2):
            ws4.cell(row=r, column=1, value=log.get_contact_type_display())
            ws4.cell(row=r, column=2, value=str(log.contact_date))
            ws4.cell(row=r, column=3, value=log.get_outcome_display())
            ws4.cell(row=r, column=4, value=log.notes)
            ws4.cell(row=r, column=5, value=str(log.next_followup_date) if log.next_followup_date else '')
            ws4.cell(row=r, column=6, value=log.created_by.get_full_name() if log.created_by else '')

        # Return file
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        filename = f'مهندس_{profile.designer_code}_{date.today()}.xlsx'
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
```

---

### 26.2 Import View (Bulk Upload)

```python
class ImportEngineersExcelView(DecoratorManagerRequiredMixin, View):
    """
    استيراد بيانات مهندسين بالجملة من ملف Excel
    POST /external-sales/decorator/import/
    يقبل ملف .xlsx بنفس تنسيق قالب الاستيراد
    """
    template_name = 'external_sales/decorator/import_engineers.html'

    def get(self, request):
        """عرض نموذج الرفع + رابط تنزيل قالب Excel الفارغ"""
        return render(request, self.template_name)

    def post(self, request):
        """معالجة الملف المرفوع"""
        import openpyxl
        from core.utils.general import convert_arabic_numbers_to_english

        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, 'يرجى اختيار ملف Excel.')
            return redirect('external_sales:import_engineers')

        if not excel_file.name.endswith('.xlsx'):
            messages.error(request, 'يُقبل ملف Excel بصيغة .xlsx فقط.')
            return redirect('external_sales:import_engineers')

        if excel_file.size > 5 * 1024 * 1024:  # 5 MB limit
            messages.error(request, 'حجم الملف يتجاوز 5 ميجابايت.')
            return redirect('external_sales:import_engineers')

        try:
            wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
            ws = wb.active
        except Exception:
            messages.error(request, 'ملف Excel تالف أو غير صالح.')
            return redirect('external_sales:import_engineers')

        # Expected columns (row 1 = headers, data starts row 2)
        EXPECTED_HEADERS = [
            'اسم المهندس',       # A — REQUIRED
            'الهاتف',            # B — REQUIRED
            'الهاتف 2',          # C
            'البريد الإلكتروني', # D
            'المدينة',           # E
            'اسم المكتب / الشركة', # F
            'منطقة العمل',       # G
            'سنوات الخبرة',      # H
            'Instagram',         # I
            'Portfolio URL',     # J
            'الشريحة السعرية',   # K  (low/medium/luxury)
            'أسلوب التصميم',     # L
            'ملاحظات',           # M
        ]

        results = {'created': 0, 'updated': 0, 'skipped': 0, 'errors': []}

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or not row[0]:  # skip empty rows
                continue

            name  = str(row[0]).strip() if row[0] else ''
            phone = convert_arabic_numbers_to_english(str(row[1]).strip()) if row[1] else ''

            if not name or not phone:
                results['errors'].append(f'الصف {row_num}: الاسم والهاتف مطلوبان.')
                results['skipped'] += 1
                continue

            # Validate phone format (basic)
            import re
            if not re.match(r'^\+?[0-9\s\-]{7,20}$', phone):
                results['errors'].append(f'الصف {row_num}: رقم الهاتف "{phone}" غير صحيح.')
                results['skipped'] += 1
                continue

            # Try to find existing Customer by phone
            # NOTE: SoftDeleteManager is the default `objects` manager — no `.active()` method
            from customers.models import Customer, CustomerType
            customer = Customer.objects.filter(phone=phone).first()

            if not customer:
                # Create a new Customer record
                # Ensure the 'decorator_engineer' CustomerType exists
                ct, _ = CustomerType.objects.get_or_create(
                    code='decorator_engineer',
                    defaults={
                        'name': 'مهندس ديكور',
                        'pricing_type': 'retail',
                    }
                )
                customer = Customer.objects.create(
                    name=name,
                    phone=phone,
                    phone2=str(row[2]).strip() if row[2] else '',
                    email=str(row[3]).strip() if row[3] else '',
                    customer_type='decorator_engineer',
                    address=str(row[6]).strip() if row[6] else '',
                    status='active',
                )
                created_new = True
            else:
                created_new = False

            # Create or update DecoratorEngineerProfile
            price_segment_map = {
                'اقتصادي': 'low', 'low': 'low',
                'متوسط': 'medium', 'medium': 'medium',
                'فاخر': 'luxury', 'luxury': 'luxury',
            }
            raw_segment = str(row[10]).strip().lower() if row[10] else ''
            price_segment = price_segment_map.get(raw_segment, '')

            profile, profile_created = DecoratorEngineerProfile.objects.update_or_create(
                customer=customer,
                defaults={
                    'city':                str(row[4]).strip() if row[4] else '',
                    'company_office_name': str(row[5]).strip() if row[5] else '',
                    'area_of_operation':   str(row[6]).strip() if row[6] else '',
                    'years_of_experience': int(convert_arabic_numbers_to_english(str(row[7]))) if row[7] else None,
                    'instagram_handle':    str(row[8]).strip() if row[8] else '',
                    'portfolio_url':       str(row[9]).strip() if row[9] else '',
                    'price_segment':       price_segment,
                    'design_style':        str(row[11]).strip() if row[11] else '',
                    'internal_notes':      str(row[12]).strip() if row[12] else '',
                }
            )

            if created_new or profile_created:
                results['created'] += 1
            else:
                results['updated'] += 1

        wb.close()

        messages.success(
            request,
            f'تم الاستيراد: {results["created"]} مهندس جديد، '
            f'{results["updated"]} تم تحديثه، '
            f'{results["skipped"]} تم تخطيه.'
        )
        if results['errors']:
            # Show first 10 errors only
            for err in results['errors'][:10]:
                messages.warning(request, err)

        return redirect('external_sales:engineer_list')
```

---

### 26.3 Import Template Download (Blank Excel Template)

```python
class DownloadImportTemplateView(DecoratorDeptRequiredMixin, View):
    """
    تنزيل قالب Excel الفارغ مع التعليمات
    GET /external-sales/decorator/import/template/
    """
    def get(self, request):
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'مهندسو الديكور'
        ws.sheet_view.rightToLeft = True

        headers = [
            ('اسم المهندس *',           30, True),
            ('الهاتف *',                18, True),
            ('الهاتف 2',               18, False),
            ('البريد الإلكتروني',       30, False),
            ('المدينة',                 20, False),
            ('اسم المكتب / الشركة',     30, False),
            ('منطقة العمل',             25, False),
            ('سنوات الخبرة',            15, False),
            ('Instagram',               25, False),
            ('Portfolio URL',           35, False),
            ('الشريحة السعرية',         20, False),  # low / medium / luxury أو اقتصادي / متوسط / فاخر
            ('أسلوب التصميم',           25, False),
            ('ملاحظات',                 35, False),
        ]

        required_fill = PatternFill(start_color='C0392B', end_color='C0392B', fill_type='solid')
        optional_fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
        header_font   = Font(bold=True, color='FFFFFF', size=11)

        # Row 1 — Headers
        for col_idx, (label, width, required) in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=label)
            cell.font  = header_font
            cell.fill  = required_fill if required else optional_fill
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            ws.column_dimensions[get_column_letter(col_idx)].width = width
        ws.row_dimensions[1].height = 35

        # Row 2 — Example data
        example = [
            'أحمد محمد علي', '01012345678', '01098765432',
            'ahmed@example.com', 'القاهرة', 'مكتب الإبداع للديكور',
            'القاهرة، الجيزة', '8', 'ahmed_deco', 'https://portfolio.com/ahmed',
            'luxury', 'مودرن كونتمبوراري', 'مهندس متميز يعمل مع مشاريع راقية',
        ]
        for col_idx, value in enumerate(example, 1):
            ws.cell(row=2, column=col_idx, value=value)

        # Instructions sheet
        ws2 = wb.create_sheet('تعليمات الاستيراد')
        ws2.sheet_view.rightToLeft = True
        instructions = [
            ('📌 تعليمات الاستيراد', True),
            ('', False),
            ('1. الحقول المعلّمة بـ (*) مطلوبة، والباقي اختياري.', False),
            ('2. يجب أن يكون رقم الهاتف بالأرقام الإنجليزية أو العربية.', False),
            ('3. إذا كان المهندس موجوداً بنفس الهاتف → يتم تحديث بياناته.', False),
            ('4. إذا كان جديداً → يتم إنشاء عميل جديد وملف مهندس.', False),
            ('5. الشريحة السعرية: اكتب low أو medium أو luxury (أو اقتصادي / متوسط / فاخر).', False),
            ('6. لا تغيّر أسماء الأعمدة في صف الرأس.', False),
            ('7. ابدأ البيانات من الصف الثاني.', False),
            ('8. الحد الأقصى لحجم الملف: 5 ميجابايت.', False),
        ]
        for row_idx, (text, bold) in enumerate(instructions, 1):
            c = ws2.cell(row=row_idx, column=1, value=text)
            if bold: c.font = Font(bold=True, size=13)
        ws2.column_dimensions['A'].width = 70

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="قالب_استيراد_مهندسين_الديكور.xlsx"'
        return response
```

---

### 26.4 Commissions Export

```python
class ExportCommissionsExcelView(DecoratorManagerRequiredMixin, View):
    """
    تصدير تقرير العمولات
    GET /external-sales/decorator/commissions/export/
    """
    def get(self, request):
        status_filter = request.GET.get('status')  # pending / approved / paid
        qs = EngineerLinkedOrder.objects.select_related(
            'engineer__customer', 'order', 'order__customer'
        ).order_by('-linked_at')

        if status_filter:
            qs = qs.filter(commission_status=status_filter)

        columns = [
            {'header': 'كود المهندس',     'key': 'designer_code',      'width': 15},
            {'header': 'اسم المهندس',      'key': 'engineer_name',      'width': 30},
            {'header': 'رقم الطلب',        'key': 'order_number',       'width': 20},
            {'header': 'عميل الطلب',       'key': 'order_customer',     'width': 30},
            {'header': 'تاريخ الطلب',      'key': 'order_date',         'width': 18},
            {'header': 'قيمة الطلب',       'key': 'order_total',        'width': 18},
            {'header': 'نوع العمولة',      'key': 'commission_type',    'width': 18},
            {'header': 'نسبة العمولة %',   'key': 'commission_rate',    'width': 18},
            {'header': 'قيمة العمولة',     'key': 'commission_value',   'width': 18},
            {'header': 'حالة العمولة',     'key': 'commission_status',  'width': 18},
            {'header': 'تاريخ الدفع',      'key': 'paid_at',            'width': 18},
        ]

        data = []
        for lo in qs:
            data.append({
                'designer_code':     lo.engineer.designer_code,
                'engineer_name':     lo.engineer.customer.name,
                'order_number':      lo.order.order_number,
                'order_customer':    lo.order.customer.name,
                'order_date':        str(lo.order.order_date.date()),
                'order_total':       float(getattr(lo.order, 'total_amount', 0) or 0),
                'commission_type':   lo.get_commission_type_display(),
                'commission_rate':   float(lo.commission_rate),
                'commission_value':  float(lo.commission_value),
                'commission_status': lo.get_commission_status_display(),
                'paid_at':           str(lo.commission_paid_at.date()) if lo.commission_paid_at else '',
            })

        label = {'pending': 'معلقة', 'approved': 'معتمدة', 'paid': 'مدفوعة'}.get(status_filter, 'الكل')
        return export_to_excel(
            data=data,
            columns=columns,
            filename=f'عمولات_مهندسي_الديكور_{label}_{date.today()}',
            sheet_name='العمولات',
        )
```

---

### 26.5 New URL Patterns (add to `urls.py`)

```python
# Export
path('decorator/export/engineers/',            views_decorator.ExportEngineersExcelView.as_view(),    name='export_engineers'),
path('decorator/engineers/<int:pk>/export/',   views_decorator.ExportEngineerFullDataView.as_view(),  name='export_engineer'),
path('decorator/commissions/export/',          views_decorator.ExportCommissionsExcelView.as_view(),  name='export_commissions'),

# Import
path('decorator/import/',                      views_decorator.ImportEngineersExcelView.as_view(),    name='import_engineers'),
path('decorator/import/template/',             views_decorator.DownloadImportTemplateView.as_view(),  name='import_template'),
```

---

### 26.6 Import Page Template (`import_engineers.html`)

```django
{% extends "base.html" %}
{% load static %}

{% block title %}استيراد مهندسي الديكور{% endblock %}

{% block content %}
<div class="container-fluid py-4" dir="rtl">
  <div class="row justify-content-center">
    <div class="col-lg-7">

      <!-- Header -->
      <div class="d-flex align-items-center mb-4 gap-3">
        <a href="{% url 'external_sales:engineer_list' %}" class="btn btn-outline-secondary btn-sm">
          <i class="fas fa-arrow-right"></i>
        </a>
        <h4 class="mb-0">استيراد مهندسين بالجملة من Excel</h4>
      </div>

      <!-- Instructions card -->
      <div class="card border-info mb-4">
        <div class="card-header bg-info bg-opacity-10 text-info fw-bold">
          <i class="fas fa-info-circle me-1"></i> تعليمات قبل الاستيراد
        </div>
        <div class="card-body small">
          <ol class="mb-0">
            <li>حمّل قالب Excel الفارغ أولاً ثم امله بالبيانات.</li>
            <li>الحقول الحمراء في القالب (<strong>الاسم والهاتف</strong>) مطلوبة — لا تتركها فارغة.</li>
            <li>إذا كان المهندس موجوداً بنفس رقم الهاتف، سيتم <strong>تحديث</strong> بياناته.</li>
            <li>الملف المقبول: <code>.xlsx</code> فقط — حد أقصى 5 ميجابايت.</li>
            <li>افتح ورقة "تعليمات الاستيراد" داخل القالب لمزيد من التفاصيل.</li>
          </ol>
        </div>
        <div class="card-footer">
          <a href="{% url 'external_sales:import_template' %}" class="btn btn-success btn-sm">
            <i class="fas fa-download me-1"></i> تنزيل قالب Excel الفارغ
          </a>
        </div>
      </div>

      <!-- Upload form -->
      <div class="card shadow-sm">
        <div class="card-header fw-bold">
          <i class="fas fa-file-excel me-1 text-success"></i> رفع ملف Excel
        </div>
        <div class="card-body">
          <form method="post" enctype="multipart/form-data" id="importForm">
            {% csrf_token %}
            <div class="mb-3">
              <label class="form-label fw-semibold">اختر ملف Excel <span class="text-danger">*</span></label>
              <input type="file" name="excel_file" class="form-control" accept=".xlsx" required>
              <div class="form-text">صيغة .xlsx فقط — حد أقصى 5 ميجابايت</div>
            </div>
            <button type="submit" class="btn btn-primary w-100" id="uploadBtn">
              <i class="fas fa-upload me-1"></i> بدء الاستيراد
            </button>
          </form>
        </div>
      </div>

      <!-- Django messages (import results) -->
      {% for message in messages %}
      <div class="alert alert-{{ message.tags|default:'info' }} alert-dismissible mt-3" role="alert">
        {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
      {% endfor %}

    </div>
  </div>
</div>

<script>
document.getElementById('importForm').addEventListener('submit', function() {
  document.getElementById('uploadBtn').disabled = true;
  document.getElementById('uploadBtn').innerHTML =
    '<span class="spinner-border spinner-border-sm me-1"></span> جارٍ الاستيراد...';
});
</script>
{% endblock %}
```

---

### 26.7 Export Buttons — Integration in Existing Templates

**In `engineer_list.html`** — add to the page action bar:
```django
<div class="btn-group">
  <a href="{% url 'external_sales:export_engineers' %}{% if request.GET %}?{{ request.GET.urlencode }}{% endif %}"
     class="btn btn-outline-success btn-sm">
    <i class="fas fa-file-excel me-1"></i> تصدير Excel
  </a>
  {% if request.user.is_decorator_dept_manager or request.user.is_superuser %}
  <a href="{% url 'external_sales:import_engineers' %}" class="btn btn-outline-primary btn-sm">
    <i class="fas fa-upload me-1"></i> استيراد بالجملة
  </a>
  {% endif %}
</div>
```

**In `engineer_detail.html`** — in profile header actions:
```django
<a href="{% url 'external_sales:export_engineer' profile.pk %}"
   class="btn btn-outline-success btn-sm">
  <i class="fas fa-file-excel me-1"></i> تصدير الملف الكامل
</a>
```

**In `commissions.html`** — in commission page header:
```django
<a href="{% url 'external_sales:export_commissions' %}?status={{ current_status_filter }}"
   class="btn btn-outline-success btn-sm">
  <i class="fas fa-file-excel me-1"></i> تصدير العمولات
</a>
```

---

### 26.8 Security Constraints for Import/Export

- **Export**: requires `request.user.can_export OR is_decorator_dept_manager OR is_superuser`
- **Import (bulk create/update)**: restricted to `is_decorator_dept_manager OR is_superuser` only (never dept staff)
- **File validation**: only `.xlsx` accepted, max 5 MB, validated with `openpyxl.load_workbook()` before processing
- **Phone sanitization**: always pass through `convert_arabic_numbers_to_english()` before DB write
- **No shell/system calls**: use `openpyxl` in-memory only (`io.BytesIO`) — no temp files written to disk
- Each import run is logged via `AuditLog` with action `'BULK_UPDATE'` and row counts in `extra_data`

```python
# At end of ImportEngineersExcelView.post()
AuditLog.log(
    user=request.user,
    action='BULK_UPDATE',
    description=f'استيراد مهندسي ديكور من Excel: {results["created"]} جديد، {results["updated"]} محدَّث',
    app_label='external_sales',
    model_name='DecoratorEngineerProfile',
    severity='INFO',
    extra_data=results,
)
```

> **ملاحظة**: لا تستخدم مكتبات مثل `pandas` أو `django-import-export` — `openpyxl` مثبتة بالفعل في المشروع ويكفي استخدامها مباشرةً.

---

## 27. Board Dashboard Integration — External Sales Tab

> **الشرح**: نضيف تبويبة "المبيعات الخارجية" في داشبورد مجلس الإدارة (`/board-level/`) تحتوي على تبويبة "مهندسو الديكور" بداخلها — كل شيء يسير على نمط `BoardDashboardView` و `BoardAccessMixin` الموجودَين، مع AJAX data endpoints منفصلة.

---

### 27.1 Overview — Tab Architecture

The main board dashboard (`board_dashboard/dashboard.html`) currently shows one view. We extend it with a **top-level Bootstrap tab bar**:

```
┌─────────────────────────────────────────────────────────────────────┐
│   لوحة تحكم مجلس الإدارة                         🔴 سري للغاية      │
├─────────────────────────────────────────────────────────────────────┤
│  [ الرئيسية ]  [ المبيعات الخارجية ]  [ ... future tabs ... ]        │
└─────────────────────────────────────────────────────────────────────┘
```

Inside **المبيعات الخارجية** tab:
```
┌──────────────────────────────────────────────────────────────┐
│  [ نظرة عامة ]  [ مهندسو الديكور ]  [ الجملة* ]  [ المشاريع* ]│
│                                         * قريباً               │
└──────────────────────────────────────────────────────────────┘
```

---

### 27.2 Template Changes — `board_dashboard/dashboard.html`

Add a **top-level tab nav** just after the filter strip, wrapping existing content in a "الرئيسية" tab pane, and adding an "المبيعات الخارجية" tab pane:

```django
{# ── Top-level tab bar ──────────────────────────────────────── #}
<ul class="nav nav-tabs board-main-tabs mb-4" id="boardMainTabs" role="tablist">
  <li class="nav-item" role="presentation">
    <button class="nav-link active" id="tab-main-btn"
            data-bs-toggle="tab" data-bs-target="#tab-main"
            type="button" role="tab">
      <i class="fas fa-chart-line me-1"></i> الرئيسية
    </button>
  </li>
  <li class="nav-item" role="presentation">
    <button class="nav-link" id="tab-ext-sales-btn"
            data-bs-toggle="tab" data-bs-target="#tab-ext-sales"
            type="button" role="tab"
            data-loaded="false">
      <i class="fas fa-handshake me-1"></i> المبيعات الخارجية
      <span class="badge bg-success ms-1 badge-new">جديد</span>
    </button>
  </li>
</ul>

<div class="tab-content" id="boardMainTabsContent">

  {# ── Tab 1: Main (existing content unchanged) ── #}
  <div class="tab-pane fade show active" id="tab-main" role="tabpanel">
    {# … all existing dashboard content here … #}
  </div>

  {# ── Tab 2: External Sales ─────────────────────── #}
  <div class="tab-pane fade" id="tab-ext-sales" role="tabpanel">
    {% include "board_dashboard/partials/external_sales_tab.html" %}
  </div>

</div>
```

---

### 27.3 New Partial — `board_dashboard/partials/external_sales_tab.html`

This partial contains the nested tab bar for the three external sales departments (Wholesale and Projects are placeholder stubs):

```django
{# board_dashboard/partials/external_sales_tab.html #}
<div dir="rtl">

  {# ── Dept sub-tabs ──────────────────────────────────────── #}
  <ul class="nav nav-pills mb-4 gap-2" id="extSalesDeptTabs" role="tablist">
    <li class="nav-item">
      <button class="nav-link active" id="dept-overview-btn"
              data-bs-toggle="pill" data-bs-target="#dept-overview" type="button">
        <i class="fas fa-globe me-1"></i> نظرة عامة
      </button>
    </li>
    <li class="nav-item">
      <button class="nav-link" id="dept-decorator-btn"
              data-bs-toggle="pill" data-bs-target="#dept-decorator" type="button"
              data-loaded="false" onclick="loadDecoratorBoardData(this)">
        <i class="fas fa-paint-brush me-1"></i> مهندسو الديكور
      </button>
    </li>
    <li class="nav-item">
      <button class="nav-link disabled" type="button" title="قريباً">
        <i class="fas fa-boxes me-1"></i> الجملة
        <span class="badge bg-secondary ms-1">قريباً</span>
      </button>
    </li>
    <li class="nav-item">
      <button class="nav-link disabled" type="button" title="قريباً">
        <i class="fas fa-building me-1"></i> المشاريع
        <span class="badge bg-secondary ms-1">قريباً</span>
      </button>
    </li>
  </ul>

  <div class="tab-content">

    {# ── Sub-tab 1: General Overview (static summary) ─── #}
    <div class="tab-pane fade show active" id="dept-overview">
      {% include "board_dashboard/partials/ext_sales_overview.html" %}
    </div>

    {# ── Sub-tab 2: Decorator Engineers ───────────────── #}
    <div class="tab-pane fade" id="dept-decorator">
      <div id="decorator-board-container">
        {# Skeleton loader shown before AJAX loads #}
        <div id="decorator-board-skeleton" class="row g-3">
          {% for i in "12345" %}
          <div class="col-lg-2 col-md-4 col-6">
            <div class="card skeleton-card"><div class="card-body p-4"></div></div>
          </div>
          {% endfor %}
        </div>
        {# Static HTML — JS populates values after AJAX fetch #}
        <div id="decorator-board-content" class="d-none">
          {% include "board_dashboard/partials/decorator_board.html" %}
        </div>
      </div>
    </div>

  </div>
</div>
```

---

### 27.4 General Overview Partial — `ext_sales_overview.html`

Simple summary cards that load server-side (no AJAX needed — lightweight counts):

```django
{# Rendered by BoardDashboardView.get_context_data() adding ext_sales_summary #}
<div class="row g-3 mb-4">
  <div class="col-lg-3 col-md-6">
    <div class="kpi-card">
      <div class="kpi-icon" style="background:#e0f2fe">
        <i class="fas fa-paint-brush text-info"></i>
      </div>
      <div class="kpi-value">{{ ext_sales_summary.total_decorator_engineers }}</div>
      <div class="kpi-label">إجمالي مهندسي الديكور</div>
    </div>
  </div>
  <div class="col-lg-3 col-md-6">
    <div class="kpi-card">
      <div class="kpi-icon" style="background:#dcfce7">
        <i class="fas fa-user-check text-success"></i>
      </div>
      <div class="kpi-value">{{ ext_sales_summary.active_engineers }}</div>
      <div class="kpi-label">مهندسون نشطون</div>
    </div>
  </div>
  <div class="col-lg-3 col-md-6">
    <div class="kpi-card">
      <div class="kpi-icon" style="background:#fef3c7">
        <i class="fas fa-clock text-warning"></i>
      </div>
      <div class="kpi-value">{{ ext_sales_summary.no_contact_engineers }}</div>
      <div class="kpi-label">بدون تواصل (60+ يوم)</div>
    </div>
  </div>
  <div class="col-lg-3 col-md-6">
    <div class="kpi-card">
      <div class="kpi-icon" style="background:#fce7f3">
        <i class="fas fa-coins text-danger"></i>
      </div>
      <div class="kpi-value">{{ ext_sales_summary.pending_commissions_value|floatformat:0 }}</div>
      <div class="kpi-label">عمولات معلقة (ريال)</div>
    </div>
  </div>
</div>

{# New this month row #}
<div class="row g-3">
  <div class="col-lg-4">
    <div class="card shadow-sm h-100">
      <div class="card-header fw-bold small bg-transparent">
        <i class="fas fa-user-plus text-primary me-1"></i>
        مهندسون أُضيفوا هذا الشهر
      </div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-sm table-hover mb-0">
            <thead class="table-light"><tr>
              <th>الاسم</th><th>الفرع</th><th>التاريخ</th>
            </tr></thead>
            <tbody>
              {% for eng in ext_sales_summary.new_this_month %}
              <tr>
                <td><a href="{% url 'external_sales:engineer_detail' eng.pk %}" class="text-decoration-none">
                  {{ eng.customer.name }}</a></td>
                <td>{{ eng.customer.branch.name|default:"—" }}</td>
                <td>{{ eng.created_at|date:"d/m" }}</td>
              </tr>
              {% empty %}
              <tr><td colspan="3" class="text-center text-muted small py-3">لا يوجد إضافات هذا الشهر</td></tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <div class="col-lg-8">
    <div class="card shadow-sm h-100">
      <div class="card-header fw-bold small bg-transparent">
        <i class="fas fa-chart-bar text-primary me-1"></i>
        إيرادات مهندسي الديكور — آخر 6 أشهر
      </div>
      <div class="card-body">
        <canvas id="extSalesOverviewChart" height="80"></canvas>
      </div>
    </div>
  </div>
</div>
```

---

### 27.5 Decorator Board Data — AJAX View

New endpoint in `board_dashboard/api_views.py`:

```python
# board_dashboard/api_views.py

class BoardDecoratorDashboardView(BoardAccessMixin, View):
    """
    Single endpoint that returns all data for the decorator board tab
    GET /board-level/api/decorator/
    Returns JSON: {kpis, new_engineers, contact_status_breakdown,
                   priority_breakdown, top_engineers, recent_activity,
                   monthly_trend, inactive_list}
    """
    def get(self, request):
        from external_sales.models import (
            DecoratorEngineerProfile, EngineerContactLog, EngineerLinkedOrder
        )
        from django.db.models import Sum, Count, Q
        from django.db.models.functions import TruncMonth
        from datetime import date, timedelta

        today         = date.today()
        month_start   = today.replace(day=1)
        six_months_ago = today - timedelta(days=180)
        sixty_days_ago = today - timedelta(days=60)
        thirty_days_ago = today - timedelta(days=30)

        # ── KPI Cards ──────────────────────────────────────────
        total_engineers   = DecoratorEngineerProfile.objects.count()
        active_engineers  = DecoratorEngineerProfile.objects.filter(
            customer__status='active').count()
        new_this_month    = DecoratorEngineerProfile.objects.filter(
            created_at__date__gte=month_start).count()
        new_last_30_days  = DecoratorEngineerProfile.objects.filter(
            created_at__date__gte=thirty_days_ago).count()

        # Contact status
        contacted_30d     = DecoratorEngineerProfile.objects.filter(
            last_contact_date__gte=thirty_days_ago).count()
        never_contacted   = DecoratorEngineerProfile.objects.filter(
            last_contact_date__isnull=True).count()
        inactive_60d      = DecoratorEngineerProfile.objects.filter(
            last_contact_date__lt=sixty_days_ago).count()

        # Commissions
        pending_comm = EngineerLinkedOrder.objects.filter(
            commission_status='pending'
        ).aggregate(total=Sum('commission_value'))['total'] or 0

        paid_comm_month = EngineerLinkedOrder.objects.filter(
            commission_status='paid',
            commission_paid_at__date__gte=month_start
        ).aggregate(total=Sum('commission_value'))['total'] or 0

        # ── Recently Added (last 10) ───────────────────────────
        new_engineers = list(
            DecoratorEngineerProfile.objects.filter(
                created_at__date__gte=thirty_days_ago
            ).select_related('customer', 'customer__branch', 'assigned_staff')
            .order_by('-created_at')[:10]
            .values(
                'pk', 'designer_code',
                'customer__name', 'customer__phone',
                'customer__branch__name',
                'created_at',
                'last_contact_date',
                'priority',
                'assigned_staff__first_name', 'assigned_staff__last_name',
            )
        )
        # Annotate contact status for each new engineer
        for e in new_engineers:
            e['contact_status'] = (
                'contacted' if e['last_contact_date'] else 'not_contacted'
            )
            e['created_at'] = str(e['created_at'])[:10] if e['created_at'] else ''
            e['last_contact_date'] = str(e['last_contact_date']) if e['last_contact_date'] else None

        # ── Contact Status Breakdown (Donut Chart) ─────────────
        contact_breakdown = {
            'contacted_30d':   contacted_30d,
            'inactive_31_60d': DecoratorEngineerProfile.objects.filter(
                last_contact_date__lt=thirty_days_ago,
                last_contact_date__gte=sixty_days_ago).count(),
            'inactive_60d_plus': inactive_60d,
            'never_contacted': never_contacted,
        }

        # ── Priority Breakdown ─────────────────────────────────
        priority_breakdown = list(
            DecoratorEngineerProfile.objects.values('priority')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # ── Top 5 Engineers this month ─────────────────────────
        top_engineers = list(
            DecoratorEngineerProfile.objects.filter(
                linked_orders__linked_at__date__gte=month_start
            ).annotate(
                month_orders=Count('linked_orders'),
                month_value=Sum('linked_orders__order__total_amount'),
            ).order_by('-month_value')
            .select_related('customer')[:5]
            .values('pk', 'designer_code', 'customer__name',
                    'month_orders', 'month_value',
                    'priority', 'last_contact_date')
        )

        # ── Monthly Trend (last 6 months) ─────────────────────
        monthly_new = list(
            DecoratorEngineerProfile.objects.filter(
                created_at__date__gte=six_months_ago
            ).annotate(month=TruncMonth('created_at'))
            .values('month').annotate(count=Count('id')).order_by('month')
        )
        monthly_orders = list(
            EngineerLinkedOrder.objects.filter(
                linked_at__date__gte=six_months_ago
            ).annotate(month=TruncMonth('linked_at'))
            .values('month').annotate(count=Count('id'), value=Sum('order__total_amount'))
            .order_by('month')
        )
        for row in monthly_new + monthly_orders:
            row['month'] = str(row['month'])[:7] if row.get('month') else ''

        # ── Inactive List ─────────────────────────────────────
        inactive_list = list(
            DecoratorEngineerProfile.objects.filter(
                last_contact_date__lt=sixty_days_ago
            ).select_related('customer', 'assigned_staff')
            .order_by('last_contact_date')[:8]
            .values(
                'pk', 'designer_code', 'customer__name', 'customer__phone',
                'last_contact_date', 'priority',
                'assigned_staff__first_name', 'assigned_staff__last_name',
            )
        )
        for e in inactive_list:
            e['last_contact_date'] = str(e['last_contact_date']) if e['last_contact_date'] else None
            days_since = (today - date.fromisoformat(e['last_contact_date'])).days \
                          if e['last_contact_date'] else None
            e['days_since_contact'] = days_since

        return JsonResponse({
            'kpis': {
                'total_engineers':    total_engineers,
                'active_engineers':   active_engineers,
                'new_this_month':     new_this_month,
                'new_last_30_days':   new_last_30_days,
                'contacted_30d':      contacted_30d,
                'never_contacted':    never_contacted,
                'inactive_60d':       inactive_60d,
                'pending_commission': float(pending_comm),
                'paid_this_month':    float(paid_comm_month),
            },
            'new_engineers':        new_engineers,
            'contact_breakdown':    contact_breakdown,
            'priority_breakdown':   priority_breakdown,
            'top_engineers':        top_engineers,
            'monthly_trend': {
                'new':    monthly_new,
                'orders': monthly_orders,
            },
            'inactive_list':        inactive_list,
        })
```

Add URL in `board_dashboard/urls.py`:
```python
path('api/decorator/', api_views.BoardDecoratorDashboardView.as_view(), name='api_decorator'),
```

---

### 27.6 Decorator Board Tab HTML — `board_dashboard/partials/decorator_board.html`

This HTML is **injected via AJAX** into `#decorator-board-content` on first click:

```django
{# Injected via AJAX — receives `data` JSON from /board-level/api/decorator/ #}

{# ── Row 1: KPI Cards ──────────────────────────────────────── #}
<div class="row g-3 mb-4" id="dec-kpi-row">
  <!-- 1 Total -->
  <div class="col-6 col-md-4 col-lg-2">
    <div class="kpi-card border-start border-primary border-3">
      <div class="kpi-icon bg-primary bg-opacity-10">
        <i class="fas fa-id-badge text-primary"></i>
      </div>
      <div class="kpi-value" id="kpi-total">—</div>
      <div class="kpi-label">إجمالي المهندسين</div>
    </div>
  </div>
  <!-- 2 Active -->
  <div class="col-6 col-md-4 col-lg-2">
    <div class="kpi-card border-start border-success border-3">
      <div class="kpi-icon bg-success bg-opacity-10">
        <i class="fas fa-user-check text-success"></i>
      </div>
      <div class="kpi-value" id="kpi-active">—</div>
      <div class="kpi-label">نشطون</div>
    </div>
  </div>
  <!-- 3 New this month -->
  <div class="col-6 col-md-4 col-lg-2">
    <div class="kpi-card border-start border-info border-3">
      <div class="kpi-icon bg-info bg-opacity-10">
        <i class="fas fa-user-plus text-info"></i>
      </div>
      <div class="kpi-value" id="kpi-new">—</div>
      <div class="kpi-label">جديد هذا الشهر</div>
    </div>
  </div>
  <!-- 4 Never contacted -->
  <div class="col-6 col-md-4 col-lg-2">
    <div class="kpi-card border-start border-warning border-3">
      <div class="kpi-icon bg-warning bg-opacity-10">
        <i class="fas fa-phone-slash text-warning"></i>
      </div>
      <div class="kpi-value" id="kpi-never">—</div>
      <div class="kpi-label">لم يُتواصل معهم</div>
    </div>
  </div>
  <!-- 5 Inactive 60d -->
  <div class="col-6 col-md-4 col-lg-2">
    <div class="kpi-card border-start border-danger border-3">
      <div class="kpi-icon bg-danger bg-opacity-10">
        <i class="fas fa-user-clock text-danger"></i>
      </div>
      <div class="kpi-value" id="kpi-inactive60">—</div>
      <div class="kpi-label">غير نشط 60+ يوم</div>
    </div>
  </div>
  <!-- 6 Pending Commission -->
  <div class="col-6 col-md-4 col-lg-2">
    <div class="kpi-card border-start border-secondary border-3">
      <div class="kpi-icon bg-secondary bg-opacity-10">
        <i class="fas fa-coins text-secondary"></i>
      </div>
      <div class="kpi-value" id="kpi-commission">—</div>
      <div class="kpi-label">عمولات معلقة (ريال)</div>
    </div>
  </div>
</div>

{# ── Row 2: Charts ─────────────────────────────────────────── #}
<div class="row g-3 mb-4">
  <!-- Contact Status Donut -->
  <div class="col-lg-4">
    <div class="card shadow-sm h-100">
      <div class="card-header small fw-bold bg-transparent">
        <i class="fas fa-phone-alt me-1 text-primary"></i> حالة التواصل مع المهندسين
      </div>
      <div class="card-body d-flex align-items-center justify-content-center">
        <canvas id="decContactDonut" style="max-height:220px"></canvas>
      </div>
    </div>
  </div>
  <!-- Priority Breakdown Donut -->
  <div class="col-lg-4">
    <div class="card shadow-sm h-100">
      <div class="card-header small fw-bold bg-transparent">
        <i class="fas fa-star me-1 text-warning"></i> توزيع الأولوية
      </div>
      <div class="card-body d-flex align-items-center justify-content-center">
        <canvas id="decPriorityDonut" style="max-height:220px"></canvas>
      </div>
    </div>
  </div>
  <!-- Monthly Trend Line -->
  <div class="col-lg-4">
    <div class="card shadow-sm h-100">
      <div class="card-header small fw-bold bg-transparent">
        <i class="fas fa-chart-line me-1 text-success"></i> الاتجاه الشهري
      </div>
      <div class="card-body">
        <canvas id="decMonthlyTrend" style="max-height:220px"></canvas>
      </div>
    </div>
  </div>
</div>

{# ── Row 3: Tables ────────────────────────────────────────── #}
<div class="row g-3 mb-4">

  {# Recently Added Engineers #}
  <div class="col-lg-6">
    <div class="card shadow-sm">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span class="fw-bold small">
          <i class="fas fa-user-plus text-success me-1"></i>
          المهندسون المضافون مؤخراً (آخر 30 يوم)
        </span>
        <a href="/external-sales/decorator/engineers/?filter=new_30d"
           class="btn btn-outline-primary btn-xs" target="_blank">
          عرض الكل <i class="fas fa-external-link-alt ms-1"></i>
        </a>
      </div>
      <div class="card-body p-0">
        <div class="table-responsive" style="max-height:300px; overflow-y:auto">
          <table class="table table-sm table-hover mb-0 small" id="decNewEngTable">
            <thead class="table-light sticky-top">
              <tr>
                <th>الاسم</th>
                <th>الفرع</th>
                <th>تاريخ الإضافة</th>
                <th>حالة التواصل</th>
                <th>موظف المتابعة</th>
              </tr>
            </thead>
            <tbody>
              {# Populated by JS #}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  {# Inactive Engineers Alert #}
  <div class="col-lg-6">
    <div class="card shadow-sm border-warning">
      <div class="card-header bg-warning bg-opacity-10 fw-bold small text-warning-emphasis">
        <i class="fas fa-exclamation-triangle me-1"></i>
        مهندسون يحتاجون متابعة عاجلة (60+ يوم بلا تواصل)
      </div>
      <div class="card-body p-0">
        <div class="table-responsive" style="max-height:300px; overflow-y:auto">
          <table class="table table-sm table-hover mb-0 small" id="decInactiveTable">
            <thead class="table-light sticky-top">
              <tr>
                <th>الاسم</th>
                <th>أيام بلا تواصل</th>
                <th>الأولوية</th>
                <th>موظف المتابعة</th>
                <th>إجراء</th>
              </tr>
            </thead>
            <tbody>
              {# Populated by JS #}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

</div>

{# ── Row 4: Top Performers ────────────────────────────────── #}
<div class="row g-3">
  <div class="col-12">
    <div class="card shadow-sm">
      <div class="card-header fw-bold small bg-transparent">
        <i class="fas fa-trophy text-warning me-1"></i>
        أفضل مهندسي الديكور أداءً هذا الشهر
      </div>
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-hover mb-0 align-middle" id="decTopTable">
            <thead class="table-dark">
              <tr>
                <th>#</th><th>المهندس</th><th>الأولوية</th>
                <th>عدد الطلبات</th><th>إجمالي الإيرادات</th>
                <th>آخر تواصل</th><th>الملف</th>
              </tr>
            </thead>
            <tbody>
              {# Populated by JS #}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>
```

---

### 27.7 JavaScript — AJAX Load & Chart Rendering

Add to `board_dashboard/dashboard.html` (inside `{% block extra_js %}`):

```javascript
const PRIORITY_LABELS = {vip:'VIP',active:'نشط',regular:'عادي',cold:'فاتر'};
const PRIORITY_COLORS = {vip:'#dc2626',active:'#16a34a',regular:'#2563eb',cold:'#9ca3af'};
const CONTACT_LABELS  = ['تواصل خلال 30 يوم','31-60 يوم','60+ يوم','لم يُتواصل معه'];
const CONTACT_COLORS  = ['#16a34a','#f59e0b','#dc2626','#9ca3af'];

function loadDecoratorBoardData(btn) {
  if (btn.dataset.loaded === 'true') return;
  btn.dataset.loaded = 'true';

  fetch('{% url "board_dashboard:api_decorator" %}')
    .then(r => r.json())
    .then(data => {
      renderDecoratorKPIs(data.kpis);
      renderDecoratorCharts(data);
      renderDecoratorTables(data);

      document.getElementById('decorator-board-skeleton').classList.add('d-none');
      document.getElementById('decorator-board-content').classList.remove('d-none');
    })
    .catch(() => {
      document.getElementById('decorator-board-container').innerHTML =
        '<div class="alert alert-danger">تعذّر تحميل البيانات. يرجى إعادة المحاولة.</div>';
    });
}

function renderDecoratorKPIs(kpis) {
  document.getElementById('kpi-total').textContent      = kpis.total_engineers;
  document.getElementById('kpi-active').textContent     = kpis.active_engineers;
  document.getElementById('kpi-new').textContent        = kpis.new_this_month;
  document.getElementById('kpi-never').textContent      = kpis.never_contacted;
  document.getElementById('kpi-inactive60').textContent = kpis.inactive_60d;
  document.getElementById('kpi-commission').textContent =
    Number(kpis.pending_commission).toLocaleString('ar-SA', {maximumFractionDigits:0});
}

function renderDecoratorCharts(data) {
  // Contact status donut
  new Chart(document.getElementById('decContactDonut'), {
    type: 'doughnut',
    data: {
      labels: CONTACT_LABELS,
      datasets: [{
        data: [
          data.contact_breakdown.contacted_30d,
          data.contact_breakdown.inactive_31_60d,
          data.contact_breakdown.inactive_60d_plus,
          data.contact_breakdown.never_contacted,
        ],
        backgroundColor: CONTACT_COLORS,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      plugins: {legend: {position:'bottom', labels:{font:{size:11}}}}
    }
  });

  // Priority donut
  const prLabels = data.priority_breakdown.map(p => PRIORITY_LABELS[p.priority] || p.priority);
  const prColors = data.priority_breakdown.map(p => PRIORITY_COLORS[p.priority] || '#6b7280');
  new Chart(document.getElementById('decPriorityDonut'), {
    type: 'doughnut',
    data: {
      labels: prLabels,
      datasets: [{data: data.priority_breakdown.map(p=>p.count), backgroundColor: prColors, borderWidth:2}]
    },
    options: {responsive:true, maintainAspectRatio:true,
      plugins:{legend:{position:'bottom',labels:{font:{size:11}}}}}
  });

  // Monthly trend line
  const months = [...new Set([
    ...data.monthly_trend.new.map(r=>r.month),
    ...data.monthly_trend.orders.map(r=>r.month)
  ])].sort();
  const newMap   = Object.fromEntries(data.monthly_trend.new.map(r=>[r.month, r.count]));
  const ordMap   = Object.fromEntries(data.monthly_trend.orders.map(r=>[r.month, r.count]));
  new Chart(document.getElementById('decMonthlyTrend'), {
    type: 'line',
    data: {
      labels: months.map(m => {const d=new Date(m+'-01');
        return d.toLocaleDateString('ar-SA',{month:'short',year:'2-digit'});}),
      datasets: [
        {label:'مهندسون جدد', data: months.map(m=>newMap[m]||0),
          borderColor:'#3b82f6', backgroundColor:'rgba(59,130,246,0.1)', tension:0.4, fill:true},
        {label:'طلبات مرتبطة', data: months.map(m=>ordMap[m]||0),
          borderColor:'#10b981', backgroundColor:'rgba(16,185,129,0.1)', tension:0.4, fill:true},
      ]
    },
    options: {responsive:true, maintainAspectRatio:true,
      plugins:{legend:{position:'bottom'}},
      scales:{y:{beginAtZero:true, ticks:{precision:0}}}}
  });
}

const PRIORITY_BADGE = {
  vip:     '<span class="badge bg-danger">VIP</span>',
  active:  '<span class="badge bg-success">نشط</span>',
  regular: '<span class="badge bg-primary">عادي</span>',
  cold:    '<span class="badge bg-secondary">فاتر</span>',
};
const CONTACT_BADGE = {
  contacted:     '<span class="badge bg-success">تم التواصل</span>',
  not_contacted: '<span class="badge bg-danger">لم يُتواصل</span>',
};

function renderDecoratorTables(data) {
  // New engineers table
  const newTbody = document.querySelector('#decNewEngTable tbody');
  newTbody.innerHTML = data.new_engineers.length === 0
    ? '<tr><td colspan="5" class="text-center text-muted py-3">لا يوجد مهندسون جدد</td></tr>'
    : data.new_engineers.map(e => `
        <tr>
          <td><a href="/external-sales/decorator/engineers/${e.pk}/" class="text-decoration-none fw-semibold">
            ${e['customer__name']}</a>
            <div class="text-muted" style="font-size:0.7rem">${e.designer_code}</div>
          </td>
          <td>${e['customer__branch__name'] || '—'}</td>
          <td>${e.created_at}</td>
          <td>${CONTACT_BADGE[e.contact_status] || '—'}</td>
          <td>${(e['assigned_staff__first_name']||'')+' '+(e['assigned_staff__last_name']||'')||'غير محدد'}</td>
        </tr>`).join('');

  // Inactive engineers table
  const inactTbody = document.querySelector('#decInactiveTable tbody');
  inactTbody.innerHTML = data.inactive_list.length === 0
    ? '<tr><td colspan="5" class="text-center text-muted py-3">🎉 جميع المهندسين نشطون</td></tr>'
    : data.inactive_list.map(e => `
        <tr class="${e.days_since_contact > 90 ? 'table-danger' : 'table-warning'}">
          <td><a href="/external-sales/decorator/engineers/${e.pk}/" class="text-decoration-none fw-semibold">
            ${e['customer__name']}</a></td>
          <td><span class="badge bg-danger">${e.days_since_contact} يوم</span></td>
          <td>${PRIORITY_BADGE[e.priority] || e.priority}</td>
          <td>${(e['assigned_staff__first_name']||'')+' '+(e['assigned_staff__last_name']||'')||'غير محدد'}</td>
          <td><a href="/external-sales/decorator/engineers/${e.pk}/contact/add/"
                 class="btn btn-warning btn-sm" target="_blank">
            <i class="fas fa-phone"></i> تواصل</a></td>
        </tr>`).join('');

  // Top performers table
  const topTbody = document.querySelector('#decTopTable tbody');
  topTbody.innerHTML = data.top_engineers.length === 0
    ? '<tr><td colspan="7" class="text-center text-muted py-3">لا توجد بيانات هذا الشهر</td></tr>'
    : data.top_engineers.map((e, i) => `
        <tr>
          <td><span class="badge bg-dark">${i+1}</span></td>
          <td><span class="fw-semibold">${e['customer__name']}</span>
            <div class="text-muted" style="font-size:0.7rem">${e.designer_code}</div></td>
          <td>${PRIORITY_BADGE[e.priority] || e.priority}</td>
          <td><span class="badge bg-info text-dark">${e.month_orders || 0}</span></td>
          <td class="fw-bold text-success">
            ${Number(e.month_value || 0).toLocaleString('ar-SA',{maximumFractionDigits:0})} ريال</td>
          <td>${e.last_contact_date || '<span class="text-danger">لم يُتواصل</span>'}</td>
          <td><a href="/external-sales/decorator/engineers/${e.pk}/"
                 class="btn btn-outline-primary btn-sm" target="_blank">
            <i class="fas fa-eye"></i></a></td>
        </tr>`).join('');
}

// Load overview chart when external-sales tab is first opened
document.getElementById('tab-ext-sales-btn').addEventListener('shown.bs.tab', function () {
  if (this.dataset.overviewLoaded) return;
  this.dataset.overviewLoaded = 'true';
  // fetch six-month revenue summary for the overview line chart
  fetch('{% url "board_dashboard:api_decorator" %}')
    .then(r => r.json())
    .then(data => {
      const months = data.monthly_trend.orders.map(r => r.month);
      const values = data.monthly_trend.orders.map(r => Number(r.value || 0));
      new Chart(document.getElementById('extSalesOverviewChart'), {
        type: 'bar',
        data: {
          labels: months.map(m => {const d=new Date(m+'-01');
            return d.toLocaleDateString('ar-SA',{month:'short',year:'2-digit'});}),
          datasets: [{
            label: 'إيرادات مهندسي الديكور (ريال)',
            data: values,
            backgroundColor: 'rgba(59,130,246,0.7)',
            borderRadius: 6,
          }]
        },
        options: {responsive:true, plugins:{legend:{display:false}},
          scales:{y:{beginAtZero:true}}}
      });
    });
});
```

---

### 27.8 `BoardDashboardView` — Add `ext_sales_summary` to Context

In `board_dashboard/views.py`, add to `get_context_data()`:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    # ... existing code ...

    # External Sales Summary (lightweight — for overview tab, server-side)
    try:
        from external_sales.models import DecoratorEngineerProfile, EngineerLinkedOrder
        from datetime import date, timedelta
        from django.db.models import Sum, Count

        today = date.today()
        month_start = today.replace(day=1)
        sixty_days_ago = today - timedelta(days=60)

        context['ext_sales_summary'] = {
            'total_decorator_engineers': DecoratorEngineerProfile.objects.count(),
            'active_engineers': DecoratorEngineerProfile.objects.filter(
                customer__status='active').count(),
            'no_contact_engineers': DecoratorEngineerProfile.objects.filter(
                last_contact_date__lt=sixty_days_ago).count(),
            'pending_commissions_value': EngineerLinkedOrder.objects.filter(
                commission_status='pending'
            ).aggregate(t=Sum('commission_value'))['t'] or 0,
            'new_this_month': DecoratorEngineerProfile.objects.filter(
                created_at__date__gte=month_start
            ).select_related('customer', 'customer__branch')
            .order_by('-created_at')[:8],
        }
    except Exception:
        # external_sales app not yet installed — graceful fallback
        context['ext_sales_summary'] = None

    return context
```

> **ملاحظة**: الـ `try/except` يضمن أن داشبورد مجلس الإدارة لا ينكسر إذا كان `external_sales` لم يُطبَّق بعد.

---

### 27.9 CSS Additions for New Tabs

Add to `board_dashboard/dashboard.html` inside `{% block extra_css %}`:

```css
/* External Sales Tab */
.board-main-tabs .nav-link {
    color: rgba(255,255,255,0.6);
    border: none;
    border-bottom: 3px solid transparent;
    border-radius: 0;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 0.85rem;
    transition: all 0.2s;
    background: transparent;
}
.board-main-tabs .nav-link:hover {
    color: rgba(255,255,255,0.9);
    background: rgba(255,255,255,0.06);
}
.board-main-tabs .nav-link.active {
    color: #fff;
    border-bottom-color: #3b82f6;
    background: rgba(59,130,246,0.1);
}
.board-main-tabs {
    border-bottom: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 0 !important;
}
.badge-new {
    font-size: 0.6rem;
    padding: 2px 6px;
    vertical-align: middle;
    animation: pulse-badge 2s infinite;
}
@keyframes pulse-badge {
    0%,100% { opacity:1; } 50% { opacity:0.5; }
}
.skeleton-card {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 12px;
    min-height: 90px;
}
@keyframes shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
```

---

### 27.10 Summary of All New Files & Changes for §27

| File | Change |
|---|---|
| `board_dashboard/views.py` | Add `ext_sales_summary` context in `get_context_data()` |
| `board_dashboard/api_views.py` | Add `BoardDecoratorDashboardView` |
| `board_dashboard/urls.py` | Add `api/decorator/` endpoint |
| `board_dashboard/templates/board_dashboard/dashboard.html` | Add tab bar + wrap existing content + CSS + JS |
| `board_dashboard/templates/board_dashboard/partials/external_sales_tab.html` | NEW — nested dept tabs |
| `board_dashboard/templates/board_dashboard/partials/ext_sales_overview.html` | NEW — overview sub-tab |
| `board_dashboard/templates/board_dashboard/partials/decorator_board.html` | NEW — decorator AJAX content |

> **الشرح الكامل**: هنضيف تبويبة "المبيعات الخارجية" في أعلى داشبورد مجلس الإدارة. بداخلها تبويبة "نظرة عامة" تعرض 4 KPI cards وجدول المهندسين الجدد + رسم بياني للإيرادات. وتبويبة "مهندسو الديكور" تُحمَّل عبر AJAX وتعرض: 6 KPIs، دونات حالة التواصل، دونات توزيع الأولوية، منحنى شهري، جدول المهندسين المضافين مؤخراً مع حالة تواصل كل واحد، جدول تحذيري للمهندسين الخاملين (60+ يوم) مع زر "تواصل الآن"، وجدول أفضل المهندسين أداءً هذا الشهر.

---

## 28. Updated Migrations Checklist

```bash
# 1. accounts — new role flags
python manage.py makemigrations accounts

# 2. external_sales — all models including new fields from §18–§21
python manage.py makemigrations external_sales

# 3. board_dashboard — new widget keys (data migration only, no schema change needed
#    if using existing BoardWidgetSettings.name CharField)
python manage.py makemigrations board_dashboard --empty --name add_decorator_widgets
# then fill migration with BoardWidgetSettings.objects.get_or_create() calls

# 4. Apply all
python manage.py migrate
```

---

## الملخص الكامل بالعربية

هذا البرومبت يصف بناء **مديول إدارة المبيعات الخارجية** بتطبيق Django جديد اسمه `external_sales`.

**المرحلة الأولى: قسم مهندسي الديكور تحتوي على:**

1. **5 نماذج جديدة**:
   - `DecoratorEngineerProfile`: ملف المهندس (بيانات خاصة بالقسم، أولوية، موظف متابعة)
   - `EngineerLinkedCustomer`: ربط عملاء أفراد بالمهندس يدوياً مع نسبة عمولة
   - `EngineerLinkedOrder`: ربط طلبات بالمهندس مع إدارة العمولة (معلقة/معتمدة/مدفوعة)
   - `EngineerContactLog`: سجل كامل للتواصل (مكالمات، مواعيد، واتساب، زيارات) مع جدولة المتابعة
   - `EngineerMaterialInterest`: الخامات والأقمشة المفضلة للمهندس

2. **إشعار فوري** لمدير القسم عند إضافة أي مهندس ديكور جديد من أي فرع

3. **صفحة تفاصيل المهندس** بـ 5 تبويبات: نظرة عامة، العملاء، الطلبات، سجل التواصل، العمولات

4. **لوحة تحكم القسم** مع KPIs ومن يحتاج متابعة عاجلة وآخر النشاطات

5. **تكامل مع باقي التطبيقات**: صفحة العميل تُظهر رابط ملف المهندس، صفحة الطلب تُظهر المهندس المرتبط والعمولة

6. **دورين جديدين** على موديل المستخدم: مدير القسم وموظف القسم

7. **صفحة الطلبات المفلترة** تعرض طلبات مهندسي الديكور فقط أو الطلبات المرتبطة بهم

كل شيء بـ Bootstrap 5 وبنفس ثيم المشروع الحالي.
