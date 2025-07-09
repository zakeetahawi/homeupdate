import re
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now

# أكواد الألوان ANSI
RED = '\033[0;31m'
GREEN = '\033[0;32m'
WHITE = '\033[1;37m'
YELLOW = '\033[1;33m'
NC = '\033[0m'


class TerminalActivityLoggerMiddleware(MiddlewareMixin):
    def process_request(self, request):
        path = request.path
        user = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
        method = request.method
        time_str = now().strftime('%H:%M:%S')

        # عمليات الدخول
        if path == '/accounts/login/' and method == 'POST':
            if user:
                print(
                    f"{GREEN}[{time_str}] ✅ دخول المستخدم: "
                    f"{user.username}{NC}"
                )
            else:
                print(
                    f"{RED}[{time_str}] ❌ محاولة دخول فاشلة "
                    f"(اسم مستخدم أو كلمة مرور خاطئة){NC}"
                )

        # عمليات الخروج
        elif path == '/accounts/logout/':
            if user:
                print(
                    f"{RED}[{time_str}] 🚪 خروج المستخدم: "
                    f"{user.username}{NC}"
                )
            else:
                print(f"{RED}[{time_str}] 🚪 خروج مستخدم غير معروف{NC}")

        # محاولات مشبوهة (محاولة POST على صفحات حساسة أو محاولات اختراق)
        elif method == 'POST' and (
            re.search(r'admin|delete|reset|hack|attack', path, re.I)
            or 'sql' in request.body.decode(errors='ignore').lower()
        ):
            ip = request.META.get('REMOTE_ADDR')
            print(
                f"{RED}[{time_str}] ⚠️ محاولة مشبوهة على "
                f"{path} من IP {ip}{NC}"
            )

        # تتبع الصفحات المهمة
        elif method == 'GET' and path not in ['/favicon.ico', '/static/', '/media/']:
            important_pages = [
                '/orders/', '/dashboard/', '/reports/', '/accounts/',
                '/customers/', '/manufacturing/', '/inventory/'
            ]
            if any(path.startswith(p) for p in important_pages):
                print(
                    f"{WHITE}[{time_str}] 📄 تم فتح صفحة: "
                    f"{path}{NC}"
                )

        return None 