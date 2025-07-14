from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import Role, User
from django.db.models import Q


class Command(BaseCommand):
    help = 'إنشاء أدوار مخصصة مع صلاحيات محددة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='اسم الدور'
        )
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='وصف الدور'
        )
        parser.add_argument(
            '--permissions',
            type=str,
            default='',
            help='قائمة الصلاحيات مفصولة بفواصل (مثال: view_customer,add_customer)'
        )
        parser.add_argument(
            '--apps',
            type=str,
            default='',
            help='التطبيقات المطلوبة مفصولة بفواصل (مثال: customers,orders)'
        )
        parser.add_argument(
            '--users',
            type=str,
            default='',
            help='أسماء المستخدمين لإسناد الدور لهم مفصولة بفواصل'
        )
        parser.add_argument(
            '--read-only',
            action='store_true',
            help='إنشاء دور للقراءة فقط'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='إعادة إنشاء الدور إذا كان موجوداً'
        )

    def handle(self, *args, **options):
        role_name = options['name']
        description = options['description']
        permissions_list = options['permissions']
        apps_list = options['apps']
        users_list = options['users']
        read_only = options['read_only']
        force = options['force']

        # التحقق من وجود الدور
        existing_role = Role.objects.filter(name=role_name).first()
        if existing_role and not force:
            raise CommandError(f'الدور "{role_name}" موجود بالفعل. استخدم --force لإعادة الإنشاء.')

        # إنشاء أو تحديث الدور
        if existing_role and force:
            role = existing_role
            role.description = description
            role.save()
            self.stdout.write(f'تم تحديث الدور: {role_name}')
        else:
            role = Role.objects.create(
                name=role_name,
                description=description,
                is_system_role=False
            )
            self.stdout.write(f'تم إنشاء الدور: {role_name}')

        # تحديد الصلاحيات
        permissions = []
        
        if permissions_list:
            # استخدام الصلاحيات المحددة
            permission_codes = [p.strip() for p in permissions_list.split(',')]
            for code in permission_codes:
                try:
                    permission = Permission.objects.get(codename=code)
                    permissions.append(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'الصلاحية غير موجودة: {code}'))
        
        elif apps_list:
            # استخدام صلاحيات التطبيقات المحددة
            apps = [app.strip() for app in apps_list.split(',')]
            for app in apps:
                app_permissions = Permission.objects.filter(
                    content_type__app_label=app
                )
                if read_only:
                    app_permissions = app_permissions.filter(codename__startswith='view')
                
                permissions.extend(app_permissions)
                self.stdout.write(f'تم إضافة {app_permissions.count()} صلاحية من التطبيق: {app}')
        
        else:
            # صلاحيات افتراضية
            default_permissions = Permission.objects.filter(
                codename__in=['view_customer', 'add_customer', 'view_order', 'add_order']
            )
            permissions.extend(default_permissions)
            self.stdout.write('تم إضافة الصلاحيات الافتراضية')

        # إضافة الصلاحيات للدور
        if permissions:
            role.permissions.add(*permissions)
            self.stdout.write(f'تم إضافة {len(permissions)} صلاحية للدور')

        # إسناد الدور للمستخدمين
        if users_list:
            usernames = [u.strip() for u in users_list.split(',')]
            assigned_count = 0
            
            for username in usernames:
                try:
                    user = User.objects.get(username=username)
                    role.assign_to_user(user)
                    assigned_count += 1
                    self.stdout.write(f'تم إسناد الدور للمستخدم: {username}')
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'المستخدم غير موجود: {username}'))
            
            self.stdout.write(f'تم إسناد الدور لـ {assigned_count} مستخدم')

        # عرض ملخص الدور
        self.display_role_summary(role)

    def display_role_summary(self, role):
        """عرض ملخص الدور"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'ملخص الدور: {role.name}')
        self.stdout.write('='*50)
        self.stdout.write(f'الوصف: {role.description}')
        self.stdout.write(f'نوع الدور: {"نظام" if role.is_system_role else "مخصص"}')
        self.stdout.write(f'عدد الصلاحيات: {role.permissions.count()}')
        self.stdout.write(f'عدد المستخدمين: {role.user_roles.count()}')
        
        # عرض الصلاحيات
        if role.permissions.exists():
            self.stdout.write('\nالصلاحيات:')
            for permission in role.permissions.all()[:10]:  # عرض أول 10 صلاحيات
                self.stdout.write(f'  • {permission.content_type.app_label}.{permission.codename}')
            
            if role.permissions.count() > 10:
                self.stdout.write(f'  ... و {role.permissions.count() - 10} صلاحية أخرى')
        
        # عرض المستخدمين
        if role.user_roles.exists():
            self.stdout.write('\nالمستخدمون:')
            for user_role in role.user_roles.all()[:5]:  # عرض أول 5 مستخدمين
                self.stdout.write(f'  • {user_role.user.username}')
            
            if role.user_roles.count() > 5:
                self.stdout.write(f'  ... و {role.user_roles.count() - 5} مستخدم آخر')

    def get_available_permissions(self):
        """الحصول على قائمة الصلاحيات المتاحة"""
        permissions = Permission.objects.all().order_by('content_type__app_label', 'codename')
        permission_list = []
        
        for permission in permissions:
            permission_list.append(
                f"{permission.content_type.app_label}.{permission.codename}"
            )
        
        return permission_list

    def get_available_apps(self):
        """الحصول على قائمة التطبيقات المتاحة"""
        content_types = ContentType.objects.all().values_list('app_label', flat=True).distinct()
        return sorted(list(set(content_types))) 