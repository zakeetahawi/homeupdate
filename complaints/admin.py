from django.contrib import admin
from django.db import models
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from accounts.models import Department

from .models import (
    Complaint,
    ComplaintAttachment,
    ComplaintEscalation,
    ComplaintSLA,
    ComplaintTemplate,
    ComplaintType,
    ComplaintUpdate,
    ComplaintUserPermissions,
    ResolutionMethod,
)


@admin.register(ComplaintType)
class ComplaintTypeAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        "name",
        "default_priority",
        "default_deadline_hours",
        "responsible_department",
        "default_assignee",
        "is_active",
        "order",
    ]
    list_filter = ["default_priority", "is_active", "responsible_department"]
    search_fields = ["name", "description"]
    ordering = ["order", "name"]

    fieldsets = (
        ("معلومات أساسية", {"fields": ("name", "description", "is_active", "order")}),
        (
            "الإعدادات الافتراضية",
            {
                "fields": (
                    "default_priority",
                    "default_deadline_hours",
                    "responsible_department",
                    "default_assignee",
                    "responsible_staff",
                )
            },
        ),
        (
            "التواريخ",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    filter_horizontal = ("responsible_staff",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ComplaintUserPermissions)
class ComplaintUserPermissionsAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "permissions_summary",
        "current_assigned_count",
        "max_assigned_complaints",
        "is_active",
    ]
    list_filter = [
        "can_be_assigned_complaints",
        "can_receive_escalations",
        "can_escalate_complaints",
        "can_view_all_complaints",
        "can_edit_all_complaints",
        "can_delete_complaints",
        "can_assign_complaints",
        "can_resolve_complaints",
        "can_close_complaints",
        "is_active",
    ]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    ]
    filter_horizontal = ["departments", "complaint_types"]
    list_editable = ["is_active"]

    fieldsets = (
        ("المستخدم", {"fields": ("user",)}),
        (
            "صلاحيات الإسناد والتصعيد",
            {
                "fields": (
                    "can_be_assigned_complaints",
                    "can_receive_escalations",
                    "can_escalate_complaints",
                    "can_assign_complaints",
                    "max_assigned_complaints",
                ),
                "description": "صلاحيات متعلقة بإسناد وتصعيد الشكاوى",
            },
        ),
        (
            "صلاحيات العرض والتعديل",
            {
                "fields": (
                    "can_view_all_complaints",
                    "can_edit_all_complaints",
                    "can_delete_complaints",
                ),
                "description": "صلاحيات عرض وتعديل الشكاوى",
            },
        ),
        (
            "صلاحيات إدارة الحالة",
            {
                "fields": (
                    "can_change_complaint_status",
                    "can_resolve_complaints",
                    "can_close_complaints",
                ),
                "description": "صلاحيات تغيير حالة الشكاوى",
            },
        ),
        (
            "التخصص",
            {
                "fields": ("departments", "complaint_types"),
                "description": "تحديد الأقسام وأنواع الشكاوى التي يمكن للمستخدم التعامل معها",
            },
        ),
        ("الحالة", {"fields": ("is_active",)}),
        (
            "معلومات النظام",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ("created_at", "updated_at")

    def permissions_summary(self, obj):
        """ملخص الصلاحيات"""
        permissions = []
        if obj.can_view_all_complaints:
            permissions.append("عرض الكل")
        if obj.can_edit_all_complaints:
            permissions.append("تعديل الكل")
        if obj.can_be_assigned_complaints:
            permissions.append("إسناد إليه")
        if obj.can_assign_complaints:
            permissions.append("إسناد للآخرين")
        if obj.can_escalate_complaints:
            permissions.append("تصعيد")
        if obj.can_receive_escalations:
            permissions.append("استقبال تصعيد")
        if obj.can_resolve_complaints:
            permissions.append("حل")
        if obj.can_close_complaints:
            permissions.append("إغلاق")
        if obj.can_delete_complaints:
            permissions.append("حذف")

        if not permissions:
            return format_html('<span style="color: gray;">لا توجد صلاحيات</span>')

        return format_html(
            '<span style="color: green;">{}</span>', " | ".join(permissions)
        )

    permissions_summary.short_description = "ملخص الصلاحيات"

    def current_assigned_count(self, obj):
        """عدد الشكاوى المسندة حالياً"""
        count = obj.current_assigned_complaints_count
        if obj.max_assigned_complaints > 0:
            percentage = (count / obj.max_assigned_complaints) * 100
            if percentage >= 90:
                color = "red"
            elif percentage >= 70:
                color = "orange"
            else:
                color = "green"
            return format_html(
                '<span style="color: {};">{}/{}</span>',
                color,
                count,
                obj.max_assigned_complaints,
            )
        return count

    current_assigned_count.short_description = "الشكاوى المسندة"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    actions = [
        "enable_assignment",
        "disable_assignment",
        "enable_escalation",
        "disable_escalation",
        "enable_escalate_permission",
        "disable_escalate_permission",
        "enable_all_permissions",
        "disable_all_permissions",
        "make_supervisor",
        "make_staff_member",
    ]

    def enable_assignment(self, request, queryset):
        """تفعيل إمكانية الإسناد"""
        updated = queryset.update(can_be_assigned_complaints=True)
        self.message_user(request, f"تم تفعيل إمكانية الإسناد لـ {updated} مستخدم")

    enable_assignment.short_description = "تفعيل إمكانية الإسناد"

    def disable_assignment(self, request, queryset):
        """إلغاء إمكانية الإسناد"""
        updated = queryset.update(can_be_assigned_complaints=False)
        self.message_user(request, f"تم إلغاء إمكانية الإسناد لـ {updated} مستخدم")

    disable_assignment.short_description = "إلغاء إمكانية الإسناد"

    def enable_escalation(self, request, queryset):
        """تفعيل إمكانية التصعيد"""
        updated = queryset.update(can_receive_escalations=True)
        self.message_user(request, f"تم تفعيل إمكانية التصعيد لـ {updated} مستخدم")

    enable_escalation.short_description = "تفعيل إمكانية التصعيد"

    def disable_escalation(self, request, queryset):
        """إلغاء إمكانية التصعيد"""
        updated = queryset.update(can_receive_escalations=False)
        self.message_user(request, f"تم إلغاء إمكانية التصعيد لـ {updated} مستخدم")

    disable_escalation.short_description = "إلغاء إمكانية التصعيد"

    def enable_escalate_permission(self, request, queryset):
        """تفعيل صلاحية التصعيد"""
        updated = queryset.update(can_escalate_complaints=True)
        self.message_user(request, f"تم تفعيل صلاحية التصعيد لـ {updated} مستخدم")

    enable_escalate_permission.short_description = "تفعيل صلاحية التصعيد"

    def disable_escalate_permission(self, request, queryset):
        """إلغاء صلاحية التصعيد"""
        updated = queryset.update(can_escalate_complaints=False)
        self.message_user(request, f"تم إلغاء صلاحية التصعيد لـ {updated} مستخدم")

    disable_escalate_permission.short_description = "إلغاء صلاحية التصعيد"

    def enable_all_permissions(self, request, queryset):
        """تفعيل جميع الصلاحيات (مشرف)"""
        updated = queryset.update(
            can_be_assigned_complaints=True,
            can_receive_escalations=True,
            can_escalate_complaints=True,
            can_view_all_complaints=True,
            can_edit_all_complaints=True,
            can_assign_complaints=True,
            can_resolve_complaints=True,
            can_close_complaints=True,
            is_active=True,
        )
        self.message_user(request, f"تم تفعيل جميع الصلاحيات لـ {updated} مستخدم")

    enable_all_permissions.short_description = "تفعيل جميع الصلاحيات (مشرف)"

    def disable_all_permissions(self, request, queryset):
        """إلغاء جميع الصلاحيات"""
        updated = queryset.update(
            can_be_assigned_complaints=False,
            can_receive_escalations=False,
            can_escalate_complaints=False,
            can_view_all_complaints=False,
            can_edit_all_complaints=False,
            can_assign_complaints=False,
            can_resolve_complaints=False,
            can_close_complaints=False,
            can_delete_complaints=False,
        )
        self.message_user(request, f"تم إلغاء جميع الصلاحيات لـ {updated} مستخدم")

    disable_all_permissions.short_description = "إلغاء جميع الصلاحيات"

    def make_supervisor(self, request, queryset):
        """جعل المستخدم مشرف شكاوى"""
        updated = queryset.update(
            can_be_assigned_complaints=True,
            can_receive_escalations=True,
            can_escalate_complaints=True,
            can_view_all_complaints=True,
            can_edit_all_complaints=True,
            can_assign_complaints=True,
            can_resolve_complaints=True,
            can_close_complaints=True,
            is_active=True,
        )

        # إضافة المستخدمين للمجموعات المناسبة
        from django.contrib.auth.models import Group

        try:
            supervisor_group = Group.objects.get(name="Complaints_Supervisors")
            manager_group = Group.objects.get(name="Managers")
            for permission in queryset:
                permission.user.groups.add(supervisor_group, manager_group)
        except Group.DoesNotExist:
            pass

        self.message_user(request, f"تم جعل {updated} مستخدم مشرف شكاوى")

    make_supervisor.short_description = "جعل مشرف شكاوى"

    def make_staff_member(self, request, queryset):
        """جعل المستخدم موظف شكاوى عادي"""
        updated = queryset.update(
            can_be_assigned_complaints=True,
            can_receive_escalations=False,
            can_escalate_complaints=False,
            can_view_all_complaints=False,
            can_edit_all_complaints=False,
            can_assign_complaints=False,
            can_resolve_complaints=True,
            can_close_complaints=False,
            can_delete_complaints=False,
            can_change_complaint_status=True,
            is_active=True,
        )

        # إضافة المستخدمين لمجموعة الموظفين
        from django.contrib.auth.models import Group

        try:
            staff_group = Group.objects.get(name="Complaints_Staff")
            for permission in queryset:
                # إزالة من المجموعات الإدارية
                permission.user.groups.remove(
                    *Group.objects.filter(
                        name__in=[
                            "Complaints_Supervisors",
                            "Managers",
                            "Complaints_Managers",
                        ]
                    )
                )
                # إضافة لمجموعة الموظفين
                permission.user.groups.add(staff_group)
        except Group.DoesNotExist:
            pass

        self.message_user(request, f"تم جعل {updated} مستخدم موظف شكاوى عادي")

    make_staff_member.short_description = "جعل موظف شكاوى عادي"


class ComplaintUpdateInline(admin.TabularInline):
    model = ComplaintUpdate
    extra = 0
    max_num = 10  # حد أقصى لعدد التحديثات المعروضة
    readonly_fields = ("created_at", "created_by")
    fields = (
        "update_type",
        "title",
        "description",
        "is_visible_to_customer",
        "old_status",
        "new_status",
        "old_assignee",
        "new_assignee",
        "resolution_method",
        "created_by",
        "created_at",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "created_by", "old_assignee", "new_assignee", "resolution_method"
            )
            .order_by("-created_at")[:10]
        )  # أحدث 10 تحديثات فقط

    def has_delete_permission(self, request, obj=None):
        return False  # منع حذف التحديثات للحفاظ على سجل التغييرات


class ComplaintAttachmentInline(admin.TabularInline):
    model = ComplaintAttachment
    extra = 0
    max_num = 5  # حد أقصى للمرفقات المعروضة
    readonly_fields = (
        "uploaded_at",
        "file_size",
        "uploaded_by",
        "filename",
        "file_size_display",
    )
    fields = (
        "file",
        "filename",
        "description",
        "uploaded_by",
        "uploaded_at",
        "file_size_display",
    )

    def file_size_display(self, obj):
        """عرض حجم الملف بتنسيق مناسب"""
        if not obj.file_size:
            return "-"

        if obj.file_size < 1024:
            return f"{obj.file_size} بايت"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} كيلوبايت"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} ميجابايت"

    file_size_display.short_description = "حجم الملف"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("uploaded_by")
            .order_by("-uploaded_at")
        )


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_per_page = 25  # تقليل العدد لتحسين الأداء
    list_max_show_all = 100  # حد أقصى للعرض الكامل
    list_display = [
        "complaint_number",
        "customer_name",
        "complaint_type",
        "status_display",
        "priority_display",
        "assigned_to",
        "deadline",
        "is_overdue_display",
        "created_at",
    ]
    list_filter = [
        "status",
        "priority",
        "complaint_type",
        "assigned_department",
        "created_at",
        "deadline",
    ]
    search_fields = ["complaint_number", "customer__name", "title", "description"]
    readonly_fields = [
        "complaint_number",
        "created_at",
        "updated_at",
        "resolved_at",
        "closed_at",
        "last_activity_at",
        "is_overdue_display",
        "time_remaining_display",
        "resolution_time_display",
    ]

    # تحسين الأداء
    list_select_related = [
        "customer",
        "complaint_type",
        "assigned_to",
        "assigned_department",
        "created_by",
    ]
    autocomplete_fields = ["customer", "assigned_to"]

    fieldsets = (
        (
            "معلومات الشكوى",
            {
                "fields": (
                    "complaint_number",
                    "customer",
                    "complaint_type",
                    "title",
                    "description",
                )
            },
        ),
        (
            "الطلب والأنظمة المرتبطة",
            {"fields": ("related_order", "content_type", "object_id")},
        ),
        (
            "الحالة والأولوية",
            {"fields": ("status", "priority", "assigned_to", "assigned_department")},
        ),
        (
            "التوقيتات",
            {
                "fields": (
                    "created_at",
                    "deadline",
                    "resolved_at",
                    "closed_at",
                    "is_overdue_display",
                    "time_remaining_display",
                    "resolution_time_display",
                )
            },
        ),
        (
            "تقييم العميل",
            {
                "fields": ("customer_rating", "customer_feedback"),
                "classes": ("collapse",),
            },
        ),
        ("ملاحظات", {"fields": ("internal_notes",), "classes": ("collapse",)}),
        (
            "معلومات النظام",
            {
                "fields": ("created_by", "branch", "updated_at", "last_activity_at"),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [ComplaintUpdateInline, ComplaintAttachmentInline]

    # تحسين الأداء للنماذج
    save_on_top = True
    preserve_filters = True

    def customer_name(self, obj):
        return obj.customer.name

    customer_name.short_description = "العميل"

    def status_display(self, obj):
        return format_html(
            '<span class="badge {}">{}</span>',
            obj.get_status_badge_class().replace("bg-", "badge-"),
            obj.get_status_display(),
        )

    status_display.short_description = "الحالة"

    def priority_display(self, obj):
        return format_html(
            '<span class="badge {}">{}</span>',
            obj.get_priority_badge_class().replace("bg-", "badge-"),
            obj.get_priority_display(),
        )

    priority_display.short_description = "الأولوية"

    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red;">✗ متأخرة</span>')
        return format_html('<span style="color: green;">✓ في الوقت</span>')

    is_overdue_display.short_description = "متأخرة؟"

    def time_remaining_display(self, obj):
        remaining = obj.time_remaining
        if remaining is None:
            return "منتهية"

        if remaining.total_seconds() <= 0:
            return format_html('<span style="color: red;">انتهت المهلة</span>')

        days = remaining.days
        hours = remaining.seconds // 3600

        if days > 0:
            return f"{days} يوم و {hours} ساعة"
        return f"{hours} ساعة"

    time_remaining_display.short_description = "الوقت المتبقي"

    def resolution_time_display(self, obj):
        resolution_time = obj.resolution_time
        if resolution_time is None:
            return "لم تحل بعد"

        days = resolution_time.days
        hours = resolution_time.seconds // 3600

        if days > 0:
            return f"{days} يوم و {hours} ساعة"
        return f"{hours} ساعة"

    resolution_time_display.short_description = "وقت الحل"

    def get_queryset(self, request):
        """تحسين الاستعلامات لتقليل وقت التحميل"""
        queryset = super().get_queryset(request)

        # تحسين العلاقات
        queryset = queryset.select_related(
            "customer",
            "complaint_type",
            "assigned_to",
            "assigned_department",
            "created_by",
            "branch",
        )

        # تطبيق صلاحيات الوصول
        user = request.user

        # مدير النظام يرى جميع الشكاوى
        if user.is_superuser:
            return queryset

        # فحص المجموعات الإدارية
        admin_groups = ["Complaints_Managers", "Complaints_Supervisors", "Managers"]
        if user.groups.filter(name__in=admin_groups).exists():
            return queryset

        # فحص صلاحيات الشكاوى المخصصة
        try:
            permissions = user.complaint_permissions
            if permissions.is_active and permissions.can_view_all_complaints:
                return queryset
        except:
            pass

        # المستخدمون العاديون يرون الشكاوى المسندة إليهم أو التي أنشأوها
        return queryset.filter(models.Q(assigned_to=user) | models.Q(created_by=user))

    actions = [
        "mark_as_resolved",
        "escalate_complaints",
        "export_as_csv",
        "export_as_excel",
    ]

    def has_change_permission(self, request, obj=None):
        """فحص صلاحية التعديل"""
        if not super().has_change_permission(request, obj):
            return False

        user = request.user

        # مدير النظام يمكنه التعديل
        if user.is_superuser:
            return True

        # فحص المجموعات الإدارية
        admin_groups = ["Complaints_Managers", "Complaints_Supervisors", "Managers"]
        if user.groups.filter(name__in=admin_groups).exists():
            return True

        # فحص صلاحيات الشكاوى المخصصة
        try:
            permissions = user.complaint_permissions
            if permissions.is_active and permissions.can_edit_all_complaints:
                return True
        except:
            pass

        # إذا كان هناك كائن محدد، فحص إذا كان المستخدم مسؤولاً عنه
        if obj:
            # السماح بتعديل الشكاوى المتأخرة للمسؤولين والمدراء
            if obj.is_overdue:
                # المدراء والمشرفين يمكنهم تعديل الشكاوى المتأخرة
                if user.groups.filter(
                    name__in=[
                        "Complaints_Managers",
                        "Complaints_Supervisors",
                        "Managers",
                    ]
                ).exists():
                    return True
                # المستخدمون مع صلاحية استقبال التصعيد يمكنهم تعديل الشكاوى المتأخرة
                try:
                    if (
                        hasattr(user, "complaint_permissions")
                        and user.complaint_permissions.can_receive_escalations
                    ):
                        return True
                except:
                    pass

            return obj.assigned_to == user or obj.created_by == user

        return False

    def has_delete_permission(self, request, obj=None):
        """فحص صلاحية الحذف"""
        if not super().has_delete_permission(request, obj):
            return False

        user = request.user

        # مدير النظام يمكنه الحذف
        if user.is_superuser:
            return True

        # فحص صلاحيات الحذف المخصصة
        try:
            permissions = user.complaint_permissions
            if permissions.is_active and permissions.can_delete_complaints:
                return True
        except:
            pass

        return False

    def mark_as_resolved(self, request, queryset):
        updated = queryset.filter(status__in=["new", "in_progress", "overdue"]).update(
            status="resolved", resolved_at=timezone.now()
        )
        self.message_user(request, f"تم تحديد {updated} شكاوى كمحلولة.")

    mark_as_resolved.short_description = "تحديد كمحلولة"

    def escalate_complaints(self, request, queryset):
        # هذا سيتطلب منطق أكثر تعقيداً
        self.message_user(request, "يرجى استخدام نموذج التصعيد الفردي لكل شكوى.")

    escalate_complaints.short_description = "تصعيد الشكاوى"

    def export_as_csv(self, request, queryset):
        """تصدير الشكاوى المحددة إلى ملف CSV"""
        from .utils.export import export_complaints_to_csv

        return export_complaints_to_csv(queryset=queryset)

    export_as_csv.short_description = "تصدير إلى CSV"

    def export_as_excel(self, request, queryset):
        """تصدير الشكاوى المحددة إلى ملف Excel"""
        from .utils.export import export_complaints_to_excel

        return export_complaints_to_excel(queryset=queryset)

    export_as_excel.short_description = "تصدير إلى Excel"


@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        "complaint",
        "update_type",
        "title",
        "created_by",
        "created_at",
        "is_visible_to_customer",
        "status_change_display",
        "resolution_method",
    ]
    list_filter = [
        "update_type",
        "is_visible_to_customer",
        "created_at",
        "complaint__status",
        ("created_by", admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        "complaint__complaint_number",
        "title",
        "description",
        "created_by__username",
        "created_by__first_name",
        "created_by__last_name",
    ]
    readonly_fields = [
        "created_at",
        "created_by",
        "old_status",
        "new_status",
        "old_assignee",
        "new_assignee",
    ]

    fieldsets = (
        (
            "معلومات التحديث",
            {
                "fields": (
                    "complaint",
                    "update_type",
                    "title",
                    "description",
                    "is_visible_to_customer",
                )
            },
        ),
        (
            "تغيير الحالة",
            {
                "fields": ("old_status", "new_status", "resolution_method"),
                "classes": ("collapse",),
            },
        ),
        (
            "تغيير التعيين",
            {"fields": ("old_assignee", "new_assignee"), "classes": ("collapse",)},
        ),
        (
            "معلومات النظام",
            {"fields": ("created_by", "created_at"), "classes": ("collapse",)},
        ),
    )

    def status_change_display(self, obj):
        """عرض تغيير الحالة"""
        if obj.update_type == "status_change" and obj.old_status and obj.new_status:
            return f"{obj.old_status} → {obj.new_status}"
        return "-"

    status_change_display.short_description = "تغيير الحالة"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("complaint", "created_by")


@admin.register(ComplaintAttachment)
class ComplaintAttachmentAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        "complaint",
        "filename",
        "file_size_display",
        "uploaded_by",
        "uploaded_at",
    ]
    list_filter = ["uploaded_at"]
    search_fields = ["complaint__complaint_number", "filename", "description"]
    readonly_fields = ["uploaded_at", "file_size"]

    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} بايت"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} كيلوبايت"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} ميجابايت"
        return "غير محدد"

    file_size_display.short_description = "حجم الملف"


@admin.register(ComplaintEscalation)
class ComplaintEscalationAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        "complaint",
        "reason",
        "escalated_from",
        "escalated_to",
        "escalated_by",
        "escalated_at",
        "resolved_at",
    ]
    list_filter = ["reason", "escalated_at", "resolved_at"]
    search_fields = ["complaint__complaint_number", "description"]
    readonly_fields = ["escalated_at"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "complaint", "escalated_from", "escalated_to", "escalated_by"
            )
        )


@admin.register(ComplaintSLA)
class ComplaintSLAAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = [
        "complaint_type",
        "response_time_hours",
        "resolution_time_hours",
        "escalation_time_hours",
        "target_satisfaction_rate",
        "is_active",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["complaint_type__name"]
    readonly_fields = ["created_at", "updated_at"]


# ملاحظة: Department admin موجود بالفعل في accounts.admin


@admin.register(ResolutionMethod)
class ResolutionMethodAdmin(admin.ModelAdmin):
    """إدارة طرق حل الشكاوى"""

    list_display = ["name", "description", "is_active", "order", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    list_editable = ["is_active", "order"]
    ordering = ["order", "name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("معلومات أساسية", {"fields": ("name", "description", "is_active", "order")}),
        (
            "معلومات النظام",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(ComplaintTemplate)
class ComplaintTemplateAdmin(admin.ModelAdmin):
    """إدارة قوالب الشكاوى"""

    list_display = ["name", "complaint_type", "priority", "is_active", "created_at"]
    list_filter = ["complaint_type", "priority", "is_active", "created_at"]
    search_fields = ["name", "title_template", "description_template"]
    list_editable = ["is_active"]
    ordering = ["complaint_type", "name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "معلومات أساسية",
            {"fields": ("name", "complaint_type", "priority", "is_active")},
        ),
        (
            "قوالب النصوص",
            {
                "fields": ("title_template", "description_template"),
                "description": "يمكن استخدام {customer}، {order}، {date} كمتغيرات",
            },
        ),
        ("إعدادات المهلة", {"fields": ("default_deadline_hours",)}),
        (
            "معلومات النظام",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
