"""
دوال مساعدة محسنة لداشبورد الإدارة - مصححة
"""
from django.utils import timezone
from django.db.models import Count, Sum, Q, F, Max
from datetime import datetime, timedelta
from customers.models import Customer
from orders.models import Order
from inventory.models import Product
from inspections.models import Inspection
from manufacturing.models import ManufacturingOrder
from installations.models import InstallationSchedule
from accounts.models import Branch, DashboardYearSettings
from complaints.models import Complaint, ComplaintType


def get_customers_statistics(branch_filter, start_date=None, end_date=None, show_all_years=False):
    """إحصائيات العملاء المحسنة"""
    customers = Customer.objects.all()
    
    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        customers = customers.filter(created_at__range=(start_date, end_date))
    
    # فلترة حسب الفرع
    if branch_filter != 'all':
        customers = customers.filter(branch_id=branch_filter)
    
    # إحصائيات متقدمة
    stats = customers.aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status='active')),
        inactive=Count('id', filter=Q(status='inactive')),
        individual=Count('id', filter=Q(customer_type='individual')),
        company=Count('id', filter=Q(customer_type='company')),
    )
    
    # العملاء الجدد هذا الشهر
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = customers.filter(created_at__gte=current_month_start).count()
    
    # توزيع العملاء حسب الفرع والفئة
    by_branch = customers.values('branch__name').annotate(count=Count('id')).order_by('-count')
    by_category = customers.values('category__name').annotate(count=Count('id')).order_by('-count')
    
    return {
        **stats,
        'new_this_month': new_this_month,
        'by_branch': list(by_branch),
        'by_category': list(by_category),
        'growth_rate': calculate_growth_rate(customers, 'created_at'),
    }


def get_orders_statistics(branch_filter, start_date, end_date, show_all_years=False):
    """إحصائيات الطلبات المحسنة"""
    orders = Order.objects.all()
    
    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        orders = orders.filter(order_date__range=(start_date, end_date))
    
    # فلترة حسب الفرع
    if branch_filter != 'all':
        orders = orders.filter(branch_id=branch_filter)
    
    # إحصائيات متقدمة
    stats = orders.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(order_status='pending')),
        pending_approval=Count('id', filter=Q(order_status='pending_approval')),
        in_progress=Count('id', filter=Q(order_status='in_progress')),
        ready_install=Count('id', filter=Q(order_status='ready_install')),
        completed=Count('id', filter=Q(order_status='completed')),
        delivered=Count('id', filter=Q(order_status='delivered')),
        cancelled=Count('id', filter=Q(order_status='cancelled')),
        rejected=Count('id', filter=Q(order_status='rejected')),
        total_amount=Sum('total_amount'),
    )
    
    # حساب المتوسط يدوياً لتجنب خطأ Avg على Sum
    avg_amount = 0
    if stats['total'] > 0 and stats['total_amount']:
        avg_amount = stats['total_amount'] / stats['total']
    
    # إحصائيات حسب النوع
    by_type = orders.values('selected_types').annotate(count=Count('id')).order_by('-count')
    
    # معدل الإتمام
    completion_rate = 0
    if stats['total'] > 0:
        completed_count = (stats['completed'] or 0) + (stats['delivered'] or 0)
        completion_rate = (completed_count / stats['total']) * 100
    
    return {
        **stats,
        'avg_amount': round(avg_amount, 2),
        'by_type': list(by_type),
        'completion_rate': round(completion_rate, 1),
    }


def get_manufacturing_statistics(branch_filter, start_date, end_date, show_all_years=False):
    """إحصائيات التصنيع المحسنة"""
    manufacturing_orders = ManufacturingOrder.objects.select_related('order')
    
    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        manufacturing_orders = manufacturing_orders.filter(order__order_date__range=(start_date, end_date))
    
    # فلترة حسب الفرع
    if branch_filter != 'all':
        manufacturing_orders = manufacturing_orders.filter(order__branch_id=branch_filter)
    
    # إحصائيات متقدمة
    stats = manufacturing_orders.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        completed=Count('id', filter=Q(status='completed')),
        delivered=Count('id', filter=Q(status='delivered')),
        cancelled=Count('id', filter=Q(status='cancelled')),
        total_amount=Sum('order__total_amount'),
    )
    
    # إحصائيات حسب النوع
    by_type = manufacturing_orders.values('order_type').annotate(count=Count('id')).order_by('-count')
    
    return {
        **stats,
        'by_type': list(by_type),
    }


def get_inspections_statistics(branch_filter, start_date, end_date, show_all_years=False):
    """إحصائيات المعاينات المحسنة"""
    inspections = Inspection.objects.all()
    
    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        inspections = inspections.filter(created_at__range=(start_date, end_date))
    
    # فلترة حسب الفرع
    if branch_filter != 'all':
        inspections = inspections.filter(branch_id=branch_filter)
    
    # إحصائيات متقدمة
    stats = inspections.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        scheduled=Count('id', filter=Q(status='scheduled')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        completed=Count('id', filter=Q(status='completed')),
        cancelled=Count('id', filter=Q(status='cancelled')),
        successful=Count('id', filter=Q(result='passed')),
        failed=Count('id', filter=Q(result='failed')),
    )
    
    # معدل النجاح
    success_rate = 0
    if stats['total'] > 0:
        success_rate = ((stats['successful'] or 0) / stats['total']) * 100
    
    return {
        **stats,
        'success_rate': round(success_rate, 1),
    }


def get_installation_orders_statistics(branch_filter, start_date, end_date, show_all_years=False):
    """إحصائيات طلبات التركيب المحسنة"""
    # البحث في الطلبات التي تحتوي على تركيب
    orders = Order.objects.filter(
        Q(selected_types__icontains='installation') | 
        Q(service_types__contains=['installation']) |
        Q(service_types__icontains='installation')
    )
    
    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        orders = orders.filter(order_date__range=(start_date, end_date))
    
    # فلترة حسب الفرع
    if branch_filter != 'all':
        orders = orders.filter(branch_id=branch_filter)
    
    # إحصائيات متقدمة
    stats = orders.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(order_status='pending')),
        in_progress=Count('id', filter=Q(order_status='in_progress')),
        ready_install=Count('id', filter=Q(order_status='ready_install')),
        completed=Count('id', filter=Q(order_status='completed')),
        delivered=Count('id', filter=Q(order_status='delivered')),
        cancelled=Count('id', filter=Q(order_status='cancelled')),
        total_amount=Sum('total_amount'),
    )
    
    return stats


def get_installations_statistics(branch_filter, start_date, end_date, show_all_years=False):
    """إحصائيات التركيبات الفعلية المحسنة"""
    try:
        installations = InstallationSchedule.objects.all()
        
        # تطبيق فلتر التاريخ
        if not show_all_years and start_date and end_date:
            installations = installations.filter(created_at__range=(start_date, end_date))
        
        # فلترة حسب الفرع
        if branch_filter != 'all':
            installations = installations.filter(order__branch_id=branch_filter)
        
        # إحصائيات متقدمة
        stats = installations.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            scheduled=Count('id', filter=Q(status='scheduled')),
            in_installation=Count('id', filter=Q(status='in_installation')),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled')),
        )
        
        return stats
    except Exception:
        # في حالة عدم وجود نموذج التركيبات
        return {
            'total': 0,
            'pending': 0,
            'scheduled': 0,
            'in_installation': 0,
            'completed': 0,
            'cancelled': 0,
        }


def get_inventory_statistics(branch_filter):
    """إحصائيات المخزون المبسطة - سريعة جداً"""
    # فلترة المنتجات
    products_filter = {}
    if branch_filter != 'all' and hasattr(Product, 'branch'):
        products_filter['branch_id'] = branch_filter
    
    # الحصول على عدد المنتجات الإجمالي فقط
    total_products = Product.objects.filter(**products_filter).count()
    
    # إحصائيات مبسطة بدون حساب المخزون التفصيلي
    # يمكن إضافة حساب المخزون لاحقاً عند الحاجة
    
    return {
        'total_products': total_products,
        'low_stock': 0,  # سيتم حسابها لاحقاً
        'out_of_stock': 0,  # سيتم حسابها لاحقاً
        'total_value': 0,  # سيتم حسابها لاحقاً
        'low_stock_percentage': 0,
        'out_of_stock_percentage': 0,
    }


def get_enhanced_chart_data(branch_filter, selected_year, show_all_years=False):
    """البيانات المحسنة للرسوم البيانية"""
    if show_all_years or selected_year == 'all':
        # عرض البيانات لجميع السنوات
        return get_multi_year_chart_data(branch_filter)
    else:
        # عرض البيانات لسنة محددة
        return get_single_year_chart_data(branch_filter, selected_year)


def get_single_year_chart_data(branch_filter, year):
    """بيانات الرسوم البيانية لسنة واحدة"""
    # بيانات شهرية للطلبات
    orders_monthly = Order.objects.filter(order_date__year=year)
    if branch_filter != 'all':
        orders_monthly = orders_monthly.filter(branch_id=branch_filter)
    
    orders_by_month = orders_monthly.extra(
        select={'month': "EXTRACT(month FROM order_date)"}
    ).values('month').annotate(
        count=Count('id'),
        amount=Sum('total_amount')
    ).order_by('month')
    
    # بيانات شهرية للعملاء
    customers_monthly = Customer.objects.filter(created_at__year=year)
    if branch_filter != 'all':
        customers_monthly = customers_monthly.filter(branch_id=branch_filter)
    
    customers_by_month = customers_monthly.extra(
        select={'month': "EXTRACT(month FROM created_at)"}
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    # بيانات شهرية للمعاينات
    inspections_monthly = Inspection.objects.filter(created_at__year=year)
    if branch_filter != 'all':
        inspections_monthly = inspections_monthly.filter(branch_id=branch_filter)
    
    inspections_by_month = inspections_monthly.extra(
        select={'month': "EXTRACT(month FROM created_at)"}
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    return {
        'orders_by_month': list(orders_by_month),
        'customers_by_month': list(customers_by_month),
        'inspections_by_month': list(inspections_by_month),
        'type': 'monthly',
        'year': year,
    }


def get_multi_year_chart_data(branch_filter):
    """بيانات الرسوم البيانية لعدة سنوات"""
    # بيانات سنوية للطلبات
    orders_yearly = Order.objects.all()
    if branch_filter != 'all':
        orders_yearly = orders_yearly.filter(branch_id=branch_filter)
    
    orders_by_year = orders_yearly.extra(
        select={'year': "EXTRACT(year FROM order_date)"}
    ).values('year').annotate(
        count=Count('id'),
        amount=Sum('total_amount')
    ).order_by('year')
    
    # بيانات سنوية للعملاء
    customers_yearly = Customer.objects.all()
    if branch_filter != 'all':
        customers_yearly = customers_yearly.filter(branch_id=branch_filter)
    
    customers_by_year = customers_yearly.extra(
        select={'year': "EXTRACT(year FROM created_at)"}
    ).values('year').annotate(count=Count('id')).order_by('year')
    
    # بيانات سنوية للمعاينات
    inspections_yearly = Inspection.objects.all()
    if branch_filter != 'all':
        inspections_yearly = inspections_yearly.filter(branch_id=branch_filter)
    
    inspections_by_year = inspections_yearly.extra(
        select={'year': "EXTRACT(year FROM created_at)"}
    ).values('year').annotate(count=Count('id')).order_by('year')
    
    return {
        'orders_by_year': list(orders_by_year),
        'customers_by_year': list(customers_by_year),
        'inspections_by_year': list(inspections_by_year),
        'type': 'yearly',
    }


def calculate_growth_rate(queryset, date_field):
    """حساب معدل النمو"""
    try:
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = (current_month - timedelta(days=1)).replace(day=1)
        
        current_count = queryset.filter(**{f'{date_field}__gte': current_month}).count()
        last_count = queryset.filter(
            **{f'{date_field}__gte': last_month, f'{date_field}__lt': current_month}
        ).count()
        
        if last_count > 0:
            growth_rate = ((current_count - last_count) / last_count) * 100
            return round(growth_rate, 1)
        return 0
    except Exception:
        return 0


def get_dashboard_summary(stats):
    """ملخص الداشبورد"""
    try:
        total_revenue = stats['orders_stats']['total_amount'] or 0
        total_orders = stats['orders_stats']['total'] or 0
        total_customers = stats['customers_stats']['total'] or 0
        
        avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0
        
        return {
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'total_customers': total_customers,
            'avg_order_value': round(avg_order_value, 2),
        }
    except Exception:
        return {
            'total_revenue': 0,
            'total_orders': 0,
            'total_customers': 0,
            'avg_order_value': 0,
        }


def get_complaints_statistics(branch_filter, start_date=None, end_date=None, show_all_years=False):
    """إحصائيات الشكاوى"""
    complaints = Complaint.objects.all()
    
    # تطبيق فلتر التاريخ
    if not show_all_years and start_date and end_date:
        complaints = complaints.filter(created_at__range=(start_date, end_date))
    
    # فلترة حسب الفرع
    if branch_filter != 'all':
        complaints = complaints.filter(branch_id=branch_filter)
    
    # إحصائيات متقدمة
    stats = complaints.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='pending')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        resolved=Count('id', filter=Q(status='resolved')),
        closed=Count('id', filter=Q(status='closed')),
        urgent=Count('id', filter=Q(priority='urgent')),
        high=Count('id', filter=Q(priority='high')),
        medium=Count('id', filter=Q(priority='medium')),
        low=Count('id', filter=Q(priority='low')),
    )
    
    # الشكاوى الجديدة هذا الشهر
    current_month_start = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    new_this_month = complaints.filter(created_at__gte=current_month_start).count()
    
    # الشكاوى المتأخرة
    overdue = complaints.filter(
        deadline__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).count()
    
    # توزيع الشكاوى حسب النوع
    by_type = complaints.values('complaint_type__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # الشكاوى حسب الأسبوع (آخر 4 أسابيع)
    weekly_stats = []
    for i in range(4):
        week_start = timezone.now() - timedelta(weeks=i+1)
        week_end = timezone.now() - timedelta(weeks=i)
        week_count = complaints.filter(
            created_at__range=(week_start, week_end)
        ).count()
        weekly_stats.append({
            'week': f'الأسبوع {i+1}',
            'count': week_count
        })
    
    return {
        **stats,
        'new_this_month': new_this_month,
        'overdue': overdue,
        'by_type': list(by_type),
        'weekly_stats': weekly_stats,
        'resolution_rate': calculate_resolution_rate(complaints),
        'growth_rate': calculate_growth_rate(complaints, 'created_at'),
    }


def calculate_resolution_rate(complaints):
    """حساب معدل حل الشكاوى"""
    try:
        total = complaints.count()
        resolved = complaints.filter(
            status__in=['resolved', 'closed']
        ).count()
        
        if total > 0:
            return round((resolved / total) * 100, 1)
        return 0
    except Exception:
        return 0