#!/usr/bin/env python
"""
سكريبت لاختبار توليد العقود
"""
import os
import django
import logging

# تهيئة Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order
from orders.services.contract_generation_service import ContractGenerationService
from orders.contract_models import ContractTemplate

# إعداد logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_contract_generation():
    """اختبار توليد العقد لآخر طلب"""
    
    # الحصول على آخر طلب
    order = Order.objects.filter(
        selected_types__contains=['installation']
    ).order_by('-created_at').first()
    
    if not order:
        print("❌ لا توجد طلبات من نوع installation")
        return
    
    print(f"\n{'='*60}")
    print(f"📋 اختبار توليد العقد للطلب: {order.order_number}")
    print(f"{'='*60}")
    
    print(f"\n📊 معلومات الطلب:")
    print(f"  - رقم الطلب: {order.order_number}")
    print(f"  - العميل: {order.customer.name if order.customer else 'غير محدد'}")
    print(f"  - الأنواع: {order.selected_types}")
    print(f"  - ملف العقد الحالي: {order.contract_file.name if order.contract_file else 'لا يوجد'}")
    
    # التحقق من القالب
    template = ContractTemplate.get_default_template()
    if not template:
        print("\n❌ لا يوجد قالب عقد افتراضي!")
        return
    
    print(f"\n✅ القالب الافتراضي: {template.name}")
    
    # محاولة توليد العقد
    print(f"\n🔄 محاولة توليد العقد...")
    try:
        service = ContractGenerationService(order, template)
        result = service.save_contract_to_order()
        
        if result:
            print(f"\n✅ تم توليد العقد بنجاح!")
            print(f"  - مسار الملف: {order.contract_file.name if order.contract_file else 'لم يتم الحفظ'}")
        else:
            print(f"\n❌ فشل في توليد العقد!")
            
    except Exception as e:
        print(f"\n❌ خطأ في توليد العقد:")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_contract_generation()
