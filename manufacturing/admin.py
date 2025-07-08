from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import ManufacturingOrder, ManufacturingOrderItem
from django.utils.html import format_html
from django.contrib import messages

User = get_user_model()


class ManufacturingOrderItemInline(admin.TabularInline):
    model = ManufacturingOrderItem
    extra = 1
    fields = ('product_name', 'quantity', 'specifications', 'status')
    readonly_fields = ('status',)


@admin.register(ManufacturingOrder)
class ManufacturingOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order_link',
        'contract_number',
        'order_type_display',
        'status_display',
        'order_date',
        'expected_delivery_date',
        'exit_permit_number',
        'delivery_info',
        'created_at',
    )
    
    list_filter = (
        'status',
        'order_type',
        'order_date',
        'expected_delivery_date',
        'delivery_date',
    )
    
    search_fields = (
        'id',
        'order__id',
        'contract_number',
        'invoice_number',
        'exit_permit_number',
        'delivery_permit_number',
        'delivery_recipient_name',
    )
    
    readonly_fields = (
        'created_at', 'updated_at', 'completion_date', 'delivery_date'
    )
    inlines = [ManufacturingOrderItemInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('معلومات الطلب', {
            'fields': (
                'order',
                'contract_number',
                'invoice_number',
                'order_type',
                'status',
                'order_date',
                'expected_delivery_date',
                'exit_permit_number',
                'notes',
                'rejection_reason',
            )
        }),
        ('معلومات التسليم', {
            'fields': (
                'delivery_permit_number',
                'delivery_recipient_name',
                'delivery_date',
            ),
            'classes': ('collapse',),
        }),
        ('الملفات', {
            'fields': (
                'contract_file',
                'inspection_file',
            )
        }),
        ('التواريخ', {
            'fields': (
                'completion_date',
                'created_at',
                'updated_at',
            )
        }),
    )
    
    def order_link(self, obj):
        if obj.order:
            url = f'/admin/orders/order/{obj.order.id}/change/'
            return format_html(
                '<a href="{}">{}</a>', url, f'طلب #{obj.order.id}'
            )
        return "-"
    order_link.short_description = 'الطلب'
    
    def order_type_display(self, obj):
        return obj.get_order_type_display()
    order_type_display.short_description = 'نوع الطلب'
    
    def status_display(self, obj):
        colors = {
            'pending_approval': '#ffc107',
            'pending': '#17a2b8',
            'in_progress': '#007bff',
            'ready_for_installation': '#6f42c1',
            'completed': '#28a745',
            'delivered': '#20c997',
            'rejected': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'الحالة'
    
    def delivery_info(self, obj):
        if obj.status == 'delivered' and obj.delivery_permit_number:
            return format_html(
                '<strong>إذن:</strong> {}<br><strong>المستلم:</strong> {}',
                obj.delivery_permit_number,
                obj.delivery_recipient_name or '-'
            )
        return "-"
    delivery_info.short_description = 'معلومات التسليم'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'order__customer'
        )

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == 'pending_approval':
            # Only users with approval permission can change pending_approval
            return (request.user.has_perm('manufacturing.can_approve_orders') 
                    or request.user.is_superuser)
        return super().has_change_permission(request, obj)


# إضافة إدارة صلاحيات الموافقة للمستخدمين
class ManufacturingPermissionInline(admin.StackedInline):
    model = User.user_permissions.through
    extra = 0
    verbose_name = 'صلاحية الموافقة على التصنيع'
    verbose_name_plural = 'صلاحيات الموافقة على التصنيع'
    
    def get_queryset(self, request):
        # عرض فقط صلاحيات الموافقة على التصنيع
        content_type = ContentType.objects.get_for_model(ManufacturingOrder)
        manufacturing_permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=['can_approve_orders', 'can_reject_orders']
        )
        return super().get_queryset(request).filter(
            permission__in=manufacturing_permissions
        )


# إضافة قسم منفصل لإدارة صلاحيات الموافقة
# تم إزالة تسجيل Permission لتجنب التضارب مع admin المدمج


# إضافة إجراءات مخصصة للمستخدمين
def add_manufacturing_approval_permission(modeladmin, request, queryset):
    """إعطاء صلاحية الموافقة على التصنيع للمستخدمين المحددين"""
    content_type = ContentType.objects.get_for_model(ManufacturingOrder)
    approve_permission = Permission.objects.get(
        codename='can_approve_orders',
        content_type=content_type
    )
    reject_permission = Permission.objects.get(
        codename='can_reject_orders',
        content_type=content_type
    )
    
    count = 0
    for user in queryset:
        if not user.user_permissions.filter(id=approve_permission.id).exists():
            user.user_permissions.add(approve_permission, reject_permission)
            count += 1
    
    messages.success(
        request,
        f'تم إعطاء صلاحيات الموافقة على التصنيع لـ {count} مستخدم'
    )


add_manufacturing_approval_permission.short_description = (
    'إعطاء صلاحيات الموافقة على التصنيع'
)


def remove_manufacturing_approval_permission(modeladmin, request, queryset):
    """إزالة صلاحية الموافقة على التصنيع من المستخدمين المحددين"""
    content_type = ContentType.objects.get_for_model(ManufacturingOrder)
    approve_permission = Permission.objects.get(
        codename='can_approve_orders',
        content_type=content_type
    )
    reject_permission = Permission.objects.get(
        codename='can_reject_orders',
        content_type=content_type
    )
    
    count = 0
    for user in queryset:
        if user.user_permissions.filter(id=approve_permission.id).exists():
            user.user_permissions.remove(approve_permission, reject_permission)
            count += 1
    
    messages.success(
        request,
        f'تم إزالة صلاحيات الموافقة على التصنيع من {count} مستخدم'
    )


remove_manufacturing_approval_permission.short_description = (
    'إزالة صلاحيات الموافقة على التصنيع'
)


# تخصيص إدارة المستخدمين
class CustomUserAdmin(BaseUserAdmin):
    actions = [
        add_manufacturing_approval_permission,
        remove_manufacturing_approval_permission
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('user_permissions')
    
    def has_manufacturing_approval(self, obj):
        """عرض ما إذا كان المستخدم لديه صلاحية الموافقة على التصنيع"""
        content_type = ContentType.objects.get_for_model(ManufacturingOrder)
        return obj.user_permissions.filter(
            codename='can_approve_orders',
            content_type=content_type
        ).exists()
    
    has_manufacturing_approval.boolean = True
    has_manufacturing_approval.short_description = (
        'صلاحية الموافقة على التصنيع'
    )
    
    # إضافة العمود للقائمة
    list_display = BaseUserAdmin.list_display + (
        'has_manufacturing_approval',
    )


# إلغاء تسجيل المستخدم الافتراضي وإعادة تسجيله بالتخصيص الجديد
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
