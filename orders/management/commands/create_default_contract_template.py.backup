"""
أمر لإنشاء قالب عقد افتراضي
"""
from django.core.management.base import BaseCommand
from orders.contract_models import ContractTemplate


class Command(BaseCommand):
    help = 'إنشاء قالب عقد افتراضي'

    def handle(self, *args, **options):
        # التحقق من وجود قالب افتراضي
        if ContractTemplate.objects.filter(is_default=True).exists():
            self.stdout.write(self.style.WARNING('يوجد قالب افتراضي بالفعل'))
            return
        
        # إنشاء قالب افتراضي
        template = ContractTemplate.objects.create(
            name='قالب العقد الافتراضي',
            template_type='standard',
            is_active=True,
            is_default=True,
            company_name='شركة الستائر والديكور',
            company_address='المملكة العربية السعودية',
            company_phone='0500000000',
            company_email='info@company.com',
            company_tax_number='123456789',
            company_commercial_register='987654321',
            primary_color='#2C3E50',
            secondary_color='#34495E',
            accent_color='#E74C3C',
            font_family='Arial, sans-serif',
            font_size=12,
            page_size='A4',
            page_margins=15,
            show_company_logo=True,
            show_order_details=True,
            show_customer_details=True,
            show_items_table=True,
            show_payment_details=True,
            show_terms=True,
            show_signatures=True,
            header_text='عقد تفصيل ستائر',
            footer_text='شكراً لتعاملكم معنا',
            terms_text='''
الشروط والأحكام:

1. يتم التسليم خلال المدة المتفق عليها
2. يجب دفع 50% من قيمة العقد عند التوقيع
3. يتم دفع المبلغ المتبقي عند التسليم
4. الشركة غير مسؤولة عن أي تأخير بسبب ظروف خارجة عن إرادتها
5. يحق للعميل طلب تعديلات بسيطة خلال 7 أيام من التسليم
6. الضمان ساري لمدة سنة من تاريخ التسليم
7. يجب على العميل فحص المنتج عند التسليم والإبلاغ عن أي عيوب فوراً
            '''.strip()
        )
        
        self.stdout.write(self.style.SUCCESS(f'تم إنشاء القالب الافتراضي: {template.name}'))

