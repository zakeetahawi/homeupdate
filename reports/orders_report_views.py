"""
تقارير الطلبات - عرض تفصيلي للطلبات التقليدية وطلبات الويزارد
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from orders.models import Order, DraftOrder


@login_required
def orders_report_view(request):
    """
    صفحة تقرير الطلبات الشامل
    - عرض بطاقات إحصائية للطلبات التقليدية وطلبات الويزارد
    - جداول تفصيلية قابلة للفلترة
    - فلاتر: اليوم، الأسبوع، الشهر، تاريخ مخصص
    """
    
    # الحصول على الفلاتر من الطلب
    filter_type = request.GET.get('filter', 'today')  # today, week, month, custom, all
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    branch_id = request.GET.get('branch')
    salesperson_id = request.GET.get('salesperson')
    order_type = request.GET.get('order_type')  # wizard or traditional
    
    # تحديد نطاق التاريخ
    today = timezone.now().date()
    
    if filter_type == 'today':
        date_filter = Q(created_at__date=today)
    elif filter_type == 'week':
        week_start = today - timedelta(days=today.weekday())
        date_filter = Q(created_at__date__gte=week_start)
    elif filter_type == 'month':
        month_start = today.replace(day=1)
        date_filter = Q(created_at__date__gte=month_start)
    elif filter_type == 'custom' and start_date and end_date:
        date_filter = Q(
            created_at__date__gte=datetime.strptime(start_date, '%Y-%m-%d').date(),
            created_at__date__lte=datetime.strptime(end_date, '%Y-%m-%d').date()
        )
    else:  # all
        date_filter = Q()
    
    # === الطلبات التقليدية (Traditional Orders) ===
    traditional_orders = Order.objects.filter(date_filter).exclude(
        source_draft__isnull=False  # استبعاد الطلبات المرتبطة بـ wizard
    ).select_related(
        'customer', 'salesperson', 'branch', 'created_by'
    ).order_by('-created_at')
    
    # فلترة إضافية للطلبات التقليدية
    if branch_id:
        traditional_orders = traditional_orders.filter(branch_id=branch_id)
    if salesperson_id:
        traditional_orders = traditional_orders.filter(salesperson_id=salesperson_id)
    
    # === طلبات الويزارد (Wizard Orders) ===
    wizard_orders = DraftOrder.objects.filter(
        date_filter,
        is_completed=True  # فقط الطلبات المكتملة
    ).select_related(
        'customer', 'salesperson', 'branch', 'created_by', 'final_order'
    ).order_by('-created_at')
    
    # فلترة إضافية لطلبات الويزارد
    if branch_id:
        wizard_orders = wizard_orders.filter(branch_id=branch_id)
    if salesperson_id:
        wizard_orders = wizard_orders.filter(salesperson_id=salesperson_id)
    
    # تطبيق فلتر نوع الطلب
    if order_type == 'traditional':
        wizard_orders = wizard_orders.none()
    elif order_type == 'wizard':
        traditional_orders = traditional_orders.none()
    
    # === الإحصائيات ===
    traditional_count = traditional_orders.count()
    wizard_count = wizard_orders.count()
    
    # === أكثر البائعين نشاطاً ===
    # أكثر البائعين في الطلبات التقليدية
    top_traditional_salespersons = (
        traditional_orders
        .values('salesperson__id', 'salesperson__name')
        .annotate(order_count=Count('id'))
        .filter(salesperson__isnull=False)
        .order_by('-order_count')[:5]
    )
    
    # أكثر البائعين في طلبات الويزارد
    top_wizard_salespersons = (
        wizard_orders
        .values('salesperson__id', 'salesperson__name')
        .annotate(order_count=Count('id'))
        .filter(salesperson__isnull=False)
        .order_by('-order_count')[:5]
    )
    
    # الحصول على قوائم الفروع والبائعين للفلاتر
    from accounts.models import Branch, Salesperson
    
    branches = Branch.objects.filter(is_active=True).order_by('name')
    salespersons = Salesperson.objects.filter(is_active=True).order_by('name')
    
    context = {
        'traditional_orders': traditional_orders,
        'wizard_orders': wizard_orders,
        'traditional_count': traditional_count,
        'wizard_count': wizard_count,
        'total_count': traditional_count + wizard_count,
        
        # أكثر البائعين نشاطاً
        'top_traditional_salespersons': top_traditional_salespersons,
        'top_wizard_salespersons': top_wizard_salespersons,
        
        # الفلاتر
        'filter_type': filter_type,
        'start_date': start_date,
        'end_date': end_date,
        'selected_branch': branch_id,
        'selected_salesperson': salesperson_id,
        'selected_order_type': order_type,
        
        # البيانات للفلاتر
        'branches': branches,
        'salespersons': salespersons,
        
        # التاريخ الحالي
        'today': today,
    }
    
    return render(request, 'reports/orders_report.html', context)
