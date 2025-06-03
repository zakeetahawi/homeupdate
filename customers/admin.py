from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Customer, CustomerCategory, CustomerNote, CustomerType

@admin.register(CustomerCategory)
class CustomerCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']

@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    list_display = ['customer', 'note_preview', 'created_by', 'created_at']
    list_filter = ['created_at', 'created_by']
    search_fields = ['customer__name', 'note', 'created_by__username']
    readonly_fields = ['created_by', 'created_at']

    def note_preview(self, obj):
        return obj.note[:50] + '...' if len(obj.note) > 50 else obj.note
    note_preview.short_description = _('الملاحظة')

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(CustomerType)
class CustomerTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at']
    ordering = ['name']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'customer_image', 'name', 'customer_type',
        'branch', 'phone', 'status', 'category'
    ]
    list_filter = [
        'status', 'customer_type', 'category',
        'branch', 'created_at'
    ]
    search_fields = [
        'code', 'name', 'phone', 'email',
        'notes', 'category__name'
    ]
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': (
                'code', 'name', 'image', 'customer_type',
                'category', 'status'
            )
        }),
        (_('معلومات الاتصال'), {
            'fields': ('phone', 'email', 'address')
        }),
        (_('معلومات الفرع'), {
            'fields': ('branch', 'notes')
        }),
        (_('معلومات النظام'), {
            'classes': ('collapse',),
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    def customer_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%;" />',
                obj.image.url
            )
        return '-'
    customer_image.short_description = _('الصورة')

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('css/admin-extra.css',)
        }
