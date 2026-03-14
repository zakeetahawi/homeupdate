"""
python manage.py link_engineer_orders

يربط طلبات المهندسين بملفاتهم تلقائياً بناءً على عميل الطلب.
يُستخدم لمعالجة الطلبات القديمة التي أُنشئت قبل إضافة الربط التلقائي.
"""
from django.core.management.base import BaseCommand

from external_sales.models import DecoratorEngineerProfile, EngineerLinkedOrder
from external_sales.signals import _auto_link_order_to_engineer


class Command(BaseCommand):
    help = "ربط طلبات المهندسين تلقائياً بملفاتهم (للطلبات القديمة)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="عرض ما سيتم ربطه بدون تنفيذ فعلي",
        )
        parser.add_argument(
            "--engineer",
            type=int,
            default=None,
            help="معرّف ملف مهندس محدد (اختياري)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        engineer_pk = options["engineer"]

        profiles_qs = DecoratorEngineerProfile.objects.select_related(
            "customer"
        ).filter(customer__isnull=False)

        if engineer_pk:
            profiles_qs = profiles_qs.filter(pk=engineer_pk)

        linked = 0
        skipped = 0

        for profile in profiles_qs:
            from orders.models import Order

            orders = Order.objects.filter(
                customer=profile.customer
            ).exclude(
                engineer_link__isnull=False  # already linked
            )

            for order in orders:
                if dry_run:
                    self.stdout.write(
                        f"  [dry-run] سيُربط: {order.order_number} → {profile.designer_code}"
                    )
                    linked += 1
                else:
                    _auto_link_order_to_engineer(order)
                    # check it was actually created
                    if EngineerLinkedOrder.objects.filter(order=order).exists():
                        linked += 1
                    else:
                        skipped += 1

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}تم: ربط {linked} طلب" + (f" | تخطي {skipped}" if skipped else "")
            )
        )
