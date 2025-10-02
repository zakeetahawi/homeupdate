"""
أمر Django لإصلاح حالة رفع الملفات إلى Google Drive
"""

import os

from django.core.management.base import BaseCommand
from django.utils import timezone

from inspections.models import Inspection
from inspections.services.google_drive_service import get_google_drive_service


class Command(BaseCommand):
    help = "إصلاح حالة رفع الملفات إلى Google Drive"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض التغييرات دون تطبيقها",
        )
        parser.add_argument(
            "--check-drive",
            action="store_true",
            help="التحقق من وجود الملفات في Google Drive",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        check_drive = options["check_drive"]

        self.stdout.write(self.style.SUCCESS("🔧 بدء إصلاح حالة رفع الملفات..."))

        # الحصول على المعاينات التي تحتوي على ملفات
        inspections = Inspection.objects.filter(inspection_file__isnull=False).exclude(
            inspection_file=""
        )

        total_count = inspections.count()

        if total_count == 0:
            self.stdout.write(self.style.WARNING("⚠️ لا توجد معاينات تحتوي على ملفات."))
            return

        self.stdout.write(f"📊 تم العثور على {total_count} معاينة تحتوي على ملفات.")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 وضع المعاينة - لن يتم تطبيق التغييرات.")
            )

        # الحصول على خدمة Google Drive إذا كان مطلوب التحقق
        drive_service = None
        if check_drive:
            drive_service = get_google_drive_service()
            if not drive_service:
                self.stdout.write(self.style.ERROR("❌ فشل في الاتصال بـ Google Drive"))
                check_drive = False

        fixed_count = 0
        error_count = 0

        for inspection in inspections:
            try:
                # التحقق من وجود الملف محلياً
                file_exists = False
                if inspection.inspection_file:
                    file_path = inspection.inspection_file.path
                    file_exists = os.path.exists(file_path)

                # التحقق من حالة الرفع الحالية
                current_status = inspection.is_uploaded_to_drive
                has_drive_url = bool(inspection.google_drive_file_url)
                has_drive_id = bool(inspection.google_drive_file_id)

                # تحديد الحالة الصحيحة
                should_be_uploaded = has_drive_url and has_drive_id

                # التحقق من Google Drive إذا كان مطلوب
                drive_file_exists = None
                if check_drive and drive_service:
                    if has_drive_id:
                        try:
                            drive_service.service.files().get(
                                fileId=inspection.google_drive_file_id
                            ).execute()
                            drive_file_exists = True
                        except:
                            drive_file_exists = False
                            should_be_uploaded = False
                    else:
                        # البحث عن الملف بالاسم إذا لم يكن هناك معرف
                        try:
                            filename = (
                                inspection.google_drive_file_name
                                or inspection.generate_drive_filename()
                            )
                            files = (
                                drive_service.service.files()
                                .list(
                                    q=f"name='{filename}' and trashed=false",
                                    fields="files(id, name, webViewLink)",
                                )
                                .execute()
                            )

                            if files.get("files"):
                                # تم العثور على الملف - تحديث البيانات
                                file_info = files["files"][0]
                                inspection.google_drive_file_id = file_info["id"]
                                inspection.google_drive_file_url = file_info[
                                    "webViewLink"
                                ]
                                inspection.is_uploaded_to_drive = True
                                inspection.google_drive_file_name = filename

                                if not dry_run:
                                    inspection.save(
                                        update_fields=[
                                            "google_drive_file_id",
                                            "google_drive_file_url",
                                            "is_uploaded_to_drive",
                                            "google_drive_file_name",
                                        ]
                                    )

                                drive_file_exists = True
                                should_be_uploaded = True
                                has_drive_url = True
                                has_drive_id = True

                                self.stdout.write(
                                    f"   🔧 تم العثور على الملف وتحديث البيانات"
                                )
                            else:
                                drive_file_exists = False
                        except Exception as search_error:
                            self.stdout.write(
                                f"   ❌ خطأ في البحث: {str(search_error)}"
                            )
                            drive_file_exists = False

                # عرض معلومات المعاينة
                self.stdout.write(f"\n📋 معاينة #{inspection.id}:")
                self.stdout.write(
                    f'   العميل: {inspection.customer.name if inspection.customer else "غير محدد"}'
                )
                self.stdout.write(
                    f'   الملف المحلي: {"✅ موجود" if file_exists else "❌ مفقود"}'
                )
                self.stdout.write(
                    f'   الحالة الحالية: {"✅ مرفوع" if current_status else "❌ غير مرفوع"}'
                )
                self.stdout.write(
                    f'   رابط Google Drive: {"✅ موجود" if has_drive_url else "❌ مفقود"}'
                )
                self.stdout.write(
                    f'   معرف Google Drive: {"✅ موجود" if has_drive_id else "❌ مفقود"}'
                )

                if check_drive and has_drive_id:
                    self.stdout.write(
                        f'   الملف في Google Drive: {"✅ موجود" if drive_file_exists else "❌ مفقود"}'
                    )

                # تحديد ما إذا كان يحتاج إصلاح
                needs_fix = current_status != should_be_uploaded

                if needs_fix:
                    self.stdout.write(
                        f"   🔧 يحتاج إصلاح: {current_status} → {should_be_uploaded}"
                    )

                    if not dry_run:
                        # تطبيق الإصلاح
                        inspection.is_uploaded_to_drive = should_be_uploaded
                        inspection.save(update_fields=["is_uploaded_to_drive"])

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"   ✅ تم إصلاح المعاينة #{inspection.id}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"   🔍 سيتم إصلاح المعاينة #{inspection.id}"
                            )
                        )

                    fixed_count += 1
                else:
                    self.stdout.write(f"   ✅ الحالة صحيحة")

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"   ❌ خطأ في المعاينة #{inspection.id}: {str(e)}"
                    )
                )

        # عرض النتائج النهائية
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"📊 ملخص العملية:"))
        self.stdout.write(f"   إجمالي المعاينات: {total_count}")
        self.stdout.write(f"   تم الإصلاح: {fixed_count}")
        self.stdout.write(f"   الأخطاء: {error_count}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n🔍 هذه كانت معاينة فقط. لتطبيق التغييرات، قم بتشغيل الأمر بدون --dry-run"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n✅ تم الانتهاء من إصلاح حالة الرفع بنجاح!")
            )

            if fixed_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"💡 تم إصلاح {fixed_count} معاينة. يجب أن تظهر الأيقونات بالألوان الصحيحة الآن."
                    )
                )
