from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django import forms

from .models import ProductionLine, ProductionOrder, ProductionStage, ProductionIssue
from .forms import (
    ProductionLineForm, 
    ProductionOrderForm, 
    ProductionStageForm,
    ProductionIssueForm
)
from accounts.utils import send_notification

@login_required
def factory_dashboard(request):
    """
    لوحة تحكم المصنع المتقدمة
    """
    # إحصائيات عامة
    total_production_lines = ProductionLine.objects.count()
    active_production_lines = ProductionLine.objects.filter(is_active=True).count()

    # طلبات الإنتاج
    total_orders = ProductionOrder.objects.count()
    pending_orders = ProductionOrder.objects.filter(status='pending').count()
    in_progress_orders = ProductionOrder.objects.filter(status='in_progress').count()
    completed_orders = ProductionOrder.objects.filter(status='completed').count()
    stalled_orders = ProductionOrder.objects.filter(status='stalled').count()

    # طلبات اليوم
    today = timezone.now().date()
    today_orders = ProductionOrder.objects.filter(
        created_at__date=today
    ).count()

    # طلبات هذا الأسبوع
    week_start = today - timedelta(days=today.weekday())
    week_orders = ProductionOrder.objects.filter(
        created_at__date__gte=week_start
    ).count()

    # المشاكل النشطة
    active_issues = ProductionIssue.objects.filter(
        resolved=False
    ).count()

    # أحدث الطلبات
    recent_orders = ProductionOrder.objects.select_related(
        'order', 'production_line'
    ).order_by('-created_at')[:10]

    # أحدث المشاكل
    recent_issues = ProductionIssue.objects.select_related(
        'production_order', 'reported_by'
    ).order_by('-reported_at')[:5]

    # خطوط الإنتاج النشطة
    active_lines = ProductionLine.objects.filter(
        is_active=True
    ).annotate(
        active_orders_count=Count('production_orders', filter=Q(production_orders__status='in_progress'))
    )

    # إحصائيات الأداء
    completion_rate = 0
    if total_orders > 0:
        completion_rate = (completed_orders / total_orders) * 100

    context = {
        'title': 'لوحة تحكم المصنع',
        'total_production_lines': total_production_lines,
        'active_production_lines': active_production_lines,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'in_progress_orders': in_progress_orders,
        'completed_orders': completed_orders,
        'stalled_orders': stalled_orders,
        'today_orders': today_orders,
        'week_orders': week_orders,
        'active_issues': active_issues,
        'recent_orders': recent_orders,
        'recent_issues': recent_issues,
        'active_lines': active_lines,
        'completion_rate': round(completion_rate, 1),
    }

    return render(request, 'factory/dashboard.html', context)

@login_required
def factory_list(request):
    """
    View for displaying the factory dashboard
    """
    # Get active production lines
    production_lines = ProductionLine.objects.all()
    
    # Get current production orders
    production_orders = ProductionOrder.objects.select_related(
        'order', 'production_line'
    ).exclude(
        status__in=['completed', 'cancelled']
    ).order_by('estimated_completion')[:10]
    
    # Get stalled production orders
    stalled_orders = ProductionOrder.objects.filter(
        status='stalled'
    ).select_related('order', 'production_line').order_by('-created_at')[:5]
    
    # Get recent issues
    recent_issues = ProductionIssue.objects.select_related(
        'production_order', 'reported_by'
    ).order_by('-reported_at')[:5]
    
    context = {
        'title': 'إدارة المصنع',
        'production_lines': production_lines,
        'production_orders': production_orders,
        'stalled_orders': stalled_orders,
        'recent_issues': recent_issues,
    }
    return render(request, 'factory/factory_list.html', context)

# Production Line Views
@login_required
def production_line_list(request):
    """
    View for displaying the list of production lines
    """
    search_query = request.GET.get('search', '')
    
    # Filter production lines based on search query
    if search_query:
        production_lines = ProductionLine.objects.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    else:
        production_lines = ProductionLine.objects.all()
    
    # Pagination
    paginator = Paginator(production_lines, 10)  # Show 10 production lines per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_production_lines': production_lines.count(),
        'title': 'خطوط الإنتاج',
    }
    
    return render(request, 'factory/production_line_list.html', context)

@login_required
def production_line_detail(request, pk):
    """
    View for displaying production line details
    """
    production_line = get_object_or_404(ProductionLine, pk=pk)
    production_orders = production_line.production_orders.all().order_by('-start_date')
    
    context = {
        'production_line': production_line,
        'production_orders': production_orders,
        'title': f'خط الإنتاج: {production_line.name}',
    }
    
    return render(request, 'factory/production_line_detail.html', context)

@login_required
def production_line_create(request):
    """
    View for creating a new production line
    """
    if request.method == 'POST':
        form = ProductionLineForm(request.POST)
        if form.is_valid():
            production_line = form.save()
            messages.success(request, 'تم إضافة خط الإنتاج بنجاح.')
            return redirect('factory:production_line_detail', pk=production_line.pk)
    else:
        form = ProductionLineForm()
    
    context = {
        'form': form,
        'title': 'إضافة خط إنتاج جديد',
    }
    
    return render(request, 'factory/production_line_form.html', context)

@login_required
def production_line_update(request, pk):
    """
    View for updating an existing production line
    """
    production_line = get_object_or_404(ProductionLine, pk=pk)
    
    if request.method == 'POST':
        form = ProductionLineForm(request.POST, instance=production_line)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث خط الإنتاج بنجاح.')
            return redirect('factory:production_line_detail', pk=production_line.pk)
    else:
        form = ProductionLineForm(instance=production_line)
    
    context = {
        'form': form,
        'production_line': production_line,
        'title': f'تعديل خط الإنتاج: {production_line.name}',
    }
    
    return render(request, 'factory/production_line_form.html', context)

@login_required
def production_line_delete(request, pk):
    """
    View for deleting a production line
    """
    production_line = get_object_or_404(ProductionLine, pk=pk)
    
    if request.method == 'POST':
        production_line.delete()
        messages.success(request, 'تم حذف خط الإنتاج بنجاح.')
        return redirect('factory:production_line_list')
    
    context = {
        'production_line': production_line,
        'title': f'حذف خط الإنتاج: {production_line.name}',
    }
    
    return render(request, 'factory/production_line_confirm_delete.html', context)

# Production Order Views
@login_required
def production_order_list(request):
    """
    View for displaying the list of production orders
    """
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    production_orders = ProductionOrder.objects.select_related('order', 'production_line')
    
    # Apply filters
    if search_query:
        production_orders = production_orders.filter(
            Q(order__order_number__icontains=search_query) |
            Q(production_line__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    if status_filter:
        production_orders = production_orders.filter(status=status_filter)
    
    # Order by created_at
    production_orders = production_orders.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(production_orders, 10)  # Show 10 production orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_production_orders': production_orders.count(),
        'title': 'أوامر الإنتاج',
        'status_choices': ProductionOrder.STATUS_CHOICES,
    }
    
    return render(request, 'factory/production_order_list.html', context)

@login_required
def production_order_detail(request, pk):
    """
    View for displaying production order details
    """
    production_order = get_object_or_404(ProductionOrder, pk=pk)

    # الحصول على عناصر الطلب
    order_items = []
    if production_order.order:
        try:
            order_items = production_order.order.items.all().select_related('product')
        except:
            order_items = []

    # الحصول على المراحل والمشاكل (إذا كانت موجودة)
    stages = []
    issues = []
    try:
        if hasattr(production_order, 'stages'):
            stages = production_order.stages.all().order_by('start_date')
        if hasattr(production_order, 'issues'):
            issues = production_order.issues.all().order_by('-reported_at')
    except:
        pass

    context = {
        'production_order': production_order,
        'order_items': order_items,
        'stages': stages,
        'issues': issues,
        'title': f'أمر الإنتاج: {production_order.order.order_number}',
    }
    
    return render(request, 'factory/production_order_detail.html', context)

@login_required
def production_order_create(request):
    """
    View for creating a new production order
    """
    if request.method == 'POST':
        form = ProductionOrderForm(request.POST)
        if form.is_valid():
            production_order = form.save(commit=False)
            production_order.created_by = request.user
            production_order.save()
            messages.success(request, 'تم إضافة أمر الإنتاج بنجاح.')
            return redirect('factory:production_order_detail', pk=production_order.pk)
    else:
        form = ProductionOrderForm()
    
    context = {
        'form': form,
        'title': 'إضافة أمر إنتاج جديد',
    }
    
    return render(request, 'factory/production_order_form.html', context)

@login_required
def production_order_update(request, pk):
    """
    View for updating an existing production order
    """
    production_order = get_object_or_404(ProductionOrder, pk=pk)
    old_status = production_order.status
    
    if request.method == 'POST':
        form = ProductionOrderForm(request.POST, instance=production_order)
        if form.is_valid():
            production_order = form.save()
            
            # If status changed from stalled to something else, notify
            if old_status == 'stalled' and production_order.status != 'stalled':
                # Send notification to the branch
                if production_order.order.branch:
                    send_notification(
                        title=f'استئناف أمر إنتاج #{production_order.id}',
                        message=f'تم استئناف العمل على أمر الإنتاج الخاص بالطلب {production_order.order.order_number} بعد توقف',
                        sender=request.user,
                        sender_department_code='factory',
                        target_department_code='orders',
                        target_branch=production_order.order.branch,
                        priority='medium',
                        related_object=production_order
                    )
            
            messages.success(request, 'تم تحديث أمر الإنتاج بنجاح.')
            return redirect('factory:production_order_detail', pk=production_order.pk)
    else:
        form = ProductionOrderForm(instance=production_order)
    
    context = {
        'form': form,
        'production_order': production_order,
        'title': f'تعديل أمر الإنتاج: {production_order.order.order_number}',
    }
    
    return render(request, 'factory/production_order_form.html', context)

@login_required
def production_order_delete(request, pk):
    """
    View for deleting a production order
    """
    production_order = get_object_or_404(ProductionOrder, pk=pk)
    
    if request.method == 'POST':
        production_order.delete()
        messages.success(request, 'تم حذف أمر الإنتاج بنجاح.')
        return redirect('factory:production_order_list')
    
    context = {
        'production_order': production_order,
        'title': f'حذف أمر الإنتاج: {production_order.order.order_number}',
    }
    
    return render(request, 'factory/production_order_confirm_delete.html', context)

# Production Stage Views
@login_required
def production_stage_create(request, order_pk):
    """
    View for creating a new production stage for a specific order
    """
    production_order = get_object_or_404(ProductionOrder, pk=order_pk)
    
    if request.method == 'POST':
        form = ProductionStageForm(request.POST)
        if form.is_valid():
            stage = form.save(commit=False)
            stage.production_order = production_order
            stage.save()
            messages.success(request, 'تم إضافة مرحلة الإنتاج بنجاح.')
            return redirect('factory:production_order_detail', pk=production_order.pk)
    else:
        form = ProductionStageForm(initial={'production_order': production_order})
        form.fields['production_order'].widget = forms.HiddenInput()
    
    context = {
        'form': form,
        'production_order': production_order,
        'title': f'إضافة مرحلة إنتاج جديدة لأمر الإنتاج: {production_order.order.order_number}',
    }
    
    return render(request, 'factory/production_stage_form.html', context)

@login_required
def production_stage_update(request, pk):
    """
    View for updating an existing production stage
    """
    stage = get_object_or_404(ProductionStage, pk=pk)
    production_order = stage.production_order
    
    if request.method == 'POST':
        form = ProductionStageForm(request.POST, instance=stage)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث مرحلة الإنتاج بنجاح.')
            return redirect('factory:production_order_detail', pk=production_order.pk)
    else:
        form = ProductionStageForm(instance=stage)
        form.fields['production_order'].widget = forms.HiddenInput()
    
    context = {
        'form': form,
        'stage': stage,
        'production_order': production_order,
        'title': f'تعديل مرحلة الإنتاج: {stage.name}',
    }
    
    return render(request, 'factory/production_stage_form.html', context)

@login_required
def production_stage_delete(request, pk):
    """
    View for deleting a production stage
    """
    stage = get_object_or_404(ProductionStage, pk=pk)
    production_order = stage.production_order
    
    if request.method == 'POST':
        stage.delete()
        messages.success(request, 'تم حذف مرحلة الإنتاج بنجاح.')
        return redirect('factory:production_order_detail', pk=production_order.pk)
    
    context = {
        'stage': stage,
        'production_order': production_order,
        'title': f'حذف مرحلة الإنتاج: {stage.name}',
    }
    
    return render(request, 'factory/production_stage_confirm_delete.html', context)

# Production Issue Views
@login_required
def production_issue_create(request, order_pk):
    """
    View for creating a new production issue for a specific order
    """
    production_order = get_object_or_404(ProductionOrder, pk=order_pk)
    
    if request.method == 'POST':
        form = ProductionIssueForm(request.POST)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.production_order = production_order
            issue.reported_by = request.user
            issue.save()
            
            # Update production order status to stalled
            if production_order.status != 'stalled':
                production_order.status = 'stalled'
                production_order.save()
                
                # Send notification to the branch
                if production_order.order.branch:
                    send_notification(
                        title=f'تعطل أمر إنتاج #{production_order.id}',
                        message=f'تم تعطل أمر الإنتاج الخاص بالطلب {production_order.order.order_number} بسبب مشكلة: {issue.title}',
                        sender=request.user,
                        sender_department_code='factory',
                        target_department_code='orders',
                        target_branch=production_order.order.branch,
                        priority='high',
                        related_object=production_order
                    )
            
            messages.success(request, 'تم تسجيل مشكلة الإنتاج بنجاح.')
            return redirect('factory:production_order_detail', pk=production_order.pk)
    else:
        form = ProductionIssueForm(initial={'production_order': production_order})
        form.fields['production_order'].widget = forms.HiddenInput()
    
    context = {
        'form': form,
        'production_order': production_order,
        'title': f'تسجيل مشكلة إنتاج لأمر الإنتاج: {production_order.order.order_number}',
    }
    
    return render(request, 'factory/production_issue_form.html', context)

@login_required
def production_issue_update(request, pk):
    """
    View for updating an existing production issue
    """
    issue = get_object_or_404(ProductionIssue, pk=pk)
    production_order = issue.production_order
    was_resolved = issue.resolved
    
    if request.method == 'POST':
        form = ProductionIssueForm(request.POST, instance=issue)
        if form.is_valid():
            issue = form.save(commit=False)
            
            # If issue is being marked as resolved
            if not was_resolved and issue.resolved:
                issue.resolved_by = request.user
                issue.resolved_at = timezone.now()
                
                # Check if all issues are resolved
                unresolved_issues = ProductionIssue.objects.filter(
                    production_order=production_order,
                    resolved=False
                ).exclude(pk=issue.pk).count()
                
                # If no more unresolved issues, update production order status
                if unresolved_issues == 0 and production_order.status == 'stalled':
                    production_order.status = 'in_progress'
                    production_order.save()
                    
                    # Send notification to the branch
                    if production_order.order.branch:
                        send_notification(
                            title=f'استئناف أمر إنتاج #{production_order.id}',
                            message=f'تم استئناف العمل على أمر الإنتاج الخاص بالطلب {production_order.order.order_number} بعد حل المشكلة: {issue.title}',
                            sender=request.user,
                            sender_department_code='factory',
                            target_department_code='orders',
                            target_branch=production_order.order.branch,
                            priority='medium',
                            related_object=production_order
                        )
            
            issue.save()
            messages.success(request, 'تم تحديث مشكلة الإنتاج بنجاح.')
            return redirect('factory:production_order_detail', pk=production_order.pk)
    else:
        form = ProductionIssueForm(instance=issue)
        form.fields['production_order'].widget = forms.HiddenInput()
    
    context = {
        'form': form,
        'issue': issue,
        'production_order': production_order,
        'title': f'تعديل مشكلة الإنتاج: {issue.title}',
    }
    
    return render(request, 'factory/production_issue_form.html', context)

@login_required
def production_issue_list(request):
    """
    View for displaying the list of production issues
    """
    search_query = request.GET.get('search', '')
    severity_filter = request.GET.get('severity', '')
    resolved_filter = request.GET.get('resolved', '')
    
    # Base queryset
    issues = ProductionIssue.objects.select_related(
        'production_order', 'reported_by', 'resolved_by'
    )
    
    # Apply filters
    if search_query:
        issues = issues.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(production_order__order__order_number__icontains=search_query)
        )
    
    if severity_filter:
        issues = issues.filter(severity=severity_filter)
    
    if resolved_filter:
        is_resolved = resolved_filter == 'resolved'
        issues = issues.filter(resolved=is_resolved)
    
    # Order by reported_at
    issues = issues.order_by('-reported_at')
    
    # Pagination
    paginator = Paginator(issues, 10)  # Show 10 issues per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'severity_filter': severity_filter,
        'resolved_filter': resolved_filter,
        'total_issues': issues.count(),
        'title': 'مشاكل الإنتاج',
        'severity_choices': ProductionIssue.SEVERITY_CHOICES,
    }
    
    return render(request, 'factory/production_issue_list.html', context)

@login_required
def production_issue_detail(request, pk):
    """
    View for displaying production issue details
    """
    issue = get_object_or_404(
        ProductionIssue.objects.select_related(
            'production_order', 'reported_by', 'resolved_by'
        ),
        pk=pk
    )
    
    context = {
        'issue': issue,
        'title': f'تفاصيل مشكلة الإنتاج: {issue.title}',
    }
    
    return render(request, 'factory/production_issue_detail.html', context)

@login_required
def production_issue_delete(request, pk):
    """
    View for deleting a production issue
    """
    issue = get_object_or_404(ProductionIssue, pk=pk)
    order = issue.production_order

    if request.method == 'POST':
        issue.delete()
        messages.success(request, 'تم حذف المشكلة بنجاح.')
        return redirect('factory:production_order_detail', pk=order.pk)

    context = {
        'issue': issue,
        'order': order,
    }

    return render(request, 'factory/production_issue_confirm_delete.html', context)

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class FactoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'factory/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_lines'] = ProductionLine.objects.count()
        context['total_orders'] = ProductionOrder.objects.count()
        context['pending_orders'] = ProductionOrder.objects.filter(status='pending').count()
        context['recent_orders'] = ProductionOrder.objects.order_by('-created_at')[:10]
        return context
