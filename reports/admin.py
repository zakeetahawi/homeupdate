from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Report, ReportSchedule, SavedReport


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ("title", "report_type", "created_by", "created_at", "updated_at")
    list_filter = ("report_type", "created_by", "created_at")
    search_fields = ("title", "description")
    readonly_fields = ("created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = ("name", "report", "created_by", "created_at")
    list_filter = ("report", "created_by", "created_at")
    search_fields = ("name", "report__title")
    readonly_fields = ("created_by", "created_at")

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_per_page = 50  # عرض 50 صف كافتراضي
    list_display = (
        "name",
        "report",
        "frequency",
        "is_active",
        "created_by",
        "created_at",
    )
    list_filter = ("frequency", "is_active", "created_by", "created_at")
    search_fields = ("name", "report__title")
    filter_horizontal = ("recipients",)
    readonly_fields = ("created_by", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
