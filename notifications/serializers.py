from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Notification, NotificationSettings, NotificationVisibility

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """مسلسل المستخدم"""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "full_name"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class NotificationVisibilitySerializer(serializers.ModelSerializer):
    """مسلسل رؤية الإشعارات"""

    user = UserSerializer(read_only=True)

    class Meta:
        model = NotificationVisibility
        fields = ["user", "is_read", "read_at", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    """مسلسل الإشعارات"""

    created_by = UserSerializer(read_only=True)
    notification_type_display = serializers.CharField(
        source="get_notification_type_display", read_only=True
    )
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )
    icon_class = serializers.CharField(source="get_icon_class", read_only=True)
    color_class = serializers.CharField(source="get_color_class", read_only=True)
    absolute_url = serializers.CharField(source="get_absolute_url", read_only=True)
    is_read = serializers.SerializerMethodField()
    read_at = serializers.SerializerMethodField()
    related_object_info = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "notification_type_display",
            "priority",
            "priority_display",
            "icon_class",
            "color_class",
            "created_by",
            "created_at",
            "extra_data",
            "absolute_url",
            "is_read",
            "read_at",
            "related_object_info",
        ]

    def get_is_read(self, obj):
        """الحصول على حالة القراءة للمستخدم الحالي"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                visibility = NotificationVisibility.objects.get(
                    notification=obj, user=request.user
                )
                return visibility.is_read
            except NotificationVisibility.DoesNotExist:
                return False
        return False

    def get_read_at(self, obj):
        """الحصول على تاريخ القراءة للمستخدم الحالي"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                visibility = NotificationVisibility.objects.get(
                    notification=obj, user=request.user
                )
                return visibility.read_at
            except NotificationVisibility.DoesNotExist:
                return None
        return None

    def get_related_object_info(self, obj):
        """الحصول على معلومات الكائن المرتبط"""
        if obj.related_object:
            try:
                return {
                    "type": obj.content_type.model,
                    "id": obj.object_id,
                    "str": str(obj.related_object),
                    "url": (
                        obj.related_object.get_absolute_url()
                        if hasattr(obj.related_object, "get_absolute_url")
                        else None
                    ),
                }
            except:
                return {
                    "type": obj.content_type.model if obj.content_type else None,
                    "id": obj.object_id,
                    "str": "كائن محذوف",
                    "url": None,
                }
        return None


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """مسلسل إعدادات الإشعارات"""

    user = UserSerializer(read_only=True)
    min_priority_level_display = serializers.CharField(
        source="get_min_priority_level_display", read_only=True
    )

    class Meta:
        model = NotificationSettings
        fields = [
            "user",
            "enable_customer_notifications",
            "enable_order_notifications",
            "enable_inspection_notifications",
            "enable_installation_notifications",
            "enable_complaint_notifications",
            "min_priority_level",
            "min_priority_level_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "created_at", "updated_at"]


class NotificationCreateSerializer(serializers.Serializer):
    """مسلسل إنشاء الإشعارات (للاستخدام الداخلي)"""

    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    notification_type = serializers.ChoiceField(choices=Notification.NOTIFICATION_TYPES)
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_LEVELS, default="normal"
    )
    extra_data = serializers.JSONField(required=False, default=dict)

    # معلومات الكائن المرتبط
    content_type_id = serializers.IntegerField(required=False, allow_null=True)
    object_id = serializers.IntegerField(required=False, allow_null=True)

    # المستخدمون المستهدفون
    recipient_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )


class NotificationSummarySerializer(serializers.Serializer):
    """مسلسل ملخص الإشعارات"""

    total_count = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    by_type = serializers.DictField()
    by_priority = serializers.DictField()
    recent_notifications = NotificationSerializer(many=True)


class NotificationBulkActionSerializer(serializers.Serializer):
    """مسلسل العمليات المجمعة على الإشعارات"""

    notification_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1
    )
    action = serializers.ChoiceField(choices=["mark_read", "mark_unread", "delete"])


class NotificationFilterSerializer(serializers.Serializer):
    """مسلسل فلترة الإشعارات"""

    notification_type = serializers.ChoiceField(
        choices=Notification.NOTIFICATION_TYPES, required=False, allow_blank=True
    )
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_LEVELS, required=False, allow_blank=True
    )
    is_read = serializers.BooleanField(required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    search = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """التحقق من صحة البيانات"""
        date_from = data.get("date_from")
        date_to = data.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                "تاريخ البداية يجب أن يكون قبل تاريخ النهاية"
            )

        return data
