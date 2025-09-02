import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Role, UserRole

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'تحديث صلاحيات المستخدمين بناءً على أدوارهم'

    def add_arguments(self, parser):
        parser.add_argument('--role_id', type=int, help='معرف الدور المراد تحديث صلاحياته')
        parser.add_argument('--user_id', type=int, help='معرف المستخدم المراد تحديث صلاحياته')

    def handle(self, *args, **options):
        role_id = options.get('role_id')
        user_id = options.get('user_id')
        
        if role_id:
            # تحديث صلاحيات المستخدمين لدور محدد
            try:
                role = Role.objects.get(id=role_id)
                user_roles = UserRole.objects.filter(role=role)
                self.update_user_permissions_for_role(role, user_roles)
                self.stdout.write(self.style.SUCCESS(f'تم تحديث صلاحيات {user_roles.count()} مستخدمين للدور {role.name}'))
            except Role.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'الدور برقم {role_id} غير موجود'))
        
        elif user_id:
            # تحديث صلاحيات مستخدم محدد
            try:
                user = User.objects.get(id=user_id)
                self.update_permissions_for_user(user)
                self.stdout.write(self.style.SUCCESS(f'تم تحديث صلاحيات المستخدم {user.username}'))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'المستخدم برقم {user_id} غير موجود'))
        
        else:
            # تحديث صلاحيات جميع المستخدمين
            users = User.objects.filter(is_active=True)
            count = 0
            for user in users:
                self.update_permissions_for_user(user)
                count += 1
            
            self.stdout.write(self.style.SUCCESS(f'تم تحديث صلاحيات {count} مستخدمين بنجاح'))

    def update_user_permissions_for_role(self, role, user_roles):
        """تحديث صلاحيات المستخدمين المرتبطين بدور معين"""
        for user_role in user_roles:
            user = user_role.user
            self.update_permissions_for_user(user)

    def update_permissions_for_user(self, user):
        """تحديث صلاحيات مستخدم بناءً على أدواره"""
        # مسح كافة الصلاحيات المباشرة للمستخدم
        user.user_permissions.clear()
        
        # إعادة تعيين الصلاحيات من الأدوار
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        
        for user_role in user_roles:
            role = user_role.role
            for permission in role.permissions.all():
                user.user_permissions.add(permission)
        
        return user