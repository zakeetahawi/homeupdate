from django.core.management.base import BaseCommand

from whatsapp.models import WhatsAppMessageTemplate, WhatsAppNotificationRule


class Command(BaseCommand):
    help = "إنشاء قواعد الإشعارات الافتراضية"

    def handle(self, *args, **options):
        rules_data = [
            {
                "event_type": "ORDER_CREATED",
                "template_name": "إنشاء طلب عادي",
                "is_enabled": True,
                "delay_minutes": 0,
            },
            {
                "event_type": "INSTALLATION_SCHEDULED",
                "template_name": "جدولة تركيب",
                "is_enabled": True,
                "delay_minutes": 0,
            },
            {
                "event_type": "INSTALLATION_COMPLETED",
                "template_name": "اكتمال تركيب",
                "is_enabled": True,
                "delay_minutes": 0,
            },
            {
                "event_type": "INSPECTION_CREATED",
                "template_name": "إنشاء معاينة",
                "is_enabled": True,
                "delay_minutes": 0,
            },
            {
                "event_type": "INSPECTION_SCHEDULED",
                "template_name": "جدولة معاينة",
                "is_enabled": True,
                "delay_minutes": 0,
            },
        ]

        created_count = 0
        updated_count = 0

        for rule_data in rules_data:
            # الحصول على القالب
            template = WhatsAppMessageTemplate.objects.filter(
                name=rule_data["template_name"]
            ).first()

            if not template:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ القالب غير موجود: {rule_data["template_name"]}'
                    )
                )
                continue

            # إنشاء أو تحديث القاعدة
            rule, created = WhatsAppNotificationRule.objects.update_or_create(
                event_type=rule_data["event_type"],
                defaults={
                    "template": template,
                    "is_enabled": rule_data["is_enabled"],
                    "delay_minutes": rule_data["delay_minutes"],
                },
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ تم إنشاء القاعدة: {rule.get_event_type_display()}"
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"⟳ تم تحديث القاعدة: {rule.get_event_type_display()}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ اكتمل! تم إنشاء {created_count} قاعدة وتحديث {updated_count} قاعدة"
            )
        )
