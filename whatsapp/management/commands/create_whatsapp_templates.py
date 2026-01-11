from django.core.management.base import BaseCommand

from whatsapp.models import WhatsAppMessageTemplate


class Command(BaseCommand):
    help = "إنشاء قوالب WhatsApp الافتراضية"

    def handle(self, *args, **options):
        templates = [
            {
                "name": "إنشاء طلب عادي",
                "message_type": "ORDER_CREATED",
                "template_text": """مرحباً {customer_name} 👋

تم إنشاء طلبك بنجاح!

📋 رقم الطلب: {order_number}
📅 التاريخ: {order_date}
💰 المبلغ الإجمالي: {total_amount} جنيه
✅ المبلغ المدفوع: {paid_amount} جنيه
⏳ المبلغ المتبقي: {remaining_amount} جنيه

شكراً لثقتك بنا 🙏""",
                "order_types": [],
            },
            {
                "name": "إنشاء طلب تركيب",
                "message_type": "ORDER_CREATED",
                "template_text": """مرحباً {customer_name} 👋

تم إنشاء طلب التركيب بنجاح!

📋 رقم الطلب: {order_number}
📅 التاريخ: {order_date}
💰 المبلغ الإجمالي: {total_amount} جنيه
✅ المبلغ المدفوع: {paid_amount} جنيه
⏳ المبلغ المتبقي: {remaining_amount} جنيه

⚠️ تنبيه مهم:
يرجى إغلاق المبلغ المتبقي قبل 72 ساعة من موعد التركيب لضمان عدم التأخير

شكراً لثقتك بنا 🙏""",
                "order_types": ["installation"],
            },
            {
                "name": "طلب مع عقد",
                "message_type": "ORDER_WITH_CONTRACT",
                "template_text": """مرحباً {customer_name} 👋

تم إنشاء طلبك بنجاح!

📋 رقم الطلب: {order_number}
📄 نوع الطلب: {order_type}

📎 نسخة من العقد الإلكتروني مرفقة

للاستفسار: {company_phone}""",
                "send_contract": True,
                "order_types": ["installation", "delivery", "accessory"],
            },
            {
                "name": "جدولة تركيب",
                "message_type": "INSTALLATION_SCHEDULED",
                "template_text": """مرحباً {customer_name} 👋

تم جدولة موعد التركيب! ✅

📋 رقم الطلب: {order_number}
📅 التاريخ: {installation_date}

👨‍🔧 الفني: {technician_name}
📞 هاتف الفني: {technician_phone}

⏰ سيتم تنسيق وقت الوصول من قبل الفني في نفس اليوم لتحديد ساعة الوصول

يرجى التأكد من تواجدكم""",
            },
            {
                "name": "اكتمال تركيب",
                "message_type": "INSTALLATION_COMPLETED",
                "template_text": """مرحباً {customer_name} 👋

تم إتمام عملية التركيب بنجاح! ✅

📋 رقم الطلب: {order_number}

نرجو تقييم الخدمة من خلال مسح الكود المرفق 📱

شكراً لثقتك بنا 🙏""",
            },
            {
                "name": "إنشاء معاينة",
                "message_type": "INSPECTION_CREATED",
                "template_text": """مرحباً {customer_name} 👋

تم إنشاء طلب المعاينة بنجاح! ✅

📋 رقم الطلب: {order_number}
📅 تاريخ الإنشاء: {created_date}

سيتم التواصل معكم قريباً لتحديد موعد المعاينة""",
                "order_types": ["inspection"],
            },
            {
                "name": "جدولة معاينة",
                "message_type": "INSPECTION_SCHEDULED",
                "template_text": """مرحباً {customer_name} 👋

تم جدولة موعد المعاينة! ✅

📋 رقم الطلب: {order_number}
📅 التاريخ: {inspection_date}

👨‍🔧 المعاين: {inspector_name}
📞 هاتف المعاين: {inspector_phone}

⏰ سيتم تنسيق وقت الوصول من قبل المعاين في نفس اليوم لتحديد ساعة الوصول

يرجى التأكد من تواجدكم""",
            },
            {
                "name": "فاتورة",
                "message_type": "ORDER_WITH_INVOICE",
                "template_text": """مرحباً {customer_name} 👋

📋 رقم الطلب: {order_number}
💰 المبلغ الإجمالي: {total_amount} جنيه
✅ المبلغ المدفوع: {paid_amount} جنيه
⏳ المبلغ المتبقي: {remaining_amount} جنيه

📎 نسخة من الفاتورة مرفقة

شكراً لتعاملكم معنا 🙏""",
                "send_invoice": True,
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = WhatsAppMessageTemplate.objects.update_or_create(
                name=template_data["name"],
                message_type=template_data["message_type"],
                defaults={
                    "template_text": template_data["template_text"],
                    "send_contract": template_data.get("send_contract", False),
                    "send_invoice": template_data.get("send_invoice", False),
                    "order_types": template_data.get("order_types", []),
                    "is_active": True,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ تم إنشاء القالب: {template.name}")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"⟳ تم تحديث القالب: {template.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ اكتمل! تم إنشاء {created_count} قالب وتحديث {updated_count} قالب"
            )
        )
