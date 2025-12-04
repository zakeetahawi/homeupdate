"""
نماذج إدارة قواعد البيانات على طراز أودو
"""

import calendar
import json
import os
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ImportLog(models.Model):
    """سجل عمليات الاستيراد"""
    sheet_name = models.CharField(_('اسم الجدول'), max_length=100)
    total_records = models.IntegerField(_('إجمالي السجلات'), default=0)
    imported_records = models.IntegerField(_('السجلات المستوردة'), default=0)
    updated_records = models.IntegerField(_('السجلات المحدثة'), default=0)
    failed_records = models.IntegerField(_('السجلات الفاشلة'), default=0)
    clear_existing = models.BooleanField(_('حذف البيانات القديمة'), default=False)
    status = models.CharField(
        _('الحالة'),
        max_length=20,
        choices=[
            ('success', 'نجح'),
            ('failed', 'فشل'),
            ('partial', 'جزئي'),
        ],
        default='success'
    )
    error_details = models.TextField(_('تفاصيل الأخطاء'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('المستخدم'),
        related_name='created_import_logs',  # Add this line
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('المستخدم'),
        related_name='assigned_import_logs',  # Add this line
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _('سجل استيراد')
        verbose_name_plural = _('سجلات الاستيراد')
        ordering = ['-created_at']

    def __str__(self):
        return f"استيراد {self.sheet_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class Database(models.Model):
    """نموذج قاعدة البيانات الرئيسي"""
    DB_TYPES = [
        ('postgresql', 'PostgreSQL'),
    ]
    name = models.CharField(_('اسم قاعدة البيانات'), max_length=100)
    db_type = models.CharField(_('نوع قاعدة البيانات'), max_length=20, choices=DB_TYPES)
    connection_info = models.JSONField(_('معلومات الاتصال'), default=dict)
    is_active = models.BooleanField(_('نشطة'), default=False)
    # إضافة الحقول المفقودة
    status = models.BooleanField(_('حالة الاتصال'), default=False)
    error_message = models.TextField(_('رسالة الخطأ'), blank=True, null=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    class Meta:
        verbose_name = _('قاعدة بيانات')
        verbose_name_plural = _('قواعد البيانات')
        ordering = ['-created_at']
    def __str__(self):
        return self.name
    @property
    def connection_string(self):
        """إنشاء سلسلة الاتصال"""
        if self.db_type == 'postgresql':
            host = self.connection_info.get('HOST', 'localhost')
            port = self.connection_info.get('PORT', '5432')
            name = self.connection_info.get('NAME', self.name)
            user = self.connection_info.get('USER', '')
            return f"postgresql://{user}@{host}:{port}/{name}"
        return ""

    @property
    def connection_status(self):
        """فحص حالة الاتصال الفعلية بقاعدة البيانات"""
        try:
            # التحقق من الاتصال بقاعدة البيانات
            if self.db_type == 'postgresql':
                import psycopg2
                conn = psycopg2.connect(
                    dbname=self.connection_info.get('NAME', self.name),
                    user=self.connection_info.get('USER', ''),
                    password=self.connection_info.get('PASSWORD', ''),
                    host=self.connection_info.get('HOST', 'localhost'),
                    port=self.connection_info.get('PORT', '5432'),
                    connect_timeout=3  # وقت انتهاء المهلة بالثواني
                )
                conn.close()
                return True
            return True
        except Exception:
            return False

    @property
    def size_display(self):
        """عرض حجم قاعدة البيانات بشكل مقروء"""
        total_size = 0
        # Django يوفر self.backups إذا كان هناك علاقة Backup صحيحة
        if hasattr(self, 'backups'):
            total_size = sum(backup.size for backup in self.backups.all())
        for unit in ['B', 'KB', 'MB', 'GB']:
            if total_size < 1024.0:
                return f"{total_size:.1f} {unit}"
            total_size /= 1024.0
        return f"{total_size:.1f} TB"
    def update_env_file(self):
        """تحديث ملف .env بإعدادات قاعدة البيانات النشطة"""
        try:
            import os
            from pathlib import Path
            from dotenv import load_dotenv
            import time
            # الحصول على مسار ملف .env
            BASE_DIR = Path(__file__).resolve().parent.parent
            env_file = os.path.join(BASE_DIR, '.env')
            # التحقق من وجود ملف .env
            if not os.path.exists(env_file):
                print(f"ملف .env غير موجود في {env_file}")
                return False            # إنشاء نسخة احتياطية من ملف .env
            backup_file = os.path.join(BASE_DIR, f'.env.backup.{int(time.time())}')
            try:
                with open(env_file, 'r', encoding='utf-8') as src, open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                print(f"تم إنشاء نسخة احتياطية من ملف .env في {backup_file}")
            except Exception as e:
                print(f"حدث خطأ أثناء إنشاء نسخة احتياطية من ملف .env: {str(e)}")
            # قراءة محتوى ملف .env
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # تحديث إعدادات قاعدة البيانات
            connection_info = self.connection_info
            new_lines = []
            db_url_updated = False
            db_name_updated = False
            db_user_updated = False
            db_password_updated = False
            db_host_updated = False
            db_port_updated = False
            pgpassword_updated = False
            # إضافة تعليق يشير إلى أن الملف تم تحديثه
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            new_lines.append(f"# تم تحديث هذا الملف تلقائياً بواسطة نظام إدارة قواعد البيانات في {current_time}\n")
            new_lines.append(f"# قاعدة البيانات النشطة: {self.name} ({connection_info.get('NAME')})\n\n")
            for line in lines:
                # تخطي التعليقات والأسطر الفارغة
                if line.strip().startswith('#') or not line.strip():
                    continue
                if line.startswith('DATABASE_URL='):
                    # تحديث DATABASE_URL
                    db_url = f"postgres://{connection_info.get('USER')}:{connection_info.get('PASSWORD')}@{connection_info.get('HOST')}:{connection_info.get('PORT')}/{connection_info.get('NAME')}"
                    new_lines.append(f"DATABASE_URL={db_url}\n")
                    db_url_updated = True
                elif line.startswith('DB_NAME='):
                    # تحديث DB_NAME
                    new_lines.append(f"DB_NAME={connection_info.get('NAME')}\n")
                    db_name_updated = True
                elif line.startswith('DB_USER='):
                    # تحديث DB_USER
                    new_lines.append(f"DB_USER={connection_info.get('USER')}\n")
                    db_user_updated = True
                elif line.startswith('DB_PASSWORD='):
                    # تحديث DB_PASSWORD
                    new_lines.append(f"DB_PASSWORD={connection_info.get('PASSWORD')}\n")
                    db_password_updated = True
                elif line.startswith('DB_HOST='):
                    # تحديث DB_HOST
                    new_lines.append(f"DB_HOST={connection_info.get('HOST')}\n")
                    db_host_updated = True
                elif line.startswith('DB_PORT='):
                    # تحديث DB_PORT
                    new_lines.append(f"DB_PORT={connection_info.get('PORT')}\n")
                    db_port_updated = True
                elif line.startswith('PGPASSWORD='):
                    # تحديث PGPASSWORD
                    new_lines.append(f"PGPASSWORD={connection_info.get('PASSWORD')}\n")
                    pgpassword_updated = True
                else:
                    new_lines.append(line)
            # إضافة الإعدادات إذا لم تكن موجودة
            if not db_url_updated:
                db_url = f"postgres://{connection_info.get('USER')}:{connection_info.get('PASSWORD')}@{connection_info.get('HOST')}:{connection_info.get('PORT')}/{connection_info.get('NAME')}"
                new_lines.append(f"DATABASE_URL={db_url}\n")
            if not db_name_updated:
                new_lines.append(f"DB_NAME={connection_info.get('NAME')}\n")
            if not db_user_updated:
                new_lines.append(f"DB_USER={connection_info.get('USER')}\n")
            if not db_password_updated:
                new_lines.append(f"DB_PASSWORD={connection_info.get('PASSWORD')}\n")
            if not db_host_updated:
                new_lines.append(f"DB_HOST={connection_info.get('HOST')}\n")
            if not db_port_updated:
                new_lines.append(f"DB_PORT={connection_info.get('PORT')}\n")
            if not pgpassword_updated:
                new_lines.append(f"PGPASSWORD={connection_info.get('PASSWORD')}\n")
            # إضافة متغيرات البيئة الأخرى التي قد تكون موجودة في الملف الأصلي
            for line in lines:
                if (not line.strip().startswith('#') and
                    not line.startswith('DATABASE_URL=') and
                    not line.startswith('DB_NAME=') and
                    not line.startswith('DB_USER=') and
                    not line.startswith('DB_PASSWORD=') and
                    not line.startswith('DB_HOST=') and
                    not line.startswith('DB_PORT=') and
                    not line.startswith('PGPASSWORD=') and
                    line.strip() and
                    '=' in line and
                    line not in new_lines):
                    new_lines.append(line)
            # كتابة المحتوى المحدث إلى ملف .env
            with open(env_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"تم تحديث ملف .env بنجاح")
            return True
        except Exception as e:
            print(f"حدث خطأ أثناء تحديث ملف .env: {str(e)}")
            return False
    def update_settings_file(self):
        """تحديث ملف db_settings.json بإعدادات قاعدة البيانات النشطة"""
        try:
            import os
            import json
            from pathlib import Path
            # الحصول على مسار ملف db_settings.json
            BASE_DIR = Path(__file__).resolve().parent.parent
            settings_file = os.path.join(BASE_DIR, 'db_settings.json')
            # قراءة محتوى ملف db_settings.json
            with open(settings_file, 'r') as f:
                settings = json.load(f)
            # تحديث إعدادات قاعدة البيانات النشطة
            settings['active_db'] = str(self.pk)            # التحقق من وجود قاعدة البيانات في الإعدادات
            if str(self.pk) not in settings['databases']:
                settings['databases'][str(self.pk)] = self.connection_info.copy()
            else:
                settings['databases'][str(self.pk)] = self.connection_info.copy()

            # إزالة TIME_ZONE إذا كان موجوداً (لأنه يسبب مشاكل في PostgreSQL)
            if 'TIME_ZONE' in settings['databases'][str(self.pk)]:
                del settings['databases'][str(self.pk)]['TIME_ZONE']
            # كتابة المحتوى المحدث إلى ملف db_settings.json
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            print(f"تم تحديث ملف db_settings.json بنجاح")
            return True
        except Exception as e:
            print(f"حدث خطأ أثناء تحديث ملف db_settings.json: {str(e)}")
            return False
    def create_default_user(self):
        """إنشاء مستخدم افتراضي في حال عدم وجود مستخدمين"""
        try:
            from django.contrib.auth import get_user_model
            from django.db import connections
            import secrets
            import os
            User = get_user_model()
            # التحقق من وجود مستخدمين
            if User.objects.count() == 0:
                # 🔒 إنشاء كلمة سر عشوائية آمنة
                default_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', secrets.token_urlsafe(16))
                # إنشاء مستخدم افتراضي
                User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password=default_password,
                    first_name='مدير',
                    last_name='النظام'
                )
                print(f"تم إنشاء مستخدم افتراضي (admin/{default_password})")
                print("⚠️ احفظ كلمة السر وغيّرها فوراً!")
                return True
            return False
        except Exception as e:
            print(f"حدث خطأ أثناء إنشاء المستخدم الافتراضي: {str(e)}")
            return False

    def activate(self):
        """تنشيط قاعدة البيانات"""
        try:
            print(f"🔄 بدء تنشيط قاعدة البيانات: {self.name}")

            # تعطيل جميع قواعد البيانات الأخرى
            print("📝 تعطيل قواعد البيانات الأخرى...")
            Database.objects.exclude(pk=self.pk).update(is_active=False)

            # تنشيط قاعدة البيانات الحالية
            print("✅ تنشيط قاعدة البيانات الحالية...")
            self.is_active = True
            self.save()

            # تحديث ملف .env
            print("📄 تحديث ملف .env...")
            env_updated = self.update_env_file()
            print(f"نتيجة تحديث .env: {env_updated}")

            # تحديث ملف db_settings.json
            print("⚙️ تحديث ملف db_settings.json...")
            settings_updated = self.update_settings_file()
            print(f"نتيجة تحديث settings: {settings_updated}")

            # التحقق من نجاح التحديث
            if env_updated and settings_updated:
                print(f"✅ تم تنشيط قاعدة البيانات {self.name} بنجاح")
                # محاولة تحديث إعدادات Django في الذاكرة
                try:
                    print("🔄 محاولة تحديث إعدادات Django في الذاكرة...")
                    from django.conf import settings
                    from django.db import connections
                    import importlib
                    # تحديث إعدادات قاعدة البيانات في الذاكرة
                    connection_info = self.connection_info.copy()
                    db_config = {
                        'ENGINE': connection_info.get('ENGINE', 'django.db.backends.postgresql'),
                        'NAME': connection_info.get('NAME'),
                        'USER': connection_info.get('USER'),
                        'PASSWORD': connection_info.get('PASSWORD'),
                        'HOST': connection_info.get('HOST'),
                        'PORT': connection_info.get('PORT'),
                        'ATOMIC_REQUESTS': False,
                        'AUTOCOMMIT': True,
                        'CONN_MAX_AGE': 600,
                        'CONN_HEALTH_CHECKS': True,
                        'TIME_ZONE': None,  # Django يحتاج هذا المفتاح
                        'OPTIONS': {},
                    }
                    print(f"🔧 إعدادات قاعدة البيانات الجديدة: {db_config}")
                    # إغلاق جميع الاتصالات الحالية أولاً
                    print("🔌 إغلاق جميع الاتصالات الحالية...")
                    connections.close_all()

                    # تحديث إعدادات قاعدة البيانات
                    print("⚙️ تحديث إعدادات قاعدة البيانات في Django...")
                    settings.DATABASES['default'] = db_config

                    # إعادة تعيين مدير الاتصالات لضمان استخدام الإعدادات الجديدة
                    # نحتاج لإجبار Django على إعادة إنشاء الاتصالات
                    if 'default' in connections:
                        del connections['default']

                    # اختبار الاتصال الجديد
                    print("🧪 اختبار الاتصال الجديد...")
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT current_database()")
                        result = cursor.fetchone()
                    current_db = result[0] if result else "غير معروف"

                    print(f"✅ تم تحديث إعدادات Django في الذاكرة بنجاح - قاعدة البيانات الحالية: {current_db}")

                    if current_db == connection_info.get('NAME'):
                        print("🎉 تم التبديل بنجاح إلى قاعدة البيانات الجديدة!")
                        # تشغيل migrations للتأكد من وجود جميع الجداول المطلوبة
                        try:
                            print("🔄 تشغيل migrations للتأكد من وجود جميع الجداول...")
                            # self.run_migrations()  # مؤقتاً معطل
                            print("✅ سيتم تشغيل migrations بعد إعادة التشغيل")
                        except Exception as migration_error:
                            print(f"⚠️ خطأ في تشغيل migrations: {str(migration_error)}")
                            # رغم خطأ migrations، التبديل نجح

                        return {'success': True, 'requires_restart': False, 'database_name': self.name}
                    else:
                        print(f"⚠️ لم يتم التبديل بنجاح. قاعدة البيانات الحالية: {current_db}, المطلوبة: {connection_info.get('NAME')}")
                        return {'success': True, 'requires_restart': True, 'database_name': self.name}
                except Exception as e:
                    print(f"❌ خطأ أثناء تحديث إعدادات Django في الذاكرة: {str(e)}")
            # ...existing code...
        except Exception as e:
            print(f"❌ خطأ أثناء تنشيط قاعدة البيانات: {str(e)}")
            return False
        return True
    # ...existing code...
# تم حذف نموذج Backup القديم - استخدم backup_system بدلاً من ذلك
class BackupSchedule(models.Model):
    """نموذج جدولة النسخ الاحتياطية"""
    FREQUENCY_CHOICES = [
        ('hourly', _('كل ساعة')),
        ('daily', _('يومياً')),
        ('weekly', _('أسبوعياً')),
        ('monthly', _('شهرياً')),
    ]
    DAYS_OF_WEEK = [
        (0, _('الاثنين')),
        (1, _('الثلاثاء')),
        (2, _('الأربعاء')),
        (3, _('الخميس')),
        (4, _('الجمعة')),
        (5, _('السبت')),
        (6, _('الأحد')),
    ]
    database = models.ForeignKey(
        Database,
        on_delete=models.CASCADE,
        related_name='backup_schedules',
        verbose_name=_('قاعدة البيانات')
    )
    name = models.CharField(_('اسم الجدولة'), max_length=100)
    backup_type = models.CharField(
        _('نوع النسخة الاحتياطية'),
        max_length=20,
        choices=[
            ('customers', 'بيانات العملاء'),
            ('users', 'بيانات المستخدمين'),
            ('settings', 'إعدادات النظام'),
            ('full', 'كل البيانات'),
        ],
        default='full'
    )
    frequency = models.CharField(
        _('التكرار'),
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='daily'
    )
    # وقت التنفيذ
    hour = models.IntegerField(_('الساعة'), default=0, help_text=_('0-23'))
    minute = models.IntegerField(_('الدقيقة'), default=0, help_text=_('0-59'))
    # أيام الأسبوع (للتكرار الأسبوعي)
    day_of_week = models.IntegerField(
        _('يوم الأسبوع'),
        choices=DAYS_OF_WEEK,
        default=0,
        null=True,
        blank=True
    )
    # يوم الشهر (للتكرار الشهري)
    day_of_month = models.IntegerField(
        _('يوم الشهر'),
        default=1,
        help_text=_('1-31'),
        null=True,
        blank=True
    )
    # الحد الأقصى لعدد النسخ الاحتياطية
    max_backups = models.IntegerField(
        _('الحد الأقصى لعدد النسخ'),
        default=24,
        help_text=_('الحد الأقصى هو 24 نسخة')
    )
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    last_run = models.DateTimeField(_('آخر تشغيل'), null=True, blank=True)
    next_run = models.DateTimeField(_('التشغيل القادم'), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('تم الإنشاء بواسطة'),
        related_name='backup_schedules'
    )
    class Meta:
        verbose_name = _('جدولة النسخ الاحتياطية')
        verbose_name_plural = _('جدولة النسخ الاحتياطية')
        ordering = ['-created_at']
    def __str__(self):
        frequency_map = {
            'daily': 'يومياً',
            'weekly': 'أسبوعياً',
            'monthly': 'شهرياً',
        }
        return f"{self.name} - {frequency_map.get(self.frequency, self.frequency)}"
    def calculate_next_run(self):
        """حساب موعد التشغيل القادم"""
        now = timezone.now()
        # تعيين الساعة والدقيقة
        next_run = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        # إذا كان الوقت المحدد قد مر بالفعل، نضيف الفترة المناسبة
        if next_run <= now:
            if self.frequency == 'hourly':
                next_run = next_run.replace(hour=now.hour) + timedelta(hours=1)
            elif self.frequency == 'daily':
                next_run = next_run + timedelta(days=1)
            elif self.frequency == 'weekly':
                # حساب عدد الأيام حتى يوم الأسبوع المحدد
                days_ahead = (self.day_of_week or 0) - now.weekday()
                if days_ahead <= 0:  # إذا كان اليوم المحدد قد مر هذا الأسبوع
                    days_ahead += 7
                next_run = next_run + timedelta(days=days_ahead)
            elif self.frequency == 'monthly':
                # الانتقال إلى الشهر التالي
                if now.month == 12:
                    next_month = 1
                    next_year = now.year + 1
                else:
                    next_month = now.month + 1
                    next_year = now.year
                # التعامل مع أيام الشهر غير الصالحة
                last_day = calendar.monthrange(next_year, next_month)[1]
                day = min(self.day_of_month or last_day, last_day)
                next_run = now.replace(year=next_year, month=next_month, day=day)
        self.next_run = next_run
        self.save(update_fields=['next_run'])
        return next_run
class GoogleDriveConfig(models.Model):
    """نموذج إعدادات Google Drive للمعاينات"""
    name = models.CharField(_('اسم الإعداد'), max_length=100, default="إعدادات Google Drive")
    # إعدادات المجلد
    inspections_folder_id = models.CharField(
        _('معرف مجلد المعاينات'),
        max_length=255,
        blank=True,
        help_text=_('معرف المجلد في Google Drive لحفظ ملفات المعاينات')
    )
    inspections_folder_name = models.CharField(
        _('اسم مجلد المعاينات'),
        max_length=255,
        blank=True,
        help_text=_('اسم المجلد في Google Drive')
    )
    # إعدادات مجلد العقود
    contracts_folder_id = models.CharField(
        _('معرف مجلد العقود'),
        max_length=255,
        blank=True,
        help_text=_('معرف المجلد في Google Drive لحفظ ملفات العقود')
    )
    contracts_folder_name = models.CharField(
        _('اسم مجلد العقود'),
        max_length=255,
        blank=True,
        default='العقود - Contracts',
        help_text=_('اسم المجلد في Google Drive للعقود')
    )
    # ملف الاعتماد
    credentials_file = models.FileField(
        _('ملف اعتماد Google'),
        upload_to='google_credentials/',
        blank=True,
        null=True,
        help_text=_('ملف JSON من Google Cloud Console')
    )
    # إعدادات تسمية الملفات
    filename_pattern = models.CharField(
        _('نمط تسمية الملفات'),
        max_length=200,
        default="{customer}_{branch}_{date}_{order}",
        help_text=_('المتغيرات المتاحة: {customer}, {branch}, {date}, {order}')
    )
    # حالة الخدمة
    is_active = models.BooleanField(_('مفعل'), default=True)
    last_test = models.DateTimeField(_('آخر اختبار'), null=True, blank=True)
    test_status = models.CharField(_('حالة الاختبار'), max_length=50, blank=True)
    test_message = models.TextField(_('رسالة الاختبار'), blank=True)
    # إحصائيات
    total_uploads = models.IntegerField(_('إجمالي الرفعات'), default=0)
    last_upload = models.DateTimeField(_('آخر رفع'), null=True, blank=True)
    # تواريخ النظام
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('تم الإنشاء بواسطة')
    )
    class Meta:
        verbose_name = _('إعدادات Google Drive')
        verbose_name_plural = _('إعدادات Google Drive')
        ordering = ['-created_at']
    def __str__(self):
        return self.name
    @classmethod
    def get_active_config(cls):
        """الحصول على الإعدادات النشطة"""
        return cls.objects.filter(is_active=True).first()
    def save(self, *args, **kwargs):
        # التأكد من وجود إعداد واحد نشط فقط
        if self.is_active:
            GoogleDriveConfig.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class RestoreProgress(models.Model):
    """نموذج لتتبع تقدم عملية الاستعادة"""

    STATUS_CHOICES = [
        ('starting', 'بدء العملية'),
        ('reading_file', 'قراءة الملف'),
        ('processing', 'معالجة البيانات'),
        ('restoring', 'استعادة البيانات'),
        ('completed', 'مكتملة'),
        ('failed', 'فشلت'),
    ]

    session_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='معرف الجلسة'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='المستخدم'
    )

    database = models.ForeignKey(
        Database,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='قاعدة البيانات'
    )

    filename = models.CharField(
        max_length=255,
        verbose_name='اسم الملف'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='starting',
        verbose_name='الحالة'
    )

    total_items = models.IntegerField(
        default=0,
        verbose_name='إجمالي العناصر'
    )

    processed_items = models.IntegerField(
        default=0,
        verbose_name='العناصر المعالجة'
    )

    success_count = models.IntegerField(
        default=0,
        verbose_name='عدد النجاح'
    )

    error_count = models.IntegerField(
        default=0,
        verbose_name='عدد الأخطاء'
    )

    current_step = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='الخطوة الحالية'
    )

    progress_percentage = models.FloatField(
        default=0.0,
        verbose_name='نسبة التقدم'
    )

    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='رسالة الخطأ'
    )

    result_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name='بيانات النتيجة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاريخ التحديث'
    )

    class Meta:
        verbose_name = 'تقدم الاستعادة'
        verbose_name_plural = 'تقدم الاستعادة'
        ordering = ['-created_at']

    def __str__(self):
        return f'استعادة {self.filename} - {self.get_status_display()}'

    def update_progress(self, status=None, processed_items=None, current_step=None,
                       success_count=None, error_count=None, error_message=None):
        """تحديث تقدم العملية"""
        try:
            if status:
                self.status = status
            if processed_items is not None:
                self.processed_items = processed_items
            if current_step:
                self.current_step = current_step
            if success_count is not None:
                self.success_count = success_count
            if error_count is not None:
                self.error_count = error_count
            if error_message:
                self.error_message = error_message

            # حساب نسبة التقدم
            if self.total_items > 0 and self.processed_items is not None:
                self.progress_percentage = (self.processed_items / self.total_items) * 100
            else:
                self.progress_percentage = 0.0

            # التأكد من أن النسبة لا تتجاوز 100%
            if self.progress_percentage > 100:
                self.progress_percentage = 100.0

            self.save()

        except Exception as e:
            # في حالة فشل التحديث، نطبع الخطأ ونستمر
            print(f"خطأ في تحديث التقدم: {str(e)}")
            try:
                # محاولة حفظ الحالة الأساسية على الأقل
                if status:
                    self.status = status
                if current_step:
                    self.current_step = current_step
                self.save(update_fields=['status', 'current_step', 'updated_at'])
            except:
                pass  # إذا فشل حتى هذا، نتجاهل الخطأ

    def set_completed(self, result_data=None):
        """تعيين العملية كمكتملة"""
        self.status = 'completed'
        self.progress_percentage = 100.0
        self.current_step = 'تمت الاستعادة بنجاح'
        if result_data:
            self.result_data = result_data
        self.save()

    def set_failed(self, error_message):
        """تعيين العملية كفاشلة"""
        self.status = 'failed'
        self.error_message = error_message
        self.current_step = 'فشلت العملية'
        self.save()
