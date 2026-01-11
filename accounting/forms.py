"""
نماذج النظام المحاسبي
Accounting Forms
"""

from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from .models import (
    Account,
    AccountingSettings,
    CustomerAdvance,
    Transaction,
    TransactionLine,
)


class AccountForm(forms.ModelForm):
    """
    نموذج الحساب
    """

    class Meta:
        model = Account
        fields = [
            "code",
            "name",
            "name_en",
            "account_type",
            "parent",
            "description",
            "branch",
            "is_active",
            "opening_balance",
        ]
        widgets = {
            "code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "كود الحساب"}
            ),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "اسم الحساب بالعربية"}
            ),
            "name_en": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account Name in English",
                }
            ),
            "account_type": forms.Select(attrs={"class": "form-control"}),
            "parent": forms.Select(attrs={"class": "form-control select2"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "branch": forms.Select(attrs={"class": "form-control"}),
            "opening_balance": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TransactionForm(forms.ModelForm):
    """
    نموذج القيد المحاسبي
    """

    class Meta:
        model = Transaction
        fields = ["date", "transaction_type", "description", "reference"]
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "transaction_type": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 2, "placeholder": "وصف القيد"}
            ),
            "reference": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "رقم المرجع"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial["date"] = timezone.now().date()


class TransactionLineForm(forms.ModelForm):
    """
    نموذج سطر القيد
    """

    class Meta:
        model = TransactionLine
        fields = ["account", "debit", "credit", "description"]
        widgets = {
            "account": forms.Select(attrs={"class": "form-control select2-account"}),
            "debit": forms.NumberInput(
                attrs={
                    "class": "form-control debit-input",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),
            "credit": forms.NumberInput(
                attrs={
                    "class": "form-control credit-input",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),
            "description": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "البيان"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        debit = cleaned_data.get("debit", Decimal("0")) or Decimal("0")
        credit = cleaned_data.get("credit", Decimal("0")) or Decimal("0")

        if debit > 0 and credit > 0:
            raise forms.ValidationError("لا يمكن أن يكون السطر مدين ودائن في نفس الوقت")

        if debit == 0 and credit == 0:
            raise forms.ValidationError("يجب تحديد مبلغ مدين أو دائن")

        return cleaned_data


# Formset لسطور القيد
TransactionLineFormSet = inlineformset_factory(
    Transaction,
    TransactionLine,
    form=TransactionLineForm,
    extra=2,
    min_num=2,
    validate_min=True,
    can_delete=True,
)


class CustomerAdvanceForm(forms.ModelForm):
    """
    نموذج عربون العميل
    """

    class Meta:
        model = CustomerAdvance
        fields = [
            "customer",
            "amount",
            "payment_method",
            "receipt_number",
            "notes",
            "branch",
        ]
        widgets = {
            "customer": forms.Select(attrs={"class": "form-control select2"}),
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "مبلغ العربون",
                }
            ),
            "payment_method": forms.Select(attrs={"class": "form-control"}),
            "receipt_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "رقم الإيصال"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2, "placeholder": "ملاحظات"}
            ),
            "branch": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop("customer", None)
        super().__init__(*args, **kwargs)

        if self.customer:
            self.fields["customer"].initial = self.customer
            self.fields["customer"].widget = forms.HiddenInput()


class AdvanceUsageForm(forms.Form):
    """
    نموذج استخدام العربون
    """

    order = forms.IntegerField(
        label="رقم الطلب", widget=forms.Select(attrs={"class": "form-control select2"})
    )
    amount = forms.DecimalField(
        label="المبلغ المستخدم",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=forms.NumberInput(
            attrs={"class": "form-control", "step": "0.01", "placeholder": "المبلغ"}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.advance = kwargs.pop("advance", None)
        super().__init__(*args, **kwargs)

        if self.advance:
            # تحديد الحد الأقصى للمبلغ
            self.fields["amount"].max_value = self.advance.remaining_amount
            self.fields["amount"].widget.attrs["max"] = str(
                self.advance.remaining_amount
            )


class QuickPaymentForm(forms.Form):
    """
    نموذج دفعة سريعة من صفحة العميل
    """

    order = forms.IntegerField(
        label="الطلب",
        required=False,
        widget=forms.Select(attrs={"class": "form-control select2"}),
    )
    amount = forms.DecimalField(
        label="المبلغ",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "مبلغ الدفعة",
            }
        ),
    )
    payment_method = forms.ChoiceField(
        label="طريقة الدفع",
        choices=[
            ("cash", "نقداً"),
            ("bank_transfer", "تحويل بنكي"),
            ("card", "بطاقة"),
            ("cheque", "شيك"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    payment_date = forms.DateField(
        label="تاريخ الدفع",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    receipt_number = forms.CharField(
        label="رقم الإيصال",
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "رقم الإيصال"}
        ),
    )
    notes = forms.CharField(
        label="ملاحظات",
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 2, "placeholder": "ملاحظات"}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop("customer", None)
        super().__init__(*args, **kwargs)
        self.initial["payment_date"] = timezone.now().date()


class QuickAdvanceForm(forms.Form):
    """
    نموذج عربون سريع من صفحة العميل
    """

    amount = forms.DecimalField(
        label="المبلغ",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "مبلغ السلفة",
            }
        ),
    )
    payment_method = forms.ChoiceField(
        label="طريقة الدفع",
        choices=[
            ("cash", "نقداً"),
            ("bank_transfer", "تحويل بنكي"),
            ("check", "شيك"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    receipt_number = forms.CharField(
        label="رقم الإيصال",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "رقم الإيصال"}
        ),
    )
    notes = forms.CharField(
        label="ملاحظات",
        required=False,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 2, "placeholder": "ملاحظات"}
        ),
    )

    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop("customer", None)
        super().__init__(*args, **kwargs)


class DateRangeFilterForm(forms.Form):
    """
    نموذج فلترة بالتاريخ
    """

    start_date = forms.DateField(
        label="من تاريخ",
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    end_date = forms.DateField(
        label="إلى تاريخ",
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")

        if start and end and start > end:
            raise forms.ValidationError("تاريخ البداية يجب أن يكون قبل تاريخ النهاية")

        return cleaned_data


class AccountingSettingsForm(forms.ModelForm):
    """
    نموذج إعدادات النظام المحاسبي
    """

    class Meta:
        model = AccountingSettings
        fields = [
            "fiscal_year_start",
            "default_cash_account",
            "default_bank_account",
            "default_receivables_account",
            "default_revenue_account",
            "default_advances_account",
            "auto_post_transactions",
            "require_transaction_approval",
        ]
        widgets = {
            "fiscal_year_start": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "default_cash_account": forms.Select(
                attrs={"class": "form-control select2"}
            ),
            "default_bank_account": forms.Select(
                attrs={"class": "form-control select2"}
            ),
            "default_receivables_account": forms.Select(
                attrs={"class": "form-control select2"}
            ),
            "default_revenue_account": forms.Select(
                attrs={"class": "form-control select2"}
            ),
            "default_advances_account": forms.Select(
                attrs={"class": "form-control select2"}
            ),
            "auto_post_transactions": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "require_transaction_approval": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
