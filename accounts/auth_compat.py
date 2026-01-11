"""
وحدة لتوفير توافق المصادقة بين النظام القديم (Bootstrap) والجديد (React)
"""

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken


@api_view(["POST"])
@permission_classes([AllowAny])
def auth_compat_view(request):
    """
    نقطة نهاية متوافقة مع كل من النظام القديم والجديد للمصادقة
    تقبل طلبات الكلا الواجهتين وترجع الردود بتنسيق يفهمه كل منهما
    """
    print("Auth compat endpoint called!")
    print(f"Request headers: {request.headers}")
    print(f"Request data: {request.data}")

    # استخراج بيانات الاعتماد
    username = request.data.get("username")
    password = request.data.get("password")

    # التحقق من وجود البيانات المطلوبة
    if not username or not password:
        print("Missing username or password")
        return Response(
            {"error": "يرجى إدخال اسم المستخدم وكلمة المرور"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # محاولة المصادقة
    user = authenticate(username=username, password=password)
    print(f"Authentication result: {user}")

    if user is not None:
        # إنشاء توكن JWT
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # إنشاء بيانات المستخدم
        user_data = {
            "username": user.username,
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }

        # إعداد الاستجابة بتنسيق يناسب كلا الواجهتين
        response_data = {
            # للواجهة الجديدة (React)
            "access": access_token,
            "refresh": str(refresh),
            "user": user_data,
            # للواجهة القديمة (Bootstrap)
            "token": access_token,
            "user_info": user_data,
        }

        return Response(response_data)
    else:
        return Response(
            {"error": "اسم المستخدم أو كلمة المرور غير صحيحة"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
