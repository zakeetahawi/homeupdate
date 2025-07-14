from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from accounts.models import Role, UserRole
from django.db import transaction
import sys

User = get_user_model()

class Command(BaseCommand):
    help = 'إدارة تعيين الأدوار للمستخدمين'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list-users',
            action='store_true',
            help='عرض قائمة المستخدمين وأدوارهم'
        )
        parser.add_argument(
            '--list-roles',
            action='store_true',
            help='عرض قائمة الأدوار المتاحة'
        )
        parser.add_argument(
            '--assign',
            type=str,
            help='تعيين دور لمستخدم (صيغة: username:role_name)'
        )
        parser.add_argument(
            '--remove',
            type=str,
            help='إزالة دور من مستخدم (صيغة: username:role_name)'
        )
        parser.add_argument(
            '--auto-assign',
            action='store_true',
            help='تعيين أدوار تلقائياً للمستخدمين بدون أدوار'
        )
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='وضع تفاعلي لتعيين الأدوار'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('بدء إدارة تعيين الأدوار...\n'))

        if options['list_users']:
            self.list_users()
        elif options['list_roles']:
            self.list_roles()
        elif options['assign']:
            self.assign_role(options['assign'])
        elif options['remove']:
            self.remove_role(options['remove'])
        elif options['auto_assign']:
            self.auto_assign_roles()
        elif options['interactive']:
            self.interactive_mode()
        else:
            self.show_help()

    def list_users(self):
        """عرض قائمة المستخدمين وأدوارهم"""
        self.stdout.write(self.style.WARNING('📋 قائمة المستخدمين وأدوارهم:\n'))
        
        users = User.objects.all().order_by('username')
        for user in users:
            roles = UserRole.objects.filter(user=user).values_list('role__name', flat=True)
            roles_str = ', '.join(roles) if roles else 'لا توجد أدوار'
            
            status = '✅' if roles else '⚠️'
            self.stdout.write(f'{status} {user.username} ({user.get_full_name() or "بدون اسم"}): {roles_str}')

    def list_roles(self):
        """عرض قائمة الأدوار المتاحة"""
        self.stdout.write(self.style.WARNING('🎭 قائمة الأدوار المتاحة:\n'))
        
        roles = Role.objects.all().order_by('name')
        for role in roles:
            user_count = UserRole.objects.filter(role=role).count()
            self.stdout.write(f'• {role.name} ({user_count} مستخدم)')

    def assign_role(self, assignment):
        """تعيين دور لمستخدم"""
        try:
            username, role_name = assignment.split(':')
            user = User.objects.get(username=username)
            role = Role.objects.get(name=role_name)
            
            # التحقق من عدم وجود الدور مسبقاً
            if UserRole.objects.filter(user=user, role=role).exists():
                self.stdout.write(self.style.WARNING(f'⚠️ المستخدم {username} يملك الدور {role_name} بالفعل'))
                return
            
            with transaction.atomic():
                UserRole.objects.create(user=user, role=role)
                self.stdout.write(self.style.SUCCESS(f'✅ تم تعيين دور {role_name} للمستخدم {username}'))
                
        except ValueError:
            self.stdout.write(self.style.ERROR('❌ صيغة خاطئة. استخدم: username:role_name'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ المستخدم {username} غير موجود'))
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ الدور {role_name} غير موجود'))

    def remove_role(self, assignment):
        """إزالة دور من مستخدم"""
        try:
            username, role_name = assignment.split(':')
            user = User.objects.get(username=username)
            role = Role.objects.get(name=role_name)
            
            user_role = UserRole.objects.filter(user=user, role=role).first()
            if not user_role:
                self.stdout.write(self.style.WARNING(f'⚠️ المستخدم {username} لا يملك الدور {role_name}'))
                return
            
            with transaction.atomic():
                user_role.delete()
                self.stdout.write(self.style.SUCCESS(f'✅ تم إزالة دور {role_name} من المستخدم {username}'))
                
        except ValueError:
            self.stdout.write(self.style.ERROR('❌ صيغة خاطئة. استخدم: username:role_name'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ المستخدم {username} غير موجود'))
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ الدور {role_name} غير موجود'))

    def auto_assign_roles(self):
        """تعيين أدوار تلقائياً للمستخدمين بدون أدوار"""
        self.stdout.write(self.style.WARNING('🤖 بدء التعيين التلقائي للأدوار...\n'))
        
        # الحصول على المستخدمين بدون أدوار
        users_without_roles = []
        for user in User.objects.all():
            if not UserRole.objects.filter(user=user).exists():
                users_without_roles.append(user)
        
        if not users_without_roles:
            self.stdout.write(self.style.SUCCESS('✅ جميع المستخدمين لديهم أدوار'))
            return
        
        # الحصول على الأدوار المتاحة
        available_roles = list(Role.objects.all())
        if not available_roles:
            self.stdout.write(self.style.ERROR('❌ لا توجد أدوار متاحة'))
            return
        
        # تعيين الأدوار تلقائياً
        assigned_count = 0
        for i, user in enumerate(users_without_roles):
            # اختيار دور بشكل دوري
            role = available_roles[i % len(available_roles)]
            
            with transaction.atomic():
                UserRole.objects.create(user=user, role=role)
                self.stdout.write(f'✅ تم تعيين دور {role.name} للمستخدم {user.username}')
                assigned_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ تم تعيين {assigned_count} دور للمستخدمين'))

    def interactive_mode(self):
        """الوضع التفاعلي لتعيين الأدوار"""
        self.stdout.write(self.style.WARNING('🎮 بدء الوضع التفاعلي...\n'))
        
        while True:
            self.stdout.write('\n' + '='*50)
            self.stdout.write('1. عرض المستخدمين')
            self.stdout.write('2. عرض الأدوار')
            self.stdout.write('3. تعيين دور')
            self.stdout.write('4. إزالة دور')
            self.stdout.write('5. تعيين تلقائي')
            self.stdout.write('0. خروج')
            self.stdout.write('='*50)
            
            choice = input('\nاختر رقم العملية: ').strip()
            
            if choice == '0':
                self.stdout.write(self.style.SUCCESS('👋 تم الخروج من الوضع التفاعلي'))
                break
            elif choice == '1':
                self.list_users()
            elif choice == '2':
                self.list_roles()
            elif choice == '3':
                username = input('اسم المستخدم: ').strip()
                role_name = input('اسم الدور: ').strip()
                self.assign_role(f'{username}:{role_name}')
            elif choice == '4':
                username = input('اسم المستخدم: ').strip()
                role_name = input('اسم الدور: ').strip()
                self.remove_role(f'{username}:{role_name}')
            elif choice == '5':
                self.auto_assign_roles()
            else:
                self.stdout.write(self.style.ERROR('❌ اختيار غير صحيح'))

    def show_help(self):
        """عرض المساعدة"""
        self.stdout.write(self.style.WARNING('📖 أوامر إدارة تعيين الأدوار:\n'))
        self.stdout.write('• --list-users: عرض قائمة المستخدمين وأدوارهم')
        self.stdout.write('• --list-roles: عرض قائمة الأدوار المتاحة')
        self.stdout.write('• --assign username:role_name: تعيين دور لمستخدم')
        self.stdout.write('• --remove username:role_name: إزالة دور من مستخدم')
        self.stdout.write('• --auto-assign: تعيين أدوار تلقائياً للمستخدمين بدون أدوار')
        self.stdout.write('• --interactive: الوضع التفاعلي')
        self.stdout.write('\nأمثلة:')
        self.stdout.write('  python manage.py assign_user_roles --assign "admin:مدير النظام"')
        self.stdout.write('  python manage.py assign_user_roles --auto-assign')
        self.stdout.write('  python manage.py assign_user_roles --interactive') 