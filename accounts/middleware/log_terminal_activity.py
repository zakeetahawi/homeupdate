import re
import json
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now, timezone

from django.contrib.sessions.models import Session
from user_agents import parse

# أكواد الألوان ANSI
RED = '\033[0;31m'
GREEN = '\033[0;32m'
WHITE = '\033[1;37m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
PURPLE = '\033[0;35m'
CYAN = '\033[0;36m'
NC = '\033[0m'


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
        user = getattr(request, 'user', None)
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

            if not session_key:
                # إنشاء session key إذا لم يكن موجود
                request.session.create()
                session_key = request.session.session_key

            # تنظيف المستخدمين غير المتصلين أولاً
            OnlineUser.cleanup_offline_users()

            # تحديث أو إنشاء سجل المستخدم المتصل
            existing_user = OnlineUser.objects.filter(user=user).first()
            login_time = existing_user.login_time if existing_user else now()

            online_user, created = OnlineUser.objects.update_or_create(
                user=user,
                defaults={
                    'ip_address': ip_address,
                    'session_key': session_key,
                    'login_time': login_time,
                    'device_info': self._get_device_info(request),
                    'last_seen': now(),
                    'current_page': request.path,
                    'current_page_title': self._get_page_title(request.path),
                }
            )

            # تحديث النشاط إذا كان المستخدم موجود مسبقاً
            if not created:
                page_title = self._get_page_title(request.path)
                action_performed = request.method in ['POST', 'PUT', 'DELETE', 'PATCH']
                online_user.update_activity(
                    page_path=request.path,
                    page_title=page_title,
                    action_performed=action_performed
                )

        except Exception as e:
            print(f"{RED}[ERROR] خطأ في تحديث حالة المستخدم المتصل: {e}{NC}")

    def _log_activity(self, request, response):
        """تسجيل النشاط في قاعدة البيانات"""
        try:
            from user_activity.models import UserActivityLog, UserSession

            user = getattr(request, '_activity_user', None)
            if not user:
                return

            path = getattr(request, '_activity_path', request.path)
            method = getattr(request, '_activity_method', request.method)

            # تحديد نوع العملية
            action_type = self._determine_action_type(path, method, response.status_code)
            entity_type = self._determine_entity_type(path)

            # إنشاء وصف العملية
            description = self._create_description(path, method, action_type, entity_type)

            # تجنب تسجيل طلبات الإشعارات والصور في سجل النشاط
            if (
                '/accounts/notifications/data/' in path or
                '/media/users/' in path or
                path.startswith('/media/') or
                path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico')) or
                '/accounts/api/online-users/' in path
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
                description=description,
                url_path=path,
                http_method=method,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=200 <= response.status_code < 400,
                error_message='' if 200 <= response.status_code < 400 else f'HTTP {response.status_code}',
                extra_data={
                    'status_code': response.status_code,
                    'content_type': response.get('Content-Type', ''),
                    'page_title': self._get_page_title(path),
                }
            )

            # طباعة في Terminal
            self._print_terminal_log(user, action_type, path, method, response.status_code)

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
                    'user': user,
                    'ip_address': self._get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'device_type': self._get_device_type(request),
                    'browser': self._get_browser_info(request),
                    'operating_system': self._get_os_info(request),
                }
            )

            return session

        except Exception as e:
            print(f"{RED}[ERROR] خطأ في الحصول على الجلسة: {e}{NC}")
            return None

    def _determine_action_type(self, path, method, status_code):
        """تحديد نوع العملية"""
        if '/login/' in path and method == 'POST':
            return 'login' if status_code < 400 else 'login_failed'
        elif '/logout/' in path:
            return 'logout'
        elif method == 'GET':
            if '/dashboard/' in path or '/admin/' in path:
                return 'dashboard_view'
            else:
                return 'page_view'
        elif method == 'POST':
            if '/search/' in path or 'search' in path:
                return 'search'
            elif '/export/' in path or 'export' in path:
                return 'export'
            elif '/import/' in path or 'import' in path:
                return 'import'
            else:
                return 'create'
        elif method == 'PUT' or method == 'PATCH':
            return 'update'
        elif method == 'DELETE':
            return 'delete'
        else:
            return 'other'

    def _determine_entity_type(self, path):
        """تحديد نوع الكائن"""
        if '/customer' in path:
            return 'customer'
        elif '/order' in path:
            return 'order'
        elif '/product' in path or '/inventory' in path:
            return 'product'
        elif '/inspection' in path:
            return 'inspection'
        elif '/manufacturing' in path:
            return 'manufacturing'
        elif '/installation' in path:
            return 'installation'
        elif '/report' in path:
            return 'report'
        elif '/user' in path or '/account' in path:
            return 'user'
        elif '/admin' in path or '/dashboard' in path:
            return 'system'
        else:
            return 'page'

    def _create_description(self, path, method, action_type, entity_type):
        """إنشاء وصف العملية"""
        action_names = {
            'login': 'تسجيل دخول',
            'logout': 'تسجيل خروج',
            'login_failed': 'فشل تسجيل دخول',
            'page_view': 'عرض صفحة',
            'dashboard_view': 'عرض لوحة التحكم',
            'create': 'إنشاء',
            'update': 'تحديث',
            'delete': 'حذف',
            'search': 'بحث',
            'export': 'تصدير',
            'import': 'استيراد',
        }

        entity_names = {
            'customer': 'عميل',
            'order': 'طلب',
            'product': 'منتج',
            'inspection': 'معاينة',
            'manufacturing': 'تصنيع',
            'installation': 'تركيب',
            'report': 'تقرير',
            'user': 'مستخدم',
            'system': 'النظام',
            'page': 'صفحة',
        }

        action_name = action_names.get(action_type, action_type)
        entity_name = entity_names.get(entity_type, entity_type)

        if action_type in ['page_view', 'dashboard_view']:
            return f"{action_name}: {path}"
        else:
            return f"{action_name} {entity_name}"

    def _get_page_title(self, path):
        """الحصول على عنوان الصفحة"""
        page_titles = {
            '/': 'الصفحة الرئيسية',
            '/dashboard/': 'لوحة التحكم',
            '/admin/': 'لوحة الإدارة',
            '/customers/': 'العملاء',
            '/orders/': 'الطلبات',
            '/products/': 'المنتجات',
            '/inventory/': 'المخزون',
            '/inspections/': 'المعاينات',
            '/manufacturing/': 'التصنيع',
            '/installations/': 'التركيبات',
            '/reports/': 'التقارير',
            '/accounts/': 'الحسابات',
        }

        for pattern, title in page_titles.items():
            if path.startswith(pattern):
                return title

        return path

    def _get_client_ip(self, request):
        """الحصول على عنوان IP الحقيقي للعميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _get_device_info(self, request):
        """الحصول على معلومات الجهاز"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        parsed_ua = parse(user_agent)

        return {
            'browser': f"{parsed_ua.browser.family} {parsed_ua.browser.version_string}",
            'os': f"{parsed_ua.os.family} {parsed_ua.os.version_string}",
            'device': parsed_ua.device.family,
            'is_mobile': parsed_ua.is_mobile,
            'is_tablet': parsed_ua.is_tablet,
            'is_pc': parsed_ua.is_pc,
        }

    def _get_device_type(self, request):
        """تحديد نوع الجهاز"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        parsed_ua = parse(user_agent)

        if parsed_ua.is_mobile:
            return 'mobile'
        elif parsed_ua.is_tablet:
            return 'tablet'
        elif parsed_ua.is_pc:
            return 'desktop'
        else:
            return 'unknown'

    def _get_browser_info(self, request):
        """الحصول على معلومات المتصفح"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        parsed_ua = parse(user_agent)
        return f"{parsed_ua.browser.family} {parsed_ua.browser.version_string}"

    def _get_os_info(self, request):
        """الحصول على معلومات نظام التشغيل"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        parsed_ua = parse(user_agent)
        return f"{parsed_ua.os.family} {parsed_ua.os.version_string}"

    def _print_terminal_log(self, user, action_type, path, method, status_code):
        """طباعة السجل في Terminal"""
        # إخفاء طباعة طلبات الإشعارات والصور والـ API لتجنب الإزعاج
        if (
            '/accounts/notifications/data/' in path or
            '/media/users/' in path or
            path.startswith('/media/') or
            path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico')) or
            '/accounts/api/online-users/' in path
        ):
            return

        time_str = now().strftime('%H:%M:%S')

        # تحديد اللون حسب نوع العملية
        if action_type == 'login':
            color = GREEN
            icon = '🔐'
        elif action_type == 'logout':
            color = BLUE
            icon = '🚪'
        elif action_type == 'login_failed':
            color = RED
            icon = '❌'
        elif status_code >= 400:
            color = RED
            icon = '⚠️'
        elif method == 'POST':
            color = YELLOW
            icon = '➕'
        elif method == 'PUT' or method == 'PATCH':
            color = PURPLE
            icon = '✏️'
        elif method == 'DELETE':
            color = RED
            icon = '🗑️'
        else:
            color = WHITE
            icon = '👁️'

        print(f"{color}[{time_str}] {icon} {user.username} - {action_type} - {path} ({method}) [{status_code}]{NC}")





# الاحتفاظ بالـ middleware القديم للتوافق
class TerminalActivityLoggerMiddleware(AdvancedActivityLoggerMiddleware):
    """Middleware قديم للتوافق مع الإعدادات الحالية"""
    pass