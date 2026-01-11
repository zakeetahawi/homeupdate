from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import Department
from customers.models import Customer
from orders.models import Order

from .models import (
    Complaint,
    ComplaintAttachment,
    ComplaintEscalation,
    ComplaintType,
    ComplaintUpdate,
)

User = get_user_model()


class ComplaintForm(forms.ModelForm):
    """نموذج إنشاء وتحديث الشكوى"""

    # حقل البحث الذكي للعميل
    customer_search = forms.CharField(
        label="البحث عن العميل",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "ابحث بالاسم أو الهاتف أو الإيميل...",
                "autocomplete": "off",
            }
        ),
    )

    # حقول التعيين والمسؤولية
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="الموظف المسؤول",
        required=False,
        empty_label="اختر الموظف المسؤول",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    assigned_department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        label="القسم المختص",
        required=False,
        empty_label="اختر القسم المختص",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    branch = forms.ModelChoiceField(
        queryset=None,
        label="الفرع",
        required=False,
        empty_label="اختر الفرع",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.customer = kwargs.pop("customer", None)
        super().__init__(*args, **kwargs)

        # إخفاء حقل العميل الأصلي واستخدام البحث الذكي
        self.fields["customer"].widget = forms.HiddenInput()

        # تحديد الطلبات المرتبطة بالعميل
        if self.customer:
            self.fields["related_order"].queryset = Order.objects.filter(
                customer=self.customer
            ).order_by("-created_at")
            self.fields["customer"].initial = self.customer
            customer_info = f"{self.customer.name} - {self.customer.phone}"
            self.fields["customer_search"].initial = customer_info
        else:
            # إذا لم يتم تحديد عميل، أظهر قائمة فارغة للطلبات
            self.fields["related_order"].queryset = Order.objects.none()

        # تحديد أنواع الشكاوى النشطة
        self.fields["complaint_type"].queryset = ComplaintType.objects.filter(
            is_active=True
        ).order_by("name")

        # تحديث queryset للموظفين النشطين
        self.fields["assigned_to"].queryset = User.objects.filter(
            is_active=True, is_staff=True
        ).order_by("first_name", "last_name")

        # تحديث queryset للفروع
        try:
            from accounts.models import Branch

            self.fields["branch"].queryset = Branch.objects.filter(
                is_active=True
            ).order_by("name")
        except ImportError:
            self.fields["branch"].queryset = None

        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs["class"] = "form-control"
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["rows"] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs["class"] = "form-select"

    class Meta:
        model = Complaint
        fields = [
            "customer",
            "complaint_type",
            "title",
            "description",
            "related_order",
            "priority",
            "assigned_to",
            "assigned_department",
            "branch",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "اكتب موضوع الشكوى"}),
            "description": forms.Textarea(
                attrs={"placeholder": "اكتب وصف مفصل للشكوى", "rows": 4}
            ),
        }

    def save(self, commit=True):
        complaint = super().save(commit=False)

        if self.request:
            complaint.created_by = self.request.user
            if hasattr(self.request.user, "branch"):
                complaint.branch = self.request.user.branch

        if commit:
            complaint.save()

        return complaint


class ComplaintUpdateForm(forms.ModelForm):
    """نموذج إضافة تحديث للشكوى"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs["class"] = "form-control"
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["rows"] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs["class"] = "form-select"

    class Meta:
        model = ComplaintUpdate
        fields = ["update_type", "title", "description", "is_visible_to_customer"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "عنوان التحديث"}),
            "description": forms.Textarea(
                attrs={"placeholder": "تفاصيل التحديث", "rows": 4}
            ),
        }


class ComplaintStatusUpdateForm(forms.ModelForm):
    """نموذج تحديث حالة الشكوى"""

    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="ملاحظات التحديث",
        help_text="ملاحظات إضافية حول تغيير الحالة",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs["class"] = "form-control"
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["rows"] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs["class"] = "form-select"

    class Meta:
        model = Complaint
        fields = ["status"]


class ComplaintAssignmentForm(forms.ModelForm):
    """نموذج تعيين الشكوى"""

    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="ملاحظات التعيين",
        help_text="ملاحظات إضافية حول تعيين الشكوى",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # فلترة الموظفين النشطين فقط
        self.fields["assigned_to"].queryset = User.objects.filter(
            is_active=True, is_staff=True
        )

        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs["class"] = "form-control"
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["rows"] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs["class"] = "form-select"

    class Meta:
        model = Complaint
        fields = ["assigned_to", "assigned_department"]


class ComplaintEscalationForm(forms.ModelForm):
    """نموذج تصعيد الشكوى"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # فلترة الموظفين النشطين فقط
        self.fields["escalated_to"].queryset = User.objects.filter(
            is_active=True, is_staff=True
        )

        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs["class"] = "form-control"
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["rows"] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs["class"] = "form-select"

    class Meta:
        model = ComplaintEscalation
        fields = ["escalated_to", "reason", "urgency_level"]
        widgets = {"reason": forms.Textarea(attrs={"rows": 4})}


class ComplaintAttachmentForm(forms.ModelForm):
    """نموذج إضافة مرفق للشكوى"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs["class"] = "form-control"
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["rows"] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs["class"] = "form-select"

    class Meta:
        model = ComplaintAttachment
        fields = ["title", "file", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class ComplaintResolutionForm(forms.ModelForm):
    """نموذج حل الشكوى"""

    resolution_notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        required=True,
        label="ملاحظات الحل",
        help_text="اشرح كيف تم حل الشكوى",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs["class"] = "form-control"
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["rows"] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs["class"] = "form-select"

    class Meta:
        model = Complaint
        fields = ["status"]

    def save(self, commit=True):
        complaint = super().save(commit=False)
        complaint.resolved_at = timezone.now()

        if commit:
            complaint.save()

        return complaint


class ComplaintCustomerRatingForm(forms.ModelForm):
    """نموذج تقييم العميل للشكوى"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs["class"] = "form-control"
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs["class"] = "form-control"
                field.widget.attrs["rows"] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs["class"] = "form-select"

    class Meta:
        model = Complaint
        fields = ["customer_rating", "customer_feedback"]
        widgets = {
            "customer_rating": forms.Select(choices=Complaint.RATING_CHOICES),
            "customer_feedback": forms.Textarea(attrs={"rows": 4}),
        }


class ComplaintFilterForm(forms.Form):
    """نموذج فلترة الشكاوى"""

    status = forms.ChoiceField(
        choices=[("", "جميع الحالات")] + Complaint.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    priority = forms.ChoiceField(
        choices=[("", "جميع الأولويات")] + Complaint.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    complaint_type = forms.ModelChoiceField(
        queryset=ComplaintType.objects.filter(is_active=True),
        required=False,
        empty_label="جميع الأنواع",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, is_staff=True),
        required=False,
        empty_label="جميع الموظفين",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )


class ComplaintBulkActionForm(forms.Form):
    """نموذج الإجراءات المجمعة للشكاوى"""

    ACTION_CHOICES = [
        ("assign", "تعيين موظف"),
        ("change_status", "تغيير الحالة"),
        ("change_priority", "تغيير الأولوية"),
        ("assign_department", "تعيين قسم"),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES, widget=forms.Select(attrs={"class": "form-select"})
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, is_staff=True),
        required=False,
        empty_label="اختر الموظف",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    status = forms.ChoiceField(
        choices=Complaint.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    priority = forms.ChoiceField(
        choices=Complaint.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    assigned_department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="اختر القسم",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")

        if action == "assign" and not cleaned_data.get("assigned_to"):
            raise forms.ValidationError("يجب اختيار موظف للتعيين")
        elif action == "change_status" and not cleaned_data.get("status"):
            raise forms.ValidationError("يجب اختيار حالة جديدة")
        elif action == "change_priority" and not cleaned_data.get("priority"):
            raise forms.ValidationError("يجب اختيار أولوية جديدة")
        elif action == "assign_department" and not cleaned_data.get(
            "assigned_department"
        ):
            raise forms.ValidationError("يجب اختيار قسم للتعيين")

        return cleaned_data
