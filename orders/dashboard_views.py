"""
دوال الداشبورد والصفحات المنفصلة لقسم الطلبات
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from accounts.models import SystemSettings
from .permissions import get_user_orders_queryset, get_user_role_permissions


@login_required
def orders_dashboard(request):
    """داشبورد الطلبات الرئيسي"""
    # التحقق من صلاحيات المستخدم
    user_permissions = get_user_role_permissions(request.user)
    if not user_permissions.get("can_manage_dashboard", False):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("ليس لديك صلاحية للوصول إلى هذه الصفحة")

    # الحصول على الطلبات حسب صلاحيات المستخدم
    orders = get_user_orders_queryset(request.user)
    
    # إحصائيات البطاقات الأربع
    inspection_count = orders.filter(selected_types__icontains='inspection').count()
    installation_count = orders.filter(selected_types__icontains='installation').count()
    accessory_count = orders.filter(selected_types__icontains='accessory').count()
    tailoring_count = orders.filter(selected_types__icontains='tailoring').count()
    
    # إحصائيات عامة
    total_orders = orders.count()
    pending_orders = orders.filter(order_status__in=['pending', 'pending_approval']).count()
    in_progress_orders = orders.filter(order_status='in_progress').count()
    completed_orders = orders.filter(order_status__in=['completed', 'delivered']).count()
    ready_install_orders = orders.filter(order_status='ready_install').count()
    
    # إجمالي الإيرادات
    total_revenue = orders.filter(order_status__in=['completed', 'delivered']).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # أحدث الطلبات
    recent_orders = orders.order_by('-created_at')[:10]
    
    # رمز العملة
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'
    
    context = {
        'inspection_count': inspection_count,
        'installation_count': installation_count,
        'accessory_count': accessory_count,
        'tailoring_count': tailoring_count,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'in_progress_orders': in_progress_orders,
        'completed_orders': completed_orders,
        'ready_install_orders': ready_install_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'currency_symbol': currency_symbol,
    }
    
    return render(request, 'orders/orders_dashboard.html', context)


@login_required
def inspection_orders(request):
    """صفحة طلبات المعاينة"""
    # الحصول على الطلبات حسب صلاحيات المستخدم
    orders = get_user_orders_queryset(request.user)
    
    # تصفية طلبات المعاينة فقط
    orders = orders.filter(selected_types__icontains='inspection')
    
    # معالجة البحث والتصفية
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    page_size = request.GET.get('page_size', '25')
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(customer__phone__icontains=search_query)
        )
    
    if status_filter:
        orders = orders.filter(inspection_status=status_filter)
    
    # ترتيب وتقسيم الصفحات
    orders = orders.order_by('-created_at')
    
    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 25
    except:
        page_size = 25
    
    paginator = Paginator(orders, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات
    total_count = orders.count()
    pending_count = orders.filter(inspection_status__in=['not_scheduled', 'pending']).count()
    in_progress_count = orders.filter(inspection_status='in_progress').count()
    completed_count = orders.filter(inspection_status='completed').count()
    
    # رمز العملة
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': total_count,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'currency_symbol': currency_symbol,
    }
    
    return render(request, 'orders/inspection_orders.html', context)


@login_required
def installation_orders(request):
    """صفحة طلبات التركيب"""
    # الحصول على الطلبات حسب صلاحيات المستخدم
    orders = get_user_orders_queryset(request.user)
    
    # تصفية طلبات التركيب فقط
    orders = orders.filter(selected_types__icontains='installation')
    
    # معالجة البحث والتصفية
    search_query = request.GET.get('search', '')
    installation_status_filter = request.GET.get('installation_status', '')
    page_size = request.GET.get('page_size', '25')
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(customer__phone__icontains=search_query)
        )
    
    if installation_status_filter:
        orders = orders.filter(installation_status=installation_status_filter)
    
    # ترتيب وتقسيم الصفحات
    orders = orders.order_by('-created_at')
    
    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 25
    except:
        page_size = 25
    
    paginator = Paginator(orders, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات
    total_count = orders.count()
    needs_scheduling_count = orders.filter(installation_status='needs_scheduling').count()
    in_installation_count = orders.filter(installation_status='in_installation').count()
    completed_count = orders.filter(installation_status='completed').count()
    
    # رمز العملة
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'installation_status_filter': installation_status_filter,
        'total_count': total_count,
        'needs_scheduling_count': needs_scheduling_count,
        'in_installation_count': in_installation_count,
        'completed_count': completed_count,
        'currency_symbol': currency_symbol,
    }
    
    return render(request, 'orders/installation_orders.html', context)


@login_required
def accessory_orders(request):
    """صفحة طلبات الإكسسوار"""
    # الحصول على الطلبات حسب صلاحيات المستخدم
    orders = get_user_orders_queryset(request.user)
    
    # تصفية طلبات الإكسسوار فقط
    orders = orders.filter(selected_types__icontains='accessory')
    
    # معالجة البحث والتصفية
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    page_size = request.GET.get('page_size', '25')
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(customer__phone__icontains=search_query)
        )
    
    if status_filter:
        orders = orders.filter(order_status=status_filter)
    
    # ترتيب وتقسيم الصفحات
    orders = orders.order_by('-created_at')
    
    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 25
    except:
        page_size = 25
    
    paginator = Paginator(orders, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات
    total_count = orders.count()
    pending_count = orders.filter(order_status__in=['pending', 'pending_approval']).count()
    ready_count = orders.filter(order_status='ready_install').count()
    delivered_count = orders.filter(order_status='delivered').count()
    
    # رمز العملة
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': total_count,
        'pending_count': pending_count,
        'ready_count': ready_count,
        'delivered_count': delivered_count,
        'currency_symbol': currency_symbol,
    }
    
    return render(request, 'orders/accessory_orders.html', context)


@login_required
def tailoring_orders(request):
    """صفحة طلبات التسليم"""
    # الحصول على الطلبات حسب صلاحيات المستخدم
    orders = get_user_orders_queryset(request.user)
    
    # تصفية طلبات التسليم فقط
    orders = orders.filter(selected_types__icontains='tailoring')
    
    # معالجة البحث والتصفية
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    delivery_type_filter = request.GET.get('delivery_type', '')
    contract_filter = request.GET.get('contract', '')
    page_size = request.GET.get('page_size', '25')
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(customer__phone__icontains=search_query)
        )
    
    if status_filter:
        orders = orders.filter(order_status=status_filter)
    
    if delivery_type_filter:
        orders = orders.filter(delivery_type=delivery_type_filter)
    
    if contract_filter:
        orders = orders.filter(contract_number__icontains=contract_filter)
    
    # ترت��ب وتقسيم الصفحات
    orders = orders.order_by('-created_at')
    
    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 25
    except:
        page_size = 25
    
    paginator = Paginator(orders, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات
    total_count = orders.count()
    in_progress_count = orders.filter(order_status='in_progress').count()
    ready_count = orders.filter(order_status='ready_install').count()
    delivered_count = orders.filter(order_status='delivered').count()
    
    # رمز العملة
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'delivery_type_filter': delivery_type_filter,
        'contract_filter': contract_filter,
        'total_count': total_count,
        'in_progress_count': in_progress_count,
        'ready_count': ready_count,
        'delivered_count': delivered_count,
        'currency_symbol': currency_symbol,
    }
    
    return render(request, 'orders/tailoring_orders.html', context)