"""
Forms for ProductSet management
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import BaseProduct, ProductSet, ProductSetItem


class ProductSetForm(forms.ModelForm):
    """Form لإنشاء/تعديل ProductSet"""

    selected_products = forms.ModelMultipleChoiceField(
        queryset=BaseProduct.objects.filter(is_active=True).select_related(
            "category"
        ),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="المنتجات",
        help_text="اختر 2-5 منتجات",
    )

    class Meta:
        model = ProductSet
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "مثل: طقم كلاسيكي"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "وصف اختياري للمجموعة",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # في حالة التعديل، إظهار المنتجات المحددة
            self.fields["selected_products"].initial = self.instance.base_products.all()

    def clean_selected_products(self):
        products = self.cleaned_data.get("selected_products")
        if products:
            count = len(products)
            if count < 2:
                raise ValidationError("يجب اختيار منتجين على الأقل")
            if count > 5:
                raise ValidationError("لا يمكن اختيار أكثر من 5 منتجات")
        return products

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            # حذف المنتجات القديمة
            instance.productsetitem_set.all().delete()
            # إضافة المنتجات الجديدة
            products = self.cleaned_data["selected_products"]
            for i, product in enumerate(products, start=1):
                ProductSetItem.objects.create(
                    product_set=instance, base_product=product, display_order=i
                )
            instance.cloudflare_synced = False  # تحديث حالة المزامنة
            instance.save(update_fields=["cloudflare_synced"])
        return instance
