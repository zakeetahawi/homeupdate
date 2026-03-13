from django.contrib import admin

from .models import (
    DecoratorEngineerProfile,
    EngineerContactLog,
    EngineerLinkedCustomer,
    EngineerLinkedOrder,
    EngineerMaterialInterest,
)


class LinkedCustomerInline(admin.TabularInline):
    model = EngineerLinkedCustomer
    extra = 0
    fields = ("customer", "linked_by", "default_commission_rate", "is_active", "linked_at")
    readonly_fields = ("linked_by", "linked_at")
    raw_id_fields = ("customer",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("customer", "linked_by")


class LinkedOrderInline(admin.TabularInline):
    model = EngineerLinkedOrder
    extra = 0
    fields = (
        "order",
        "link_type",
        "commission_rate",
        "commission_value",
        "commission_status",
        "linked_at",
    )
    readonly_fields = ("linked_at",)
    raw_id_fields = ("order",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("order")


class ContactLogInline(admin.TabularInline):
    model = EngineerContactLog
    extra = 0
    ordering = ["-contact_date"]
    fields = ("contact_type", "contact_date", "outcome", "next_followup_date", "created_by")
    readonly_fields = ("created_by",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("created_by")


class MaterialInterestInline(admin.TabularInline):
    model = EngineerMaterialInterest
    extra = 0
    fields = ("material_name", "interest_level", "request_count", "added_at")
    readonly_fields = ("added_at",)


@admin.register(DecoratorEngineerProfile)
class DecoratorEngineerProfileAdmin(admin.ModelAdmin):
    list_display = [
        "designer_code",
        "customer",
        "priority",
        "assigned_staff",
        "company_office_name",
        "city",
        "last_contact_date",
        "total_orders_count",
    ]
    list_filter = ("priority", "price_segment", "city")
    search_fields = (
        "customer__name",
        "customer__phone",
        "designer_code",
        "company_office_name",
        "city",
    )
    list_select_related = ("customer", "assigned_staff")
    raw_id_fields = ("customer", "assigned_staff")
    readonly_fields = ("designer_code", "created_at", "updated_at")
    list_per_page = 25
    show_full_result_count = False
    inlines = [
        LinkedCustomerInline,
        LinkedOrderInline,
        ContactLogInline,
        MaterialInterestInline,
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("customer", "assigned_staff")
        )
