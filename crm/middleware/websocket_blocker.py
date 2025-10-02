"""
Middleware لحظر طلبات WebSocket والدردشة
"""

import logging

from django.http import HttpResponseGone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("websocket_blocker")


class BlockWebSocketMiddleware(MiddlewareMixin):
    """
    Middleware لحظر جميع طلبات WebSocket والدردشة
    """

    def process_request(self, request):
        """
        فحص الطلبات وحظر طلبات WebSocket
        """
        path = request.path.lower()

        # قائمة المسارات المحظورة
        blocked_paths = [
            "/ws/",
            "/websocket/",
            "/chat/",
            "/socket.io/",
            "/ws/chat/",
            "/chat/general/",
            "/ws/chat/general/",
        ]

        # فحص إذا كان المسار محظور
        for blocked_path in blocked_paths:
            if blocked_path in path:
                # تسجيل معلومات الطلب
                user_agent = request.META.get("HTTP_USER_AGENT", "Unknown")
                referer = request.META.get("HTTP_REFERER", "No referer")
                remote_addr = request.META.get("REMOTE_ADDR", "Unknown IP")

                logger.warning(
                    f"🚫 Blocked WebSocket request: {path} - "
                    f"IP: {remote_addr}, "
                    f"User-Agent: {user_agent[:50]}..., "
                    f"Referer: {referer}"
                )

                # إرجاع 410 Gone مع headers قوية
                response = HttpResponseGone(
                    "WebSocket and chat services have been permanently removed. "
                    "Please clear your browser cache and disable any chat-related extensions."
                )
                response["Cache-Control"] = (
                    "no-cache, no-store, must-revalidate, max-age=0"
                )
                response["Pragma"] = "no-cache"
                response["Expires"] = "0"
                response["Retry-After"] = "86400"  # 24 ساعة
                response["X-Chat-Status"] = "PERMANENTLY_REMOVED"
                response["X-WebSocket-Status"] = "DISABLED"

                return response

        # فحص headers للطلبات WebSocket
        upgrade_header = request.META.get("HTTP_UPGRADE", "").lower()
        connection_header = request.META.get("HTTP_CONNECTION", "").lower()

        if upgrade_header == "websocket" or "upgrade" in connection_header:
            logger.warning(
                f"🚫 Blocked WebSocket upgrade request: {path} - "
                f"Upgrade: {upgrade_header}, Connection: {connection_header}"
            )

            response = HttpResponseGone("WebSocket connections are not supported")
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

        return None
