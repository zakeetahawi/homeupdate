# Data migration لإنشاء جميع المجموعات الثابتة مع صلاحياتها

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import migrations


def create_all_groups(apps, schema_editor):
    """إنشاء جميع المجموعات الثابتة مع صلاحياتها"""

    # قائمة المجموعات المطلوبة مع صلاحياتها
    groups_config = {
        "مدير عام": {
            "permissions": ["*"],  # كل الصلاحيات
            "description": "صلاحيات كاملة على النظام",
        },
        "مدير منطقة": {
            "permissions": [
                # صلاحيات الطلبات
                "orders.view_order",
                "orders.add_order",
                "orders.change_order",
                # صلاحيات العملاء
                "customers.view_customer",
                "customers.add_customer",
                "customers.change_customer",
                # صلاحيات التقارير
                "reports.view_report",
            ],
            "description": "إدارة الطلبات والعملاء في المنطقة",
        },
        "مدير فرع": {
            "permissions": [
                # صلاحيات الطلبات
                "orders.view_order",
                "orders.add_order",
                "orders.change_order",
                # صلاحيات العملاء
                "customers.view_customer",
                "customers.add_customer",
                "customers.change_customer",
            ],
            "description": "إدارة الطلبات والعملاء في الفرع",
        },
        "بائع": {
            "permissions": [
                "orders.view_order",
                "orders.add_order",
                "customers.view_customer",
                "customers.add_customer",
            ],
            "description": "إنشاء وعرض الطلبات والعملاء",
        },
        "مسؤول مصنع": {
            "permissions": [
                "manufacturing.view_manufacturingorder",
                "manufacturing.add_manufacturingorder",
                "manufacturing.change_manufacturingorder",
                "manufacturing.can_receive_fabric",
                "manufacturing.can_deliver_to_production_line",
                "manufacturing.can_view_fabric_receipts",
                "inventory.view_warehouse",
                "inventory.view_product",
            ],
            "description": "إدارة التصنيع والمخزون",
        },
        "مسؤول استلام مصنع": {
            "permissions": [
                "manufacturing.can_receive_fabric",
                "manufacturing.can_deliver_to_production_line",
                "manufacturing.can_view_fabric_receipts",
                "manufacturing.view_manufacturingorder",
            ],
            "description": "استلام الأقمشة وتسليمها لخطوط الإنتاج",
        },
        "مسؤول معاينات": {
            "permissions": [
                "inspections.view_inspection",
                "inspections.add_inspection",
                "inspections.change_inspection",
                "inspections.delete_inspection",
            ],
            "description": "إدارة المعاينات",
        },
        "فني معاينة": {
            "permissions": [
                "inspections.view_inspection",
                "inspections.change_inspection",
            ],
            "description": "تنفيذ المعاينات",
        },
        "مسؤول تركيبات": {
            "permissions": [
                "installations.view_installation",
                "installations.add_installation",
                "installations.change_installation",
                "installations.delete_installation",
            ],
            "description": "إدارة التركيبات",
        },
        "موظف مستودع": {
            "permissions": [
                "inventory.view_warehouse",
                "inventory.view_product",
                "inventory.change_product",
                "inventory.view_stocktransfer",
                "inventory.add_stocktransfer",
            ],
            "description": "إدارة المخزون والتحويلات",
        },
    }

    total_created = 0
    total_updated = 0

    for group_name, config in groups_config.items():
        group, created = Group.objects.get_or_create(name=group_name)

        if created:
            total_created += 1
            print(f"✓ تم إنشاء مجموعة: {group_name}")
        else:
            total_updated += 1
            print(f"⟳ تحديث مجموعة موجودة: {group_name}")

        # إضافة الصلاحيات
        if config["permissions"] == ["*"]:
            # إعطاء كل الصلاحيات
            all_permissions = Permission.objects.all()
            group.permissions.set(all_permissions)
            print(f"  → تم منح جميع الصلاحيات ({all_permissions.count()} صلاحية)")
        else:
            # إضافة الصلاحيات المحددة
            permissions_added = 0
            for perm_code in config["permissions"]:
                try:
                    app_label, codename = perm_code.split(".")
                    perm = Permission.objects.get(
                        content_type__app_label=app_label, codename=codename
                    )
                    group.permissions.add(perm)
                    permissions_added += 1
                except Permission.DoesNotExist:
                    print(f"  ⚠️ الصلاحية غير موجودة: {perm_code}")
                except ValueError:
                    print(f"  ⚠️ تنسيق خاطئ للصلاحية: {perm_code}")

            print(f"  → تم منح {permissions_added} صلاحية")

    print(f"\n{'='*60}")
    print(f"✅ تم إنشاء {total_created} مجموعة جديدة")
    print(f"⟳ تم تحديث {total_updated} مجموعة موجودة")
    print(f"📊 إجمالي المجموعات: {len(groups_config)}")
    print(f"{'='*60}")


def reverse_create_groups(apps, schema_editor):
    """حذف جميع المجموعات عند التراجع"""
    Group = apps.get_model("auth", "Group")

    groups_to_delete = [
        "مدير عام",
        "مدير منطقة",
        "مدير فرع",
        "بائع",
        "مسؤول مصنع",
        "مسؤول استلام مصنع",
        "مسؤول معاينات",
        "فني معاينة",
        "مسؤول تركيبات",
        "موظف مستودع",
    ]

    deleted_count = Group.objects.filter(name__in=groups_to_delete).delete()[0]
    print(f"تم حذف {deleted_count} مجموعة")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0035_user_is_factory_receiver"),
        ("manufacturing", "0001_initial"),  # للتأكد من وجود صلاحيات التصنيع
    ]

    operations = [
        migrations.RunPython(create_all_groups, reverse_create_groups),
    ]
