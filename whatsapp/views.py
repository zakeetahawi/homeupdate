from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
import json
import logging
from .models import WhatsAppMessage

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def twilio_webhook(request):
    """
    Webhook من Twilio لتحديث حالة الرسائل
    
    يتم استدعاؤه عند:
    - إرسال الرسالة (sent)
    - تسليم الرسالة (delivered)
    - قراءة الرسالة (read)
    - فشل الإرسال (failed)
    """
    try:
        # الحصول على البيانات من Twilio
        message_sid = request.POST.get('MessageSid')
        message_status = request.POST.get('MessageStatus')
        
        if not message_sid:
            logger.warning("Webhook received without MessageSid")
            return JsonResponse({'error': 'MessageSid required'}, status=400)
        
        # البحث عن الرسالة
        try:
            whatsapp_message = WhatsAppMessage.objects.get(external_id=message_sid)
        except WhatsAppMessage.DoesNotExist:
            logger.warning(f"Message not found: {message_sid}")
            return JsonResponse({'error': 'Message not found'}, status=404)
        
        # تحديث الحالة
        status_mapping = {
            'sent': 'SENT',
            'delivered': 'DELIVERED',
            'read': 'READ',
            'failed': 'FAILED',
            'undelivered': 'FAILED'
        }
        
        new_status = status_mapping.get(message_status, whatsapp_message.status)
        
        # تحديث الحقول
        whatsapp_message.status = new_status
        
        if message_status == 'sent' and not whatsapp_message.sent_at:
            whatsapp_message.sent_at = timezone.now()
        elif message_status == 'delivered' and not whatsapp_message.delivered_at:
            whatsapp_message.delivered_at = timezone.now()
        elif message_status == 'read' and not whatsapp_message.read_at:
            whatsapp_message.read_at = timezone.now()
        elif message_status in ['failed', 'undelivered']:
            error_message = request.POST.get('ErrorMessage', 'Unknown error')
            whatsapp_message.error_message = error_message
        
        whatsapp_message.save()
        
        logger.info(f"Updated message {message_sid} to status {new_status}")
        
        return JsonResponse({
            'status': 'success',
            'message_id': whatsapp_message.id,
            'new_status': new_status
        })
        
    except Exception as e:
        logger.error(f"Error in twilio_webhook: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def twilio_status_callback(request):
    """
    Callback بديل لتحديث الحالة
    يستخدم نفس المنطق
    """
    return twilio_webhook(request)


@csrf_exempt
def meta_webhook(request):
    """
    Webhook من Meta WhatsApp Cloud API
    
    يستقبل تحديثات:
    - message status (sent, delivered, read, failed)
    - message errors
    - incoming messages
    """
    try:
        # Webhook verification (GET request from Meta)
        if request.method == 'GET':
            mode = request.GET.get('hub.mode')
            token = request.GET.get('hub.verify_token')
            challenge = request.GET.get('hub.challenge')
            
            # Verify token matches
            from django.conf import settings
            verify_token = getattr(settings, 'WHATSAPP_VERIFY_TOKEN', 'your-verify-token')
            
            if mode == 'subscribe' and token == verify_token:
                logger.info("Webhook verified successfully")
                return HttpResponse(challenge)
            else:
                logger.warning("Webhook verification failed")
                return HttpResponse('Verification failed', status=403)
        
        # Handle webhook events (POST request)
        body = json.loads(request.body.decode('utf-8'))
        
        # Process each entry
        for entry in body.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                
                # Handle message status updates
                for status in value.get('statuses', []):
                    message_id = status.get('id')
                    new_status = status.get('status')
                    timestamp = status.get('timestamp')
                    
                    try:
                        msg = WhatsAppMessage.objects.get(external_id=message_id)
                        _update_message_status(msg, new_status, status)
                        logger.info(f"Updated message {message_id} to {new_status}")
                    except WhatsAppMessage.DoesNotExist:
                        logger.warning(f"Message not found: {message_id}")
                
                # Handle incoming messages (optional - for future use)
                for message in value.get('messages', []):
                    logger.info(f"Received incoming message: {message.get('id')}")
        
        return JsonResponse({'status': 'success'})
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Meta webhook error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def _update_message_status(message, status, data):
    """
    تحديث حالة الرسالة من Meta webhook
    
    Args:
        message: WhatsAppMessage instance
        status: new status string
        data: full status data from Meta
    """
    status_mapping = {
        'sent': 'SENT',
        'delivered': 'DELIVERED',
        'read': 'READ',
        'failed': 'FAILED'
    }
    
    old_status = message.status
    message.status = status_mapping.get(status, message.status)
    
    # Update timestamps
    if status == 'sent' and not message.sent_at:
        message.sent_at = timezone.now()
    elif status == 'delivered' and not message.delivered_at:
        message.delivered_at = timezone.now()
    elif status == 'read' and not message.read_at:
        message.read_at = timezone.now()
    elif status == 'failed':
        errors = data.get('errors', [])
        if errors:
            message.error_message = errors[0].get('message', 'Unknown error')
    
    message.save()
    
    logger.info(f"Message {message.id} status: {old_status} → {message.status}")
