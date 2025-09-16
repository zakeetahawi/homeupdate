from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Command(BaseCommand):
    help = _('إنشاء مستخدم مسؤول جديد')

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help=_('اسم المستخدم'))
        parser.add_argument('--email', type=str, default='admin@example.com', help=_('البريد الإلكتروني'))
        parser.add_argument('--password', type=str, default=None, help=_('كلمة المرور'))
        parser.add_argument('--force', action='store_true', help=_('إنشاء المستخدم حتى لو كان موجودًا بالفعل'))

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        force = options['force']

        # التحقق من وجود المستخدم
        if User.objects.filter(username=username).exists() and not force:
            self.stdout.write(self.style.WARNING(
                f'المستخدم "{username}" موجود بالفعل. استخدم --force لإعادة إنشائه.'
            ))
            return

        # إنشاء المستخدم
        try:
            if User.objects.filter(username=username).exists() and force:
                user = User.objects.get(username=username)
                user.email = email
                if password:
                    user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f'تم تحديث المستخدم المسؤول "{username}" بنجاح.'
                ))
            else:
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password or username  # استخدام اسم المستخدم ككلمة مرور إذا لم يتم تحديد كلمة مرور
                )
                self.stdout.write(self.style.SUCCESS(
                    f'تم إنشاء المستخدم المسؤول "{username}" بنجاح.'
                ))
                if not password:
                    self.stdout.write(self.style.WARNING(
                        f'تم استخدام اسم المستخدم "{username}" ككلمة مرور. يرجى تغييرها فورًا.'
                    ))
        except Exception as e:
            raise CommandError(f'حدث خطأ أثناء إنشاء المستخدم: {str(e)}')
