"""
Migration: Create Django Groups and Permissions for External Sales (Decorator Engineers) department.
Groups created:
  - مدير قسم مهندسي الديكور (decorator_dept_manager)
  - موظف قسم مهندسي الديكور (decorator_dept_staff)
"""

from django.db import migrations


def create_external_sales_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Helper: safely get permissions
    def get_perms(app_label, codenames):
        perms = []
        for codename in codenames:
            try:
                perm = Permission.objects.get(
                    content_type__app_label=app_label, codename=codename
                )
                perms.append(perm)
            except Permission.DoesNotExist:
                print(f"  Warning: {app_label}.{codename} not found, skipping")
        return perms

    # ── Staff group (موظف قسم مهندسي الديكور) ──
    staff_group, _ = Group.objects.get_or_create(
        name="موظف قسم مهندسي الديكور"
    )
    staff_group.permissions.clear()

    # External sales model permissions
    staff_perms = []
    staff_perms += get_perms("external_sales", [
        "view_decoratorengineerprofile",
        "add_decoratorengineerprofile",
        "change_decoratorengineerprofile",
        "view_engineerlinkedcustomer",
        "add_engineerlinkedcustomer",
        "change_engineerlinkedcustomer",
        "view_engineerlinkedorder",
        "add_engineerlinkedorder",
        "view_engineercontactlog",
        "add_engineercontactlog",
        "change_engineercontactlog",
        "view_engineermaterialinterest",
        "add_engineermaterialinterest",
        "change_engineermaterialinterest",
    ])
    # View customers and orders (needed for linking)
    staff_perms += get_perms("customers", ["view_customer"])
    staff_perms += get_perms("orders", ["view_order"])

    for perm in staff_perms:
        staff_group.permissions.add(perm)

    print(f"  ✅ Group '{staff_group.name}' created with {len(staff_perms)} permissions")

    # ── Manager group (مدير قسم مهندسي الديكور) ──
    manager_group, _ = Group.objects.get_or_create(
        name="مدير قسم مهندسي الديكور"
    )
    manager_group.permissions.clear()

    # Manager gets all staff permissions plus commission management and deletion
    manager_perms = list(staff_perms)  # inherit staff perms
    manager_perms += get_perms("external_sales", [
        "delete_decoratorengineerprofile",
        "change_engineerlinkedorder",  # approve/manage commissions
        "delete_engineerlinkedorder",
        "delete_engineerlinkedcustomer",
        "delete_engineercontactlog",
        "delete_engineermaterialinterest",
    ])
    # Full customer and order viewing
    manager_perms += get_perms("customers", [
        "add_customer",
        "change_customer",
    ])
    manager_perms += get_perms("orders", [
        "change_order",
    ])

    # Deduplicate
    seen = set()
    unique_perms = []
    for p in manager_perms:
        if p.pk not in seen:
            seen.add(p.pk)
            unique_perms.append(p)

    for perm in unique_perms:
        manager_group.permissions.add(perm)

    print(f"  ✅ Group '{manager_group.name}' created with {len(unique_perms)} permissions")

    # ── مدير عام المبيعات الخارجية (overall external sales director) ──
    director_group, _ = Group.objects.get_or_create(
        name="مدير عام المبيعات الخارجية"
    )
    director_group.permissions.clear()

    # Director gets all manager permissions plus system-wide access
    director_perms = list(unique_perms)
    director_perms += get_perms("customers", [
        "delete_customer",
        "view_customer",
    ])
    director_perms += get_perms("orders", [
        "view_order",
        "add_order",
    ])
    director_perms += get_perms("accounting", [
        "view_transaction",
        "view_transactionline",
    ])

    seen2 = set()
    unique_director = []
    for p in director_perms:
        if p.pk not in seen2:
            seen2.add(p.pk)
            unique_director.append(p)

    for perm in unique_director:
        director_group.permissions.add(perm)

    print(f"  ✅ Group '{director_group.name}' created with {len(unique_director)} permissions")


def reverse_func(apps, schema_editor):
    # Don't delete groups on reverse to avoid data loss
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0059_user_is_decorator_dept_manager_and_more"),
        ("external_sales", "0001_initial"),
        ("customers", "0001_initial"),
        ("orders", "0001_initial"),
        ("accounting", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_external_sales_groups, reverse_func),
    ]
