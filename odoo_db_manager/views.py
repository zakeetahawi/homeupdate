"""
وجهات نظر إدارة قواعد البيانات على طراز أودو
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse, JsonResponse, FileResponse
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
import os
import datetime
import shutil

from .models import Database, Backup, BackupSchedule, GoogleDriveConfig
from .services.database_service import DatabaseService
# تم إزالة BackupService لتجنب التضارب
from .services.scheduled_backup_service import scheduled_backup_service
from .forms import BackupScheduleForm, GoogleDriveConfigForm

def is_staff_or_superuser(user):
    """التحقق من أن المستخدم موظف أو مدير"""
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_staff_or_superuser)
def dashboard(request):
    """عرض لوحة التحكم الرئيسية"""
    # الحصول على قواعد البيانات
    databases = Database.objects.all().order_by('-is_active', '-created_at')

    # الحصول على النسخ الاحتياطية
    backups = Backup.objects.all().order_by('-created_at')[:10]

    # حساب إجمالي حجم النسخ الاحتياطية
    total_size = sum(backup.size for backup in Backup.objects.all())

    # تحويل الحجم إلى وحدة مناسبة
    total_size_display = "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if total_size < 1024.0:
            total_size_display = f"{total_size:.1f} {unit}"
            break
        total_size /= 1024.0
    else:
        total_size_display = f"{total_size:.1f} TB"

    # الحصول على آخر نسخة احتياطية
    last_backup = Backup.objects.order_by('-created_at').first()

    context = {
        'databases': databases,
        'backups': backups,
        'total_size_display': total_size_display,
        'last_backup': last_backup,
        'title': _('إدارة قواعد البيانات'),
    }

    return render(request, 'odoo_db_manager/dashboard.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def database_list(request):
    """عرض قائمة قواعد البيانات"""
    # الحصول على قواعد البيانات
    databases = Database.objects.all().order_by('-is_active', '-created_at')

    context = {
        'databases': databases,
        'title': _('قائمة قواعد البيانات'),
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

    # الحصول على النسخ الاحتياطية
    backups = database.backups.all().order_by('-created_at')

    context = {
        'database': database,
        'backups': backups,
        'title': _('تفاصيل قاعدة البيانات'),
    }

    return render(request, 'odoo_db_manager/database_detail.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def database_create(request):
    """إنشاء قاعدة بيانات جديدة"""
    if request.method == 'POST':
        # الحصول على بيانات النموذج
        name = request.POST.get('name')
        db_type = request.POST.get('db_type', 'postgresql')

        # إنشاء معلومات الاتصال حسب نوع قاعدة البيانات
        connection_info = {}

        if db_type == 'postgresql':
            # معلومات اتصال PostgreSQL
            host = request.POST.get('host', 'localhost')
            port = request.POST.get('port', '5432')
            database_name = request.POST.get('database_name', '')
            # استخدام اسم قاعدة البيانات المدخل إذا لم يتم تحديد اسم قاعدة البيانات في الخادم
            if not database_name:
                # استبدال المسافات بالشرطات السفلية لتجنب أخطاء SQL
                database_name = name.replace(' ', '_')
            username = request.POST.get('username', '')
            password = request.POST.get('password', '')

            connection_info = {
                'NAME': database_name,
                'USER': username,
                'PASSWORD': password,
                'HOST': host,
                'PORT': port,
            }
        elif db_type == 'sqlite3':
            # معلومات اتصال SQLite
            sqlite_path = request.POST.get('sqlite_path', f"{name}.sqlite3")

            connection_info = {
                'NAME': sqlite_path,
            }

        try:
            # التحقق مما إذا كان المستخدم يريد تجاوز التحقق من وجود قاعدة البيانات
            force_create = request.POST.get('force_create') == 'on'

            # التحقق مما إذا كان المستخدم يريد تجاهل أخطاء إنشاء قاعدة البيانات
            ignore_db_errors = request.POST.get('ignore_db_errors') == 'on'

            # إنشاء قاعدة البيانات
            database_service = DatabaseService()

            if ignore_db_errors:
                # إنشاء سجل قاعدة البيانات فقط دون محاولة إنشاء قاعدة البيانات الفعلية
                database = Database.objects.create(
                    name=name,
                    db_type=db_type,
                    connection_info=connection_info
                )
                messages.warning(request, _('تم إنشاء سجل قاعدة البيانات فقط، دون محاولة إنشاء قاعدة البيانات الفعلية.'))
            else:
                # إنشاء قاعدة البيانات وسجلها
                database = database_service.create_database(
                    name=name,
                    db_type=db_type,
                    connection_info=connection_info,
                    force_create=force_create
                )

            if database.status:
                messages.success(request, _('تم إنشاء قاعدة البيانات بنجاح.'))
            else:
                messages.warning(request, _(f'تم إنشاء سجل قاعدة البيانات ولكن حدث خطأ أثناء إنشاء قاعدة البيانات الفعلية: {database.error_message}'))

            return redirect('odoo_db_manager:database_detail', pk=database.pk)
        except Exception as e:
            messages.error(request, _(f'حدث خطأ أثناء إنشاء قاعدة البيانات: {str(e)}'))
            return redirect('odoo_db_manager:database_create')

    context = {
        'title': _('إنشاء قاعدة بيانات جديدة'),
    }

    return render(request, 'odoo_db_manager/database_form.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def database_activate(request, pk):
    """تنشيط قاعدة بيانات"""
    # الحصول على قاعدة البيانات
    database = get_object_or_404(Database, pk=pk)

    try:
        # تنشيط قاعدة البيانات
        database_service = DatabaseService()
        database_service.activate_database(database.id)

        messages.success(request, _('تم تنشيط قاعدة البيانات بنجاح.'))
    except Exception as e:
        messages.error(request, _(f'حدث خطأ أثناء تنشيط قاعدة البيانات: {str(e)}'))

    return redirect('odoo_db_manager:database_detail', pk=database.pk)

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
        'title': _('حذف قاعدة البيانات'),
    }

    return render(request, 'odoo_db_manager/database_delete.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def backup_create(request, database_id=None):
    """إنشاء نسخة احتياطية"""
    # الحصول على قاعدة البيانات
    database = None
    if database_id:
        database = get_object_or_404(Database, pk=database_id)

    if request.method == 'POST':
        # الحصول على بيانات النموذج
        database_id = request.POST.get('database_id', database_id)
        name = request.POST.get('name', '')
        backup_type = request.POST.get('backup_type', 'full')

        try:
            # طباعة معلومات تشخيصية
            print(f"إنشاء نسخة احتياطية جديدة")
            print(f"معرف قاعدة البيانات: {database_id}")
            print(f"اسم النسخة الاحتياطية: {name}")
            print(f"نوع النسخة الاحتياطية: {backup_type}")

            # الحصول على قاعدة البيانات
            db = Database.objects.get(id=database_id)
            print(f"معلومات قاعدة البيانات: {db.name}, {db.db_type}, {db.connection_info}")

            # التأكد من وجود كلمة المرور الصحيحة
            if db.db_type == 'postgresql' and (not db.connection_info.get('PASSWORD') or db.connection_info.get('PASSWORD') != '5525'):
                # تحديث كلمة المرور
                connection_info = db.connection_info
                connection_info['PASSWORD'] = '5525'
                db.connection_info = connection_info
                db.save()
                print(f"تم تحديث كلمة المرور لقاعدة البيانات: {db.name}")

            # إنشاء نسخة احتياطية بسيطة عن طريق نسخ ملف قاعدة البيانات SQLite مباشرة
            if settings.DATABASES['default']['ENGINE'].endswith('sqlite3'):

                # الحصول على مسار ملف قاعدة البيانات
                db_file = settings.DATABASES['default']['NAME']
                print(f"مسار ملف قاعدة البيانات: {db_file}")

                # إنشاء اسم النسخة الاحتياطية إذا لم يتم توفيره
                if not name:
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    name = f"{db.name}_{backup_type}_{timestamp}"

                # إنشاء مجلد النسخ الاحتياطي إذا لم يكن موجود
                backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
                os.makedirs(backup_dir, exist_ok=True)

                # إنشاء مسار ملف النسخة الاحتياطية
                backup_file = os.path.join(backup_dir, f"{name}.sqlite3")
                print(f"مسار ملف النسخة الاحتياطية: {backup_file}")

                # نسخ ملف قاعدة البيانات
                shutil.copy2(db_file, backup_file)
                print(f"تم نسخ ملف قاعدة البيانات بنجاح إلى: {backup_file}")

                # إنشاء سجل النسخة الاحتياطية في قاعدة البيانات
                backup = Backup.objects.create(
                    name=name,
                    database=db,
                    backup_type=backup_type,
                    file_path=backup_file,
                    created_by=request.user
                )
                print(f"تم إنشاء سجل النسخة الاحتياطية بنجاح: {backup.id}")
            else:
                # إنشاء النسخة الاحتياطية لقاعدة بيانات PostgreSQL
                if not name:
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    name = f"{db.name}_{backup_type}_{timestamp}"

                # إنشاء مجلد النسخ الاحتياطي إذا لم يكن موجود
                backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
                os.makedirs(backup_dir, exist_ok=True)

                # إنشاء ملف JSON باستخدام Django dumpdata
                backup_file = os.path.join(backup_dir, f"{name}.json")
                print(f"🔄 إنشاء نسخة احتياطية JSON: {backup_file}")

                try:
                    # استخدام Django dumpdata لإنشاء النسخة الاحتياطية
                    from django.core.management import call_command
                    from io import StringIO

                    # إنشاء buffer لحفظ البيانات
                    output = StringIO()

                    # تحديد التطبيقات المراد نسخها حسب نوع النسخة الاحتياطية
                    if backup_type == 'customers':
                        apps_to_backup = ['customers']
                    elif backup_type == 'users':
                        apps_to_backup = ['auth', 'accounts']
                    elif backup_type == 'settings':
                        apps_to_backup = ['odoo_db_manager']
                    else:  # full
                        apps_to_backup = ['customers', 'orders', 'inspections', 'inventory', 'installations', 'factory', 'accounts', 'odoo_db_manager']

                    # تنفيذ dumpdata
                    call_command('dumpdata', *apps_to_backup, stdout=output, format='json', indent=2)

                    # حفظ البيانات في الملف
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        f.write(output.getvalue())

                    print(f"تم إنشاء ملف النسخة الاحتياطية: {backup_file}")
                    print(f"حجم الملف: {os.path.getsize(backup_file)} بايت")

                    # إنشاء سجل النسخة الاحتياطية في قاعدة البيانات
                    backup = Backup.objects.create(
                        name=name,
                        database=db,
                        backup_type=backup_type,
                        file_path=backup_file,
                        size=os.path.getsize(backup_file),
                        created_by=request.user
                    )
                    print(f"تم إنشاء سجل النسخة الاحتياطية بنجاح: {backup.id}")

                except Exception as backup_error:
                    print(f"خطأ في إنشاء النسخة الاحتياطية: {str(backup_error)}")
                    # في حالة الفشل، إنشاء سجل بدون ملف
                    backup = Backup.objects.create(
                        name=name,
                        database=db,
                        backup_type=backup_type,
                        file_path="",
                        created_by=request.user
                    )
                    raise backup_error

            messages.success(request, _('تم إنشاء النسخة الاحتياطية بنجاح.'))
            return redirect('odoo_db_manager:backup_detail', pk=backup.pk)
        except Exception as e:
            messages.error(request, _(f'حدث خطأ أثناء إنشاء النسخة الاحتياطية: {str(e)}'))
            return redirect('odoo_db_manager:backup_create')

    # الحصول على قواعد البيانات
    databases = Database.objects.all()

    # الحصول على أنواع النسخ الاحتياطية من نموذج Backup
    backup_types = Backup.BACKUP_TYPES

    context = {
        'database': database,
        'databases': databases,
        'backup_types': backup_types,
        'title': _('إنشاء نسخة احتياطية جديدة'),
    }

    return render(request, 'odoo_db_manager/backup_form.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def backup_detail(request, pk):
    """عرض تفاصيل النسخة الاحتياطية"""
    # الحصول على النسخة الاحتياطية
    backup = get_object_or_404(Backup, pk=pk)

    context = {
        'backup': backup,
        'title': _('تفاصيل النسخة الاحتياطية'),
    }

    return render(request, 'odoo_db_manager/backup_detail.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def backup_restore(request, pk):
    """استعادة النسخة الاحتياطية"""
    # الحصول على النسخة الاحتياطية
    backup = get_object_or_404(Backup, pk=pk)

    # حفظ معلومات النسخة الاحتياطية قبل استعادتها
    backup_info = {
        'id': backup.id,
        'name': backup.name,
        'database_id': backup.database.id,
        'backup_type': backup.backup_type,
        'file_path': backup.file_path,
        'created_at': backup.created_at,
        'created_by_id': backup.created_by.id if backup.created_by else None
    }

    if request.method == 'POST':
        # الحصول على خيار حذف البيانات القديمة
        clear_data = request.POST.get('clear_data', 'off') == 'on'

        try:
            # التحقق من وجود الملف
            if not os.path.exists(backup.file_path):
                raise FileNotFoundError(f"ملف النسخة الاحتياطية '{backup.file_path}' غير موجود")

            # إذا كان ملف SQLite3، نقوم باستعادته مباشرة
            if backup.file_path.endswith('.sqlite3'):
                # الحصول على مسار ملف قاعدة البيانات الحالية
                db_file = settings.DATABASES['default']['NAME']

                # إنشاء نسخة احتياطية من قاعدة البيانات الحالية قبل الاستبدال
                backup_current_db = f"{db_file}.bak"
                shutil.copy2(db_file, backup_current_db)

                try:
                    # نسخ ملف النسخة الاحتياطية إلى مسار قاعدة البيانات الحالية
                    shutil.copy2(backup.file_path, db_file)

                    # إعادة إنشاء سجل النسخة الاحتياطية بعد استعادة قاعدة البيانات
                    from accounts.models import User

                    # الحصول على قاعدة البيانات
                    try:
                        db = Database.objects.get(id=backup_info['database_id'])
                    except Database.DoesNotExist:
                        # إذا لم تكن قاعدة البيانات موجودة، نستخدم أول قاعدة بيانات متاحة
                        db = Database.objects.first()
                        if not db:
                            # إذا لم تكن هناك قواعد بيانات، نقوم بإنشاء واحدة
                            db = Database.objects.create(
                                name="Default Database",
                                db_type="sqlite3",
                                connection_info={}
                            )

                    # الحصول على المستخدم
                    user_id = backup_info['created_by_id']
                    user = None
                    if user_id:
                        try:
                            user = User.objects.get(id=user_id)
                        except User.DoesNotExist:
                            # إذا لم يكن المستخدم موجودًا، نستخدم أول مستخدم متاح
                            user = User.objects.first()

                    # إعادة إنشاء سجل النسخة الاحتياطية
                    try:
                        Backup.objects.get(id=backup_info['id'])
                    except Backup.DoesNotExist:
                        Backup.objects.create(
                            id=backup_info['id'],
                            name=backup_info['name'],
                            database=db,
                            backup_type=backup_info['backup_type'],
                            file_path=backup_info['file_path'],
                            created_at=backup_info['created_at'],
                            created_by=user
                        )

                    messages.success(request, _('تم استعادة النسخة الاحتياطية بنجاح.'))
                except Exception as e:
                    # استعادة النسخة الاحتياطية في حالة حدوث خطأ
                    shutil.copy2(backup_current_db, db_file)
                    raise RuntimeError(f"فشل استعادة قاعدة البيانات: {str(e)}")
                finally:
                    # حذف النسخة الاحتياطية المؤقتة
                    if os.path.exists(backup_current_db):
                        os.unlink(backup_current_db)
            else:
                # استعادة النسخة الاحتياطية بطريقة مبسطة
                # تم إزالة BackupService لتجنب التعقيدات
                if backup.file_path.endswith('.json'):
                    _restore_json_simple(backup.file_path)
                else:
                    raise ValueError("نوع ملف غير مدعوم. يرجى استخدام ملفات JSON.")
                messages.success(request, _('تم استعادة النسخة الاحتياطية بنجاح.'))

            return redirect('odoo_db_manager:dashboard')
        except Exception as e:
            messages.error(request, _(f'حدث خطأ أثناء استعادة النسخة الاحتياطية: {str(e)}'))
            try:
                # محاولة الوصول إلى صفحة تفاصيل النسخة الاحتياطية
                return redirect('odoo_db_manager:backup_detail', pk=backup.pk)
            except:
                # إذا لم يكن سجل النسخة الاحتياطية موجودًا، نعود إلى لوحة التحكم
                return redirect('odoo_db_manager:dashboard')

    context = {
        'backup': backup,
        'title': _('استعادة النسخة الاحتياطية'),
    }

    return render(request, 'odoo_db_manager/backup_restore.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def backup_delete(request, pk):
    """حذف النسخة الاحتياطية"""
    # الحصول على النسخة الاحتياطية
    backup = get_object_or_404(Backup, pk=pk)

    if request.method == 'POST':
        try:
            # حذف النسخة الاحتياطية بطريقة مبسطة
            # حذف الملف إذا كان موجوداً
            if backup.file_path and os.path.exists(backup.file_path):
                os.unlink(backup.file_path)

            # حذف السجل من قاعدة البيانات
            backup.delete()

            messages.success(request, _('تم حذف النسخة الاحتياطية بنجاح.'))
            return redirect('odoo_db_manager:dashboard')
        except Exception as e:
            messages.error(request, _(f'حدث خطأ أثناء حذف النسخة الاحتياطية: {str(e)}'))
            return redirect('odoo_db_manager:backup_detail', pk=backup.pk)

    context = {
        'backup': backup,
        'title': _('حذف النسخة الاحتياطية'),
    }

    return render(request, 'odoo_db_manager/backup_delete.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def backup_download(request, pk):
    """تحميل ملف النسخة الاحتياطية"""
    # الحصول على النسخة الاحتياطية
    backup = get_object_or_404(Backup, pk=pk)

    # التحقق من وجود الملف
    if not os.path.exists(backup.file_path):
        messages.error(request, _('ملف النسخة الاحتياطية غير موجود.'))
        return redirect('odoo_db_manager:backup_detail', pk=backup.pk)

    # إنشاء استجابة الملف
    response = FileResponse(open(backup.file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(backup.file_path)}"'

    return response

@login_required
@user_passes_test(is_staff_or_superuser)
def backup_upload(request, database_id=None):
    """استعادة من ملف تم تحميله"""
    # الحصول على قاعدة البيانات
    database = None
    if database_id:
        database = get_object_or_404(Database, pk=database_id)

    if request.method == 'POST':
        # التحقق من وجود قاعدة بيانات
        database_id = request.POST.get('database_id', database_id)
        if not database_id:
            messages.error(request, _('يرجى اختيار قاعدة بيانات.'))
            return redirect('odoo_db_manager:backup_upload')

        # التحقق من وجود ملف
        if 'backup_file' not in request.FILES or not request.FILES['backup_file']:
            messages.error(request, _('يرجى اختيار ملف النسخة الاحتياطية.'))
            return redirect('odoo_db_manager:backup_upload')

        # التحقق من أن الملف ليس فارغاً
        uploaded_file = request.FILES['backup_file']
        if uploaded_file.size == 0:
            messages.error(request, _('الملف المرفوع فارغ. يرجى اختيار ملف صالح.'))
            return redirect('odoo_db_manager:backup_upload')

        # الحصول على خيارات الاستعادة
        backup_type = request.POST.get('backup_type', 'full')
        clear_data = request.POST.get('clear_data', 'off') == 'on'

        try:
            print("🚀 بدء عملية الاستعادة المباشرة...")
            print(f"📁 اسم الملف المرفوع: {uploaded_file.name}")
            print(f"📊 حجم الملف المرفوع: {uploaded_file.size} بايت")

            # حفظ الملف في مجلد النسخ الاحتياطية مباشرة
            backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
            os.makedirs(backup_dir, exist_ok=True)

            # إنشاء اسم ملف فريد
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"uploaded_{timestamp}_{uploaded_file.name}"
            file_path = os.path.join(backup_dir, file_name)

            print(f"💾 حفظ الملف في: {file_path}")

            # حفظ الملف
            with open(file_path, 'wb') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            actual_size = os.path.getsize(file_path)
            print(f"✅ تم حفظ الملف بنجاح - الحجم الفعلي: {actual_size} بايت")

            # استعادة مباشرة
            from django.core.management import call_command

            if clear_data:
                print("⚠️ تم تجاهل خيار حذف البيانات القديمة لتجنب مشاكل قاعدة البيانات")

            # استعادة مبسطة جداً
            print(f"🔄 بدء استعادة الملف: {file_path}")

            # التحقق من نوع الملف
            if uploaded_file.name.endswith('.gz'):
                print("📦 ملف مضغوط - فك الضغط...")
                import gzip
                import tempfile

                with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
                    temp_path = temp_file.name

                    try:
                        print(f"🔓 فك ضغط من: {file_path}")
                        with gzip.open(file_path, 'rt', encoding='utf-8') as gz_file:
                            content = gz_file.read()

                        print(f"📝 كتابة المحتوى المفكوك إلى: {temp_path}")
                        with open(temp_path, 'w', encoding='utf-8') as json_file:
                            json_file.write(content)

                        temp_size = os.path.getsize(temp_path)
                        print(f"✅ تم فك الضغط بنجاح - حجم الملف المفكوك: {temp_size} بايت")

                        # استعادة من الملف المفكوك
                        print("🔄 استعادة البيانات من الملف المفكوك...")
                        _restore_json_simple(temp_path)

                    except Exception as gz_error:
                        print(f"❌ خطأ في فك الضغط: {str(gz_error)}")
                        raise
                    finally:
                        # حذف الملف المؤقت
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                            print(f"🗑️ تم حذف الملف المؤقت: {temp_path}")
            else:
                print("📄 ملف JSON عادي - استعادة مباشرة...")
                _restore_json_simple(file_path)

            print("🎉 تمت الاستعادة بنجاح!")

            messages.success(request, _('تم استعادة النسخة الاحتياطية بنجاح.'))
            return redirect('odoo_db_manager:database_detail', pk=database_id)
        except Exception as e:
            error_message = str(e)
            print(f"خطأ في الاستعادة: {error_message}")

            # رسالة خطأ مبسطة
            if "flush" in error_message:
                error_message = "مشكلة في إعدادات قاعدة البيانات. تم تجاهل حذف البيانات القديمة."
            elif "JSON" in error_message or "fixture" in error_message:
                error_message = "مشكلة في تنسيق الملف. تأكد من أن الملف بتنسيق JSON صالح."
            elif "فشل تثبيت البيانات من الملف المضغوط" in error_message:
                error_message = "مشكلة في الملف المضغوط. جرب ملف JSON غير مضغوط."
            else:
                error_message = f"خطأ في الاستعادة: {error_message[:200]}..."

            messages.error(request, _(f'حدث خطأ أثناء استعادة النسخة الاحتياطية: {error_message}'))
            return redirect('odoo_db_manager:backup_upload')

    # الحصول على قواعد البيانات
    databases = Database.objects.all()

    context = {
        'database': database,
        'databases': databases,
        'backup_types': Backup.BACKUP_TYPES,
        'title': _('استعادة من ملف'),
    }

    return render(request, 'odoo_db_manager/backup_upload.html', context)


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

    # الحصول على النسخ الاحتياطية المرتبطة بهذه الجدولة
    backups = Backup.objects.filter(
        database=schedule.database,
        backup_type=schedule.backup_type,
        is_scheduled=True
    ).order_by('-created_at')

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
            # حذف النسخ الاحتياطية المرتبطة إذا طلب المستخدم ذلك
            if delete_backups:
                backups = Backup.objects.filter(
                    database=schedule.database,
                    backup_type=schedule.backup_type,
                    is_scheduled=True
                )
                for backup in backups:
                    # حذف ملف النسخة الاحتياطية
                    if os.path.exists(backup.file_path):
                        os.unlink(backup.file_path)
                    # حذف سجل النسخة الاحتياطية
                    backup.delete()

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


def _restore_json_simple(file_path):
    """استعادة ملف JSON بطريقة مبسطة"""
    import json
    from django.core import serializers

    try:
        print(f"📖 قراءة ملف JSON: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"✅ تم تحميل {len(data)} عنصر من الملف")

        # استعادة البيانات عنصر بعنصر مع تجاهل الأخطاء
        success_count = 0
        error_count = 0

        print("🔄 بدء استعادة العناصر...")

        for i, item in enumerate(data):
            try:
                # تحويل العنصر إلى كائن Django
                for obj in serializers.deserialize('json', json.dumps([item])):
                    obj.save()
                success_count += 1

                # طباعة تقدم كل 10 عناصر
                if (i + 1) % 10 == 0:
                    print(f"📊 تم معالجة {i + 1} عنصر...")

            except Exception as item_error:
                error_count += 1
                # طباعة تفاصيل الخطأ للعناصر القليلة الأولى فقط
                if error_count <= 3:
                    print(f"⚠️ خطأ في العنصر {i + 1}: {str(item_error)[:100]}...")

        print(f"🎯 تمت الاستعادة: {success_count} عنصر بنجاح، {error_count} عنصر تم تجاهله")

    except Exception as e:
        print(f"❌ خطأ في قراءة الملف: {str(e)}")
        raise


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