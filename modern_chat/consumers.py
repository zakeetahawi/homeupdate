import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ChatRoom, Message, UserStatus

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        # إضافة المستخدم لمجموعة المستخدمين النشطين
        self.user_group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        # تحديث حالة المستخدم إلى متصل
        await self.update_user_status('online')
        
        await self.accept()
        
        # إشعار المستخدمين الآخرين بالاتصال
        await self.broadcast_user_status_update()

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        # تحديث حالة المستخدم إلى غير متصل
        if hasattr(self, 'user') and not self.user.is_anonymous:
            await self.update_user_status('offline')
            await self.broadcast_user_status_update()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'join_room':
                await self.join_room(data.get('room_id'))
            elif message_type == 'leave_room':
                await self.leave_room(data.get('room_id'))
            elif message_type == 'send_message':
                await self.send_message(data)
            elif message_type == 'typing_start':
                await self.handle_typing(data.get('room_id'), True)
            elif message_type == 'typing_stop':
                await self.handle_typing(data.get('room_id'), False)
            elif message_type == 'mark_read':
                await self.mark_messages_read(data.get('room_id'))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def join_room(self, room_id):
        if not room_id:
            return

        # التحقق من صلاحية الوصول للغرفة
        room = await self.get_room(room_id)
        if not room:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Room not found or access denied'
            }))
            return

        # مغادرة الغرفة السابقة إن وجدت
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        # الانضمام للغرفة الجديدة
        self.room_id = room_id
        self.room_group_name = f"chat_{room_id}"
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # إرسال تأكيد الانضمام
        await self.send(text_data=json.dumps({
            'type': 'room_joined',
            'room_id': room_id
        }))

    async def leave_room(self, room_id):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            delattr(self, 'room_group_name')
            delattr(self, 'room_id')

    async def send_message(self, data):
        room_id = data.get('room_id')
        content = data.get('content', '').strip()
        
        if not content or not room_id:
            return

        # حفظ الرسالة في قاعدة البيانات
        message = await self.save_message(room_id, content)
        if not message:
            return

        # إرسال الرسالة لجميع أعضاء الغرفة
        message_data = {
            'type': 'new_message',
            'message': {
                'id': str(message['id']),
                'content': message['content'],
                'sender': {
                    'id': message['sender_id'],
                    'name': message['sender_name'],
                    'is_current_user': False  # سيتم تحديثه في chat_message
                },
                'created_at': message['created_at'],
                'room_id': room_id
            }
        }

        await self.channel_layer.group_send(
            f"chat_{room_id}",
            message_data
        )

        # إرسال إشعار للمستخدمين غير المتصلين بالغرفة
        await self.notify_offline_users(room_id, message)

    async def handle_typing(self, room_id, is_typing):
        if not hasattr(self, 'room_group_name') or not room_id:
            return

        await self.channel_layer.group_send(
            f"chat_{room_id}",
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'user_name': self.user.get_full_name() or self.user.username,
                'is_typing': is_typing,
                'room_id': room_id
            }
        )

    async def mark_messages_read(self, room_id):
        if not room_id:
            return
            
        await self.mark_room_messages_read(room_id)
        
        # إشعار أعضاء الغرفة بقراءة الرسائل
        await self.channel_layer.group_send(
            f"chat_{room_id}",
            {
                'type': 'messages_read',
                'user_id': self.user.id,
                'room_id': room_id
            }
        )

    # معالجات الأحداث
    async def new_message(self, event):
        message = event['message']
        message['sender']['is_current_user'] = message['sender']['id'] == self.user.id
        
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': message
        }))

    async def typing_indicator(self, event):
        # لا نرسل مؤشر الكتابة للمستخدم نفسه
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user_name': event['user_name'],
                'is_typing': event['is_typing'],
                'room_id': event['room_id']
            }))

    async def messages_read(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'messages_read',
                'user_id': event['user_id'],
                'room_id': event['room_id']
            }))

    async def user_status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status_update',
            'user_id': event['user_id'],
            'status': event['status']
        }))

    async def new_message_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_message_notification',
            'message': event['message'],
            'room_id': event['room_id']
        }))

    # دوال قاعدة البيانات
    @database_sync_to_async
    def get_room(self, room_id):
        try:
            room = ChatRoom.objects.get(id=room_id, participants=self.user)
            return room
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, room_id, content):
        try:
            room = ChatRoom.objects.get(id=room_id, participants=self.user)
            message = Message.objects.create(
                room=room,
                sender=self.user,
                content=content,
                message_type='text'
            )
            return {
                'id': message.id,
                'content': message.content,
                'sender_id': message.sender.id,
                'sender_name': message.sender.get_full_name() or message.sender.username,
                'created_at': message.created_at.isoformat()
            }
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def update_user_status(self, status):
        user_status, created = UserStatus.objects.get_or_create(user=self.user)
        user_status.status = status
        user_status.save()

    @database_sync_to_async
    def mark_room_messages_read(self, room_id):
        from .models import MessageRead
        try:
            room = ChatRoom.objects.get(id=room_id, participants=self.user)
            unread_messages = Message.objects.filter(
                room=room,
                is_deleted=False
            ).exclude(sender=self.user).exclude(reads__user=self.user)
            
            for message in unread_messages:
                MessageRead.objects.get_or_create(message=message, user=self.user)
                
        except ChatRoom.DoesNotExist:
            pass

    async def broadcast_user_status_update(self):
        # إشعار جميع المستخدمين المتصلين بتحديث الحالة
        await self.channel_layer.group_send(
            "users_online",
            {
                'type': 'user_status_update',
                'user_id': self.user.id,
                'status': 'online' if hasattr(self, 'user_group_name') else 'offline'
            }
        )

    async def notify_offline_users(self, room_id, message):
        # إشعار المستخدمين غير المتصلين بالغرفة
        room_participants = await self.get_room_participants(room_id)
        for participant_id in room_participants:
            if participant_id != self.user.id:
                await self.channel_layer.group_send(
                    f"user_{participant_id}",
                    {
                        'type': 'new_message_notification',
                        'message': message,
                        'room_id': room_id
                    }
                )

    @database_sync_to_async
    def get_room_participants(self, room_id):
        try:
            room = ChatRoom.objects.get(id=room_id)
            return list(room.participants.values_list('id', flat=True))
        except ChatRoom.DoesNotExist:
            return []
