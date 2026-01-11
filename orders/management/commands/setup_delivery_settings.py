from django.core.management.base import BaseCommand

from orders.models import DeliveryTimeSettings


class Command(BaseCommand):
    help = "إعداد القيم الافتراضية لإعدادات مواعيد التسليم"

    def handle(self, *args, **options):
        # القيم الافتراضية لإعدادات مواعيد التسليم
        default_settings = [
            {
                "order_type": "normal",
                "delivery_days": 15,
                "description": "الطلبات العادية - 15 يوم",
            },
            {
                "order_type": "vip",
                "delivery_days": 7,
                "description": "طلبات VIP - 7 أيام",
            },
            {
                "order_type": "inspection",
                "delivery_days": 2,
                "description": "المعاينات - 48 ساعة (يومين)",
            },
        ]

        created_count = 0
        updated_count = 0

        for setting_data in default_settings:
            order_type = setting_data["order_type"]
            delivery_days = setting_data["delivery_days"]
            description = setting_data["description"]

            # التحقق من وجود الإعداد
            setting, created = DeliveryTimeSettings.objects.get_or_create(
                order_type=order_type,
                defaults={"delivery_days": delivery_days, "is_active": True},
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✅ تم إنشاء إعداد {description}")
                )
            else:
                # تحديث الإعداد الموجود إذا كان مختلفاً
                if setting.delivery_days != delivery_days:
                    setting.delivery_days = delivery_days
                    setting.is_active = True
                    setting.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"🔄 تم تحديث إعداد {description}")
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ إعداد {description} موجود بالفعل")
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 تم إكمال إعداد مواعيد التسليم:\n"
                f"   - تم إنشاء: {created_count} إعداد\n"
                f"   - تم تحديث: {updated_count} إعداد"
            )
        )
