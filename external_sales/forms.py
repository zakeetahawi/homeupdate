from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    DecoratorEngineerProfile,
    EngineerContactLog,
    EngineerLinkedCustomer,
    EngineerLinkedOrder,
    EngineerMaterialInterest,
)


class DecoratorEngineerProfileForm(forms.ModelForm):
    class Meta:
        model = DecoratorEngineerProfile
        fields = [
            "customer",
            "company_office_name",
            "years_of_experience",
            "area_of_operation",
            "city",
            "instagram_handle",
            "portfolio_url",
            "linkedin_url",
            "price_segment",
            "design_style",
            "preferred_colors",
            "project_types",
            "interests_notes",
            "internal_notes",
            "priority",
            "assigned_staff",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-control select2"}),
            "company_office_name": forms.TextInput(attrs={"class": "form-control"}),
            "years_of_experience": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "area_of_operation": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "instagram_handle": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "portfolio_url": forms.URLInput(attrs={"class": "form-control", "dir": "ltr"}),
            "linkedin_url": forms.URLInput(attrs={"class": "form-control", "dir": "ltr"}),
            "price_segment": forms.Select(attrs={"class": "form-select"}),
            "design_style": forms.TextInput(attrs={"class": "form-control"}),
            "preferred_colors": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "interests_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "internal_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "assigned_staff": forms.Select(attrs={"class": "form-control select2"}),
        }


class EngineerProfileEditForm(forms.ModelForm):
    """Edit form — excludes customer (cannot change once created)"""

    class Meta:
        model = DecoratorEngineerProfile
        fields = [
            "company_office_name",
            "years_of_experience",
            "area_of_operation",
            "city",
            "instagram_handle",
            "portfolio_url",
            "linkedin_url",
            "price_segment",
            "design_style",
            "preferred_colors",
            "project_types",
            "interests_notes",
            "internal_notes",
            "priority",
            "assigned_staff",
        ]
        widgets = {
            "company_office_name": forms.TextInput(attrs={"class": "form-control"}),
            "years_of_experience": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "area_of_operation": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "instagram_handle": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "portfolio_url": forms.URLInput(attrs={"class": "form-control", "dir": "ltr"}),
            "linkedin_url": forms.URLInput(attrs={"class": "form-control", "dir": "ltr"}),
            "price_segment": forms.Select(attrs={"class": "form-select"}),
            "design_style": forms.TextInput(attrs={"class": "form-control"}),
            "preferred_colors": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "interests_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "internal_notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "assigned_staff": forms.Select(attrs={"class": "form-control select2"}),
        }


class ContactLogForm(forms.ModelForm):
    class Meta:
        model = EngineerContactLog
        fields = [
            "contact_type",
            "contact_date",
            "outcome",
            "notes",
            "next_followup_date",
            "next_followup_notes",
            "appointment_datetime",
            "appointment_location",
        ]
        widgets = {
            "contact_type": forms.Select(attrs={"class": "form-select"}),
            "contact_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "outcome": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "next_followup_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "next_followup_notes": forms.TextInput(attrs={"class": "form-control"}),
            "appointment_datetime": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "appointment_location": forms.TextInput(attrs={"class": "form-control"}),
        }


class LinkCustomerForm(forms.ModelForm):
    class Meta:
        model = EngineerLinkedCustomer
        fields = [
            "customer",
            "relationship_type",
            "notes",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-control"}),
            "relationship_type": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = self.fields["customer"].queryset.none()
        if self.data.get("customer"):
            from customers.models import Customer

            try:
                self.fields["customer"].queryset = Customer.objects.filter(
                    pk=int(self.data["customer"])
                )
            except (ValueError, TypeError):
                pass


class LinkOrderForm(forms.ModelForm):
    class Meta:
        model = EngineerLinkedOrder
        fields = [
            "order",
            "commission_type",
            "commission_rate",
            "commission_value",
            "notes",
        ]
        widgets = {
            "order": forms.Select(attrs={"class": "form-control"}),
            "commission_type": forms.Select(attrs={"class": "form-select"}),
            "commission_rate": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0", "max": "100"}
            ),
            "commission_value": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["order"].queryset = self.fields["order"].queryset.none()
        if self.data.get("order"):
            from orders.models import Order

            try:
                self.fields["order"].queryset = Order.objects.filter(
                    pk=int(self.data["order"])
                )
            except (ValueError, TypeError):
                pass


class MaterialInterestForm(forms.ModelForm):
    class Meta:
        model = EngineerMaterialInterest
        fields = [
            "material_name",
            "inventory_category",
            "interest_level",
            "request_count",
            "notes",
        ]
        widgets = {
            "material_name": forms.TextInput(attrs={"class": "form-control"}),
            "inventory_category": forms.Select(attrs={"class": "form-control select2"}),
            "interest_level": forms.Select(attrs={"class": "form-select"}),
            "request_count": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class EngineerExcelImportForm(forms.Form):
    file = forms.FileField(
        label=_("ملف Excel"),
        help_text=_("يجب أن يكون ملف .xlsx بنفس تنسيق القالب"),
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".xlsx"}),
    )
