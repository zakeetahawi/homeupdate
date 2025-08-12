"""
وجهات نظر إدارة قواعد البيانات على طراز أودو
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse, FileResponse, StreamingHttpResponse
from django.utils import timezone
from django.conf import settings
import os
import time
import shutil
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import secrets
from django.core.cache import cache
from django.contrib.auth import get_user_model

from .models import (
    Database, BackupSchedule,
    GoogleDriveConfig, RestoreProgress
)
from .services.database_service import DatabaseService
from .services.scheduled_backup_service import scheduled_backup_service
from .forms import BackupScheduleForm, GoogleDriveConfigForm, DatabaseForm


def is_staff_or_superuser(user):
    """التحقق من أن المستخدم موظف أو مدير"""
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_staff_or_superuser)
def dashboard(request):
    """عرض لوحة التحكم الرئيسية"""
    # تحديث حالة الاتصال لجميع قواعد البيانات
    database_service = DatabaseService()
    databases = Database.objects.all().order_by('-is_active', '-created_at')

    # تحديث حالة الاتصال لكل قاعدة بيانات
    for db in databases:
        try:
            success, message = database_service.test_connection(db.connection_info)
            db.status = success
            if not success:
                db.error_message = message
            else:
                db.error_message = ""
            db.save()
        except Exception as e:
            db.status = False
            db.error_message = str(e)
            db.save()

    # محاولة اكتشاف قواعد البيانات الموجودة في PostgreSQL
    try:
        discovered_databases = database_service.discover_postgresql_databases()
        # سنعرض هذه في context لإظهارها للمستخدم
    except Exception as e:
        discovered_databases = []
        print(f"خطأ في اكتشاف قواعد البيانات: {e}")

    # تم حذف النسخ الاحتياطية القديمة - استخدم backup_system بدلاً من ذلك
    backups = []
    total_size_display = "0 B"

    # تم حذف النسخ الاحتياطية القديمة - استخدم backup_system بدلاً من ذلك
    last_backup = None

    # التحقق من وجود رسالة نجاح لتنشيط قاعدة البيانات
    show_activation_success = request.session.pop('show_db_activation_success', False)
    activated_db_name = request.session.pop('activated_db_name', '')
    created_default_user = request.session.pop('created_default_user', False)

    # الحصول على معلومات قاعدة البيانات الحالية من إعدادات Django
    from django.conf import settings
    current_db_name = settings.DATABASES['default']['NAME']
    current_db_user = settings.DATABASES['default']['USER']
    current_db_host = settings.DATABASES['default']['HOST']
    current_db_port = settings.DATABASES['default']['PORT']
    current_db_password = settings.DATABASES['default']['PASSWORD']

    # البحث عن قاعدة البيانات الحالية في قائمة قواعد البيانات
    current_database = None
    for db in databases:
        if db.connection_info.get('NAME') == current_db_name:
            current_database = db
            break

    # إذا لم يتم العثور على قاعدة البيانات الحالية، نقوم بإنشائها
    if not current_database:
        try:
            # إنشاء قاعدة بيانات جديدة للقاعدة الحالية
            current_database = Database(
                name=f"قاعدة البيانات الحالية ({current_db_name})",
                db_type='postgresql',
                connection_info={
                    'ENGINE': 'django.db.backends.postgresql',
                    'NAME': current_db_name,
                    'USER': current_db_user,
                    'PASSWORD': current_db_password,
                    'HOST': current_db_host,
                    'PORT': current_db_port,
                }
            )
            current_database.save()
            print(f"تم إنشاء قاعدة البيانات الحالية: {current_db_name}")
        except Exception as e:
            print(f"حدث خطأ أثناء إنشاء قاعدة البيانات الحالية: {str(e)}")

    # الحصول على قاعدة البيانات النشطة
    active_database = databases.filter(is_active=True).first()

    # إذا كانت قاعدة البيانات الحالية موجودة ولكنها غير نشطة، نقوم بتنشيطها
    if current_database and not current_database.is_active:
        # تعطيل جميع قواعد البيانات الأخرى
        Database.objects.exclude(id=current_database.id).update(is_active=False)
        # تنشيط قاعدة البيانات الحالية
        current_database.is_active = True
        current_database.save()
        active_database = current_database
        print(f"تم تنشيط قاعدة البيانات الحالية: {current_db_name}")

    # التحقق من حالة الاتصال بقاعدة البيانات الحالية
    current_db_status = False
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname=current_db_name,
            user=current_db_user,
            password=current_db_password,
            host=current_db_host,
            port=current_db_port,
            connect_timeout=3
        )
        conn.close()
        current_db_status = True
    except Exception as e:
        print(f"فشل الاتصال بقاعدة البيانات الحالية: {str(e)}")
        pass

    context = {
        'databases': databases,
        'backups': backups,
        'total_size_display': total_size_display,
        'last_backup': None,  # تم حذف النسخ الاحتياطية القديمة
        'title': _('إدارة قواعد البيانات'),
        'show_activation_success': show_activation_success,
        'activated_db_name': activated_db_name,
        'created_default_user': created_default_user,
        'active_database': active_database,
        'current_db_name': current_db_name,
        'current_db_user': current_db_user,
        'current_db_host': current_db_host,
        'current_db_port': current_db_port,
        'current_db_status': current_db_status,
        'discovered_databases': discovered_databases,  # قواعد البيانات الموجودة في PostgreSQL
    }

    return render(request, 'odoo_db_manager/dashboard.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def database_list(request):
    """عرض قائمة قواعد البيانات"""
    # الحصول على قواعد البيانات
    databases = Database.objects.all().order_by('-is_active', '-created_at')

    # التحقق من وجود رسالة نجاح لتنشيط قاعدة البيانات
    show_activation_success = request.session.pop('show_activation_success', False)
    activated_db_name = request.session.pop('activated_db_name', '')

    context = {
        'databases': databases,
        'title': _('قائمة قواعد البيانات'),
        'show_activation_success': show_activation_success,
        'activated_db_name': activated_db_name,
    }

    return render(request, 'odoo_db_manager/database_list.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def database_discover(request):
    """اكتشاف قواعد البيانات الموجودة في PostgreSQL"""
    if request.method == 'POST':
        try:
            # اكتشاف ومزامنة قواعد البيانات
            database_service = DatabaseService()
            database_service.sync_discovered_databases()

            messages.success(request, _('تم اكتشاف ومزامنة قواعد البيانات بنجاح.'))
        except Exception as e:
            messages.error(request, _(f'حدث خطأ أثناء اكتشاف قواعد البيانات: {str(e)}'))

        return redirect('odoo_db_manager:database_list')

    # عرض قواعد البيانات المكتشفة قبل المزامنة
    try:
        database_service = DatabaseService()
        discovered_dbs = database_service.discover_postgresql_databases()

        # التحقق من قواعد البيانات الموجودة في النظام
        existing_dbs = Database.objects.filter(db_type='postgresql').values_list('name', flat=True)

        # تصنيف قواعد البيانات
        new_dbs = []
        existing_in_system = []

        for db_info in discovered_dbs:
            if db_info['name'] in existing_dbs:
                existing_in_system.append(db_info)
            else:
                new_dbs.append(db_info)

        context = {
            'discovered_dbs': discovered_dbs,
            'new_dbs': new_dbs,
            'existing_in_system': existing_in_system,
            'title': _('اكتشاف قواعد البيانات'),
        }

    except Exception as e:
        messages.error(request, _(f'حدث خطأ أثناء اكتشاف قواعد البيانات: {str(e)}'))
        context = {
            'discovered_dbs': [],
            'new_dbs': [],
            'existing_in_system': [],
            'title': _('اكتشاف قواعد البيانات'),
        }

    return render(request, 'odoo_db_manager/database_discover.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def database_detail(request, pk):
    """عرض تفاصيل قاعدة البيانات"""
    # الحصول على قاعدة البيانات
    database = get_object_or_404(Database, pk=pk)

    # تم حذف النسخ الاحتياطية القديمة - استخدم backup_system بدلاً من ذلك
    backups = []    # التحقق من رسائل نجاح إنشاء قاعدة البيانات
    database_created_success = request.session.pop('database_created_success', False)
    created_database_name = request.session.pop('created_database_name', '')
    default_user_created = request.session.pop('default_user_created', False)
    migrations_applied = request.session.pop('migrations_applied', False)

    context = {
        'database': database,
        'backups': backups,
        'title': _('تفاصيل قاعدة البيانات'),
        'database_created_success': database_created_success,
        'created_database_name': created_database_name,
        'default_user_created': default_user_created,
        'migrations_applied': migrations_applied,
    }

    return render(request, 'odoo_db_manager/database_detail.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
@login_required
@user_passes_test(is_staff_or_superuser)
def database_create(request):
    """إنشاء قاعدة بيانات جديدة"""
    if request.method == 'POST':
        form = DatabaseForm(request.POST)
        if form.is_valid():
            try:                # حفظ قاعدة البيانات من النموذج (بدون إنشاء قاعدة البيانات الفعلية)
                database = form.save(commit=False)

                # إنشاء قاعدة البيانات الفعلية إذا أراد المستخدم ذلك
                force_create = request.POST.get('force_create') == 'on'
                ignore_db_errors = request.POST.get('ignore_db_errors') == 'on'
                create_actual_db = request.POST.get('create_actual_db') == 'on'                  # حفظ السجل أولاً
                database.save()
                  # إنشاء خدمة قاعدة البيانات مرة واحدة
                database_service = DatabaseService()

                if create_actual_db and not ignore_db_errors:
                    # استخدام خدمة إنشاء قواعد البيانات لإنشاء قاعدة البيانات الفعلية
                    try:
                        # إنشاء قاعدة البيانات الفعلية
                        db_created, create_message = database_service.create_physical_database(
                            connection_info=database.connection_info,
                            force_create=force_create
                        )

                        if db_created:
                            # اختبار الاتصال بعد الإنشاء
                            success, test_message = database_service.test_connection(database.connection_info)

                            if success:
                                database.status = True
                                database.error_message = ''
                                database.save()

                                # تطبيق migrations في قاعدة البيانات الجديدة
                                migrations_applied = False
                                try:
                                    migrations_applied = _apply_migrations_to_database(database)
                                except Exception as migrate_error:
                                    print(f"خطأ في تطبيق migrations: {migrate_error}")
                                  # محاولة إنشاء مستخدم افتراضي فقط إذا تم تطبيق migrations
                                default_user_created = False
                                if migrations_applied:
                                    # انتظار قصير لضمان اكتمال migrations
                                    import time
                                    time.sleep(2)

                                    try:
                                        default_user_created = _create_default_user(database)
                                    except Exception as user_error:
                                        print(f"خطأ في إنشاء المستخدم الافتراضي: {user_error}")
                                        # محاولة ثانية بعد انتظار أطول
                                        try:
                                            time.sleep(3)
                                            default_user_created = _create_default_user(database)
                                        except Exception as user_error2:
                                            print(f"فشل في المحاولة الثانية لإنشاء المستخدم الافتراضي: {user_error2}")

                                # حفظ معلومات نجاح الإنشاء في الجلسة لعرضها في SweetAlert
                                request.session['database_created_success'] = True
                                request.session['created_database_name'] = database.name
                                request.session['created_database_id'] = database.id
                                request.session['default_user_created'] = default_user_created
                                request.session['migrations_applied'] = migrations_applied

                                success_msg = f'تم إنشاء قاعدة البيانات في PostgreSQL وتم اختبار الاتصال بنجاح. {create_message}'
                                if migrations_applied:
                                    success_msg += " تم تطبيق migrations."
                                if default_user_created:
                                    success_msg += " تم إنشاء مستخدم افتراضي."

                                messages.success(request, success_msg)
                            else:
                                database.status = False
                                database.error_message = test_message
                                database.save()
                                messages.warning(request, f'تم إنشاء قاعدة البيانات في PostgreSQL ولكن فشل اختبار الاتصال: {test_message}')
                        else:
                            database.status = False
                            database.error_message = create_message
                            database.save()
                            messages.error(request, f'فشل في إنشاء قاعدة البيانات: {create_message}')

                    except Exception as e:
                        database.status = False
                        database.error_message = str(e)
                        database.save()
                        messages.error(request, f'حدث خطأ أثناء إنشاء قاعدة البيانات: {str(e)}')

                elif not create_actual_db and not ignore_db_errors:
                    # فقط اختبار الاتصال بدون إنشاء قاعدة البيانات
                    success, message = database_service.test_connection(database.connection_info)

                    if success:
                        database.status = True
                        database.error_message = ''
                        database.save()
                        messages.success(request, f'تم إنشاء سجل قاعدة البيانات وتم اختبار الاتصال بقاعدة البيانات الموجودة. {message}')
                    else:
                        database.status = False
                        database.error_message = message
                        database.save()
                        messages.warning(request, f'تم إنشاء سجل قاعدة البيانات ولكن فشل اختبار الاتصال: {message}')
                else:
                    # تجاهل اختبار الاتصال
                    messages.warning(request, 'تم إنشاء سجل قاعدة البيانات دون اختبار الاتصال أو إنشاء قاعدة البيانات.')

                return redirect('odoo_db_manager:database_detail', pk=database.pk)

            except Exception as e:
                messages.error(request, _(f'حدث خطأ أثناء إنشاء قاعدة البيانات: {str(e)}'))
        else:
            # إضافة رسائل الأخطاء للمستخدم
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = DatabaseForm()

    context = {
        'title': _('إنشاء قاعدة بيانات جديدة'),
        'form': form,
    }

    return render(request, 'odoo_db_manager/database_form.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def database_activate(request, pk):
    """تنشيط قاعدة بيانات"""
      # التأكد من أن الطلب POST فقط أو AJAX GET
    if request.method == 'GET':
        # إذا كان GET request، إعادة توجيه إلى dashboard مع رسالة
        messages.warning(request, 'يرجى استخدام زر التفعيل من لوحة التحكم.')
        return redirect('odoo_db_manager:dashboard')

    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'طريقة الطلب غير صحيحة. يجب استخدام POST.'
        })

    try:
        # الحصول على قاعدة البيانات
        print(f"محاولة تنشيط قاعدة البيانات بمعرف: {pk}")
        database = get_object_or_404(Database, pk=pk)
        print(f"تم العثور على قاعدة البيانات: {database.name}")

        # تنشيط قاعدة البيانات باستخدام الطريقة الجديدة
        print("بدء عملية تنشيط قاعدة البيانات...")
        activation_result = database.activate()
        print(f"نتيجة التنشيط: {activation_result}")

        if activation_result.get('success', False):
            print("تم تنشيط قاعدة البيانات بنجاح، محاولة إنشاء مستخدم افتراضي...")

            # محاولة إنشاء مستخدم افتراضي إذا لم يكن هناك مستخدمين
            try:
                created_default_user = database.create_default_user()
                print(f"نتيجة إنشاء المستخدم الافتراضي: {created_default_user}")
            except Exception as user_error:
                print(f"خطأ في إنشاء المستخدم الافتراضي: {str(user_error)}")
                created_default_user = False
              # استخدام رسالة نجاح مع معلومات إضافية
            success_message = f'تم تنشيط قاعدة البيانات {database.name} بنجاح.'
            messages.success(request, success_message)

            # لا نحفظ في session لتجنب مشاكل تغيير قاعدة البيانات
            # request.session['show_db_activation_success'] = True
            # request.session['activated_db_name'] = database.name
            # request.session['created_default_user'] = created_default_user

            # إعادة توجيه مع رسالة تطلب إعادة التشغيل
            response_data = {
                'success': True,
                'message': 'تم تنشيط قاعدة البيانات وتطبيق التغييرات بنجاح',
                'database_name': activation_result.get('database_name', database.name),
                'created_default_user': created_default_user,
                'requires_restart': activation_result.get('requires_restart', False)
            }
            print(f"إعادة الاستجابة: {response_data}")

            response = JsonResponse(response_data)
            response['Content-Type'] = 'application/json; charset=utf-8'
            return response
        else:
            error_message = activation_result.get('message', f'حدث خطأ أثناء تنشيط قاعدة البيانات {database.name}.')
            print(f"فشل التنشيط: {error_message}")

            response = JsonResponse({
                'success': False,
                'message': error_message
            })
            response['Content-Type'] = 'application/json; charset=utf-8'
            return response

    except Exception as e:
        print(f"خطأ عام في database_activate: {str(e)}")
        import traceback
        print(f"تفاصيل الخطأ: {traceback.format_exc()}")

        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ أثناء تنشيط قاعدة البيانات: {str(e)}'
        })

@login_required
@user_passes_test(is_staff_or_superuser)
def database_delete(request, pk):
    """حذف قاعدة بيانات"""
    # الحصول على قاعدة البيانات
    database = get_object_or_404(Database, pk=pk)

    if request.method == 'POST':
        try:
            # حذف قاعدة البيانات
            database_service = DatabaseService()
            database_service.delete_database(database.id)

            messages.success(request, _('تم حذف قاعدة البيانات بنجاح.'))
            return redirect('odoo_db_manager:database_list')
        except Exception as e:
            messages.error(request, _(f'حدث خطأ أثناء حذف قاعدة البيانات: {str(e)}'))
            return redirect('odoo_db_manager:database_detail', pk=database.pk)

    context = {
        'database': database,
        'title': _('حذف قاعدة بيانات'),
    }

    return render(request, 'odoo_db_manager/database_delete.html', context)

# تم حذف دوال النسخ الاحتياطي القديمة - استخدم backup_system بدلاً من ذلك

# backup_create, backup_detail, backup_restore, backup_delete, backup_download, backup_upload
# تم نقلها إلى backup_system للحصول على نظام موحد ومحسن














@login_required
@user_passes_test(is_staff_or_superuser)
def schedule_list(request):
    """عرض قائمة جدولة النسخ الاحتياطية"""
    # الحصول على جدولات النسخ الاحتياطية
    schedules = BackupSchedule.objects.all().order_by('-is_active', '-created_at')

    context = {
        'schedules': schedules,
        'title': _('جدولة النسخ الاحتياطية'),
    }

    return render(request, 'odoo_db_manager/schedule_list.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def schedule_detail(request, pk):
    """عرض تفاصيل جدولة النسخة الاحتياطية"""
    # الحصول على جدولة النسخة الاحتياطية
    schedule = get_object_or_404(BackupSchedule, pk=pk)

    # تم حذف النسخ الاحتياطية القديمة - استخدم backup_system بدلاً من ذلك
    backups = []

    context = {
        'schedule': schedule,
        'backups': backups,
        'title': _('تفاصيل جدولة النسخة الاحتياطية'),
    }

    return render(request, 'odoo_db_manager/schedule_detail.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def schedule_create(request, database_id=None):
    """إنشاء جدولة نسخة احتياطية جديدة"""
    # الحصول على قاعدة البيانات
    database = None
    if database_id:
        database = get_object_or_404(Database, pk=database_id)

    if request.method == 'POST':
        form = BackupScheduleForm(request.POST)
        if form.is_valid():
            # إنشاء جدولة النسخة الاحتياطية
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()

            # حساب موعد التشغيل القادم
            schedule.calculate_next_run()

            # إضافة الجدولة إلى المجدول
            scheduled_backup_service.start()
            scheduled_backup_service._schedule_backup(schedule)

            messages.success(request, _('تم إنشاء جدولة النسخة الاحتياطية بنجاح.'))
            return redirect('odoo_db_manager:schedule_detail', pk=schedule.pk)
    else:
        initial_data = {}
        if database:
            initial_data['database'] = database.id
        form = BackupScheduleForm(initial=initial_data)

    context = {
        'form': form,
        'database': database,
        'title': _('إنشاء جدولة نسخة احتياطية جديدة'),
    }

    return render(request, 'odoo_db_manager/schedule_form.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def schedule_update(request, pk):
    """تعديل جدولة نسخة احتياطية"""
    # الحصول على جدولة النسخة الاحتياطية
    schedule = get_object_or_404(BackupSchedule, pk=pk)

    if request.method == 'POST':
        form = BackupScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            # تحديث جدولة النسخة الاحتياطية
            form.save()

            # حساب موعد التشغيل القادم
            schedule.calculate_next_run()

            # تحديث الجدولة في المجدول
            scheduled_backup_service.start()
            scheduled_backup_service._schedule_backup(schedule)

            messages.success(request, _('تم تحديث جدولة النسخة الاحتياطية بنجاح.'))
            return redirect('odoo_db_manager:schedule_detail', pk=schedule.pk)
    else:
        form = BackupScheduleForm(instance=schedule)

    context = {
        'form': form,
        'schedule': schedule,
        'title': _('تعديل جدولة النسخة الاحتياطية'),
    }

    return render(request, 'odoo_db_manager/schedule_form.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def schedule_delete(request, pk):
    """حذف جدولة نسخة احتياطية"""
    # الحصول على جدولة النسخة الاحتياطية
    schedule = get_object_or_404(BackupSchedule, pk=pk)

    if request.method == 'POST':
        # التحقق مما إذا كان المستخدم يريد حذف النسخ الاحتياطية المرتبطة
        delete_backups = request.POST.get('delete_backups') == 'on'

        try:
            # تم حذف النسخ الاحتياطية القديمة - لا حاجة لحذفها
            # استخدم backup_system بدلاً من ذلك

            # حذف الجدولة من المجدول
            job_id = f"backup_{schedule.id}"
            scheduled_backup_service.remove_job(job_id)

            # حذف جدولة النسخة الاحتياطية
            schedule.delete()

            messages.success(request, _('تم حذف جدولة النسخة الاحتياطية بنجاح.'))
            return redirect('odoo_db_manager:schedule_list')
        except Exception as e:
            messages.error(request, _(f'حدث خطأ أثناء حذف جدولة النسخة الاحتياطية: {str(e)}'))
            return redirect('odoo_db_manager:schedule_detail', pk=schedule.pk)

    context = {
        'schedule': schedule,
        'title': _('حذف جدولة النسخة الاحتياطية'),
    }

    return render(request, 'odoo_db_manager/schedule_delete.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def schedule_toggle(request, pk):
    """تنشيط/إيقاف جدولة نسخة احتياطية"""
    # الحصول على جدولة النسخة الاحتياطية
    schedule = get_object_or_404(BackupSchedule, pk=pk)

    # تغيير حالة الجدولة
    schedule.is_active = not schedule.is_active
    schedule.save()

    # تحديث الجدولة في المجدول
    if schedule.is_active:
        scheduled_backup_service.start()
        scheduled_backup_service._schedule_backup(schedule)
        messages.success(request, _('تم تنشيط جدولة النسخة الاحتياطية بنجاح.'))
    else:
        job_id = f"backup_{schedule.id}"
        scheduled_backup_service.remove_job(job_id)
        messages.success(request, _('تم إيقاف جدولة النسخة الاحتياطية بنجاح.'))

    return redirect('odoo_db_manager:schedule_detail', pk=schedule.pk)


@login_required
@user_passes_test(is_staff_or_superuser)
def schedule_run_now(request, pk):
    """تشغيل جدولة نسخة احتياطية الآن"""
    # الحصول على جدولة النسخة الاحتياطية
    schedule = get_object_or_404(BackupSchedule, pk=pk)

    try:
        # تشغيل الجدولة الآن
        backup = scheduled_backup_service.run_job_now(schedule.id)
        if backup:
            messages.success(request, _('تم إنشاء النسخة الاحتياطية بنجاح.'))
        else:
            messages.error(request, _('فشل إنشاء النسخة الاحتياطية.'))
    except Exception as e:
        messages.error(request, _(f'حدث خطأ أثناء إنشاء النسخة الاحتياطية: {str(e)}'))

    return redirect('odoo_db_manager:schedule_detail', pk=schedule.pk)


@login_required
@user_passes_test(is_staff_or_superuser)
def scheduler_status(request):
    """عرض حالة المجدول وإصلاح المشاكل"""
    from .services.scheduled_backup_service import scheduled_backup_service, get_scheduler

    context = {
        'title': _('حالة مجدول النسخ الاحتياطية'),
    }

    try:
        # فحص حالة المجدول
        scheduler = get_scheduler()
        context['scheduler_running'] = scheduler.running if scheduler else False
        context['scheduler_available'] = scheduler is not None

        if scheduler:
            context['scheduler_jobs'] = len(scheduler.get_jobs())
        else:
            context['scheduler_jobs'] = 0

        # فحص الجدولات النشطة
        active_schedules = BackupSchedule.objects.filter(is_active=True)
        context['active_schedules_count'] = active_schedules.count()
        context['active_schedules'] = active_schedules

        # تم حذف النسخ الاحتياطية القديمة - استخدم backup_system بدلاً من ذلك
        context['recent_scheduled_backups'] = []

    except Exception as e:
        context['error'] = str(e)
        messages.error(request, f'خطأ في فحص حالة المجدول: {str(e)}')

    # معالجة الطلبات
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'restart_scheduler':
            try:
                scheduled_backup_service.stop()
                scheduled_backup_service.start()
                messages.success(request, 'تم إعادة تشغيل المجدول بنجاح')
            except Exception as e:
                messages.error(request, f'فشل إعادة تشغيل المجدول: {str(e)}')

        elif action == 'run_manual_backup':
            try:
                from django.core.management import call_command
                call_command('run_scheduled_backups', force=True)
                messages.success(request, 'تم تشغيل النسخ الاحتياطية يدوياً')
            except Exception as e:
                messages.error(request, f'فشل تشغيل النسخ الاحتياطية: {str(e)}')

        return redirect('odoo_db_manager:scheduler_status')

    return render(request, 'odoo_db_manager/scheduler_status.html', context)


def _restore_json_simple(file_path, clear_existing=False):
    """استعادة ملف JSON بطريقة محسنة مع دعم الملفات المضغوطة"""
    import json
    import gzip
    import os
    from django.core import serializers
    from django.apps import apps
    from django.db import transaction

    summary = {
        'total': 0,
        'success': 0,
        'errors': 0,
        'failed_items': []
    }

    try:
        # دعم الملفات المضغوطة والعادية
        print(f"🔄 قراءة ملف الاستعادة: {file_path}")

        if file_path.lower().endswith('.gz'):
            print("📦 فك ضغط ملف .gz...")
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
            print("✅ تم فك ضغط الملف بنجاح")
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        if not isinstance(data, list):
            if isinstance(data, dict):
                if 'private_key' in data and 'client_email' in data and 'project_id' in data:
                    raise ValueError("هذا الملف يبدو وكأنه ملف Google Service Account Credentials وليس نسخة احتياطية للنظام. يرجى رفع ملف نسخة احتياطية صالح بتنسيق Django fixture.")
                elif 'model' in data and 'fields' in data:
                    data = [data]
                elif 'version' in data or 'created_at' in data or 'database' in data:
                    raise ValueError("تنسيق النسخة الاحتياطية غير مدعوم. يرجى استخدام ملف بتنسيق Django fixture (JSON).")
                else:
                    raise ValueError("تنسيق الملف غير صالح. يجب أن يكون ملف JSON يحتوي على قائمة من البيانات أو بيانات Django fixture.")
            else:
                raise ValueError(f"تنسيق البيانات غير مدعوم: {type(data)}. يجب أن تكون البيانات عبارة عن قائمة أو قاموس.")

        summary['total'] = len(data)
        from django.contrib.contenttypes.models import ContentType
        required_content_types = [
            ('inventory', 'product'),
            ('inventory', 'category'),
            ('inventory', 'brand'),
            ('inventory', 'warehouse'),
            ('inventory', 'stocktransaction'),
            ('orders', 'order'),
            ('orders', 'orderitem'),
            ('customers', 'customer'),
            ('customers', 'customernote'),
            ('inspections', 'inspection'),
            ('installations', 'installationschedule'),
            ('reports', 'report'),
            ('accounts', 'department'),
            ('accounts', 'branch'),
        ]
        for app_label, model_name in required_content_types:
            try:
                ContentType.objects.get_or_create(
                    app_label=app_label,
                    model=model_name
                )
            except Exception:
                pass
        priority_order = [
            'contenttypes.contenttype',
            'auth.user',
            'auth.group',
            'accounts.department',
            'accounts.branch',
            'auth.permission',
            'customers.customer',
            'inventory.category',
            'inventory.brand',
            'inventory.warehouse',
            'inventory.product',
            'orders.order',
            'orders.orderitem',
            'inspections.inspection',
            'installations.installationschedule',
            'reports.report',
            'odoo_db_manager.database',
            'odoo_db_manager.backupschedule',
            'odoo_db_manager.importlog',
            'inventory.stocktransaction',
            'customers.customernote',
        ]
        sorted_data = []
        remaining_data = []
        for model_name in priority_order:
            for item in data:
                if item.get('model') == model_name:
                    sorted_data.append(item)
        for item in data:
            if item not in sorted_data:
                remaining_data.append(item)
        final_data = sorted_data + remaining_data
        for item in final_data:
            model_name = item.get('model', 'unknown')
            fields = item.get('fields', {})
            if model_name == 'accounts.systemsettings':
                if 'default_currency' in fields:
                    default_curr = fields.pop('default_currency', 'SAR')
                    fields['currency'] = default_curr
                old_fields = ['timezone', 'date_format', 'time_format']
                for field in old_fields:
                    if field in fields:
                        removed_value = fields.pop(field, None)
                item['fields'] = fields
        if clear_existing:
            models_to_clear = set()
            for item in final_data:
                model_name = item.get('model')
                if model_name:
                    models_to_clear.add(model_name)
            for model_name in reversed(priority_order):
                if model_name in models_to_clear:
                    try:
                        app_label, model_class = model_name.split('.')
                        model = apps.get_model(app_label, model_class)
                        count = model.objects.count()
                        if count > 0:
                            model.objects.all().delete()
                    except Exception as e:
                        pass
        success_count = 0
        error_count = 0
        failed_items = []
        for i, item in enumerate(final_data):
            try:
                with transaction.atomic():
                    for obj in serializers.deserialize('json', json.dumps([item])):
                        obj.save()
                success_count += 1
            except Exception as item_error:
                error_count += 1
                failed_items.append((i, item, str(item_error)))
        if failed_items:
            second_attempt_success = 0
            for original_index, item, original_error in failed_items:
                try:
                    with transaction.atomic():
                        item_copy = item.copy()
                        fields = item_copy.get('fields', {})
                        for obj in serializers.deserialize('json', json.dumps([item_copy])):
                            obj.save()
                    success_count += 1
                    second_attempt_success += 1
                except Exception as second_error:
                    pass
        summary['success'] = success_count
        summary['errors'] = error_count
        summary['failed_items'] = failed_items
        return summary
    except Exception as e:
        raise

def _restore_json_simple_with_progress(file_path, clear_existing=False,
                                       progress_callback=None, session_id=None):
    """
    دالة استعادة محسنة للملفات الكبيرة مع معالجة الذاكرة
    """
    import json
    import gzip
    import os
    from django.core import serializers
    from django.db import transaction
    from django.apps import apps
    from django.contrib.contenttypes.models import ContentType
    
    def update_progress(current_step=None, processed_items=None, success_count=None, error_count=None):
        if progress_callback:
            progress_percentage = 0
            if processed_items is not None and hasattr(update_progress, 'total_items'):
                total_items = update_progress.total_items
                if total_items > 0:
                    progress_percentage = min(100, int((processed_items / total_items) * 100))
            
            progress_callback(
                progress_percentage=progress_percentage,
                current_step=current_step,
                processed_items=processed_items,
                success_count=success_count,
                error_count=error_count
            )
    
    try:
        update_progress(current_step='🔄 بدء عملية الاستعادة المحسنة...')
        
        # التحقق من حجم الملف
        file_size = os.path.getsize(file_path)
        print(f"📊 حجم الملف: {file_size:,} بايت ({file_size/1024/1024:.1f} MB)")
        
        if file_size > 50 * 1024 * 1024:  # أكبر من 50MB
            raise ValueError("الملف كبير جداً (أكبر من 50MB). يرجى استخدام ملف أصغر.")
        
        update_progress(current_step='📖 قراءة الملف بطريقة محسنة...')
        
        # قراءة الملف بطريقة محسنة
        data = None
        if file_path.lower().endswith('.gz'):
            print("📦 فك ضغط ملف .gz...")
            try:
                with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                    # قراءة الملف على دفعات لتجنب استهلاك الذاكرة
                    content = ""
                    chunk_size = 1024 * 1024  # 1MB chunks
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        content += chunk
                        update_progress(current_step=f'📖 قراءة الملف... ({len(content):,} حرف)')
                    
                    data = json.loads(content)
                    del content  # تحرير الذاكرة
                    
            except Exception as e:
                print(f"❌ خطأ في فك ضغط الملف: {e}")
                raise ValueError(f"فشل في فك ضغط الملف: {str(e)}")
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"❌ خطأ في قراءة الملف: {e}")
                raise ValueError(f"فشل في قراءة الملف: {str(e)}")
        
        if not isinstance(data, list):
            if isinstance(data, dict) and 'model' in data and 'fields' in data:
                data = [data]
            else:
                raise ValueError("تنسيق الملف غير صحيح. يجب أن يكون ملف Django fixture صالح.")
        
        total_items = len(data)
        update_progress.total_items = total_items  # حفظ العدد الإجمالي
        update_progress(current_step=f'📊 تم تحليل {total_items} عنصر', processed_items=0)
        
        if progress_callback:
            progress_callback(total_items=total_items)
        
        success_count = 0
        error_count = 0
        
        # معالجة البيانات على دفعات صغيرة
        batch_size = 50  # معالجة 50 عنصر في كل مرة
        
        for i in range(0, total_items, batch_size):
            batch = data[i:i + batch_size]
            batch_start = i + 1
            batch_end = min(i + batch_size, total_items)
            
            update_progress(
                current_step=f'🔄 معالجة الدفعة {batch_start}-{batch_end} من {total_items}',
                processed_items=i
            )
            
            for j, item in enumerate(batch):
                try:
                    with transaction.atomic():
                        for obj in serializers.deserialize('json', json.dumps([item])):
                            obj.save()
                    success_count += 1
                except Exception as item_error:
                    error_count += 1
                    print(f"⚠️ فشل في استعادة العنصر {i + j + 1}: {str(item_error)}")
                
                # تحديث التقدم كل 10 عناصر
                if (i + j + 1) % 10 == 0:
                    update_progress(
                        processed_items=i + j + 1,
                        success_count=success_count,
                        error_count=error_count
                    )
        
        # التحديث النهائي
        update_progress(
            current_step='✅ اكتملت العملية بنجاح',
            processed_items=total_items,
            success_count=success_count,
            error_count=error_count
        )
        
        return {
            'total_count': total_items,
            'success_count': success_count,
            'error_count': error_count
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ خطأ في الاستعادة: {error_msg}")
        update_progress(
            current_step=f'❌ فشلت العملية: {error_msg}',
            error_message=error_msg
        )
        raise

        for item in data:
            if item not in sorted_data:
                remaining_data.append(item)

        final_data = sorted_data + remaining_data

        # تنظيف البيانات القديمة إذا طُلب ذلك
        if clear_existing:
            update_progress(current_step='🗑️ حذف البيانات القديمة بترتيب آمن...')

            # حفظ معلومات سجل التقدم الحالي قبل الحذف
            current_progress_data = None
            try:
                current_progress = RestoreProgress.objects.get(session_id=session_id)
                current_progress_data = {
                    'session_id': current_progress.session_id,
                    'user_id': current_progress.user.id,
                    'database_id': current_progress.database.id,
                    'filename': current_progress.filename,
                    'status': current_progress.status,
                    'progress_percentage': current_progress.progress_percentage,
                    'current_step': current_progress.current_step,
                    'total_items': current_progress.total_items,
                    'processed_items': current_progress.processed_items,
                    'success_count': current_progress.success_count,
                    'error_count': current_progress.error_count,
                    'error_message': current_progress.error_message,
                    'result_data': current_progress.result_data
                }
            except RestoreProgress.DoesNotExist:
                pass

            # قائمة النماذج المحظورة من الحذف
            protected_models = {
                'odoo_db_manager.restoreprogress',
                'sessions.session',
                'auth.user',
                'auth.group',
                'auth.permission',
                'contenttypes.contenttype',
                'admin.logentry',
                'django_apscheduler.djangojob',
                'django_apscheduler.djangojobexecution'
            }

            # جمع النماذج المطلوب حذفها
            models_to_clear = set()
            for item in final_data:
                model_name = item.get('model')
                if model_name and model_name.lower() not in protected_models:
                    models_to_clear.add(model_name)

            # حذف البيانات بترتيب عكسي لتجنب مشاكل المفاتيح الخارجية
            deletion_order = list(reversed(priority_order))
            deleted_models_count = 0
            total_models = len(models_to_clear)

            for model_name in deletion_order:
                if model_name in models_to_clear:
                    try:
                        app_label, model_class = model_name.split('.')
                        model = apps.get_model(app_label, model_class)
                        deleted_count = model.objects.all().delete()[0]
                        deleted_models_count += 1

                        update_progress(
                            current_step=f'🗑️ حذف البيانات القديمة... ({deleted_models_count}/{total_models}) - {model_name}',
                            processed_items=0,
                            success_count=0,
                            error_count=0
                        )

                        print(f"✅ تم حذف {deleted_count} عنصر من {model_name}")
                    except Exception as e:
                        print(f"⚠️ خطأ في حذف بيانات {model_name}: {str(e)}")

            # حذف النماذج المتبقية
            for model_name in models_to_clear:
                if model_name not in deletion_order:
                    try:
                        app_label, model_class = model_name.split('.')
                        model = apps.get_model(app_label, model_class)
                        deleted_count = model.objects.all().delete()[0]
                        deleted_models_count += 1

                        update_progress(
                            current_step=f'🗑️ حذف البيانات المتبقية... ({deleted_models_count}/{total_models}) - {model_name}',
                            processed_items=0,
                            success_count=0,
                            error_count=0
                        )

                        print(f"✅ تم حذف {deleted_count} عنصر من {model_name}")
                    except Exception as e:
                        print(f"⚠️ خطأ في حذف بيانات {model_name}: {str(e)}")

            # إعادة إنشاء سجل التقدم إذا تم حذفه
            if current_progress_data:
                try:
                    RestoreProgress.objects.get(session_id=session_id)
                except RestoreProgress.DoesNotExist:
                    try:
                        from accounts.models import User
                        user = User.objects.get(id=current_progress_data['user_id'])
                        database = Database.objects.get(id=current_progress_data['database_id'])

                        RestoreProgress.objects.create(
                            session_id=current_progress_data['session_id'],
                            user=user,
                            database=database,
                            filename=current_progress_data['filename'],
                            status=current_progress_data['status'],
                            progress_percentage=current_progress_data['progress_percentage'],
                            current_step=current_progress_data['current_step'],
                            total_items=current_progress_data['total_items'],
                            processed_items=current_progress_data['processed_items'],
                            success_count=current_progress_data['success_count'],
                            error_count=current_progress_data['error_count'],
                            error_message=current_progress_data['error_message'],
                            result_data=current_progress_data['result_data']
                        )
                    except Exception as recreate_error:
                        print(f"❌ فشل في إعادة إنشاء سجل التقدم: {str(recreate_error)}")

        # تعطيل فحص المفاتيح الخارجية مؤقتاً (PostgreSQL)
        update_progress(current_step='🔧 تحضير قاعدة البيانات للاستعادة الشاملة...')

        foreign_key_checks_disabled = False
        try:
            with connection.cursor() as cursor:
                # تعطيل فحص المفاتيح الخارجية في PostgreSQL
                cursor.execute("SET session_replication_role = replica;")
                foreign_key_checks_disabled = True
                print("✅ تم تعطيل فحص المفاتيح الخارجية مؤقتاً")
        except Exception as e:
            print(f"⚠️ لم يتم تعطيل فحص المفاتيح الخارجية: {str(e)}")

        # بدء عملية الاستعادة
        update_progress(current_step='🔄 بدء استعادة البيانات الشاملة...', processed_items=0, success_count=0, error_count=0)

        print(f"🚀 بدء عملية الاستعادة الشاملة لـ {total_items} عنصر")

        # استعادة البيانات مع معالجة محسنة للأخطاء
        for idx, item in enumerate(final_data):
            try:
                # تحديث التقدم كل 50 عنصر لتحسين الأداء
                if idx % 50 == 0 or idx == total_items - 1:
                    update_progress(
                        current_step=f'⚙️ معالجة العنصر {idx + 1} من {total_items}...',
                        processed_items=idx + 1,
                        success_count=success_count,
                        error_count=error_count
                    )

                # تنظيف البيانات المشكوك فيها
                model_name = item.get('model', '')
                fields = item.get('fields', {})

                # إصلاح مشاكل البيانات الشائعة
                if model_name == 'accounts.systemsettings':
                    # إصلاح إعدادات النظام
                    if 'default_currency' in fields:
                        default_curr = fields.pop('default_currency', 'SAR')
                        fields['currency'] = default_curr

                    # إزالة الحقول القديمة
                    old_fields = ['timezone', 'date_format', 'time_format']
                    for field in old_fields:
                        if field in fields:
                            fields.pop(field, None)

                    item['fields'] = fields

                # إصلاح مشاكل البيانات المنطقية
                for field_name, field_value in fields.items():
                    if isinstance(field_value, str):
                        if field_value.lower() in ['true', 'false']:
                            fields[field_name] = field_value.lower() == 'true'
                        elif field_value == 'connected':
                            fields[field_name] = True
                        elif field_value == 'disconnected':
                            fields[field_name] = False

                # معالجة خاصة للمفاتيح الخارجية المفقودة
                if model_name == 'customers.customer':
                    # إنشاء تصنيف افتراضي إذا كان مفقود
                    category_id = fields.get('category')
                    if category_id:
                        try:
                            from customers.models import CustomerCategory
                            CustomerCategory.objects.get(id=category_id)
                        except CustomerCategory.DoesNotExist:
                            # إنشاء تصنيف افتراضي
                            default_category = CustomerCategory.objects.create(
                                id=category_id,
                                name=f"تصنيف {category_id}",
                                description="تصنيف تم إنشاؤه تلقائياً أثناء الاستعادة"
                            )
                            print(f"✅ تم إنشاء تصنيف افتراضي: {default_category.name}")

                # محاولة استعادة العنصر
                try:
                    with transaction.atomic():
                        item_json = json.dumps([item])
                        for deserialized_obj in serializers.deserialize('json', item_json):
                            deserialized_obj.save()

                    success_count += 1

                except Exception as item_error:
                    error_count += 1
                    error_msg = str(item_error)
                    failed_items.append({
                        'index': idx + 1,
                        'model': model_name,
                        'error': error_msg[:200] + ('...' if len(error_msg) > 200 else ''),
                        'pk': item.get('pk', 'غير محدد')
                    })

                    # طباعة تفاصيل الأخطاء الأولى فقط
                    if error_count <= 10:
                        print(f"❌ خطأ في العنصر {idx + 1} ({model_name}): {error_msg[:100]}...")

            except Exception as e:
                error_count += 1
                failed_items.append({
                    'index': idx + 1,
                    'model': 'غير محدد',
                    'error': str(e)[:200],
                    'pk': 'غير محدد'
                })

        # إعادة تفعيل فحص المفاتيح الخارجية
        if foreign_key_checks_disabled:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET session_replication_role = DEFAULT;")
                print("✅ تم إعادة تفعيل فحص المفاتيح الخارجية")
            except Exception as e:
                print(f"⚠️ خطأ في إعادة تفعيل فحص المفاتيح الخارجية: {str(e)}")

        # تحديث نهائي
        success_rate = (success_count / total_items * 100) if total_items > 0 else 0
        update_progress(
            current_step=f'✅ اكتملت الاستعادة الشاملة بنسبة {success_rate:.1f}%',
            processed_items=total_items,
            success_count=success_count,
            error_count=error_count
        )

        # طباعة ملخص مفصل
        print(f"\n{'='*60}")
        print(f"📊 ملخص عملية الاستعادة الشاملة:")
        print(f"{'='*60}")
        print(f"📁 الملف: {os.path.basename(file_path)}")
        print(f"📈 إجمالي العناصر: {total_items}")
        print(f"✅ تمت الاستعادة بنجاح: {success_count}")
        print(f"❌ فشلت: {error_count}")
        print(f"📊 نسبة النجاح: {success_rate:.1f}%")

        if failed_items:
            print(f"\n❌ تفاصيل الأخطاء (أول 10 أخطاء):")
            for i, error in enumerate(failed_items[:10], 1):
                print(f"  {i}. العنصر {error['index']} ({error['model']} - PK: {error['pk']})")
                print(f"     الخطأ: {error['error']}")

        print(f"{'='*60}")

        # إنشاء تقرير مفصل
        detailed_report = {
            'total_items': total_items,
            'success_count': success_count,
            'error_count': error_count,
            'success_rate': success_rate,
            'filename': os.path.basename(file_path),
            'errors': failed_items[:20],  # أول 20 خطأ
            'summary': f"تم استعادة {success_count} من {total_items} عنصر بنسبة نجاح {success_rate:.1f}%",
            'is_comprehensive': True,
            'foreign_keys_handled': True
        }

        return detailed_report

    except Exception as e:
        error_msg = f'❌ خطأ في عملية الاستعادة الشاملة: {str(e)}'
        update_progress(current_step=error_msg)
        print(f"\n{error_msg}")

        # إعادة تفعيل فحص المفاتيح الخارجية في حالة الخطأ
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET session_replication_role = DEFAULT;")
        except:
            pass

        raise e


# ==================== عروض Google Drive ====================

@login_required
@user_passes_test(is_staff_or_superuser)
def google_drive_settings(request):
    """إدارة إعدادات Google Drive"""
    # الحصول على الإعدادات الحالية أو إنشاء جديدة
    config = GoogleDriveConfig.get_active_config()

    if request.method == 'POST':
        form = GoogleDriveConfigForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            config = form.save(commit=False)
            config.created_by = request.user
            config.save()

            messages.success(request, _('تم حفظ إعدادات Google Drive بنجاح.'))
            return redirect('odoo_db_manager:google_drive_settings')
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج.'))
    else:
        form = GoogleDriveConfigForm(instance=config)

    context = {
        'form': form,
        'config': config,
        'title': _('إعدادات Google Drive'),
    }

    return render(request, 'odoo_db_manager/google_drive_settings.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def google_drive_test_connection(request):
    """اختبار الاتصال مع Google Drive"""
    if request.method == 'POST':
        try:
            from inspections.services.google_drive_service import get_google_drive_service

            # الحصول على خدمة Google Drive
            drive_service = get_google_drive_service()

            if not drive_service:
                return JsonResponse({
                    'success': False,
                    'message': 'فشل في تهيئة خدمة Google Drive'
                })

            # اختبار الاتصال
            result = drive_service.test_connection()

            if result['success']:
                messages.success(request, result['message'])
            else:
                messages.error(request, result['message'])

            return JsonResponse(result)

        except Exception as e:
            error_message = f'خطأ في اختبار الاتصال: {str(e)}'
            messages.error(request, error_message)
            return JsonResponse({
                'success': False,
                'message': error_message
            })

    return JsonResponse({
        'success': False,
        'message': 'طريقة الطلب غير صحيحة'
    })


@login_required
@user_passes_test(is_staff_or_superuser)
def google_drive_create_test_folder(request):
    """إنشاء مجلد تجريبي في Google Drive"""
    if request.method == 'POST':
        try:
            from inspections.services.google_drive_service import create_test_folder

            # إنشاء مجلد تجريبي
            result = create_test_folder()

            if result:
                messages.success(request, f'تم إنشاء مجلد تجريبي بنجاح: {result["name"]}')
                return JsonResponse({
                    'success': True,
                    'message': f'تم إنشاء مجلد تجريبي بنجاح',
                    'folder': result
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'فشل في إنشاء المجلد التجريبي'
                })

        except Exception as e:
            error_message = f'خطأ في إنشاء المجلد التجريبي: {str(e)}'
            messages.error(request, error_message)
            return JsonResponse({
                'success': False,
                'message': error_message
            })

    return JsonResponse({
        'success': False,
        'message': 'طريقة الطلب غير صحيحة'
    })


@login_required
@user_passes_test(is_staff_or_superuser)
def google_drive_test_file_upload(request):
    """اختبار رفع ملف تجريبي إلى المجلد المحدد"""
    if request.method == 'POST':
        try:
            from inspections.services.google_drive_service import test_file_upload_to_folder

            # اختبار رفع ملف
            result = test_file_upload_to_folder()

            if result and result.get('success'):
                messages.success(request, 'تم اختبار رفع الملف بنجاح')
                return JsonResponse({
                    'success': True,
                    'message': result.get('message'),
                    'details': {
                        'file_name': result.get('file_name'),
                        'folder_id': result.get('folder_id')
                    }
                })
            else:
                error_message = result.get('message') if result else 'فشل في اختبار رفع الملف'
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })

        except Exception as e:
            error_message = f'خطأ في اختبار رفع الملف: {str(e)}'
            messages.error(request, error_message)
            return JsonResponse({
                'success': False,
                'message': error_message
            })

    return JsonResponse({
        'success': False,
        'message': 'طريقة الطلب غير صحيحة'
    })


@login_required
@user_passes_test(is_staff_or_superuser)
def google_drive_test_contract_upload(request):
    """اختبار رفع ملف عقد تجريبي إلى المجلد المحدد"""
    if request.method == 'POST':
        try:
            from orders.services.google_drive_service import test_contract_file_upload_to_folder

            # اختبار رفع ملف عقد
            result = test_contract_file_upload_to_folder()

            if result and result.get('success'):
                messages.success(request, 'تم اختبار رفع ملف العقد بنجاح')
                return JsonResponse({
                    'success': True,
                    'message': result.get('message'),
                    'details': {
                        'file_name': result.get('file_name'),
                        'folder_id': result.get('folder_id')
                    }
                })
            else:
                error_message = result.get('message') if result else 'فشل في اختبار رفع ملف العقد'
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })

        except Exception as e:
            error_message = f'خطأ في اختبار رفع ملف العقد: {str(e)}'
            messages.error(request, error_message)
            return JsonResponse({
                'success': False,
                'message': error_message
            })

    return JsonResponse({
        'success': False,
        'message': 'طريقة الطلب غير صحيحة'
    })

@login_required
@user_passes_test(is_staff_or_superuser)
def database_register(request):
    """تسجيل قاعدة بيانات مكتشفة في النظام"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            db_name = data.get('name')

            if not db_name:
                return JsonResponse({'success': False, 'message': 'اسم قاعدة البيانات مطلوب'})

            # التحقق من عدم وجود قاعدة البيانات مسبقاً
            if Database.objects.filter(name=db_name).exists():
                return JsonResponse({'success': False, 'message': 'قاعدة البيانات مسجلة بالفعل'})

            # الحصول على معلومات الاتصال الافتراضية من Django settings
            from django.conf import settings
            default_db = settings.DATABASES['default']

            # إنشاء معلومات الاتصال
            connection_info = {
                'ENGINE': 'django.db.backends.postgresql',
                'HOST': default_db.get('HOST', 'localhost'),
                'PORT': default_db.get('PORT', '5432'),
                'USER': default_db.get('USER', 'postgres'),
                'PASSWORD': default_db.get('PASSWORD', ''),
                'NAME': db_name,
            }

            # إنشاء سجل قاعدة البيانات
            database = Database.objects.create(
                name=db_name,
                db_type='postgresql',
                connection_info=connection_info,
                status=True,  # نفترض أنها متاحة لأنها مكتشفة
            )

            return JsonResponse({
                'success': True,
                'message': f'تم تسجيل قاعدة البيانات "{db_name}" بنجاح',
                'database_id': database.id
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'حدث خطأ: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'طريقة غير مسموحة'})

@login_required
@user_passes_test(is_staff_or_superuser)
def database_refresh_status(request):
    """تحديث حالة الاتصال لجميع قواعد البيانات"""
    if request.method == 'POST':
        try:
            database_service = DatabaseService()
            databases = Database.objects.all()
            updated_count = 0

            for db in databases:
                try:
                    success, message = database_service.test_connection(db.connection_info)
                    if db.status != success:
                        db.status = success
                        db.error_message = message if not success else ""
                        db.save()
                        updated_count += 1
                except Exception as e:
                    if db.status != False:
                        db.status = False
                        db.error_message = str(e)
                        db.save()
                        updated_count += 1

            return JsonResponse({
                'success': True,
                'message': f'تم تحديث حالة {updated_count} قاعدة بيانات',
                'updated_count': updated_count
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'طريقة غير مسموحة'})


def _create_default_user(database):
    """إنشاء مستخدم افتراضي في قاعدة البيانات الجديدة"""
    try:
        import psycopg2
        from django.contrib.auth.hashers import make_password

        # الاتصال بقاعدة البيانات الجديدة
        conn = psycopg2.connect(
            dbname=database.connection_info.get('NAME'),
            user=database.connection_info.get('USER'),
            password=database.connection_info.get('PASSWORD'),
            host=database.connection_info.get('HOST', 'localhost'),
            port=database.connection_info.get('PORT', '5432')
        )
        conn.autocommit = True
        cursor = conn.cursor()
          # التحقق من وجود جدول المستخدمين
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'accounts_user'
            );
        """)

        table_exists = cursor.fetchone()
        if not table_exists or not table_exists[0]:
            print("جدول المستخدمين غير موجود في قاعدة البيانات الجديدة")
            cursor.close()
            conn.close()
            return False

        # التحقق من عدد الأعمدة في الجدول للتأكد من اكتمال الـ migrations
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'accounts_user'
        """)

        column_count = cursor.fetchone()
        if not column_count or column_count[0] < 10:  # نتوقع على الأقل 10 أعمدة
            print("جدول المستخدمين غير مكتمل، migrations لم تطبق بالكامل")
            cursor.close()
            conn.close()
            return False

        # التحقق من عدم وجود مستخدم admin مسبقاً
        cursor.execute("SELECT COUNT(*) FROM accounts_user WHERE username = %s", ('admin',))
        admin_result = cursor.fetchone()
        admin_exists = admin_result and admin_result[0] > 0

        if admin_exists:
            print("المستخدم admin موجود بالفعل")
            cursor.close()
            conn.close()
            return False

        # إنشاء كلمة مرور مُشفرة
        hashed_password = make_password('admin123')
          # إدراج المستخدم الجديد
        cursor.execute("""
            INSERT INTO accounts_user (
                username, password, email, first_name, last_name,
                is_staff, is_active, is_superuser, date_joined
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, ('admin', hashed_password, 'admin@example.com', 'مدير', 'النظام',
              True, True, True, timezone.now()))
        conn.commit()
        cursor.close()
        conn.close()

        print("تم إنشاء المستخدم admin بنجاح")
        return True

    except Exception as e:
        print(f"خطأ في إنشاء المستخدم admin: {str(e)}")
        return False


def _apply_migrations_to_database(database):
    try:
        import subprocess
        import os
        from django.conf import settings

        # إنشاء DATABASE_URL للقاعة الجديدة
        conn_info = database.connection_info
        database_url = f"postgres://{conn_info.get('USER')}:{conn_info.get('PASSWORD')}@{conn_info.get('HOST', 'localhost')}:{conn_info.get('PORT', '5432')}/{conn_info.get('NAME')}"

        # تطبيق migrations في قاعدة البيانات الجديدة
        env = os.environ.copy()
        env['DATABASE_URL'] = database_url
          # تشغيل migrate command مع تجاهل أخطاء django_apscheduler
        migrate_cmd = [
            'python', 'manage.py', 'migrate', '--fake-initial'
        ]

        result = subprocess.run(
            migrate_cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            cwd=settings.BASE_DIR        )

        if result.returncode == 0:
            print(f"تم تطبيق migrations في قاعدة البيانات {database.name} بنجاح")
            return True
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            print(f"فشل في تطبيق migrations: {error_msg}")
            # التحقق إذا كان الخطأ متعلق بـ django_apscheduler فقط
            if 'django_apscheduler' in error_msg and 'column' in error_msg and 'does not exist' in error_msg:
                print("خطأ django_apscheduler - سيتم تجاهله")
                return True  # نعتبر العملية ناجحة رغم خطأ django_apscheduler
            return False

    except Exception as e:
        print(f"خطأ في تطبيق migrations: {str(e)}")
        return False

@login_required
@user_passes_test(is_staff_or_superuser)
def restore_progress_stream(request, session_id):
    """Server-Sent Events endpoint لإرسال تحديثات التقدم"""

    def event_stream():
        """دالة لإرسال تحديثات التقدم"""
        last_update = None

        while True:
            try:
                # الحصول على تحديث التقدم
                progress = RestoreProgress.objects.filter(session_id=session_id).first()

                if not progress:
                    # إرسال رسالة خطأ وإنهاء الاتصال
                    yield f"data: {json.dumps({'error': 'الجلسة غير موجودة'})}\n\n"
                    break

                # التحقق من وجود تحديث جديد
                if last_update is None or progress.updated_at > last_update:
                    last_update = progress.updated_at

                    # إعداد البيانات للإرسال
                    data = {
                        'status': progress.status,
                        'progress_percentage': progress.progress_percentage,
                        'current_step': progress.current_step,
                        'total_items': progress.total_items,
                        'processed_items': progress.processed_items,
                        'success_count': progress.success_count,
                        'error_count': progress.error_count,
                        'error_message': progress.error_message,
                        'result_data': progress.result_data,
                        'updated_at': progress.updated_at.isoformat()
                    }

                    yield f"data: {json.dumps(data)}\n\n"

                    # إنهاء الاتصال إذا انتهت العملية
                    if progress.status in ['completed', 'failed']:
                        break

                # انتظار قبل التحقق مرة أخرى
                time.sleep(1)

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    response['Access-Control-Allow-Origin'] = '*'
    return response


@csrf_exempt
def restore_progress_status(request, session_id):
    """
    الحصول على حالة تقدم الاستعادة عبر AJAX
    """
    print(f"🔍 [DEBUG] restore_progress_status called for session: {session_id}")

    try:
        # البحث عن جلسة الاستعادة أولاً
        progress = RestoreProgress.objects.filter(session_id=session_id).first()

        if not progress:
            print(f"❌ [DEBUG] Progress not found for session: {session_id}")
            return JsonResponse({'error': 'الجلسة غير موجودة'}, status=404)

        print(f"✅ [DEBUG] Progress found for session: {session_id}")
        print(f"✅ [DEBUG] Progress status: {progress.status} - {progress.progress_percentage}%")

        # إعداد البيانات للإرسال
        data = {
            'status': progress.status,
            'progress_percentage': progress.progress_percentage,
            'current_step': progress.current_step,
            'total_items': progress.total_items,
            'processed_items': progress.processed_items,
            'success_count': progress.success_count,
            'error_count': progress.error_count,
            'error_message': progress.error_message,
            'result_data': progress.result_data,
            'updated_at': progress.updated_at.isoformat(),
            'session_valid': True
        }

        return JsonResponse(data)

    except Exception as e:
        print(f"❌ [DEBUG] Error in restore_progress_status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_temp_token(request):
    """إنشاء رمز مؤقت للعمليات الطويلة"""
    try:
        print(f"🔍 [DEBUG] generate_temp_token called")
        print(f"🔍 [DEBUG] User authenticated: {request.user.is_authenticated}")
        print(f"🔍 [DEBUG] User: {request.user}")
        print(f"🔍 [DEBUG] User is_staff: {getattr(request.user, 'is_staff', False)}")
        print(f"🔍 [DEBUG] User is_superuser: {getattr(request.user, 'is_superuser', False)}")

        # التحقق من تسجيل الدخول
        if not request.user.is_authenticated:
            print("❌ [DEBUG] User not authenticated")
            return JsonResponse({'error': 'يجب تسجيل الدخول أولاً'}, status=401)

        if not (request.user.is_staff or request.user.is_superuser):
            print("❌ [DEBUG] User not staff or superuser")
            return JsonResponse({
                'error': 'ليس لديك صلاحية للقيام بهذا الإجراء'
            }, status=403)

        # إنشاء رمز مميز
        temp_token = secrets.token_urlsafe(32)
        cache.set(f'temp_token_{temp_token}', request.user.id, 10800)  # 3 ساعات

        print(f"✅ [DEBUG] Generated temp token: {temp_token[:10]}...")
        return JsonResponse({'temp_token': temp_token})

    except Exception as e:
        print(f"❌ [DEBUG] Error in generate_temp_token: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def refresh_session(request):
    """
    تجديد جلسة المستخدم باستخدام رمز مؤقت.
    """
    try:
        print(f"🔍 [DEBUG] refresh_session called")
        print(f"🔍 [DEBUG] Request method: {request.method}")
        print(f"🔍 [DEBUG] Request path: {request.path}")
        print(f"🔍 [DEBUG] Request body: {request.body}")

        data = json.loads(request.body)
        temp_token = data.get('temp_token')
        print(f"🔍 [DEBUG] temp_token received: {temp_token[:10] if temp_token else 'None'}...")

        if not temp_token:
            return JsonResponse({
                'success': False,
                'message': 'الرمز المؤقت مفقود'
            }, status=400)

        # التحقق من الرمز المؤقت
        user_id = cache.get(f'temp_token_{temp_token}')
        print(f"🔍 [DEBUG] user_id from cache: {user_id}")
        if not user_id:
            print(f"❌ [DEBUG] temp_token not found in cache")
            return JsonResponse({
                'success': False,
                'message': 'الرمز المؤقت غير صالح أو منتهي الصلاحية'
            }, status=403)

        try:
            user = get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            # المستخدم قد يكون محذوف أثناء عملية الاستعادة
            # في هذه الحالة، نسمح بالمتابعة بدون مستخدم فعلي
            user = None

        # لا تقم بتسجيل الدخول هنا، لتجنب التعارض مع عملية الاستعادة
        # login(request, user)

        # إنشاء رمز API جديد للاستخدام المتعدد
        api_token = secrets.token_urlsafe(32)
        # استخدام user_id بدلاً من user.id لتجنب خطأ NoneType
        cache.set(f'progress_api_token_{api_token}', user_id, timeout=300) # صالح لمدة 5 دقائق

        return JsonResponse({
            'success': True,
            'message': 'تم تجديد الجلسة بنجاح',
            'api_token': api_token  # إرجاع الرمز الجديد
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
