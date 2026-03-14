"""
أمر لتزامن الأدوار البولينية → UserRole M2M لجميع المستخدمين
يُستخدم مرة واحدة عند التحويل، أو كصيانة دورية.

Usage:
    python manage.py sync_roles_to_m2m
    python manage.py sync_roles_to_m2m --dry-run
"""

from django.core.management.base import BaseCommand

from accounts.models import Role, User, UserRole


class Command(BaseCommand):
    help = "مزامنة حقول الأدوار البولينية إلى UserRole M2M"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض التغييرات بدون تطبيقها",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        users = User.objects.filter(is_active=True)
        created_count = 0
        removed_count = 0

        # تأكد من وجود كل أدوار النظام
        role_objects = {}
        for field_name, role_key in User.ROLE_FIELD_MAP.items():
            role_obj, _ = Role.objects.get_or_create(
                name=role_key,
                defaults={"description": f"دور {role_key} (نظام)", "is_system_role": True},
            )
            role_objects[role_key] = role_obj

        for user in users:
            active_keys = user.get_active_roles()
            for field_name, role_key in User.ROLE_FIELD_MAP.items():
                role_obj = role_objects[role_key]
                has_m2m = UserRole.objects.filter(user=user, role=role_obj).exists()

                if role_key in active_keys and not has_m2m:
                    if not dry_run:
                        UserRole.objects.create(user=user, role=role_obj)
                    created_count += 1
                    self.stdout.write(f"  + {user.username} ← {role_key}")
                elif role_key not in active_keys and has_m2m:
                    if not dry_run:
                        UserRole.objects.filter(user=user, role=role_obj).delete()
                    removed_count += 1
                    self.stdout.write(f"  - {user.username} ✕ {role_key}")

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{prefix}تمت المزامنة: {created_count} إضافة، {removed_count} إزالة"
            )
        )
