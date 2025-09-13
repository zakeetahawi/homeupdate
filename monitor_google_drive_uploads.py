#!/usr/bin/env python3
"""
مراقبة رفع الملفات إلى Google Drive في الوقت الفعلي
"""

import os
import sys
import django
import time
import json
from datetime import datetime

# إعداد Django
sys.path.append('/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from inspections.models import Inspection
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from odoo_db_manager.models import GoogleDriveConfig

def get_drive_service():
    """الحصول على خدمة Google Drive"""
    try:
        config = GoogleDriveConfig.get_active_config()
        if not config:
            return None
            
        credentials_path = config.credentials_file.path
        with open(credentials_path, 'r') as f:
            credentials_data = json.load(f)
            
        scopes = ['https://www.googleapis.com/auth/drive.file']
        credentials = Credentials.from_service_account_info(credentials_data, scopes=scopes)
        service = build('drive', 'v3', credentials=credentials)
        
        return service, config
    except Exception as e:
        print(f"❌ خطأ في الاتصال بـ Google Drive: {e}")
        return None, None

def count_files_in_drive():
    """عد الملفات في Google Drive"""
    service, config = get_drive_service()
    if not service:
        return 0, 0
    
    try:
        # عد ملفات العقود
        contracts_query = f"'{config.contracts_folder_id}' in parents and trashed=false"
        contracts_result = service.files().list(
            q=contracts_query,
            fields="files(id)",
            pageSize=1000
        ).execute()
        contracts_count = len(contracts_result.get('files', []))
        
        # عد ملفات المعاينات
        inspections_query = f"'{config.inspections_folder_id}' in parents and trashed=false"
        inspections_result = service.files().list(
            q=inspections_query,
            fields="files(id)",
            pageSize=1000
        ).execute()
        inspections_count = len(inspections_result.get('files', []))
        
        return contracts_count, inspections_count
    except Exception as e:
        print(f"❌ خطأ في عد الملفات: {e}")
        return 0, 0

def get_upload_status():
    """الحصول على حالة الرفع من قاعدة البيانات"""
    
    # العقود
    total_contracts = Order.objects.filter(contract_file__isnull=False).count()
    uploaded_contracts = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=False
    ).count()
    pending_contracts = Order.objects.filter(
        contract_file__isnull=False,
        contract_google_drive_file_id__isnull=True
    ).count()
    
    # المعاينات
    total_inspections = Inspection.objects.filter(inspection_file__isnull=False).count()
    uploaded_inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=False
    ).count()
    pending_inspections = Inspection.objects.filter(
        inspection_file__isnull=False,
        google_drive_file_id__isnull=True
    ).count()
    
    return {
        'contracts': {
            'total': total_contracts,
            'uploaded': uploaded_contracts,
            'pending': pending_contracts,
            'percentage': round((uploaded_contracts / total_contracts * 100) if total_contracts > 0 else 0, 2)
        },
        'inspections': {
            'total': total_inspections,
            'uploaded': uploaded_inspections,
            'pending': pending_inspections,
            'percentage': round((uploaded_inspections / total_inspections * 100) if total_inspections > 0 else 0, 2)
        }
    }

def monitor_uploads(duration_minutes=30):
    """مراقبة الرفع لفترة محددة"""
    print("🔍 بدء مراقبة رفع الملفات إلى Google Drive")
    print("=" * 70)
    
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    # الحالة الأولية
    initial_drive_contracts, initial_drive_inspections = count_files_in_drive()
    initial_status = get_upload_status()
    
    print(f"📊 الحالة الأولية:")
    print(f"   📁 ملفات العقود في Google Drive: {initial_drive_contracts}")
    print(f"   📁 ملفات المعاينات في Google Drive: {initial_drive_inspections}")
    print(f"   📋 عقود مرفوعة في قاعدة البيانات: {initial_status['contracts']['uploaded']}/{initial_status['contracts']['total']} ({initial_status['contracts']['percentage']}%)")
    print(f"   📋 معاينات مرفوعة في قاعدة البيانات: {initial_status['inspections']['uploaded']}/{initial_status['inspections']['total']} ({initial_status['inspections']['percentage']}%)")
    print(f"   ⏱️ مراقبة لمدة {duration_minutes} دقيقة...")
    print()
    
    iteration = 0
    while time.time() < end_time:
        iteration += 1
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # الحصول على الحالة الحالية
        current_drive_contracts, current_drive_inspections = count_files_in_drive()
        current_status = get_upload_status()
        
        # حساب التقدم
        contracts_progress = current_status['contracts']['uploaded'] - initial_status['contracts']['uploaded']
        inspections_progress = current_status['inspections']['uploaded'] - initial_status['inspections']['uploaded']
        drive_contracts_progress = current_drive_contracts - initial_drive_contracts
        drive_inspections_progress = current_drive_inspections - initial_drive_inspections
        
        print(f"🕐 {current_time} - التحديث #{iteration}")
        print(f"   📈 تقدم العقود: +{contracts_progress} (إجمالي: {current_status['contracts']['uploaded']}/{current_status['contracts']['total']} - {current_status['contracts']['percentage']}%)")
        print(f"   📈 تقدم المعاينات: +{inspections_progress} (إجمالي: {current_status['inspections']['uploaded']}/{current_status['inspections']['total']} - {current_status['inspections']['percentage']}%)")
        print(f"   🌐 ملفات Google Drive: عقود +{drive_contracts_progress} ({current_drive_contracts}), معاينات +{drive_inspections_progress} ({current_drive_inspections})")
        
        # التحقق من وجود تقدم
        if contracts_progress > 0 or inspections_progress > 0:
            print(f"   ✅ يتم الرفع بنجاح!")
        elif iteration > 3:  # بعد 3 تحديثات
            print(f"   ⏳ لا يوجد تقدم حتى الآن...")
        
        print()
        
        # انتظار 30 ثانية
        time.sleep(30)
    
    # التقرير النهائي
    final_drive_contracts, final_drive_inspections = count_files_in_drive()
    final_status = get_upload_status()
    
    total_contracts_uploaded = final_status['contracts']['uploaded'] - initial_status['contracts']['uploaded']
    total_inspections_uploaded = final_status['inspections']['uploaded'] - initial_status['inspections']['uploaded']
    total_drive_contracts_added = final_drive_contracts - initial_drive_contracts
    total_drive_inspections_added = final_drive_inspections - initial_drive_inspections
    
    print("=" * 70)
    print("📊 تقرير المراقبة النهائي")
    print("=" * 70)
    print(f"⏱️ مدة المراقبة: {duration_minutes} دقيقة")
    print(f"📤 عقود تم رفعها: {total_contracts_uploaded}")
    print(f"📤 معاينات تم رفعها: {total_inspections_uploaded}")
    print(f"🌐 ملفات أضيفت لـ Google Drive: عقود {total_drive_contracts_added}, معاينات {total_drive_inspections_added}")
    print(f"📋 الحالة النهائية:")
    print(f"   - عقود: {final_status['contracts']['uploaded']}/{final_status['contracts']['total']} ({final_status['contracts']['percentage']}%)")
    print(f"   - معاينات: {final_status['inspections']['uploaded']}/{final_status['inspections']['total']} ({final_status['inspections']['percentage']}%)")
    
    if total_contracts_uploaded > 0 or total_inspections_uploaded > 0:
        print("🎉 تم رفع ملفات جديدة بنجاح!")
    else:
        print("⚠️ لم يتم رفع ملفات جديدة خلال فترة المراقبة")
    
    return {
        'contracts_uploaded': total_contracts_uploaded,
        'inspections_uploaded': total_inspections_uploaded,
        'drive_contracts_added': total_drive_contracts_added,
        'drive_inspections_added': total_drive_inspections_added,
        'final_status': final_status
    }

def quick_status():
    """عرض حالة سريعة للرفع"""
    print("📊 حالة الرفع الحالية")
    print("=" * 40)
    
    drive_contracts, drive_inspections = count_files_in_drive()
    status = get_upload_status()
    
    print(f"🌐 Google Drive:")
    print(f"   📁 عقود: {drive_contracts}")
    print(f"   📁 معاينات: {drive_inspections}")
    print()
    print(f"💾 قاعدة البيانات:")
    print(f"   📋 عقود: {status['contracts']['uploaded']}/{status['contracts']['total']} ({status['contracts']['percentage']}%)")
    print(f"   📋 معاينات: {status['inspections']['uploaded']}/{status['inspections']['total']} ({status['inspections']['percentage']}%)")
    print(f"   ⏳ عقود معلقة: {status['contracts']['pending']}")
    print(f"   ⏳ معاينات معلقة: {status['inspections']['pending']}")

def main():
    """الدالة الرئيسية"""
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            quick_status()
            return
        elif sys.argv[1] == "monitor":
            duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            monitor_uploads(duration)
            return
    
    # عرض الحالة السريعة أولاً
    quick_status()
    print()
    
    # سؤال المستخدم
    choice = input("هل تريد بدء المراقبة؟ (y/n): ").lower()
    if choice in ['y', 'yes', 'نعم']:
        duration = input("كم دقيقة تريد المراقبة؟ (افتراضي: 30): ")
        try:
            duration = int(duration) if duration else 30
        except:
            duration = 30
        
        print()
        monitor_uploads(duration)

if __name__ == "__main__":
    main()
