from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import connection

User = get_user_model()


class CustomModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            # استخدام raw SQL للحصول على المستخدم
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM accounts_user WHERE username = %s LIMIT 1",
                    [username],
                )
                result = cursor.fetchone()

            if result:
                user_id = result[0]
                user = User.objects.get(id=user_id)

                # التحقق من كلمة المرور
                if user.check_password(password):
                    return user

            return None
        except Exception as e:
            # تسجيل الخطأ
            import traceback

            print(f"[Authentication Error] {e}")
            traceback.print_exc()
            return None
