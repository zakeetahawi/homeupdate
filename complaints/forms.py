from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import (
    Complaint, ComplaintType, ComplaintUpdate, ComplaintAttachment,
    ComplaintEscalation, ComplaintTemplate, ResolutionMethod
)
from customers.models import Customer
from orders.models import Order
from accounts.models import Department

User = get_user_model()


class ComplaintForm(forms.ModelForm):
    """نموذج إنشاء وتحديث الشكوى"""
    
    template = forms.ModelChoiceField(
        queryset=ComplaintTemplate.objects.filter(is_active=True),
        required=False,
        empty_label='اختر نموذجاً (اختياري)',
        label='نموذج جاهز',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': 'اختر نموذجاً جاهزاً'
        })
    )
    
    # حقول التعيين والمسؤولية
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='إسناد إلى',
        required=False,
        empty_label='اختر الموظف المختص',
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
        
        # تحديث قائمة النماذج بناءً على نوع الشكوى
        if 'complaint_type' in self.data:
            try:
                complaint_type_id = int(self.data.get('complaint_type'))
                self.fields['template'].queryset = ComplaintTemplate.objects.filter(
                    complaint_type_id=complaint_type_id,
                    is_active=True
                )
            except (ValueError, TypeError):
                self.fields['template'].queryset = ComplaintTemplate.objects.none()
        
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

        # إضافة JavaScript لتحديث قائمة الموظفين بناءً على نوع الشكوى والقسم
        self.fields['complaint_type'].widget.attrs.update({
            'onchange': 'updateResponsibleStaff(this.value)'
        })
        self.fields['assigned_department'].widget.attrs.update({
            'onchange': 'updateStaffByDepartment(this.value)'
        })
        
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
            # Set the customer in the hidden field
            self.fields['customer'].initial = self.customer.pk
            # Update orders queryset for the current customer
            self.fields['related_order'].queryset = Order.objects.filter(
                customer=self.customer
            ).order_by('-created_at')
            # Make customer search field readonly when customer is pre-selected
            self.fields['customer_search'].widget.attrs['readonly'] = True
            self.fields['customer_search'].widget.attrs['class'] += ' bg-light'
        else:
            self.fields['customer_search'].initial = ''
            self.fields['related_order'].queryset = Order.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        errors = {}

        try:
            # استخدام النموذج إذا تم اختياره
            template = cleaned_data.get('template')
            if template:
                customer = cleaned_data.get('customer')
                related_order = cleaned_data.get('related_order')

                try:
                    # تعبئة العنوان والوصف من النموذج
                    cleaned_data['title'] = template.generate_title(
                        customer=customer,
                        order=related_order
                    )
                    cleaned_data['description'] = template.generate_description(
                        customer=customer,
                        order=related_order
                    )

                    # تعيين الأولوية والموعد النهائي من النموذج
                    cleaned_data['priority'] = template.priority
                    if not cleaned_data.get('deadline'):
                        cleaned_data['deadline'] = timezone.now() + timedelta(
                            hours=template.default_deadline_hours
                        )
                except Exception as e:
                    errors['template'] = f'خطأ في تطبيق النموذج: {str(e)}'

            # التحقق من العميل
            customer = cleaned_data.get('customer')
            if not customer:
                errors['customer'] = 'يجب اختيار عميل'
            else:
                # التحقق من نشاط العميل
                if hasattr(customer, 'is_active') and not customer.is_active:
                    errors['customer'] = 'هذا العميل غير نشط حالياً'

                # التحقق من وجود عقد ساري للعميل (إذا كان مطلوباً)
                try:
                    if hasattr(customer, 'has_active_contract') and not customer.has_active_contract():
                        errors['customer'] = 'لا يوجد عقد ساري لهذا العميل'
                except Exception:
                    # تجاهل الخطأ إذا كانت الطريقة غير متوفرة
                    pass

            # التحقق من الطلب المرتبط
            related_order = cleaned_data.get('related_order')
            if related_order and customer:
                if related_order.customer != customer:
                    errors['related_order'] = 'الطلب المحدد لا ينتمي للعميل المختار'

                # التحقق من حالة الطلب
                if hasattr(related_order, 'status') and related_order.status in ['cancelled', 'rejected']:
                    errors['related_order'] = 'لا يمكن ربط شكوى بطلب ملغي أو مرفوض'

        except Exception as e:
            errors['__all__'] = f'حدث خطأ في التحقق من البيانات: {str(e)}'

        if errors:
            raise forms.ValidationError(errors)

        # تحديث قائمة الطلبات
        if customer and customer != self.customer:
            self.customer = customer
            self.update_related_order_queryset()
        
        # التحقق من الموعد النهائي
        deadline = cleaned_data.get('deadline')
        if deadline:
            if deadline < timezone.now():
                raise forms.ValidationError({
                    'deadline': 'لا يمكن تحديد موعد نهائي في الماضي'
                })
            
            complaint_type = cleaned_data.get('complaint_type')
            if complaint_type and complaint_type.default_deadline_hours:
                max_deadline = timezone.now() + timedelta(hours=complaint_type.default_deadline_hours * 2)
                if deadline > max_deadline:
                    raise forms.ValidationError({
                        'deadline': f'الموعد النهائي يتجاوز الحد المسموح به ({complaint_type.default_deadline_hours * 2} ساعة)'
                    })
        
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
    
    class Meta:
        model = ComplaintUpdate
        fields = ['update_type', 'title', 'description', 'is_visible_to_customer']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'عنوان التحديث'}),
            'description': forms.Textarea(attrs={
                'placeholder': 'تفاصيل التحديث (إجباري)',
                'rows': 4
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # جعل الوصف إجباري
        self.fields['description'].required = True
        self.fields['description'].help_text = 'يجب إضافة تفاصيل التحديث'

        # إضافة CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.widgets.Input):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.widgets.Textarea):
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['rows'] = 4
            elif isinstance(field.widget, forms.widgets.Select):
                field.widget.attrs['class'] = 'form-select'


class ComplaintStatusUpdateForm(forms.ModelForm):
    """نموذج تحديث حالة الشكوى"""
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=True,
        label='ملاحظات التحديث',
        help_text='ملاحظات إضافية حول تغيير الحالة (إجباري)'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # فلترة الموظفين النشطين فقط (جميع المستخدمين النشطين)
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name')
        self.fields['assigned_to'].required = False

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
        fields = ['status', 'assigned_to', 'assigned_department']


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
        
        # فلترة الموظفين النشطين فقط (جميع المستخدمين النشطين)
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name')
        
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


from django.db.models import Q

class ComplaintEscalationForm(forms.ModelForm):
    """نموذج تصعيد الشكوى"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # فلترة الموظفين المسموح لهم باستلام التصعيدات
        eligible_users = User.objects.filter(
            is_active=True,
            is_staff=True
        ).filter(
            Q(complaint_permissions__is_active=True, 
              complaint_permissions__can_receive_escalations=True) |
            Q(is_superuser=True) |
            Q(groups__name__in=['Complaints_Managers', 'Complaints_Supervisors'])
        ).distinct()
        
        self.fields['escalated_to'].queryset = eligible_users
        
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

    resolution_method = forms.ModelChoiceField(
        queryset=ResolutionMethod.objects.filter(is_active=True),
        required=True,
        label='طريقة الحل',
        help_text='اختر طريقة الحل المناسبة',
        empty_label='اختر طريقة الحل...'
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
        fields = ['status', 'resolution_method']
        
    def save(self, commit=True):
        complaint = super().save(commit=False)
        complaint.status = 'resolved'
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
    """نموذج فلترة الشكاوى المحسن مع دعم single selection"""

    status = forms.ChoiceField(
        choices=[('', 'جميع الحالات')] + list(Complaint.STATUS_CHOICES),
        required=False,
        label='الحالة',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': 'اختر الحالة...'
        })
    )
    priority = forms.ChoiceField(
        choices=[('', 'جميع الأولويات')] + list(Complaint.PRIORITY_CHOICES),
        required=False,
        label='الأولوية',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': 'اختر الأولوية...'
        })
    )
    complaint_type = forms.ModelChoiceField(
        queryset=ComplaintType.objects.filter(is_active=True),
        required=False,
        empty_label='جميع الأنواع',
        label='نوع الشكوى',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': 'اختر النوع...'
        })
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        required=False,
        empty_label='جميع الموظفين',
        label='المسؤول',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': 'اختر الموظف...'
        })
    )
    assigned_department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label='جميع الأقسام',
        label='القسم',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-placeholder': 'اختر القسم...'
        })
    )
    date_from = forms.DateField(
        required=False,
        label='من تاريخ',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        label='إلى تاريخ',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    search = forms.CharField(
        required=False,
        label='البحث',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ابحث في رقم الشكوى، العميل، العنوان، أو الوصف...'
        })
    )

    def clean(self):
        """تنظيف وتحقق من صحة البيانات"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')

        # التحقق من صحة التواريخ
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')

        return cleaned_data


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
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'last_name'),
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
