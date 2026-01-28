from django.contrib import admin

from .models import InstallationAccountingSettings, InstallationCard, TechnicianShare


@admin.register(InstallationAccountingSettings)
class InstallationAccountingSettingsAdmin(admin.ModelAdmin):
    list_display = ("default_price_per_window", "updated_at")

    def has_add_permission(self, request):
        # Only one instance allowed
        return not InstallationAccountingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class TechnicianShareInline(admin.TabularInline):
    model = TechnicianShare
    extra = 0
    fields = ("technician", "assigned_windows", "amount", "is_paid")
    readonly_fields = ("technician", "assigned_windows", "amount")


@admin.register(InstallationCard)
class InstallationCardAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_name",
        "windows_count",
        "total_cost",
        "status",
        "completion_date",
    )
    list_filter = ("status", "completion_date")
    search_fields = (
        "installation_schedule__order__order_number",
        "installation_schedule__order__customer__name",
    )
    inlines = [TechnicianShareInline]
    readonly_fields = ("total_cost", "completion_date")


@admin.register(TechnicianShare)
class TechnicianShareAdmin(admin.ModelAdmin):
    list_display = (
        "technician",
        "card",
        "assigned_windows",
        "amount",
        "is_paid",
        "paid_date",
    )
    list_filter = ("is_paid", "technician")
    search_fields = (
        "technician__name",
        "card__installation_schedule__order__order_number",
    )
