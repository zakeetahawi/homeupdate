from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from accounts.models import Role, User, UserRole
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class Command(BaseCommand):
    help = 'مراجعة وتوحيد الأدوار والصلاحيات في النظام'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='إصلاح المشاكل المكتشفة تلقائياً'
        )
        parser.add_argument(
            '--report-only',
            action='store_true',
            help='عرض التقرير فقط بدون إجراء تغييرات'
        )

    def handle(self, *args, **options):
        self.stdout.write('بدء مراجعة الأدوار والصلاحيات...')
        
        # جمع المعلومات
        roles_info = self.analyze_roles()
        permissions_info = self.analyze_permissions()
        users_info = self.analyze_users()
        
        # عرض التقرير
        self.display_report(roles_info, permissions_info, users_info)
        
        # إصلاح المشاكل إذا طُلب
        if options['fix'] and not options['report_only']:
            self.fix_issues(roles_info, permissions_info, users_info)
        
        self.stdout.write(self.style.SUCCESS('اكتملت مراجعة الأدوار والصلاحيات!'))

    def analyze_roles(self):
        """تحليل الأدوار الموجودة"""
        roles = Role.objects.all()
        roles_info = {
            'total': roles.count(),
            'system_roles': roles.filter(is_system_role=True).count(),
            'custom_roles': roles.filter(is_system_role=False).count(),
            'roles_without_permissions': roles.filter(permissions__isnull=True).count(),
            'roles_without_users': [],
            'duplicate_roles': []
        }
        
        # البحث عن الأدوار بدون مستخدمين
        for role in roles:
            if not role.user_roles.exists():
                roles_info['roles_without_users'].append(role.name)
        
        # البحث عن الأدوار المكررة (نفس الاسم)
        role_names = list(roles.values_list('name', flat=True))
        duplicate_names = [name for name in set(role_names) if role_names.count(name) > 1]
        roles_info['duplicate_roles'] = duplicate_names
        
        return roles_info

    def analyze_permissions(self):
        """تحليل الصلاحيات"""
        permissions = Permission.objects.all()
        permissions_info = {
            'total': permissions.count(),
            'unused_permissions': [],
            'orphaned_permissions': []
        }
        
        # البحث عن الصلاحيات غير المستخدمة
        for permission in permissions:
            if not permission.role_set.exists() and not permission.user_set.exists():
                permissions_info['unused_permissions'].append(
                    f"{permission.content_type.app_label}.{permission.codename}"
                )
        
        return permissions_info

    def analyze_users(self):
        """تحليل المستخدمين"""
        users = User.objects.all()
        users_info = {
            'total': users.count(),
            'users_without_roles': [],
            'users_with_multiple_roles': [],
            'superusers': users.filter(is_superuser=True).count(),
            'staff_users': users.filter(is_staff=True).count()
        }
        
        for user in users:
            if not user.user_roles.exists() and not user.is_superuser:
                users_info['users_without_roles'].append(user.username)
            
            if user.user_roles.count() > 1:
                users_info['users_with_multiple_roles'].append(user.username)
        
        return users_info

    def display_report(self, roles_info, permissions_info, users_info):
        """عرض تقرير المراجعة"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('تقرير مراجعة الأدوار والصلاحيات')
        self.stdout.write('='*50)
        
        # معلومات الأدوار
        self.stdout.write('\n📊 معلومات الأدوار:')
        self.stdout.write(f'  • إجمالي الأدوار: {roles_info["total"]}')
        self.stdout.write(f'  • أدوار النظام: {roles_info["system_roles"]}')
        self.stdout.write(f'  • الأدوار المخصصة: {roles_info["custom_roles"]}')
        self.stdout.write(f'  • أدوار بدون صلاحيات: {roles_info["roles_without_permissions"]}')
        
        if roles_info['roles_without_users']:
            self.stdout.write(self.style.WARNING(
                f'  ⚠️  أدوار بدون مستخدمين: {", ".join(roles_info["roles_without_users"])}'
            ))
        
        if roles_info['duplicate_roles']:
            self.stdout.write(self.style.ERROR(
                f'  ❌ أدوار مكررة: {", ".join(roles_info["duplicate_roles"])}'
            ))
        
        # معلومات الصلاحيات
        self.stdout.write('\n🔐 معلومات الصلاحيات:')
        self.stdout.write(f'  • إجمالي الصلاحيات: {permissions_info["total"]}')
        self.stdout.write(f'  • صلاحيات غير مستخدمة: {len(permissions_info["unused_permissions"])}')
        
        if permissions_info['unused_permissions']:
            self.stdout.write(self.style.WARNING(
                f'  ⚠️  صلاحيات غير مستخدمة: {", ".join(permissions_info["unused_permissions"][:5])}'
            ))
        
        # معلومات المستخدمين
        self.stdout.write('\n👥 معلومات المستخدمين:')
        self.stdout.write(f'  • إجمالي المستخدمين: {users_info["total"]}')
        self.stdout.write(f'  • المستخدمون المشرفون: {users_info["superusers"]}')
        self.stdout.write(f'  • المستخدمون الموظفون: {users_info["staff_users"]}')
        self.stdout.write(f'  • مستخدمون بدون أدوار: {len(users_info["users_without_roles"])}')
        self.stdout.write(f'  • مستخدمون بأدوار متعددة: {len(users_info["users_with_multiple_roles"])}')
        
        if users_info['users_without_roles']:
            self.stdout.write(self.style.WARNING(
                f'  ⚠️  مستخدمون بدون أدوار: {", ".join(users_info["users_without_roles"][:5])}'
            ))
        
        if users_info['users_with_multiple_roles']:
            self.stdout.write(self.style.WARNING(
                f'  ⚠️  مستخدمون بأدوار متعددة: {", ".join(users_info["users_with_multiple_roles"][:5])}'
            ))

    def fix_issues(self, roles_info, permissions_info, users_info):
        """إصلاح المشاكل المكتشفة"""
        self.stdout.write('\n🔧 بدء إصلاح المشاكل...')
        
        # إصلاح المستخدمين بدون أدوار
        if users_info['users_without_roles']:
            self.fix_users_without_roles(users_info['users_without_roles'])
        
        # إصلاح الأدوار المكررة
        if roles_info['duplicate_roles']:
            self.fix_duplicate_roles(roles_info['duplicate_roles'])
        
        # إصلاح الأدوار بدون صلاحيات
        if roles_info['roles_without_permissions'] > 0:
            self.fix_roles_without_permissions()
        
        self.stdout.write(self.style.SUCCESS('تم إصلاح المشاكل بنجاح!'))

    def fix_users_without_roles(self, usernames):
        """إصلاح المستخدمين بدون أدوار"""
        self.stdout.write('  🔧 إصلاح المستخدمين بدون أدوار...')
        
        # البحث عن دور افتراضي أو إنشاء دور موظف مبيعات
        default_role, created = Role.objects.get_or_create(
            name='موظف مبيعات',
            defaults={
                'description': 'دور افتراضي للمستخدمين الجدد',
                'is_system_role': True
            }
        )
        
        for username in usernames:
            try:
                user = User.objects.get(username=username)
                if not user.is_superuser:
                    default_role.assign_to_user(user)
                    self.stdout.write(f'    ✅ تم إسناد دور افتراضي للمستخدم: {username}')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'    ❌ المستخدم غير موجود: {username}'))

    def fix_duplicate_roles(self, duplicate_names):
        """إصلاح الأدوار المكررة"""
        self.stdout.write('  🔧 إصلاح الأدوار المكررة...')
        
        for name in duplicate_names:
            roles = Role.objects.filter(name=name).order_by('created_at')
            if roles.count() > 1:
                # الاحتفاظ بالدور الأقدم وحذف الباقي
                keep_role = roles.first()
                delete_roles = roles[1:]
                
                for role in delete_roles:
                    # نقل المستخدمين إلى الدور المحتفظ به
                    for user_role in role.user_roles.all():
                        keep_role.assign_to_user(user_role.user)
                    
                    # حذف الدور المكرر
                    role.delete()
                
                self.stdout.write(f'    ✅ تم إصلاح الدور المكرر: {name}')

    def fix_roles_without_permissions(self):
        """إصلاح الأدوار بدون صلاحيات"""
        self.stdout.write('  🔧 إصلاح الأدوار بدون صلاحيات...')
        
        roles_without_permissions = Role.objects.filter(permissions__isnull=True)
        
        for role in roles_without_permissions:
            if not role.is_system_role:
                # إضافة صلاحيات أساسية للأدوار المخصصة
                basic_permissions = Permission.objects.filter(
                    codename__in=['view_customer', 'add_customer', 'view_order', 'add_order']
                )
                role.permissions.add(*basic_permissions)
                self.stdout.write(f'    ✅ تم إضافة صلاحيات أساسية للدور: {role.name}')
            else:
                self.stdout.write(self.style.WARNING(
                    f'    ⚠️  دور نظام بدون صلاحيات: {role.name}'
                )) 