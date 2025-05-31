"""
خدمة إدارة قواعد البيانات
"""

import os
import subprocess
import json
import sqlite3
import re
from django.conf import settings
from ..models import Database

class DatabaseService:
    """خدمة إدارة قواعد البيانات"""
    
    def activate_database(self, database_id):
        """تنشيط قاعدة بيانات باستخدام طريقة النموذج الجديدة"""
        try:
            # الحصول على قاعدة البيانات
            database = Database.objects.get(id=database_id)
            
            # استخدام طريقة activate الجديدة في النموذج
            return database.activate()
        except Exception as e:
            print(f"حدث خطأ أثناء تنشيط قاعدة البيانات: {str(e)}")
            raise

    def create_database(self, name, db_type, connection_info, force_create=False):
        """إنشاء قاعدة بيانات جديدة"""
        # التحقق من وجود قاعدة البيانات في النظام (وليس في PostgreSQL)
        if not force_create and Database.objects.filter(name=name).exists():
            raise ValueError(f"قاعدة البيانات '{name}' موجودة بالفعل في النظام")

        # تأكد من أن اسم قاعدة البيانات موجود في connection_info
        if db_type == 'postgresql':
            # إذا لم يتم تحديد اسم قاعدة البيانات، استخدم الاسم المدخل
            if 'NAME' not in connection_info or not connection_info['NAME']:
                connection_info['NAME'] = name

            # طباعة معلومات تشخيصية
            print(f"إنشاء قاعدة بيانات PostgreSQL: {name}")
            print(f"اسم قاعدة البيانات في PostgreSQL: {connection_info['NAME']}")
        elif db_type == 'sqlite3':
            # إذا لم يتم تحديد اسم ملف SQLite، استخدم الاسم المدخل
            if 'NAME' not in connection_info or not connection_info['NAME']:
                connection_info['NAME'] = f"{name}.sqlite3"

            # طباعة معلومات تشخيصية
            print(f"إنشاء قاعدة بيانات SQLite: {name}")
            print(f"مسار ملف SQLite: {connection_info['NAME']}")

        try:
            # إنشاء قاعدة البيانات حسب النوع
            if db_type == 'postgresql':
                # الحصول على اسم قاعدة البيانات في PostgreSQL
                pg_db_name = connection_info['NAME']

                # التحقق من وجود قاعدة البيانات في PostgreSQL إذا كان ذلك ممكنًا
                if not force_create and self._check_postgresql_db_exists(
                    name=pg_db_name,
                    user=connection_info.get('USER', ''),
                    password=connection_info.get('PASSWORD', ''),
                    host=connection_info.get('HOST', 'localhost'),
                    port=connection_info.get('PORT', '5432')
                ):
                    raise ValueError(f"قاعدة البيانات '{pg_db_name}' موجودة بالفعل في PostgreSQL")

                # إنشاء قاعدة البيانات PostgreSQL
                self._create_postgresql_database(
                    name=pg_db_name,
                    user=connection_info.get('USER', ''),
                    password=connection_info.get('PASSWORD', ''),
                    host=connection_info.get('HOST', 'localhost'),
                    port=connection_info.get('PORT', '5432')
                )
            elif db_type == 'sqlite3':
                # إنشاء قاعدة بيانات SQLite
                self._create_sqlite_database(
                    name=connection_info['NAME']
                )
        except Exception as e:
            # تسجيل الخطأ ولكن الاستمرار في إنشاء السجل
            print(f"تحذير: {str(e)}")
            # تحديث معلومات الاتصال لتشير إلى أن قاعدة البيانات لم يتم إنشاؤها فعلياً
            connection_info['_CREATED'] = False
            connection_info['_ERROR'] = str(e)
        else:
            # تحديث معلومات الاتصال لتشير إلى أن قاعدة البيانات تم إنشاؤها بنجاح
            connection_info['_CREATED'] = True

        # إنشاء سجل قاعدة البيانات
        database = Database.objects.create(
            name=name,
            db_type=db_type,
            connection_info=connection_info
        )

        return database

    def _check_postgresql_db_exists(self, name, user, password, host, port):
        """التحقق من وجود قاعدة بيانات PostgreSQL"""
        # التحقق من وجود أداة psql
        if not self._check_command_exists('psql'):
            # إذا لم تكن أداة psql موجودة، نفترض أن قاعدة البيانات غير موجودة
            return False

        # التحقق من صحة اسم قاعدة البيانات
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)

        # التحقق من وجود قاعدة البيانات باستخدام psql
        env = os.environ.copy()
        env['PGPASSWORD'] = password

        # استعلام للتحقق من وجود قاعدة البيانات
        check_cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', user,
            '-lqt'  # قائمة قواعد البيانات بتنسيق جدولي بدون عنوان
        ]

        try:
            result = subprocess.run(check_cmd, env=env, check=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True)

            # البحث عن قاعدة البيانات في النتيجة
            for line in result.stdout.splitlines():
                if line.strip().startswith(safe_name + '|'):
                    return True

            return False
        except Exception:
            # في حالة حدوث خطأ، نفترض أن قاعدة البيانات غير موجودة
            return False

    def _create_sqlite_database(self, name):
        """إنشاء قاعدة بيانات SQLite"""
        # التأكد من أن المسار موجود
        db_path = os.path.join(settings.BASE_DIR, name)
        db_dir = os.path.dirname(db_path)

        # إنشاء المجلد إذا لم يكن موجوداً
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # إنشاء قاعدة بيانات SQLite فارغة
        conn = sqlite3.connect(db_path)
        conn.close()

        return True

    def _create_postgresql_database(self, name, user, password, host, port):
        """إنشاء قاعدة بيانات PostgreSQL"""
        # التحقق من وجود أداة psql
        if not self._check_command_exists('psql'):
            raise RuntimeError("أداة psql غير موجودة. يرجى التأكد من تثبيت PostgreSQL وإضافته إلى مسار النظام.")

        # التحقق من صحة اسم قاعدة البيانات
        # استبدال الأحرف غير المسموح بها بالشرطة السفلية
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)

        # إنشاء قاعدة البيانات باستخدام psql
        env = os.environ.copy()
        env['PGPASSWORD'] = password

        # إنشاء قاعدة البيانات
        create_cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', user,
            '-c', f"CREATE DATABASE \"{safe_name}\";"
        ]

        try:
            subprocess.run(create_cmd, env=env, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"فشل إنشاء قاعدة البيانات: {e.stderr.decode()}")
        except FileNotFoundError:
            raise RuntimeError("أداة psql غير موجودة. يرجى التأكد من تثبيت PostgreSQL وإضافته إلى مسار النظام.")

    def _check_command_exists(self, command):
        """التحقق من وجود أمر في النظام"""
        try:
            # استخدام 'where' في Windows أو 'which' في Unix
            if os.name == 'nt':  # Windows
                check_cmd = ['where', command]
            else:  # Unix/Linux/Mac
                check_cmd = ['which', command]

            result = subprocess.run(check_cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            return result.returncode == 0
        except:
            return False

    def activate_database(self, database_id):
        """تنشيط قاعدة بيانات"""
        # إلغاء تنشيط جميع قواعد البيانات
        Database.objects.all().update(is_active=False)

        # تنشيط قاعدة البيانات المحددة
        database = Database.objects.get(id=database_id)
        database.is_active = True
        database.save()

        # تحديث ملف الإعدادات
        self._update_settings_file(database)

        return database

    def _update_settings_file(self, database):
        """تحديث ملف إعدادات قاعدة البيانات"""
        # إنشاء إعدادات قاعدة البيانات
        if database:
            db_settings = {
                'active_db': database.id,
                'databases': {
                    str(database.id): {
                        'ENGINE': f"django.db.backends.{database.db_type}",
                        **database.connection_info
                    }
                }
            }
        else:
            # إذا لم يتم تحديد قاعدة بيانات، استخدم إعدادات فارغة
            db_settings = {
                'active_db': None,
                'databases': {}
            }

        # حفظ الإعدادات في ملف
        settings_file = os.path.join(settings.BASE_DIR, 'db_settings.json')
        with open(settings_file, 'w') as f:
            json.dump(db_settings, f, indent=4)

    def discover_postgresql_databases(self):
        """اكتشاف قواعد البيانات الموجودة في PostgreSQL"""
        try:
            # الحصول على معلومات الاتصال من إعدادات Django
            from django.conf import settings
            db_settings = settings.DATABASES['default']
            
            user = db_settings.get('USER', 'admin')
            password = db_settings.get('PASSWORD', 'admin123')
            host = db_settings.get('HOST', 'localhost')
            port = str(db_settings.get('PORT', '5433'))
            
            # استخدام psycopg2 للاتصال بقاعدة البيانات
            import psycopg2
            
            # إنشاء اتصال بقاعدة البيانات postgres الافتراضية
            conn = psycopg2.connect(
                dbname='postgres',
                user=user,
                password=password,
                host=host,
                port=port
            )
            conn.autocommit = True
            
            # إنشاء cursor للاستعلام
            cursor = conn.cursor()
            
            # استعلام للحصول على قائمة قواعد البيانات
            cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")
            
            # تحليل النتيجة
            databases = []
            for row in cursor.fetchall():
                db_name = row[0]
                if db_name and db_name not in ['postgres', 'template0', 'template1']:
                    databases.append({
                        'name': db_name,
                        'type': 'postgresql',
                        'connection_info': {
                            'ENGINE': 'django.db.backends.postgresql',
                            'NAME': db_name,
                            'USER': user,
                            'PASSWORD': password,
                            'HOST': host,
                            'PORT': port,
                        }
                    })
            
            # إغلاق الاتصال
            cursor.close()
            conn.close()
            
            print(f"تم اكتشاف {len(databases)} قاعدة بيانات في PostgreSQL")
            return databases
            
        except Exception as e:
            print(f"خطأ في اكتشاف قواعد البيانات: {str(e)}")
            # إرجاع قاعدة البيانات الافتراضية على الأقل
            try:
                from django.conf import settings
                current_db_name = settings.DATABASES['default']['NAME']
                return [{
                    'name': current_db_name,
                    'type': 'postgresql',
                    'connection_info': settings.DATABASES['default']
                }]
            except:
                return []

    def sync_discovered_databases(self):
        """مزامنة قواعد البيانات المكتشفة مع النظام"""
        discovered_dbs = self.discover_postgresql_databases()

        if not discovered_dbs:
            return

        synced_count = 0
        for db_info in discovered_dbs:
            try:
                # التحقق من وجود قاعدة البيانات في النظام
                existing_db = Database.objects.filter(
                    name=db_info['name'],
                    db_type='postgresql'
                ).first()

                if not existing_db:
                    # إنشاء قاعدة بيانات جديدة في النظام
                    database = Database.objects.create(
                        name=db_info['name'],
                        db_type='postgresql',
                        connection_info=db_info['connection_info'],
                        is_active=False  # لا نجعلها نشطة تلقائياً
                    )
                    print(f"تم إضافة قاعدة البيانات المكتشفة: {db_info['name']}")
                    synced_count += 1
                else:
                    # تحديث معلومات الاتصال إذا لزم الأمر
                    existing_db.connection_info = db_info['connection_info']
                    existing_db.save()
                    print(f"تم تحديث قاعدة البيانات: {db_info['name']}")

            except Exception as e:
                print(f"خطأ في مزامنة قاعدة البيانات {db_info['name']}: {str(e)}")

        if synced_count > 0:
            print(f"تم مزامنة {synced_count} قاعدة بيانات جديدة مع النظام")

    def sync_databases_from_settings(self):
        """مزامنة قواعد البيانات من ملف الإعدادات"""
        # إذا كان DATABASE_URL موجود، لا نحتاج لملف الإعدادات
        if os.environ.get('DATABASE_URL'):
            return

        # قراءة ملف الإعدادات
        settings_file = os.path.join(settings.BASE_DIR, 'db_settings.json')
        if not os.path.exists(settings_file):
            # لا نطبع رسالة إذا كان DATABASE_URL موجود
            return

        try:
            with open(settings_file, 'r') as f:
                db_settings = json.load(f)

            # الحصول على قاعدة البيانات النشطة
            active_db_id = db_settings.get('active_db')

            # مزامنة قواعد البيانات
            for db_id, db_info in db_settings.get('databases', {}).items():
                # استخراج معلومات قاعدة البيانات
                engine = db_info.get('ENGINE', '')

                # تحديد نوع قاعدة البيانات من المحرك
                if 'postgresql' in engine:
                    db_type = 'postgresql'
                elif 'sqlite3' in engine:
                    db_type = 'sqlite3'
                else:
                    # تخطي قواعد البيانات غير المدعومة
                    continue

                # استخراج اسم قاعدة البيانات
                db_name = db_info.get('NAME', '')
                if not db_name:
                    # تخطي قواعد البيانات بدون اسم
                    continue

                # إنشاء نسخة من معلومات الاتصال بدون المحرك
                connection_info = {k: v for k, v in db_info.items() if k != 'ENGINE'}

                # التحقق مما إذا كانت قاعدة البيانات موجودة بالفعل
                try:
                    database = Database.objects.get(id=int(db_id))
                    # تحديث قاعدة البيانات الموجودة
                    database.name = os.path.basename(db_name) if db_type == 'sqlite3' else db_name
                    database.db_type = db_type
                    database.connection_info = connection_info
                    database.is_active = (active_db_id == int(db_id))
                    database.save()
                    print(f"تم تحديث قاعدة البيانات: {database.name}")
                except Database.DoesNotExist:
                    # إنشاء قاعدة بيانات جديدة
                    database = Database.objects.create(
                        id=int(db_id),
                        name=os.path.basename(db_name) if db_type == 'sqlite3' else db_name,
                        db_type=db_type,
                        connection_info=connection_info,
                        is_active=(active_db_id == int(db_id))
                    )
                    print(f"تم إنشاء قاعدة البيانات: {database.name}")

            print("تمت مزامنة قواعد البيانات بنجاح")
        except Exception as e:
            print(f"حدث خطأ أثناء مزامنة قواعد البيانات: {str(e)}")

    def delete_database(self, database_id):
        """حذف قاعدة بيانات"""
        # الحصول على قاعدة البيانات
        database = Database.objects.get(id=database_id)

        try:
            # حذف قاعدة البيانات حسب النوع
            if database.db_type == 'postgresql':
                # حذف قاعدة بيانات PostgreSQL
                self._delete_postgresql_database(
                    name=database.connection_info.get('NAME', database.name),
                    user=database.connection_info.get('USER', ''),
                    password=database.connection_info.get('PASSWORD', ''),
                    host=database.connection_info.get('HOST', 'localhost'),
                    port=database.connection_info.get('PORT', '5432')
                )
            elif database.db_type == 'sqlite3':
                # حذف قاعدة بيانات SQLite
                self._delete_sqlite_database(
                    name=database.connection_info.get('NAME', f"{database.name}.sqlite3")
                )
        except Exception as e:
            # تسجيل الخطأ ولكن الاستمرار في حذف السجل
            print(f"تحذير: {str(e)}")

        # حذف سجل قاعدة البيانات
        database.delete()

        return True

    def _delete_sqlite_database(self, name):
        """حذف قاعدة بيانات SQLite"""
        # التأكد من وجود الملف
        db_path = os.path.join(settings.BASE_DIR, name)

        # حذف الملف إذا كان موجوداً
        if os.path.exists(db_path):
            os.remove(db_path)

        return True

    def _delete_postgresql_database(self, name, user, password, host, port):
        """حذف قاعدة بيانات PostgreSQL"""
        # التحقق من وجود أداة psql
        if not self._check_command_exists('psql'):
            raise RuntimeError("أداة psql غير موجودة. يرجى التأكد من تثبيت PostgreSQL وإضافته إلى مسار النظام.")

        # التحقق من صحة اسم قاعدة البيانات
        # استبدال الأحرف غير المسموح بها بالشرطة السفلية
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)

        # حذف قاعدة البيانات باستخدام psql
        env = os.environ.copy()
        env['PGPASSWORD'] = password

        # حذف قاعدة البيانات
        drop_cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', user,
            '-c', f"DROP DATABASE IF EXISTS \"{safe_name}\";"
        ]

        try:
            subprocess.run(drop_cmd, env=env, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"فشل حذف قاعدة البيانات: {e.stderr.decode()}")
        except FileNotFoundError:
            raise RuntimeError("أداة psql غير موجودة. يرجى التأكد من تثبيت PostgreSQL وإضافته إلى مسار النظام.")
