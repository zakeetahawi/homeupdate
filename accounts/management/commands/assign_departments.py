"""
أمر إدارة لتخصيص الأقسام للمستخدمين
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Department

User = get_user_model()

class Command(BaseCommand):
    help = 'Assign departments to users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            required=True,
            help='Username to assign departments to',
        )
        parser.add_argument(
            '--departments',
            type=str,
            help='Comma-separated list of department codes (e.g., customers,orders)',
        )
        parser.add_argument(
            '--list-departments',
            action='store_true',
            help='List available departments',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all departments for the user',
        )
        parser.add_argument(
            '--show',
            action='store_true',
            help='Show current departments for the user',
        )

    def handle(self, *args, **options):
        username = options['user']
        
        # التحقق من وجود المستخدم
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"❌ المستخدم '{username}' غير موجود")
            )
            return
        
        # عرض الأقسام المتاحة
        if options['list_departments']:
            departments = Department.objects.filter(is_active=True).order_by('order')
            self.stdout.write("📋 الأقسام المتاحة:")
            for dept in departments:
                self.stdout.write(f"  - {dept.code}: {dept.name}")
            return
        
        # عرض الأقسام الحالية للمستخدم
        if options['show']:
            current_departments = user.departments.all()
            self.stdout.write(f"👤 الأقسام الحالية للمستخدم '{username}':")
            if current_departments.exists():
                for dept in current_departments:
                    self.stdout.write(f"  - {dept.code}: {dept.name}")
            else:
                self.stdout.write("  لا توجد أقسام مخصصة")
            return
        
        # مسح جميع الأقسام
        if options['clear']:
            user.departments.clear()
            self.stdout.write(
                self.style.SUCCESS(f"✅ تم مسح جميع الأقسام للمستخدم '{username}'")
            )
            return
        
        # تخصيص أقسام جديدة
        if options['departments']:
            dept_codes = [code.strip() for code in options['departments'].split(',')]
            
            # التحقق من وجود الأقسام
            existing_departments = Department.objects.filter(
                code__in=dept_codes, 
                is_active=True
            )
            
            found_codes = list(existing_departments.values_list('code', flat=True))
            missing_codes = [code for code in dept_codes if code not in found_codes]
            
            if missing_codes:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ أقسام غير موجودة: {', '.join(missing_codes)}")
                )
            
            if existing_departments.exists():
                # مسح الأقسام الحالية وإضافة الجديدة
                user.departments.clear()
                user.departments.add(*existing_departments)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ تم تخصيص {existing_departments.count()} قسم للمستخدم '{username}'"
                    )
                )
                
                self.stdout.write("📋 الأقسام المخصصة:")
                for dept in existing_departments:
                    self.stdout.write(f"  - {dept.code}: {dept.name}")
            else:
                self.stdout.write(
                    self.style.ERROR("❌ لم يتم العثور على أقسام صالحة")
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️ يجب تحديد --departments أو --clear أو --show أو --list-departments"
                )
            )
            self.stdout.write("\nأمثلة:")
            self.stdout.write("  python manage.py assign_departments --user john --departments customers,orders")
            self.stdout.write("  python manage.py assign_departments --user john --show")
            self.stdout.write("  python manage.py assign_departments --user john --clear")
            self.stdout.write("  python manage.py assign_departments --user john --list-departments")
