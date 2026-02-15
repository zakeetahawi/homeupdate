"""
خدمات نظام النسخ الاحتياطي والاستعادة
"""

import gzip
import json
import os
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection, models, transaction
from django.utils import timezone

from .models import BackupJob, RestoreJob


class BackupService:
    """خدمة النسخ الاحتياطي"""

    def __init__(self):
        self.backup_dir = Path(settings.MEDIA_ROOT) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        name: str,
        user,
        backup_type: str = "full",
        description: str = "",
        apps_to_include: List[str] = None,
    ) -> BackupJob:
        """إنشاء نسخة احتياطية جديدة"""

        # إنشاء مهمة النسخ الاحتياطي
        job = BackupJob.objects.create(
            name=name, description=description, backup_type=backup_type, created_by=user
        )

        # تشغيل النسخ الاحتياطي في thread منفصل
        thread = threading.Thread(
            target=self._run_backup, args=(job.id, apps_to_include), daemon=True
        )
        thread.start()

        return job

    def _run_backup(self, job_id: str, apps_to_include: List[str] = None):
        """تنفيذ النسخ الاحتياطي"""
        try:
            job = BackupJob.objects.get(id=job_id)
            job.mark_as_started()

            # تحديد التطبيقات المراد نسخها
            if apps_to_include is None:
                apps_to_include = self._get_default_apps()

            job.update_progress(5, "جمع بيانات التطبيقات...")

            # جمع البيانات
            all_data = []
            total_apps = len(apps_to_include)

            for i, app_name in enumerate(apps_to_include):
                try:
                    job.update_progress(
                        10 + (i * 60 / total_apps), f"جمع بيانات {app_name}..."
                    )

                    app_data = self._get_app_data(app_name)
                    all_data.extend(app_data)

                except Exception as e:
                    print(f"خطأ في جمع بيانات {app_name}: {str(e)}")
                    continue

            job.total_records = len(all_data)
            job.update_progress(70, "إنشاء ملف النسخة الاحتياطية...")

            # إنشاء ملف النسخة الاحتياطية
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{job.name}_{timestamp}.json.gz"
            file_path = self.backup_dir / filename

            # كتابة البيانات مع الضغط
            original_size = self._write_compressed_backup(all_data, file_path)
            compressed_size = file_path.stat().st_size

            job.update_progress(95, "إنهاء النسخة الاحتياطية...")

            # تحديث معلومات المهمة
            job.mark_as_completed(
                file_path=str(file_path),
                file_size=original_size,
                compressed_size=compressed_size,
            )

        except Exception as e:
            try:
                job = BackupJob.objects.get(id=job_id)
                job.mark_as_failed(str(e))
            except Exception:
                pass

    def _get_default_apps(self) -> List[str]:
        """الحصول على قائمة التطبيقات الافتراضية للنسخ الاحتياطي"""
        return [
            "contenttypes",
            "auth",
            "accounts",
            "customers",
            "orders",
            "inspections",
            "installations",
            "manufacturing",
            "inventory",
            "reports",
            "odoo_db_manager",  # إضافة تطبيق إدارة قاعدة البيانات ومزامنة Google
        ]

    def _get_app_data(self, app_name: str) -> List[Dict]:
        """الحصول على بيانات تطبيق معين"""
        try:
            app_config = apps.get_app_config(app_name)
            app_data = []

            for model in app_config.get_models():
                # تخطي النماذج التي لا نريد نسخها
                if self._should_skip_model(model):
                    continue

                try:
                    queryset = model.objects.all()
                    model_data = serializers.serialize("python", queryset)
                    app_data.extend(model_data)
                except Exception as e:
                    print(f"خطأ في نسخ نموذج {model._meta.label}: {str(e)}")
                    continue

            return app_data

        except Exception as e:
            print(f"خطأ في الحصول على بيانات {app_name}: {str(e)}")
            return []

    def _should_skip_model(self, model) -> bool:
        """تحديد ما إذا كان يجب تخطي نموذج معين"""
        skip_models = [
            "session",
            "logentry",
            "migration",
            "backupjob",
            "restorejob",
            "backupschedule",
            "contenttype",  # سيتم التعامل معه بشكل خاص
        ]

        model_name = model._meta.model_name.lower()
        return model_name in skip_models

    def _write_compressed_backup(self, data: List[Dict], file_path: Path) -> int:
        """كتابة البيانات مع الضغط"""
        # إنشاء ملف مؤقت للبيانات غير المضغوطة
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        ) as temp_file:
            json.dump(data, temp_file, ensure_ascii=False, indent=2, default=str)
            temp_path = temp_file.name

        try:
            # الحصول على حجم الملف الأصلي
            original_size = Path(temp_path).stat().st_size

            # ضغط الملف
            with open(temp_path, "rb") as f_in:
                with gzip.open(file_path, "wb", compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)

            return original_size

        finally:
            # حذف الملف المؤقت
            os.unlink(temp_path)


class RestoreService:
    """خدمة الاستعادة"""

    def restore_from_file(
        self,
        file_path: str,
        user,
        name: str = None,
        clear_existing: bool = False,
        description: str = "",
    ) -> RestoreJob:
        """استعادة من ملف"""

        if name is None:
            name = f"استعادة {Path(file_path).name}"

        # التحقق من وجود الملف
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"الملف غير موجود: {file_path}")

        # إنشاء مهمة الاستعادة
        job = RestoreJob.objects.create(
            name=name,
            description=description,
            source_file=file_path,
            file_size=Path(file_path).stat().st_size,
            clear_existing_data=clear_existing,
            created_by=user,
        )

        # تشغيل الاستعادة في thread منفصل
        thread = threading.Thread(target=self._run_restore, args=(job.id,), daemon=True)
        thread.start()

        return job

    def _run_restore(self, job_id: str):
        """تنفيذ الاستعادة"""
        try:
            job = RestoreJob.objects.get(id=job_id)
            job.mark_as_started()

            job.update_progress(5, "قراءة ملف النسخة الاحتياطية...")

            # قراءة البيانات
            data = self._read_backup_file(job.source_file)
            if not data:
                raise ValueError("الملف فارغ أو تالف")

            job.total_records = len(data)
            job.update_progress(10, "تحضير البيانات للاستعادة...")

            # ترتيب البيانات حسب التبعيات
            sorted_data = self._sort_data_by_dependencies(data)

            # حذف البيانات الموجودة إذا طُلب ذلك
            if job.clear_existing_data:
                job.update_progress(15, "حذف البيانات الموجودة...")
                self._clear_existing_data(sorted_data)

            job.update_progress(20, "بدء استعادة البيانات...")

            # استعادة البيانات
            success_count = 0
            failed_count = 0

            # تعطيل فحص المفاتيح الخارجية مؤقتاً
            with connection.cursor() as cursor:
                # PostgreSQL compatibility
                if "mysql" in connection.settings_dict["ENGINE"].lower():
                    cursor.execute("SET foreign_key_checks = 0;")
                elif "postgresql" in connection.settings_dict["ENGINE"].lower():
                    cursor.execute("SET session_replication_role = replica;")

            try:
                for i, item in enumerate(sorted_data):
                    try:
                        progress = 20 + (i * 75 / len(sorted_data))
                        model_name = item.get("model", "غير معروف")

                        job.update_progress(
                            progress,
                            f"استعادة {model_name}...",
                            processed=i + 1,
                            success=success_count,
                            failed=failed_count,
                        )

                        # استعادة العنصر
                        self._restore_item(item)
                        success_count += 1

                    except Exception as e:
                        failed_count += 1
                        print(f"خطأ في استعادة العنصر {i} ({model_name}): {str(e)}")
                        continue

            finally:
                # إعادة تفعيل فحص المفاتيح الخارجية
                with connection.cursor() as cursor:
                    # PostgreSQL compatibility
                    if "mysql" in connection.settings_dict["ENGINE"].lower():
                        cursor.execute("SET foreign_key_checks = 1;")
                    elif "postgresql" in connection.settings_dict["ENGINE"].lower():
                        cursor.execute("SET session_replication_role = DEFAULT;")

            job.update_progress(95, "إنهاء الاستعادة...")

            # تحديث الإحصائيات النهائية
            job.success_records = success_count
            job.failed_records = failed_count
            job.mark_as_completed()

        except Exception as e:
            try:
                job = RestoreJob.objects.get(id=job_id)
                job.mark_as_failed(str(e))
            except Exception:
                pass

    def _read_backup_file(self, file_path: str) -> List[Dict]:
        """قراءة ملف النسخة الاحتياطية"""
        file_path = Path(file_path)

        try:
            if file_path.suffix == ".gz" or file_path.name.endswith(".json.gz"):
                # ملف مضغوط
                with gzip.open(file_path, "rt", encoding="utf-8") as f:
                    return json.load(f)
            else:
                # ملف عادي
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"خطأ في قراءة ملف JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"خطأ في قراءة الملف: {str(e)}")

    def _sort_data_by_dependencies(self, data: List[Dict]) -> List[Dict]:
        """ترتيب البيانات حسب التبعيات"""
        # ترتيب أولوية النماذج
        priority_order = [
            "contenttypes.contenttype",
            "auth.permission",
            "auth.group",
            "accounts.department",
            "accounts.branch",
            "auth.user",
            "accounts.user",
            "customers.customercategory",  # إضافة تصنيفات العملاء قبل العملاء
            "customers.customer",
            "inventory.category",
            "inventory.brand",
            "inventory.warehouse",
            "inventory.product",
            "orders.order",
            "orders.orderitem",
            "inspections.inspection",
            "installations.installationschedule",
            "manufacturing.manufacturingorder",
            "reports.report",
            # إضافة نماذج Google Sync المتقدمة
            "odoo_db_manager.googlesheetsconfig",
            "odoo_db_manager.googledriveconfig",
            "odoo_db_manager.googlesheetmapping",
            "odoo_db_manager.googlesynctask",
            "odoo_db_manager.googlesyncconflict",
            "odoo_db_manager.googlesyncschedule",
            "odoo_db_manager.database",
            "odoo_db_manager.backupschedule",
        ]

        sorted_data = []
        remaining_data = []
        processed_items = set()

        # ترتيب حسب الأولوية
        for model_name in priority_order:
            for item in data:
                item_id = id(item)
                if item_id not in processed_items and item.get("model") == model_name:
                    sorted_data.append(item)
                    processed_items.add(item_id)

        # إضافة باقي البيانات
        for item in data:
            item_id = id(item)
            if item_id not in processed_items:
                remaining_data.append(item)
                processed_items.add(item_id)

        return sorted_data + remaining_data

    def _clear_existing_data(self, data: List[Dict]):
        """حذف البيانات الموجودة"""
        models_to_clear = set()

        # جمع النماذج المراد حذفها
        for item in data:
            model_name = item.get("model")
            if model_name:
                models_to_clear.add(model_name)

        # ترتيب النماذج للحذف (عكس ترتيب الإنشاء)
        clear_order = [
            "reports.report",
            "manufacturing.manufacturingorder",
            "installations.installationschedule",
            "inspections.inspection",
            "orders.orderitem",
            "orders.order",
            "inventory.product",
            "inventory.warehouse",
            "inventory.brand",
            "inventory.category",
            "customers.customer",
            # لا نحذف المستخدمين والأقسام والفروع
        ]

        # حذف البيانات بالترتيب المحدد
        for model_name in clear_order:
            if model_name in models_to_clear:
                try:
                    app_label, model_class = model_name.split(".")
                    model = apps.get_model(app_label, model_class)

                    # تخطي النماذج المهمة
                    if self._should_skip_clearing(model):
                        continue

                    count = model.objects.count()
                    if count > 0:
                        print(f"حذف {count} سجل من {model_name}")
                        model.objects.all().delete()

                except Exception as e:
                    print(f"خطأ في حذف بيانات {model_name}: {str(e)}")
                    continue

    def _should_skip_clearing(self, model) -> bool:
        """تحديد ما إذا كان يجب تخطي حذف نموذج معين"""
        skip_models = [
            "user",  # لا نحذف المستخدمين
            "department",  # لا نحذف الأقسام
            "branch",  # لا نحذف الفروع
            "session",
            "logentry",
            "migration",
            "backupjob",
            "restorejob",
            "backupschedule",
            "contenttype",
            "permission",
            "group",
        ]

        model_name = model._meta.model_name.lower()
        return model_name in skip_models

    def _restore_item(self, item: Dict):
        """استعادة عنصر واحد"""
        try:
            # التحقق من صحة البيانات
            if not item or "model" not in item or "fields" not in item:
                raise ValueError("بيانات العنصر غير صحيحة")

            model_name = item["model"]

            # تخطي النماذج التي لا نريد استعادتها
            if self._should_skip_restoring(model_name):
                return

            # استعادة العنصر باستخدام Django serializer
            with transaction.atomic():
                for obj in serializers.deserialize("python", [item]):
                    try:
                        # محاولة حفظ ا��كائن
                        obj.save()
                    except Exception as e:
                        # في حالة فشل الحفظ، محاولة تحديث الكائن الموجود
                        if hasattr(obj.object, "pk") and obj.object.pk:
                            try:
                                existing = obj.object.__class__.objects.get(
                                    pk=obj.object.pk
                                )
                                # تحديث الحقول
                                for field_name, field_value in item["fields"].items():
                                    if hasattr(existing, field_name):
                                        setattr(existing, field_name, field_value)
                                existing.save()
                            except obj.object.__class__.DoesNotExist:
                                # إذا لم يكن الكائن موجود، إنشاء جديد بدون PK
                                obj.object.pk = None
                                obj.save()
                        else:
                            raise e

        except Exception as e:
            raise Exception(
                f"خطأ في استعادة العنصر {item.get('model', 'غير معروف')}: {str(e)}"
            )

    def _should_skip_restoring(self, model_name: str) -> bool:
        """تحديد ما إذا كان يجب تخطي استعادة نموذج معين"""
        skip_models = [
            "contenttypes.contenttype",  # يتم إنشاؤها تلقائياً
            "auth.permission",  # يتم إنشاؤها تلقائياً
            "django_session.session",
            "admin.logentry",
            "migrations.migration",
            "backup_system.backupjob",
            "backup_system.restorejob",
            "backup_system.backupschedule",
        ]

        return model_name.lower() in [m.lower() for m in skip_models]


class BackupManager:
    """مدير النسخ الاحتياطية"""

    def __init__(self):
        self.backup_service = BackupService()
        self.restore_service = RestoreService()

    def create_full_backup(self, name: str, user, description: str = "") -> BackupJob:
        """إنشاء نسخة احتياطية كاملة"""
        return self.backup_service.create_backup(
            name=name, user=user, backup_type="full", description=description
        )

    def create_partial_backup(
        self, name: str, user, apps: List[str], description: str = ""
    ) -> BackupJob:
        """إنشاء نسخة احتياطية جزئية"""
        return self.backup_service.create_backup(
            name=name,
            user=user,
            backup_type="partial",
            description=description,
            apps_to_include=apps,
        )

    def restore_backup(
        self,
        file_path: str,
        user,
        name: str = None,
        clear_existing: bool = False,
        description: str = "",
    ) -> RestoreJob:
        """استعادة نسخة احتياطية"""
        return self.restore_service.restore_from_file(
            file_path=file_path,
            user=user,
            name=name,
            clear_existing=clear_existing,
            description=description,
        )

    def get_backup_status(self, job_id: str) -> Dict[str, Any]:
        """الحصول على حالة النسخ الاحتياطي"""
        try:
            job = BackupJob.objects.get(id=job_id)
            return {
                "id": str(job.id),
                "name": job.name,
                "status": job.status,
                "progress": job.progress_percentage,
                "current_step": job.current_step,
                "total_records": job.total_records,
                "processed_records": job.processed_records,
                "error_message": job.error_message,
                "file_size": job.file_size_display,
                "compressed_size": job.compressed_size_display,
                "compression_ratio": job.compression_ratio,
                "duration": str(job.duration) if job.duration else None,
            }
        except BackupJob.DoesNotExist:
            return {"error": "المهمة غير موجودة"}

    def get_restore_status(self, job_id: str) -> Dict[str, Any]:
        """الحصول على حالة الاستعادة"""
        try:
            job = RestoreJob.objects.get(id=job_id)
            return {
                "id": str(job.id),
                "name": job.name,
                "status": job.status,
                "progress": job.progress_percentage,
                "current_step": job.current_step,
                "total_records": job.total_records,
                "processed_records": job.processed_records,
                "success_records": job.success_records,
                "failed_records": job.failed_records,
                "success_rate": job.success_rate,
                "error_message": job.error_message,
                "file_size": job.file_size_display,
                "duration": str(job.duration) if job.duration else None,
            }
        except RestoreJob.DoesNotExist:
            return {"error": "المهمة غير موجودة"}

    def cleanup_old_backups(self, keep_count: int = 10):
        """تنظيف النسخ الاحتياطية الق��يمة"""
        # الحصول على النسخ الاحتياطية المكتملة مرتبة حسب التاريخ
        completed_backups = BackupJob.objects.filter(status="completed").order_by(
            "-completed_at"
        )

        # حذف النسخ الزائدة
        backups_to_delete = completed_backups[keep_count:]

        for backup in backups_to_delete:
            try:
                # حذف الملف
                if backup.file_path and os.path.exists(backup.file_path):
                    os.remove(backup.file_path)

                # حذف السجل
                backup.delete()

            except Exception as e:
                print(f"خطأ في حذف النسخة الاحتياطية {backup.id}: {str(e)}")


# إنشاء مثيل مشترك
backup_manager = BackupManager()
