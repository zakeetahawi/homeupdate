import json
import re

from django.contrib.sessions.models import Session
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now, timezone
from user_agents import parse

# أكواد الألوان ANSI
RED = "\033[0;31m"
GREEN = "\033[0;32m"
WHITE = "\033[1;37m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
PURPLE = "\033[0;35m"
CYAN = "\033[0;36m"
NC = "\033[0m"


class AdvancedActivityLoggerMiddleware(MiddlewareMixin):
    """Middleware متقدم لتسجيل جميع أنشطة المستخدمين"""

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """معالجة الطلب وتسجيل النشاط"""
        # تخزين معلومات الطلب للاستخدام لاحقاً
        request._activity_start_time = now()
        request._activity_path = request.path
        request._activity_method = request.method

        # الحصول على معلومات المستخدم
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            request._activity_user = user
            self._update_online_status(request, user)

        return None

    def process_response(self, request, response):
        """معالجة الاستجابة وتسجيل النشاط"""
        try:
            self._log_activity(request, response)
        except Exception as e:
            print(f"{RED}[ERROR] خطأ في تسجيل النشاط: {e}{NC}")

        return response

    def _update_online_status(self, request, user):
        """تحديث حالة المستخدم المتصل"""
        try:
            from user_activity.models import OnlineUser

            ip_address = self._get_client_ip(request)
            session_key = request.session.session_key

            print(
                f"{GREEN}[DEBUG] Updating online status for user: {user.username}{NC}"
            )
            print(f"{GREEN}[DEBUG] IP: {ip_address}, Session: {session_key}{NC}")

            if not session_key:
                # إنشاء session key إذا لم يكن موجود
                request.session.create()
                session_key = request.session.session_key
                print(f"{GREEN}[DEBUG] Created new session: {session_key}{NC}")

            # تنظيف المستخدمين غير المتصلين أولاً
            OnlineUser.cleanup_offline_users()

            # محاولة الحصول على السجل الموجود لتقليل عمليات الكتابة على DB
            existing_user = OnlineUser.objects.filter(user=user).first()
            login_time = existing_user.login_time if existing_user else now()

            now_ts = now()
            should_write = True

            # إذا كان لدينا existing_user وتحديث آخر حدث قبل أقل من 10 ثواني
            # نتجنب الكتابة لتقليل حمل قاعدة البيانات
            if existing_user and existing_user.last_seen:
                delta = (now_ts - existing_user.last_seen).total_seconds()
                if delta < 10:
                    should_write = False

            if should_write:
                online_user, created = OnlineUser.objects.update_or_create(
                    user=user,
                    defaults={
                        "ip_address": ip_address,
                        "session_key": session_key,
                        "login_time": login_time,
                        "device_info": self._get_device_info(request),
                        "last_seen": now_ts,
                        "current_page": request.path,
                        "current_page_title": self._get_page_title(request.path),
                    },
                )

                print(
                    f"{GREEN}[DEBUG] Online user {'created' if created else 'updated'}: {user.username}{NC}"
                )

                # تحديث النشاط إذا كان المستخدم موجود مسبقاً
                if not created:
                    page_title = self._get_page_title(request.path)
                    action_performed = request.method in [
                        "POST",
                        "PUT",
                        "DELETE",
                        "PATCH",
                    ]
                    online_user.update_activity(
                        page_path=request.path,
                        page_title=page_title,
                        action_performed=action_performed,
                    )
                    print(f"{GREEN}[DEBUG] Activity updated for {user.username}{NC}")
            else:
                # فقط نحدّث الحقول في الذاكرة (لا نكتب للـ DB)
                # هذا يسمح للـ API أن يقرأ last_seen قريباً دون ضغط على DB
                existing_user.current_page = request.path
                existing_user.current_page_title = self._get_page_title(request.path)
                # لا ننادي save() هنا لتجنب عملية كتابة
                print(
                    f"{GREEN}[DEBUG] Skipped DB update for {user.username} (throttled){NC}"
                )

        except Exception as e:
            print(f"{RED}[ERROR] خطأ في تحديث حالة المستخدم المتصل: {e}{NC}")
            import traceback

            traceback.print_exc()

    def _log_activity(self, request, response):
        """تسجيل النشاط في قاعدة البيانات"""
        try:
            from user_activity.models import UserActivityLog, UserSession

            user = getattr(request, "_activity_user", None)
            if not user:
                return

            path = getattr(request, "_activity_path", request.path)
            method = getattr(request, "_activity_method", request.method)

            # تحديد نوع العملية
            action_type = self._determine_action_type(
                path, method, response.status_code
            )
            entity_type = self._determine_entity_type(path)

            # استخراج تفاصيل الكائن
            entity_id, entity_name = self._extract_entity_details(
                request, path, entity_type
            )

            # إنشاء وصف العملية
            description = self._create_description(
                path, method, action_type, entity_type, entity_name
            )

            # تجنب تسجيل طلبات الإشعارات والصور في سجل النشاط
            if (
                "/accounts/notifications/data/" in path
                or "/media/users/" in path
                or path.startswith("/media/")
                or path.endswith((".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico"))
                or "/accounts/api/online-users/" in path
            ):
                # لا تسجيل في قاعدة البيانات ولا طباعة في Terminal
                return

            # الحصول على الجلسة
            session = self._get_or_create_session(request, user)

            # تسجيل النشاط
            UserActivityLog.objects.create(
                user=user,
                session=session,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                description=description,
                url_path=path,
                http_method=method,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                success=200 <= response.status_code < 400,
                error_message=(
                    ""
                    if 200 <= response.status_code < 400
                    else f"HTTP {response.status_code}"
                ),
                extra_data={
                    "status_code": response.status_code,
                    "content_type": response.get("Content-Type", ""),
                    "page_title": self._get_page_title(path),
                },
            )

            # طباعة في Terminal
            self._print_terminal_log(
                user, action_type, path, method, response.status_code
            )

        except Exception as e:
            print(f"{RED}[ERROR] خطأ في تسجيل النشاط: {e}{NC}")

    def _get_or_create_session(self, request, user):
        """الحصول على الجلسة أو إنشاؤها"""
        try:
            from user_activity.models import UserSession

            session_key = request.session.session_key
            if not session_key:
                return None

            session, created = UserSession.objects.get_or_create(
                session_key=session_key,
                defaults={
                    "user": user,
                    "ip_address": self._get_client_ip(request),
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "device_type": self._get_device_type(request),
                    "browser": self._get_browser_info(request),
                    "operating_system": self._get_os_info(request),
                },
            )

            return session

        except Exception as e:
            print(f"{RED}[ERROR] خطأ في الحصول على الجلسة: {e}{NC}")
            return None

    def _determine_action_type(self, path, method, status_code):
        """تحديد نوع العملية"""
        if "/login/" in path and method == "POST":
            return "login" if status_code < 400 else "login_failed"
        elif "/logout/" in path:
            return "logout"
        elif method == "GET":
            if "/dashboard/" in path or "/admin/" in path:
                return "dashboard_view"
            else:
                return "page_view"
        elif method == "POST":
            if "/search/" in path or "search" in path:
                return "search"
            elif "/export/" in path or "export" in path:
                return "export"
            elif "/import/" in path or "import" in path:
                return "import"
            else:
                return "create"
        elif method == "PUT" or method == "PATCH":
            return "update"
        elif method == "DELETE":
            return "delete"
        else:
            return "other"

    def _determine_entity_type(self, path):
        """تحديد نوع الكائن"""
        if "/customer" in path:
            return "customer"
        elif "/order" in path:
            return "order"
        elif "/product" in path or "/inventory" in path:
            return "product"
        elif "/inspection" in path:
            return "inspection"
        elif "/manufacturing" in path:
            return "manufacturing"
        elif "/installation" in path:
            return "installation"
        elif "/report" in path:
            return "report"
        elif "/user" in path or "/account" in path:
            return "user"
        elif "/admin" in path or "/dashboard" in path:
            return "system"
        else:
            return "page"

    def _extract_entity_details(self, request, path, entity_type):
        """استخراج معرف واسم الكائن من الطلب"""
        try:
            # استخراج المعرف من URL
            entity_id = None
            entity_name = ""

            # البحث عن أنماط ID في URL
            import re

            id_patterns = [
                r"/(\d+)/",  # /123/
                r"/(\d+)$",  # /123 نهاية URL
                r"id=(\d+)",  # ?id=123
                r"pk=(\d+)",  # ?pk=123
            ]

            for pattern in id_patterns:
                match = re.search(pattern, path)
                if match:
                    entity_id = int(match.group(1))
                    break

            # محاولة استخراج اسم الكائن من بيانات POST أو GET
            if request.method == "POST":
                # البحث في بيانات POST
                if hasattr(request, "POST") and request.POST:
                    # أسماء حقول شائعة للأسماء
                    name_fields = [
                        "name",
                        "title",
                        "customer_name",
                        "product_name",
                        "order_number",
                        "full_name",
                    ]
                    for field in name_fields:
                        if field in request.POST and request.POST[field]:
                            entity_name = request.POST[field][:100]  # تقييد الطول
                            break

                    # إذا لم نجد اسم، نبحث عن رقم طلب أو معرف
                    if not entity_name:
                        order_fields = ["order_number", "order_id", "reference_number"]
                        for field in order_fields:
                            if field in request.POST and request.POST[field]:
                                entity_name = f"طلب #{request.POST[field]}"
                                break

            elif request.method == "GET":
                # البحث في بيانات GET
                if hasattr(request, "GET") and request.GET:
                    search_fields = ["search", "q", "query", "name"]
                    for field in search_fields:
                        if field in request.GET and request.GET[field]:
                            entity_name = f"بحث: {request.GET[field][:50]}"
                            break

            # إذا لم نجد اسم من البيانات، نحاول استخدام المعرف
            if not entity_name and entity_id:
                if entity_type == "customer":
                    entity_name = f"عميل #{entity_id}"
                elif entity_type == "order":
                    entity_name = f"طلب #{entity_id}"
                elif entity_type == "product":
                    entity_name = f"منتج #{entity_id}"
                elif entity_type == "inspection":
                    entity_name = f"معاينة #{entity_id}"
                else:
                    entity_name = f"{entity_type} #{entity_id}"

            return entity_id, entity_name

        except Exception as e:
            print(f"{YELLOW}[WARNING] خطأ في استخراج تفاصيل الكائن: {e}{NC}")
            return None, ""

    def _create_description(
        self, path, method, action_type, entity_type, entity_name=""
    ):
        """إنشاء وصف العملية مع تفاصيل الكائن"""
        action_names = {
            "login": "تسجيل دخول",
            "logout": "تسجيل خروج",
            "login_failed": "فشل تسجيل دخول",
            "page_view": "عرض صفحة",
            "dashboard_view": "عرض لوحة التحكم",
            "create": "إنشاء",
            "update": "تحديث",
            "delete": "حذف",
            "search": "بحث",
            "export": "تصدير",
            "import": "استيراد",
        }

        entity_names = {
            "customer": "عميل",
            "order": "طلب",
            "product": "منتج",
            "inspection": "معاينة",
            "manufacturing": "تصنيع",
            "installation": "تركيب",
            "report": "تقرير",
            "user": "مستخدم",
            "system": "النظام",
            "page": "صفحة",
        }

        action_name = action_names.get(action_type, action_type)
        entity_name_arabic = entity_names.get(entity_type, entity_type)

        if action_type in ["page_view", "dashboard_view"]:
            return f"{action_name}: {path}"
        elif action_type == "search":
            return f"{action_name} في {entity_name_arabic}"
        elif entity_name:
            return f"{action_name} {entity_name_arabic}: {entity_name}"
        else:
            return f"{action_name} {entity_name_arabic}"

    def _get_page_title(self, path):
        """الحصول على عنوان الصفحة"""
        page_titles = {
            "/": "الصفحة الرئيسية",
            "/dashboard/": "لوحة التحكم",
            "/admin/": "لوحة الإدارة",
            "/customers/": "العملاء",
            "/orders/": "الطلبات",
            "/products/": "المنتجات",
            "/inventory/": "المخزون",
            "/inspections/": "المعاينات",
            "/manufacturing/": "التصنيع",
            "/installations/": "التركيبات",
            "/reports/": "التقارير",
            "/accounts/": "الحسابات",
        }

        for pattern, title in page_titles.items():
            if path.startswith(pattern):
                return title

        return path

    def _get_client_ip(self, request):
        """الحصول على عنوان IP الحقيقي للعميل"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def _get_device_info(self, request):
        """الحصول على معلومات الجهاز"""
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        parsed_ua = parse(user_agent)

        return {
            "browser": f"{parsed_ua.browser.family} {parsed_ua.browser.version_string}",
            "os": f"{parsed_ua.os.family} {parsed_ua.os.version_string}",
            "device": parsed_ua.device.family,
            "is_mobile": parsed_ua.is_mobile,
            "is_tablet": parsed_ua.is_tablet,
            "is_pc": parsed_ua.is_pc,
        }

    def _get_device_type(self, request):
        """تحديد نوع الجهاز"""
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        parsed_ua = parse(user_agent)

        if parsed_ua.is_mobile:
            return "mobile"
        elif parsed_ua.is_tablet:
            return "tablet"
        elif parsed_ua.is_pc:
            return "desktop"
        else:
            return "unknown"

    def _get_browser_info(self, request):
        """الحصول على معلومات المتصفح"""
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        parsed_ua = parse(user_agent)
        return f"{parsed_ua.browser.family} {parsed_ua.browser.version_string}"

    def _get_os_info(self, request):
        """الحصول على معلومات نظام التشغيل"""
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        parsed_ua = parse(user_agent)
        return f"{parsed_ua.os.family} {parsed_ua.os.version_string}"

    def _print_terminal_log(self, user, action_type, path, method, status_code):
        """طباعة السجل في Terminal"""
        # إخفاء طباعة طلبات الإشعارات والصور والـ API لتجنب الإزعاج
        if (
            "/accounts/notifications/data/" in path
            or "/media/users/" in path
            or path.startswith("/media/")
            or path.endswith((".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico"))
            or "/accounts/api/online-users/" in path
        ):
            return

        time_str = now().strftime("%H:%M:%S")

        # تحديد اللون حسب نوع العملية
        if action_type == "login":
            color = GREEN
            icon = "🔐"
        elif action_type == "logout":
            color = BLUE
            icon = "🚪"
        elif action_type == "login_failed":
            color = RED
            icon = "❌"
        elif status_code >= 400:
            color = RED
            icon = "⚠️"
        elif method == "POST":
            color = YELLOW
            icon = "➕"
        elif method == "PUT" or method == "PATCH":
            color = PURPLE
            icon = "✏️"
        elif method == "DELETE":
            color = RED
            icon = "🗑️"
        else:
            color = WHITE
            icon = "👁️"

        print(
            f"{color}[{time_str}] {icon} {user.username} - {action_type} - {path} ({method}) [{status_code}]{NC}"
        )


# الاحتفاظ بالـ middleware القديم للتوافق
class TerminalActivityLoggerMiddleware(AdvancedActivityLoggerMiddleware):
    """Middleware قديم للتوافق مع الإعدادات الحالية"""

    pass
