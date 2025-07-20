"""
العرض الرئيسي للنظام
"""
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Count, Sum, F, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from customers.models import Customer
from orders.models import Order
from inventory.models import Product
from inspections.models import Inspection
from accounts.models import CompanyInfo, ContactFormSettings, AboutPageSettings, FooterSettings, Branch
from manufacturing.models import ManufacturingOrder, ManufacturingOrderItem
from installations.models import InstallationSchedule
import re
from datetime import datetime, timedelta
from django.http import JsonResponse

from django.http import HttpResponse, FileResponse, Http404
from django.conf import settings
import os
import mimetypes
from django.utils.encoding import smart_str

def is_admin_user(user):
    """التحقق من أن المستخدم مدير للنظام"""
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin_user)
def admin_dashboard(request):
    """
    داش بورد احترافي للمدراء يعرض تحليلات شاملة لجميع الأقسام
    """
    # الحصول على المعاملات من الطلب
    selected_branch = request.GET.get('branch', 'all')
    selected_month = request.GET.get('month', 'year')  # الافتراضي هو السنة الكاملة
    selected_year = request.GET.get('year', timezone.now().year)
    comparison_month = request.GET.get('comparison_month', '')
    comparison_year = request.GET.get('comparison_year', '')
    comparison_type = request.GET.get('comparison_type', 'month')  # 'month' or 'year'
    
    # تحويل المعاملات إلى أرقام
    try:
        if selected_month != 'year':
            selected_month = int(selected_month)
        selected_year = int(selected_year)
        if comparison_month:
            comparison_month = int(comparison_month)
        if comparison_year:
            comparison_year = int(comparison_year)
    except (ValueError, TypeError):
        selected_month = 'year'  # الافتراضي هو السنة الكاملة
        selected_year = timezone.now().year
        comparison_month = ''
        comparison_year = ''
    
    # تحديد الفترة الزمنية
    if selected_month == 'year':  # إذا تم اختيار سنة كاملة
        start_date = datetime(selected_year, 1, 1)
        end_date = datetime(selected_year, 12, 31)
    else:  # إذا تم اختيار شهر محدد
        start_date = datetime(selected_year, selected_month, 1)
        if selected_month == 12:
            end_date = datetime(selected_year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(selected_year, selected_month + 1, 1) - timedelta(days=1)
    
    # فلترة البيانات حسب الفرع
    branch_filter = {}
    if selected_branch != 'all':
        branch_filter = {'branch_id': selected_branch}
    
    # إحصائيات العملاء - تطبيق الفلتر الزمني
    customers_stats = get_customers_statistics(selected_branch, start_date, end_date)
    
    # إحصائيات الطلبات
    orders_stats = get_orders_statistics(selected_branch, start_date, end_date)
    
    # إحصائيات التصنيع
    manufacturing_stats = get_manufacturing_statistics(selected_branch, start_date, end_date)
    
    # إحصائيات المعاينات
    inspections_stats = get_inspections_statistics(selected_branch, start_date, end_date)
    
    # إحصائيات التركيبات
    installations_stats = get_installations_statistics(selected_branch, start_date, end_date)
    
    # إحصائيات المخزون
    inventory_stats = get_inventory_statistics(selected_branch)
    
    # مقارنة مع الفترة المحددة إذا تم تحديدها
    comparison_data = {}
    if comparison_year:
        if comparison_type == 'year':  # مقارنة سنة كاملة
            comp_start_date = datetime(comparison_year, 1, 1)
            comp_end_date = datetime(comparison_year, 12, 31)
        elif comparison_month and comparison_month != 'year':  # مقارنة شهر محدد
            comp_start_date = datetime(comparison_year, comparison_month, 1)
            if comparison_month == 12:
                comp_end_date = datetime(comparison_year + 1, 1, 1) - timedelta(days=1)
            else:
                comp_end_date = datetime(comparison_year, comparison_month + 1, 1) - timedelta(days=1)
        else:
            comp_start_date = None
            comp_end_date = None
        
        if comp_start_date and comp_end_date:
            comparison_data = {
                'customers': get_customers_statistics(selected_branch, comp_start_date, comp_end_date),
                'orders': get_orders_statistics(selected_branch, comp_start_date, comp_end_date),
                'manufacturing': get_manufacturing_statistics(selected_branch, comp_start_date, comp_end_date),
                'inspections': get_inspections_statistics(selected_branch, comp_start_date, comp_end_date),
                'installations': get_installations_statistics(selected_branch, comp_start_date, comp_end_date),
            }
    
    # البيانات للرسوم البيانية
    chart_data = get_chart_data(selected_branch, selected_year)
    
    # معلومات الشركة
    company_info = CompanyInfo.objects.first()
    if not company_info:
        company_info = CompanyInfo.objects.create(
            name='LATARA',
            version='1.0.0',
            release_date='2025-04-30',
            developer='zakee tahawi'
        )
    
    # قائمة الفروع للفلتر
    branches = Branch.objects.all()
    
    # قائمة الأشهر للفلتر
    months = [
        (1, 'يناير'), (2, 'فبراير'), (3, 'مارس'), (4, 'أبريل'),
        (5, 'مايو'), (6, 'يونيو'), (7, 'يوليو'), (8, 'أغسطس'),
        (9, 'سبتمبر'), (10, 'أكتوبر'), (11, 'نوفمبر'), (12, 'ديسمبر')
    ]
    
    # قائمة السنوات للفلتر - من قاعدة البيانات
    try:
        from accounts.models import DashboardYearSettings
        available_years = DashboardYearSettings.get_available_years()
        if available_years:
            years = list(available_years)
        else:
            # إذا لم تكن هناك سنوات محددة، استخدم النطاق الافتراضي
            current_year = timezone.now().year
            years = list(range(current_year - 2, current_year + 2))
    except ImportError:
        # في حالة عدم وجود النموذج، استخدم النطاق الافتراضي
        current_year = timezone.now().year
        years = list(range(current_year - 2, current_year + 2))
    
    # تحويل selected_branch إلى string للتأكد من المقارنة الصحيحة
    if selected_branch != 'all':
        selected_branch = str(selected_branch)
    
    context = {
        'customers_stats': customers_stats,
        'orders_stats': orders_stats,
        'manufacturing_stats': manufacturing_stats,
        'inspections_stats': inspections_stats,
        'installations_stats': installations_stats,
        'inventory_stats': inventory_stats,
        'comparison_data': comparison_data,
        'chart_data': chart_data,
        'company_info': company_info,
        'branches': branches,
        'months': months,
        'years': years,
        'selected_branch': selected_branch,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'comparison_month': comparison_month,
        'comparison_year': comparison_year,
        'comparison_type': comparison_type,
        'start_date': start_date,
        'end_date': end_date,
        'timezone': timezone,
    }
    
    return render(request, 'admin_dashboard.html', context)

def get_customers_statistics(branch_filter, start_date=None, end_date=None):
    """إحصائيات العملاء"""
    customers = Customer.objects.all()
    
    # فلترة حسب التاريخ إذا تم تحديده
    if start_date and end_date:
        customers = customers.filter(created_at__range=(start_date, end_date))
    
    # فلترة حسب الفرع
    if branch_filter != 'all':
        customers = customers.filter(branch_id=branch_filter)
    
    # حساب العملاء الجدد هذا الشهر (بغض النظر عن الفلتر الزمني)
    current_month_customers = Customer.objects.all()
    if branch_filter != 'all':
        current_month_customers = current_month_customers.filter(branch_id=branch_filter)
    new_this_month = current_month_customers.filter(created_at__month=timezone.now().month).count()
    
    return {
        'total': customers.count(),
        'active': customers.filter(status='active').count(),
        'inactive': customers.filter(status='inactive').count(),
        'new_this_month': new_this_month,
        'by_branch': customers.values('branch__name').annotate(count=Count('id')),
        'by_category': customers.values('category__name').annotate(count=Count('id')),
    }

def get_orders_statistics(branch_filter, start_date, end_date):
    """إحصائيات الطلبات"""
    orders = Order.objects.filter(created_at__range=(start_date, end_date))
    if branch_filter != 'all':
        orders = orders.filter(branch_id=branch_filter)
    
    return {
        'total': orders.count(),
        'pending': orders.filter(order_status='pending').count(),
        'in_progress': orders.filter(order_status='in_progress').count(),
        'completed': orders.filter(order_status='completed').count(),
        'delivered': orders.filter(order_status='delivered').count(),
        'cancelled': orders.filter(order_status='cancelled').count(),
        'total_amount': orders.aggregate(total=Sum('total_amount'))['total'] or 0,
        'by_type': orders.values('order_type').annotate(count=Count('id')),
    }

def get_manufacturing_statistics(branch_filter, start_date, end_date):
    """إحصائيات التصنيع"""
    manufacturing_orders = ManufacturingOrder.objects.filter(order_date__range=(start_date, end_date))
    if branch_filter != 'all':
        manufacturing_orders = manufacturing_orders.filter(order__branch_id=branch_filter)
    
    return {
        'total': manufacturing_orders.count(),
        'pending': manufacturing_orders.filter(status='pending').count(),
        'in_progress': manufacturing_orders.filter(status='in_progress').count(),
        'completed': manufacturing_orders.filter(status='completed').count(),
        'delivered': manufacturing_orders.filter(status='delivered').count(),
        'cancelled': manufacturing_orders.filter(status='cancelled').count(),
        'by_type': manufacturing_orders.values('order_type').annotate(count=Count('id')),
    }

def get_inspections_statistics(branch_filter, start_date, end_date):
    """إحصائيات المعاينات"""
    inspections = Inspection.objects.filter(created_at__range=(start_date, end_date))
    if branch_filter != 'all':
        inspections = inspections.filter(branch_id=branch_filter)
    
    return {
        'total': inspections.count(),
        'pending': inspections.filter(status='pending').count(),
        'scheduled': inspections.filter(status='scheduled').count(),
        'completed': inspections.filter(status='completed').count(),
        'cancelled': inspections.filter(status='cancelled').count(),
        'successful': inspections.filter(result='passed').count(),
        'failed': inspections.filter(result='failed').count(),
    }

def get_installations_statistics(branch_filter, start_date, end_date):
    """إحصائيات التركيبات"""
    installations = InstallationSchedule.objects.filter(created_at__range=(start_date, end_date))
    if branch_filter != 'all':
        installations = installations.filter(order__branch_id=branch_filter)
    
    return {
        'total': installations.count(),
        'pending': installations.filter(status='pending').count(),
        'scheduled': installations.filter(status='scheduled').count(),
        'in_installation': installations.filter(status='in_installation').count(),
        'completed': installations.filter(status='completed').count(),
        'cancelled': installations.filter(status='cancelled').count(),
    }

def get_inventory_statistics(branch_filter):
    """إحصائيات المخزون"""
    products = Product.objects.all()
    if branch_filter != 'all':
        # يمكن إضافة فلتر حسب الفرع إذا كان متوفراً في نموذج المنتج
        pass
    
    # حساب الإحصائيات باستخدام property
    low_stock_count = 0
    out_of_stock_count = 0
    total_value = 0
    
    for product in products:
        current_stock = product.current_stock
        if current_stock <= product.minimum_stock and current_stock > 0:
            low_stock_count += 1
        elif current_stock == 0:
            out_of_stock_count += 1
        total_value += current_stock * product.price
    
    return {
        'total_products': products.count(),
        'low_stock': low_stock_count,
        'out_of_stock': out_of_stock_count,
        'total_value': total_value,
    }

def get_chart_data(branch_filter, year):
    """البيانات للرسوم البيانية"""
    # بيانات شهرية للطلبات
    orders_monthly = Order.objects.filter(created_at__year=year)
    if branch_filter != 'all':
        orders_monthly = orders_monthly.filter(branch_id=branch_filter)
    
    orders_by_month = orders_monthly.extra(
        select={'month': "EXTRACT(month FROM created_at)"}
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    # بيانات شهرية للعملاء
    customers_monthly = Customer.objects.filter(created_at__year=year)
    if branch_filter != 'all':
        customers_monthly = customers_monthly.filter(branch_id=branch_filter)
    
    customers_by_month = customers_monthly.extra(
        select={'month': "EXTRACT(month FROM created_at)"}
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    return {
        'orders_by_month': list(orders_by_month),
        'customers_by_month': list(customers_by_month),
    }

def home(request):
    """
    View for the home page
    """
    # إذا كان المستخدم مدير، توجيهه إلى داش بورد الإدارة
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('admin_dashboard')
    
    # Get counts for dashboard
    customers_count = Customer.objects.count()
    orders_count = Order.objects.count()
    production_count = ManufacturingOrder.objects.count()
    products_count = Product.objects.count()

    # Get recent orders
    recent_orders = Order.objects.select_related('customer').order_by('-order_date')[:5]

    # Get active manufacturing orders
    production_orders = ManufacturingOrder.objects.select_related(
        'order'
    ).exclude(
        status__in=['completed', 'cancelled']
    ).order_by('expected_delivery_date')[:5]    # Get low stock products
    low_stock_products = [
        product for product in Product.objects.all()
        if product.current_stock > 0 and product.current_stock <= product.minimum_stock
    ][:10]

    # Get company info for logo
    company_info = CompanyInfo.objects.first()
    if not company_info:
        company_info = CompanyInfo.objects.create(
            name='LATARA',
            version='1.0.0',
            release_date='2025-04-30',
            developer='zakee tahawi'
        )

    context = {
        'customers_count': customers_count,
        'orders_count': orders_count,
        'production_count': production_count,
        'products_count': products_count,
        'recent_orders': recent_orders,
        'production_orders': production_orders,
        'low_stock_products': low_stock_products,
        'current_year': timezone.now().year,
        'company_info': company_info,
    }

    return render(request, 'home.html', context)


def about(request):
    """
    View for the about page
    """
    # الحصول على إعدادات صفحة حول النظام أو إنشاء إعداد افتراضي إذا لم يكن موجودًا
    about_settings = AboutPageSettings.objects.first()
    if not about_settings:
        about_settings = AboutPageSettings.objects.create()

    # جلب معلومات الشركة (logo)
    company_info = CompanyInfo.objects.first()
    
    context = {
        'title': about_settings.title,
        'subtitle': about_settings.subtitle,
        'system_description': about_settings.system_description,
        'system_version': about_settings.system_version,
        'system_release_date': about_settings.system_release_date,
        'system_developer': about_settings.system_developer,
        'current_year': timezone.now().year,
        'company_info': company_info,  # إضافة معلومات الشركة للسياق
    }
    return render(request, 'about.html', context)

def contact(request):
    """
    View for the contact page
    """
    # الحصول على معلومات الشركة من CompanyInfo
    from accounts.models import CompanyInfo
    company_info = CompanyInfo.objects.first() or CompanyInfo.objects.create()

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        if not all([name, email, subject, message]):
            messages.error(request, 'يرجى ملء جميع الحقول المطلوبة.')
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            messages.error(request, 'يرجى إدخال بريد إلكتروني صحيح.')
        else:
            # هنا يمكن إرسال البريد الإلكتروني فعليًا
            messages.success(request, 'تم إرسال رسالتك بنجاح. سنتواصل معك قريباً.')
            return redirect('contact')

    context = {
        'title': 'اتصل بنا',
        'description': company_info.description,
        'form_title': 'نموذج الاتصال',
        'company_info': company_info,
        'current_year': timezone.now().year,
    }
    return render(request, 'contact.html', context)

def serve_media_file(request, path):
    """
    Custom view to serve media files using FileResponse.
    Securely serves files from MEDIA_ROOT directory.
    """
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        raise Http404("Media file not found")

    try:
        # استخدام mimetypes للكشف عن نوع الملف
        content_type, encoding = mimetypes.guess_type(file_path)
        content_type = content_type or 'application/octet-stream'

        # فتح الملف كـ binary stream
        file = open(file_path, 'rb')

        # إنشاء FileResponse مع streaming content
        response = FileResponse(file, content_type=content_type)

        # إعداد headers مناسبة للملف
        filename = os.path.basename(file_path)
        response['Content-Disposition'] = f'inline; filename="{smart_str(filename)}"'

        # إضافة headers إضافية للPDF
        if content_type == 'application/pdf':
            response['Accept-Ranges'] = 'bytes'
            response['Content-Length'] = os.path.getsize(file_path)

        return response
    except IOError:
        raise Http404("Error reading file")
    except Exception as e:
        if 'file' in locals():
            file.close()
        raise Http404(f"Error processing file: {str(e)}")

def data_management_redirect(request):
    """
    إعادة توجيه من المسارات القديمة إلى المسار الجديد لإدارة قواعد البيانات
    """
    return redirect('odoo_db_manager:dashboard')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api(request):
    """API endpoint for dashboard data"""
    today = timezone.now().date()
    data = {
        'customers': {
            'total': Customer.objects.count(),
            'active': Customer.objects.filter(status='active').count()
        },
        'orders': {
            'total': Order.objects.count(),
            'pending': Order.objects.filter(status='pending').count(),
            'completed': Order.objects.filter(status='completed').count(),
            'recent': list(Order.objects.select_related('customer')
                         .order_by('-created_at')[:5]
                         .values('id', 'customer__name', 'total_amount', 'status'))
        },
        'inventory': {
            'total_products': Product.objects.count(),
            'low_stock': Product.objects.filter(current_stock__lte=F('minimum_stock')).count()
        },
        'production': {
            'active_orders': ManufacturingOrder.objects.exclude(status__in=['completed', 'cancelled']).count(),
            'completed_today': ManufacturingOrder.objects.filter(completed_at__date=today).count()
        },
        'inspections': {
            'pending': Inspection.objects.filter(status='pending').count(),
            'completed': Inspection.objects.filter(status='completed').count()
        }
    }
    return Response(data)
