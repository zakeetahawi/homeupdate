from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.core.serializers import serialize
import json
from datetime import datetime, timedelta

from .models import (
    InstallationSchedule, InstallationTeam, Technician, Driver,
    ModificationReport, ReceiptMemo, InstallationPayment, InstallationArchive
)
from .forms import (
    InstallationScheduleForm, InstallationTeamForm, TechnicianForm, DriverForm,
    ModificationReportForm, ReceiptMemoForm, InstallationPaymentForm,
    InstallationFilterForm, DailyScheduleForm
)


@login_required
def dashboard(request):
    """لوحة تحكم قسم التركيبات"""
    today = timezone.now().date()
    
    # إحصائيات عامة
    total_installations = InstallationSchedule.objects.count()
    pending_installations = InstallationSchedule.objects.filter(status='pending').count()
    scheduled_installations = InstallationSchedule.objects.filter(status='scheduled').count()
    in_progress_installations = InstallationSchedule.objects.filter(status='in_progress').count()
    completed_installations = InstallationSchedule.objects.filter(status='completed').count()
    
    # التركيبات المجدولة اليوم
    today_installations = InstallationSchedule.objects.filter(
        scheduled_date=today,
        status__in=['scheduled', 'in_progress']
    ).order_by('scheduled_time')
    
    # التركيبات القادمة
    upcoming_installations = InstallationSchedule.objects.filter(
        scheduled_date__gt=today,
        status='scheduled'
    ).order_by('scheduled_date', 'scheduled_time')[:10]
    
    # إحصائيات الفرق
    teams_stats = InstallationTeam.objects.filter(is_active=True).annotate(
        installations_count=Count('installationschedule')
    )
    
    context = {
        'total_installations': total_installations,
        'pending_installations': pending_installations,
        'scheduled_installations': scheduled_installations,
        'in_progress_installations': in_progress_installations,
        'completed_installations': completed_installations,
        'today_installations': today_installations,
        'upcoming_installations': upcoming_installations,
        'teams_stats': teams_stats,
    }
    
    return render(request, 'installations/dashboard.html', context)


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
    modification_reports = ModificationReport.objects.filter(installation=installation)
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
        from orders.models import Order
        order = get_object_or_404(Order, id=order_id)
        
        # إنشاء جدولة تركيب جديدة
        installation = InstallationSchedule.objects.create(
            order=order,
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
    today = timezone.now().date()
    
    stats = {
        'total': InstallationSchedule.objects.count(),
        'pending': InstallationSchedule.objects.filter(status='pending').count(),
        'scheduled': InstallationSchedule.objects.filter(status='scheduled').count(),
        'in_progress': InstallationSchedule.objects.filter(status='in_progress').count(),
        'completed': InstallationSchedule.objects.filter(status='completed').count(),
        'today': InstallationSchedule.objects.filter(scheduled_date=today).count(),
    }
    
    return JsonResponse(stats)
