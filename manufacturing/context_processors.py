from django.urls import reverse

def manufacturing_nav_links(request):
    """
    إضافة روابط شريط التنقل الخاصة بالمصنع إلى سياق القالب
    """
    if not request.user.is_authenticated:
        return {}
    
    # التحقق من الصلاحيات
    has_manufacturing_permission = request.user.has_perm('manufacturing.view_manufacturingorder')
    
    if not has_manufacturing_permission:
        return {}
    
    # تحديد الروابط النشطة
    active_links = {
        'dashboard': request.path == reverse('manufacturing:dashboard'),
        'order_list': request.path == reverse('manufacturing:order_list'),
        'reports': '/reports/' in request.path,
    }
    
    return {
        'manufacturing_nav_links': [
            {
                'name': 'لوحة التحكم',
                'url': reverse('manufacturing:dashboard'),
                'is_active': active_links['dashboard'],
                'icon': 'fas fa-tachometer-alt',
            },
            {
                'name': 'أوامر التصنيع',
                'url': reverse('manufacturing:order_list'),
                'is_active': active_links['order_list'],
                'icon': 'fas fa-industry',
            },
            {
                'name': 'التقارير',
                'url': reverse('manufacturing:reports'),
                'is_active': active_links['reports'],
                'icon': 'fas fa-chart-bar',
            },
        ]
    }
