"""
نظام تتبع شامل لجميع العمليات الحساسة
Audit Trail متقدم — يسجل جميع عمليات CRUD والأحداث الأمنية
"""

import json
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)

User = get_user_model()


class AuditLog(models.Model):
    """
    سجل تدقيق شامل لجميع العمليات
    يتتبع كل إنشاء وتعديل وحذف مع القيم القديمة والجديدة
    """

    ACTION_TYPES = (
        ("CREATE", "إنشاء"),
        ("UPDATE", "تحديث"),
        ("DELETE", "حذف"),
        ("LOGIN", "تسجيل دخول"),
        ("LOGOUT", "تسجيل خروج"),
        ("PERMISSION_CHANGE", "تغيير صلاحيات"),
        ("SECURITY_EVENT", "حدث أمني"),
        ("DATA_EXPORT", "تصدير بيانات"),
        ("SETTINGS_CHANGE", "تغيير إعدادات"),
        ("VIEW", "عرض"),
        ("BULK_UPDATE", "تحديث جماعي"),
        ("BULK_DELETE", "حذف جماعي"),
    )

    SEVERITY_LEVELS = (
        ("INFO", "معلومات"),
        ("WARNING", "تحذير"),
        ("ERROR", "خطأ"),
        ("CRITICAL", "حرج"),
    )

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, verbose_name="المستخدم",
        related_name="audit_logs",
    )
    username = models.CharField(
        max_length=150, blank=True, verbose_name="اسم المستخدم",
        help_text="يُحفظ كنسخة نصية في حال حذف المستخدم",
    )
    action = models.CharField(
        max_length=50, choices=ACTION_TYPES, verbose_name="نوع العملية"
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default="INFO",
        verbose_name="مستوى الخطورة",
    )
    # تفاصيل النموذج
    app_label = models.CharField(max_length=100, blank=True, verbose_name="التطبيق")
    model_name = models.CharField(max_length=100, blank=True, verbose_name="اسم النموذج")
    object_id = models.CharField(max_length=255, blank=True, verbose_name="معرف الكائن")
    object_repr = models.CharField(
        max_length=500, blank=True, verbose_name="وصف الكائن",
        help_text="تمثيل نصي للكائن وقت التسجيل",
    )
    description = models.TextField(blank=True, verbose_name="الوصف")
    # القيم القديمة والجديدة (JSON)
    old_value = models.JSONField(null=True, blank=True, verbose_name="القيمة القديمة")
    new_value = models.JSONField(null=True, blank=True, verbose_name="القيمة الجديدة")
    changed_fields = models.JSONField(
        null=True, blank=True, verbose_name="الحقول المتغيرة",
        help_text="قائمة بأسماء الحقول التي تغيرت",
    )
    # معلومات الاتصال
    ip_address = models.GenericIPAddressField(null=True, verbose_name="عنوان IP")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    url_path = models.CharField(max_length=500, blank=True, verbose_name="المسار")
    http_method = models.CharField(max_length=10, blank=True, verbose_name="HTTP Method")
    session_key = models.CharField(
        max_length=40, blank=True, verbose_name="مفتاح الجلسة"
    )
    # بيانات إضافية
    extra_data = models.JSONField(
        null=True, blank=True, verbose_name="بيانات إضافية",
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ والوقت")

    class Meta:
        verbose_name = "سجل تدقيق"
        verbose_name_plural = "سجلات التدقيق"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
            models.Index(fields=["severity", "-timestamp"]),
            models.Index(fields=["app_label", "model_name", "-timestamp"]),
            models.Index(fields=["object_id", "model_name"]),
        ]

    def __str__(self):
        return f"{self.username or self.user} - {self.get_action_display()} - {self.model_name} - {self.timestamp}"

    @property
    def changes_summary(self):
        """ملخص التغييرات في شكل قابل للقراءة"""
        if not self.old_value or not self.new_value:
            return []
        changes = []
        for field in (self.changed_fields or []):
            old = self.old_value.get(field, "—")
            new = self.new_value.get(field, "—")
            changes.append({"field": field, "old": old, "new": new})
        return changes

    @classmethod
    def log(cls, user, action, description="", **kwargs):
        """
        تسجيل حدث في سجل التدقيق

        Args:
            user: المستخدم
            action: نوع العملية
            description: الوصف
            **kwargs: معاملات إضافية (model_name, object_id, old_value, new_value, etc.)
        """
        # حفظ اسم المستخدم كنص احتياطي
        if user and hasattr(user, "username") and "username" not in kwargs:
            kwargs["username"] = user.username
        try:
            return cls.objects.create(
                user=user, action=action, description=description, **kwargs
            )
        except Exception as e:
            logger.error(f"خطأ في تسجيل سجل التدقيق: {e}")
            return None

    @classmethod
    def log_model_change(cls, instance, action, user=None, old_values=None, request=None):
        """
        تسجيل تغيير على نموذج Django تلقائياً

        Args:
            instance: نسخة النموذج
            action: CREATE, UPDATE, DELETE
            user: المستخدم (يؤخذ من الطلب أو CurrentUserMiddleware)
            old_values: القيم القديمة (قاموس)
            request: الطلب HTTP (اختياري)
        """
        from accounts.middleware.current_user import get_current_request, get_current_user

        if user is None:
            user = get_current_user()
        if request is None:
            request = get_current_request()

        # بناء القيم الجديدة
        new_values = {}
        changed_fields = []

        if action in ("CREATE", "UPDATE"):
            new_values = cls._serialize_instance(instance)

        if action == "UPDATE" and old_values:
            # حساب الحقول المتغيرة فقط
            for field, new_val in new_values.items():
                old_val = old_values.get(field)
                if str(old_val) != str(new_val):
                    changed_fields.append(field)

        # معلومات الاتصال من الطلب
        ip_address = None
        user_agent = ""
        url_path = ""
        http_method = ""
        session_key = ""

        if request:
            ip_address = cls._get_client_ip(request)
            user_agent = request.META.get("HTTP_USER_AGENT", "")
            url_path = request.path
            http_method = request.method
            session_key = getattr(request.session, "session_key", "") or ""

        # تحديد مستوى الخطورة
        severity = "INFO"
        if action == "DELETE":
            severity = "WARNING"

        return cls.log(
            user=user,
            action=action,
            description=cls._build_description(instance, action),
            app_label=instance._meta.app_label,
            model_name=instance._meta.model_name,
            object_id=str(instance.pk) if instance.pk else "",
            object_repr=str(instance)[:500],
            old_value=old_values if old_values else None,
            new_value=new_values if new_values else None,
            changed_fields=changed_fields if changed_fields else None,
            ip_address=ip_address,
            user_agent=user_agent,
            url_path=url_path,
            http_method=http_method,
            session_key=session_key,
            severity=severity,
        )

    @staticmethod
    def _serialize_instance(instance):
        """تحويل نسخة النموذج إلى قاموس قابل للتسلسل (JSON)"""
        data = {}
        for field in instance._meta.concrete_fields:
            value = getattr(instance, field.attname, None)
            if value is not None:
                try:
                    json.dumps(value)
                    data[field.name] = value
                except (TypeError, ValueError):
                    data[field.name] = str(value)
            else:
                data[field.name] = None
        return data

    @staticmethod
    def _build_description(instance, action):
        """بناء وصف تلقائي للعملية"""
        model_name = instance._meta.verbose_name
        action_map = {
            "CREATE": "إنشاء",
            "UPDATE": "تعديل",
            "DELETE": "حذف",
        }
        action_text = action_map.get(action, action)
        return f"{action_text} {model_name}: {str(instance)[:200]}"

    @staticmethod
    def _get_client_ip(request):
        """الحصول على IP العميل مع دعم Cloudflare"""
        # Cloudflare
        cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")
        if cf_ip:
            return cf_ip
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class SecurityEvent(models.Model):
    """
    سجل الأحداث الأمنية
    """

    EVENT_TYPES = (
        ("LOGIN_FAILED", "فشل تسجيل دخول"),
        ("LOGIN_SUCCESS", "نجاح تسجيل دخول"),
        ("BRUTE_FORCE", "محاولة Brute Force"),
        ("SQL_INJECTION", "محاولة SQL Injection"),
        ("XSS_ATTEMPT", "محاولة XSS"),
        ("CSRF_FAILED", "فشل CSRF"),
        ("RATE_LIMIT", "تجاوز Rate Limit"),
        ("SUSPICIOUS_ACTIVITY", "نشاط مشبوه"),
        ("PERMISSION_DENIED", "رفض صلاحيات"),
    )

    event_type = models.CharField(
        max_length=50, choices=EVENT_TYPES, verbose_name="نوع الحدث"
    )
    ip_address = models.GenericIPAddressField(verbose_name="عنوان IP")
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المستخدم"
    )
    details = models.JSONField(default=dict, verbose_name="التفاصيل")
    user_agent = models.TextField(null=True, verbose_name="User Agent")
    url = models.URLField(max_length=500, null=True, verbose_name="URL")
    method = models.CharField(max_length=10, null=True, verbose_name="HTTP Method")
    blocked = models.BooleanField(default=False, verbose_name="تم الحظر")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ والوقت")

    class Meta:
        verbose_name = "حدث أمني"
        verbose_name_plural = "الأحداث الأمنية"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["event_type", "-timestamp"]),
            models.Index(fields=["ip_address", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.ip_address} - {self.timestamp}"

    @classmethod
    def log_event(cls, event_type, ip_address, **kwargs):
        """
        تسجيل حدث أمني
        """
        return cls.objects.create(
            event_type=event_type, ip_address=ip_address, **kwargs
        )


# =========================================================================
# AuditMixin — يُضاف إلى أي Model لتفعيل التتبع التلقائي عبر الإشارات
# =========================================================================

class AuditMixin(models.Model):
    """
    Mixin لتفعيل تتبع التدقيق التلقائي على أي نموذج.

    يضيف حقل updated_by ويسجل التغييرات في AuditLog تلقائياً.

    Usage:
        class Order(AuditMixin, models.Model):
            AUDIT_FIELDS = ['status', 'total_price', 'customer']  # اختياري — حقول محددة للتتبع
            ...
    """

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="آخر تعديل بواسطة",
        editable=False,
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from accounts.middleware.current_user import get_current_user

        user = get_current_user()
        if user and hasattr(user, "pk") and user.pk:
            self.updated_by = user
        super().save(*args, **kwargs)


# =========================================================================
# Middleware للـ Audit Logging التلقائي
# =========================================================================
class AuditLoggingMiddleware:
    """
    Middleware لتسجيل جميع العمليات الحساسة وعمليات CRUD التلقائية.
    يستخرج معلومات النموذج والكائن تلقائياً من مسار URL باستخدام Django resolver.
    يسجل عمليات POST/PUT/PATCH/DELETE على المسارات الحساسة.
    """

    SENSITIVE_PATHS = [
        "/admin/",
        "/accounts/",
        "/api/",
        "/orders/",
        "/customers/",
        "/manufacturing/",
        "/cutting/",
        "/installations/",
        "/accounting/",
        "/inventory/",
        "/inspections/",
        "/complaints/",
        "/factory-accounting/",
        "/installation-accounting/",
        "/backup-system/",
        "/notifications/",
    ]

    # مسارات يتم تجاهلها (AJAX, health checks, etc.)
    IGNORED_PATHS = [
        "/health",
        "/csrf-",
        "/api/monitoring/",
        "/static/",
        "/media/",
        "/ws/",
    ]

    # -------------------------------------------------------------------
    # خريطة namespace → app_label في Django
    # -------------------------------------------------------------------
    NAMESPACE_TO_APP = {
        "customers": "customers",
        "orders": "orders",
        "accounts": "accounts",
        "manufacturing": "manufacturing",
        "cutting": "cutting",
        "installations": "installations",
        "accounting": "accounting",
        "inventory": "inventory",
        "inspections": "inspections",
        "complaints": "complaints",
        "notifications": "notifications",
        "factory_accounting": "factory_accounting",
        "backup_system": "backup_system",
        "board_dashboard": "board_dashboard",
        "whatsapp": "whatsapp",
        "audit": "core",
    }

    # -------------------------------------------------------------------
    # خريطة (namespace, model_hint) → (ModelClassName, اسم عربي)
    # model_hint يُستخرج من اسم URL: customer_update → "customer"
    # -------------------------------------------------------------------
    MODEL_MAP = {
        # ---- العملاء ----
        ("customers", "customer"): ("Customer", "عميل"),
        ("customers", "category"): ("CustomerCategory", "فئة عميل"),
        ("customers", "note"): ("CustomerNote", "ملاحظة عميل"),
        # ---- الطلبات ----
        ("orders", "order"): ("Order", "طلب"),
        ("orders", "payment"): ("Payment", "دفعة"),
        ("orders", "draft"): ("OrderDraft", "مسودة طلب"),
        ("orders", "wizard"): ("OrderDraft", "مسودة طلب"),
        ("orders", "curtain"): ("OrderItem", "بند ستائر"),
        ("orders", "item"): ("OrderItem", "بند طلب"),
        ("orders", "template"): ("InvoiceTemplate", "قالب فاتورة"),
        ("orders", "contract"): ("Order", "عقد"),
        ("orders", "invoice"): ("Order", "فاتورة"),
        ("orders", "discount"): ("Order", "خصم"),
        # ---- التصنيع ----
        ("manufacturing", "order"): ("ManufacturingOrder", "أمر تصنيع"),
        ("manufacturing", "approval"): ("ManufacturingOrder", "أمر تصنيع"),
        ("manufacturing", "item"): ("ManufacturingOrderItem", "بند تصنيع"),
        ("manufacturing", "line"): ("ProductionLine", "خط إنتاج"),
        ("manufacturing", "receipt"): ("FabricReceipt", "إيصال أقمشة"),
        ("manufacturing", "fabric"): ("FabricReceipt", "أقمشة"),
        ("manufacturing", "cutting"): ("CuttingOrder", "أمر قص"),
        # ---- القص ----
        ("cutting", "order"): ("CuttingOrder", "أمر قص"),
        ("cutting", "item"): ("CuttingItem", "بند قص"),
        ("cutting", "report"): ("DailyReport", "تقرير يومي"),
        ("cutting", "warehouse"): ("CuttingOrder", "مستودع قص"),
        # ---- التركيبات ----
        ("installations", "installation"): ("InstallationSchedule", "تركيب"),
        ("installations", "modification"): ("ModificationRequest", "طلب تعديل"),
        ("installations", "team"): ("InstallationTeam", "فريق تركيب"),
        ("installations", "technician"): ("Technician", "فني"),
        ("installations", "driver"): ("Driver", "سائق"),
        ("installations", "vehicle"): ("Vehicle", "مركبة"),
        ("installations", "mission"): ("TrafficMission", "مهمة نقل"),
        ("installations", "debt"): ("CustomerDebt", "دين عميل"),
        ("installations", "request"): ("VehicleRequest", "طلب مركبة"),
        # ---- المحاسبة ----
        ("accounting", "account"): ("Account", "حساب محاسبي"),
        ("accounting", "transaction"): ("Transaction", "قيد محاسبي"),
        ("accounting", "customer"): ("Customer", "عميل"),
        ("accounting", "payment"): ("Payment", "دفعة محاسبية"),
        # ---- المخزون ----
        ("inventory", "product"): ("Product", "منتج"),
        ("inventory", "category"): ("Category", "فئة منتج"),
        ("inventory", "warehouse"): ("Warehouse", "مستودع"),
        ("inventory", "location"): ("WarehouseLocation", "موقع مستودع"),
        ("inventory", "transfer"): ("StockTransfer", "تحويل مخزون"),
        ("inventory", "stock"): ("StockTransfer", "تحويل مخزون"),
        ("inventory", "base"): ("BaseProduct", "منتج أساسي"),
        ("inventory", "variant"): ("ProductVariant", "متغير منتج"),
        ("inventory", "supplier"): ("Supplier", "مورد"),
        ("inventory", "purchase"): ("PurchaseOrder", "أمر شراء"),
        ("inventory", "set"): ("ProductSet", "طقم منتج"),
        ("inventory", "alert"): ("StockAlert", "تنبيه مخزون"),
        # ---- المعاينات ----
        ("inspections", "inspection"): ("Inspection", "معاينة"),
        ("inspections", "evaluation"): ("InspectionEvaluation", "تقييم معاينة"),
        ("inspections", "file"): ("InspectionFile", "ملف معاينة"),
        ("inspections", "notification"): ("InspectionNotification", "إشعار معاينة"),
        # ---- الشكاوى ----
        ("complaints", "complaint"): ("Complaint", "شكوى"),
        ("complaints", "evaluation"): ("ComplaintEvaluation", "تقييم شكوى"),
        ("complaints", "attachment"): ("ComplaintAttachment", "مرفق شكوى"),
        # ---- الحسابات والمستخدمين ----
        ("accounts", "field"): ("FormField", "حقل نموذج"),
        ("accounts", "form"): ("FormField", "حقل نموذج"),
        ("accounts", "department"): ("Department", "قسم"),
        ("accounts", "salesperson"): ("Salesperson", "مندوب مبيعات"),
        ("accounts", "role"): ("Role", "دور"),
        ("accounts", "message"): ("Message", "رسالة"),
        ("accounts", "device"): ("DeviceReport", "تقرير جهاز"),
        ("accounts", "user"): ("User", "مستخدم"),
    }

    # -------------------------------------------------------------------
    # خريطة أفعال العمليات: كلمة مفتاحية → (نوع العملية, وصف عربي)
    # -------------------------------------------------------------------
    ACTION_KEYWORDS = {
        "create": ("CREATE", "إنشاء"),
        "add": ("CREATE", "إضافة"),
        "register": ("CREATE", "تسجيل"),
        "update": ("UPDATE", "تعديل"),
        "edit": ("UPDATE", "تعديل"),
        "change": ("UPDATE", "تغيير"),
        "toggle": ("UPDATE", "تبديل حالة"),
        "delete": ("DELETE", "حذف"),
        "remove": ("DELETE", "حذف"),
        "approve": ("UPDATE", "اعتماد"),
        "reject": ("UPDATE", "رفض"),
        "complete": ("UPDATE", "إكمال"),
        "close": ("UPDATE", "إغلاق"),
        "assign": ("UPDATE", "تعيين"),
        "schedule": ("UPDATE", "جدولة"),
        "start": ("UPDATE", "بدء"),
        "cancel": ("UPDATE", "إلغاء"),
        "void": ("UPDATE", "إلغاء"),
        "post": ("UPDATE", "ترحيل"),
        "submit": ("UPDATE", "إرسال"),
        "resolve": ("UPDATE", "حل"),
        "escalate": ("UPDATE", "تصعيد"),
        "status": ("UPDATE", "تغيير حالة"),
        "pay": ("CREATE", "دفع"),
        "upload": ("CREATE", "رفع ملف"),
        "receive": ("UPDATE", "استلام"),
        "sync": ("UPDATE", "مزامنة"),
        "merge": ("UPDATE", "دمج"),
        "bulk": ("BULK_UPDATE", "تحديث جماعي"),
        "mark": ("UPDATE", "تحديث حالة"),
        "reply": ("CREATE", "رد"),
        "print": ("VIEW", "طباعة"),
        "export": ("DATA_EXPORT", "تصدير"),
        "iterate": ("UPDATE", "تكرار"),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # -----------------------------------------------------------
        # مرحلة ما قبل التنفيذ: التقاط الحالة القديمة للكائن
        # -----------------------------------------------------------
        old_state = None
        resolved_info = None
        should_log = (
            request.method in ("POST", "PUT", "PATCH", "DELETE")
            and hasattr(request, "user")
            and getattr(request.user, "is_authenticated", False)
            and self._should_log(request)
        )

        if should_log:
            resolved_info = self._pre_resolve(request)
            if resolved_info and resolved_info.get("model_class") and resolved_info.get("object_id"):
                old_state = self._snapshot_object(
                    resolved_info["model_class"], resolved_info["object_id"]
                )

        # -----------------------------------------------------------
        # تنفيذ الـ View
        # -----------------------------------------------------------
        response = self.get_response(request)

        # -----------------------------------------------------------
        # مرحلة ما بعد التنفيذ: التقاط الحالة الجديدة وتسجيل الفرق
        # -----------------------------------------------------------
        if should_log and not getattr(request, "_audit_logged", False):
            self._log_request(request, response, old_state=old_state, resolved=resolved_info)

        return response

    def _should_log(self, request):
        """هل يجب تسجيل هذا الطلب؟"""
        path = request.path
        if any(path.startswith(p) for p in self.IGNORED_PATHS):
            return False
        return any(path.startswith(p) for p in self.SENSITIVE_PATHS)

    def _log_request(self, request, response, old_state=None, resolved=None):
        """تسجيل الطلب بمعلومات غنية مع تفاصيل التغييرات (قبل/بعد)"""
        try:
            from django.urls import Resolver404, resolve

            # ① حل مسار URL (أو استخدام النتيجة المحفوظة)
            if resolved:
                url_name = resolved.get("url_name", "")
                namespace = resolved.get("namespace", "")
                kwargs = resolved.get("kwargs", {})
                model_name = resolved.get("model_name", "")
                model_verbose = resolved.get("model_verbose", "")
                model_class = resolved.get("model_class")
                object_id = resolved.get("object_id")
            else:
                try:
                    match = resolve(request.path)
                    url_name = match.url_name or ""
                    namespace = match.namespace or ""
                    kwargs = match.kwargs or {}
                except Resolver404:
                    url_name = ""
                    namespace = ""
                    kwargs = {}
                model_name, model_verbose, model_class = self._resolve_model(
                    namespace, url_name
                )
                object_id = self._extract_object_id(kwargs)

            # ② تحديد نوع العملية
            action, action_label = self._determine_action(
                url_name, request.method, request.path
            )

            # ③ تحديد مستوى الخطورة
            severity = self._determine_severity(action, request.path)

            # ④ استخراج app_label
            app_label = self.NAMESPACE_TO_APP.get(namespace, namespace) or ""

            # ⑤ تحميل حالة الكائن بعد التنفيذ وحساب الفرق
            new_state = None
            old_value = None
            new_value = None
            changed_fields = None

            if model_class and object_id:
                if action == "DELETE":
                    # الحذف: القيم القديمة فقط (الكائن لم يعد موجوداً)
                    old_value = old_state
                    new_value = None
                    if old_state:
                        changed_fields = list(old_state.keys())
                else:
                    # التعديل أو الإنشاء: التقاط الحالة الجديدة
                    new_state = self._snapshot_object(model_class, object_id)

                    if old_state and new_state:
                        # حساب الحقول المتغيرة فقط
                        diff_old, diff_new, diff_fields = self._compute_diff(
                            old_state, new_state, model_class
                        )
                        if diff_fields:
                            old_value = diff_old
                            new_value = diff_new
                            changed_fields = diff_fields
                    elif new_state and not old_state:
                        # إنشاء جديد: القيم الجديدة فقط
                        new_value = new_state
                        changed_fields = list(new_state.keys())

            # ⑥ تحميل repr الكائن (بعد التعديل)
            object_repr = ""
            if model_class and object_id:
                object_repr = self._load_object_repr(model_class, object_id)
                # في حالة الحذف، نأخذ repr من الحالة القديمة
                if not object_repr and old_state:
                    # محاولة بناء repr من الحالة القديمة
                    name_keys = ("name", "الاسم", "order_number", "__str__", "title")
                    for k in name_keys:
                        if k in old_state and old_state[k]:
                            object_repr = str(old_state[k])[:500]
                            break
                    if not object_repr:
                        object_repr = f"#{object_id} (محذوف)"

            # ⑦ بناء الوصف العربي المقروء
            description = self._build_audit_description(
                action_label,
                model_verbose,
                object_repr,
                object_id,
                request.user,
                url_name,
                request.path,
            )

            AuditLog.log(
                user=request.user,
                action=action,
                description=description,
                severity=severity,
                app_label=app_label,
                model_name=model_name,
                object_id=str(object_id) if object_id else "",
                object_repr=object_repr,
                old_value=old_value,
                new_value=new_value,
                changed_fields=changed_fields,
                ip_address=AuditLog._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                url_path=request.path,
                http_method=request.method,
                session_key=getattr(request.session, "session_key", "") or "",
            )
        except Exception as e:
            logger.error(f"خطأ في AuditLoggingMiddleware: {e}")

    # ------------------------------------------------------------------
    # دوال مساعدة داخلية
    # ------------------------------------------------------------------

    def _pre_resolve(self, request):
        """حل مسار URL مبكراً واستخراج جميع البيانات اللازمة"""
        from django.urls import Resolver404, resolve

        try:
            match = resolve(request.path)
            url_name = match.url_name or ""
            namespace = match.namespace or ""
            kwargs = match.kwargs or {}
        except Resolver404:
            return None

        model_name, model_verbose, model_class = self._resolve_model(namespace, url_name)
        object_id = self._extract_object_id(kwargs)

        return {
            "url_name": url_name,
            "namespace": namespace,
            "kwargs": kwargs,
            "model_name": model_name,
            "model_verbose": model_verbose,
            "model_class": model_class,
            "object_id": object_id,
        }

    def _snapshot_object(self, model_class, object_id):
        """
        التقاط حالة كائن من قاعدة البيانات كقاموس {field_verbose: value}.
        يُستخدم لمقارنة الحالة قبل وبعد التعديل.
        """
        if not model_class or not object_id:
            return None
        try:
            instance = model_class.objects.filter(pk=object_id).first()
            if not instance:
                return None
            data = {}
            for field in instance._meta.concrete_fields:
                # تجاهل الحقول التقنية التي لا تهم المستخدم
                if field.name in (
                    "id", "pk", "password", "last_login",
                    "created_at", "updated_at", "created_date", "modified_date",
                    "updated_by_id", "created_by_id",
                ):
                    continue
                # استخدام verbose_name العربي كمفتاح
                label = str(field.verbose_name) if field.verbose_name else field.name
                value = getattr(instance, field.attname, None)
                # تحويل القيم إلى نص قابل للقراءة
                if value is None:
                    data[label] = ""
                elif hasattr(field, "choices") and field.choices:
                    # عرض النص المقروء بدلاً من الكود
                    display_method = f"get_{field.name}_display"
                    if hasattr(instance, display_method):
                        data[label] = str(getattr(instance, display_method)())
                    else:
                        data[label] = str(value)
                elif field.is_relation:
                    # FK: عرض repr الكائن المرتبط
                    try:
                        related = getattr(instance, field.name, None)
                        data[label] = str(related)[:200] if related else ""
                    except Exception:
                        data[label] = str(value) if value else ""
                else:
                    try:
                        json.dumps(value)
                        data[label] = value
                    except (TypeError, ValueError):
                        data[label] = str(value)
            return data
        except Exception:
            return None

    def _compute_diff(self, old_state, new_state, model_class=None):
        """
        مقارنة الحالة القديمة والجديدة وإرجاع الحقول المتغيرة فقط.
        يعيد: (old_diff, new_diff, changed_field_names)
        """
        old_diff = {}
        new_diff = {}
        changed = []

        all_keys = set(list(old_state.keys()) + list(new_state.keys()))
        for key in all_keys:
            old_val = old_state.get(key)
            new_val = new_state.get(key)
            # تطبيع للمقارنة العادلة
            old_str = str(old_val) if old_val is not None else ""
            new_str = str(new_val) if new_val is not None else ""
            if old_str != new_str:
                old_diff[key] = old_val if old_val is not None else ""
                new_diff[key] = new_val if new_val is not None else ""
                changed.append(key)

        return old_diff, new_diff, changed

    def _determine_action(self, url_name, method, path):
        """تحديد نوع العملية من اسم URL والمسار والـ HTTP method"""
        lower_name = (url_name or "").lower()

        # حالات خاصة: تسجيل دخول / خروج
        if "login" in lower_name or "/login" in path:
            return "LOGIN", "تسجيل دخول"
        if "logout" in lower_name or "/logout" in path:
            return "LOGOUT", "تسجيل خروج"

        # DELETE HTTP method يعني دائماً حذف
        if method == "DELETE":
            return "DELETE", "حذف"

        # تحليل اسم URL لاستخراج الفعل
        if url_name:
            parts = url_name.split("_")
            # نبحث من النهاية — الفعل عادةً آخر كلمة
            for part in reversed(parts):
                if part in self.ACTION_KEYWORDS:
                    return self.ACTION_KEYWORDS[part]

        # بحث في المسار كخطة بديلة
        path_lower = path.lower().rstrip("/")
        last_segment = path_lower.rsplit("/", 1)[-1] if "/" in path_lower else ""
        if last_segment in self.ACTION_KEYWORDS:
            return self.ACTION_KEYWORDS[last_segment]

        # افتراضي بحسب HTTP method
        if method == "POST":
            return "CREATE", "إنشاء"
        if method in ("PUT", "PATCH"):
            return "UPDATE", "تعديل"
        return "UPDATE", "عملية"

    def _determine_severity(self, action, path):
        """تحديد مستوى الخطورة"""
        if action in ("DELETE", "BULK_DELETE"):
            return "WARNING"
        if action in ("BULK_UPDATE",):
            return "WARNING"
        if "/admin/" in path:
            return "WARNING"
        if action in ("LOGIN", "LOGOUT"):
            return "INFO"
        return "INFO"

    def _resolve_model(self, namespace, url_name):
        """
        تحديد النموذج من namespace واسم URL.
        يعيد: (model_class_name, verbose_arabic, model_class_or_None)
        """
        if not url_name or not namespace:
            return "", "", None

        parts = url_name.split("_")

        # جرب كل جزء من اسم URL كمفتاح بحث في خريطة النماذج
        for part in parts:
            key = (namespace, part)
            if key in self.MODEL_MAP:
                class_name, verbose = self.MODEL_MAP[key]
                app_label = self.NAMESPACE_TO_APP.get(namespace, namespace)
                try:
                    from django.apps import apps
                    model_class = apps.get_model(app_label, class_name)
                    return class_name, verbose, model_class
                except (LookupError, Exception):
                    return class_name, verbose, None

        return "", "", None

    def _extract_object_id(self, kwargs):
        """استخراج معرف الكائن من URL kwargs"""
        if not kwargs:
            return None

        # أولوية: pk ثم أي param ينتهي بـ _id أو _pk
        if "pk" in kwargs:
            val = kwargs["pk"]
            if isinstance(val, int):
                return val
            if isinstance(val, str) and val.isdigit():
                return int(val)

        # بحث في params ذات الأسماء المحددة
        for key, val in kwargs.items():
            if key.endswith("_id") or key.endswith("_pk"):
                if isinstance(val, int):
                    return val
                if isinstance(val, str) and val.isdigit():
                    return int(val)

        # آخر محاولة: أول رقم صحيح
        for val in kwargs.values():
            if isinstance(val, int):
                return val

        return None

    def _load_object_repr(self, model_class, object_id):
        """تحميل التمثيل النصي للكائن من قاعدة البيانات"""
        if not model_class or not object_id:
            return ""
        try:
            instance = model_class.objects.filter(pk=object_id).first()
            if instance:
                return str(instance)[:500]
        except Exception:
            pass
        return ""

    def _build_audit_description(
        self, action_label, model_verbose, object_repr, object_id, user, url_name, path
    ):
        """بناء وصف عربي مقروء للعملية"""
        lower_name = (url_name or "").lower()

        # تسجيل دخول / خروج
        if "login" in lower_name or "/login" in path:
            full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
            display = full_name or getattr(user, "username", str(user))
            return f"تسجيل دخول المستخدم {display}"
        if "logout" in lower_name or "/logout" in path:
            full_name = user.get_full_name() if hasattr(user, "get_full_name") else ""
            display = full_name or getattr(user, "username", str(user))
            return f"تسجيل خروج المستخدم {display}"

        # العمليات العادية
        if model_verbose and object_repr:
            return f"{action_label} {model_verbose}: {object_repr}"
        if model_verbose and object_id:
            return f"{action_label} {model_verbose} #{object_id}"
        if model_verbose:
            return f"{action_label} {model_verbose}"

        # خطة بديلة: اسم التطبيق فقط
        if action_label:
            return f"{action_label} — {path}"

        return f"عملية على {path}"


# =========================================================================
# دوال مساعدة للاستخدام المباشر
# =========================================================================
def log_audit(user, action, description, **kwargs):
    """
    تسجيل سريع في سجل التدقيق

    Usage:
        from core.audit import log_audit

        log_audit(
            user=request.user,
            action='CREATE',
            description='إنشاء طلب جديد',
            model_name='Order',
            object_id=order.id
        )
    """
    return AuditLog.log(user, action, description, **kwargs)


def log_security_event(event_type, ip_address, **kwargs):
    """
    تسجيل سريع لحدث أمني

    Usage:
        from core.audit import log_security_event

        log_security_event(
            'SQL_INJECTION',
            request.META.get('REMOTE_ADDR'),
            user=request.user,
            details={'query': bad_query}
        )
    """
    return SecurityEvent.log_event(event_type, ip_address, **kwargs)
