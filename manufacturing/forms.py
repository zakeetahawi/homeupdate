"""
Forms for Manufacturing App
"""

from django import forms
from django.forms import inlineformset_factory
from .models import ManufacturingOrder, ManufacturingOrderItem

class ManufacturingOrderForm(forms.ModelForm):
    """Form for Manufacturing Order"""
    
    class Meta:
        model = ManufacturingOrder
        fields = [
            'order', 'order_type', 'contract_number', 'invoice_number',
            'order_date', 'expected_delivery_date', 'notes',
            'contract_file', 'inspection_file'
        ]
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class ManufacturingOrderItemForm(forms.ModelForm):
    """Form for Manufacturing Order Item"""
    
    class Meta:
        model = ManufacturingOrderItem
        fields = ['product_name', 'quantity', 'specifications']
        widgets = {
            'specifications': forms.Textarea(attrs={'rows': 3}),
        }

# Inline formset for manufacturing order items
ManufacturingItemFormSet = inlineformset_factory(
    ManufacturingOrder,
    ManufacturingOrderItem,
    form=ManufacturingOrderItemForm,
    extra=1,
    can_delete=True,
    fields=['product_name', 'quantity', 'specifications']
) 