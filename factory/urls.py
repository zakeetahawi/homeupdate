from django.urls import path
from . import views

app_name = 'factory'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]
