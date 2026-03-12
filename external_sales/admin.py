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


class ContactLogInline(admin.TabularInline):
    model = EngineerContactLog
    extra = 0
    ordering = ["-contact_date"]
    fields = ("contact_type", "contact_date", "outcome", "next_followup_date", "created_by")
    readonly_fields = ("created_by",)


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
    readonly_fields = ("designer_code", "created_at", "updated_at")
    inlines = [
        LinkedCustomerInline,
        LinkedOrderInline,
        ContactLogInline,
        MaterialInterestInline,
    ]
