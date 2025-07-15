from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.core.serializers import serialize
from django.db import models
import json
from datetime import datetime, timedelta
from accounts.models import SystemSettings
from orders.models import Order
from customers.models import Customer

from .models import (
    InstallationSchedule, InstallationTeam, Technician, Driver,
    ModificationRequest, ModificationImage, ManufacturingOrder,
    ModificationReport, ReceiptMemo, InstallationPayment, InstallationArchive, CustomerDebt,
    InstallationAnalytics, ModificationErrorAnalysis, ModificationErrorType
)
from .forms import (
    InstallationScheduleForm, QuickScheduleForm, InstallationTeamForm, TechnicianForm, DriverForm,
    ModificationReportForm, ReceiptMemoForm, InstallationPaymentForm,
    InstallationFilterForm, DailyScheduleForm, CustomerDebtForm, CustomerDebtPaymentForm,
    InstallationStatusForm, ModificationRequestForm, ModificationImageForm,
    ManufacturingOrderForm, ModificationReportForm as ModificationReportForm_new,
    InstallationAnalyticsForm, ModificationErrorAnalysisForm
)


@login_required
def dashboard(request):
    """لوحة تحكم التركيبات"""
    # إحصائيات عامة
    total_installations = InstallationSchedule.objects.count()
    completed_installations = InstallationSchedule.objects.filter(status='completed').count()
    pending_installations = InstallationSchedule.objects.filter(status='pending').count()
    in_progress_installations = InstallationSchedule.objects.filter(status='in_progress').count()
    
    # إحصائيات التعديلات
    total_modifications = ModificationRequest.objects.count()
    pending_modifications = ModificationRequest.objects.filter(installation__status='modification_required').count()
    in_progress_modifications = ModificationRequest.objects.filter(installation__status='modification_in_progress').count()
    completed_modifications = ModificationRequest.objects.filter(installation__status='modification_completed').count()
    
    # الطلبات الجاهزة للتركيب (مكتملة في التصنيع)
    orders_ready_for_installation = Order.objects.filter(
        order_status='completed',
        installationschedule__isnull=True
    ).count()
    
    # الطلبات الجاهزة للتركيب مع مديونية
    orders_with_debt = Order.objects.filter(
        order_status='completed',
        installationschedule__isnull=True
    ).filter(
        total_amount__gt=F('paid_amount')
    ).count()
    
    # الطلبات تحت التصنيع
    orders_in_manufacturing = Order.objects.filter(
        order_status='in_progress'
    ).count()
    
    # الطلبات المكتملة في المصنع
    orders_completed_in_factory = Order.objects.filter(
        order_status='completed'
    ).count()
    
    # التركيبات المجدولة اليوم
    today = timezone.now().date()
    today_installations = InstallationSchedule.objects.filter(
        scheduled_date=today
    ).select_related('order', 'order__customer', 'team')
    
    # التركيبات القادمة
    upcoming_installations = InstallationSchedule.objects.filter(
        scheduled_date__gt=today
    ).select_related('order', 'order__customer', 'team')[:5]
    
    # الطلبات الجديدة (آخر 7 أيام)
    recent_orders = Order.objects.filter(
        created_at__gte=timezone.now() - timezone.timedelta(days=7),
        order_status='completed'
    ).select_related('customer')[:10]
    
    # الطلبات التي تحتاج جدولة
    orders_needing_scheduling = Order.objects.filter(
        order_status='completed',
        installationschedule__isnull=True
    ).select_related('customer')[:10]
    
    # إحصائيات الفرق
    teams_stats = InstallationTeam.objects.annotate(
        installations_count=Count('installationschedule')
    ).filter(is_active=True)
    
    context = {
        'total_installations': total_installations,
        'completed_installations': completed_installations,
        'pending_installations': pending_installations,
        'in_progress_installations': in_progress_installations,
        'scheduled_installations': InstallationSchedule.objects.filter(status='scheduled').count(),
        'orders_ready_for_installation': orders_ready_for_installation,
        'ready_for_installation_orders': orders_ready_for_installation,
        'orders_with_debt': orders_with_debt,
        'ready_with_debt': orders_with_debt,
        'orders_in_manufacturing': orders_in_manufacturing,
        'orders_completed_in_factory': orders_completed_in_factory,
        'scheduled_orders': InstallationSchedule.objects.filter(status='scheduled').count(),
        'today_installations': today_installations,
        'upcoming_installations': upcoming_installations,
        'recent_orders': recent_orders,
        'orders_needing_scheduling': orders_needing_scheduling,
        'teams_stats': teams_stats,
        # إحصائيات التعديلات
        'total_modifications': total_modifications,
        'pending_modifications': pending_modifications,
        'in_progress_modifications': in_progress_modifications,
        'completed_modifications': completed_modifications,
    }
    
    return render(request, 'installations/dashboard.html', context)


@login_required
def change_installation_status(request, installation_id):
    """تغيير حالة التركيب"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    if request.method == 'POST':
        form = InstallationStatusForm(request.POST, instance=installation)
        if form.is_valid():
            old_status = installation.status
            installation = form.save()
            
            # إذا تم تغيير الحالة إلى مكتمل، تحديث حالة الطلب
            if installation.status == 'completed' and old_status != 'completed':
                installation.order.order_status = 'completed'
                installation.order.save()
                messages.success(request, 'تم إكمال التركيب بنجاح')
            else:
                messages.success(request, 'تم تحديث حالة التركيب بنجاح')
            
            return redirect('installations:installation_detail', installation_id=installation.id)
    else:
        form = InstallationStatusForm(instance=installation)
    
    context = {
        'form': form,
        'installation': installation,
        'title': 'تغيير حالة التركيب'
    }
    
    return render(request, 'installations/change_status.html', context)


@login_required
def create_modification_request(request, installation_id):
    """إنشاء طلب تعديل"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    if request.method == 'POST':
        form = ModificationRequestForm(request.POST)
        if form.is_valid():
            modification_request = form.save(commit=False)
            modification_request.installation = installation
            modification_request.customer = installation.order.customer
            modification_request.save()
            
            # تحديث حالة التركيب إلى يحتاج تعديل
            installation.status = 'modification_required'
            installation.save()
            
            messages.success(request, 'تم إنشاء طلب التعديل بنجاح')
            return redirect('installations:modification_detail', modification_id=modification_request.id)
    else:
        form = ModificationRequestForm()
    
    context = {
        'form': form,
        'installation': installation,
        'title': 'إنشاء طلب تعديل'
    }
    
    return render(request, 'installations/create_modification.html', context)


@login_required
def modification_detail(request, modification_id):
    """تفاصيل طلب التعديل"""
    modification_request = get_object_or_404(ModificationRequest, id=modification_id)
    images = ModificationImage.objects.filter(modification=modification_request)
    
    context = {
        'modification_request': modification_request,
        'images': images,
        'title': 'تفاصيل طلب التعديل'
    }
    
    return render(request, 'installations/modification_detail.html', context)


@login_required
def upload_modification_images(request, modification_id):
    """رفع صور التعديل"""
    modification_request = get_object_or_404(ModificationRequest, id=modification_id)
    
    if request.method == 'POST':
        form = ModificationImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.modification = modification_request
            image.save()
            messages.success(request, 'تم رفع الصورة بنجاح')
            return redirect('installations:modification_detail', modification_id=modification_request.id)
    else:
        form = ModificationImageForm()
    
    context = {
        'form': form,
        'modification_request': modification_request,
        'title': 'رفع صور التعديل'
    }
    
    return render(request, 'installations/upload_images.html', context)


@login_required
def create_manufacturing_order(request, modification_id):
    """إنشاء أمر تصنيع للتعديل"""
    modification_request = get_object_or_404(ModificationRequest, id=modification_id)
    
    if request.method == 'POST':
        form = ManufacturingOrderForm(request.POST)
        if form.is_valid():
            manufacturing_order = form.save(commit=False)
            manufacturing_order.modification_request = modification_request
            manufacturing_order.order_type = 'modification'
            manufacturing_order.save()
            
            # تحديث حالة طلب التعديل
            modification_request.installation.status = 'modification_in_progress'
            modification_request.installation.save()
            
            messages.success(request, 'تم إنشاء أمر التصنيع بنجاح')
            return redirect('installations:manufacturing_order_detail', order_id=manufacturing_order.id)
    else:
        form = ManufacturingOrderForm()
    
    context = {
        'form': form,
        'modification_request': modification_request,
        'title': 'إنشاء أمر تصنيع للتعديل'
    }
    
    return render(request, 'installations/create_manufacturing_order.html', context)


@login_required
def manufacturing_order_detail(request, order_id):
    """تفاصيل أمر التصنيع"""
    manufacturing_order = get_object_or_404(ManufacturingOrder, id=order_id)
    
    context = {
        'manufacturing_order': manufacturing_order,
        'title': 'تفاصيل أمر التصنيع'
    }
    
    return render(request, 'installations/manufacturing_order_detail.html', context)


@login_required
def complete_manufacturing_order(request, order_id):
    """إكمال أمر التصنيع"""
    manufacturing_order = get_object_or_404(ManufacturingOrder, id=order_id)
    
    if request.method == 'POST':
        form = ModificationReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.manufacturing_order = manufacturing_order
            report.modification_request = manufacturing_order.modification_request
            report.created_by = request.user
            report.save()
            
            # تحديث حالة أمر التصنيع
            manufacturing_order.status = 'completed'
            manufacturing_order.actual_completion_date = timezone.now()
            manufacturing_order.save()
            
            # تحديث حالة التركيب
            installation = manufacturing_order.modification_request.installation
            installation.status = 'modification_completed'
            installation.save()
            
            messages.success(request, 'تم إكمال أمر التصنيع بنجاح')
            return redirect('installations:manufacturing_order_detail', order_id=manufacturing_order.id)
    else:
        form = ModificationReportForm()
    
    context = {
        'form': form,
        'manufacturing_order': manufacturing_order,
        'title': 'إكمال أمر التصنيع'
    }
    
    return render(request, 'installations/complete_manufacturing_order.html', context)


@login_required
def modification_requests_list(request):
    """قائمة طلبات التعديل"""
    modifications = ModificationRequest.objects.select_related(
        'installation', 'installation__order', 'customer'
    ).order_by('-created_at')
    
    # فلترة
    status_filter = request.GET.get('status')
    if status_filter:
        modifications = modifications.filter(installation__status=status_filter)
    
    priority_filter = request.GET.get('priority')
    if priority_filter:
        modifications = modifications.filter(priority=priority_filter)
    
    # ترقيم الصفحات
    paginator = Paginator(modifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'title': 'طلبات التعديل'
    }
    
    return render(request, 'installations/modification_requests_list.html', context)


@login_required
def manufacturing_orders_list(request):
    """قائمة أوامر التصنيع للتعديلات"""
    orders = ManufacturingOrder.objects.select_related(
        'modification_request', 'modification_request__installation',
        'modification_request__installation__order', 'assigned_to'
    ).filter(order_type='modification').order_by('-created_at')
    
    # فلترة
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # ترقيم الصفحات
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'title': 'أوامر التصنيع للتعديلات'
    }
    
    return render(request, 'installations/manufacturing_orders_list.html', context)


@login_required
def installation_list(request):
    """قائمة التركيبات"""
    installations = InstallationSchedule.objects.select_related(
        'order', 'order__customer', 'team'
    ).order_by('-created_at')
    
    # تطبيق الفلاتر
    filter_form = InstallationFilterForm(request.GET)
    if filter_form.is_valid():
        status = filter_form.cleaned_data.get('status')
        team = filter_form.cleaned_data.get('team')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        search = filter_form.cleaned_data.get('search')
        
        if status:
            installations = installations.filter(status=status)
        if team:
            installations = installations.filter(team=team)
        if date_from:
            installations = installations.filter(scheduled_date__gte=date_from)
        if date_to:
            installations = installations.filter(scheduled_date__lte=date_to)
        if search:
            installations = installations.filter(
                Q(order__order_number__icontains=search) |
                Q(order__customer__name__icontains=search)
            )
    
    # ترقيم الصفحات
    paginator = Paginator(installations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'installations': page_obj,
    }
    
    return render(request, 'installations/installation_list.html', context)


@login_required
def installation_detail(request, installation_id):
    """تفاصيل التركيب"""
    installation = get_object_or_404(
        InstallationSchedule.objects.select_related('order', 'order__customer', 'team'),
        id=installation_id
    )
    
    # الحصول على المدفوعات والتقارير
    payments = InstallationPayment.objects.filter(installation=installation)
    # تصحيح العلاقة مع ModificationReport
    modification_reports = ModificationReport.objects.filter(
        modification_request__installation=installation
    )
    receipt_memo = ReceiptMemo.objects.filter(installation=installation).first()
    
    context = {
        'installation': installation,
        'payments': payments,
        'modification_reports': modification_reports,
        'receipt_memo': receipt_memo,
    }
    
    return render(request, 'installations/installation_detail.html', context)


@login_required
def schedule_installation(request, installation_id):
    """جدولة تركيب"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    if request.method == 'POST':
        form = InstallationScheduleForm(request.POST, instance=installation)
        if form.is_valid():
            installation = form.save(commit=False)
            installation.status = 'scheduled'
            installation.save()
            messages.success(request, _('تم جدولة التركيب بنجاح'))
            return redirect('installations:installation_detail', installation_id=installation.id)
    else:
        form = InstallationScheduleForm(instance=installation)
    
    context = {
        'form': form,
        'installation': installation,
    }
    
    return render(request, 'installations/schedule_installation.html', context)


@login_required
def quick_schedule_installation(request, order_id):
    """جدولة سريعة للتركيب من الطلب"""
    
    # الحصول على الطلب من قاعدة البيانات
    order = get_object_or_404(Order, id=order_id)
    
    # التحقق من عدم وجود جدولة سابقة
    if InstallationSchedule.objects.filter(order=order).exists():
        messages.warning(request, _('يوجد جدولة تركيب سابقة لهذا الطلب'))
        return redirect('installations:dashboard')
    
    if request.method == 'POST':
        form = QuickScheduleForm(request.POST)
        if form.is_valid():
            installation = form.save(commit=False)
            installation.order = order
            installation.status = 'scheduled'
            installation.save()
            messages.success(request, _('تم جدولة التركيب بنجاح'))
            return redirect('installations:dashboard')
    else:
        # تعيين قيم افتراضية
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        default_time = timezone.datetime.strptime('09:00', '%H:%M').time()
        form = QuickScheduleForm(initial={
            'scheduled_date': tomorrow,
            'scheduled_time': default_time
        })
    
    context = {
        'form': form,
        'order': order,
    }
    
    return render(request, 'installations/quick_schedule_installation.html', context)


@login_required
@csrf_exempt
def update_status(request, installation_id):
    """تحديث حالة التركيب"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(InstallationSchedule.STATUS_CHOICES):
            installation.status = new_status
            installation.save()
            messages.success(request, _('تم تحديث حالة التركيب بنجاح'))
            return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@login_required
def daily_schedule(request):
    """الجدول اليومي"""
    if request.method == 'POST':
        form = DailyScheduleForm(request.POST)
    else:
        form = DailyScheduleForm()
    
    installations = []
    if form.is_valid():
        date = form.cleaned_data.get('date')
        team = form.cleaned_data.get('team')
        
        installations = InstallationSchedule.objects.filter(
            scheduled_date=date,
            status__in=['scheduled', 'in_progress']
        ).select_related('order', 'order__customer', 'team')
        
        if team:
            installations = installations.filter(team=team)
        
        installations = installations.order_by('scheduled_time')
    
    context = {
        'form': form,
        'installations': installations,
    }
    
    return render(request, 'installations/daily_schedule.html', context)


@login_required
def print_daily_schedule(request):
    """طباعة الجدول اليومي"""
    date = request.GET.get('date', timezone.now().date())
    team_id = request.GET.get('team')
    
    installations = InstallationSchedule.objects.filter(
        scheduled_date=date,
        status__in=['scheduled', 'in_progress']
    ).select_related('order', 'order__customer', 'team')
    
    if team_id:
        installations = installations.filter(team_id=team_id)
    
    installations = installations.order_by('scheduled_time')
    
    context = {
        'installations': installations,
        'date': date,
    }
    
    return render(request, 'installations/print_daily_schedule.html', context)


@login_required
def add_payment(request, installation_id):
    """إضافة دفعة"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    if request.method == 'POST':
        form = InstallationPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.installation = installation
            payment.save()
            messages.success(request, _('تم إضافة الدفعة بنجاح'))
            return redirect('installations:installation_detail', installation_id=installation.id)
    else:
        form = InstallationPaymentForm()
    
    context = {
        'form': form,
        'installation': installation,
    }
    
    return render(request, 'installations/add_payment.html', context)


@login_required
def add_modification_report(request, installation_id):
    """إضافة تقرير تعديل"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    if request.method == 'POST':
        form = ModificationReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.installation = installation
            report.save()
            messages.success(request, _('تم إضافة تقرير التعديل بنجاح'))
            return redirect('installations:installation_detail', installation_id=installation.id)
    else:
        form = ModificationReportForm()
    
    context = {
        'form': form,
        'installation': installation,
    }
    
    return render(request, 'installations/add_modification_report.html', context)


@login_required
def add_receipt_memo(request, installation_id):
    """إضافة مذكرة استلام"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    if request.method == 'POST':
        form = ReceiptMemoForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.installation = installation
            receipt.save()
            messages.success(request, _('تم إضافة مذكرة الاستلام بنجاح'))
            return redirect('installations:installation_detail', installation_id=installation.id)
    else:
        form = ReceiptMemoForm()
    
    context = {
        'form': form,
        'installation': installation,
    }
    
    return render(request, 'installations/add_receipt_memo.html', context)


@login_required
def complete_installation(request, installation_id):
    """إكمال التركيب"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    if request.method == 'POST':
        installation.status = 'completed'
        installation.save()
        
        # إنشاء أرشيف
        InstallationArchive.objects.create(
            installation=installation,
            archived_by=request.user
        )
        
        messages.success(request, _('تم إكمال التركيب بنجاح'))
        return redirect('installations:installation_detail', installation_id=installation.id)
    
    context = {
        'installation': installation,
    }
    
    return render(request, 'installations/complete_installation.html', context)


@login_required
def team_management(request):
    """إدارة الفرق"""
    teams = InstallationTeam.objects.all().prefetch_related('technicians', 'driver')
    technicians = Technician.objects.filter(is_active=True)
    drivers = Driver.objects.filter(is_active=True)
    
    context = {
        'teams': teams,
        'technicians': technicians,
        'drivers': drivers,
    }
    
    return render(request, 'installations/team_management.html', context)


@login_required
def add_team(request):
    """إضافة فريق"""
    if request.method == 'POST':
        form = InstallationTeamForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة الفريق بنجاح'))
            return redirect('installations:team_management')
    else:
        form = InstallationTeamForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'installations/add_team.html', context)


@login_required
def add_technician(request):
    """إضافة فني"""
    if request.method == 'POST':
        form = TechnicianForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة الفني بنجاح'))
            return redirect('installations:team_management')
    else:
        form = TechnicianForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'installations/add_technician.html', context)


@login_required
def add_driver(request):
    """إضافة سائق"""
    if request.method == 'POST':
        form = DriverForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم إضافة السائق بنجاح'))
            return redirect('installations:team_management')
    else:
        form = DriverForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'installations/add_driver.html', context)


@login_required
def archive_list(request):
    """قائمة الأرشيف"""
    archives = InstallationArchive.objects.select_related(
        'installation', 'installation__order', 'installation__order__customer'
    ).order_by('-completion_date')
    
    # ترقيم الصفحات
    paginator = Paginator(archives, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'archives': page_obj,
    }
    
    return render(request, 'installations/archive_list.html', context)


# API Views
@csrf_exempt
@require_http_methods(["POST"])
def receive_completed_order(request):
    """استقبال الطلبات المكتملة من قسم التصنيع"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        # التحقق من وجود الطلب
        
        order = get_object_or_404(Order, id=order_id)
        
        # التحقق من عدم وجود جدولة سابقة
        if InstallationSchedule.objects.filter(order=order).exists():
            return JsonResponse({
                'success': False,
                'error': 'يوجد جدولة تركيب سابقة لهذا الطلب'
            }, status=400)
        
        # إنشاء جدولة تركيب جديدة مع تاريخ افتراضي
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        default_time = timezone.datetime.strptime('09:00', '%H:%M').time()
        
        installation = InstallationSchedule.objects.create(
            order=order,
            scheduled_date=tomorrow,
            scheduled_time=default_time,
            status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'installation_id': installation.id,
            'message': 'تم استقبال الطلب بنجاح'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def installation_stats_api(request):
    """API لإحصائيات التركيبات"""
    total = InstallationSchedule.objects.count()
    completed = InstallationSchedule.objects.filter(status='completed').count()
    pending = InstallationSchedule.objects.filter(status='pending').count()
    in_progress = InstallationSchedule.objects.filter(status='in_progress').count()
    
    return JsonResponse({
        'total': total,
        'completed': completed,
        'pending': pending,
        'in_progress': in_progress
    })


# إدارة مديونية العملاء
@login_required
def manage_customer_debt(request, order_id):
    """إدارة مديونية العميل"""
    order = get_object_or_404(Order, id=order_id)
    debt, created = CustomerDebt.objects.get_or_create(
        order=order,
        defaults={
            'customer': order.customer,
            'debt_amount': order.remaining_amount
        }
    )
    
    if request.method == 'POST':
        form = CustomerDebtForm(request.POST, instance=debt)
        if form.is_valid():
            debt = form.save()
            messages.success(request, 'تم تحديث مديونية العميل بنجاح')
            return redirect('installations:dashboard')
    else:
        form = CustomerDebtForm(instance=debt)
    
    context = {
        'form': form,
        'order': order,
        'debt': debt,
        'title': 'إدارة مديونية العميل'
    }
    
    return render(request, 'installations/manage_debt.html', context)


@login_required
def pay_debt(request, debt_id):
    """دفع المديونية"""
    debt = get_object_or_404(CustomerDebt, id=debt_id)
    
    if request.method == 'POST':
        form = CustomerDebtForm(request.POST, instance=debt)
        if form.is_valid():
            debt = form.save()
            if debt.is_paid:
                debt.payment_date = timezone.now()
                debt.save()
                messages.success(request, 'تم تسجيل الدفع بنجاح')
            return redirect('installations:dashboard')
    else:
        form = CustomerDebtForm(instance=debt)
    
    context = {
        'form': form,
        'debt': debt,
        'title': 'دفع المديونية'
    }
    
    return render(request, 'installations/pay_debt.html', context)


@login_required
def debt_list(request):
    """قائمة مديونيات العملاء"""
    debts = CustomerDebt.objects.select_related('customer', 'order').order_by('-created_at')
    
    # تطبيق الفلاتر
    status_filter = request.GET.get('status')
    if status_filter == 'paid':
        debts = debts.filter(is_paid=True)
    elif status_filter == 'unpaid':
        debts = debts.filter(is_paid=False)
    
    # ترقيم الصفحات
    paginator = Paginator(debts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'debts': page_obj,
    }
    
    return render(request, 'installations/debt_list.html', context)


# API Views للطلبات
@login_required
def orders_modal(request):
    """عرض الطلبات في modal"""
    order_type = request.GET.get('type', 'total')
    
    if order_type == 'total':
        orders = Order.objects.filter(
            installationschedule__isnull=False
        ).select_related('customer', 'branch', 'salesperson')
    elif order_type == 'ready':
        orders = Order.objects.filter(
            order_status='completed',
            installationschedule__isnull=True
        ).select_related('customer', 'branch', 'salesperson')
    elif order_type == 'manufacturing':
        orders = Order.objects.filter(
            order_status='in_progress'
        ).select_related('customer', 'branch', 'salesperson')
    elif order_type == 'completed':
        orders = Order.objects.filter(
            order_status='completed'
        ).select_related('customer', 'branch', 'salesperson')
    elif order_type == 'scheduled':
        # تحويل InstallationSchedule إلى Order objects للتوافق مع template
        installations = InstallationSchedule.objects.filter(
            status='scheduled'
        ).select_related('order', 'order__customer', 'order__branch', 'order__salesperson')
        orders = [installation.order for installation in installations]
    elif order_type == 'in_progress':
        # جلب التركيبات قيد التنفيذ ثم استخراج الطلبات الفريدة
        installations = InstallationSchedule.objects.filter(
            status='in_progress'
        ).select_related('order', 'order__customer', 'order__branch', 'order__salesperson')
        orders = list({installation.order for installation in installations})
    elif order_type == 'debt':
        orders = Order.objects.filter(
            order_status='completed',
            installationschedule__isnull=True
        ).filter(
            total_amount__gt=F('paid_amount')
        ).select_related('customer', 'branch', 'salesperson')
    elif order_type == 'modifications':
        # جلب التعديلات مع الطلبات المرتبطة
        modifications = ModificationRequest.objects.select_related(
            'installation', 'installation__order', 'installation__order__customer',
            'installation__order__branch', 'installation__order__salesperson'
        ).order_by('-created_at')
        orders = [mod.installation.order for mod in modifications]
    else:
        orders = Order.objects.none()
    
    context = {
        'orders': orders,
        'currency_symbol': 'ج.م'
    }
    
    return render(request, 'installations/orders_modal.html', context)


@login_required
def installation_analytics(request):
    """تحليل التركيبات الشهري"""
    from datetime import datetime, timedelta
    from django.db.models import Count, Q
    
    # تحديد الفترة الزمنية
    months_back = int(request.GET.get('months', 6))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=months_back * 30)
    
    # جلب البيانات الشهرية
    analytics_data = []
    current_date = start_date
    
    while current_date <= end_date:
        month_start = current_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # إحصائيات التركيبات
        installations = InstallationSchedule.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        )
        
        total_installations = installations.count()
        completed_installations = installations.filter(status='completed').count()
        pending_installations = installations.filter(status='pending').count()
        in_progress_installations = installations.filter(status='in_progress').count()
        
        # إحصائيات العملاء
        customers = Order.objects.filter(
            installationschedule__created_at__date__gte=month_start,
            installationschedule__created_at__date__lte=month_end
        ).values('customer').distinct().count()
        
        new_customers = Order.objects.filter(
            installationschedule__created_at__date__gte=month_start,
            installationschedule__created_at__date__lte=month_end
        ).values('customer').distinct().count()
        
        # إحصائيات التعديلات
        modifications = ModificationRequest.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        ).count()
        
        # حساب النسب
        completion_rate = (completed_installations / total_installations * 100) if total_installations > 0 else 0
        modification_rate = (modifications / total_installations * 100) if total_installations > 0 else 0
        
        analytics_data.append({
            'month': month_start,
            'total_installations': total_installations,
            'completed_installations': completed_installations,
            'pending_installations': pending_installations,
            'in_progress_installations': in_progress_installations,
            'total_customers': customers,
            'new_customers': new_customers,
            'total_modifications': modifications,
            'completion_rate': round(completion_rate, 2),
            'modification_rate': round(modification_rate, 2),
        })
        
        current_date = (month_start + timedelta(days=32)).replace(day=1)
    
    # إحصائيات إضافية
    total_stats = {
        'total_installations': sum(d['total_installations'] for d in analytics_data),
        'total_completed': sum(d['completed_installations'] for d in analytics_data),
        'total_modifications': sum(d['total_modifications'] for d in analytics_data),
        'avg_completion_rate': sum(d['completion_rate'] for d in analytics_data) / len(analytics_data) if analytics_data else 0,
        'avg_modification_rate': sum(d['modification_rate'] for d in analytics_data) / len(analytics_data) if analytics_data else 0,
    }
    
    context = {
        'analytics_data': analytics_data,
        'total_stats': total_stats,
        'months_back': months_back,
    }
    
    return render(request, 'installations/analytics.html', context)


@login_required
def modification_error_analysis(request):
    """تحليل أخطاء التعديلات"""
    error_analyses = ModificationErrorAnalysis.objects.select_related(
        'modification_request', 'modification_request__installation', 
        'modification_request__installation__order', 'error_type'
    ).order_by('-created_at')
    
    # إحصائيات الأخطاء حسب نوع السبب
    error_stats = {}
    error_types = ModificationErrorType.objects.filter(is_active=True)
    for error_type in error_types:
        error_stats[error_type.name] = error_analyses.filter(error_type=error_type).count()
    
    # إجمالي التكاليف والوقت
    total_cost_impact = error_analyses.aggregate(total=models.Sum('cost_impact'))['total'] or 0
    total_time_impact = error_analyses.aggregate(total=models.Sum('time_impact_hours'))['total'] or 0
    
    # ترقيم الصفحات
    paginator = Paginator(error_analyses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # تحويل error_types إلى التنسيق المطلوب للقالب
    error_types_choices = [(error_type.name, error_type.name) for error_type in error_types]
    
    context = {
        'error_analyses': page_obj,
        'error_stats': error_stats,
        'total_cost_impact': total_cost_impact,
        'total_time_impact': total_time_impact,
        'error_types': error_types_choices,
    }
    
    return render(request, 'installations/error_analysis.html', context)


@login_required
def add_error_analysis(request, modification_id):
    """إضافة تحليل خطأ"""
    modification_request = get_object_or_404(ModificationRequest, id=modification_id)
    
    if request.method == 'POST':
        form = ModificationErrorAnalysisForm(request.POST)
        if form.is_valid():
            error_analysis = form.save(commit=False)
            error_analysis.modification_request = modification_request
            error_analysis.save()
            messages.success(request, 'تم إضافة تحليل الخطأ بنجاح')
            return redirect('installations:modification_error_analysis')
    else:
        form = ModificationErrorAnalysisForm()
    
    context = {
        'form': form,
        'modification_request': modification_request,
        'title': 'إضافة تحليل خطأ'
    }
    
    return render(request, 'installations/add_error_analysis.html', context)


@login_required
def edit_schedule(request, installation_id):
    """تعديل جدولة التركيب"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    if request.method == 'POST':
        form = InstallationScheduleForm(request.POST, instance=installation)
        if form.is_valid():
            installation = form.save()
            messages.success(request, _('تم تعديل جدولة التركيب بنجاح'))
            return redirect('installations:installation_detail', installation_id=installation.id)
    else:
        form = InstallationScheduleForm(instance=installation)
    
    context = {
        'form': form,
        'installation': installation,
        'title': 'تعديل جدولة التركيب'
    }
    
    return render(request, 'installations/edit_schedule.html', context)
