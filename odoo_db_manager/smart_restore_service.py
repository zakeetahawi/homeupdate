"""
خدمة الاستعادة الذكية المحسنة
============================
"""

import gzip
import json
import os

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import transaction

User = get_user_model()


class SmartRestoreService:
    """خدمة الاستعادة الذكية المحسنة"""

    def __init__(self):
        self.dependency_order = [
            # النماذج الأساسية أولاً
            "contenttypes.contenttype",
            "auth.permission",
            "auth.group",
            # نماذج الحسابات
            "accounts.branch",
            "accounts.department",
            "accounts.user",
            "accounts.salesperson",
            "accounts.employee",
            "accounts.companyinfo",
            "accounts.systemsettings",
            # نماذج العملاء
            "customers.customercategory",
            "customers.customer",
            "customers.customernote",
            # نماذج المخزون
            "inventory.category",
            "inventory.brand",
            "inventory.warehouse",
            "inventory.product",
            "inventory.stocktransaction",
            # نماذج الطلبات
            "orders.order",
            "orders.orderitem",
            "orders.payment",
            # نماذج المعاينات
            "inspections.inspection",
            "inspections.inspectionreport",
            # نماذج التركيبات
            "installations.installationschedule",
            "installations.installationteam",
            # نماذج التصنيع
            "manufacturing.manufacturingorder",
            "manufacturing.manufacturingorderitem",
            # نماذج التقارير
            "reports.report",
            # نماذج إدارة قواعد البيانات
            "odoo_db_manager.database",
            "odoo_db_manager.backup",
            "odoo_db_manager.backupschedule",
            "odoo_db_manager.importlog",
            "odoo_db_manager.googlesheetsconfig",
            "odoo_db_manager.restoreProgress",
        ]

        self.required_defaults = {
            "accounts.branch": {
                "code": "MAIN",
                "name": "الفرع الرئيسي",
                "is_main_branch": True,
                "is_active": True,
            },
            "accounts.department": {
                "name": "الإدارة العامة",
                "code": "ADMIN",
                "department_type": "administration",
                "is_active": True,
                "is_core": True,
            },
        }

    def create_missing_dependencies(self):
        """إنشاء التبعيات المفقودة"""
        # إنشاء الفرع الرئيسي إذا لم يكن موجوداً
        from accounts.models import Branch

        if not Branch.objects.exists():
            Branch.objects.create(**self.required_defaults["accounts.branch"])

        # إنشاء القسم الرئيسي إذا لم يكن موجوداً
        from accounts.models import Department

        if not Department.objects.exists():
            Department.objects.create(**self.required_defaults["accounts.department"])

        # إنشاء ContentTypes المطلوبة
        self.ensure_content_types()

    def ensure_content_types(self):
        """التأكد من وجود ContentTypes المطلوبة"""
        required_content_types = [
            ("accounts", "branch"),
            ("accounts", "department"),
            ("accounts", "user"),
            ("accounts", "salesperson"),
            ("customers", "customer"),
            ("orders", "order"),
            ("inspections", "inspection"),
            ("inventory", "product"),
        ]

        for app_label, model_name in required_content_types:
            try:
                ContentType.objects.get_or_create(app_label=app_label, model=model_name)
            except Exception:
                pass

    def preprocess_data(self, data):
        """معالجة البيانات قبل الاستعادة"""
        processed_data = []

        for item in data:
            if not isinstance(item, dict) or "model" not in item:
                continue

            model_name = item.get("model", "")
            fields = item.get("fields", {})

            # معالجة خاصة لنماذج معينة
            if model_name in ["accounts.user", "customers.customer", "orders.order"]:
                # التأكد من وجود فرع
                if "branch" in fields and fields["branch"]:
                    from accounts.models import Branch

                    if not Branch.objects.filter(id=fields["branch"]).exists():
                        main_branch = Branch.objects.first()
                        if main_branch:
                            fields["branch"] = main_branch.id
                        else:
                            fields["branch"] = None

            # تنظيف الحقول
            cleaned_fields = {}
            for key, value in fields.items():
                if key in ["last_login", "date_joined"] and value == "":
                    continue
                cleaned_fields[key] = value

            item["fields"] = cleaned_fields
            processed_data.append(item)

        return processed_data

    def sort_data_by_dependencies(self, data):
        """ترتيب البيانات حسب التبعيات"""
        sorted_data = []
        remaining_data = []

        # ترتيب حسب الأولوية المحددة
        for model_name in self.dependency_order:
            for item in data:
                if item.get("model") == model_name:
                    sorted_data.append(item)

        # إضافة البيانات المتبقية
        for item in data:
            if item not in sorted_data:
                remaining_data.append(item)

        return sorted_data + remaining_data

    def restore_item_with_retry(self, item, max_retries=3):
        """استعادة عنصر مع إعادة ا��محاولة"""
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    for obj in serializers.deserialize("json", json.dumps([item])):
                        obj.save()
                return True, None
            except Exception as e:
                if attempt == max_retries - 1:
                    return False, str(e)

                # محاولة إصلاح المشكلة
                if "foreign key" in str(e).lower():
                    self.fix_foreign_key_issues(item)

                continue

        return False, "فشل بعد عدة محاولات"

    def fix_foreign_key_issues(self, item):
        """إصلاح مشاكل المفاتيح الخارجية"""
        fields = item.get("fields", {})

        # إصلاح مشاكل شائعة
        if "created_by" in fields and fields["created_by"]:
            if not User.objects.filter(id=fields["created_by"]).exists():
                admin_user = User.objects.filter(is_superuser=True).first()
                if admin_user:
                    fields["created_by"] = admin_user.id
                else:
                    fields["created_by"] = None

        if "branch" in fields and fields["branch"]:
            from accounts.models import Branch

            if not Branch.objects.filter(id=fields["branch"]).exists():
                main_branch = Branch.objects.first()
                if main_branch:
                    fields["branch"] = main_branch.id
                else:
                    fields["branch"] = None

        item["fields"] = fields

    def restore_from_file(
        self, file_path, clear_existing=False, progress_callback=None
    ):
        """الدالة الرئيسية للاستعادة"""
        try:
            # قراءة الملف
            if progress_callback:
                progress_callback(current_step="📖 قراءة ملف النسخة الاحتياطية...")

            data = self.read_backup_file(file_path)
            if not data:
                raise ValueError("لا توجد بيانات صالحة في الملف")

            # إنشاء التبعيات المفقودة
            if progress_callback:
                progress_callback(current_step="🔧 إنشاء التبعيات المفقودة...")

            self.create_missing_dependencies()

            # معالجة ��لبيانات
            if progress_callback:
                progress_callback(current_step="🔄 معالجة البيانات...")

            processed_data = self.preprocess_data(data)

            # ترتيب البيانات
            if progress_callback:
                progress_callback(current_step="📋 ترتيب البيانات حسب التبعيات...")

            sorted_data = self.sort_data_by_dependencies(processed_data)

            # حذف البيانات القديمة إذا طُلب ذلك
            if clear_existing:
                if progress_callback:
                    progress_callback(current_step="🗑️ حذف البيانات القديمة...")

                self.clear_existing_data(sorted_data)

            # استعادة البيانات
            if progress_callback:
                progress_callback(current_step="💾 بدء استعادة البيانات...")

            success_count = 0
            error_count = 0
            failed_items = []

            for i, item in enumerate(sorted_data):
                if progress_callback and i % 10 == 0:
                    progress_percentage = int((i / len(sorted_data)) * 100)
                    progress_callback(
                        progress_percentage=progress_percentage,
                        current_step=f"💾 استعادة العنصر {i+1} من {len(sorted_data)}...",
                        processed_items=i,
                        success_count=success_count,
                        error_count=error_count,
                    )

                success, error = self.restore_item_with_retry(item)
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    failed_items.append((i, item, error))

            # محاولة ثانية للعناصر الفاشلة
            if failed_items:
                if progress_callback:
                    progress_callback(current_step="🔄 محاولة ثانية للعناصر الفاشلة...")

                retry_success = 0
                for i, (original_index, item, original_error) in enumerate(
                    failed_items
                ):
                    success, error = self.restore_item_with_retry(item, max_retries=1)
                    if success:
                        success_count += 1
                        error_count -= 1
                        retry_success += 1

            # النتيجة النهائية
            if progress_callback:
                progress_callback(
                    status="completed",
                    progress_percentage=100,
                    current_step="✅ اكتملت عملية الاستعادة بنجاح!",
                    processed_items=len(sorted_data),
                    success_count=success_count,
                    error_count=error_count,
                )

            return {
                "total_count": len(sorted_data),
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": (
                    (success_count / len(sorted_data)) * 100 if sorted_data else 0
                ),
            }

        except Exception as e:
            error_msg = f"خطأ في عملية الاستعادة: {str(e)}"

            if progress_callback:
                progress_callback(
                    status="failed",
                    current_step=f"❌ فشلت العملية: {error_msg}",
                    error_message=error_msg,
                )

            raise

    def read_backup_file(self, file_path):
        """قراءة ملف النسخة الاحتياطية"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"الملف غير موجود: {file_path}")

        try:
            if file_path.lower().endswith(".gz"):
                with gzip.open(file_path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            if not isinstance(data, list):
                if isinstance(data, dict) and "model" in data and "fields" in data:
                    data = [data]
                else:
                    raise ValueError("تنسيق الملف غير صحيح")

            return data

        except json.JSONDecodeError as e:
            raise ValueError(f"خطأ في تحليل ملف JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"خطأ في قراءة الملف: {str(e)}")

    def clear_existing_data(self, data):
        """حذف البيانات الموجودة بترتيب آمن"""
        models_to_clear = set()
        for item in data:
            model_name = item.get("model")
            if model_name:
                models_to_clear.add(model_name)

        # حذف بترتيب عكسي للتبعيات
        for model_name in reversed(self.dependency_order):
            if model_name in models_to_clear:
                try:
                    app_label, model_class = model_name.split(".")
                    model = apps.get_model(app_label, model_class)

                    # لا نحذف المستخدمين المديرين
                    if model_name == "accounts.user":
                        model.objects.filter(is_superuser=False).delete()
                    else:
                        model.objects.all().delete()

                except Exception:
                    pass
