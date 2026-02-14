"""
ملف توافقية — تم نقل CurrentUserMiddleware إلى accounts/middleware/current_user.py
يُعاد التصدير هنا لمنع أخطاء الاستيراد في الكود القديم.
"""

# إعادة التصدير من الموقع الموحّد
from accounts.middleware.current_user import (  # noqa: F401
    get_current_request,
    get_current_user,
    set_current_user,
)

# CurrentUserMiddleware ← مسجّلة في settings.py من accounts.middleware.current_user
