"""
خدمة Google Drive لرفع ملفات المعاينات
"""

import os
import json
from django.conf import settings
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.service_account import Credentials
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("Google API libraries not available. Install google-api-python-client and google-auth")


class GoogleDriveService:
    """خدمة Google Drive لرفع ملفات المعاينات"""

    def __init__(self):
        self.service = None
        self.config = None
        self._initialize()

    def _initialize(self):
        """تهيئة خدمة Google Drive"""
        if not GOOGLE_AVAILABLE:
            raise Exception("مكتبات Google API غير متوفرة. يرجى تثبيت google-api-python-client و google-auth")

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
            scopes = ['https://www.googleapis.com/auth/drive.file']
            credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)

            # إنشاء خدمة Google Drive
            self.service = build('drive', 'v3', credentials=credentials)

        except Exception as e:
            logger.error(f"خطأ في تهيئة خدمة Google Drive: {str(e)}")
            raise Exception(f"فشل في تهيئة خدمة Google Drive: {str(e)}")

    def upload_inspection_file(self, file_path, inspection):
        """رفع ملف معاينة إلى Google Drive مع التسمية الجديدة"""
        try:
            if not self.service:
                raise Exception("خدمة Google Drive غير مهيأة")

            if not self.config.inspections_folder_id:
                raise Exception("معرف مجلد المعاينات غير محدد")

            # توليد اسم الملف الجديد
            drive_filename = inspection.generate_drive_filename()

            # معلومات الملف
            file_metadata = {
                'name': drive_filename,
                'parents': [self.config.inspections_folder_id],
                'description': self._generate_file_description(inspection)
            }

            # رفع الملف
            media = MediaFileUpload(file_path, mimetype='application/pdf')
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink,webContentLink'
            ).execute()

            # تحديث الإحصائيات
            self.config.total_uploads += 1
            self.config.last_upload = timezone.now()
            self.config.save(update_fields=['total_uploads', 'last_upload'])

            return {
                'file_id': file.get('id'),
                'view_url': file.get('webViewLink'),
                'download_url': file.get('webContentLink'),
                'filename': drive_filename,
                'customer_name': inspection.customer.name if inspection.customer else 'عميل جديد',
                'branch_name': inspection.branch.name if inspection.branch else 'فرع غير محدد'
            }

        except Exception as e:
            logger.error(f"خطأ في رفع الملف: {str(e)}")
            raise Exception(f"خطأ في رفع الملف: {str(e)}")

    def _generate_file_description(self, inspection):
        """توليد وصف الملف"""
        description_parts = [
            f'ملف معاينة للعميل: {inspection.customer.name if inspection.customer else "عميل جديد"}',
            f'الفرع: {inspection.branch.name if inspection.branch else "غير محدد"}',
            f'التاريخ: {inspection.scheduled_date}',
        ]

        if inspection.order:
            description_parts.append(f'رقم الطلب: {inspection.order.order_number}')
        elif inspection.contract_number:
            description_parts.append(f'رقم العقد: {inspection.contract_number}')

        return '\n'.join(description_parts)

    def get_file_view_url(self, file_id):
        """الحصول على رابط معاينة الملف"""
        return f"https://drive.google.com/file/d/{file_id}/view"

    def test_connection(self):
        """اختبار الاتصال مع Google Drive"""
        try:
            if not self.service:
                return {
                    'success': False,
                    'message': 'خدمة Google Drive غير مهيأة'
                }

            if not self.config.inspections_folder_id:
                return {
                    'success': False,
                    'message': 'معرف مجلد المعاينات غير محدد'
                }

            # أولاً: اختبار الاتصال العام مع Google Drive
            try:
                about = self.service.about().get(fields="user").execute()
                user_email = about.get('user', {}).get('emailAddress', 'غير معروف')
                logger.info(f"تم الاتصال بـ Google Drive باستخدام الحساب: {user_email}")
            except Exception as e:
                return {
                    'success': False,
                    'message': f'فشل الاتصال مع Google Drive: {str(e)}'
                }

            # ثانياً: اختبار الوصول للمجلد المحدد باستخدام نفس طريقة الرفع
            try:
                # اختبار رفع ملف تجريبي مباشرة (نفس الطريقة التي نجحت)
                from io import BytesIO
                test_content = BytesIO(f'ملف اختبار الاتصال - {timezone.now()}'.encode('utf-8'))

                file_metadata = {
                    'name': f'connection_test_{timezone.now().strftime("%Y%m%d_%H%M%S")}.txt',
                    'parents': [self.config.inspections_folder_id]
                }

                from googleapiclient.http import MediaIoBaseUpload
                media = MediaIoBaseUpload(test_content, mimetype='text/plain')

                # رفع الملف
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,name,webViewLink,parents'
                ).execute()

                # حذف الملف فوراً بعد الاختبار
                self.service.files().delete(fileId=file.get('id')).execute()

                # نجح الاختبار
                success_message = f'''✅ تم الاتصال بنجاح مع Google Drive!

🔗 Service Account: {user_email}
📁 معرف المجلد: {self.config.inspections_folder_id}
✅ اختبار الرفع: نجح
✅ صلاحيات الكتابة: متوفرة
📄 ملف الاختبار: {file.get('name')} (تم حذفه)

🎉 النظام جاهز لرفع ملفات المعاينات!'''

                # تحديث حالة الاختبار
                self.config.last_test = timezone.now()
                self.config.test_status = 'success'
                self.config.test_message = success_message
                self.config.save(update_fields=['last_test', 'test_status', 'test_message'])

                return {
                    'success': True,
                    'message': success_message,
                    'user_email': user_email
                }

            except Exception as folder_error:
                # تحليل نوع الخطأ وتقديم حلول
                error_str = str(folder_error)

                if "404" in error_str or "notFound" in error_str:
                    # محاولة أخيرة: البحث عن جميع المجلدات المتاحة
                    try:
                        # البحث عن جميع المجلدات
                        search_results = self.service.files().list(
                            q="mimeType='application/vnd.google-apps.folder'",
                            fields="files(id,name,parents,owners,shared)",
                            pageSize=20
                        ).execute()

                        folders_found = search_results.get('files', [])

                        if folders_found:
                            folder_list = "\n".join([
                                f"- {f['name']} (ID: {f['id']}) - مشارك: {f.get('shared', False)}"
                                for f in folders_found[:10]
                            ])
                        else:
                            # إذا لم توجد مجلدات، جرب البحث عن أي ملفات
                            all_files = self.service.files().list(
                                fields="files(id,name,mimeType)",
                                pageSize=10
                            ).execute()

                            files_found = all_files.get('files', [])
                            if files_found:
                                folder_list = f"لا توجد مجلدات، لكن توجد ملفات:\n" + "\n".join([
                                    f"- {f['name']} ({f.get('mimeType', 'unknown')})"
                                    for f in files_found[:5]
                                ])
                            else:
                                folder_list = "لا توجد ملفات أو مجلدات متاحة للـ Service Account"

                        detailed_message = f"""
خطأ 404: لا يمكن الوصول للمجلد المحدد

معرف المجلد المحدد: {self.config.inspections_folder_id}
Service Account: {user_email}

المجلدات المتاحة للـ Service Account:
{folder_list if folder_list else "لا توجد مجلدات متاحة"}

الحلول المقترحة:
1. تأكد من مشاركة المجلد مع: {user_email}
2. امنح صلاحية "Editor" للـ Service Account
3. تحقق من أن معرف المجلد صحيح
4. جرب استخدام معرف أحد المجلدات المتاحة أعلاه

خطوات المشاركة:
- اذهب إلى المجلد في Google Drive
- انقر بالزر الأيمن > مشاركة
- أضف البريد الإلكتروني: {user_email}
- اختر صلاحية "Editor"
- انقر على "إرسال"
                        """
                    except:
                        detailed_message = f"""
خطأ 404: المجلد غير موجود أو غير مشارك مع Service Account

معرف المجلد: {self.config.inspections_folder_id}
Service Account: {user_email}

الحلول المقترحة:
1. تأكد من مشاركة المجلد مع: {user_email}
2. امنح Service Account صلاحية "Editor" أو "Viewer" على الأقل
3. تأكد من أن المجلد موجود في Google Drive
4. تحقق من صحة معرف المجلد

خطوات المشاركة:
- اذهب إلى المجلد في Google Drive
- انقر بالزر الأيمن > مشاركة
- أضف البريد الإلكتروني: {user_email}
- اختر صلاحية "Editor"
                        """
                elif "403" in error_str or "forbidden" in error_str:
                    detailed_message = f"""
                    خطأ 403: ليس لديك صلاحية للوصول إلى هذا المجلد

                    الحلول:
                    1. تأكد من مشاركة المجلد مع: {user_email}
                    2. امنح صلاحية "Editor" للـ Service Account
                    3. تحقق من أن Google Drive API مفعل في Google Cloud Console
                    """
                else:
                    detailed_message = f"خطأ غير متوقع: {error_str}"

                # تحديث حالة الاختبار
                self.config.last_test = timezone.now()
                self.config.test_status = 'failed'
                self.config.test_message = detailed_message
                self.config.save(update_fields=['last_test', 'test_status', 'test_message'])

                return {
                    'success': False,
                    'message': detailed_message,
                    'user_email': user_email
                }

        except Exception as e:
            error_message = f'خطأ عام في الاتصال: {str(e)}'

            # تحديث حالة الاختبار
            if self.config:
                self.config.last_test = timezone.now()
                self.config.test_status = 'failed'
                self.config.test_message = error_message
                self.config.save(update_fields=['last_test', 'test_status', 'test_message'])

            return {
                'success': False,
                'message': error_message
            }


def get_google_drive_service():
    """الحصول على خدمة Google Drive"""
    try:
        return GoogleDriveService()
    except Exception as e:
        logger.error(f"فشل في إنشاء خدمة Google Drive: {str(e)}")
        return None


def create_test_folder():
    """إنشاء مجلد تجريبي لاختبار الصلاحيات"""
    try:
        drive_service = get_google_drive_service()
        if not drive_service:
            return None

        # الحصول على معرف المجلد المحدد في الإعدادات
        config = drive_service.config
        if config and config.inspections_folder_id:
            # إنشاء مجلد فرعي داخل المجلد المحدد
            folder_metadata = {
                'name': f'CRM_Test_Folder_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [config.inspections_folder_id]  # إنشاء داخل المجلد المحدد
            }
        else:
            # إنشاء مجلد في الجذر إذا لم يكن هناك مجلد محدد
            folder_metadata = {
                'name': f'CRM_Test_Folder_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                'mimeType': 'application/vnd.google-apps.folder'
            }

        folder = drive_service.service.files().create(
            body=folder_metadata,
            fields='id,name,webViewLink,parents'
        ).execute()

        return {
            'id': folder.get('id'),
            'name': folder.get('name'),
            'url': folder.get('webViewLink'),
            'parents': folder.get('parents', [])
        }

    except Exception as e:
        logger.error(f"فشل في إنشاء مجلد تجريبي: {str(e)}")
        return None


def test_file_upload_to_folder():
    """اختبار رفع ملف تجريبي إلى المجلد المحدد"""
    try:
        drive_service = get_google_drive_service()
        if not drive_service:
            return None

        config = drive_service.config
        if not config or not config.inspections_folder_id:
            return {
                'success': False,
                'message': 'معرف المجلد غير محدد في الإعدادات'
            }

        # إنشاء ملف تجريبي
        from io import BytesIO
        test_content = BytesIO(f'ملف اختبار تم إنشاؤه في {timezone.now()}'.encode('utf-8'))

        file_metadata = {
            'name': f'test_file_{timezone.now().strftime("%Y%m%d_%H%M%S")}.txt',
            'parents': [config.inspections_folder_id]
        }

        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(test_content, mimetype='text/plain')

        # رفع الملف
        file = drive_service.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink,parents'
        ).execute()

        # حذف الملف فوراً بعد الاختبار
        drive_service.service.files().delete(fileId=file.get('id')).execute()

        return {
            'success': True,
            'message': 'تم اختبار رفع الملف بنجاح',
            'file_name': file.get('name'),
            'folder_id': config.inspections_folder_id
        }

    except Exception as e:
        logger.error(f"فشل في اختبار رفع الملف: {str(e)}")
        return {
            'success': False,
            'message': f'فشل في اختبار رفع الملف: {str(e)}'
        }


def get_service_account_email():
    """الحصول على البريد الإلكتروني للـ Service Account من ملف الاعتماد"""
    try:
        from odoo_db_manager.models import GoogleDriveConfig
        config = GoogleDriveConfig.get_active_config()

        if not config or not config.credentials_file:
            return None

        credentials_path = config.credentials_file.path
        if not os.path.exists(credentials_path):
            return None

        with open(credentials_path, 'r') as f:
            credentials_data = json.load(f)
            return credentials_data.get('client_email')

    except Exception as e:
        logger.error(f"خطأ في قراءة البريد الإلكتروني للـ Service Account: {str(e)}")
        return None
