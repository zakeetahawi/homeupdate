from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path

from .models import WhatsAppMessageTemplate, WhatsAppSettings
from .services import WhatsAppService


class TestMessageForm(forms.Form):
    """نموذج إرسال رسالة اختبار"""

    phone_number = forms.CharField(
        label="رقم الهاتف",
        max_length=15,
        help_text="مثال: 01119238775",
        widget=forms.TextInput(attrs={"placeholder": "01119238775"}),
    )
    template_name = forms.ChoiceField(
        label="القالب",
        choices=[],  # Will be populated dynamically
        help_text="القوالب المعتمدة من Meta تظهر بعلامة ✅",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load templates dynamically from database
        choices = [("hello_world", "Hello World (معتمد ✅)")]  # Default Meta template

        templates = WhatsAppMessageTemplate.objects.filter(is_active=True)
        for template in templates:
            if template.meta_template_name:
                # Has Meta template name - approved
                label = f"{template.name} ({template.meta_template_name}) ✅"
            else:
                # No Meta template name - not approved
                label = f"{template.name} ❌ غير معتمد"
            choices.append((template.meta_template_name or f"db_{template.id}", label))

        self.fields["template_name"].choices = choices

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"]
        # إزالة المسافات والرموز
        phone = phone.replace(" ", "").replace("-", "").replace("+", "")

        # التحقق من أنه رقم
        if not phone.isdigit():
            raise forms.ValidationError("رقم الهاتف يجب أن يحتوي على أرقام فقط")

        # التحقق من الطول
        if len(phone) < 10 or len(phone) > 15:
            raise forms.ValidationError("رقم الهاتف غير صحيح")

        return phone
