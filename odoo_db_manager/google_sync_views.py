"""
عروض مزامنة غوغل
"""

import os
import json
import logging
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .google_sync import GoogleSyncConfig, GoogleSyncLog, sync_with_google_sheets
from .views import is_staff_or_superuser

# إعداد التسجيل
logger = logging.getLogger(__name__)

@login_required
@user_passes_test(is_staff_or_superuser)
def google_sync(request):
    """عرض صفحة مزامنة غوغل الرئيسية"""
    # الحصول على إعداد المزامنة النشط
    config = GoogleSyncConfig.get_active_config()
    
    # الحصول على سجلات المزامنة
    logs = GoogleSyncLog.objects.all().order_by('-created_at')[:10]
    
    # حساب وقت المزامنة التالية
    next_sync = None
    if config and config.last_sync:
        next_sync = config.last_sync + datetime.timedelta(hours=config.sync_frequency)
    
    # التحقق من حالة الاتصال
    connection_status = False
    if config:
        try:
            from googleapiclient.discovery import build
            from google.oauth2.credentials import Credentials
            
            # الحصول على بيانات الاعتماد
            credentials = config.get_credentials()
            if credentials:
                # إنشاء كائن بيانات الاعتماد
                creds = Credentials.from_authorized_user_info(credentials)
                
                # محاولة إنشاء خدمة Google Sheets
                service = build('sheets', 'v4', credentials=creds)
                
                # محاولة الوصول إلى جدول البيانات
                service.spreadsheets().get(spreadsheetId=config.spreadsheet_id).execute()
                
                connection_status = True
        except Exception as e:
            logger.error(f"فشل اختبار الاتصال: {str(e)}")
    
    # إعداد سياق العرض
    context = {
        'title': 'مزامنة غوغل',
        'config': config,
        'logs': logs,
        'next_sync': next_sync,
        'connection_status': connection_status,
        'sync_success': request.session.pop('sync_success', False),
        'sync_results': request.session.pop('sync_results', {}),
        'sync_error': request.session.pop('sync_error', False),
        'sync_error_message': request.session.pop('sync_error_message', ''),
    }
    
    return render(request, 'odoo_db_manager/google_sync.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def google_sync_config(request):
    """عرض صفحة إعدادات مزامنة غوغل"""
    # الحصول على إعداد المزامنة النشط
    config = GoogleSyncConfig.get_active_config()
    
    # الحصول على حالة المجدول
    scheduler_enabled = getattr(settings, 'GOOGLE_SYNC_SCHEDULER_ENABLED', False)
    scheduler_status = False
    scheduler_last_run = None
    
    try:
        from django_apscheduler.models import DjangoJobExecution
        
        # التحقق من وجود وظيفة المزامنة
        job_executions = DjangoJobExecution.objects.filter(job_id='google_sync_job').order_by('-run_time')
        if job_executions.exists():
            scheduler_status = True
            scheduler_last_run = job_executions.first().run_time
    except Exception as e:
        logger.error(f"فشل التحقق من حالة المجدول: {str(e)}")
    
    # الحصول على إعدادات الاحتفاظ بالسجلات
    keep_history = getattr(settings, 'GOOGLE_SYNC_KEEP_HISTORY', True)
    history_retention = getattr(settings, 'GOOGLE_SYNC_HISTORY_RETENTION', 30)
    
    # إعداد سياق العرض
    context = {
        'title': 'إعدادات مزامنة غوغل',
        'config': config,
        'config_saved': request.session.pop('config_saved', False),
        'scheduler_enabled': scheduler_enabled,
        'scheduler_status': scheduler_status,
        'scheduler_last_run': scheduler_last_run,
        'keep_history': keep_history,
        'history_retention': history_retention,
    }
    
    return render(request, 'odoo_db_manager/google_sync_config.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def google_sync_config_save(request):
    """حفظ إعدادات مزامنة غوغل"""
    if request.method == 'POST':
        try:
            # الحصول على البيانات من النموذج
            name = request.POST.get('name')
            spreadsheet_id = request.POST.get('spreadsheet_id')
            sync_frequency = int(request.POST.get('sync_frequency', 24))
            is_active = request.POST.get('is_active') == 'on'
            
            # الحصول على إعداد المزامنة الحالي أو إنشاء واحد جديد
            config = GoogleSyncConfig.get_active_config()
            if not config:
                config = GoogleSyncConfig()
            
            # تحديث البيانات
            config.name = name
            config.spreadsheet_id = spreadsheet_id
            config.sync_frequency = sync_frequency
            config.is_active = is_active
            
            # معالجة ملف بيانات الاعتماد
            credentials_file = request.FILES.get('credentials_file')
            if credentials_file:
                # حذف الملف القديم إذا كان موجودًا
                if config.credentials_file:
                    try:
                        default_storage.delete(config.credentials_file.path)
                    except Exception as e:
                        logger.error(f"فشل حذف ملف بيانات الاعتماد القديم: {str(e)}")
                
                # حفظ الملف الجديد
                file_path = f'google_credentials/{credentials_file.name}'
                config.credentials_file.save(file_path, credentials_file)
            
            # حفظ الإعدادات
            config.save()
            
            # تعطيل جميع الإعدادات الأخرى إذا كان هذا الإعداد نشطًا
            if is_active:
                GoogleSyncConfig.objects.exclude(id=config.id).update(is_active=False)
            
            # إضافة رسالة نجاح
            messages.success(request, 'تم حفظ إعدادات مزامنة غوغل بنجاح')
            
            # إضافة متغير في الجلسة لعرض رسالة نجاح
            request.session['config_saved'] = True
            
            # إعادة التوجيه إلى صفحة الإعدادات
            return redirect('odoo_db_manager:google_sync_config')
        
        except Exception as e:
            # تسجيل الخطأ
            logger.error(f"حدث خطأ أثناء حفظ إعدادات مزامنة غوغل: {str(e)}")
            
            # إضافة رسالة خطأ
            messages.error(request, f'حدث خطأ أثناء حفظ الإعدادات: {str(e)}')
            
            # إعادة التوجيه إلى صفحة الإعدادات
            return redirect('odoo_db_manager:google_sync_config')
    
    # إعادة التوجيه إلى صفحة الإعدادات إذا لم تكن الطلب POST
    return redirect('odoo_db_manager:google_sync_config')


@login_required
@user_passes_test(is_staff_or_superuser)
def google_sync_delete_credentials(request):
    """حذف ملف بيانات الاعتماد"""
    try:
        # الحصول على إعداد المزامنة النشط
        config = GoogleSyncConfig.get_active_config()
        
        if config and config.credentials_file:
            # حذف الملف
            default_storage.delete(config.credentials_file.path)
            
            # تحديث الإعداد
            config.credentials_file = None
            config.save()
            
            # إضافة رسالة نجاح
            messages.success(request, 'تم حذف ملف بيانات الاعتماد بنجاح')
        else:
            # إضافة رسالة خطأ
            messages.error(request, 'لا يوجد ملف بيانات اعتماد لحذفه')
    
    except Exception as e:
        # تسجيل الخطأ
        logger.error(f"حدث خطأ أثناء حذف ملف بيانات الاعتماد: {str(e)}")
        
        # إضافة رسالة خطأ
        messages.error(request, f'حدث خطأ أثناء حذف ملف بيانات الاعتماد: {str(e)}')
    
    # إعادة التوجيه إلى صفحة الإعدادات
    return redirect('odoo_db_manager:google_sync_config')


@login_required
@user_passes_test(is_staff_or_superuser)
def google_sync_options(request):
    """حفظ خيارات المزامنة"""
    if request.method == 'POST':
        try:
            # الحصول على إعداد المزامنة النشط
            config = GoogleSyncConfig.get_active_config()
            
            if not config:
                # إضافة رسالة خطأ
                messages.error(request, 'لا يوجد إعداد مزامنة نشط')
                
                # إعادة التوجيه إلى صفحة المزامنة
                return redirect('odoo_db_manager:google_sync')
            
            # تحديث خيارات المزامنة
            config.sync_databases = request.POST.get('sync_databases') == 'on'
            config.sync_users = request.POST.get('sync_users') == 'on'
            config.sync_customers = request.POST.get('sync_customers') == 'on'
            config.sync_orders = request.POST.get('sync_orders') == 'on'
            config.sync_products = request.POST.get('sync_products') == 'on'
            config.sync_settings = request.POST.get('sync_settings') == 'on'
            
            # تحديث تكرار المزامنة
            config.sync_frequency = int(request.POST.get('sync_frequency', 24))
            
            # حفظ الإعدادات
            config.save()
            
            # إضافة رسالة نجاح
            messages.success(request, 'تم حفظ خيارات المزامنة بنجاح')
        
        except Exception as e:
            # تسجيل الخطأ
            logger.error(f"حدث خطأ أثناء حفظ خيارات المزامنة: {str(e)}")
            
            # إضافة رسالة خطأ
            messages.error(request, f'حدث خطأ أثناء حفظ خيارات المزامنة: {str(e)}')
    
    # إعادة التوجيه إلى صفحة المزامنة
    return redirect('odoo_db_manager:google_sync')


@login_required
@user_passes_test(is_staff_or_superuser)
def google_sync_now(request):
    """تنفيذ المزامنة الآن"""
    try:
        # الحصول على إعداد المزامنة النشط
        config = GoogleSyncConfig.get_active_config()
        
        if not config:
            # إضافة رسالة خطأ
            messages.error(request, 'لا يوجد إعداد مزامنة نشط')
            
            # إعادة التوجيه إلى صفحة المزامنة
            return redirect('odoo_db_manager:google_sync')
        
        # تنفيذ المزامنة
        start_time = datetime.datetime.now()
        result = sync_with_google_sheets(config_id=config.id, manual=True)
        end_time = datetime.datetime.now()
        
        # حساب مدة المزامنة
        duration = (end_time - start_time).total_seconds()
        
        if result['status'] == 'success':
            # إضافة رسالة نجاح
            messages.success(request, 'تمت المزامنة مع Google Sheets بنجاح')
            
            # إضافة متغيرات في الجلسة لعرض رسالة نجاح
            request.session['sync_success'] = True
            
            # حساب إجمالي العناصر التي تمت مزامنتها
            total_items = 0
            for key, value in result.get('results', {}).items():
                if isinstance(value, dict) and 'message' in value:
                    # استخراج عدد العناصر من الرسالة (مثال: "تمت مزامنة 10 قاعدة بيانات")
                    import re
                    match = re.search(r'(\d+)', value['message'])
                    if match:
                        total_items += int(match.group(1))
            
            request.session['sync_results'] = {
                'total_items': total_items,
                'duration': round(duration, 2)
            }
        else:
            # إضافة رسالة خطأ
            messages.error(request, f'فشلت المزامنة مع Google Sheets: {result["message"]}')
            
            # إضافة متغيرات في الجلسة لعرض رسالة خطأ
            request.session['sync_error'] = True
            request.session['sync_error_message'] = result['message']
    
    except Exception as e:
        # تسجيل الخطأ
        logger.error(f"حدث خطأ أثناء تنفيذ المزامنة: {str(e)}")
        
        # إضافة رسالة خطأ
        messages.error(request, f'حدث خطأ أثناء تنفيذ المزامنة: {str(e)}')
        
        # إضافة متغيرات في الجلسة لعرض رسالة خطأ
        request.session['sync_error'] = True
        request.session['sync_error_message'] = str(e)
    
    # إعادة التوجيه إلى صفحة المزامنة
    return redirect('odoo_db_manager:google_sync')


@login_required
@user_passes_test(is_staff_or_superuser)
def google_sync_test(request):
    """اختبار الاتصال بـ Google Sheets"""
    try:
        # الحصول على إعداد المزامنة النشط
        config = GoogleSyncConfig.get_active_config()
        
        if not config:
            # إضافة رسالة خطأ
            messages.error(request, 'لا يوجد إعداد مزامنة نشط')
            
            # إعادة التوجيه إلى صفحة المزامنة
            return redirect('odoo_db_manager:google_sync')
        
        # الحصول على بيانات الاعتماد
        credentials = config.get_credentials()
        
        if not credentials:
            # إضافة رسالة خطأ
            messages.error(request, 'لا يمكن قراءة بيانات الاعتماد')
            
            # إعادة التوجيه إلى صفحة المزامنة
            return redirect('odoo_db_manager:google_sync')
        
        # اختبار الاتصال
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        
        # إنشاء كائن بيانات الاعتماد
        creds = Credentials.from_authorized_user_info(credentials)
        
        # إنشاء خدمة Google Sheets
        service = build('sheets', 'v4', credentials=creds)
        
        # محاولة الوصول إلى جدول البيانات
        spreadsheet = service.spreadsheets().get(spreadsheetId=config.spreadsheet_id).execute()
        
        # الحصول على عنوان جدول البيانات
        spreadsheet_title = spreadsheet.get('properties', {}).get('title', 'جدول بيانات')
        
        # إضافة رسالة نجاح
        messages.success(request, f'تم الاتصال بنجاح بجدول البيانات "{spreadsheet_title}"')
    
    except Exception as e:
        # تسجيل الخطأ
        logger.error(f"فشل اختبار الاتصال: {str(e)}")
        
        # إضافة رسالة خطأ
        messages.error(request, f'فشل الاتصال بـ Google Sheets: {str(e)}')
    
    # إعادة التوجيه إلى صفحة المزامنة
    return redirect('odoo_db_manager:google_sync')


@login_required
@user_passes_test(is_staff_or_superuser)
def google_sync_reset(request):
    """إعادة تعيين بيانات المزامنة"""
    try:
        # الحصول على إعداد المزامنة النشط
        config = GoogleSyncConfig.get_active_config()
        
        if not config:
            # إضافة رسالة خطأ
            messages.error(request, 'لا يوجد إعداد مزامنة نشط')
            
            # إعادة التوجيه إلى صفحة المزامنة
            return redirect('odoo_db_manager:google_sync')
        
        # الحصول على بيانات الاعتماد
        credentials = config.get_credentials()
        
        if not credentials:
            # إضافة رسالة خطأ
            messages.error(request, 'لا يمكن قراءة بيانات الاعتماد')
            
            # إعادة التوجيه إلى صفحة المزامنة
            return redirect('odoo_db_manager:google_sync')
        
        # إعادة تعيين البيانات
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        
        # إنشاء كائن بيانات الاعتماد
        creds = Credentials.from_authorized_user_info(credentials)
        
        # إنشاء خدمة Google Sheets
        service = build('sheets', 'v4', credentials=creds)
        
        # الحصول على معلومات جدول البيانات
        spreadsheet = service.spreadsheets().get(spreadsheetId=config.spreadsheet_id).execute()
        
        # حذف جميع أوراق العمل باستثناء الورقة الأولى
        sheets = spreadsheet.get('sheets', [])
        requests = []
        
        for sheet in sheets[1:]:  # تجاوز الورقة الأولى
            sheet_id = sheet.get('properties', {}).get('sheetId')
            requests.append({
                'deleteSheet': {
                    'sheetId': sheet_id
                }
            })
        
        # مسح محتوى الورقة الأولى
        first_sheet_id = sheets[0].get('properties', {}).get('sheetId')
        first_sheet_title = sheets[0].get('properties', {}).get('title')
        
        requests.append({
            'updateCells': {
                'range': {
                    'sheetId': first_sheet_id,
                    'startRowIndex': 0,
                    'startColumnIndex': 0
                },
                'fields': 'userEnteredValue'
            }
        })
        
        # تنفيذ الطلبات
        if requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=config.spreadsheet_id,
                body={'requests': requests}
            ).execute()
        
        # إعادة تعيين وقت آخر مزامنة
        config.last_sync = None
        config.save()
        
        # حذف سجلات المزامنة
        GoogleSyncLog.objects.all().delete()
        
        # إضافة رسالة نجاح
        messages.success(request, 'تم إعادة تعيين بيانات المزامنة بنجاح')
        
        # تنفيذ المزامنة مرة أخرى
        return redirect('odoo_db_manager:google_sync_now')
    
    except Exception as e:
        # تسجيل الخطأ
        logger.error(f"حدث خطأ أثناء إعادة تعيين بيانات المزامنة: {str(e)}")
        
        # إضافة رسالة خطأ
        messages.error(request, f'حدث خطأ أثناء إعادة تعيين بيانات المزامنة: {str(e)}')
    
    # إعادة التوجيه إلى صفحة المزامنة
    return redirect('odoo_db_manager:google_sync')


@login_required
@user_passes_test(is_staff_or_superuser)
@require_POST
@csrf_exempt
def google_sync_advanced_settings(request):
    """حفظ الإعدادات المتقدمة"""
    try:
        # الحصول على البيانات من الطلب
        data = json.loads(request.body)
        
        # تحديث الإعدادات
        enable_scheduler = data.get('enable_scheduler', False)
        keep_history = data.get('keep_history', True)
        history_retention = int(data.get('history_retention', 30))
        
        # حفظ الإعدادات في ملف الإعدادات
        settings_file = os.path.join(settings.BASE_DIR, 'google_sync_settings.json')
        
        settings_data = {
            'enable_scheduler': enable_scheduler,
            'keep_history': keep_history,
            'history_retention': history_retention,
            'updated_at': timezone.now().isoformat()
        }
        
        with open(settings_file, 'w') as f:
            json.dump(settings_data, f, indent=4)
        
        # تحديث إعدادات Django
        setattr(settings, 'GOOGLE_SYNC_SCHEDULER_ENABLED', enable_scheduler)
        setattr(settings, 'GOOGLE_SYNC_KEEP_HISTORY', keep_history)
        setattr(settings, 'GOOGLE_SYNC_HISTORY_RETENTION', history_retention)
        
        # تحديث المجدول
        if enable_scheduler:
            # تفعيل المجدول
            try:
                from django_apscheduler.models import DjangoJob
                from apscheduler.triggers.interval import IntervalTrigger
                from django_apscheduler.jobstores import DjangoJobStore
                from apscheduler.schedulers.background import BackgroundScheduler
                
                # إنشاء المجدول
                scheduler = BackgroundScheduler()
                scheduler.add_jobstore(DjangoJobStore(), 'default')
                
                # إضافة وظيفة المزامنة
                job = scheduler.add_job(
                    sync_with_google_sheets,
                    trigger=IntervalTrigger(hours=24),
                    id='google_sync_job',
                    replace_existing=True
                )
                
                # بدء المجدول
                scheduler.start()
            except Exception as e:
                logger.error(f"فشل تفعيل المجدول: {str(e)}")
        else:
            # تعطيل المجدول
            try:
                from django_apscheduler.models import DjangoJob
                
                # حذف وظيفة المزامنة
                DjangoJob.objects.filter(id='google_sync_job').delete()
            except Exception as e:
                logger.error(f"فشل تعطيل المجدول: {str(e)}")
        
        # حذف سجلات المزامنة القديمة
        if keep_history and history_retention > 0:
            # حساب تاريخ الحذف
            delete_date = timezone.now() - datetime.timedelta(days=history_retention)
            
            # حذف السجلات القديمة
            GoogleSyncLog.objects.filter(created_at__lt=delete_date).delete()
        
        # إرجاع استجابة نجاح
        return JsonResponse({'status': 'success', 'message': 'تم حفظ الإعدادات المتقدمة بنجاح'})
    
    except Exception as e:
        # تسجيل الخطأ
        logger.error(f"حدث خطأ أثناء حفظ الإعدادات المتقدمة: {str(e)}")
        
        # إرجاع استجابة خطأ
        return JsonResponse({'status': 'error', 'message': str(e)})