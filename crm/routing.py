from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path

# Define an empty list for WebSocket URL patterns
# This will be populated when the new installations app is created
websocket_urlpatterns = []

application = ProtocolTypeRouter({
    'websocket': URLRouter(
        websocket_urlpatterns
    )
})
