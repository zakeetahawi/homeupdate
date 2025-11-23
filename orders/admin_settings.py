"""
إدارة إعدادات النظام من لوحة التحكم
System Settings Admin Panel
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django import forms
from .models_settings import SystemSettings


class DynamicFieldInlineForm(forms.Form):
    """نموذج لإضافة/تعديل حقل ديناميكي"""
    value = forms.CharField(
        max_length=50,
        label='القيمة (بالإنجليزية)',
        help_text='القيمة المخزنة في قاعدة البيانات'
    )
    label = forms.CharField(
        max_length=100,
        label='التسمية (بالعربية)',
        help_text='النص المعروض للمستخدم'
    )


class SystemSettingsAdminForm(forms.ModelForm):
    """نموذج مخصص لإدارة الإعدادات"""
    
    # حقول إضافية لإدارة أنواع التفصيل
    new_tailoring_value = forms.CharField(
        max_length=50,
        required=False,
        label='قيمة نوع تفصيل جديد',
        help_text='القيمة بالإنجليزية (مثل: regular)'
    )
    new_tailoring_label = forms.CharField(
        max_length=100,
        required=False,
        label='تسمية نوع تفصيل جديد',
        help_text='التسمية بالعربية (مثل: عادي)'
    )
    
    # حقول إضافية لإدارة أنواع الأقمشة
    new_fabric_value = forms.CharField(
        max_length=50,
        required=False,
        label='قيمة نوع قماش جديد',
        help_text='القيمة بالإنجليزية (مثل: silk)'
    )
    new_fabric_label = forms.CharField(
        max_length=100,
        required=False,
        label='تسمية نوع قماش جديد',
        help_text='التسمية بالعربية (مثل: حرير)'
    )
    
    # حقول إضافية لإدارة أنواع التركيب
    new_installation_value = forms.CharField(
        max_length=50,
        required=False,
        label='قيمة نوع تركيب جديد',
        help_text='القيمة بالإنجليزية (مثل: track)'
    )
    new_installation_label = forms.CharField(
        max_length=100,
        required=False,
        label='تسمية نوع تركيب جديد',
        help_text='التسمية بالعربية (مثل: سكة)'
    )
    
    # حقول إضافية لإدارة طرق الدفع
    new_payment_value = forms.CharField(
        max_length=50,
        required=False,
        label='قيمة طريقة دفع جديدة',
        help_text='القيمة بالإنجليزية (مثل: online)'
    )
    new_payment_label = forms.CharField(
        max_length=100,
        required=False,
        label='تسمية طريقة دفع جديدة',
        help_text='التسمية بالعربية (مثل: دفع إلكتروني)'
    )
    
    class Meta:
        model = SystemSettings
        fields = '__all__'
        widgets = {
            'tailoring_types': forms.HiddenInput(),
            'fabric_types': forms.HiddenInput(),
            'installation_types': forms.HiddenInput(),
            'payment_methods': forms.HiddenInput(),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # إضافة نوع تفصيل جديد
        if self.cleaned_data.get('new_tailoring_value') and self.cleaned_data.get('new_tailoring_label'):
            if not instance.tailoring_types:
                instance.tailoring_types = []
            instance.tailoring_types.append({
                'value': self.cleaned_data['new_tailoring_value'],
                'label': self.cleaned_data['new_tailoring_label']
            })
        
        # إضافة نوع قماش جديد
        if self.cleaned_data.get('new_fabric_value') and self.cleaned_data.get('new_fabric_label'):
            if not instance.fabric_types:
                instance.fabric_types = []
            instance.fabric_types.append({
                'value': self.cleaned_data['new_fabric_value'],
                'label': self.cleaned_data['new_fabric_label']
            })
        
        # إضافة نوع تركيب جديد
        if self.cleaned_data.get('new_installation_value') and self.cleaned_data.get('new_installation_label'):
            if not instance.installation_types:
                instance.installation_types = []
            instance.installation_types.append({
                'value': self.cleaned_data['new_installation_value'],
                'label': self.cleaned_data['new_installation_label']
            })
        
        # إضافة طريقة دفع جديدة
        if self.cleaned_data.get('new_payment_value') and self.cleaned_data.get('new_payment_label'):
            if not instance.payment_methods:
                instance.payment_methods = []
            instance.payment_methods.append({
                'value': self.cleaned_data['new_payment_value'],
                'label': self.cleaned_data['new_payment_label']
            })
        
        if commit:
            instance.save()
        return instance


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات النظام"""
    form = SystemSettingsAdminForm
    
    # لا نعرض قائمة - Singleton Model
    def has_add_permission(self, request):
        # السماح بإضافة سجل واحد فقط
        return SystemSettings.objects.count() == 0
    
    def has_delete_permission(self, request, obj=None):
        # منع الحذف
        return False
    
    def changelist_view(self, request, extra_context=None):
        """إعادة توجيه إلى صفحة التعديل مباشرة"""
        settings = SystemSettings.get_settings()
        from django.shortcuts import redirect
        from django.urls import reverse
        return redirect(reverse('admin:orders_systemsettings_change', args=[settings.pk]))
    
    fieldsets = (
        (_('⚙️ إعدادات نظام الطلبات'), {
            'fields': (
                'order_system',
                'edit_priority',
                'hide_legacy_system',
                'hide_wizard_system',
                'allow_legacy_to_wizard_conversion',
            ),
            'description': format_html(
                '<div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px;">'
                '<h3 style="margin-top: 0; color: #1976d2;">🎯 التحكم في أنظمة إنشاء الطلبات</h3>'
                '<ul style="margin-bottom: 0;">'
                '<li><strong>نظام الويزارد:</strong> نظام متطور متعدد الخطوات لإنشاء الطلبات بدقة</li>'
                '<li><strong>النظام القديم:</strong> النظام التقليدي البسيط لإنشاء الطلبات</li>'
                '<li>يمكنك اختيار استخدام نظام واحد أو كلا النظامين معاً</li>'
                '</ul>'
                '</div>'
            )
        }),
        (_('📝 إدارة أنواع التفصيل'), {
            'fields': (
                'tailoring_types_display',
                'new_tailoring_value',
                'new_tailoring_label',
            ),
            'classes': ('collapse',),
            'description': 'إدارة أنواع التفصيل المتاحة في النظام'
        }),
        (_('🎨 إدارة أنواع الأقمشة'), {
            'fields': (
                'fabric_types_display',
                'new_fabric_value',
                'new_fabric_label',
            ),
            'classes': ('collapse',),
            'description': 'إدارة أنواع الأقمشة المتاحة في النظام'
        }),
        (_('🔧 إدارة أنواع التركيب'), {
            'fields': (
                'installation_types_display',
                'new_installation_value',
                'new_installation_label',
            ),
            'classes': ('collapse',),
            'description': 'إدارة أنواع التركيب المتاحة في النظام'
        }),
        (_('💰 إدارة طرق الدفع'), {
            'fields': (
                'payment_methods_display',
                'new_payment_value',
                'new_payment_label',
            ),
            'classes': ('collapse',),
            'description': 'إدارة طرق الدفع المتاحة في النظام'
        }),
        (_('📄 إعدادات العقود'), {
            'fields': (
                'require_contract_number',
                'require_contract_file',
            ),
            'classes': ('collapse',)
        }),
        (_('🔔 إعدادات الإشعارات'), {
            'fields': ('enable_wizard_notifications',),
            'classes': ('collapse',)
        }),
        (_('ℹ️ معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = (
        'created_at',
        'updated_at',
        'tailoring_types_display',
        'fabric_types_display',
        'installation_types_display',
        'payment_methods_display',
    )
    
    def tailoring_types_display(self, obj):
        """عرض أنواع التفصيل الحالية"""
        if not obj or not obj.tailoring_types:
            return format_html('<em>لا توجد أنواع تفصيل محددة</em>')
        
        html = '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<thead><tr style="background: #e0e0e0;"><th style="padding: 8px; text-align: right;">القيمة</th><th style="padding: 8px; text-align: right;">التسمية</th><th style="padding: 8px; text-align: center;">إجراءات</th></tr></thead>'
        html += '<tbody>'
        
        for idx, item in enumerate(obj.tailoring_types):
            html += f'<tr style="border-bottom: 1px solid #ddd;">'
            html += f'<td style="padding: 8px;"><code>{item.get("value", "")}</code></td>'
            html += f'<td style="padding: 8px;"><strong>{item.get("label", "")}</strong></td>'
            html += f'<td style="padding: 8px; text-align: center;">'
            html += f'<a href="javascript:void(0);" onclick="deleteTailoringType({idx})" style="color: #dc3545; text-decoration: none;">🗑️ حذف</a>'
            html += f'</td></tr>'
        
        html += '</tbody></table></div>'
        return format_html(html)
    tailoring_types_display.short_description = 'أنواع التفصيل الحالية'
    
    def fabric_types_display(self, obj):
        """عرض أنواع الأقمشة الحالية"""
        if not obj or not obj.fabric_types:
            return format_html('<em>لا توجد أنواع أقمشة محددة</em>')
        
        html = '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<thead><tr style="background: #e0e0e0;"><th style="padding: 8px; text-align: right;">القيمة</th><th style="padding: 8px; text-align: right;">التسمية</th><th style="padding: 8px; text-align: center;">إجراءات</th></tr></thead>'
        html += '<tbody>'
        
        for idx, item in enumerate(obj.fabric_types):
            html += f'<tr style="border-bottom: 1px solid #ddd;">'
            html += f'<td style="padding: 8px;"><code>{item.get("value", "")}</code></td>'
            html += f'<td style="padding: 8px;"><strong>{item.get("label", "")}</strong></td>'
            html += f'<td style="padding: 8px; text-align: center;">'
            html += f'<a href="javascript:void(0);" onclick="deleteFabricType({idx})" style="color: #dc3545; text-decoration: none;">🗑️ حذف</a>'
            html += f'</td></tr>'
        
        html += '</tbody></table></div>'
        return format_html(html)
    fabric_types_display.short_description = 'أنواع الأقمشة الحالية'
    
    def installation_types_display(self, obj):
        """عرض أنواع التركيب الحالية"""
        if not obj or not obj.installation_types:
            return format_html('<em>لا توجد أنواع تركيب محددة</em>')
        
        html = '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<thead><tr style="background: #e0e0e0;"><th style="padding: 8px; text-align: right;">القيمة</th><th style="padding: 8px; text-align: right;">التسمية</th><th style="padding: 8px; text-align: center;">إجراءات</th></tr></thead>'
        html += '<tbody>'
        
        for idx, item in enumerate(obj.installation_types):
            html += f'<tr style="border-bottom: 1px solid #ddd;">'
            html += f'<td style="padding: 8px;"><code>{item.get("value", "")}</code></td>'
            html += f'<td style="padding: 8px;"><strong>{item.get("label", "")}</strong></td>'
            html += f'<td style="padding: 8px; text-align: center;">'
            html += f'<a href="javascript:void(0);" onclick="deleteInstallationType({idx})" style="color: #dc3545; text-decoration: none;">🗑️ حذف</a>'
            html += f'</td></tr>'
        
        html += '</tbody></table></div>'
        return format_html(html)
    installation_types_display.short_description = 'أنواع التركيب الحالية'
    
    def payment_methods_display(self, obj):
        """عرض طرق الدفع الحالية"""
        if not obj or not obj.payment_methods:
            return format_html('<em>لا توجد طرق دفع محددة</em>')
        
        html = '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<thead><tr style="background: #e0e0e0;"><th style="padding: 8px; text-align: right;">القيمة</th><th style="padding: 8px; text-align: right;">التسمية</th><th style="padding: 8px; text-align: center;">إجراءات</th></tr></thead>'
        html += '<tbody>'
        
        for idx, item in enumerate(obj.payment_methods):
            html += f'<tr style="border-bottom: 1px solid #ddd;">'
            html += f'<td style="padding: 8px;"><code>{item.get("value", "")}</code></td>'
            html += f'<td style="padding: 8px;"><strong>{item.get("label", "")}</strong></td>'
            html += f'<td style="padding: 8px; text-align: center;">'
            html += f'<a href="javascript:void(0);" onclick="deletePaymentMethod({idx})" style="color: #dc3545; text-decoration: none;">🗑️ حذف</a>'
            html += f'</td></tr>'
        
        html += '</tbody></table></div>'
        return format_html(html)
    payment_methods_display.short_description = 'طرق الدفع الحالية'
    
    class Media:
        js = ('admin/js/system_settings.js',)
        css = {
            'all': ('admin/css/system_settings.css',)
        }
