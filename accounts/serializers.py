from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework import serializers

from .models import Role, UserRole

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    مسلسل معلومات المستخدم الأساسية
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "is_active",
            "is_staff",
            "is_superuser",
        ]
        read_only_fields = ["id", "is_active", "is_staff", "is_superuser"]

    def get_full_name(self, obj):
        return (
            f"{obj.first_name} {obj.last_name}".strip()
            if hasattr(obj, "first_name") and hasattr(obj, "last_name")
            else obj.username
        )


class PermissionSerializer(serializers.ModelSerializer):
    """معالج بيانات الصلاحية"""

    content_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ("id", "name", "codename", "content_type", "content_type_name")

    def get_content_type_name(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"


class RoleSerializer(serializers.ModelSerializer):
    """معالج بيانات الدور"""

    permissions_count = serializers.SerializerMethodField()
    users_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = (
            "id",
            "name",
            "description",
            "is_system_role",
            "permissions_count",
            "users_count",
            "created_at",
        )

    def get_permissions_count(self, obj):
        return obj.permissions.count()

    def get_users_count(self, obj):
        return obj.user_roles.count()


class RoleDetailSerializer(serializers.ModelSerializer):
    """معالج بيانات الدور مع التفاصيل الكاملة"""

    permissions = PermissionSerializer(many=True, read_only=True)
    users_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = (
            "id",
            "name",
            "description",
            "is_system_role",
            "permissions",
            "users_count",
            "created_at",
            "updated_at",
        )

    def get_users_count(self, obj):
        return obj.user_roles.count()


class UserRoleSerializer(serializers.ModelSerializer):
    """معالج بيانات علاقة المستخدم بالدور"""

    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), write_only=True, source="role"
    )

    class Meta:
        model = UserRole
        fields = ("id", "user", "role", "role_id", "assigned_at")
        read_only_fields = ("assigned_at",)
