from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # إرسال رسالة
    path('send/', views.send_message, name='send_message'),
    
    # الحصول على تاريخ المحادثة
    path('history/<str:username>/', views.get_chat_history, name='chat_history'),
    
    # عدد الرسائل غير المقروءة
    path('unread-count/', views.get_unread_messages_count, name='unread_count'),
    
    # تحديد الرسائل كمقروءة
    path('mark-read/', views.mark_messages_as_read, name='mark_read'),

    # الحصول على الرسائل الجديدة
    path('new-messages/', views.get_new_messages, name='new_messages'),
]
