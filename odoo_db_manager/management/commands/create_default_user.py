"""
Django management command لإنشاء مستخدم افتراضي تلقائياً
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "إنشاء مستخدم افتراضي إذا لم يكن هناك مستخدمين في قاعدة البيانات"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            default="admin",
            help="اسم المستخدم الافتراضي (افتراضي: admin)",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="admin123",
            help="كلمة مرور المستخدم الافتراضي (افتراضي: admin123)",
        )
        parser.add_argument(
            "--email",
            type=str,
            default="admin@example.com",
            help="بريد المستخدم الافتراضي",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="إنشاء المستخدم حتى لو كان هناك مستخدمين آخرين",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        try:
            with transaction.atomic():
                # التحقق من وجود مستخدمين
                users_count = User.objects.count()

                if users_count == 0 or options["force"]:
                    username = options["username"]
                    password = options["password"]
                    email = options["email"]

                    # التحقق من وجود المستخدم مسبقاً
                    if User.objects.filter(username=username).exists():
                        if not options["force"]:
                            self.stdout.write(
                                self.style.WARNING(f'المستخدم "{username}" موجود مسبقاً')
                            )
                            return
                        else:
                            # حذف المستخدم الموجود وإنشاء جديد
                            User.objects.filter(username=username).delete()
                            self.stdout.write(
                                self.style.WARNING(
                                    f'تم حذف المستخدم "{username}" الموجود مسبقاً'
                                )
                            )

                    # إنشاء المستخدم الافتراضي
                    user = User.objects.create_superuser(
                        username=username,
                        email=email,
                        password=password,
                        first_name="مدير",
                        last_name="النظام",
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"تم إنشاء المستخدم الافتراضي بنجاح:\n"
                            f"اسم المستخدم: {username}\n"
                            f"كلمة المرور: {password}\n"
                            f"البريد الإلكتروني: {email}"
                        )
                    )

                    # عرض رسالة تحذيرية حول تغيير كلمة المرور
                    self.stdout.write(
                        self.style.WARNING(
                            "تحذير: يرجى تغيير كلمة المرور الافتراضية من لوحة الإدارة لأسباب أمنية!"
                        )
                    )

                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"يوجد {users_count} مستخدم في النظام - لا حاجة لإنشاء مستخدم افتراضي"
                        )
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"حدث خطأ أثناء إنشاء المستخدم الافتراضي: {str(e)}")
            )
            raise
