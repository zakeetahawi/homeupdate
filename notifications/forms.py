from django import forms
from django.utils.translation import gettext_lazy as _
from .models import NotificationSettings, Notification


class NotificationSettingsForm(forms.ModelForm):
    """نموذج إعدادات الإشعارات"""
    
    class Meta:
        model = NotificationSettings
        fields = [
            'notifications_enabled',
            'customer_created_enabled',
            'order_created_enabled',
            'order_updated_enabled',
            'order_status_changed_enabled',
            'order_delivered_enabled',
            'installation_scheduled_enabled',
            'installation_completed_enabled',
            'inspection_created_enabled',
            'inspection_status_changed_enabled',
            'manufacturing_status_changed_enabled',
            'complaint_created_enabled',
            'min_priority_level',
        ]
        
        widgets = {
            'notifications_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'notifications_enabled'
            }),
            'customer_created_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'customer_created'
            }),
            'order_created_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'order_created'
            }),
            'order_updated_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'order_updated'
            }),
            'order_status_changed_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'order_status_changed'
            }),
            'order_delivered_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'order_delivered'
            }),
            'installation_scheduled_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'installation_scheduled'
            }),
            'installation_completed_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'installation_completed'
            }),
            'inspection_created_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'inspection_created'
            }),
            'inspection_status_changed_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'inspection_status_changed'
            }),
            'manufacturing_status_changed_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'manufacturing_status_changed'
            }),
            'complaint_created_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-type-checkbox',
                'data-type': 'complaint_created'
            }),
            'min_priority_level': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تخصيص التسميات
        self.fields['notifications_enabled'].label = _('تفعيل جميع الإشعارات')
        self.fields['notifications_enabled'].help_text = _('إلغاء تحديد هذا الخيار سيوقف جميع الإشعارات')
        
        # تجميع الحقول حسب الفئة
        self.customer_fields = ['customer_created_enabled']
        self.order_fields = [
            'order_created_enabled',
            'order_updated_enabled', 
            'order_status_changed_enabled',
            'order_delivered_enabled'
        ]
        self.inspection_fields = [
            'inspection_created_enabled',
            'inspection_status_changed_enabled'
        ]
        self.manufacturing_fields = ['manufacturing_status_changed_enabled']
        self.installation_fields = [
            'installation_scheduled_enabled',
            'installation_completed_enabled'
        ]
        self.complaint_fields = ['complaint_created_enabled']

    def get_field_groups(self):
        """الحصول على مجموعات الحقول للعرض في القالب"""
        return {
            'العملاء': {
                'icon': 'fas fa-users',
                'fields': self.customer_fields,
                'description': 'إشعارات متعلقة بالعملاء الجدد والتحديثات'
            },
            'الطلبات': {
                'icon': 'fas fa-shopping-cart',
                'fields': self.order_fields,
                'description': 'إشعارات الطلبات الجديدة وتحديثات الحالة'
            },
            'المعاينات': {
                'icon': 'fas fa-search',
                'fields': self.inspection_fields,
                'description': 'إشعارات المعاينات وتحديثات حالتها'
            },
            'التصنيع': {
                'icon': 'fas fa-industry',
                'fields': self.manufacturing_fields,
                'description': 'إشعارات أوامر التصنيع وتحديثات الحالة'
            },
            'التركيب': {
                'icon': 'fas fa-tools',
                'fields': self.installation_fields,
                'description': 'إشعارات جدولة وإكمال التركيبات'
            },
            'الشكاوى': {
                'icon': 'fas fa-exclamation-triangle',
                'fields': self.complaint_fields,
                'description': 'إشعارات الشكاوى الجديدة'
            }
        }


class BulkNotificationSettingsForm(forms.Form):
    """نموذج لتطبيق إعدادات الإشعارات على مجموعة من المستخدمين"""
    
    users = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        label=_('المستخدمون'),
        help_text=_('اختر المستخدمين لتطبيق الإعدادات عليهم')
    )
    
    action = forms.ChoiceField(
        choices=[
            ('enable_all', _('تفعيل جميع الإشعارات')),
            ('disable_all', _('إلغاء تفعيل جميع الإشعارات')),
            ('reset_to_default', _('إعادة تعيين للإعدادات الافتراضية')),
        ],
        widget=forms.RadioSelect,
        label=_('الإجراء')
    )
    
    def __init__(self, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        super().__init__(*args, **kwargs)
        self.fields['users'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')


class NotificationFilterForm(forms.Form):
    """نموذج تصفية الإشعارات"""
    
    notification_type = forms.ChoiceField(
        choices=[('', _('جميع الأنواع'))] + Notification.NOTIFICATION_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('نوع الإشعار')
    )
    
    priority = forms.ChoiceField(
        choices=[('', _('جميع الأولويات'))] + Notification.PRIORITY_LEVELS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('الأولوية')
    )
    
    is_read = forms.ChoiceField(
        choices=[
            ('', _('الكل')),
            ('true', _('مقروء')),
            ('false', _('غير مقروء'))
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('حالة القراءة')
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label=_('من تاريخ')
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label=_('إلى تاريخ')
    )
