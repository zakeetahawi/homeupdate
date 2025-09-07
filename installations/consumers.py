import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import InstallationSchedule


class InstallationConsumer(AsyncWebsocketConsumer):
    """WebSocket Consumer لقسم التركيبات"""
    
    async def connect(self):
        """اتصال العميل"""
        await self.channel_layer.group_add(
            "installations",
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        """فصل العميل"""
        await self.channel_layer.group_discard(
            "installations",
            self.channel_name
        )
    
    async def receive(self, text_data):
        """استقبال الرسائل"""
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'status_update':
            installation_id = text_data_json.get('installation_id')
            new_status = text_data_json.get('status')
            
            # تحديث الحالة في قاعدة البيانات
            await self.update_installation_status(installation_id, new_status)
            
            # إرسال التحديث لجميع العملاء
            await self.channel_layer.group_send(
                "installations",
                {
                    'type': 'installation_status_update',
                    'installation_id': installation_id,
                    'status': new_status
                }
            )
    
    async def installation_status_update(self, event):
        """إرسال تحديث حالة التركيب"""
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'installation_id': event['installation_id'],
            'status': event['status']
        }))
    
    @database_sync_to_async
    def update_installation_status(self, installation_id, new_status):
        """تحديث حالة التركيب في قاعدة البيانات"""
        try:
            installation = InstallationSchedule.objects.get(id=installation_id)
            old_status = installation.status
            installation.status = new_status
            installation.save()

            # تحديث الطلبات المرتبطة
            from installations.views import update_related_orders
            update_related_orders(installation, new_status, old_status)

            return True
        except InstallationSchedule.DoesNotExist:
            return False
