from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from manufacturing.models import ManufacturingOrder

User = get_user_model()

class Command(BaseCommand):
    help = 'إعداد صلاحيات الموافقة على أوامر التصنيع'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='اسم المستخدم الذي سيحصل على صلاحيات الموافقة',
        )
        parser.add_argument(
            '--all-staff',
            action='store_true',
            help='إعطاء صلاحيات الموافقة لجميع الموظفين',
        )

    def handle(self, *args, **options):
        # الحصول على صلاحيات الموافقة
        content_type = ContentType.objects.get_for_model(ManufacturingOrder)
        
        try:
            approve_permission = Permission.objects.get(
                codename='can_approve_orders',
                content_type=content_type
            )
            reject_permission = Permission.objects.get(
                codename='can_reject_orders',
                content_type=content_type
            )
        except Permission.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('صلاحيات الموافقة غير موجودة. يرجى تشغيل migrate أولاً.')
            )
            return

        if options['user']:
            # إعطاء صلاحيات لمستخدم محدد
            try:
                user = User.objects.get(username=options['user'])
                user.user_permissions.add(approve_permission, reject_permission)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'تم إعطاء صلاحيات الموافقة للمستخدم: {user.username}'
                    )
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'المستخدم {options["user"]} غير موجود')
                )
                
        elif options['all_staff']:
            # إعطاء صلاحيات لجميع الموظفين
            staff_users = User.objects.filter(is_staff=True)
            for user in staff_users:
                user.user_permissions.add(approve_permission, reject_permission)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'تم إعطاء صلاحيات الموافقة لـ {staff_users.count()} موظف'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    'يرجى تحديد --user أو --all-staff'
                )
            )
            
        # عرض المستخدمين الذين لديهم صلاحيات الموافقة
        users_with_permission = User.objects.filter(
            user_permissions__in=[approve_permission]
        ).distinct()
        
        if users_with_permission.exists():
            self.stdout.write('\nالمستخدمون الذين لديهم صلاحيات الموافقة:')
            for user in users_with_permission:
                self.stdout.write(f'  - {user.username} ({user.get_full_name()})')
        else:
            self.stdout.write(
                self.style.WARNING('\nلا يوجد مستخدمون لديهم صلاحيات الموافقة')
            ) 