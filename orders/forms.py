import json
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Order, OrderItem, Payment
from accounts.models import Salesperson, Branch
from django.utils import timezone
from datetime import timedelta
from inspections.models import Inspection

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'unit_price', 'item_type', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'item_type': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'reference_number', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'payment_method': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
        }

# Formset for managing multiple order items
OrderItemFormSet = forms.inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True,
)

class OrderForm(forms.ModelForm):
    # Override status choices to match requirements
    STATUS_CHOICES = [
        ('normal', 'عادي'),
        ('vip', 'VIP'),
    ]
    
    # Override order type choices to match requirements
    ORDER_TYPE_CHOICES = [
        ('product', 'منتج'),
        ('service', 'خدمة'),
    ]
    
    # Override status field to use our custom choices
    status = forms.ChoiceField(
        choices=Order.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False
    )

    # This is the correct field definition for the order types.
    selected_types = forms.ChoiceField(
        choices=Order.ORDER_TYPES,
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    salesperson = forms.ModelChoiceField(
        queryset=Salesperson.objects.filter(is_active=True),
        label='البائع',
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    # The following hidden fields were causing the issue by redefining 'selected_types'.
    # This has been removed.
    
    # Hidden fields for delivery
    delivery_type = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    delivery_address = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )

    # حقل المعاينة المرتبطة للخدمات الأخرى
    related_inspection = forms.ChoiceField(
        choices=[
            ('customer_side', 'طرف العميل'),
            ('', 'اختر العميل أولاً')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm',
            'data-placeholder': 'اختر المعاينة المرتبطة'
        }),
        label='معاينة مرتبطة',
        help_text='اختر المعاينة المرتبطة بهذا الطلب (اختياري)'
    )

    class Meta:
        model = Order
        fields = [
            'customer', 'status', 'invoice_number',
            'contract_number', 'contract_file', 'branch', 'tracking_status',
            'notes', 'selected_types', 'delivery_type', 'delivery_address', 'salesperson'
        ]
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-select form-select-sm',
                'data-placeholder': 'اختر العميل'
            }),
            'tracking_status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'branch': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'contract_file': forms.FileInput(attrs={
                'class': 'form-control form-control-sm',
                'accept': '.pdf',
                'data-help': 'يجب أن يكون الملف من نوع PDF وأقل من 10 ميجابايت'
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control notes-field', 'rows': 6}),
            'delivery_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'expected_delivery_date': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date',
                'readonly': True
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)
        
        # تقييد البائعين حسب الفرع إذا لم يكن المستخدم مديراً
        if user and not user.is_superuser and user.branch:
            self.fields['salesperson'].queryset = Salesperson.objects.filter(
                is_active=True,
                branch=user.branch
            )
        
        # تقييد العملاء حسب دور المستخدم والفرع
        if user:
            from customers.models import Customer
            
            if user.is_superuser:
                # المدير العام يرى جميع العملاء
                customer_queryset = Customer.objects.filter(status='active')
            elif user.is_region_manager:
                # مدير المنطقة يرى عملاء الفروع التي يديرها
                managed_branches = user.managed_branches.all()
                customer_queryset = Customer.objects.filter(
                    status='active',
                    branch__in=managed_branches
                )
            elif user.is_branch_manager or user.is_salesperson:
                # مدير الفرع والبائع يرون عملاء فرعهم فقط
                if user.branch:
                    customer_queryset = Customer.objects.filter(
                        status='active',
                        branch=user.branch
                    )
                else:
                    customer_queryset = Customer.objects.none()
            else:
                # المستخدمون الآخرون لا يرون أي عملاء
                customer_queryset = Customer.objects.none()
            
            self.fields['customer'].queryset = customer_queryset.order_by('name')
        
        # تعيين خيارات المعاينة المرتبطة للخدمات الأخرى
        if customer:
            # إضافة خيار "طرف العميل" في بداية القائمة
            inspection_choices = [('customer_side', 'طرف العميل')]
            
            # إضافة معاينات العميل كروابط
            for inspection in Inspection.objects.filter(customer=customer).order_by('-created_at'):
                # استخدام معرف المعاينة كقيمة
                inspection_choices.append((
                    str(inspection.id), 
                    f"{inspection.customer.name if inspection.customer else 'عميل غير محدد'} - {inspection.contract_number or f'معاينة {inspection.id}'} - {inspection.created_at.strftime('%Y-%m-%d')}"
                ))
            
            self.fields['related_inspection'].choices = inspection_choices
        else:
            # إذا لم يتم تحديد عميل، إظهار رسالة فقط بدون أي معاينات
            self.fields['related_inspection'].choices = [
                ('', 'اختر العميل أولاً')
            ]
        
        # Make all fields optional initially
        for field_name in self.fields:
            self.fields[field_name].required = False
            
        # Make order_number read-only but visible
        if 'order_number' in self.fields:
            self.fields['order_number'].widget.attrs['readonly'] = True
            self.fields['order_number'].widget.attrs['class'] = 'form-control form-control-sm'
        else:
            # Add order_number field if it doesn't exist
            self.fields['order_number'] = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-control form-control-sm',
                    'readonly': True,
                    'placeholder': 'سيتم إنشاؤه تلقائياً'
                }),
                label='رقم الطلب'
            )
        
        # Make invoice_number and contract_number not required initially
        self.fields['invoice_number'].required = False
        self.fields['contract_number'].required = False
        
        # Set branch to user's branch if available
        if user and hasattr(user, 'branch') and user.branch:
            self.fields['branch'].initial = user.branch
            # If not superuser, limit branch choices to user's branch
            if not user.is_superuser:
                self.fields['branch'].queryset = Branch.objects.filter(id=user.branch.id)
                self.fields['branch'].widget.attrs['readonly'] = True

    def clean_related_inspection(self):
        """تنظيف حقل المعاينة المرتبطة"""
        value = self.cleaned_data.get('related_inspection')
        
        if value == 'customer_side':
            return 'customer_side'
        elif value and value != '':
            try:
                # التحقق من وجود المعاينة في قاعدة البيانات
                inspection = Inspection.objects.get(id=value)
                return str(inspection.id)
            except (Inspection.DoesNotExist, ValueError):
                raise forms.ValidationError('معاينة غير صحيحة')
        else:
            return value

    def clean(self):
        cleaned_data = super().clean()
        selected_type = cleaned_data.get('selected_types')

        # إضافة رسائل تصحيح
        print(f"DEBUG: selected_type = {selected_type}")
        print(f"DEBUG: selected_type type = {type(selected_type)}")
        print(f"DEBUG: all cleaned_data keys = {list(cleaned_data.keys())}")

        # Required fields validation
        required_fields = ['customer', 'salesperson', 'branch']
        for field in required_fields:
            if not cleaned_data.get(field):
                self.add_error(field, f'هذا الحقل مطلوب')

        if not selected_type:
            self.add_error('selected_types', 'يجب اختيار نوع للطلب')
            return cleaned_data # Return early if no type is selected

        # التحقق من رقم الفاتورة لجميع أنواع الطلبات
        print(f"DEBUG: checking invoice_number for type: {selected_type}")
        invoice_number = cleaned_data.get('invoice_number')
        print(f"DEBUG: invoice_number = {invoice_number}")
        if not invoice_number or not invoice_number.strip():
            print(f"DEBUG: invoice_number validation failed")
            self.add_error('invoice_number', 'رقم الفاتورة مطلوب لجميع أنواع الطلبات')

        # التحقق من رقم العقد وملف العقد للتركيب والتفصيل والإكسسوار
        contract_required_types = ['installation', 'tailoring', 'accessory']
        if selected_type in contract_required_types:
            contract_number = cleaned_data.get('contract_number')
            if not contract_number or not contract_number.strip():
                self.add_error('contract_number', 'رقم العقد مطلوب لهذا النوع من الطلبات')

            # contract_file is an in-memory file object, so we check for it directly
            if 'contract_file' not in self.files:
                self.add_error('contract_file', 'ملف العقد مطلوب لهذا النوع من الطلبات')

        # التحقق من المعاينة المرتبطة للخدمات الأخرى (غير المعاينة) فقط
        if selected_type != 'inspection':
            related_inspection_value = cleaned_data.get('related_inspection')
            print(f"DEBUG: related_inspection_value = {related_inspection_value}")
            if related_inspection_value and related_inspection_value != 'customer_side':
                try:
                    # التحقق من أن القيمة رقم صحيح
                    inspection_id = int(related_inspection_value)
                    inspection = Inspection.objects.get(id=inspection_id)
                    print(f"DEBUG: Found inspection with ID {inspection_id}")
                except (ValueError, Inspection.DoesNotExist):
                    print(f"DEBUG: Invalid inspection ID: {related_inspection_value}")
                    self.add_error('related_inspection', 'معاينة غير صحيحة')
        else:
            # للمعاينات: إفراغ قيمة المعاينة المرتبطة
            cleaned_data['related_inspection'] = ''

        print(f"DEBUG: form validation completed")
        return cleaned_data

    def save(self, commit=True):
        # Get cleaned values before the instance is saved
        selected_type = self.cleaned_data.get('selected_types')
        status = self.cleaned_data.get('status')

        # Create the instance but don't commit to DB yet
        instance = super().save(commit=False)
        
        # تعيين وضع الطلب تلقائياً للمعاينة
        if selected_type == 'inspection':
            instance.status = 'normal'  # تعيين وضع الطلب تلقائياً إلى "عادي" للمعاينة
            status = 'normal'  # تحديث المتغير للاستخدام في الحسابات
        
        # --- Calculate and set Expected Delivery Date using the new system ---
        # تحديد نوع الطلب للحصول على عدد الأيام المناسب
        order_type = 'vip' if status == 'vip' else 'normal'
        
        # التحقق من وجود معاينة في الطلب
        if selected_type == 'inspection':
            order_type = 'inspection'
        
        # الحصول على عدد الأيام من الإعدادات
        from orders.models import DeliveryTimeSettings
        days_to_add = DeliveryTimeSettings.get_delivery_days(order_type)
        
        # حساب التاريخ المتوقع
        instance.expected_delivery_date = timezone.now().date() + timedelta(days=days_to_add)

        # Now, modify the instance with the other transformed data
        if selected_type:
            # Save selected_types as JSON
            instance.selected_types = json.dumps([selected_type])

            # Set order_type for compatibility
            if selected_type in ['accessory']:
                instance.order_type = 'product'
            else:
                instance.order_type = 'service'

            # Set delivery options automatically
            if selected_type == 'tailoring':
                instance.delivery_type = 'branch'
                instance.delivery_address = ''
            elif selected_type == 'installation':
                instance.delivery_type = 'home'
                if not instance.delivery_address:
                    instance.delivery_address = 'سيتم تحديد العنوان لاحقاً'
            else:  # accessory and inspection
                instance.delivery_type = 'branch'
                instance.delivery_address = ''

            # معالجة related_inspection للخدمات الأخرى (غير المعاينة)
            if selected_type != 'inspection':
                related_inspection_value = self.cleaned_data.get('related_inspection')
                if related_inspection_value == 'customer_side':
                    instance.related_inspection = None
                    instance.related_inspection_type = 'customer_side'
                elif related_inspection_value and related_inspection_value != '':
                    try:
                        inspection = Inspection.objects.get(id=related_inspection_value)
                        instance.related_inspection = inspection
                        instance.related_inspection_type = 'inspection'
                    except (Inspection.DoesNotExist, ValueError):
                        # إذا لم يتم العثور على المعاينة، تعيين كطرف العميل
                        instance.related_inspection = None
                        instance.related_inspection_type = 'customer_side'
                else:
                    # إذا لم يتم اختيار معاينة، تعيين كطرف العميل
                    instance.related_inspection = None
                    instance.related_inspection_type = 'customer_side'
            else:
                # للمعاينات: لا توجد معاينة مرتبطة
                instance.related_inspection = None
                instance.related_inspection_type = None

        if commit:
            instance.save()
            self.save_m2m()  # Important for inline formsets if any
        
        return instance
