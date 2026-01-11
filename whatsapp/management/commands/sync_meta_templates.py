"""
أمر إداري لمزامنة header_handles من Meta
يجلب روابط الصور من Meta ويحدثها في قاعدة البيانات
"""

import requests
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "مزامنة header_handles و variable_names من Meta"

    def handle(self, *args, **options):
        from whatsapp.models import WhatsAppMessageTemplate, WhatsAppSettings

        settings = WhatsAppSettings.objects.first()
        if not settings:
            self.stderr.write("❌ لم يتم العثور على إعدادات WhatsApp")
            return

        business_id = settings.business_account_id
        token = settings.access_token

        # جلب جميع القوالب من Meta
        url = f"https://graph.facebook.com/v18.0/{business_id}/message_templates"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"limit": 100}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            self.stderr.write(f"❌ خطأ في الاتصال بـ Meta: {e}")
            return

        templates_data = data.get("data", [])
        self.stdout.write(f"📥 تم جلب {len(templates_data)} قالب من Meta")

        for template_data in templates_data:
            meta_name = template_data.get("name")
            status = template_data.get("status")

            # البحث عن القالب في قاعدة البيانات
            db_template = WhatsAppMessageTemplate.objects.filter(
                meta_template_name=meta_name
            ).first()

            if not db_template:
                self.stdout.write(f"⚠️  {meta_name}: غير موجود في قاعدة البيانات")
                continue

            updated = False

            # معالجة المكونات
            for comp in template_data.get("components", []):
                # تحديث header_handle
                if comp.get("type") == "HEADER":
                    if comp.get("format") == "IMAGE":
                        db_template.header_type = "IMAGE"
                        example = comp.get("example", {})
                        header_handles = example.get("header_handle", [])
                        if header_handles:
                            db_template.header_media_url = header_handles[0]
                            updated = True
                    elif comp.get("format") == "TEXT":
                        db_template.header_type = "TEXT"
                    else:
                        db_template.header_type = "NONE"

                # تحديث variable_names
                if comp.get("type") == "BODY":
                    example = comp.get("example", {})
                    named_params = example.get("body_text_named_params", [])
                    if named_params:
                        var_names = [p.get("param_name") for p in named_params]
                        if var_names != db_template.variable_names:
                            db_template.variable_names = var_names
                            updated = True

                # تحديث footer
                if comp.get("type") == "FOOTER":
                    footer_text = comp.get("text", "")
                    if footer_text and footer_text != db_template.footer:
                        db_template.footer = footer_text[:60]
                        updated = True

            if updated:
                db_template.save()
                self.stdout.write(self.style.SUCCESS(f"✅ {meta_name}: تم التحديث"))
            else:
                self.stdout.write(f"✓ {meta_name}: لا تغييرات")

        self.stdout.write(self.style.SUCCESS("\n🎉 تمت المزامنة بنجاح!"))
