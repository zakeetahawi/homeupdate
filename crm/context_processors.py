"""
Context processors لإضافة بيانات إضافية للقوالب
"""

def admin_stats(request):
    """إضافة إحصائيات للوحة التحكم"""
    
    # التحقق من أن المستخدم في لوحة التحكم
    if not request.path.startswith('/admin/'):
        return {}
    
    try:
        # استيراد النماذج
        from customers.models import Customer
        from orders.models import Order
        from inspections.models import Inspection
        from manufacturing.models import ManufacturingOrder
        from accounts.models import CompanyInfo
        
        # حساب الإحصائيات
        stats = {
            'customers_count': Customer.objects.count(),
            'orders_count': Order.objects.count(),
            'pending_inspections': Inspection.objects.filter(status='pending').count(),
            'active_manufacturing': ManufacturingOrder.objects.filter(status='in_progress').count(),
        }
        
        # إضافة معلومات الشركة
        try:
            company_info = CompanyInfo.objects.first()
            stats['company_info'] = company_info
        except:
            stats['company_info'] = None
            
        return stats
        
    except Exception as e:
        # في حالة وجود خطأ، إرجاع قيم افتراضية
        return {
            'customers_count': 0,
            'orders_count': 0,
            'pending_inspections': 0,
            'active_manufacturing': 0,
            'company_info': None,
        }


def jazzmin_extras(request):
    """إضافات إضافية لـ Jazzmin"""
    
    if not request.path.startswith('/admin/'):
        return {}
    
    return {
        'jazzmin_version': '2.6.0',
        'custom_dashboard': True,
        'show_quick_actions': True,
        'rtl_support': True,
    }
