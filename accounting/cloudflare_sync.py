"""
نظام مزامنة الحسابات البنكية مع Cloudflare Workers KV
Bank Accounts Cloudflare Synchronization System
"""
import json
import requests
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


def sync_bank_accounts_to_cloudflare(accounts=None):
    """
    مزامنة الحسابات البنكية مع Cloudflare Workers KV
    
    Args:
        accounts: قائمة الحسابات للمزامنة (None = جميع الحسابات النشطة)
    
    Returns:
        dict: نتيجة المزامنة
    """
    
    # التحقق من التفعيل
    if not getattr(settings, 'CLOUDFLARE_SYNC_ENABLED', False):
        return {
            'success': False,
            'error': 'Cloudflare sync is disabled in settings'
        }
    
    # التحقق من الإعدادات المطلوبة
    api_key = getattr(settings, 'CLOUDFLARE_SYNC_API_KEY', None)
    is_dev_mode = getattr(settings, 'DEBUG', False) or api_key == 'dev-placeholder-token'
    
    if not api_key:
        return {
            'success': False,
            'error': 'CLOUDFLARE_SYNC_API_KEY not configured'
        }
    
    try:
        from accounting.models import BankAccount
        
        # تحديد الحسابات للمزامنة
        if accounts is None:
            accounts = BankAccount.objects.filter(is_active=True)
        
        if not accounts:
            return {
                'success': True,
                'count': 0,
                'message': 'No accounts to sync'
            }
        
        # تحويل الحسابات إلى قاموس
        bank_data = {}
        for account in accounts:
            account_data = account.to_cloudflare_dict()
            bank_data[account.unique_code] = account_data
        
        # إضافة صفحة "all" لعرض جميع الحسابات النشطة
        active_accounts = BankAccount.objects.filter(
            is_active=True,
            show_in_qr=True
        ).order_by('display_order', 'bank_name')
        
        all_accounts_data = {
            'type': 'all_accounts',
            'accounts': [acc.to_cloudflare_dict() for acc in active_accounts],
            'count': active_accounts.count(),
            'last_updated': timezone.now().isoformat(),
        }
        bank_data['all'] = all_accounts_data
        
        # في وضع التطوير، نحاكي النجاح فقط
        if is_dev_mode:
            # تحديث حالة المزامنة (simulation)
            for account in accounts:
                account.cloudflare_synced = True
                account.last_synced_at = timezone.now()
                account.save(update_fields=['cloudflare_synced', 'last_synced_at'])
            
            return {
                'success': True,
                'count': len(accounts),
                'message': f'✓ Development Mode: Simulated sync for {len(accounts)} accounts',
                'dev_mode': True
            }
        
        # إرسال إلى Cloudflare Workers KV (Production)
        success = upload_to_cloudflare_kv(bank_data, 'bank_accounts')
        
        if success:
            # تحديث حالة المزامنة
            for account in accounts:
                account.cloudflare_synced = True
                account.last_synced_at = timezone.now()
                account.save(update_fields=['cloudflare_synced', 'last_synced_at'])
            
            return {
                'success': True,
                'count': len(accounts),
                'message': f'Successfully synced {len(accounts)} bank accounts'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to upload to Cloudflare KV'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def upload_to_cloudflare_kv(data, key_prefix='bank'):
    """
    رفع البيانات إلى Cloudflare Workers KV
    
    Args:
        data: البيانات للرفع (dict)
        key_prefix: بادئة المفتاح
    
    Returns:
        bool: نجاح العملية
    """
    try:
        # الحصول على إعدادات Cloudflare
        worker_url = getattr(settings, 'CLOUDFLARE_WORKER_URL', None)
        api_key = getattr(settings, 'CLOUDFLARE_SYNC_API_KEY', None)
        
        if not all([worker_url, api_key]):
            print('Missing Cloudflare Worker configuration (URL or API Key)')
            return False
        
        # تحضير البيانات للرفع
        formatted_data = {}
        for key, value in data.items():
            # تحويل القيم إلى JSON-safe format
            safe_value = json.loads(json.dumps(value, default=str))
            formatted_data[f'{key_prefix}:{key}'] = safe_value
        
        # إعداد طلب المزامنة
        payload = {
            'action': 'sync_all_bank',
            'bank_accounts': formatted_data
        }
        
        # Headers
        headers = {
            'Content-Type': 'application/json',
            'X-Sync-API-Key': api_key,
        }
        
        # إرسال الطلب إلى Worker endpoint
        response = requests.post(
            f'{worker_url}/sync',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f'Successfully uploaded {len(formatted_data)} bank accounts to Cloudflare')
            return True
        else:
            print(f'Cloudflare Worker Error: {response.status_code} - {response.text}')
            return False
    
    except Exception as e:
        print(f'Error uploading to Cloudflare KV: {str(e)}')
        return False


def get_bank_account_from_cloudflare(unique_code):
    """
    الحصول على بيانات حساب بنكي من Cloudflare KV
    (للاختبار والتحقق)
    
    Args:
        unique_code: الكود الفريد للحساب
    
    Returns:
        dict: بيانات الحساب أو None
    """
    try:
        account_id = getattr(settings, 'CLOUDFLARE_ACCOUNT_ID', None)
        namespace_id = getattr(settings, 'CLOUDFLARE_KV_NAMESPACE_ID', None)
        api_token = getattr(settings, 'CLOUDFLARE_SYNC_API_KEY', None)
        
        if not all([account_id, namespace_id, api_token]):
            return None
        
        url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/bank:{unique_code}'
        
        headers = {
            'Authorization': f'Bearer {api_token}',
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
    except Exception as e:
        print(f'Error fetching from Cloudflare KV: {str(e)}')
        return None


def sync_qr_design_to_cloudflare(design_settings):
    """
    مزامنة إعدادات تصميم QR مع Cloudflare Workers KV
    
    Args:
        design_settings: كائن QRDesignSettings
    
    Returns:
        dict: نتيجة المزامنة
    """
    # في وضع Development
    is_dev_mode = getattr(settings, 'DEBUG', False)
    api_key = getattr(settings, 'CLOUDFLARE_SYNC_API_KEY', None)
    
    if is_dev_mode or api_key == 'dev-placeholder-token':
        # محاكاة المزامنة
        return {
            'success': True,
            'message': 'Development Mode: QR Design settings updated locally',
            'dev_mode': True
        }
    
    try:
        # تحويل الإعدادات إلى JSON
        design_data = design_settings.to_dict()
        
        # رفع إلى Cloudflare KV عبر Worker
        worker_url = getattr(settings, 'CLOUDFLARE_WORKER_URL', None)
        api_token = getattr(settings, 'CLOUDFLARE_SYNC_API_KEY', None)
        
        if not all([worker_url, api_token]):
            return {
                'success': False,
                'error': 'Cloudflare Worker configuration missing'
            }
        
        # إرسال إلى Worker
        payload = {
            'action': 'sync_qr_design',
            'design': design_data
        }
        
        headers = {
            'Content-Type': 'application/json',
            'X-Sync-API-Key': api_token,
        }
        
        response = requests.post(
            f'{worker_url}/sync',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                'success': True,
                'message': 'QR Design settings synced successfully'
            }
        else:
            return {
                'success': False,
                'error': f'Failed to upload to Cloudflare KV: {response.text}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

