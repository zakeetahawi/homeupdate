from django.urls import path

from . import views

app_name = "whatsapp"

urlpatterns = [
    path("webhook/meta/", views.meta_webhook, name="meta_webhook"),
]
