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

from .google_sync import (
    GoogleSyncConfig, GoogleSyncLog, sync_with_google_sheets, sync_databases,
    sync_users, sync_customers, sync_orders, sync_products, sync_inspections, sync_settings, create_sheets_service
)
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
    
    # استخدام كاش لحالة الاتصال لتقليل استدعاءات Google Sheets API
    connection_status = False
    connection_status_cache_key = f'google_sync_connection_status_{config.id if config else "none"}'
    
    # محاولة الحصول على الحالة من الكاش
    from django.core.cache import cache
    cached_status = cache.get(connection_status_cache_key)
    
    if cached_status is not None:
        connection_status = cached_status
    else:
        if config:
            try:
                credentials = config.get_credentials()
                if credentials:
                    sheets_service = create_sheets_service(credentials)
                    if sheets_service:
                        sheets_service.spreadsheets().get(spreadsheetId=config.spreadsheet_id).execute()
                        connection_status = True
            except Exception as e:
                logger.error(f"فشل اختبار الاتصال: {str(e)}")
        # تخزين الحالة في الكاش لمدة 10 دقائق
        cache.set(connection_status_cache_key, connection_status, 600)
    
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
            return redirect('odoo_db_manager:google_sync')
        
        # الحصول على بيانات الاعتماد
        credentials = config.get_credentials()
        
        if not credentials:
            # إضافة رسالة خطأ
            messages.error(request, 'لا يمكن قراءة بيانات الاعتماد')
            return redirect('odoo_db_manager:google_sync')

        # اختبار الاتصال باستخدام حساب الخدمة
        sheets_service = create_sheets_service(credentials)
        if not sheets_service:
            messages.error(request, f"فشل إنشاء خدمة Google Sheets. تحقق من صحة بيانات الاعتماد ومشاركة جدول البيانات مع البريد: {credentials.get('client_email', 'غير معروف')}")
            return redirect('odoo_db_manager:google_sync')

        # محاولة الوصول إلى جدول البيانات
        spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=config.spreadsheet_id).execute()
        
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
    """حذف سجلات المزامنة القديمة وإنشاء سجل جديد"""
    config = GoogleSyncConfig.get_active_config()
    if not config:
        messages.error(request, 'لا يوجد إعداد مزامنة نشط')
        return redirect('odoo_db_manager:google_sync')
    
    with transaction.atomic():
        GoogleSyncLog.objects.filter(config=config).delete()
        GoogleSyncLog.objects.create(
            config=config,
            status='info',
            message='تم حذف سجلات المزامنة القديمة. سجل جديد تم إنشاؤه.'
        )
    messages.success(request, 'تم حذف سجلات المزامنة القديمة وإنشاء سجل جديد')
    return redirect('odoo_db_manager:google_sync')


from django.db import transaction

def sync_with_google_sheets(config_id=None, manual=False):
    try:
        if config_id:
            config = GoogleSyncConfig.objects.get(id=config_id)
        else:
            config = GoogleSyncConfig.get_active_config()
        
        if not config:
            message = "لا يوجد إعداد مزامنة نشط"
            logger.error(message)
            return {'status': 'error', 'message': message}

        if not manual and not config.is_sync_due():
            message = f"لم يحن وقت المزامنة بعد. آخر مزامنة: {config.last_sync}"
            logger.info(message)
            return {'status': 'info', 'message': message}
        
        credentials = config.get_credentials()
        if not credentials:
            message = "فشل قراءة بيانات الاعتماد. تأكد من تحميل ملف اعتماد حساب خدمة صالح."
            logger.error(message)
            GoogleSyncLog.objects.create(
                config=config,
                status='error',
                message=message
            )
            return {'status': 'error', 'message': message}
        
        sheets_service = create_sheets_service(credentials)
        if not sheets_service:
            message = f"فشل إنشاء خدمة Google Sheets. تحقق من صحة بيانات الاعتماد ومشاركة جدول البيانات مع البريد: {credentials.get('client_email', 'غير معروف')}"
            logger.error(message)
            GoogleSyncLog.objects.create(
                config=config,
                status='error',
                message=message
            )
            return {'status': 'error', 'message': message}
        
        try:
            sheets_service.spreadsheets().get(spreadsheetId=config.spreadsheet_id).execute()
        except Exception as e:
            message = f"فشل الوصول إلى جدول البيانات. تأكد من صحة المعرف ومشاركة الجدول مع حساب الخدمة."
            logger.error(f"{message}: {str(e)}")
            GoogleSyncLog.objects.create(
                config=config,
                status='error',
                message=message
            )
            return {'status': 'error', 'message': message}
        
        sync_results = {}
        
        if config.sync_databases:
            db_result = sync_databases(sheets_service, config.spreadsheet_id)
            sync_results['databases'] = db_result
        
        if config.sync_users:
            users_result = sync_users(sheets_service, config.spreadsheet_id)
            sync_results['users'] = users_result
        
        if config.sync_customers:
            customers_result = sync_customers(sheets_service, config.spreadsheet_id)
            sync_results['customers'] = customers_result
        
        if config.sync_orders:
            orders_result = sync_orders(sheets_service, config.spreadsheet_id)
            sync_results['orders'] = orders_result
        
        if config.sync_products:
            products_result = sync_products(sheets_service, config.spreadsheet_id)
            sync_results['products'] = products_result
        
        if config.sync_inspections:
            inspections_result = sync_inspections(sheets_service, config.spreadsheet_id)
            sync_results['inspections'] = inspections_result
        
        if config.sync_settings:
            settings_result = sync_settings(sheets_service, config.spreadsheet_id)
            sync_results['settings'] = settings_result
        
        config.update_last_sync()
        
        message = "تمت المزامنة مع Google Sheets بنجاح"
        logger.info(message)
        GoogleSyncLog.objects.create(
            config=config,
            status='success',
            message=message,
            details=sync_results
        )
        
        return {'status': 'success', 'message': message}
    except Exception as e:
        message = f"حدث خطأ أثناء المزامنة: {str(e)}"
        logger.error(message)
        GoogleSyncLog.objects.create(
            config=config,
            status='error',
            message=message
        )
        return {'status': 'error', 'message': message}


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
        logger.error(f"فشل حفظ الإعدادات المتقدمة: {str(e)}")
        
        # إرجاع استجابة خطأ
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
@user_passes_test(is_staff_or_superuser)
def google_sync_logs_api(request):
    """API لإرجاع بيانات سجل المزامنة بصيغة JSON"""
    logs = GoogleSyncLog.objects.all().order_by('-created_at')[:50]
    logs_data = []
    for log in logs:
        details = ''
        if log.details:
            try:
                import json
                details = json.dumps(log.details, indent=2, ensure_ascii=False)
            except Exception:
                details = str(log.details)
        logs_data.append({
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': log.get_status_display(),
            'message': log.message,
            'details': details
        })
    return JsonResponse({'logs': logs_data})