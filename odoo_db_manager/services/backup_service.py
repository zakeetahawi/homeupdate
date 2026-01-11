"""
خدمة النسخ الاحتياطي
تحسين النظام ليشمل جميع البيانات وإمكانية التحميل والاستعادة من ملف
"""

import datetime
import gzip
import json
import os
import shutil
import subprocess
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.db import connection

from odoo_db_manager.models import Database


class BackupService:
    """خدمة النسخ الاحتياطي المحسنة"""

    # أنواع النسخ الاحتياطي
    BACKUP_TYPES = {
        "customers": "بيانات العملاء",
        "users": "بيانات المستخدمين",
        "settings": "إعدادات النظام",
        "full": "كل البيانات",
    }

    def create_backup(
        self, database_id, name=None, user=None, backup_type="full", is_scheduled=False
    ):
        """
        إنشاء نسخة احتياطية

        Args:
            database_id: معرف قاعدة البيانات
            name: اسم النسخة الاحتياطية (اختياري)
            user: المستخدم الذي أنشأ النسخة الاحتياطية
            backup_type: نوع النسخة الاحتياطية (customers, users, settings, full)
            is_scheduled: هل النسخة الاحتياطية مجدولة

        Returns:
            كائن النسخة الاحتياطية
        """
        # الحصول على قاعدة البيانات
        database = Database.objects.get(id=database_id)

        # إنشاء اسم النسخة الاحتياطية إذا لم يتم توفيره
        if not name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"{database.name}_{backup_type}_{timestamp}"

        # إنشاء مجلد النسخ الاحتياطي إذا لم يكن موجود
        backup_dir = os.path.join(settings.MEDIA_ROOT, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        # طباعة معلومات تشخيصية
        print(f"إنشاء نسخة احتياطية: {name}")
        print(f"نوع قاعدة البيانات: {database.db_type}")
        print(f"معلومات الاتصال: {database.connection_info}")

        # تحديد نوع النسخة الاحتياطية ومسار الملف
        if database.db_type == "sqlite3" or settings.DATABASES["default"][
            "ENGINE"
        ].endswith("sqlite3"):
            # استخدام نسخة مباشرة من ملف SQLite
            db_file = settings.DATABASES["default"]["NAME"]
            print(f"استخدام نسخة مباشرة من ملف SQLite: {db_file}")

            # إنشاء مسار ملف النسخة الاحتياطية
            file_path = os.path.join(backup_dir, f"{name}.sqlite3")
            print(f"مسار ملف النسخة الاحتياطية: {file_path}")

            # نسخ ملف قاعدة البيانات مباشرة
            try:
                shutil.copy2(db_file, file_path)
                print(f"تم نسخ ملف قاعدة البيانات بنجاح إلى: {file_path}")
            except Exception as e:
                print(f"حدث خطأ أثناء نسخ ملف قاعدة البيانات: {str(e)}")
                raise RuntimeError(f"فشل إنشاء النسخة الاحتياطية: {str(e)}")
        else:
            # إنشاء مسار ملف النسخة الاحتياطية
            file_path = os.path.join(backup_dir, f"{name}.json.gz")
            print(f"مسار ملف النسخة الاحتياطية: {file_path}")

            # استخدام Django dumpdata للنسخ الاحتياطي
            print("استخدام Django dumpdata لإنشاء النسخة الاحتياطية")
            self._create_django_backup(
                database=database, file_path=file_path, backup_type=backup_type
            )

        # الحصول على حجم الملف
        size = os.path.getsize(file_path)

        # إنشاء سجل النسخة الاحتياطية
        backup = Backup.objects.create(
            database=database,
            name=name,
            file_path=file_path,
            size=size,
            created_by=user,
            backup_type=backup_type,
            is_scheduled=is_scheduled,
        )

        return backup

    def _create_django_backup(self, database, file_path, backup_type="full"):
        """
        إنشاء نسخة احتياطية باستخدام Django dumpdata أو pg_dump

        Args:
            database: كائن قاعدة البيانات
            file_path: مسار ملف النسخة الاحتياطية
            backup_type: نوع النسخة الاحتياطية
        """
        # التحقق من نوع قاعدة البيانات
        db_settings = settings.DATABASES["default"]
        is_postgresql = "postgresql" in db_settings["ENGINE"]

        # إذا كانت قاعدة البيانات PostgreSQL، نحاول استخدام pg_dump أولاً
        if is_postgresql:
            print(
                "محاولة استخدام pg_dump لإنشاء نسخة احتياطية من قاعدة بيانات PostgreSQL..."
            )

            # استخراج معلومات الاتصال من الإعدادات
            db_name = db_settings["NAME"]
            db_user = db_settings["USER"]
            db_password = db_settings["PASSWORD"]
            db_host = db_settings["HOST"] or "localhost"
            db_port = db_settings["PORT"] or "5432"

            try:
                # محاولة إنشاء النسخة الاحتياطية باستخدام pg_dump
                success = self._create_postgresql_backup(
                    database_name=db_name,
                    user=db_user,
                    password=db_password,
                    host=db_host,
                    port=db_port,
                    file_path=file_path,
                )

                if success:
                    return True
            except Exception as e:
                # إذا فشل pg_dump، نطبع الخطأ ونستخدم الطريقة البديلة
                print(f"فشل استخدام pg_dump: {str(e)}")
                print("استخدام الطريقة البديلة...")

        # إذا لم تكن قاعدة البيانات PostgreSQL أو فشل pg_dump، نستخدم الطريقة البديلة
        print("استخدام طريقة Django dumpdata كبديل...")

        # تحديد التطبيقات والنماذج المطلوبة حسب نوع النسخة الاحتياطية
        include_models = []

        if backup_type == "customers":
            include_models = [
                "customers.Customer",
                "customers.CustomerContact",
                "customers.CustomerAddress",
            ]
        elif backup_type == "users":
            include_models = ["auth.User", "auth.Group", "accounts.UserProfile"]
        elif backup_type == "settings":
            include_models = ["sites.Site", "auth.Permission"]
            # يمكن إضافة المزيد من نماذج الإعدادات حسب الحاجة
        elif backup_type == "full":
            # للنسخة الكاملة، نشمل جميع التطبيقات الأساسية
            include_models = [
                "accounts",
                "customers",
                "orders",
                "inspections",
                "inventory",
                "installations",
                "manufacturing",
                "reports",
                "odoo_db_manager",
            ]
            print(f"نسخة كاملة - سيتم تضمين {len(include_models)} تطبيق")

        # استخدام ملف مؤقت للبيانات
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, "backup.json")

        try:
            # طباعة معلومات تشخيصية
            print(f"إنشاء نسخة احتياطية باستخدام طريقة بديلة")
            print(f"نوع النسخة الاحتياطية: {backup_type}")
            print(f"مسار الملف المؤقت: {temp_path}")
            print(f"مسار الملف النهائي: {file_path}")

            # استخدام طريقة بديلة تمامًا لتجنب مشكلة الترميز
            try:
                print("استخدام طريقة بديلة لتجنب مشكلة الترميز...")

                # استخدام Python لتنفيذ الأمر وحفظ المخرجات مباشرة
                import json

                from django.core.serializers import serialize

                # تحديد النماذج المطلوبة
                if backup_type == "full":
                    # الحصول على جميع النماذج المسجلة
                    from django.apps import apps

                    all_models = []
                    for app_config in apps.get_app_configs():
                        for model in app_config.get_models():
                            # استثناء النماذج المحددة
                            if app_config.label != "contenttypes" and not (
                                app_config.label == "admin"
                                and model.__name__ == "LogEntry"
                            ):
                                all_models.append(model)

                    # تسلسل كل نموذج على حدة
                    all_data = []
                    for model in all_models:
                        try:
                            # الحصول على جميع الكائنات
                            queryset = model.objects.using("default").all()
                            # تسلسل الكائنات
                            model_data = serialize(
                                "python",
                                queryset,
                                use_natural_foreign_keys=True,
                                use_natural_primary_keys=True,
                            )
                            all_data.extend(model_data)
                        except Exception as model_error:
                            print(f"تخطي نموذج {model.__name__}: {str(model_error)}")
                else:
                    # تسلسل النماذج المحددة فقط
                    all_data = []
                    for model_name in include_models:
                        try:
                            app_label, model_name = model_name.split(".")
                            model = apps.get_model(app_label, model_name)
                            queryset = model.objects.using("default").all()
                            model_data = serialize(
                                "python",
                                queryset,
                                use_natural_foreign_keys=True,
                                use_natural_primary_keys=True,
                            )
                            all_data.extend(model_data)
                        except Exception as model_error:
                            print(f"تخطي نموذج {model_name}: {str(model_error)}")

                # تعريف دالة مساعدة لتحويل كائنات datetime و Decimal إلى سلاسل نصية
                def json_serial(obj):
                    """تحويل كائنات Python إلى JSON"""
                    import decimal

                    if isinstance(obj, (datetime.datetime, datetime.date)):
                        return obj.isoformat()
                    elif isinstance(obj, decimal.Decimal):
                        return float(obj)  # تحويل Decimal إلى float
                    raise TypeError(f"النوع {type(obj)} غير قابل للتحويل إلى JSON")

                # كتابة البيانات إلى الملف المؤقت
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(
                        all_data, f, ensure_ascii=False, indent=2, default=json_serial
                    )

                print(f"تم كتابة البيانات إلى الملف المؤقت: {temp_path}")

            except Exception as e:
                print(f"حدث خطأ أثناء إنشاء النسخة الاحتياطية: {str(e)}")
                raise RuntimeError(f"فشل إنشاء النسخة الاحتياطية: {str(e)}")

            # التحقق من وجود الملف المؤقت
            if not os.path.exists(temp_path):
                raise FileNotFoundError(
                    f"لم يتم إنشاء ملف النسخة الاحتياطية المؤقت: {temp_path}"
                )

            # التحقق من حجم الملف المؤقت
            temp_size = os.path.getsize(temp_path)
            print(f"حجم ملف النسخة الاحتياطية المؤقت: {temp_size} بايت")

            if temp_size == 0:
                raise ValueError("ملف النسخة الاحتياطية المؤقت فارغ")

            # ضغط الملف مع مراعاة الترميز
            print("ضغط الملف...")
            with open(temp_path, "rb") as f_in:
                with gzip.open(file_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # التحقق من وجود الملف النهائي
            if not os.path.exists(file_path):
                raise FileNotFoundError(
                    f"لم يتم إنشاء ملف النسخة الاحتياطية النهائي: {file_path}"
                )

            # التحقق من حجم الملف النهائي
            final_size = os.path.getsize(file_path)
            print(f"حجم ملف النسخة الاحتياطية النهائي: {final_size} بايت")

            if final_size == 0:
                raise ValueError("ملف النسخة الاحتياطية النهائي فارغ")

            print("تم إنشاء النسخة الاحتياطية بنجاح")
            return True
        except Exception as e:
            print(f"حدث خطأ أثناء إنشاء النسخة الاحتياطية: {str(e)}")
            raise RuntimeError(f"فشل إنشاء النسخة الاحتياطية: {str(e)}")
        finally:
            # حذف الملفات المؤقتة
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                print(f"تم حذف الملف المؤقت: {temp_path}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"تم حذف المجلد المؤقت: {temp_dir}")

    def _create_postgresql_backup(
        self, database_name, user, password, host, port, file_path
    ):
        """إنشاء نسخة احتياطية لقاعدة بيانات PostgreSQL"""
        # إنشاء النسخة الاحتياطية باستخدام pg_dump
        env = os.environ.copy()
        env["PGPASSWORD"] = password

        # طباعة معلومات تشخيصية
        print(f"إنشاء نسخة احتياطية لقاعدة بيانات PostgreSQL: {database_name}")
        print(f"المضيف: {host}:{port}")
        print(f"المستخدم: {user}")
        print(f"كلمة المرور: {password}")
        print(f"مسار الملف: {file_path}")

        # فحص حجم قاعدة البيانات قبل النسخ
        db_size = self._get_postgresql_database_size(
            database_name, user, password, host, port
        )
        print(f"حجم قاعدة البيانات: {db_size:,} بايت ({db_size/1024/1024:.2f} MB)")

        # تأكد من أن جميع المعلمات هي سلاسل نصية
        port_str = str(port)

        # محاولة استخدام طريقة بديلة - استخدام psql مع COPY
        try:
            # إنشاء ملف SQL مؤقت
            temp_sql_file = f"{file_path}.sql"

            # إنشاء أمر لتصدير البيانات بتنسيق SQL (نسخة كاملة محسنة)
            dump_cmd = [
                "pg_dump",
                "-h",
                str(host),
                "-p",
                port_str,
                "-U",
                str(user),
                "--format=plain",  # تنسيق SQL نصي
                "--inserts",  # استخدام INSERT بدلاً من COPY لضمان قابلية القراءة
                "--column-inserts",  # تضمين أسماء الأعمدة في INSERT
                "--no-owner",  # بدون معلومات المالك
                "--no-privileges",  # بدون صلاحيات
                "--create",  # تضمين أوامر CREATE للجداول
                "--clean",  # تضمين أوامر DROP قبل CREATE
                "--if-exists",  # استخدام IF EXISTS مع DROP
                "--verbose",  # إظهار تفاصيل العملية
                str(database_name),
            ]

            print(f"الأمر: {' '.join(dump_cmd)}")

            # تنفيذ الأمر وحفظ المخرجات في ملف SQL
            print("بدء تنفيذ pg_dump...")
            result = subprocess.run(
                dump_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,  # لا نريد رفع استثناء فوراً
                text=True,
                encoding="utf-8",
            )

            # التحقق من نجاح العملية
            if result.returncode != 0:
                error_msg = result.stderr
                print(f"خطأ في pg_dump: {error_msg}")
                raise subprocess.CalledProcessError(
                    result.returncode, dump_cmd, stderr=error_msg
                )

            # كتابة المخرجات إلى الملف المؤقت
            with open(temp_sql_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)

            # التحقق من حجم الملف المؤقت
            temp_size = os.path.getsize(temp_sql_file)
            print(f"حجم ملف SQL المؤقت: {temp_size:,} بايت")

            if temp_size < 1000:  # أقل من 1KB يعتبر صغير جداً
                print("تحذير: حجم النسخة الاحتياطية صغير جداً! قد تكون هناك مشكلة.")
                # عرض محتوى الملف للتشخيص
                with open(temp_sql_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    print(f"محتوى الملف: {content[:500]}...")

            # ضغط الملف
            print("ضغط الملف...")
            with open(temp_sql_file, "rb") as f_in:
                with gzip.open(file_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # التحقق من حجم الملف المضغوط
            compressed_size = os.path.getsize(file_path)
            print(f"حجم الملف المضغوط: {compressed_size:,} بايت")

            # حذف الملف المؤقت
            if os.path.exists(temp_sql_file):
                os.unlink(temp_sql_file)

            print(f"تم إنشاء النسخة الاحتياطية بنجاح: {file_path}")
            print(f"نسبة الضغط: {(temp_size/compressed_size):.1f}:1")
            return True

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if hasattr(e, "stderr") else str(e)
            print(f"فشل إنشاء النسخة الاحتياطية: {error_msg}")

            # إذا كان الخطأ بسبب عدم تطابق الإصدارات، نستخدم طريقة Django
            if "server version mismatch" in error_msg:
                print(
                    "تم اكتشاف عدم تطابق إصدارات PostgreSQL. استخدام طريقة Django بدلاً من ذلك."
                )
                return False

            raise RuntimeError(f"فشل إنشاء النسخة الاحتياطية: {error_msg}")

    def _get_postgresql_database_size(self, database_name, user, password, host, port):
        """الحصول على حجم قاعدة البيانات PostgreSQL"""
        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = password

            # استعلام لحساب حجم قاعدة البيانات
            size_query = f"SELECT pg_database_size('{database_name}');"

            # تنفيذ الاستعلام
            result = subprocess.run(
                [
                    "psql",
                    "-h",
                    str(host),
                    "-p",
                    str(port),
                    "-U",
                    str(user),
                    "-d",
                    str(database_name),
                    "-t",  # بدون رؤوس
                    "-c",
                    size_query,
                ],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            # استخراج الحجم من النتيجة
            size_str = result.stdout.strip()
            return int(size_str) if size_str.isdigit() else 0

        except Exception as e:
            print(f"فشل في الحصول على حجم قاعدة البيانات: {str(e)}")
            return 0

    def _create_sqlite_backup(self, database, file_path, backup_type="full"):
        """
        إنشاء نسخة احتياطية لقاعدة بيانات SQLite

        Args:
            database: كائن قاعدة البيانات
            file_path: مسار ملف النسخة الاحتياطية
            backup_type: نوع النسخة الاحتياطية
        """
        # استخدام نفس طريقة Django dumpdata
        self._create_django_backup(database, file_path, backup_type)

    def restore_backup(self, backup_id, clear_data=False, create_new_database=True):
        """
        استعادة نسخة احتياطية مع إنشاء قاعدة بيانات جديدة

        Args:
            backup_id: معرف النسخة الاحتياطية
            clear_data: هل يتم حذف البيانات القديمة قبل الاستعادة (مهمل - سيتم إنشاء قاعدة جديدة)
            create_new_database: إنشاء قاعدة بيانات جديدة مطابقة للنسخة المستعادة (افتراضي: True)

        Returns:
            True إذا تمت الاستعادة بنجاح
        """
        try:
            # الحصول على النسخة الاحتياطية
            backup = Backup.objects.get(id=backup_id)
            database = backup.database

            # طباعة معلومات تشخيصية
            print(f"استعادة النسخة الاحتياطية: {backup.name}")
            print(f"نوع النسخة الاحتياطية: {backup.backup_type}")
            print(f"مسار الملف: {backup.file_path}")
            print(f"نوع قاعدة البيانات: {database.db_type}")

            # التحقق من وجود الملف
            if not os.path.exists(backup.file_path):
                raise FileNotFoundError(
                    f"ملف النسخة الاحتياطية '{backup.file_path}' غير موجود"
                )

            # التحقق من نوع الملف
            file_info = self._check_file_type(backup.file_path)

            # إذا كان امتداد الملف .sqlite3، نضبط النوع على sqlite3 بغض النظر عن ما تم اكتشافه
            if backup.file_path.endswith(".sqlite3"):
                file_info["type"] = "sqlite3"

            print(f"معلومات الملف: {file_info}")

            # التعامل مع ملفات pg_dump الثنائية
            if file_info["type"] == "pg_dump" and file_info["is_binary"]:
                print("تم اكتشاف ملف pg_dump ثنائي")
                if database.db_type == "postgresql":
                    # تحويل الملف الثنائي إلى SQL نصي
                    try:
                        converted_file_path = self._convert_binary_pg_dump_to_sql(
                            backup.file_path
                        )
                        print(
                            f"تم تحويل الملف الثنائي إلى SQL نصي: {converted_file_path}"
                        )

                        # استعادة من الملف المحول
                        self._restore_postgresql_backup(
                            database_name=database.connection_info.get(
                                "NAME", database.name
                            ),
                            user=database.connection_info.get("USER", ""),
                            password=database.connection_info.get("PASSWORD", ""),
                            host=database.connection_info.get("HOST", "localhost"),
                            port=database.connection_info.get("PORT", "5432"),
                            file_path=converted_file_path,
                        )

                        # حذف الملف المحول بعد الانتهاء
                        if os.path.exists(converted_file_path):
                            os.unlink(converted_file_path)
                            print(f"تم حذف الملف المحول: {converted_file_path}")
                    except Exception as e:
                        print(f"فشل تحويل أو استعادة الملف الثنائي: {str(e)}")
                        raise RuntimeError(f"فشل استعادة ملف pg_dump الثنائي: {str(e)}")
                else:
                    # ملفات pg_dump الثنائية غير مدعومة لقواعد بيانات غير PostgreSQL
                    raise ValueError(
                        f"لا يمكن استعادة ملفات pg_dump الثنائية لقواعد بيانات من نوع {database.db_type}. "
                        f"يرجى استخدام ملفات JSON.gz بدلاً من ذلك."
                    )
            # استعادة النسخة الاحتياطية حسب نوع الملف
            elif file_info["type"] == "sqlite3":
                # استعادة من ملف SQLite3
                print("استعادة من ملف SQLite3")

                # التحقق من وجود الملف
                if not os.path.exists(backup.file_path):
                    raise FileNotFoundError(
                        f"ملف النسخة الاحتياطية '{backup.file_path}' غير موجود"
                    )

                # الحصول على مسار ملف قاعدة البيانات الحالية
                db_file = settings.DATABASES["default"]["NAME"]
                print(f"مسار ملف قاعدة البيانات الحالية: {db_file}")

                # حفظ معلومات النسخة الاحتياطية قبل استعادتها
                backup_info = {
                    "id": backup.id,
                    "name": backup.name,
                    "database_id": backup.database.id,
                    "backup_type": backup.backup_type,
                    "file_path": backup.file_path,
                    "created_at": backup.created_at,
                    "created_by_id": (
                        backup.created_by.id if backup.created_by else None
                    ),
                }

                # إنشاء نسخة احتياطية من قاعدة البيانات الحالية قبل الاستبدال
                backup_current_db = f"{db_file}.bak"
                print(
                    f"إنشاء نسخة احتياطية من قاعدة البيانات الحالية: {backup_current_db}"
                )
                shutil.copy2(db_file, backup_current_db)

                try:
                    # نسخ ملف النسخة الاحتياطية إلى مسار قاعدة البيانات الحالية
                    print(f"استعادة قاعدة البيانات من: {backup.file_path}")
                    shutil.copy2(backup.file_path, db_file)
                    print("تمت استعادة قاعدة البيانات بنجاح")

                    # إعادة إنشاء سجل النسخة الاحتياطية في قاعدة البيانات الجديدة

                    # الحصول على قاعدة البيانات
                    try:
                        db = Database.objects.get(id=backup_info["database_id"])
                    except Database.DoesNotExist:
                        # إذا لم تكن قاعدة البيانات موجودة، نستخدم أول قاعدة بيانات متاحة
                        db = Database.objects.first()
                        if not db:
                            # إذا لم تكن هناك قواعد بيانات، نقوم بإنشاء واحدة
                            db = Database.objects.create(
                                name="Default Database",
                                db_type="sqlite3",
                                connection_info={},
                            )

                    # الحصول على المستخدم
                    user_id = backup_info["created_by_id"]
                    user = None
                    if user_id:
                        try:
                            user = User.objects.get(id=user_id)
                        except User.DoesNotExist:
                            # إذا لم يكن المستخدم موجودًا، نستخدم أول مستخدم متاح
                            user = User.objects.first()

                    # إعادة إنشاء سجل النسخة الاحتياطية
                    try:
                        Backup.objects.get(id=backup_info["id"])
                        print(
                            f"سجل النسخة الاحتياطية موجود بالفعل: {backup_info['id']}"
                        )
                    except Backup.DoesNotExist:
                        print(f"إعادة إنشاء سجل النسخة الاحتياطية: {backup_info['id']}")
                        Backup.objects.create(
                            id=backup_info["id"],
                            name=backup_info["name"],
                            database=db,
                            backup_type=backup_info["backup_type"],
                            file_path=backup_info["file_path"],
                            created_at=backup_info["created_at"],
                            created_by=user,
                        )
                except Exception as e:
                    # استعادة النسخة الاحتياطية في حالة حدوث خطأ
                    print(f"حدث خطأ أثناء استعادة قاعدة البيانات: {str(e)}")
                    print(f"استعادة النسخة الاحتياطية من: {backup_current_db}")
                    shutil.copy2(backup_current_db, db_file)
                    raise RuntimeError(f"فشل استعادة قاعدة البيانات: {str(e)}")
                finally:
                    # حذف النسخة الاحتياطية المؤقتة
                    if os.path.exists(backup_current_db):
                        os.unlink(backup_current_db)
                        print(f"تم حذف النسخة الاحتياطية المؤقتة: {backup_current_db}")

            elif file_info["type"] == "json_gz":
                # استعادة من ملف JSON مضغوط
                print("استعادة من ملف JSON مضغوط")
                self._restore_from_json(backup, clear_data)
            elif file_info["type"] == "sql":
                # استعادة من ملف SQL
                print("استعادة من ملف SQL")
                if database.db_type == "postgresql":
                    # استعادة من ملف SQL لقاعدة بيانات PostgreSQL
                    print("استخدام PostgreSQL لاستعادة ملف SQL")
                    self._restore_postgresql_backup(
                        database_name=database.connection_info.get(
                            "NAME", database.name
                        ),
                        user=database.connection_info.get("USER", ""),
                        password=database.connection_info.get("PASSWORD", ""),
                        host=database.connection_info.get("HOST", "localhost"),
                        port=database.connection_info.get("PORT", "5432"),
                        file_path=backup.file_path,
                    )
                else:
                    # ملفات SQL غير مدعومة لقواعد بيانات غير PostgreSQL
                    raise ValueError(
                        f"لا يمكن استعادة ملفات SQL لقواعد بيانات من نوع {database.db_type}. "
                        f"يرجى استخدام ملفات JSON.gz بدلاً من ذلك."
                    )
            elif file_info["type"] == "django_fixture":
                # محاولة استعادة الملف باستخدام Django loaddata مباشرة
                print(
                    f"محاولة استعادة الملف باستخدام Django loaddata مباشرة: {backup.file_path}"
                )
                try:
                    # التحقق من صحة ملف JSON قبل الاستعادة
                    self._validate_json_file(backup.file_path)

                    # تجاهل حذف البيانات القديمة لتجنب مشاكل flush
                    if clear_data:
                        print(
                            "تم تجاهل حذف البيانات القديمة لتجنب مشاكل قاعدة البيانات"
                        )

                    call_command("loaddata", backup.file_path, database="default")
                except Exception as e:
                    error_msg = str(e)
                    print(f"خطأ في استعادة الملف: {error_msg}")

                    if "not a known serialization format" in error_msg:
                        raise ValueError(
                            f"فشل استعادة الملف: الملف ليس بتنسيق مدعوم من Django. "
                            f"يرجى التأكد من أن الملف بتنسيق JSON أو XML أو YAML صالح."
                        )
                    elif "Problem installing fixture" in error_msg:
                        raise ValueError(
                            f"فشل تثبيت البيانات من الملف. قد يكون هناك تضارب في البيانات أو مشكلة في تنسيق الملف. "
                            f"تفاصيل الخطأ: {error_msg}"
                        )
                    else:
                        raise
            elif file_info["type"] == "gzip":
                # محاولة فك ضغط الملف واستعادته
                print("محاولة فك ضغط الملف واستعادته")
                with tempfile.NamedTemporaryFile(
                    suffix=".json", delete=False
                ) as temp_file:
                    temp_path = temp_file.name

                try:
                    # فك ضغط الملف
                    with gzip.open(backup.file_path, "rb") as f_in:
                        with open(temp_path, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    # التحقق من صحة ملف JSON المفكوك
                    self._validate_json_file(temp_path)

                    # تجاهل حذف البيانات القديمة لتجنب مشاكل flush
                    if clear_data:
                        print(
                            "تم تجاهل حذف البيانات القديمة لتجنب مشاكل قاعدة البيانات"
                        )

                    # استعادة الملف المفكوك
                    call_command("loaddata", temp_path, database="default")
                except Exception as e:
                    error_msg = str(e)
                    print(f"خطأ في استعادة الملف المضغوط: {error_msg}")

                    if "Problem installing fixture" in error_msg:
                        raise ValueError(
                            f"فشل تثبيت البيانات من الملف المضغوط. قد يكون هناك تضارب في البيانات أو مشكلة في تنسيق الملف. "
                            f"تفاصيل الخطأ: {error_msg}"
                        )
                    else:
                        raise
                finally:
                    # حذف الملف المؤقت
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            else:
                # نوع ملف غير معروف
                raise ValueError(
                    f"نوع الملف '{file_info['type']}' (امتداد: {file_info['extension']}) غير مدعوم للاستعادة. "
                    f"الأنواع المدعومة هي: json_gz, django_fixture, sql, pg_dump (لقواعد بيانات PostgreSQL فقط)"
                )

            print("تمت استعادة النسخة الاحتياطية بنجاح")
            return True

        except Exception as e:
            print(f"حدث خطأ أثناء استعادة النسخة الاحتياطية: {str(e)}")
            # إعادة رفع الاستثناء ليتم التعامل معه في المستوى الأعلى
            raise RuntimeError(f"فشل استعادة النسخة الاحتياطية: {str(e)}")

    def _restore_from_json(self, backup, clear_data=False):
        """
        استعادة من ملف JSON مضغوط

        Args:
            backup: كائن النسخة الاحتياطية
            clear_data: هل يتم حذف البيانات القديمة قبل الاستعادة
        """
        # استخدام ملف مؤقت للبيانات
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # فك ضغط الملف
            with gzip.open(backup.file_path, "rb") as f_in:
                with open(temp_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # تحديد قاعدة البيانات المستهدفة
            # استخدام 'default' كاسم للاتصال، وليس اسم قاعدة البيانات
            database_connection = "default"

            # طباعة معلومات تشخيصية
            print(
                f"استعادة النسخة الاحتياطية باستخدام اتصال قاعدة البيانات: {database_connection}"
            )
            print(f"نوع النسخة الاحتياطية: {backup.backup_type}")
            print(f"مسار الملف: {temp_path}")

            # تجاهل حذف البيانات القديمة لتجنب مشاكل flush
            if clear_data:
                print("تم تجاهل حذف البيانات القديمة لتجنب مشاكل قاعدة البيانات")

            # استعادة البيانات
            call_command("loaddata", temp_path, database=database_connection)

        finally:
            # حذف الملف المؤقت
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def _check_file_type(self, file_path):
        """
        التحقق من نوع الملف وإرجاع معلومات عنه

        Args:
            file_path: مسار الملف

        Returns:
            dict: معلومات عن الملف (النوع، الامتداد، إلخ)
        """
        # التحقق من وجود الملف
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"الملف '{file_path}' غير موجود")

        # الحصول على امتداد الملف
        file_ext = os.path.splitext(file_path)[1].lower()

        # تحديد نوع الملف
        file_info = {
            "path": file_path,
            "extension": file_ext,
            "size": os.path.getsize(file_path),
            "type": "unknown",
            "is_binary": False,
        }

        # تحديد نوع الملف بناءً على الامتداد
        if file_path.endswith(".json.gz"):
            file_info["type"] = "json_gz"
        elif file_ext == ".sql":
            file_info["type"] = "sql"
        elif file_ext == ".sqlite3":
            file_info["type"] = "sqlite3"
        elif file_ext in [".json", ".xml", ".yaml", ".yml"]:
            file_info["type"] = "django_fixture"
        elif file_ext == ".dump":
            file_info["type"] = "pg_dump"
            file_info["is_binary"] = True

        # التحقق من محتوى الملف إذا كان الامتداد غير واضح
        if file_info["size"] > 0:
            try:
                # قراءة أول 1024 بايت من الملف
                with open(file_path, "rb") as f:
                    header = f.read(1024)

                # التحقق مما إذا كان الملف مضغوطًا
                if header.startswith(b"\x1f\x8b"):  # بداية ملفات GZIP
                    file_info["type"] = "gzip"
                # التحقق مما إذا كان الملف JSON
                elif header.strip().startswith(b"{") or header.strip().startswith(b"["):
                    file_info["type"] = "django_fixture"
                # التحقق مما إذا كان الملف SQL نصي
                elif (
                    b"CREATE TABLE" in header
                    or b"INSERT INTO" in header
                    or b"SELECT" in header
                ):
                    file_info["type"] = "sql"
                # التحقق مما إذا كان الملف pg_dump بتنسيق مخصص
                elif header.startswith(b"PGDMP") or b"PGCOPY" in header:
                    file_info["type"] = "pg_dump"
                    file_info["is_binary"] = True
                    # إذا كان امتداد الملف .sql ولكنه ملف ثنائي، نغير النوع
                    if file_ext == ".sql":
                        print(f"تم اكتشاف ملف SQL ثنائي: {file_path}")
                # التحقق من وجود أحرف غير مقروءة (قد يكون ملف ثنائي)
                elif file_ext == ".sql" and any(b > 127 for b in header[:100]):
                    file_info["type"] = "pg_dump"
                    file_info["is_binary"] = True
                    print(f"تم اكتشاف ملف SQL ثنائي: {file_path}")
            except Exception as e:
                print(f"حدث خطأ أثناء فحص محتوى الملف: {str(e)}")
                # إذا فشلت القراءة، نبقي النوع غير معروف
                pass

        return file_info

    def _validate_json_file(self, file_path):
        """
        فحص بسيط للملف - بدون تحققات معقدة
        """
        # فحص وجود الملف فقط
        if not os.path.exists(file_path):
            raise ValueError(f"الملف غير موجود: {file_path}")

        # فحص حجم الملف
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("الملف فارغ")

        print(f"الملف موجود وحجمه: {file_size} بايت")

    def _convert_binary_pg_dump_to_sql(self, file_path):
        """
        تحويل ملف pg_dump ثنائي إلى ملف SQL نصي

        Args:
            file_path: مسار ملف pg_dump الثنائي

        Returns:
            str: مسار ملف SQL النصي الجديد
        """
        # التحقق من وجود أداة pg_restore
        if not self._check_command_exists("pg_restore"):
            raise RuntimeError(
                "أداة pg_restore غير موجودة. يرجى التأكد من تثبيت PostgreSQL وإضافته إلى مسار النظام."
            )

        # إنشاء مسار الملف الجديد
        new_file_path = file_path + ".converted.sql"

        # تحويل الملف باستخدام pg_restore
        convert_cmd = [
            "pg_restore",
            "--no-owner",
            "--no-privileges",
            "--no-tablespaces",
            "--format=c",
            "--file=" + new_file_path,
            file_path,
        ]

        try:
            print(f"تحويل ملف pg_dump الثنائي إلى SQL نصي: {file_path}")
            print(f"الأمر: {' '.join(convert_cmd)}")

            result = subprocess.run(
                convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # التحقق من نجاح العملية
            if result.returncode != 0:
                stderr_output = result.stderr.decode()
                stdout_output = result.stdout.decode()

                print(f"فشل تحويل ملف pg_dump الثنائي")
                print(f"رمز الخروج: {result.returncode}")
                print(f"الخطأ: {stderr_output}")
                print(f"المخرجات: {stdout_output}")

                # محاولة استخدام طريقة أخرى
                print("محاولة استخدام طريقة أخرى للتحويل...")

                # استخدام pg_restore مع إخراج إلى ملف مباشرة
                convert_cmd2 = [
                    "pg_restore",
                    "--no-owner",
                    "--no-privileges",
                    "--no-tablespaces",
                    "--schema-only",
                    file_path,
                ]

                with open(new_file_path, "w") as f:
                    result2 = subprocess.run(
                        convert_cmd2, stdout=f, stderr=subprocess.PIPE
                    )

                if result2.returncode != 0:
                    stderr_output2 = result2.stderr.decode()
                    print(f"فشل التحويل باستخدام الطريقة الثانية: {stderr_output2}")
                    raise RuntimeError(
                        f"فشل تحويل ملف pg_dump الثنائي: {stderr_output}"
                    )

            print(f"تم تحويل الملف بنجاح إلى: {new_file_path}")
            return new_file_path
        except Exception as e:
            print(f"حدث خطأ أثناء تحويل ملف pg_dump الثنائي: {str(e)}")
            raise RuntimeError(f"فشل تحويل ملف pg_dump الثنائي: {str(e)}")

    def _check_command_exists(self, command):
        """التحقق من وجود أمر في النظام"""
        try:
            subprocess.run(
                ["where", command] if os.name == "nt" else ["which", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def _restore_postgresql_backup(
        self, database_name, user, password, host, port, file_path
    ):
        """استعادة نسخة احتياطية لقاعدة بيانات PostgreSQL"""
        # التحقق من وجود الأدوات المطلوبة
        if not self._check_command_exists("psql"):
            raise RuntimeError(
                "أداة psql غير موجودة. يرجى التأكد من تثبيت PostgreSQL وإضافته إلى مسار النظام."
            )

        # التحقق من نوع الملف
        if not file_path.endswith(".sql"):
            raise ValueError(
                f"الملف '{file_path}' ليس ملف SQL. يجب أن ينتهي الملف بامتداد .sql"
            )

        # التحقق من وجود الملف
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"ملف SQL '{file_path}' غير موجود")

        # استخدام معلومات الاتصال من ملف .env إذا كانت فارغة
        if not user:
            user = os.environ.get("DB_USER", "postgres")

        if not password:
            password = os.environ.get("DB_PASSWORD", "5525")

        # طباعة معلومات تشخيصية
        print(f"استعادة قاعدة بيانات PostgreSQL: {database_name}")
        print(f"المضيف: {host}:{port}")
        print(f"المستخدم: {user}")
        print(f"ملف SQL: {file_path}")

        # استعادة النسخة الاحتياطية باستخدام psql
        env = os.environ.copy()
        env["PGPASSWORD"] = password

        # استخدام psql لاستعادة ملف SQL
        restore_cmd = [
            "psql",
            "-h",
            host,
            "-p",
            port,
            "-U",
            user,
            "-d",
            database_name,
            "-f",
            file_path,
        ]

        try:
            # محاولة استعادة النسخة الاحتياطية
            print(f"تنفيذ الأمر: {' '.join(restore_cmd)}")
            result = subprocess.run(
                restore_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # التحقق من نجاح العملية
            if result.returncode != 0:
                stderr_output = result.stderr.decode()
                stdout_output = result.stdout.decode()

                print(f"فشل استعادة النسخة الاحتياطية باستخدام psql")
                print(f"رمز الخروج: {result.returncode}")
                print(f"الخطأ: {stderr_output}")
                print(f"المخرجات: {stdout_output}")

                # إذا كان الخطأ يتعلق بتنسيق الملف، نحاول استخدام Django loaddata
                if (
                    "syntax error" in stderr_output
                    or "not a known serialization format" in stderr_output
                ):
                    print(
                        "يبدو أن الملف ليس ملف SQL صالح. محاولة معالجته كملف بيانات Django..."
                    )

                    # التحقق من امتداد الملف
                    file_ext = os.path.splitext(file_path)[1].lower()
                    if file_ext in [".json", ".xml", ".yaml", ".yml"]:
                        print(
                            f"محاولة استعادة الملف باستخدام Django loaddata: {file_path}"
                        )
                        call_command("loaddata", file_path, database="default")
                        return True
                    else:
                        raise ValueError(
                            f"فشل استعادة الملف. الملف ليس ملف SQL صالح ولا ملف بيانات Django معروف. "
                            f"امتداد الملف: {file_ext}"
                        )
                else:
                    # خطأ آخر في PostgreSQL
                    raise RuntimeError(
                        f"فشل استعادة النسخة الاحتياطية باستخدام PostgreSQL: {stderr_output}"
                    )

            print("تمت استعادة النسخة الاحتياطية بنجاح باستخدام PostgreSQL")
            return True
        except subprocess.CalledProcessError as e:
            stderr_output = e.stderr.decode() if hasattr(e, "stderr") else str(e)
            raise RuntimeError(
                f"فشل تنفيذ أمر استعادة النسخة الاحتياطية: {stderr_output}"
            )
        except Exception as e:
            raise RuntimeError(
                f"حدث خطأ غير متوقع أثناء استعادة النسخة الاحتياطية: {str(e)}"
            )

    def restore_from_file(
        self, database_id, uploaded_file, backup_type="full", clear_data=False
    ):
        """
        استعادة من ملف تم تحميله

        Args:
            database_id: معرف قاعدة البيانات
            uploaded_file: الملف الذي تم تحميله
            backup_type: نوع النسخة الاحتياطية
            clear_data: هل يتم حذف البيانات القديمة قبل الاستعادة

        Returns:
            True إذا تمت الاستعادة بنجاح
        """
        # الحصول على قاعدة البيانات
        database = Database.objects.get(id=database_id)

        # إنشاء اسم للنسخة الاحتياطية
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{database.name}_uploaded_{timestamp}"

        # إنشاء مجلد النسخ الاحتياطي إذا لم يكن موجود
        backup_dir = os.path.join(settings.MEDIA_ROOT, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        # حفظ الملف المحمل مع تسجيل تفصيلي
        file_path = os.path.join(backup_dir, uploaded_file.name)
        print(f"حفظ الملف المرفوع: {file_path}")
        print(f"حجم الملف المرفوع: {uploaded_file.size} بايت")

        try:
            with open(file_path, "wb+") as destination:
                total_written = 0
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
                    total_written += len(chunk)
                print(f"تم كتابة {total_written} بايت إلى الملف")
        except Exception as e:
            print(f"خطأ في حفظ الملف: {str(e)}")
            raise

        # الحصول على حجم الملف بعد الحفظ
        size = os.path.getsize(file_path)
        print(f"حجم الملف بعد الحفظ: {size} بايت")

        # فحص سريع للملف
        if size == 0:
            raise ValueError(f"الملف المحفوظ فارغ: {file_path}")

        # قراءة أول 100 بايت للتحقق
        try:
            with open(file_path, "rb") as f:
                first_bytes = f.read(100)
            print(f"أول 100 بايت من الملف: {first_bytes[:50]}...")
        except Exception as e:
            print(f"خطأ في قراءة الملف للفحص: {str(e)}")

        # إنشاء سجل النسخة الاحتياطية
        backup = Backup.objects.create(
            database=database,
            name=name,
            file_path=file_path,
            size=size,
            backup_type=backup_type,
        )

        # استعادة النسخة الاحتياطية
        try:
            # طباعة معلومات تشخيصية
            print(f"استعادة من ملف محمل: {file_path}")
            print(f"نوع النسخة الاحتياطية: {backup_type}")
            print(f"نوع قاعدة البيانات: {database.db_type}")

            # التحقق من نوع الملف
            file_info = self._check_file_type(file_path)
            print(f"معلومات الملف: {file_info}")

            # التعامل مع ملفات pg_dump الثنائية
            if file_info["type"] == "pg_dump" and file_info["is_binary"]:
                print("تم اكتشاف ملف pg_dump ثنائي")
                if database.db_type == "postgresql":
                    # تحويل الملف الثنائي إلى SQL نصي
                    try:
                        converted_file_path = self._convert_binary_pg_dump_to_sql(
                            file_path
                        )
                        print(
                            f"تم تحويل الملف الثنائي إلى SQL نصي: {converted_file_path}"
                        )

                        # استعادة من الملف المحول
                        self._restore_postgresql_backup(
                            database_name=database.connection_info.get(
                                "NAME", database.name
                            ),
                            user=database.connection_info.get("USER", ""),
                            password=database.connection_info.get("PASSWORD", ""),
                            host=database.connection_info.get("HOST", "localhost"),
                            port=database.connection_info.get("PORT", "5432"),
                            file_path=converted_file_path,
                        )

                        # حذف الملف المحول بعد الانتهاء
                        if os.path.exists(converted_file_path):
                            os.unlink(converted_file_path)
                            print(f"تم حذف الملف المحول: {converted_file_path}")
                    except Exception as e:
                        print(f"فشل تحويل أو استعادة الملف الثنائي: {str(e)}")
                        raise RuntimeError(f"فشل استعادة ملف pg_dump الثنائي: {str(e)}")
                else:
                    # ملفات pg_dump الثنائية غير مدعومة لقواعد بيانات غير PostgreSQL
                    raise ValueError(
                        f"لا يمكن استعادة ملفات pg_dump الثنائية لقواعد بيانات من نوع {database.db_type}. "
                        f"يرجى استخدام ملفات JSON.gz بدلاً من ذلك."
                    )
            # استعادة النسخة الاحتياطية حسب نوع الملف
            elif file_info["type"] == "json_gz":
                # استعادة من ملف JSON مضغوط
                print("استعادة من ملف JSON مضغوط")
                self._restore_from_json(backup, clear_data)
            elif file_info["type"] == "sql":
                # استعادة من ملف SQL
                print("استعادة من ملف SQL")
                if database.db_type == "postgresql":
                    # استعادة من ملف SQL لقاعدة بيانات PostgreSQL
                    print("استخدام PostgreSQL لاستعادة ملف SQL")
                    self._restore_postgresql_backup(
                        database_name=database.connection_info.get(
                            "NAME", database.name
                        ),
                        user=database.connection_info.get("USER", ""),
                        password=database.connection_info.get("PASSWORD", ""),
                        host=database.connection_info.get("HOST", "localhost"),
                        port=database.connection_info.get("PORT", "5432"),
                        file_path=file_path,
                    )
                else:
                    # ملفات SQL غير مدعومة لقواعد بيانات غير PostgreSQL
                    raise ValueError(
                        f"لا يمكن استعادة ملفات SQL لقواعد بيانات من نوع {database.db_type}. "
                        f"يرجى استخدام ملفات JSON.gz بدلاً من ذلك."
                    )
            elif file_info["type"] == "django_fixture":
                # استعادة مباشرة باستخدام Django loaddata
                print(f"استعادة ملف JSON: {file_path}")
                try:
                    # تجاهل حذف البيانات القديمة لتجنب مشاكل flush
                    if clear_data:
                        print(
                            "تم تجاهل حذف البيانات القديمة لتجنب مشاكل قاعدة البيانات"
                        )

                    # استعادة مباشرة بدون فحص إضافي
                    call_command("loaddata", file_path, database="default", verbosity=2)
                    print("تمت الاستعادة بنجاح")

                except Exception as e:
                    error_msg = str(e)
                    print(f"خطأ في الاستعادة: {error_msg}")

                    # إعادة المحاولة مع تجاهل الأخطاء
                    try:
                        print("محاولة الاستعادة مع تجاهل الأخطاء...")
                        call_command(
                            "loaddata",
                            file_path,
                            database="default",
                            verbosity=2,
                            ignore=True,
                        )
                        print("تمت الاستعادة مع تجاهل بعض الأخطاء")
                    except Exception as e2:
                        print(f"فشل في الاستعادة نهائياً: {str(e2)}")
                        raise ValueError(
                            f"فشل في استعادة النسخة الاحتياطية: {error_msg}"
                        )
            elif file_info["type"] == "gzip":
                # محاولة فك ضغط الملف واستعادته
                print("محاولة فك ضغط الملف واستعادته")
                with tempfile.NamedTemporaryFile(
                    suffix=".json", delete=False
                ) as temp_file:
                    temp_path = temp_file.name

                try:
                    # فك ضغط الملف مع معالجة أفضل للأخطاء
                    try:
                        with gzip.open(file_path, "rt", encoding="utf-8") as f_in:
                            content = f_in.read()

                        # التحقق من أن المحتوى ليس فارغاً
                        if not content.strip():
                            raise ValueError(
                                "الملف المضغوط فارغ أو لا يحتوي على بيانات"
                            )

                        # كتابة المحتوى إلى الملف المؤقت
                        with open(temp_path, "w", encoding="utf-8") as f_out:
                            f_out.write(content)

                    except UnicodeDecodeError:
                        # محاولة فك الضغط بالطريقة التقليدية
                        with gzip.open(file_path, "rb") as f_in:
                            with open(temp_path, "wb") as f_out:
                                shutil.copyfileobj(f_in, f_out)

                    # التحقق من صحة ملف JSON المفكوك
                    self._validate_json_file(temp_path)

                    # تجاهل حذف البيانات القديمة لتجنب مشاكل flush
                    if clear_data:
                        print(
                            "تم تجاهل حذف البيانات القديمة لتجنب مشاكل قاعدة البيانات"
                        )

                    # استعادة الملف المفكوك
                    call_command("loaddata", temp_path, database="default")
                except Exception as e:
                    error_msg = str(e)
                    print(f"خطأ في استعادة الملف المضغوط: {error_msg}")

                    if "Problem installing fixture" in error_msg:
                        raise ValueError(
                            f"فشل تثبيت البيانات من الملف المضغوط. قد يكون هناك تضارب في البيانات أو مشكلة في تنسيق الملف. "
                            f"تفاصيل الخطأ: {error_msg}"
                        )
                    else:
                        raise
                finally:
                    # حذف الملف المؤقت
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
            else:
                # نوع ملف غير معروف
                raise ValueError(
                    f"نوع الملف '{file_info['type']}' (امتداد: {file_info['extension']}) غير مدعوم للاستعادة. "
                    f"الأنواع المدعومة هي: json_gz, django_fixture, sql, pg_dump (لقواعد بيانات PostgreSQL فقط)"
                )
            return True
        except Exception as e:
            # حذف سجل النسخة الاحتياطية في حالة فشل الاستعادة
            backup.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e

    def delete_backup(self, backup_id):
        """حذف نسخة احتياطية"""
        # الحصول على النسخة الاحتياطية
        backup = Backup.objects.get(id=backup_id)

        # حذف ملف النسخة الاحتياطية
        if os.path.exists(backup.file_path):
            os.remove(backup.file_path)

        # حذف سجل النسخة الاحتياطية
        backup.delete()

        return True
