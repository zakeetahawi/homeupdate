from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    Complaint, ComplaintType, ComplaintUpdate, ComplaintAttachment,
    ComplaintEscalation
)
from customers.models import Customer
from orders.models import Order
from accounts.models import Department

User = get_user_model()


class ComplaintForm(forms.ModelForm):
    """نموذج إنشاء وتحديث الشكوى"""
    
    # حقول التعيين والمسؤولية
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='الموظف المسؤول',
        required=False,
        empty_label='اختر الموظف المسؤول',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    related_order = forms.ModelChoiceField(
        queryset=Order.objects.none(),
        label='الطلب المرتبط',
        required=False,
        empty_label='اختر الطلب المرتبط',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-live-search': 'true'
        })
    )
    
    assigned_department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        label='القسم المختص',
        required=False,
        empty_label='اختر القسم المختص',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    branch = forms.ModelChoiceField(
        queryset=None,
        label='الفرع',
        required=False,
        empty_label='اختر الفرع',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)
        
        # إخفاء حقل العميل الأصلي واستخدام البحث الذكي
        self.fields['customer'].widget = forms.HiddenInput()
        
        # Add customer_search field for display
        self.fields['customer_search'] = forms.CharField(
            label='بحث العميل',
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ابحث عن عميل...',
                'autocomplete': 'off'
            })
        )
        
        # تحديث قائمة الطلبات بناءً على العميل المحدد
        self.update_related_order_queryset()
        
        # تحديد أنواع الشكاوى النشطة
        self.fields['complaint_type'].queryset = ComplaintType.objects.filter(
            is_active=True
        ).order_by('name')
        
        # تحديث queryset للموظفين النشطين (جميع الموظفين)
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name')
        
        # تحديث queryset للفروع
        try:
            from accounts.models import Branch
            self.fields['branch'].queryset = Branch.objects.filter(
                is_active=True
            ).order_by('name')
        except ImportError:
            self.fields['branch'].queryset = None
        
        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['rows'] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs['class'] = 'form-select'
    
    def update_related_order_queryset(self):
        """Update customer search field and related orders queryset"""
        if hasattr(self, 'customer') and self.customer:
            customer_info = f"{self.customer.name} - {self.customer.phone}"
            self.fields['customer_search'].initial = customer_info
            # Update orders queryset for the current customer
            self.fields['related_order'].queryset = Order.objects.filter(
                customer=self.customer
            ).order_by('-created_at')
        else:
            self.fields['customer_search'].initial = ''
            self.fields['related_order'].queryset = Order.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # تحديث قائمة الطلبات بناءً على العميل المحدد
        customer = cleaned_data.get('customer')
        if customer and customer != self.customer:
            self.customer = customer
            self.update_related_order_queryset()
        
        return cleaned_data
    
    class Meta:
        model = Complaint
        fields = [
            'customer', 'complaint_type', 'title', 'description',
            'related_order', 'priority', 'deadline', 'assigned_to',
            'assigned_department', 'branch'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'اكتب موضوع الشكوى'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'اكتب وصف مفصل للشكوى',
                'rows': 4
            }),
            'deadline': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            })
        }
    
    def clean_related_order(self):
        """
        التحقق من صحة الطلب المرتبط بالشكوى مع إضافة سجلات تصحيح
        """
        print("\n===== بدء التحقق من صحة الطلب المرتبط =====")
        related_order = self.cleaned_data.get('related_order')
        print(f"قيمة الطلب المستلمة: {related_order} (نوع: {type(related_order)})")
        
        # إذا لم يتم اختيار طلب، نرجع None
        if not related_order:
            print("لم يتم اختيار طلب - العودة بقيمة None")
            return None
            
        # الحصول على معرف الطلب سواء كان كائن Order أو معرف رقمي
        order_id = related_order.id if hasattr(related_order, 'id') else related_order
        print(f"معرف الطلب المستخرج: {order_id} (نوع: {type(order_id)})")
        
        # إذا كان الطلب رقم، نحاول الحصول على كائن الطلب
        if isinstance(order_id, (int, str)) and str(order_id).isdigit():
            print(f"البحث عن الطلب بالمعرف: {order_id}")
            try:
                related_order = Order.objects.get(pk=order_id)
                print(f"تم العثور على الطلب: {related_order}")
                # تحديث القيمة في cleaned_data
                self.cleaned_data['related_order'] = related_order
            except Order.DoesNotExist:
                error_msg = f'الطلب المحدد غير موجود (ID: {order_id})'
                print(error_msg)
                raise forms.ValidationError(error_msg)
        
        # الحصول على العميل من البيانات المدخلة أو من النموذج
        customer = self.cleaned_data.get('customer')
        if not customer and hasattr(self, 'customer'):
            customer = self.customer
            
        print(f"العميل المستخدم للتحقق: {customer} (نوع: {type(customer) if customer else 'None'})")
        
        # إذا كان هناك عميل محدد، نتحقق من أن الطلب يخصه
        if customer and hasattr(related_order, 'customer'):
            print(f"مقارنة: معرف عميل الطلب: {related_order.customer_id} - معرف العميل المحدد: {customer.id}")
            if related_order.customer_id != customer.id:
                error_msg = (
                    f'الطلب المحدد لا ينتمي إلى العميل الحالي. '
                    f'(معرف طلب العميل: {related_order.customer_id}, '
                    f'معرف العميل الحالي: {customer.id})'
                )
                print(error_msg)
                raise forms.ValidationError(error_msg)
        
        print("التحقق من صحة الطلب اكتمل بنجاح")
        return related_order
    
    def save(self, commit=True):
        complaint = super().save(commit=False)
        
        if self.request:
            complaint.created_by = self.request.user
            if hasattr(self.request.user, 'branch'):
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
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['rows'] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs['class'] = 'form-select'
    
    class Meta:
        model = ComplaintUpdate
        fields = ['update_type', 'title', 'description', 'is_visible_to_customer']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'عنوان التحديث'}),
            'description': forms.Textarea(attrs={
                'placeholder': 'تفاصيل التحديث',
                'rows': 4
            })
        }


class ComplaintStatusUpdateForm(forms.ModelForm):
    """نموذج تحديث حالة الشكوى"""
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label='ملاحظات التحديث',
        help_text='ملاحظات إضافية حول تغيير الحالة'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['rows'] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs['class'] = 'form-select'
    
    class Meta:
        model = Complaint
        fields = ['status']


class ComplaintAssignmentForm(forms.ModelForm):
    """نموذج تعيين الشكوى"""
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label='ملاحظات التعيين',
        help_text='ملاحظات إضافية حول تعيين الشكوى'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # فلترة الموظفين النشطين فقط
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True,
            is_staff=True
        )
        
        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['rows'] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs['class'] = 'form-select'
    
    class Meta:
        model = Complaint
        fields = ['assigned_to', 'assigned_department']


class ComplaintEscalationForm(forms.ModelForm):
    """نموذج تصعيد الشكوى"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # فلترة الموظفين النشطين فقط
        self.fields['escalated_to'].queryset = User.objects.filter(
            is_active=True,
            is_staff=True
        )
        
        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['rows'] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs['class'] = 'form-select'
    
    class Meta:
        model = ComplaintEscalation
        fields = ['escalated_to', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4})
        }


class ComplaintAttachmentForm(forms.ModelForm):
    """نموذج إضافة مرفق للشكوى"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['rows'] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs['class'] = 'form-select'
    
    class Meta:
        model = ComplaintAttachment
        fields = ['file', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3})
        }


class ComplaintResolutionForm(forms.ModelForm):
    """نموذج حل الشكوى"""
    
    resolution_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=True,
        label='ملاحظات الحل',
        help_text='اشرح كيف تم حل الشكوى'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['rows'] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs['class'] = 'form-select'
    
    class Meta:
        model = Complaint
        fields = ['status']
        
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
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['rows'] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs['class'] = 'form-select'
    
    class Meta:
        model = Complaint
        fields = ['customer_rating', 'customer_feedback']
        widgets = {
            'customer_rating': forms.Select(choices=Complaint.RATING_CHOICES),
            'customer_feedback': forms.Textarea(attrs={'rows': 4})
        }


class ComplaintFilterForm(forms.Form):
    """نموذج فلترة الشكاوى"""
    
    status = forms.ChoiceField(
        choices=[('', 'جميع الحالات')] + Complaint.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    priority = forms.ChoiceField(
        choices=[('', 'جميع الأولويات')] + Complaint.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    complaint_type = forms.ModelChoiceField(
        queryset=ComplaintType.objects.filter(is_active=True),
        required=False,
        empty_label='جميع الأنواع',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, is_staff=True),
        required=False,
        empty_label='جميع الموظفين',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class ComplaintBulkActionForm(forms.Form):
    """نموذج الإجراءات المجمعة للشكاوى"""
    
    ACTION_CHOICES = [
        ('assign', 'تعيين موظف'),
        ('change_status', 'تغيير الحالة'),
        ('change_priority', 'تغيير الأولوية'),
        ('assign_department', 'تعيين قسم'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, is_staff=True),
        required=False,
        empty_label='اختر الموظف',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=Complaint.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    priority = forms.ChoiceField(
        choices=Complaint.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    assigned_department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label='اختر القسم',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'assign' and not cleaned_data.get('assigned_to'):
            raise forms.ValidationError('يجب اختيار موظف للتعيين')
        elif action == 'change_status' and not cleaned_data.get('status'):
            raise forms.ValidationError('يجب اختيار حالة جديدة')
        elif action == 'change_priority' and not cleaned_data.get('priority'):
            raise forms.ValidationError('يجب اختيار أولوية جديدة')
        elif action == 'assign_department' and not cleaned_data.get('assigned_department'):
            raise forms.ValidationError('يجب اختيار قسم للتعيين')
        
        return cleaned_data
