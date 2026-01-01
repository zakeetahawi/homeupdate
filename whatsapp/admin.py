from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import (
    WhatsAppSettings,
    WhatsAppMessageTemplate,
    WhatsAppMessage,
    WhatsAppNotificationRule
)


@admin.register(WhatsAppSettings)
class WhatsAppSettingsAdmin(admin.ModelAdmin):
    """إدارة إعدادات WhatsApp"""
    
    list_display = [
        'api_provider',
        'phone_number',
        'is_active_badge',
        'test_mode_badge',
        'updated_at'
    ]
    
    fieldsets = (
        ('إعدادات API', {
            'fields': ('api_provider', 'phone_number', 'business_account_id', 
                      'phone_number_id', 'access_token')
        }),
        ('خيارات', {
            'fields': ('is_active', 'test_mode', 'use_template', 'enable_welcome_messages',
                      'retry_failed_messages', 'max_retry_attempts', 'default_language')
        }),
    )
    
    def get_urls(self):
        """إضافة URL لصفحة الاختبار"""
        urls = super().get_urls()
        custom_urls = [
            path('test-message/', self.admin_site.admin_view(self.test_message_view), name='whatsapp_test_message'),
        ]
        return custom_urls + urls
    
    def test_message_view(self, request):
        """صفحة إرسال رسالة اختبار"""
        from .forms import TestMessageForm
        from .services import WhatsAppService
        
        if request.method == 'POST':
            form = TestMessageForm(request.POST)
            if form.is_valid():
                phone = form.cleaned_data['phone_number']
                template = form.cleaned_data['template_name']
                
                try:
                    service = WhatsAppService()
                    
                    if template == 'hello_world':
                        result = service.send_template_message(
                            to=phone,
                            template_name='hello_world',
                            language='en_US'
                        )
                    else:
                        # order_confirmation مع بيانات تجريبية
                        result = service.send_template_message(
                            to=phone,
                            template_name='order_confirmation',
                            language='ar',
                            components=[
                                'عميل تجريبي',  # customer_name
                                'TEST-001',       # order_number
                                '2026-01-01',     # order_date
                                '1000',           # total_amount
                                '500',            # paid_amount
                                '500'             # remaining_amount
                            ]
                        )
                    
                    if result and result.get('messages'):
                        msg_id = result['messages'][0].get('id')
                        messages.success(request, f'✅ تم إرسال الرسالة بنجاح! Message ID: {msg_id}')
                    else:
                        messages.error(request, '❌ فشل إرسال الرسالة')
                        
                except Exception as e:
                    messages.error(request, f'❌ خطأ: {str(e)}')
                
                return HttpResponseRedirect(request.path)
        else:
            form = TestMessageForm()
        
        context = {
            'form': form,
            'title': 'اختبار إرسال رسالة WhatsApp',
            'site_title': 'إدارة الموقع',
            'site_header': 'إدارة الموقع',
            'has_permission': True,
        }
        
        return render(request, 'admin/whatsapp/test_message.html', context)
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span style="color: green;">✓ مفعل</span>')
        return mark_safe('<span style="color: red;">✗ معطل</span>')
    is_active_badge.short_description = 'الحالة'
    
    def test_mode_badge(self, obj):
        if obj.test_mode:
            return mark_safe('<span style="color: orange;">⚠ وضع الاختبار</span>')
        return mark_safe('<span style="color: green;">✓ إنتاج</span>')
    test_mode_badge.short_description = 'الوضع'
    
    def has_add_permission(self, request):
        # السماح بإنشاء سجل واحد فقط
        return not WhatsAppSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # منع الحذف
        return False


@admin.register(WhatsAppMessageTemplate)
class WhatsAppMessageTemplateAdmin(admin.ModelAdmin):
    """إدارة قوالب الرسائل"""
    
    list_display = [
        'name',
        'message_type',
        'is_active_badge',
        'send_contract_badge',
        'send_invoice_badge',
        'order_types_display',
        'updated_at'
    ]
    
    list_filter = [
        'message_type',
        'is_active',
        'send_contract',
        'send_invoice',
        'language'
    ]
    
    search_fields = ['name', 'template_text']
    
    fieldsets = (
        ('إعدادات القالب', {
            'fields': ('name', 'message_type', 'meta_template_name', 'language', 'is_active')
        }),
        ('نص الرسالة', {
            'fields': ('template_text',),
            'description': 'استخدم المتغيرات التالية: {customer_name}, {order_number}, {order_date}, {total_amount}, {paid_amount}, {remaining_amount}, {installation_date}, {technician_name}, {technician_phone}, {inspector_name}, {inspector_phone}'
        }),
        ('المرفقات', {
            'fields': ('send_contract', 'send_invoice')
        }),
        ('إعدادات إضافية', {
            'fields': ('order_types', 'delay_minutes'),
            'description': 'اترك order_types فارغاً لتطبيق القالب على جميع أنواع الطلبات'
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span style="color: green;">✓</span>')
        return mark_safe('<span style="color: red;">✗</span>')
    is_active_badge.short_description = 'مفعل'
    
    def send_contract_badge(self, obj):
        if obj.send_contract:
            return mark_safe('<span style="color: green;">✓</span>')
        return mark_safe('<span style="color: gray;">-</span>')
    send_contract_badge.short_description = 'عقد'
    
    def send_invoice_badge(self, obj):
        if obj.send_invoice:
            return mark_safe('<span style="color: green;">✓</span>')
        return mark_safe('<span style="color: gray;">-</span>')
    send_invoice_badge.short_description = 'فاتورة'
    
    def order_types_display(self, obj):
        if not obj.order_types:
            return 'الكل'
        return ', '.join(obj.order_types)
    order_types_display.short_description = 'أنواع الطلبات'


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    """إدارة سجل الرسائل مع إحصائيات"""

    
    list_display = [
        'id',
        'customer_link',
        'order_link',
        'message_type',
        'status_badge',
        'sent_at',
        'retry_count'
    ]
    
    list_filter = [
        'status',
        'message_type',
        'created_at',
        'sent_at'
    ]
    
    search_fields = [
        'customer__name',
        'customer__phone',
        'order__order_number',
        'message_text'
    ]
    
    readonly_fields = [
        'customer',
        'order',
        'installation',
        'inspection',
        'message_type',
        'template_used',
        'message_text',
        'phone_number',
        'external_id',
        'attachments',
        'sent_at',
        'delivered_at',
        'read_at',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('معلومات الرسالة', {
            'fields': ('customer', 'order', 'installation', 'inspection', 'message_type', 'template_used')
        }),
        ('المحتوى', {
            'fields': ('message_text', 'phone_number', 'attachments')
        }),
        ('الحالة', {
            'fields': ('status', 'external_id', 'error_message', 'retry_count')
        }),
        ('التواريخ', {
            'fields': ('sent_at', 'delivered_at', 'read_at', 'created_at', 'updated_at')
        }),
    )
    
    actions = ['retry_failed_messages']
    
    def customer_link(self, obj):
        if obj.customer:
            url = reverse('admin:customers_customer_change', args=[obj.customer.id])
            return format_html('<a href="{}">{}</a>', url, obj.customer.name)
        return '-'
    customer_link.short_description = 'العميل'
    
    def order_link(self, obj):
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return '-'
    order_link.short_description = 'الطلب'
    
    def status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'SENT': 'blue',
            'DELIVERED': 'green',
            'READ': 'darkgreen',
            'FAILED': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'الحالة'
    
    def retry_failed_messages(self, request, queryset):
        """إعادة محاولة إرسال الرسائل الفاشلة"""
        from .services import WhatsAppService
        
        service = WhatsAppService()
        success_count = 0
        
        for message in queryset.filter(status='FAILED'):
            if service.retry_failed_message(message.id):
                success_count += 1
        
        self.message_user(
            request,
            f'تم إعادة محاولة إرسال {success_count} رسالة بنجاح'
        )
    retry_failed_messages.short_description = 'إعادة محاولة الإرسال'
    
    def has_add_permission(self, request):
        # منع الإضافة اليدوية
        return False
    
    def has_delete_permission(self, request, obj=None):
        # السماح بالحذف فقط للمسؤولين
        return request.user.is_superuser
    
    def changelist_view(self, request, extra_context=None):
        """إضافة إحصائيات إلى صفحة القائمة"""
        extra_context = extra_context or {}
        
        # إحصائيات عامة
        total_messages = WhatsAppMessage.objects.count()
        
        # إحصائيات حسب الحالة
        stats_by_status = WhatsAppMessage.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # إحصائيات حسب النوع
        stats_by_type = WhatsAppMessage.objects.values('message_type').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # رسائل اليوم
        today = timezone.now().date()
        today_messages = WhatsAppMessage.objects.filter(
            created_at__date=today
        ).count()
        
        # رسائل الأسبوع
        week_ago = timezone.now() - timedelta(days=7)
        week_messages = WhatsAppMessage.objects.filter(
            created_at__gte=week_ago
        ).count()
        
        # معدل النجاح
        sent_count = WhatsAppMessage.objects.filter(status='SENT').count()
        failed_count = WhatsAppMessage.objects.filter(status='FAILED').count()
        success_rate = (sent_count / total_messages * 100) if total_messages > 0 else 0
        
        # معدل التسليم
        delivered_count = WhatsAppMessage.objects.filter(status='DELIVERED').count()
        delivery_rate = (delivered_count / sent_count * 100) if sent_count > 0 else 0
        
        # معدل القراءة
        read_count = WhatsAppMessage.objects.filter(status='READ').count()
        read_rate = (read_count / delivered_count * 100) if delivered_count > 0 else 0
        
        extra_context['statistics'] = {
            'total_messages': total_messages,
            'today_messages': today_messages,
            'week_messages': week_messages,
            'stats_by_status': list(stats_by_status),
            'stats_by_type': list(stats_by_type),
            'success_rate': round(success_rate, 1),
            'delivery_rate': round(delivery_rate, 1),
            'read_rate': round(read_rate, 1),
            'sent_count': sent_count,
            'failed_count': failed_count,
            'delivered_count': delivered_count,
            'read_count': read_count,
        }
        
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(WhatsAppNotificationRule)
class WhatsAppNotificationRuleAdmin(admin.ModelAdmin):
    """إدارة قواعد الإشعارات"""
    
    list_display = [
        'event_type',
        'is_enabled_badge',
        'template_link',
        'delay_minutes',
        'updated_at'
    ]
    
    list_filter = ['is_enabled', 'event_type']
    
    fieldsets = (
        ('معلومات القاعدة', {
            'fields': ('event_type', 'is_enabled')
        }),
        ('القالب', {
            'fields': ('template',)
        }),
        ('الإعدادات', {
            'fields': ('delay_minutes', 'conditions')
        }),
    )
    
    def is_enabled_badge(self, obj):
        if obj.is_enabled:
            return mark_safe('<span style="color: green;">✓ مفعل</span>')
        return mark_safe('<span style="color: red;">✗ معطل</span>')
    is_enabled_badge.short_description = 'الحالة'
    
    def template_link(self, obj):
        if obj.template:
            url = reverse('admin:whatsapp_whatsappmessagetemplate_change', args=[obj.template.id])
            return format_html('<a href="{}">{}</a>', url, obj.template.name)
        return '-'
    template_link.short_description = 'القالب'
