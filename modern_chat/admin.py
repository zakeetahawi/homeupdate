from django.contrib import admin
from .models import ChatRoom, Message, MessageRead, UserStatus


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'room_type', 'created_by', 'created_at', 'is_active']
    list_filter = ['room_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    filter_horizontal = ['participants']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'room_type', 'description', 'is_active')
        }),
        ('المشاركون', {
            'fields': ('created_by', 'participants')
        }),
        ('معلومات النظام', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'room', 'message_type', 'content_preview', 'created_at', 'is_deleted']
    list_filter = ['message_type', 'is_deleted', 'is_edited', 'created_at']
    search_fields = ['content', 'sender__username', 'room__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'معاينة المحتوى'
    
    fieldsets = (
        ('معلومات الرسالة', {
            'fields': ('room', 'sender', 'message_type', 'content')
        }),
        ('ملفات ومرفقات', {
            'fields': ('file', 'reply_to')
        }),
        ('حالة الرسالة', {
            'fields': ('is_edited', 'is_deleted')
        }),
        ('معلومات النظام', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MessageRead)
class MessageReadAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'read_at']
    list_filter = ['read_at']
    search_fields = ['user__username', 'message__content']
    readonly_fields = ['read_at']


@admin.register(UserStatus)
class UserStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'last_seen', 'is_typing_in']
    list_filter = ['status', 'last_seen']
    search_fields = ['user__username']
    readonly_fields = ['last_seen']
