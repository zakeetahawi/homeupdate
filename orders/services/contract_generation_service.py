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
        
        # حساب عدد أيام التشغيل
        working_days = None
        if self.order.expected_delivery_date and self.order.created_at:
            # تحويل created_at إلى date للمقارنة الصحيحة
            created_date = self.order.created_at.date() if hasattr(self.order.created_at, 'date') else self.order.created_at
            delivery_date = self.order.expected_delivery_date
            # التأكد من أن كلاهما date objects
            if hasattr(delivery_date, 'date'):
                delivery_date = delivery_date.date()
            delta = delivery_date - created_date
            working_days = delta.days
        
        # حساب إجمالي الأمتار من جميع الأقمشة
        total_meters = 0
        for curtain in curtains:
            for fabric in curtain.fabrics.all():
                total_meters += float(fabric.meters) if fabric.meters else 0
        
        # تجهيز البيانات للقالب
        context = {
            'order': self.order,
            'customer': self.order.customer,
            'curtains': curtains,
            'template': self.template,
            'settings': self.template,  # إضافة settings للوصول إلى بيانات الشركة
            'working_days': working_days,  # إضافة عدد أيام التشغيل
            'total_meters': total_meters,  # إجمالي الأمتار
            'MEDIA_URL': settings.MEDIA_URL,  # إضافة MEDIA_URL
            'MEDIA_ROOT': settings.MEDIA_ROOT,  # إضافة MEDIA_ROOT
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
        توليد ملف PDF للعقد - محسّن للأداء
        
        Returns:
            BytesIO: ملف PDF
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # توليد HTML
            html_content = self.generate_html()
            
            # إعداد الخطوط - محسّن
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
            
            # توليد PDF مع تحسينات الأداء
            pdf_file = BytesIO()
            
            # استخدام base_url بشكل صحيح
            base_url = settings.MEDIA_ROOT if hasattr(settings, 'MEDIA_ROOT') else None
            
            HTML(string=html_content, base_url=base_url).write_pdf(
                pdf_file,
                stylesheets=[CSS(string=full_css, font_config=font_config)],
                font_config=font_config,
                # تحسينات الأداء
                optimize_images=True,  # تحسين الصور
            )
            
            pdf_file.seek(0)
            file_size = len(pdf_file.getvalue())
            logger.info(f"✅ PDF generated successfully - Size: {file_size / 1024:.2f} KB")
            
            return pdf_file
            
        except Exception as e:
            logger.error(f"❌ Error generating PDF: {str(e)}", exc_info=True)
            raise
    
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
            
            # التحقق من حجم الملف (الذهاب لنهاية الملف للحصول على الحجم)
            pdf_file.seek(0, 2)  # الذهاب لنهاية الملف
            file_size = pdf_file.tell()
            pdf_file.seek(0)  # العودة للبداية
            
            if not pdf_file or file_size == 0:
                import logging
                logger = logging.getLogger(__name__)
                logger.error("فشل توليد PDF - الملف فارغ")
                return False
            
            # تجهيز اسم العميل للملف (إزالة المسافات والأحرف الخاصة)
            customer_name = ''
            if self.order.customer:
                # تنظيف اسم العميل: إزالة المسافات والأحرف الخاصة
                customer_name = self.order.customer.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                # الحد من طول اسم العميل
                if len(customer_name) > 30:
                    customer_name = customer_name[:30]
            
            # إضافة timestamp لتجنب مشاكل cache المتصفح
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # اسم الملف مع timestamp لضمان اسم فريد في كل مرة
            if customer_name:
                filename = f'contract_{self.order.order_number}_{customer_name}_{timestamp}.pdf'
            else:
                # في حالة عدم وجود عميل، استخدم رقم الطلب مع timestamp
                filename = f'contract_{self.order.order_number}_{timestamp}.pdf'
            
            # المسار الكامل للملف
            full_path = os.path.join(settings.MEDIA_ROOT, 'contracts', filename)
            
            # إنشاء المجلد إذا لم يكن موجوداً
            contract_dir = os.path.join(settings.MEDIA_ROOT, 'contracts')
            os.makedirs(contract_dir, exist_ok=True)
            
            # حذف جميع الملفات القديمة لنفس الطلب (تنظيف)
            if os.path.exists(contract_dir):
                prefix = f'contract_{self.order.order_number}_'
                deleted_count = 0
                for old_file in os.listdir(contract_dir):
                    if old_file.startswith(prefix) and old_file.endswith('.pdf'):
                        try:
                            old_file_path = os.path.join(contract_dir, old_file)
                            if os.path.isfile(old_file_path):
                                os.remove(old_file_path)
                                deleted_count += 1
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"فشل حذف الملف القديم {old_file}: {e}")
                
                if deleted_count > 0:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"🗑️ تم حذف {deleted_count} ملف قديم للطلب {self.order.order_number}")

            # حفظ الملف في الطلب
            pdf_file.seek(0)  # التأكد من أن المؤشر في بداية الملف
            self.order.contract_file.save(
                filename,
                ContentFile(pdf_file.read()),
                save=True
            )
            
            # التحقق من أن الملف تم حفظه بنجاح
            if not self.order.contract_file or not os.path.exists(self.order.contract_file.path):
                import logging
                logger = logging.getLogger(__name__)
                logger.error("فشل حفظ ملف العقد - الملف غير موجود بعد الحفظ")
                return False

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
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'خطأ في حفظ العقد: {str(e)}', exc_info=True)
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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"📝 بدء توليد العقد للطلب #{order_id}")
        
        try:
            order = Order.objects.get(id=order_id)
            logger.info(f"✅ تم العثور على الطلب {order.order_number}")
            template = None

            if template_id:
                template = ContractTemplate.objects.get(id=template_id)

            service = ContractGenerationService(order, template)
            return service.save_contract_to_order(user)

        except Order.DoesNotExist:
            logger.error(f'❌ الطلب {order_id} غير موجود')
            return False
        except ContractTemplate.DoesNotExist:
            logger.error(f'❌ القالب {template_id} غير موجود')
            return False
        except Exception as e:
            logger.error(f'❌ خطأ في توليد العقد للطلب {order_id}: {str(e)}', exc_info=True)
            return False

