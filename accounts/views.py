import hashlib
import json
import logging
import traceback

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.views.decorators.cache import never_cache
from django_ratelimit.decorators import ratelimit

from .forms import (
    CompanyInfoForm,
    DepartmentForm,
    FormFieldForm,
    RoleAssignForm,
    RoleForm,
    SalespersonForm,
    UserProfileForm,
)
from .models import (
    Branch,
    BranchDevice,
    CompanyInfo,
    Department,
    FormField,
    MasterQRCode,
    Role,
    Salesperson,
    UnauthorizedDeviceAttempt,
    UserRole,
)

logger = logging.getLogger(__name__)

# الحصول على نموذج المستخدم المخصص
User = get_user_model()


def generate_device_fingerprint(request):
    """
    توليد بصمة محسّنة للجهاز - تركز على العوامل الثابتة
    تستبعد العوامل المتغيرة (دقة الشاشة، user agent version)
    """
    device_info = request.POST.get("device_info", "{}")

    try:
        device_data = json.loads(device_info)
    except Exception:
        device_data = {}

    # العوامل الثابتة فقط - لا تتغير بسهولة
    stable_fingerprint_data = {
        # GPU Info (ثابت جداً)
        "webgl_vendor": device_data.get("webgl_vendor", ""),
        "webgl_renderer": device_data.get("webgl_renderer", ""),
        # Canvas (ثابت نسبياً)
        "canvas_hash": device_data.get("canvas_fingerprint", ""),
        # Audio (ثابت جداً)
        "audio_hash": device_data.get("audio_fingerprint", ""),
        # Hardware (ثابت)
        "cpu_cores": device_data.get("hardware_concurrency", ""),
        "device_memory": device_data.get("device_memory", ""),
        # Platform (شبه ثابت)
        "platform": device_data.get("platform", ""),
        # Timezone (نادر التغيير)
        "timezone": device_data.get("timezone", ""),
        # استبعدنا: screen_resolution, user_agent (يتغيران كثيراً)
    }

    # إنشاء hash من العوامل الثابتة فقط
    fingerprint_string = json.dumps(stable_fingerprint_data, sort_keys=True)
    fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()

    return fingerprint_hash, device_data


def get_client_ip(request):
    """Wrapper — يستخدم الدالة المركزية من user_activity.utils"""
    from user_activity.utils import get_client_ip_from_request
    return get_client_ip_from_request(request)


@never_cache
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login_view(request):
    """
    View for user login with rate limiting
    """
    import logging
    import traceback

    logger = logging.getLogger("django")

    # Rate Limiting - حماية ضد هجمات Brute Force
    if request.method == "POST":
        ip = request.META.get("REMOTE_ADDR", "unknown")
        attempts_key = f"login_attempts_{ip}"
        block_key = f"login_blocked_{ip}"

        # التحقق من الحظر
        if cache.get(block_key):
            logger.warning(f"🔒 Blocked login attempt from IP: {ip}")
            messages.error(
                request,
                "تم حظر الوصول مؤقتاً بسبب محاولات تسجيل دخول متعددة فاشلة. حاول مرة أخرى بعد 15 دقيقة.",
            )
            return HttpResponseForbidden("تم حظر الوصول مؤقتاً")

        # عد المحاولات الفاشلة
        attempts = cache.get(attempts_key, 0)
        if attempts >= 5:
            # حظر لمدة 15 دقيقة بعد 5 محاولات فاشلة
            cache.set(block_key, True, 900)  # 15 دقيقة
            logger.warning(f"🚫 IP {ip} blocked after {attempts} failed attempts")
            messages.error(
                request,
                "تم تجاوز عدد المحاولات المسموح به. تم حظر الوصول لمدة 15 دقيقة.",
            )
            return HttpResponseForbidden("تم حظر الوصول مؤقتاً")

    # إعداد نموذج تسجيل الدخول الافتراضي
    form = AuthenticationForm()

    # إضافة الأنماط إلى حقول النموذج
    try:
        form.fields["username"].widget.attrs.update(
            {"class": "form-control", "placeholder": "اسم المستخدم"}
        )
        form.fields["password"].widget.attrs.update(
            {"class": "form-control", "placeholder": "كلمة المرور"}
        )
    except Exception as form_error:
        logger.error(f"[Form Error] {form_error}")

    try:
        # تعريف context في البداية
        context = {
            "form": form,
            "title": "تسجيل الدخول",
        }

        # التحقق مما إذا كان المستخدم مسجل الدخول بالفعل
        if request.user.is_authenticated:
            return redirect("home")

        # معالجة طلب تسجيل الدخول
        if request.method == "POST":
            try:
                # الحصول على معلومات الجهاز أولاً
                ip = get_client_ip(request)
                device_info = request.POST.get("device_info", "")
                device_data = json.loads(device_info) if device_info else {}

                # بيانات للتسجيل
                device_log_data = {
                    "user_agent": device_data.get(
                        "user_agent", request.META.get("HTTP_USER_AGENT", "")
                    )
                }

                form = AuthenticationForm(request, data=request.POST)

                # إضافة الأنماط إلى حقول النموذج
                form.fields["username"].widget.attrs.update(
                    {"class": "form-control", "placeholder": "اسم المستخدم"}
                )
                form.fields["password"].widget.attrs.update(
                    {"class": "form-control", "placeholder": "كلمة المرور"}
                )

                # الحصول على username و password من الطلب
                username = request.POST.get("username", "")
                password = request.POST.get("password", "")

                # التحقق من وجود اسم المستخدم
                from accounts.models import UnauthorizedDeviceAttempt

                try:
                    user_obj = User.objects.get(username=username)
                    user_exists = True
                except User.DoesNotExist:
                    user_obj = None
                    user_exists = False
                    logger.warning(f"❌ Invalid username attempt: {username}")

                if form.is_valid():
                    logger.info(f"Login attempt for user: {username}")

                    # محاولة المصادقة المباشرة
                    user = authenticate(
                        request=request, username=username, password=password
                    )

                    if user is not None:

                        # المنطق الجديد: الفرع بدون أجهزة مسجلة = مفتوح تلقائياً
                        # الفرع مع أجهزة مسجلة = مقفول على هذه الأجهزة فقط
                        from accounts.models import BranchDevice

                        # التحقق من وجود أجهزة مسجلة لفرع المستخدم
                        user_branch_has_devices = False
                        if user.branch:
                            user_branch_has_devices = BranchDevice.objects.filter(
                                branch=user.branch, is_active=True
                            ).exists()

                        # القفل مفعل فقط إذا كان لفرع المستخدم أجهزة مسجلة
                        device_restriction_enabled = user_branch_has_devices

                        logger.info(
                            f"🏢 User branch: {user.branch.name if user.branch else 'None'}"
                        )
                        logger.info(
                            f"💻 User branch has registered devices: {user_branch_has_devices}"
                        )
                        logger.info(
                            f"✅ Device restriction enabled: {device_restriction_enabled}"
                        )

                        # الحصول على معلومات الجهاز
                        device_info = request.POST.get("device_info", "")
                        device_data = json.loads(device_info) if device_info else {}

                        logger.info(
                            f"📍 User branch: {user.branch.name if user.branch else 'None'}"
                        )

                        # التحقق من أن الجهاز مسجل ومرتبط بفرع المستخدم
                        device_authorized = False
                        device_obj = None
                        denial_reason = ""
                        denial_reason_key = ""
                        device_check_performed = False

                        # منطق تجاوز قفل الأجهزة المخفف:
                        # 1. السوبر يوزر دائماً مستثنى
                        # 2. بائعو الجملة مستثنون بناءً على طلب العميل ليتمكنوا من العمل بحرية
                        # 3. المديرين ومن هم أعلى (مثل مدير المنطقة أو المبيعات) يجب أن يدخلوا من أجهزة مسجلة فقط

                        # بائع جملة "نقي" فقط هو من يتجاوز القفل
                        is_wholesale_salesperson = (
                            getattr(user, "is_salesperson", False)
                            and getattr(user, "is_wholesale", False)
                            and not getattr(user, "is_retail", False)
                        )

                        if user.is_superuser:
                            device_authorized = True
                            logger.info(
                                f"✅ Superuser {username} authorized from any device (Security Bypass)"
                            )
                        elif is_wholesale_salesperson:
                            # بائع جملة: يسمح له بالتجاوز
                            device_authorized = True
                            logger.info(
                                f"✅ Wholesale Salesperson {username} authorized bypass (Custom Policy)"
                            )
                        else:
                            # أي شخص آخر (بما في ذلك المديرين) يجب أن يخضع لفحص الجهاز
                            device_check_performed = True
                            logger.info(
                                f"🔍 Checking device for {username} (Manager/Retail User - Restriction Enabled: {device_restriction_enabled})..."
                            )
                            try:
                                # 1. الحصول على device_token من الطلب
                                device_token_str = request.POST.get(
                                    "device_token", ""
                                ).strip()

                                if device_token_str:
                                    logger.info(
                                        f"🎫 Device token provided: {device_token_str[:8]}..."
                                    )
                                else:
                                    logger.debug(f"No device token provided")
                                    # سياسة مرنة: إذا لم يكن للفرع أجهزة مسجلة، السماح بالدخول
                                    if not device_restriction_enabled:
                                        device_authorized = True
                                        logger.info(
                                            f"✅ No token, but branch has no restrictions - allowing login"
                                        )

                                # 2. البحث بالـ device_token (الطريقة الوحيدة المدعومة)
                                if device_token_str:
                                    try:
                                        import uuid

                                        device_token_uuid = uuid.UUID(device_token_str)
                                        device_obj = BranchDevice.objects.get(
                                            device_token=device_token_uuid,
                                            is_active=True,
                                        )
                                        logger.info(
                                            f"✅ Device found by TOKEN: {device_obj.device_name} (Branch: {device_obj.branch.name})"
                                        )

                                        # لا نسمح بالدخول هنا - سيتم التحقق من الفرع لاحقاً
                                        device_check_performed = True
                                    except ValueError:
                                        logger.warning(
                                            f"⚠️ Invalid device_token format: {device_token_str}"
                                        )
                                        denial_reason = "🚫 جهاز غير مسجل - يجب تسجيل الجهاز عبر QR Master أولاً"
                                        denial_reason_key = "device_not_registered"
                                    except BranchDevice.DoesNotExist:
                                        logger.warning(
                                            f"⚠️ Device token not found in database"
                                        )
                                        denial_reason = "🚫 جهاز غير مسجل - يجب تسجيل الجهاز عبر QR Master أولاً"
                                        denial_reason_key = "device_not_registered"
                                        logger.warning(
                                            f"❌ Unknown device attempted login for user {username}"
                                        )
                                        logger.warning(
                                            f"📊 Total active devices: {BranchDevice.objects.filter(is_active=True).count()}"
                                        )

                                # التحقق من الصلاحية إذا وُجد الجهاز
                                if device_obj:
                                    # التحقق من حظر الجهاز أولاً
                                    if device_obj.is_blocked:
                                        device_authorized = False
                                        denial_reason = f"🚫 هذا الجهاز محظور"
                                        denial_reason_key = "device_blocked"
                                        logger.warning(
                                            f"❌ Blocked device attempted login: {device_obj.device_name}. Reason: {device_obj.blocked_reason}"
                                        )
                                    # تحقق إضافي: هل فرع الجهاز هو نفس فرع المستخدم؟
                                    # نمنع الدخول من أجهزة فروع أخرى حتى لو كان مصرحاً بها يدوياً (للمديرين وموظفي القطاعي)
                                    user_branch = getattr(user, "branch", None)
                                    device_branch = getattr(device_obj, "branch", None)

                                    if device_obj in user.authorized_devices.all():
                                        if (
                                            user_branch == device_branch
                                            or not device_branch
                                        ):
                                            device_authorized = True
                                            # تحديث معلومات آخر استخدام
                                            device_obj.mark_used(
                                                user=user, ip_address=ip
                                            )
                                            logger.info(
                                                f"✅ User {username} authorized for device: {device_obj.device_name} - Branch: {device_obj.branch.name}"
                                            )
                                        else:
                                            # محاولة دخول من جهاز فرع آخر
                                            device_authorized = False
                                            denial_reason = f"⛔ هذا الجهاز ينتمي لفرع {device_branch.name}، وأنت تتبع فرع {user_branch.name}"
                                            denial_reason_key = "cross_branch_device"
                                            logger.warning(
                                                f"❌ CROSS-BRANCH ACCESS BLOCKED: User {username} ({user_branch}) attempted login from device '{device_obj.device_name}' ({device_branch})"
                                            )
                                    else:
                                        # الجهاز غير مصرح للمستخدم
                                        device_authorized = False
                                        denial_reason = f"⛔ هذا الجهاز غير مصرح لك"
                                        denial_reason_key = "wrong_branch"
                                        logger.warning(
                                            f"❌ DEVICE NOT AUTHORIZED: User {username} attempted login from device '{device_obj.device_name}' (Branch: {device_obj.branch.name})"
                                        )
                                        logger.warning(
                                            f"   User's branch: {user_branch.name if user_branch else 'None'}"
                                        )
                                        logger.warning(
                                            f"   User's authorized devices: {user.authorized_devices.count()}"
                                        )
                                else:
                                    # الجهاز غير موجود في النظام
                                    # لا نضع denial_reason إذا تم السماح مسبقاً (عندما لا يوجد token والفرع بدون قيود)
                                    if not device_authorized and not denial_reason_key:
                                        denial_reason = "🚫 جهاز غير مسجل"
                                        denial_reason_key = "device_not_registered"
                            except Exception as device_error:
                                denial_reason = f"حدث خطأ أثناء التحقق من الجهاز: {str(device_error)}"
                                logger.error(f"Device check error: {device_error}")
                                logger.error(traceback.format_exc())

                            # === منطق القرار النهائي ===
                            # السياسة المرنة: الفرع بدون أجهزة = مفتوح، الفرع بأجهزة = مقفل عليها

                            # السيناريو 1: الجهاز موجود ومسجل في النظام
                            if device_obj:
                                if device_authorized:
                                    logger.info(
                                        f"✅ LOGIN ALLOWED - User and device authorized in branch: {device_obj.branch.name}"
                                    )
                                else:
                                    logger.error(
                                        f"🔒 LOGIN BLOCKED - {denial_reason_key}: {denial_reason}"
                                    )

                            # السيناريو 2: لا يوجد device_token أو الجهاز غير مسجل
                            else:
                                # التحقق: هل فرع المستخدم لديه أجهزة مسجلة؟
                                if device_restriction_enabled:
                                    # الفرع لديه أجهزة - يجب الدخول من أحدها
                                    device_authorized = False
                                    if not denial_reason_key:
                                        denial_reason = (
                                            "🚫 يجب الدخول من أحد أجهزة فرعك المسجلة"
                                        )
                                        denial_reason_key = "device_not_registered"
                                    logger.error(
                                        f"🔒 LOGIN BLOCKED - Branch has devices, must use one of them"
                                    )
                                else:
                                    # الفرع بدون أجهزة - السماح بالدخول
                                    device_authorized = True
                                    logger.info(
                                        f"✅ LOGIN ALLOWED - Branch has no device restrictions"
                                    )

                        # تسجيل المحاولة غير المصرح بها (للمراقبة والإحصائيات)
                        logger.info(
                            f"🔍 Check logging conditions: device_check={device_check_performed}, denial_key={denial_reason_key}, superuser={user.is_superuser}, sales_manager={user.is_sales_manager}"
                        )

                        if (
                            device_check_performed
                            and denial_reason_key
                            and not (user.is_superuser or user.is_sales_manager)
                        ):

                            logger.info(
                                f"📝 Logging unauthorized attempt: {username} - {denial_reason_key}"
                            )

                            # جمع بيانات الجهاز
                            device_log_data_full = {
                                "user_agent": device_data.get(
                                    "user_agent",
                                    request.META.get("HTTP_USER_AGENT", ""),
                                )
                            }

                            device_branch = device_obj.branch if device_obj else None

                            # التحقق من حظر الجهاز
                            if device_obj and device_obj.is_blocked:
                                denial_reason_key = "device_blocked"
                                denial_reason = f"🚫 هذا الجهاز محظور. السبب: {device_obj.blocked_reason}"

                            # تسجيل المحاولة
                            attempt = UnauthorizedDeviceAttempt.log_attempt(
                                username_attempted=username,
                                user=user,
                                device_data=device_log_data_full,
                                denial_reason=denial_reason_key,
                                user_branch=user.branch,
                                device_branch=device_branch,
                                device=device_obj,
                                ip_address=ip,
                            )

                            logger.error(
                                f"🚨 Unauthorized attempt logged: ID {attempt.id} - Reason: {denial_reason_key}"
                            )

                            # إرسال إشعار فوري لمدير النظام في جميع حالات رفض الدخول
                            # (سواء كان القفل مفعل لفرع المستخدم أو الجهاز مسجل لفرع آخر)
                            if not device_authorized and denial_reason_key in [
                                "wrong_branch",
                                "device_not_registered",
                                "device_blocked",
                                "fingerprint_mismatch",
                            ]:
                                try:
                                    from notifications.models import Notification

                                    superusers = User.objects.filter(
                                        is_superuser=True, is_active=True
                                    )

                                    # تخصيص رسالة الإشعار حسب السبب
                                    if denial_reason_key == "wrong_branch":
                                        device_info = (
                                            f"جهاز {device_obj.device_name} (فرع: {device_obj.branch.name})"
                                            if device_obj
                                            else "جهاز غير معروف"
                                        )
                                        notification_message = (
                                            f"🚨 محاولة دخول من فرع خاطئ!\n\n"
                                        )
                                        notification_message += (
                                            f"المستخدم: {user.username}\n"
                                        )
                                        notification_message += f'فرع المستخدم: {user.branch.name if user.branch else "غير محدد"}\n'
                                        notification_message += (
                                            f"الجهاز المستخدم: {device_info}\n"
                                        )
                                        notification_message += f'الوقت: {attempt.attempted_at.strftime("%Y-%m-%d %H:%M")}\n'
                                        notification_message += f"IP: {ip}"
                                    else:
                                        notification_message = f'{user.username} ({user.branch.name if user.branch else "بدون فرع"}) حاول الدخول من جهاز غير مصرح به.\n'
                                        notification_message += f"السبب: {attempt.get_denial_reason_display()}\n"
                                        notification_message += f'الوقت: {attempt.attempted_at.strftime("%Y-%m-%d %H:%M")}\n'
                                        notification_message += f"IP: {ip}"

                                    for admin_user in superusers:
                                        notification = Notification.objects.create(
                                            title="🚨 محاولة دخول غير مصرح بها",
                                            message=notification_message,
                                            notification_type="order_created",
                                            priority="urgent",
                                            created_by=user,
                                        )
                                        notification.visible_to.add(admin_user)

                                    attempt.is_notified = True
                                    attempt.save()
                                    logger.info(
                                        f"✅ Notification sent to {superusers.count()} admins"
                                    )
                                except Exception as notif_error:
                                    logger.error(
                                        f"❌ Failed to send notification: {notif_error}"
                                    )

                        # السماح بتسجيل الدخول فقط إذا كان الجهاز مصرح به
                        if device_authorized:
                            # نجاح تسجيل الدخول - إعادة تعيين المحاولات
                            attempts_key = f"login_attempts_{ip}"
                            cache.delete(attempts_key)

                            # حفظ آخر تسجيل دخول سابق قبل أن يكتبه login()
                            previous_last_login = user.last_login
                            login(request, user)
                            if previous_last_login:
                                request.session["previous_last_login"] = previous_last_login.isoformat()
                            logger.info(
                                f"✅ Successful login for user: {username} from IP: {ip}"
                            )
                            messages.success(request, f"مرحباً بك {username}!")
                            next_url = request.GET.get("next", "home")
                            return redirect(next_url)
                        else:
                            # الجهاز غير مصرح - عرض رسالة خطأ مفصلة
                            if denial_reason:
                                # رسالة خطأ أساسية
                                error_message = (
                                    f"<strong>{denial_reason}</strong><br><br>"
                                )

                                # إضافة تفاصيل حسب السبب
                                if "denial_reason_key" in locals():
                                    if denial_reason_key == "device_not_registered":
                                        branch_lock_status = (
                                            "مفعّل ✅"
                                            if (
                                                user.branch
                                                and user.branch.require_device_lock
                                            )
                                            else "معطّل ❌"
                                        )
                                        error_message += f"""
                                        <div style='background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;'>
                                            <strong>ℹ️ ماذا يعني هذا؟</strong><br>
                                            • هذا الجهاز لم يتم تسجيله في النظام بعد<br>
                                            • فرعك ({user.branch.name if user.branch else 'غير محدد'}) يتطلب تسجيل الأجهزة<br>
                                            • حالة قفل الأجهزة لفرعك: <strong>{branch_lock_status}</strong><br><br>
                                            
                                            <strong>📝 ما يجب فعله:</strong><br>
                                            1. تواصل مع مدير النظام<br>
                                            2. اطلب منه تسجيل هذا الجهاز لفرعك باستخدام QR Master<br>
                                            3. بعد التسجيل يمكنك المحاولة مرة أخرى<br><br>
                                            
                                            <small>🔒 تم تسجيل هذه المحاولة وإشعار مدير النظام</small>
                                        </div>
                                        """
                                    elif denial_reason_key == "wrong_branch":
                                        # حساب حالة القفل بناءً على وجود أجهزة مسجلة (المنطق الجديد)
                                        branch_name = (
                                            device_obj.branch.name
                                            if device_obj
                                            else "غير معروف"
                                        )

                                        # حساب عدد الأجهزة المسجلة لكل فرع
                                        device_branch_devices_count = 0
                                        user_branch_devices_count = 0

                                        if device_obj and device_obj.branch:
                                            device_branch_devices_count = (
                                                BranchDevice.objects.filter(
                                                    branch=device_obj.branch,
                                                    is_active=True,
                                                ).count()
                                            )

                                        if user.branch:
                                            user_branch_devices_count = (
                                                BranchDevice.objects.filter(
                                                    branch=user.branch, is_active=True
                                                ).count()
                                            )

                                        # تحديد حالة القفل
                                        device_branch_status = (
                                            f"لديه {device_branch_devices_count} جهاز مسجل 🔒"
                                            if device_branch_devices_count > 0
                                            else "مفتوح (بدون أجهزة) 🔓"
                                        )
                                        user_branch_status = (
                                            f"لديه {user_branch_devices_count} جهاز مسجل 🔒"
                                            if user_branch_devices_count > 0
                                            else "مفتوح (بدون أجهزة) 🔓"
                                        )

                                        error_message += f"""
                                        <div style='background: #f8d7da; padding: 15px; border-radius: 5px; border-left: 4px solid #dc3545;'>
                                            <strong>⚠️ تفاصيل المشكلة:</strong><br>
                                            • الجهاز مسجل لفرع: <strong>{branch_name}</strong> ({device_branch_status})<br>
                                            • أنت تنتمي لفرع: <strong>{user.branch.name if user.branch else 'غير محدد'}</strong> ({user_branch_status})<br><br>
                                            
                                            <strong>💡 الحل:</strong><br>
                                            • <strong>الأجهزة المسجلة يمكن استخدامها فقط من قبل موظفي فرعها</strong><br>
                                            • يجب استخدام جهاز غير مسجل، أو تسجيل جهاز جديد لفرعك<br><br>
                                            
                                            <small>🔒 تم تسجيل هذه المحاولة وإشعار مدير النظام</small>
                                        </div>
                                        """

                                # إضافة الرسالة للـ context بدلاً من messages للعرض كـ popup فقط
                                context["device_denial_popup"] = {
                                    "show": True,
                                    "html_content": error_message,
                                    "title": denial_reason,
                                }
                            else:
                                context["device_denial_popup"] = {
                                    "show": True,
                                    "html_content": "🚫 لا يمكنك تسجيل الدخول من هذا الجهاز. يرجى التواصل مع مدير النظام.",
                                    "title": "⛔ جهاز غير مصرح",
                                }
                            logger.warning(
                                f"❌ Login denied for {username}: {denial_reason}"
                            )
                    else:
                        # فشل المصادقة - كلمة مرور خاطئة
                        logger.warning(
                            f"❌ Invalid password for user: {username} from IP: {ip}"
                        )

                        # تسجيل محاولة فاشلة - كلمة مرور خاطئة
                        if user_exists and user_obj:

                            UnauthorizedDeviceAttempt.log_attempt(
                                username_attempted=username,
                                user=user_obj,
                                device_data=device_log_data,
                                denial_reason="invalid_password",
                                user_branch=user_obj.branch if user_obj else None,
                                device_branch=None,
                                device=None,
                                ip_address=ip,
                            )

                        # زيادة عدد المحاولات
                        attempts_key = f"login_attempts_{ip}"
                        attempts = cache.get(attempts_key, 0) + 1
                        cache.set(attempts_key, 300)  # 5 دقائق

                        remaining = 5 - attempts

                        if remaining > 0:
                            messages.error(
                                request,
                                f"❌ كلمة المرور غير صحيحة. محاولات متبقية: {remaining}",
                            )
                        else:
                            messages.error(request, "❌ كلمة المرور غير صحيحة.")
                else:
                    # النموذج غير صالح
                    if not user_exists:
                        # اسم مستخدم خاطئ
                        logger.warning(f"❌ Invalid username: {username} from IP: {ip}")

                        # تسجيل محاولة فاشلة - اسم مستخدم خاطئ
                        device_log_data["fingerprint"] = (
                            generate_device_fingerprint(request) if device_data else ""
                        )

                        # محاولة العثور على الجهاز

                        UnauthorizedDeviceAttempt.log_attempt(
                            username_attempted=username,
                            user=None,
                            device_data=device_log_data,
                            denial_reason="invalid_username",
                            user_branch=None,
                            device_branch=None,
                            device=None,
                            ip_address=ip,
                        )

                        messages.error(request, "❌ اسم المستخدم غير موجود.")
                    else:
                        messages.error(
                            request, "❌ اسم المستخدم أو كلمة المرور غير صحيحة."
                        )
            except Exception as auth_error:
                logger.error(f"[Authentication Error] {auth_error}")
                logger.error(traceback.format_exc())
                messages.error(
                    request,
                    "حدث خطأ أثناء محاولة تسجيل الدخول. يرجى المحاولة مرة أخرى.",
                )

        # تم إزالة منطق إعداد النظام الأولي (غير مستخدم بعد الآن)

        # عرض نموذج تسجيل الدخول (context تم تعريفه في البداية)

        return render(request, "accounts/login.html", context)
    except Exception as e:
        logger.error(f"[Critical Login Error] {e}")
        logger.error(traceback.format_exc())

        # في حالة حدوث خطأ غير متوقع، نعرض صفحة تسجيل دخول بسيطة
        context = {
            "form": form,
            "title": "تسجيل الدخول",
            "error_message": "حدث خطأ في النظام. يرجى الاتصال بمسؤول النظام.",
        }

        return render(request, "accounts/login.html", context)


def logout_view(request):
    """
    View for user logout
    """
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح.")
    return redirect("home")


def admin_logout_view(request):
    """
    View for admin logout that supports GET method
    """
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح.")
    return redirect("admin:index")


@staff_member_required
def validate_qr_master_ajax(request):
    """
    AJAX endpoint للتحقق من صحة QR Master
    """
    if request.method != "POST":
        return JsonResponse(
            {"valid": False, "message": "Method not allowed"}, status=405
        )

    try:
        data = json.loads(request.body)
        qr_code = data.get("qr_code", "").strip()

        if not qr_code:
            return JsonResponse({"valid": False, "message": "QR code is required"})

        # Get active QR Master
        qr_master = MasterQRCode.get_active()

        if not qr_master:
            return JsonResponse({"valid": False, "message": "لا يوجد QR Master نشط"})

        if qr_master.code == qr_code:
            return JsonResponse(
                {
                    "valid": True,
                    "version": qr_master.version,
                    "message": f"QR Master صحيح (v{qr_master.version})",
                }
            )
        else:
            # Check if it's an old/deactivated QR
            old_qr = MasterQRCode.objects.filter(code=qr_code, is_active=False).first()
            if old_qr:
                return JsonResponse(
                    {
                        "valid": False,
                        "message": f"QR منتهي الصلاحية (v{old_qr.version}). استخدم الإصدار الحالي v{qr_master.version}",
                    }
                )
            else:
                return JsonResponse({"valid": False, "message": "QR غير صحيح"})

    except Exception as e:
        return JsonResponse({"valid": False, "message": f"خطأ: {str(e)}"})


@staff_member_required
def register_device_view(request):
    """
    صفحة تسجيل جهاز جديد - يتطلب QR Master للتصريح
    """
    import logging

    logger = logging.getLogger("django")

    if request.method == "POST":
        try:
            # التحقق من QR Master أولاً
            qr_master_code = request.POST.get("qr_master_code")

            if not qr_master_code:
                messages.error(
                    request,
                    "⚠️ يرجى مسح QR Master للمتابعة. QR Master مطلوب للتصريح بتسجيل أجهزة جديدة.",
                )
                return redirect("accounts:register_device")

            # التحقق من صحة QR Master
            qr_master = MasterQRCode.get_active()

            if not qr_master:
                messages.error(
                    request, "❌ لا يوجد QR Master نشط في النظام. اتصل بمدير النظام."
                )
                logger.error("No active QR Master found in system")
                return redirect("accounts:register_device")

            if qr_master.code != qr_master_code:
                # محاولة استخدام QR ملغي أو خاطئ
                old_qr = MasterQRCode.objects.filter(
                    code=qr_master_code, is_active=False
                ).first()
                if old_qr:
                    messages.error(
                        request,
                        f'🚫 QR Master منتهي الصلاحية! تم إلغاؤه في {old_qr.deactivated_at.strftime("%Y-%m-%d")}. استخدم QR Master الحالي (v{qr_master.version}).',
                    )
                    logger.warning(
                        f"⚠️ Attempt to use deactivated QR Master v{old_qr.version} by {request.user.username} from IP {get_client_ip(request)}"
                    )
                else:
                    messages.error(
                        request,
                        "❌ QR Master غير صحيح. تأكد من مسح QR الصحيح من المدير.",
                    )
                    logger.warning(
                        f"⚠️ Invalid QR Master code attempted by {request.user.username}"
                    )
                return redirect("accounts:register_device")

            # QR Master صحيح - المتابعة في التسجيل
            branch_id = request.POST.get("branch")
            device_name = request.POST.get("device_name")
            manual_identifier = request.POST.get("manual_identifier", "").strip()
            notes = request.POST.get("notes", "")
            device_info_str = request.POST.get("device_info", "{}")

            # استخراج معلومات الجهاز
            try:
                device_info = json.loads(device_info_str)
            except Exception:
                device_info = {}

            user_agent = device_info.get(
                "user_agent", request.META.get("HTTP_USER_AGENT", "")
            )

            # التحقق من البيانات المطلوبة
            if not all([branch_id, device_name]):
                messages.error(request, "يرجى إدخال اسم الجهاز والفرع.")
                return redirect("accounts:register_device")

            # التحقق من وجود الفرع
            try:
                branch = Branch.objects.get(id=branch_id)
            except Branch.DoesNotExist:
                messages.error(request, "الفرع المحدد غير موجود.")
                return redirect("accounts:register_device")

            # التحقق من المعرّف اليدوي إذا تم إدخاله
            if manual_identifier:
                existing_manual = BranchDevice.objects.filter(
                    branch=branch, manual_identifier=manual_identifier
                ).first()

                if existing_manual:
                    messages.error(
                        request,
                        f'⚠️ المعرّف اليدوي "{manual_identifier}" مستخدم بالفعل للجهاز "{existing_manual.device_name}" في هذا الفرع. '
                        f"يرجى استخدام معرّف مختلف أو ترك الحقل فارغاً.",
                    )
                    return redirect("accounts:register_device")

            # ملاحظة: تم إزالة التحقق من device_fingerprint لحل مشكلة الأجهزة المتشابهة في بيئات الدومين
            # كل جهاز سيحصل على device_token فريد تلقائياً

            ip_address = get_client_ip(request)

            # إنشاء الجهاز الجديد (device_token يُولد تلقائياً)
            device = BranchDevice.objects.create(
                branch=branch,
                device_name=device_name,
                manual_identifier=manual_identifier,
                ip_address=ip_address,
                user_agent=user_agent,
                notes=notes,
                is_active=True,
                registered_with_qr_version=qr_master.version,
            )

            # تسجيل استخدام QR Master
            qr_master.mark_used()

            logger.info(
                f"✅ New device registered with QR Master v{qr_master.version}: {device_name} (Token: {device.device_token}) for branch {branch.name} by {request.user.username}"
            )

            messages.success(
                request,
                mark_safe(
                    f'✅ تم تسجيل الجهاز "{device_name}" بنجاح للفرع: {branch.name}<br>'
                    f"يمكن الآن لموظفي الفرع تسجيل الدخول من هذا الجهاز."
                ),
            )

            # إعادة التوجيه مع device_token في URL لحفظه في IndexedDB
            from django.http import HttpResponseRedirect

            redirect_url = (
                f"{request.path}?device_token={device.device_token}&success=1"
            )
            return HttpResponseRedirect(redirect_url)

        except Exception as e:
            logger.error(f"Error registering device: {e}")
            logger.error(traceback.format_exc())
            messages.error(request, f"حدث خطأ أثناء تسجيل الجهاز: {str(e)}")
            return redirect("accounts:register_device")

    # GET request - عرض النموذج
    branches = Branch.objects.filter(is_active=True).order_by("name")
    active_qr = MasterQRCode.get_active()

    context = {
        "branches": branches,
        "title": "تسجيل جهاز جديد",
        "qr_master_required": True,
        "active_qr_version": active_qr.version if active_qr else None,
    }

    return render(request, "accounts/register_device.html", context)


@login_required
def device_diagnostic_view(request):
    """
    صفحة تشخيص الجهاز - لمعرفة ما إذا كان مسجلاً
    """
    context = {
        "title": "تشخيص الجهاز",
    }
    return render(request, "accounts/device_diagnostic.html", context)


@staff_member_required
def print_qr_master(request, qr_id):
    """
    صفحة طباعة QR Master - تعرض QR كبير قابل للطباعة
    """
    qr_master = get_object_or_404(MasterQRCode, pk=qr_id)

    import base64
    from io import BytesIO

    import qrcode

    # توليد QR Code كبير للطباعة
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=15,  # أكبر للطباعة
        border=5,
    )
    qr.add_data(qr_master.code)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # تحويل إلى base64
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    context = {
        "qr_master": qr_master,
        "qr_image": img_base64,
        "title": f"QR Master v{qr_master.version}",
    }

    return render(request, "accounts/print_qr_master.html", context)


@login_required
def profile_view(request):
    """
    View for user profile
    """
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث الملف الشخصي بنجاح.")
            return redirect("accounts:profile")
    else:
        form = UserProfileForm(instance=request.user)

    context = {
        "form": form,
        "user": request.user,
        "title": "الملف الشخصي",
    }
    return render(request, "accounts/profile.html", context)


@login_required
def company_info_view(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, "هذه الصفحة متاحة فقط لمديري النظام.")
            return redirect("home")
        """
        View for managing company information
        """
        # Get or create company info
        company, _ = CompanyInfo.objects.get_or_create(
            defaults={
                "name": "شركة الخواجه",
                "address": "العنوان",
                "phone": "01234567890",
                "email": "info@example.com",
            }
        )

        if request.method == "POST":
            form = CompanyInfoForm(request.POST, request.FILES, instance=company)
            if form.is_valid():
                form.save()
                messages.success(request, "تم تحديث معلومات الشركة بنجاح.")
                return redirect("accounts:company_info")
        else:
            form = CompanyInfoForm(instance=company)

        context = {
            "form": form,
            "company": company,
            "title": "معلومات الشركة",
        }

        return render(request, "accounts/company_info.html", context)
    except Exception as e:
        import traceback

        logger.debug("[CompanyInfo Error]", e)
        traceback.print_exc()
        messages.error(
            request,
            "حدث خطأ غير متوقع أثناء معالجة معلومات الشركة. يرجى مراجعة الدعم الفني.",
        )
        return redirect("home")


@staff_member_required
def form_field_list(request):
    """
    View for listing form fields
    """
    form_type = request.GET.get("form_type", "")

    # Filter form fields
    if form_type:
        form_fields = FormField.objects.filter(form_type=form_type)
    else:
        form_fields = FormField.objects.all()

    # Paginate form fields
    paginator = Paginator(form_fields, 10)  # Show 10 form fields per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "form_type": form_type,
        "form_types": dict(FormField.FORM_CHOICES),
        "title": "إدارة حقول النماذج",
    }

    return render(request, "accounts/form_field_list.html", context)


@staff_member_required
def form_field_create(request):
    """
    View for creating a new form field
    """
    if request.method == "POST":
        form = FormFieldForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "تم إضافة الحقل بنجاح.")
            return redirect("accounts:form_field_list")
    else:
        # Pre-fill form type if provided in GET parameters
        form_type = request.GET.get("form_type", "")
        form = FormFieldForm(initial={"form_type": form_type})

    context = {
        "form": form,
        "title": "إضافة حقل جديد",
    }

    return render(request, "accounts/form_field_form.html", context)


@staff_member_required
def form_field_update(request, pk):
    """
    View for updating a form field
    """
    form_field = get_object_or_404(FormField, pk=pk)

    if request.method == "POST":
        form = FormFieldForm(request.POST, instance=form_field)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث الحقل بنجاح.")
            return redirect("accounts:form_field_list")
    else:
        form = FormFieldForm(instance=form_field)

    context = {
        "form": form,
        "form_field": form_field,
        "title": "تعديل الحقل",
    }

    return render(request, "accounts/form_field_form.html", context)


@staff_member_required
def form_field_delete(request, pk):
    """
    View for deleting a form field
    """
    form_field = get_object_or_404(FormField, pk=pk)

    if request.method == "POST":
        form_field.delete()
        messages.success(request, "تم حذف الحقل بنجاح.")
        return redirect("accounts:form_field_list")

    context = {
        "form_field": form_field,
        "title": "حذف الحقل",
    }

    return render(request, "accounts/form_field_confirm_delete.html", context)


@staff_member_required
def toggle_form_field(request, pk):
    """
    View for toggling a form field's enabled status via AJAX
    """
    if request.method == "POST":
        form_field = get_object_or_404(FormField, pk=pk)
        form_field.enabled = not form_field.enabled
        form_field.save()

        return JsonResponse(
            {"success": True, "enabled": form_field.enabled, "field_id": form_field.id}
        )

    return JsonResponse({"success": False, "message": "طريقة غير صالحة."})


# إدارة الأقسام Department Management Views


@staff_member_required
def department_list(request):
    """
    عرض قائمة الأقسام مع إمكانية البحث والتصفية
    """
    search_query = request.GET.get("search", "")
    parent_filter = request.GET.get("parent", "")

    # قاعدة البيانات الأساسية
    departments = (
        Department.objects.all().select_related("parent").prefetch_related("children")
    )

    # تطبيق البحث
    if search_query:
        departments = departments.filter(
            Q(name__icontains=search_query)
            | Q(code__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    # تصفية حسب القسم الرئيسي
    if parent_filter:
        departments = departments.filter(parent_id=parent_filter)

    # الترتيب
    departments = departments.order_by("order", "name")

    # التقسيم لصفحات
    paginator = Paginator(departments, 15)  # 15 قسم في كل صفحة
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # جلب قائمة الأقسام الرئيسية للتصفية مع كاش
    from django.core.cache import cache

    parent_departments = cache.get("parent_departments")
    if not parent_departments:
        parent_departments = list(Department.objects.filter(parent__isnull=True))
        cache.set("parent_departments", parent_departments, 3600)  # كاش لمدة ساعة

    context = {
        "page_obj": page_obj,
        "total_departments": departments.count(),
        "search_query": search_query,
        "parent_filter": parent_filter,
        "parent_departments": parent_departments,
        "title": "إدارة الأقسام",
    }

    return render(request, "accounts/department_list.html", context)


@staff_member_required
def department_create(request):
    """
    إنشاء قسم جديد
    """
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "تم إضافة القسم بنجاح.")
            return redirect("accounts:department_list")
    else:
        form = DepartmentForm()

    context = {
        "form": form,
        "title": "إضافة قسم جديد",
    }

    return render(request, "accounts/department_form.html", context)


@staff_member_required
def department_update(request, pk):
    """
    تحديث قسم
    """
    department = get_object_or_404(Department, pk=pk)

    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث القسم بنجاح.")
            return redirect("accounts:department_list")
    else:
        form = DepartmentForm(instance=department)

    context = {
        "form": form,
        "department": department,
        "title": "تعديل القسم",
    }

    return render(request, "accounts/department_form.html", context)


@staff_member_required
def department_delete(request, pk):
    """
    حذف قسم
    """
    department = get_object_or_404(Department, pk=pk)

    if request.method == "POST":
        # فحص ما إذا كان القسم يحتوي على أقسام فرعية
        if department.children.exists():
            messages.error(request, "لا يمكن حذف القسم لأنه يحتوي على أقسام فرعية.")
            return redirect("accounts:department_list")

        department.delete()
        messages.success(request, "تم حذف القسم بنجاح.")
        return redirect("accounts:department_list")

    context = {
        "department": department,
        "title": "حذف القسم",
    }

    return render(request, "accounts/department_confirm_delete.html", context)


@staff_member_required
def toggle_department(request, pk):
    """
    تفعيل/إيقاف قسم
    """
    if request.method == "POST":
        department = get_object_or_404(Department, pk=pk)
        department.is_active = not department.is_active
        department.save()

        return JsonResponse(
            {
                "success": True,
                "is_active": department.is_active,
                "department_id": department.id,
            }
        )

    return JsonResponse({"success": False, "message": "طريقة غير صالحة."})


# إدارة البائعين Salesperson Management Views


@staff_member_required
def salesperson_list(request):
    """
    عرض قائمة البائعين مع إمكانية البحث والتصفية
    """
    search_query = request.GET.get("search", "")
    branch_filter = request.GET.get("branch", "")
    is_active = request.GET.get("is_active", "")

    # قاعدة البيانات الأساسية
    salespersons = Salesperson.objects.select_related("branch").all()

    # تطبيق البحث
    if search_query:
        salespersons = salespersons.filter(
            Q(name__icontains=search_query)
            | Q(employee_number__icontains=search_query)
            | Q(phone__icontains=search_query)
        )

    # تصفية حسب الفرع
    if branch_filter:
        salespersons = salespersons.filter(branch_id=branch_filter)

    # تصفية حسب الحالة
    if is_active:
        is_active = is_active == "true"
        salespersons = salespersons.filter(is_active=is_active)

    # الترتيب
    salespersons = salespersons.order_by("name")

    # التقسيم لصفحات
    paginator = Paginator(salespersons, 10)  # 10 بائعين في كل صفحة
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # جلب قائمة الفروع للتصفية مع كاش
    from django.core.cache import cache

    branches = cache.get("branches")
    if not branches:
        branches = list(Branch.objects.all())
        cache.set("branches", branches, 3600)  # كاش لمدة ساعة

    context = {
        "page_obj": page_obj,
        "total_salespersons": salespersons.count(),
        "search_query": search_query,
        "branch_filter": branch_filter,
        "is_active": is_active,
        "branches": branches,
        "title": "قائمة البائعين",
    }

    return render(request, "accounts/salesperson_list.html", context)


@staff_member_required
def salesperson_create(request):
    """
    إنشاء بائع جديد
    """
    if request.method == "POST":
        form = SalespersonForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "تم إضافة البائع بنجاح.")
            return redirect("accounts:salesperson_list")
    else:
        form = SalespersonForm()

    context = {
        "form": form,
        "title": "إضافة بائع جديد",
    }

    return render(request, "accounts/salesperson_form.html", context)


@staff_member_required
def salesperson_update(request, pk):
    """
    تحديث بائع
    """
    salesperson = get_object_or_404(Salesperson, pk=pk)

    if request.method == "POST":
        form = SalespersonForm(request.POST, instance=salesperson)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات البائع بنجاح.")
            return redirect("accounts:salesperson_list")
    else:
        form = SalespersonForm(instance=salesperson)

    context = {
        "form": form,
        "salesperson": salesperson,
        "title": "تعديل بيانات البائع",
    }

    return render(request, "accounts/salesperson_form.html", context)


@staff_member_required
def salesperson_delete(request, pk):
    """
    حذف بائع
    """
    salesperson = get_object_or_404(Salesperson, pk=pk)

    if request.method == "POST":
        try:
            salesperson.delete()
            messages.success(request, "تم حذف البائع بنجاح.")
        except Exception as e:
            messages.error(request, "لا يمكن حذف البائع لارتباطه بسجلات أخرى.")
        return redirect("accounts:salesperson_list")

    context = {
        "salesperson": salesperson,
        "title": "حذف البائع",
    }

    return render(request, "accounts/salesperson_confirm_delete.html", context)


@staff_member_required
def toggle_salesperson(request, pk):
    """
    تفعيل/إيقاف بائع
    """
    if request.method == "POST":
        salesperson = get_object_or_404(Salesperson, pk=pk)
        salesperson.is_active = not salesperson.is_active
        salesperson.save()

        return JsonResponse(
            {
                "success": True,
                "is_active": salesperson.is_active,
                "salesperson_id": salesperson.id,
            }
        )

    return JsonResponse({"success": False, "message": "طريقة غير صالحة."})


# إدارة الأدوار Role Management Views


@staff_member_required
def role_list(request):
    """
    عرض قائمة الأدوار مع إمكانية البحث والتصفية والتقسيم بشكل مستقل
    """
    roles = Role.objects.all()

    # بحث عن الأدوار
    search_query = request.GET.get("search", "")
    if search_query:
        roles = roles.filter(name__icontains=search_query)

    # تصفية الأدوار
    role_type = request.GET.get("type", "")
    if role_type == "system":
        roles = roles.filter(is_system_role=True)
    elif role_type == "custom":
        roles = roles.filter(is_system_role=False)

    # ترتيب الأدوار
    roles = roles.order_by("name")

    # التقسيم لصفحات
    paginator = Paginator(roles, 10)  # عرض 10 أدوار في كل صفحة
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "role_type": role_type,
        "title": "إدارة الأدوار",
    }

    return render(request, "accounts/role_list.html", context)


@staff_member_required
def role_create(request):
    """
    إنشاء دور جديد
    """
    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()
            messages.success(request, f"تم إنشاء دور {role.name} بنجاح.")
            return redirect("accounts:role_list")
    else:
        form = RoleForm()

    context = {
        "form": form,
        "title": "إنشاء دور جديد",
    }

    return render(request, "accounts/role_form.html", context)


@staff_member_required
def role_update(request, pk):
    """
    تحديث دور
    """
    role = get_object_or_404(Role, pk=pk)

    # لا يمكن تحديث أدوار النظام إلا للمشرفين
    if role.is_system_role and not request.user.is_superuser:
        messages.error(request, "لا يمكنك تعديل أدوار النظام الأساسية.")
        return redirect("accounts:role_list")

    if request.method == "POST":
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            updated_role = form.save()

            # تحديث صلاحيات المستخدمين الذين لديهم هذا الدور
            for user_role in UserRole.objects.filter(role=updated_role):
                user = user_role.user
                # إعادة تعيين الصلاحيات من الأدوار
                user_roles = user.user_roles.all()
                # إعادة تعيين صلاحيات المستخدم
                user.user_permissions.clear()
                for ur in user_roles:
                    for permission in ur.role.permissions.all():
                        user.user_permissions.add(permission)

            messages.success(request, f"تم تحديث دور {role.name} بنجاح.")
            return redirect("accounts:role_list")
    else:
        form = RoleForm(instance=role)

    context = {
        "form": form,
        "role": role,
        "title": f"تحديث دور {role.name}",
    }

    return render(request, "accounts/role_form.html", context)


@staff_member_required
def role_delete(request, pk):
    """
    حذف دور
    """
    role = get_object_or_404(Role, pk=pk)

    # لا يمكن حذف أدوار النظام
    if role.is_system_role:
        messages.error(request, "لا يمكن حذف أدوار النظام الأساسية.")
        return redirect("accounts:role_list")

    if request.method == "POST":
        role_name = role.name

        # حذف علاقات الدور بالمستخدمين
        UserRole.objects.filter(role=role).delete()

        # حذف الدور
        role.delete()

        messages.success(request, f"تم حذف دور {role_name} بنجاح.")
        return redirect("accounts:role_list")

    context = {
        "role": role,
        "title": f"حذف دور {role.name}",
    }

    return render(request, "accounts/role_confirm_delete.html", context)


@staff_member_required
def role_assign(request, pk):
    """
    إسناد دور للمستخدمين
    """
    role = get_object_or_404(Role, pk=pk)

    if request.method == "POST":
        form = RoleAssignForm(request.POST, role=role)
        if form.is_valid():
            users = form.cleaned_data["users"]
            count = 0
            for user in users:
                # إنشاء علاقة بين الدور والمستخدم
                UserRole.objects.get_or_create(user=user, role=role)
                # إضافة صلاحيات الدور للمستخدم
                for permission in role.permissions.all():
                    user.user_permissions.add(permission)
                count += 1

            messages.success(
                request, f"تم إسناد دور {role.name} لـ {count} مستخدمين بنجاح."
            )
            return redirect("accounts:role_list")
    else:
        form = RoleAssignForm(role=role)

    context = {
        "form": form,
        "role": role,
        "title": f"إسناد دور {role.name} للمستخدمين",
    }

    return render(request, "accounts/role_assign_form.html", context)


@staff_member_required
def role_management(request):
    """
    الصفحة الرئيسية لإدارة الأدوار
    """
    roles = Role.objects.all().prefetch_related("user_roles", "permissions")
    users = (
        User.objects.filter(is_active=True)
        .exclude(is_superuser=True)
        .prefetch_related("user_roles")
    )

    # تصفية الأدوار
    role_type = request.GET.get("type", "")
    if role_type == "system":
        roles = roles.filter(is_system_role=True)
    elif role_type == "custom":
        roles = roles.filter(is_system_role=False)

    # تقسيم الصفحات
    paginator = Paginator(roles, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "users": users,
        "role_type": role_type,
        "title": "إدارة الأدوار والصلاحيات",
        "total_roles": roles.count(),
        "total_users": users.count(),
    }

    return render(request, "accounts/role_management.html", context)


@login_required
def set_default_theme(request):
    """
    تعيين الثيم الافتراضي للمستخدم
    """
    if request.method == "POST":
        try:
            import json

            data = json.loads(request.body)
            theme = data.get("theme", "default")

            # حفظ الثيم الافتراضي للمستخدم
            request.user.default_theme = theme
            request.user.save()

            return JsonResponse(
                {"success": True, "message": f'تم تعيين "{theme}" كثيم افتراضي'}
            )

        except Exception as e:
            return JsonResponse({"success": False, "message": f"حدث خطأ: {str(e)}"})

    return JsonResponse({"success": False, "message": "طريقة غير مدعومة"})
