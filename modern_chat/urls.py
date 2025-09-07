from django.urls import path
from . import views

app_name = 'modern_chat'

urlpatterns = [
    # إنشاء دردشة خاصة (API فقط)
    path('private/<int:user_id>/', views.create_private_chat, name='create_private'),

    # API endpoints
    path('api/send-message/', views.send_message, name='send_message'),
    path('api/messages/<uuid:room_id>/', views.get_messages, name='get_messages'),
    path('api/active-users/', views.get_active_users, name='active_users'),
    path('api/update-status/', views.update_user_status, name='update_status'),
    path('api/check-new-messages/', views.check_new_messages, name='check_new_messages'),
    path('api/user-rooms/', views.get_user_rooms, name='user_rooms'),
    path('api/user-info/<int:user_id>/', views.get_user_info, name='user_info'),
    path('api/mark-read/<uuid:room_id>/', views.mark_messages_read, name='mark_messages_read'),
]
