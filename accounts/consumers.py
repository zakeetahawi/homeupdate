import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import InternalMessage, User


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Room group name (Unique per user)
        self.room_group_name = f"user_{self.user.id}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name') and self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "typing":
                recipient_id = data.get("recipient_id")
                is_typing = data.get("is_typing", False)

                if recipient_id:
                    # Send typing status to recipient's group
                    await self.channel_layer.group_send(
                        f"user_{recipient_id}",
                        {
                            "type": "user_typing",
                            "sender_id": self.user.id,
                            "sender_name": self.user.get_full_name()
                            or self.user.username,
                            "is_typing": is_typing,
                        },
                    )

            elif message_type == "read_receipt":
                # Message received by recipient -> Notify sender
                original_sender_id = data.get("sender_id")
                message_id = data.get("message_id")

                if original_sender_id:
                    await self.channel_layer.group_send(
                        f"user_{original_sender_id}",
                        {
                            "type": "read_receipt",  # Maps to handler method below
                            "message_id": message_id,
                            "recipient_id": self.user.id,
                        },
                    )

        except json.JSONDecodeError:
            pass

    # Handler for 'user_typing' event
    async def user_typing(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_typing",
                    "sender_id": event["sender_id"],
                    "sender_name": event["sender_name"],
                    "is_typing": event["is_typing"],
                }
            )
        )

    # Handler for 'read_receipt' event
    async def read_receipt(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "read_receipt",
                    "message_id": event["message_id"],
                    "recipient_id": event["recipient_id"],
                }
            )
        )

    # Handler for 'chat_message' event (sent from Group)
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps({"type": "chat_message", "message": message})
        )
