"""
خدمة Google Drive لرفع ملفات العقود
"""

import json
import logging
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning(
        "Google API libraries not available. Install google-api-python-client and google-auth"
    )


class ContractGoogleDriveService:
    """خدمة Google Drive لرفع ملفات العقود"""

    def __init__(self):
        self.service = None
        self.config = None
        self._initialize()

    def _initialize(self):
        """تهيئة خدمة Google Drive"""
        if not GOOGLE_AVAILABLE:
            logger.error("Google API libraries not available")
            return

        try:
            from odoo_db_manager.models import GoogleDriveConfig

            self.config = GoogleDriveConfig.get_active_config()

            if not self.config:
                raise Exception("لا توجد إعدادات Google Drive نشطة")

            if not self.config.credentials_file:
                raise Exception("ملف اعتماد Google غير موجود")

            # تحميل ملف الاعتماد
            credentials_path = self.config.credentials_file.path
            if not os.path.exists(credentials_path):
                raise Exception("ملف اعتماد Google غير موجود في المسار المحدد")

            # إنشاء الاعتماد
            scopes = ["https://www.googleapis.com/auth/drive.file"]
            credentials = Credentials.from_service_account_file(
                credentials_path, scopes=scopes
            )

            # إنشاء خدمة Google Drive
            self.service = build("drive", "v3", credentials=credentials)

        except Exception as e:
            logger.error(f"خطأ في تهيئة خدمة Google Drive: {str(e)}")

    def upload_contract_file(self, file_path, order):
        """رفع ملف عقد إلى Google Drive مع التسمية الجديدة"""
        try:
            if not self.service:
                raise Exception("خدمة Google Drive غير مهيأة")

            # إنشاء مجلد العقود إذا لم يكن موجوداً
            contracts_folder_id = self._get_or_create_contracts_folder()

            # توليد اسم الملف الجديد
            drive_filename = self._generate_contract_filename(order)

            # معلومات الملف
            file_metadata = {
                "name": drive_filename,
                "parents": [contracts_folder_id],
                "description": self._generate_file_description(order),
            }

            # رفع الملف
            media = MediaFileUpload(file_path, mimetype="application/pdf")
            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id,webViewLink,webContentLink",
                )
                .execute()
            )

            # تحديث الإحصائيات
            self.config.total_uploads += 1
            self.config.last_upload = timezone.now()
            self.config.save(update_fields=["total_uploads", "last_upload"])

            return {
                "file_id": file.get("id"),
                "view_url": file.get("webViewLink"),
                "download_url": file.get("webContentLink"),
                "filename": drive_filename,
                "customer_name": order.customer.name if order.customer else "عميل جديد",
                "branch_name": order.branch.name if order.branch else "فرع غير محدد",
            }

        except Exception as e:
            logger.error(f"خطأ في رفع ملف العقد: {str(e)}")
            raise Exception(f"خطأ في رفع ملف العقد: {str(e)}")

    def _get_or_create_contracts_folder(self):
        """الحصول على مجلد العقود أو إنشاؤه"""
        try:
            # استخدام مجلد العقود المحدد في الإعدادات المركزية أولاً
            if self.config.contracts_folder_id:
                # التحقق من وجود المجلد المحدد
                try:
                    folder_info = (
                        self.service.files()
                        .get(fileId=self.config.contracts_folder_id, fields="id,name")
                        .execute()
                    )
                    logger.info(
                        f"استخدام مجلد العقود المحدد: {folder_info.get('name')} ({self.config.contracts_folder_id})"
                    )
                    return self.config.contracts_folder_id
                except Exception as e:
                    logger.warning(f"المجلد المحدد غير متاح: {e}")

            # البحث عن مجلد العقود أو إنشاؤه
            folder_name = "العقود - Contracts"

            # البحث في المجلد الجذر
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

            results = (
                self.service.files().list(q=query, fields="files(id, name)").execute()
            )
            folders = results.get("files", [])

            if folders:
                # المجلد موجود
                folder_id = folders[0]["id"]
                logger.info(f"وجد مجلد العقود الموجود: {folder_id}")
                return folder_id
            else:
                # إنشاء المجلد في الجذر
                folder_metadata = {
                    "name": folder_name,
                    "mimeType": "application/vnd.google-apps.folder",
                }

                folder = (
                    self.service.files()
                    .create(body=folder_metadata, fields="id")
                    .execute()
                )
                logger.info(f"تم إنشاء مجلد العقود الجديد: {folder.get('id')}")
                return folder.get("id")

        except Exception as e:
            logger.error(f"خطأ في إنشاء مجلد العقود: {str(e)}")
            # استخدام مجلد المعاينات كبديل فقط في حالة الطوارئ
            return self.config.inspections_folder_id

    def _generate_contract_filename(self, order):
        """توليد اسم ملف العقد"""
        try:
            # تنظيف اسم العميل
            customer_name = (
                self._clean_filename(order.customer.name)
                if order.customer
                else "عميل_جديد"
            )

            # تنظيف اسم الفرع
            branch_name = (
                self._clean_filename(order.branch.name)
                if order.branch
                else "فرع_غير_محدد"
            )

            # تاريخ الطلب
            order_date = (
                order.order_date.strftime("%Y%m%d")
                if order.order_date
                else timezone.now().strftime("%Y%m%d")
            )

            # رقم الطلب
            order_number = (
                self._clean_filename(order.order_number)
                if order.order_number
                else "طلب_جديد"
            )

            # رقم العقد
            contract_number = (
                self._clean_filename(order.contract_number)
                if order.contract_number
                else "عقد"
            )

            # تكوين اسم الملف
            filename = f"عقد_{customer_name}_{branch_name}_{order_date}_{order_number}_{contract_number}.pdf"

            return filename[:200]  # تحديد الطول الأقصى

        except Exception as e:
            logger.error(f"خطأ في توليد اسم الملف: {str(e)}")
            return f"عقد_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    def _clean_filename(self, name):
        """تنظيف اسم الملف من الأحرف غير المسموحة"""
        import re

        if not name:
            return "غير_محدد"

        # إزالة الأحرف غير المسموحة
        cleaned = re.sub(r"[^\w\u0600-\u06FF\s-]", "", str(name))
        # استبدال المسافات بـ underscore
        cleaned = re.sub(r"\s+", "_", cleaned)
        return cleaned[:50]  # تحديد الطول الأقصى

    def _generate_file_description(self, order):
        """توليد وصف الملف"""
        try:
            description_parts = []

            if order.customer:
                description_parts.append(f"العميل: {order.customer.name}")

            if order.branch:
                description_parts.append(f"الفرع: {order.branch.name}")

            if order.order_number:
                description_parts.append(f"رقم الطلب: {order.order_number}")

            if order.contract_number:
                description_parts.append(f"رقم العقد: {order.contract_number}")

            description_parts.append(
                f"تاريخ الرفع: {timezone.now().strftime('%Y-%m-%d %H:%M')}"
            )

            return " | ".join(description_parts)

        except Exception as e:
            logger.error(f"خطأ في توليد وصف الملف: {str(e)}")
            return f"ملف عقد - {timezone.now().strftime('%Y-%m-%d')}"


def get_contract_google_drive_service():
    """الحصول على خدمة Google Drive للعقود"""
    try:
        if not GOOGLE_AVAILABLE:
            logger.warning("Google API libraries not available")
            return None

        service = ContractGoogleDriveService()
        if service.service:
            return service
        else:
            logger.error("فشل في تهيئة خدمة Google Drive للعقود")
            return None
    except Exception as e:
        logger.error(f"خطأ في الحصول على خدمة Google Drive للعقود: {str(e)}")
        return None


def test_contract_file_upload_to_folder():
    """اختبار رفع ملف عقد تجريبي إلى المجلد المحدد"""
    try:
        drive_service = get_contract_google_drive_service()
        if not drive_service:
            return {"success": False, "message": "خدمة Google Drive للعقود غير متوفرة"}

        # إنشاء ملف تجريبي
        from io import BytesIO

        test_content = BytesIO(
            f"ملف عقد تجريبي تم إنشاؤه في {timezone.now()}".encode("utf-8")
        )

        # الحصول على مجلد العقود أو إنشاؤه
        contracts_folder_id = drive_service._get_or_create_contracts_folder()

        file_metadata = {
            "name": f'test_contract_{timezone.now().strftime("%Y%m%d_%H%M%S")}.txt',
            "parents": [contracts_folder_id],
        }

        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(test_content, mimetype="text/plain")

        # رفع الملف
        file = (
            drive_service.service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id,name,webViewLink,parents",
            )
            .execute()
        )

        # حذف الملف فوراً بعد الاختبار
        drive_service.service.files().delete(fileId=file.get("id")).execute()

        return {
            "success": True,
            "message": "تم اختبار رفع ملف العقد بنجاح",
            "file_name": file.get("name"),
            "folder_id": contracts_folder_id,
        }

    except Exception as e:
        logger.error(f"فشل في اختبار رفع ملف العقد: {str(e)}")
        return {"success": False, "message": f"فشل في اختبار رفع ملف العقد: {str(e)}"}
