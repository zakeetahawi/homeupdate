#!/usr/bin/env python
"""
سكريبت لإنشاء قالب العقد الافتراضي
Create default contract template
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/zakee/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_system.settings')
django.setup()

from orders.contract_models import ContractTemplate
from django.contrib.auth import get_user_model

User = get_user_model()

def create_default_template():
    """إنشاء القالب الافتراضي"""
    
    # التحقق من عدم وجود قالب افتراضي
    existing_template = ContractTemplate.objects.filter(is_default=True).first()
    
    if existing_template:
        print(f"✓ يوجد قالب افتراضي بالفعل: {existing_template.name}")
        return existing_template
    
    # إنشاء القالب الافتراضي
    template = ContractTemplate.objects.create(
        name='قالب العقد الافتراضي',
        template_type='standard',
        is_active=True,
        is_default=True,
        
        # إعدادات الشركة
        company_name='شركة الديكور المتقدم',
        company_address='المملكة العربية السعودية',
        company_phone='+966 XX XXX XXXX',
        company_email='info@company.com',
        company_website='www.company.com',
        company_tax_number='',
        company_commercial_register='',
        
        # الألوان
        primary_color='#a67c52',
        secondary_color='#8b6f47',
        accent_color='#d4af37',
        
        # الخطوط
        font_family='Cairo, Arial, sans-serif',
        font_size=13,
        
        # إعدادات الصفحة
        page_size='A4',
        page_margins=15,
        
        # النصوص
        header_text='عقد تفصيل وتركيب ستائر',
        footer_text='شكراً لثقتكم بنا',
        terms_text="""الشروط والأحكام:
1. يتم التسليم خلال المدة المتفق عليها
2. الدفعة المقدمة غير قابلة للاسترجاع
3. يجب فحص المنتج عند الاستلام
4. الضمان حسب الاتفاق""",
        
        # إعدادات العرض
        show_company_logo=True,
        show_order_details=True,
        show_customer_details=True,
        show_items_table=True,
        show_payment_details=True,
        show_terms=True,
        show_signatures=True,
    )
    
    print(f"✓ تم إنشاء القالب الافتراضي بنجاح: {template.name}")
    print(f"  - معرف القالب: {template.id}")
    print(f"  - نشط: {template.is_active}")
    print(f"  - افتراضي: {template.is_default}")
    
    return template


if __name__ == '__main__':
    print("=" * 60)
    print("إنشاء قالب العقد الافتراضي")
    print("=" * 60)
    print()
    
    try:
        template = create_default_template()
        
        print()
        print("=" * 60)
        print("✓ تمت العملية بنجاح!")
        print("=" * 60)
        
        # عرض ملخص
        print("\nملخص القوالب المتاحة:")
        all_templates = ContractTemplate.objects.all()
        print(f"إجمالي القوالب: {all_templates.count()}")
        
        for t in all_templates:
            status = "✓ افتراضي" if t.is_default else ""
            active = "نشط" if t.is_active else "غير نشط"
            print(f"  - {t.name} ({active}) {status}")
        
    except Exception as e:
        print(f"\n✗ حدث خطأ: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
