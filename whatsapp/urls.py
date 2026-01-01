from django.urls import path
from . import views

app_name = 'whatsapp'

urlpatterns = [
    path('webhook/twilio/', views.twilio_webhook, name='twilio_webhook'),
    path('webhook/status/', views.twilio_status_callback, name='status_callback'),
    path('webhook/meta/', views.meta_webhook, name='meta_webhook'),
]
