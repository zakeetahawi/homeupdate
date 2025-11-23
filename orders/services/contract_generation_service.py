"""
خدمة توليد ملفات PDF للعقود
"""
import os
from io import BytesIO
from django.conf import settings
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

from ..models import Order
from ..contract_models import ContractTemplate, ContractCurtain, ContractPrintLog


class ContractGenerationService:
    """خدمة توليد العقود"""
    
    def __init__(self, order, template=None):
        """
        تهيئة الخدمة
        
        Args:
            order: الطلب المراد إنشاء عقد له
            template: قالب العقد (اختياري، سيتم استخدام القالب الافتراضي إذا لم يُحدد)
        """
        self.order = order
        self.template = template or ContractTemplate.get_default_template()
        
        if not self.template:
            raise ValueError('لا يوجد قالب عقد متاح')
    
    def generate_html(self):
        """توليد HTML للعقد"""
        # الحصول على ستائر العقد
        curtains = ContractCurtain.objects.filter(order=self.order).order_by('sequence')
        
        # الحصول على إعدادات النظام للعملة
        from accounts.models import SystemSettings
        system_settings = SystemSettings.get_settings()
        
        # حساب عدد أيام التشغيل
        working_days = None
        if self.order.expected_delivery_date and self.order.created_at:
            delta = self.order.expected_delivery_date - self.order.created_at.date()
            working_days = delta.days
        
        # تجهيز البيانات للقالب
        context = {
            'order': self.order,
            'customer': self.order.customer,
            'curtains': curtains,
            'template': self.template,
            'settings': system_settings,  # إضافة إعدادات النظام
            'working_days': working_days,  # إضافة عدد أيام التشغيل
            'company_name': self.template.company_name,
            'company_logo': self.template.company_logo,
            'company_address': self.template.company_address,
            'company_phone': self.template.company_phone,
            'company_email': self.template.company_email,
            'company_website': self.template.company_website,
            'company_tax_number': self.template.company_tax_number,
            'company_commercial_register': self.template.company_commercial_register,
            'primary_color': self.template.primary_color,
            'secondary_color': self.template.secondary_color,
            'accent_color': self.template.accent_color,
            'font_family': self.template.font_family,
            'font_size': self.template.font_size,
            'header_text': self.template.header_text,
            'footer_text': self.template.footer_text,
            'terms_text': self.template.terms_text,
        }
        
        # استخدام القالب الجديد
        html_content = render_to_string('orders/contract_template.html', context)
        
        return html_content
    
    def generate_pdf(self):
        """
        توليد ملف PDF للعقد
        
        Returns:
            BytesIO: ملف PDF
        """
        # توليد HTML
        html_content = self.generate_html()
        
        # إعداد الخطوط
        font_config = FontConfiguration()
        
        # CSS إضافي من القالب
        css_content = self.template.css_styles if self.template.css_styles else ''
        
        # CSS أساسي للعقد - مناسب لصفحة عمودية
        base_css = """
        @page {
            size: A4 portrait;
            margin: 1.5cm;
        }
        body {
            font-family: 'Arial', 'Segoe UI', Tahoma, sans-serif;
            font-size: 9px;
            direction: rtl;
            text-align: right;
            color: #000;
        }
        """
        
        # دمج CSS - CSS الإضافي من القالب فقط إذا كان موجوداً
        if css_content:
            full_css = base_css + '\n' + css_content
        else:
            full_css = base_css
        
        # توليد PDF
        pdf_file = BytesIO()
        HTML(string=html_content, base_url=settings.MEDIA_URL).write_pdf(
            pdf_file,
            stylesheets=[CSS(string=full_css, font_config=font_config)],
            font_config=font_config
        )
        
        pdf_file.seek(0)
        return pdf_file
    
    def save_contract_to_order(self, user=None):
        """
        حفظ العقد في الطلب
        
        Args:
            user: المستخدم الذي قام بإنشاء العقد
        
        Returns:
            bool: True إذا تم الحفظ بنجاح
        """
        try:
            # توليد PDF
            pdf_file = self.generate_pdf()
            
            # اسم الملف
            filename = f'contract_{self.order.order_number}_{self.order.contract_number}.pdf'

            # حفظ الملف في الطلب
            self.order.contract_file.save(
                filename,
                ContentFile(pdf_file.read()),
                save=True
            )

            # تسجيل عملية الإنشاء
            ContractPrintLog.objects.create(
                order=self.order,
                template=self.template,
                printed_by=user,
                print_type='auto'
            )

            # تحديث عداد استخدام القالب
            self.template.increment_usage()

            return True

        except Exception as e:
            print(f'خطأ في حفظ العقد: {str(e)}')
            return False

    @staticmethod
    def generate_contract_for_order(order_id, template_id=None, user=None):
        """
        توليد عقد لطلب معين

        Args:
            order_id: معرف الطلب
            template_id: معرف القالب (اختياري)
            user: المستخدم

        Returns:
            bool: True إذا تم التوليد بنجاح
        """
        try:
            order = Order.objects.get(id=order_id)
            template = None

            if template_id:
                template = ContractTemplate.objects.get(id=template_id)

            service = ContractGenerationService(order, template)
            return service.save_contract_to_order(user)

        except Order.DoesNotExist:
            print(f'الطلب {order_id} غير موجود')
            return False
        except ContractTemplate.DoesNotExist:
            print(f'القالب {template_id} غير موجود')
            return False
        except Exception as e:
            print(f'خطأ في توليد العقد: {str(e)}')
            return False

