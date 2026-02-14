from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "notifications"

# إعداد DRF Router
router = DefaultRouter()
router.register(r"api", views.NotificationViewSet, basename="notification-api")

urlpatterns = [
    # صفحات الويب
    path("", views.NotificationListView.as_view(), name="list"),
    path("<int:pk>/", views.NotificationDetailView.as_view(), name="detail"),
    path("mark-read/<int:pk>/", views.mark_notification_read, name="mark_read"),
    path("mark-all-read/", views.mark_all_notifications_read, name="mark_all_read"),
    path("ajax/count/", views.notification_count_ajax, name="ajax_count"),
    path("ajax/recent/", views.recent_notifications_ajax, name="ajax_recent"),
    path("ajax/popup/", views.popup_notifications_api, name="ajax_popup"),
    # API endpoints
    path("", include(router.urls)),
]
