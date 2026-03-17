"""
أمر إدارة لإعداد/استعادة قالب الفاتورة الافتراضي.

الاستخدام:
    python manage.py setup_invoice_template          # إنشاء إذا لم يوجد
    python manage.py setup_invoice_template --force   # إعادة تعيين حتى لو موجود
    python manage.py setup_invoice_template --restore  # استعادة html_content فقط
"""

import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "إعداد أو استعادة قالب الفاتورة الافتراضي من الملف المرجعي"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="إعادة تعيين القالب بالكامل حتى لو كان موجوداً",
        )
        parser.add_argument(
            "--restore",
            action="store_true",
            help="استعادة محتوى HTML فقط (دون تغيير الإعدادات الأخرى)",
        )

    def handle(self, *args, **options):
        from accounts.models import CompanyInfo

        from orders.invoice_models import InvoiceTemplate

        force = options["force"]
        restore_only = options["restore"]

        # قراءة محتوى HTML من الملف المرجعي
        template_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "templates",
            "orders",
            "default_invoice_grapes.html",
        )

        if not os.path.exists(template_file):
            self.stderr.write(
                self.style.ERROR(f"ملف القالب المرجعي غير موجود: {template_file}")
            )
            return

        with open(template_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        self.stdout.write(f"تم قراءة القالب المرجعي ({len(html_content)} حرف)")

        # الإعدادات المتقدمة الافتراضية
        default_advanced_settings = {
            "th_qty": "الكمية",
            "th_desc": "الوصف",
            "th_price": "السعر",
            "th_total": "المجموع",
            "logo_size": "120",
            "label_date": "التاريخ",
            "notes_text": "<p>في حال وجود ملاحظات او استفسارت الرجاء التواصل على الخط الساخن او هاتف الفرع </p>",
            "show_table": True,
            "terms_text": "<p>ممنوع التعامل مالياً الا من خلال محاسب الفرع نقداً او التحويل على حسابات الشركة </p>"
            "<p>يتم سداد باقي المبلغ قبل موعد التركيب ب48 ساعه </p>"
            "<p>في حالة اي تعديل او تغيير في اي بند يجب ان يكون في نفس يوم التعاقد </p>"
            "<p>في حالة الغاء الاوردر يتم خصم مبلغ 30%</p>",
            "footer_note": "<p>شكراً لثقتكم بنا</p>",
            "show_footer": True,
            "show_totals": True,
            "th_discount": "نسبة الخصم",
            "show_company": False,
            "invoice_title": "بيان",
            "show_customer": True,
            "hotline_number": "19148",
            "note_icon_size": "16px",
            "template_style": "pro",
            "bg_logo_opacity": "6",
            "note_icon_color": "#6c757d",
            "note_text_color": "#495057",
            "phone_icon_size": "18px",
            "show_order_info": True,
            "phone_icon_color": "#19c842",
            "phone_text_color": "#0d6efd",
            "show_logo_header": True,
            "label_invoice_number": "رقم البيان",
            "show_background_logo": True,
            "label_company_section": "بيانات الشركة",
            "label_customer_section": "بيانات العميل",
        }

        # البحث عن القالب الموجود
        template = InvoiceTemplate.objects.filter(is_default=True).first()
        if not template:
            template = InvoiceTemplate.objects.first()

        if template and restore_only:
            # استعادة محتوى HTML فقط
            template.html_content = html_content
            template.advanced_settings = default_advanced_settings
            template.is_default = True
            template.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'تم استعادة محتوى HTML للقالب "{template.name}" ({len(html_content)} حرف)'
                )
            )
            return

        if template and not force:
            # القالب موجود ولم يُطلب الإجبار
            has_content = template.html_content and len(template.html_content.strip()) > 50
            if has_content:
                self.stdout.write(
                    self.style.WARNING(
                        f'القالب "{template.name}" موجود بالفعل ويحتوي على محتوى ({len(template.html_content)} حرف). '
                        "استخدم --force لإعادة التعيين أو --restore لاستعادة HTML فقط."
                    )
                )
                return
            else:
                # القالب موجود لكن بدون محتوى HTML - نستعيد المحتوى
                self.stdout.write(
                    self.style.WARNING(
                        f'القالب "{template.name}" موجود لكن بدون محتوى HTML. جاري الاستعادة...'
                    )
                )
                template.html_content = html_content
                template.advanced_settings = default_advanced_settings
                template.is_default = True
                template.save()
                self.stdout.write(
                    self.style.SUCCESS("تم استعادة محتوى HTML بنجاح!")
                )
                return

        # الحصول على بيانات الشركة
        company_info = CompanyInfo.objects.first()

        if template and force:
            # إعادة تعيين القالب الموجود
            template.html_content = html_content
            template.advanced_settings = default_advanced_settings
            template.is_default = True
            template.company_name = "Elkhawaga"
            template.company_phone = "www.elkhawaga.com"
            template.company_email = "info@elkhawaga.com"
            template.company_website = "http://www.elkhawaga.com"
            template.primary_color = "#9d5c01"
            template.secondary_color = "#198754"
            template.accent_color = "#284de2"
            template.font_family = "Cairo, Arial, sans-serif"
            template.font_size = 14
            template.terms_text = "شكراً لتعاملكم معنا."
            if company_info and company_info.logo:
                template.company_logo = company_info.logo
            template.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'تم إعادة تعيين القالب "{template.name}" بالكامل!'
                )
            )
        else:
            # إنشاء قالب جديد
            template = InvoiceTemplate.objects.create(
                name="قالب مخصص",
                template_type="custom",
                is_default=True,
                is_active=True,
                company_name="Elkhawaga",
                company_address="",
                company_phone="www.elkhawaga.com",
                company_email="info@elkhawaga.com",
                company_website="http://www.elkhawaga.com",
                primary_color="#9d5c01",
                secondary_color="#198754",
                accent_color="#284de2",
                font_family="Cairo, Arial, sans-serif",
                font_size=14,
                page_size="A4",
                page_margins=20,
                html_content=html_content,
                advanced_settings=default_advanced_settings,
                terms_text="شكراً لتعاملكم معنا.",
                company_logo=company_info.logo if company_info and company_info.logo else "",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'تم إنشاء القالب الافتراضي "{template.name}" (ID={template.id})'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"محتوى HTML: {len(template.html_content)} حرف")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"الإعدادات المتقدمة: {len(template.advanced_settings)} عنصر"
            )
        )
