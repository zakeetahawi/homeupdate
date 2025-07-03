"""
لوحة التحكم الموحدة لجميع الأقسام
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta, date

from .models_new import InstallationNew, InstallationTeamNew
from orders.models import Order
from factory.models import ProductionOrder, ProductionLine
from customers.models import Customer


@login_required
def unified_dashboard(request):
    """لوحة التحكم الموحدة لجميع الأقسام"""
    
    # التواريخ المهمة
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # === إحصائيات الطلبات ===
    orders_stats = get_orders_statistics(today, week_start, month_start)
    
    # === إحصائيات التركيبات ===
    installations_stats = get_installations_statistics(today, week_start, month_start)
    
    # === إحصائيات المصنع ===
    factory_stats = get_factory_statistics(today, week_start, month_start)
    
    # === إحصائيات العملاء ===
    customers_stats = get_customers_statistics(today, week_start, month_start)
    
    # === الأنشطة الأخيرة ===
    recent_activities = get_recent_activities()
    
    # === التنبيهات والإنذارات ===
    alerts = get_system_alerts()
    
    # === الإحصائيات السريعة ===
    quick_stats = {
        'total_orders_today': orders_stats['today_count'],
        'pending_installations': installations_stats['pending_count'],
        'active_production': factory_stats['active_orders'],
        'new_customers_week': customers_stats['new_this_week'],
    }
    
    context = {
        'title': 'لوحة التحكم الموحدة',
        'orders_stats': orders_stats,
        'installations_stats': installations_stats,
        'factory_stats': factory_stats,
        'customers_stats': customers_stats,
        'recent_activities': recent_activities,
        'alerts': alerts,
        'quick_stats': quick_stats,
        'today': today,
    }
    
    return render(request, 'installations/unified_dashboard.html', context)


def get_orders_statistics(today, week_start, month_start):
    """إحصائيات الطلبات"""
    try:
        total_orders = Order.objects.count()
        today_orders = Order.objects.filter(created_at__date=today).count()
        week_orders = Order.objects.filter(created_at__date__gte=week_start).count()
        month_orders = Order.objects.filter(created_at__date__gte=month_start).count()
        
        # الطلبات حسب النوع
        installation_orders = Order.objects.filter(
            selected_types__contains='installation'
        ).count()
        
        tailoring_orders = Order.objects.filter(
            selected_types__contains='tailoring'
        ).count()
        
        # الطلبات حسب الحالة
        pending_orders = Order.objects.filter(status='pending').count()
        completed_orders = Order.objects.filter(status='completed').count()
        
        return {
            'total_count': total_orders,
            'today_count': today_orders,
            'week_count': week_orders,
            'month_count': month_orders,
            'installation_count': installation_orders,
            'tailoring_count': tailoring_orders,
            'pending_count': pending_orders,
            'completed_count': completed_orders,
        }
    except Exception as e:
        return {'error': str(e)}


def get_installations_statistics(today, week_start, month_start):
    """إحصائيات التركيبات"""
    try:
        total_installations = InstallationNew.objects.count()
        
        # التركيبات حسب الحالة
        pending_count = InstallationNew.objects.filter(status='pending').count()
        in_production_count = InstallationNew.objects.filter(status='in_production').count()
        ready_count = InstallationNew.objects.filter(status='ready').count()
        scheduled_count = InstallationNew.objects.filter(status='scheduled').count()
        in_progress_count = InstallationNew.objects.filter(status='in_progress').count()
        completed_count = InstallationNew.objects.filter(status='completed').count()
        
        # التركيبات اليوم
        today_installations = InstallationNew.objects.filter(
            scheduled_date=today
        ).count()
        
        # التركيبات هذا الأسبوع
        week_installations = InstallationNew.objects.filter(
            scheduled_date__gte=week_start,
            scheduled_date__lte=today + timedelta(days=6)
        ).count()
        
        return {
            'total_count': total_installations,
            'pending_count': pending_count,
            'in_production_count': in_production_count,
            'ready_count': ready_count,
            'scheduled_count': scheduled_count,
            'in_progress_count': in_progress_count,
            'completed_count': completed_count,
            'today_count': today_installations,
            'week_count': week_installations,
        }
    except Exception as e:
        return {'error': str(e)}


def get_factory_statistics(today, week_start, month_start):
    """إحصائيات المصنع"""
    try:
        total_production_orders = ProductionOrder.objects.count()
        active_orders = ProductionOrder.objects.filter(status='in_progress').count()
        completed_orders = ProductionOrder.objects.filter(status='completed').count()
        pending_orders = ProductionOrder.objects.filter(status='pending').count()
        
        # خطوط الإنتاج
        total_lines = ProductionLine.objects.count()
        active_lines = ProductionLine.objects.filter(is_active=True).count()
        
        # الإنتاج اليوم
        today_production = ProductionOrder.objects.filter(
            start_date=today
        ).count()
        
        return {
            'total_orders': total_production_orders,
            'active_orders': active_orders,
            'completed_orders': completed_orders,
            'pending_orders': pending_orders,
            'total_lines': total_lines,
            'active_lines': active_lines,
            'today_production': today_production,
        }
    except Exception as e:
        return {'error': str(e)}


def get_customers_statistics(today, week_start, month_start):
    """إحصائيات العملاء"""
    try:
        total_customers = Customer.objects.count()
        new_today = Customer.objects.filter(created_at__date=today).count()
        new_this_week = Customer.objects.filter(created_at__date__gte=week_start).count()
        new_this_month = Customer.objects.filter(created_at__date__gte=month_start).count()
        
        # العملاء VIP
        vip_customers = Customer.objects.filter(is_vip=True).count() if hasattr(Customer, 'is_vip') else 0
        
        return {
            'total_count': total_customers,
            'new_today': new_today,
            'new_this_week': new_this_week,
            'new_this_month': new_this_month,
            'vip_count': vip_customers,
        }
    except Exception as e:
        return {'error': str(e)}


def get_recent_activities():
    """الأنشطة الأخيرة"""
    try:
        activities = []
        
        # آخر الطلبات
        recent_orders = Order.objects.order_by('-created_at')[:5]
        for order in recent_orders:
            activities.append({
                'type': 'order',
                'title': f'طلب جديد #{order.order_number}',
                'description': f'عميل: {order.customer_name}',
                'time': order.created_at,
                'icon': 'fas fa-shopping-cart',
                'color': 'primary'
            })
        
        # آخر التركيبات
        recent_installations = InstallationNew.objects.order_by('-created_at')[:5]
        for installation in recent_installations:
            activities.append({
                'type': 'installation',
                'title': f'تركيب جديد #{installation.id}',
                'description': f'عميل: {installation.customer_name}',
                'time': installation.created_at,
                'icon': 'fas fa-tools',
                'color': 'success'
            })
        
        # ترتيب حسب الوقت
        activities.sort(key=lambda x: x['time'], reverse=True)
        
        return activities[:10]
    except Exception as e:
        return []


def get_system_alerts():
    """التنبيهات والإنذارات"""
    try:
        alerts = []
        
        # تحقق من التركيبات المتأخرة
        overdue_installations = InstallationNew.objects.filter(
            scheduled_date__lt=timezone.now().date(),
            status__in=['scheduled', 'pending']
        ).count()
        
        if overdue_installations > 0:
            alerts.append({
                'type': 'warning',
                'title': 'تركيبات متأخرة',
                'message': f'يوجد {overdue_installations} تركيب متأخر',
                'icon': 'fas fa-exclamation-triangle'
            })
        
        # تحقق من الطلبات المعلقة
        pending_orders = Order.objects.filter(status='pending').count()
        if pending_orders > 10:
            alerts.append({
                'type': 'info',
                'title': 'طلبات معلقة',
                'message': f'يوجد {pending_orders} طلب معلق',
                'icon': 'fas fa-clock'
            })
        
        # تحقق من خطوط الإنتاج المتوقفة
        inactive_lines = ProductionLine.objects.filter(is_active=False).count()
        if inactive_lines > 0:
            alerts.append({
                'type': 'danger',
                'title': 'خطوط إنتاج متوقفة',
                'message': f'يوجد {inactive_lines} خط إنتاج متوقف',
                'icon': 'fas fa-stop-circle'
            })
        
        return alerts
    except Exception as e:
        return []
