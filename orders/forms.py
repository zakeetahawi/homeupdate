from django import forms

from .models import Payment


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "payment_method", "reference_number", "notes"]
        labels = {
            "reference_number": "رقم الفاتورة",
        }
        widgets = {
            "amount": forms.NumberInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "payment_method": forms.Select(
                attrs={"class": "form-select form-select-sm"}
            ),
            "reference_number": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 2}
            ),
        }
