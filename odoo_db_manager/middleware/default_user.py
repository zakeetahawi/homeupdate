"""
Middleware للتحقق من وجود مستخدم افتراضي عند بدء تشغيل Django
"""

import threading
from django.contrib.auth import get_user_model
from django.db import connection
from django.conf import settings


class DefaultUserMiddleware:
    """
    Middleware يتحقق من وجود مستخدمين في قاعدة البيانات
    وينشئ مستخدم افتراضي إذا لم يوجد أي مستخدمين
    """

    _checked = False
    _lock = threading.Lock()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # تخطي التحقق لمسارات معينة لتجنب التضارب أثناء الاستعادة
        path = request.path
        if 'restore-progress' in path or 'refresh-session' in path:
            return self.get_response(request)

        # التحقق مرة واحدة فقط عند بدء التشغيل
        if not DefaultUserMiddleware._checked:
            with DefaultUserMiddleware._lock:
                if not DefaultUserMiddleware._checked:
                    self._check_and_create_default_user()
                    DefaultUserMiddleware._checked = True

        response = self.get_response(request)
        return response

    def _check_and_create_default_user(self):
        """التحقق من وجود مستخدمين وإنشاء مستخدم افتراضي إذا لزم الأمر"""
        try:
            # التحقق من أن قاعدة البيانات متاحة ومهيأة
            if not self._is_database_ready():
                return

            User = get_user_model()

            # التحقق من وجود مستخدمين
            if User.objects.count() == 0:
                print("🔍 لم يتم العثور على مستخدمين في قاعدة البيانات")
                print("👤 جاري إنشاء مستخدم افتراضي...")

                # 🔒 إنشاء كلمة سر عشوائية آمنة
                import secrets
                default_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', secrets.token_urlsafe(16))
                
                # إنشاء المستخدم الافتراضي
                User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password=default_password,
                    first_name='مدير',
                    last_name='النظام'
                )

                print("✅ تم إنشاء المستخدم الافتراضي بنجاح:")
                print("   اسم المستخدم: admin")
                print(f"   كلمة المرور: {default_password}")
                print("⚠️  تحذير: يرجى تغيير كلمة المرور من لوحة الإدارة!")

        except Exception as e:
            # عدم إظهار الأخطاء في بيئة الإنتاج إلا إذا كان DEBUG مفعل
            if settings.DEBUG:
                print(f"❌ خطأ في التحقق من المستخدم الافتراضي: {str(e)}")

    def _is_database_ready(self):
        """التحقق من أن قاعدة البيانات جاهزة ومهيأة"""
        try:
            # التحقق من الاتصال بقاعدة البيانات
            with connection.cursor() as cursor:
                # التحقق من وجود جدول المستخدمين
                User = get_user_model()
                table_name = User._meta.db_table

                # استعلام للتحقق من وجود الجدول
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = %s
                    )
                """, [table_name])

                result = cursor.fetchone()
                return result[0] if result else False

        except Exception:
            return False
