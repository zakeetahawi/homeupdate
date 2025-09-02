"""
أمر إدارة لإعداد صلاحيات الطلبات الأساسية
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from orders.models import Order


class Command(BaseCommand):
    help = 'إعداد صلاحيات الطلبات الأساسية'

    def handle(self, *args, **options):
        self.stdout.write('بدء إعداد صلاحيات الطلبات...')
        
        # الحصول على نوع المحتوى للطلبات
        content_type = ContentType.objects.get_for_model(Order)
        
        # إنشاء الصلاحيات الأساسية إذا لم تكن موجودة
        permissions_to_create = [
            ('view_own_orders', 'يمكن عرض الطلبات الخاصة'),
            ('view_branch_orders', 'يمكن عرض طلبات الفرع'),
            ('view_all_orders', 'يمكن عرض جميع الطلبات'),
            ('manage_orders_dashboard', 'يمكن الوصول لداشبورد الطلبات'),
        ]
        
        created_count = 0
        for codename, name in permissions_to_create:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=content_type,
                defaults={'name': name}
            )
            if created:
                created_count += 1
                self.stdout.write(f'تم إنشاء صلاحية: {name}')
        
        # إنشاء مجموعات المستخدمين
        groups_to_create = [
            ('بائع', ['view_own_orders', 'add_order', 'change_order']),
            ('مدير فرع', ['view_branch_orders', 'add_order', 'change_order', 'delete_order', 'manage_orders_dashboard']),
            ('مدير عام', ['view_all_orders', 'add_order', 'change_order', 'delete_order', 'manage_orders_dashboard']),
        ]
        
        groups_created = 0
        for group_name, permission_codenames in groups_to_create:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                groups_created += 1
                self.stdout.write(f'تم إنشاء مجموعة: {group_name}')
            
            # إضافة الصلاحيات للمجموعة
            for codename in permission_codenames:
                try:
                    permission = Permission.objects.get(
                        codename=codename,
                        content_type=content_type
                    )
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    # محاولة البحث في الصلاحيات الافتراضية
                    try:
                        permission = Permission.objects.get(codename=codename)
                        group.permissions.add(permission)
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'لم يتم العثور على صلاحية: {codename}')
                        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'تم إعداد صلاحيات الطلبات بنجاح!\n'
                f'تم إنشاء {created_count} صلاحية جديدة\n'
                f'تم إنشاء {groups_created} مجموعة جديدة'
            )
        )