from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, TemplateView
)

from accounts.models import Department
from customers.models import Customer
from orders.models import Order

from .forms import (
    ComplaintForm, ComplaintUpdateForm, ComplaintStatusUpdateForm,
    ComplaintAssignmentForm, ComplaintEscalationForm, ComplaintAttachmentForm,
    ComplaintResolutionForm, ComplaintCustomerRatingForm, ComplaintFilterForm,
    ComplaintBulkActionForm
)
from .models import (
    Complaint, ComplaintType, ComplaintUpdate
)


class ComplaintDashboardView(LoginRequiredMixin, TemplateView):
    """لوحة تحكم الشكاوى"""
    template_name = 'complaints/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # إحصائيات عامة
        total_complaints = Complaint.objects.count()
        new_complaints = Complaint.objects.filter(status='new').count()
        in_progress_complaints = Complaint.objects.filter(status='in_progress').count()
        resolved_complaints = Complaint.objects.filter(status='resolved').count()
        overdue_complaints = Complaint.objects.filter(status='overdue').count()

        # إحصائيات حسب النوع
        complaints_by_type = Complaint.objects.values(
            'complaint_type__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        # إحصائيات حسب الأولوية
        complaints_by_priority = Complaint.objects.values(
            'priority'
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        # إحصائيات حسب المسؤول
        complaints_by_assignee = Complaint.objects.exclude(
            assigned_to__isnull=True
        ).values(
            'assigned_to__first_name', 'assigned_to__last_name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        # الشكاوى الحديثة
        recent_complaints = Complaint.objects.select_related(
            'customer', 'complaint_type', 'assigned_to'
        ).order_by('-created_at')[:10]

        # الشكاوى المتأخرة
        overdue_complaints_list = Complaint.objects.filter(
            deadline__lt=timezone.now(),
            status__in=['new', 'in_progress']
        ).select_related(
            'customer', 'complaint_type', 'assigned_to'
        ).order_by('deadline')[:10]

        # معدل الرضا
        avg_rating = Complaint.objects.filter(
            customer_rating__isnull=False
        ).aggregate(
            avg_rating=Avg('customer_rating')
        )['avg_rating'] or 0

        # إحصائيات الأداء (آخر 30 يوم)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        performance_stats = {
            'new_complaints_30d': Complaint.objects.filter(
                created_at__gte=thirty_days_ago
            ).count(),
            'resolved_complaints_30d': Complaint.objects.filter(
                resolved_at__gte=thirty_days_ago
            ).count(),
            'avg_resolution_time': self.calculate_avg_resolution_time(),
        }

        context.update({
            'total_complaints': total_complaints,
            'new_complaints': new_complaints,
            'in_progress_complaints': in_progress_complaints,
            'resolved_complaints': resolved_complaints,
            'overdue_complaints': overdue_complaints,
            'complaints_by_type': complaints_by_type,
            'complaints_by_priority': complaints_by_priority,
            'complaints_by_assignee': complaints_by_assignee,
            'recent_complaints': recent_complaints,
            'overdue_complaints_list': overdue_complaints_list,
            'avg_rating': round(avg_rating, 2),
            'performance_stats': performance_stats,
        })

        return context

    def calculate_avg_resolution_time(self):
        """حساب متوسط وقت الحل"""
        resolved_complaints = Complaint.objects.filter(
            resolved_at__isnull=False
        )

        total_time = timedelta()
        count = 0

        for complaint in resolved_complaints:
            resolution_time = complaint.resolution_time
            if resolution_time:
                total_time += resolution_time
                count += 1

        if count > 0:
            avg_seconds = total_time.total_seconds() / count
            avg_hours = avg_seconds / 3600
            return round(avg_hours, 1)

        return 0


class ComplaintListView(LoginRequiredMixin, ListView):
    """قائمة الشكاوى"""
    model = Complaint
    template_name = 'complaints/complaint_list.html'
    context_object_name = 'complaints'
    paginate_by = 20

    def get_queryset(self):
        queryset = Complaint.objects.select_related(
            'customer', 'complaint_type', 'assigned_to', 'assigned_department'
        ).order_by('-created_at')

        # تطبيق الفلاتر
        form = ComplaintFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data['status']:
                queryset = queryset.filter(status=form.cleaned_data['status'])

            if form.cleaned_data['priority']:
                queryset = queryset.filter(priority=form.cleaned_data['priority'])

            if form.cleaned_data['complaint_type']:
                queryset = queryset.filter(
                    complaint_type=form.cleaned_data['complaint_type']
                )

            if form.cleaned_data['assigned_to']:
                queryset = queryset.filter(
                    assigned_to=form.cleaned_data['assigned_to']
                )
            
            if form.cleaned_data['date_from']:
                queryset = queryset.filter(
                    created_at__date__gte=form.cleaned_data['date_from']
                )

            if form.cleaned_data['date_to']:
                queryset = queryset.filter(
                    created_at__date__lte=form.cleaned_data['date_to']
                )

            if form.cleaned_data['search']:
                search_term = form.cleaned_data['search']
                search_query = (
                    Q(complaint_number__icontains=search_term) |
                    Q(customer__name__icontains=search_term) |
                    Q(title__icontains=search_term) |
                    Q(description__icontains=search_term)
                )
                queryset = queryset.filter(search_query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ComplaintFilterForm(self.request.GET)
        context['bulk_action_form'] = ComplaintBulkActionForm()
        return context


class ComplaintDetailView(LoginRequiredMixin, DetailView):
    """تفاصيل الشكوى"""
    model = Complaint
    template_name = 'complaints/complaint_detail.html'
    context_object_name = 'complaint'

    def get_queryset(self):
        return Complaint.objects.select_related(
            'customer', 'complaint_type', 'assigned_to', 'assigned_department',
            'created_by', 'branch', 'related_order'
        ).prefetch_related(
            'updates__created_by',
            'attachments__uploaded_by',
            'notifications',
            'escalations'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # نماذج التحديث
        context['update_form'] = ComplaintUpdateForm()
        context['status_form'] = ComplaintStatusUpdateForm(instance=self.object)
        context['assignment_form'] = ComplaintAssignmentForm(instance=self.object)
        context['escalation_form'] = ComplaintEscalationForm()
        context['attachment_form'] = ComplaintAttachmentForm()
        context['resolution_form'] = ComplaintResolutionForm(instance=self.object)
        context['rating_form'] = ComplaintCustomerRatingForm(instance=self.object)

        # التحديثات والمرفقات
        context['updates'] = self.object.updates.order_by('-created_at')
        context['attachments'] = self.object.attachments.order_by('-uploaded_at')

        # الإشعارات
        context['notifications'] = self.object.notifications.filter(
            recipient=self.request.user
        ).order_by('-created_at')

        # التصعيدات
        context['escalations'] = self.object.escalations.order_by('-escalated_at')

        return context


class ComplaintCreateView(LoginRequiredMixin, CreateView):
    """إنشاء شكوى جديدة"""
    model = Complaint
    form_class = ComplaintForm
    template_name = 'complaints/complaint_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request

        # إذا تم تمرير معرف العميل
        customer_id = self.request.GET.get('customer_id')
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
                kwargs['customer'] = customer
            except Customer.DoesNotExist:
                pass

        return kwargs

    def form_valid(self, form):
        """حفظ الشكوى مع رسائل تصحيح شاملة ودعم AJAX"""
        print("===== بدء حفظ الشكوى في الخلفية =====")

        # طباعة بيانات النموذج
        print("بيانات النموذج المستلمة:")
        for field_name, field_value in form.cleaned_data.items():
            print(f"  {field_name}: {field_value}")

        # التحقق من المستخدم الحالي
        user_info = f"المستخدم الحالي: {self.request.user.username}"
        user_info += f" (ID: {self.request.user.id})"
        print(user_info)

        try:
            # تعيين المستخدم كمُنشئ للشكوى
            form.instance.created_by = self.request.user
            print(f"تم تعيين منشئ الشكوى: {self.request.user.username}")

            # حفظ الشكوى
            print("جاري حفظ الشكوى...")
            response = super().form_valid(form)
            print(f"تم حفظ الشكوى بنجاح. رقم الشكوى: {self.object.complaint_number}")
            print(f"معرف الشكوى: {self.object.pk}")

            # طباعة تفاصيل الشكوى المحفوظة
            print("تفاصيل الشكوى المحفوظة:")
            print(f"  العنوان: {self.object.title}")
            print(f"  نوع الشكوى: {self.object.complaint_type}")
            print(f"  العميل: {self.object.customer}")
            print(f"  الأولوية: {self.object.priority}")
            print(f"  الموعد النهائي: {self.object.deadline}")
            print(f"  الموظف المسؤول: {self.object.assigned_to}")
            print(f"  القسم المختص: {self.object.assigned_department}")
            print(f"  تاريخ الإنشاء: {self.object.created_at}")
            
            # التحقق من الطلبات المرتبطة
            related_orders = self.object.related_orders.all()
            if related_orders.exists():
                print(f"الطلبات المرتبطة ({related_orders.count()}):")
                for order in related_orders:
                    print(f"  - طلب رقم {order.id}: {order}")
            else:
                print("لا توجد طلبات مرتبطة")

            # التحقق من نوع الطلب (AJAX أم عادي)
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # طلب AJAX - إرسال استجابة JSON
                print("📡 إرسال استجابة AJAX")

                # معالجة العمليات المختلفة
                action = self.request.POST.get('action', 'save')
                print(f"العملية المطلوبة: {action}")
                
                if action == 'save_and_new':
                    redirect_url = reverse('complaints:complaint_create')
                else:
                    redirect_url = reverse(
                        'complaints:complaint_detail',
                        kwargs={'pk': self.object.pk}
                    )

                message = (
                    f'تم إنشاء الشكوى بنجاح برقم '
                    f'{self.object.complaint_number}'
                )
                return JsonResponse({
                    'status': 'success',
                    'message': message,
                    'complaint_id': self.object.pk,
                    'complaint_number': self.object.complaint_number,
                    'redirect_url': redirect_url
                })
            else:
                # طلب عادي
                # إرسال رسالة نجاح
                message = f'تم إنشاء الشكوى بنجاح برقم {self.object.complaint_number}'
                messages.success(self.request, message)
                print("تم إرسال رسالة النجاح للمستخدم")

                # معالجة العمليات المختلفة
                action = self.request.POST.get('action', 'save')
                if action == 'save_and_new':
                    return redirect('complaints:complaint_create')

                print("===== تم حفظ الشكوى بنجاح =====")
                return response

        except Exception as e:
            print("===== خطأ في حفظ الشكوى =====")
            print(f"نوع الخطأ: {type(e).__name__}")
            print(f"رسالة الخطأ: {str(e)}")

            # التحقق من نوع الطلب
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': f'حدث خطأ في حفظ الشكوى: {str(e)}',
                    'errors': {}
                }, status=500)
            else:
                # إضافة رسالة خطأ للمستخدم
                messages.error(
                    self.request,
                    f'حدث خطأ في حفظ الشكوى: {str(e)}'
                )

                # إعادة عرض النموذج مع الأخطاء
                return self.form_invalid(form)

    def form_invalid(self, form):
        """التعامل مع أخطاء النموذج مع رسائل تصحيح ودعم AJAX"""
        print("===== أخطاء في النموذج =====")

        # طباعة أخطاء النموذج
        if form.errors:
            print("أخطاء الحقول:")
            for field, errors in form.errors.items():
                print(f"  {field}: {errors}")

        # طباعة أخطاء عامة
        if form.non_field_errors():
            print("أخطاء عامة:")
            for error in form.non_field_errors():
                print(f"  - {error}")

        # طباعة البيانات المرسلة
        print("البيانات المرسلة:")
        for key, value in self.request.POST.items():
            print(f"  {key}: {value}")

        # التحقق من نوع الطلب
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'يوجد أخطاء في النموذج',
                'errors': form.errors
            }, status=400)
        else:
            # إضافة رسالة خطأ للمستخدم
            messages.error(
                self.request,
                'يوجد أخطاء في النموذج. يرجى تصحيحها والمحاولة مرة أخرى.'
            )
            return super().form_invalid(form)

    def get_success_url(self):
        return reverse('complaints:complaint_detail', kwargs={'pk': self.object.pk})


class ComplaintUpdateView(LoginRequiredMixin, UpdateView):
    """تحديث الشكوى"""
    model = Complaint
    form_class = ComplaintForm
    template_name = 'complaints/complaint_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'تم تحديث الشكوى بنجاح')
        return response


@login_required
def complaint_status_update(request, pk):
    """تحديث حالة الشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)
    
    if request.method == 'POST':
        form = ComplaintStatusUpdateForm(request.POST, instance=complaint)
        if form.is_valid():

            complaint = form.save()
            
            # إنشاء تحديث
            notes = form.cleaned_data.get('notes', '')
            description = (
                notes or
                f'تم تغيير حالة الشكوى إلى {complaint.get_status_display()}'
            )
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type='status_change',
                title=f'تغيير الحالة إلى {complaint.get_status_display()}',
                description=description,
                created_by=request.user,
                is_visible_to_customer=True
            )

            success_message = (
                f'تم تحديث حالة الشكوى رقم {complaint.complaint_number} '
                f'إلى "{complaint.get_status_display()}".'
            )
            messages.success(request, success_message)
            return redirect('complaints:complaint_detail', pk=pk)

    return redirect('complaints:complaint_detail', pk=pk)


@login_required
def complaint_assignment(request, pk):
    """تعيين مسؤول للشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)
    
    if request.method == 'POST':
        form = ComplaintAssignmentForm(request.POST, instance=complaint)
        if form.is_valid():
            old_assignee = complaint.assigned_to
            complaint = form.save()

            # إنشاء تحديث
            notes = form.cleaned_data.get('assignment_notes', '')
            assignee_name = (
                complaint.assigned_to.get_full_name() if complaint.assigned_to
                else 'غير محدد'
            )
            description = notes or f'تم تعيين {assignee_name} كمسؤول عن الشكوى'

            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type='assignment',
                title=f'تعيين المسؤول: {assignee_name}',
                description=description,
                created_by=request.user,
                old_assignee=old_assignee,
                new_assignee=complaint.assigned_to,
                is_visible_to_customer=False
            )

            messages.success(request, 'تم تعيين المسؤول بنجاح')
            return redirect('complaints:complaint_detail', pk=pk)
    
    return redirect('complaints:complaint_detail', pk=pk)


@login_required
def complaint_add_update(request, pk):
    """إضافة تحديث للشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == 'POST':
        form = ComplaintUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.complaint = complaint
            update.created_by = request.user
            update.save()

            messages.success(request, 'تم إضافة التحديث بنجاح')
            return redirect('complaints:complaint_detail', pk=pk)

    return redirect('complaints:complaint_detail', pk=pk)


@login_required
def complaint_escalate(request, pk):
    """تصعيد الشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == 'POST':
        form = ComplaintEscalationForm(request.POST)
        if form.is_valid():
            # إنشاء سجل تصعيد
            escalation = form.save(commit=False)
            escalation.complaint = complaint
            escalation.escalated_from = complaint.assigned_to
            escalation.escalated_by = request.user
            escalation.save()

            # تحديث حالة الشكوى
            complaint.status = 'escalated'
            complaint.save()

            # إنشاء تحديث
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type='escalation',
                title='تصعيد الشكوى',
                description=f'تم تصعيد الشكوى إلى {escalation.escalated_to.get_full_name()}',
                created_by=request.user,
                is_visible_to_customer=True
            )

            messages.success(request, 'تم تصعيد الشكوى بنجاح')
            return redirect('complaints:complaint_detail', pk=pk)

    return redirect('complaints:complaint_detail', pk=pk)


@login_required
def complaint_resolve(request, pk):
    """حل الشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == 'POST':
        form = ComplaintResolutionForm(request.POST, instance=complaint)
        if form.is_valid():
            resolution_description = form.cleaned_data['resolution_description']

            complaint.status = 'resolved'
            complaint.resolved_at = timezone.now()
            complaint.save()

            # إنشاء تحديث
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type='resolution',
                title='تم حل الشكوى',
                description=resolution_description,
                created_by=request.user,
                is_visible_to_customer=True
            )

            messages.success(request, 'تم حل الشكوى بنجاح')
            return redirect('complaints:complaint_detail', pk=pk)
    return redirect('complaints:complaint_detail', pk=pk)


@login_required
def complaint_add_attachment(request, pk):
    """إضافة مرفق للشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)
    
    if request.method == 'POST':
        form = ComplaintAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.complaint = complaint
            attachment.uploaded_by = request.user
            attachment.save()
            
            messages.success(request, 'تم إضافة المرفق بنجاح')
            return redirect('complaints:complaint_detail', pk=pk)
    
    return redirect('complaints:complaint_detail', pk=pk)


@login_required
def customer_rating(request, pk):
    """تقييم العميل للشكوى"""
    complaint = get_object_or_404(Complaint, pk=pk)
    
    if request.method == 'POST':
        form = ComplaintCustomerRatingForm(request.POST, instance=complaint)
        if form.is_valid():
            complaint = form.save()
            
            # إنشاء تحديث
            rating_text = dict(Complaint.RATING_CHOICES)[complaint.customer_rating]
            ComplaintUpdate.objects.create(
                complaint=complaint,
                update_type='customer_response',
                title=f'تقييم العميل: {rating_text}',
                description=complaint.customer_feedback or 'تم تقييم الخدمة',
                created_by=request.user,
                is_visible_to_customer=True
            )
            
            messages.success(request, 'تم حفظ تقييمك بنجاح')
            return redirect('complaints:complaint_detail', pk=pk)
    
    return redirect('complaints:complaint_detail', pk=pk)


@login_required
def customer_complaints(request, customer_id):
    """شكاوى عميل معين"""
    customer = get_object_or_404(Customer, pk=customer_id)
    
    complaints = Complaint.objects.filter(
        customer=customer
    ).select_related(
        'complaint_type', 'assigned_to'
    ).order_by('-created_at')
    
    # تطبيق ترقيم الصفحات
    paginator = Paginator(complaints, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'customer': customer,
        'complaints': page_obj,
        'page_obj': page_obj,
    }
    
    return render(request, 'complaints/customer_complaints.html', context)


@login_required
def complaints_statistics(request):
    """إحصائيات الشكاوى"""
    # إحصائيات عامة
    stats = {
        'total': Complaint.objects.count(),
        'new': Complaint.objects.filter(status='new').count(),
        'in_progress': Complaint.objects.filter(status='in_progress').count(),
        'resolved': Complaint.objects.filter(status='resolved').count(),
        'overdue': Complaint.objects.filter(status='overdue').count(),
    }
    
    # إحصائيات حسب النوع
    by_type = list(Complaint.objects.values(
        'complaint_type__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count'))
    
    # إحصائيات حسب الشهر (آخر 12 شهر)
    from django.db.models.functions import TruncMonth
    by_month = list(Complaint.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=365)
    ).annotate(
        month=TruncMonth('created_at')
    ).values(
        'month'
    ).annotate(
        count=Count('id')
    ).order_by('month'))
    
    context = {
        'stats': stats,
        'by_type': by_type,
        'by_month': by_month,
    }
    
    return render(request, 'complaints/statistics.html', context)


@login_required
@require_http_methods(["POST"])
def bulk_action(request):
    """الإجراءات المجمعة على الشكاوى"""
    form = ComplaintBulkActionForm(request.POST)
    complaint_ids = request.POST.getlist('complaint_ids')
    
    if not complaint_ids:
        messages.error(request, 'يرجى اختيار شكاوى للتطبيق عليها')
        return redirect('complaints:complaint_list')
    
    if form.is_valid():
        complaints = Complaint.objects.filter(id__in=complaint_ids)
        action = form.cleaned_data['action']
        
        if action == 'assign' and form.cleaned_data['assigned_to']:
            complaints.update(assigned_to=form.cleaned_data['assigned_to'])
            messages.success(request, f'تم تعيين المسؤول لـ {complaints.count()} شكوى')
        
        elif action == 'change_status' and form.cleaned_data['status']:
            complaints.update(status=form.cleaned_data['status'])
            messages.success(request, f'تم تغيير حالة {complaints.count()} شكوى')
        
        elif action == 'change_priority' and form.cleaned_data['priority']:
            complaints.update(priority=form.cleaned_data['priority'])
            messages.success(request, f'تم تغيير أولوية {complaints.count()} شكوى')
        
        else:
            messages.error(request, 'إجراء غير صحيح')


@login_required
def notifications_list(request):
    """قائمة إشعارات الشكاوى للمستخدم مع إحصائيات وفلاتر متقدمة."""
    # تم حذف نظام الإشعارات
    stats = {
        'total_notifications': 0,
        'unread_notifications': 0,
        'urgent_notifications': 0,
        'today_notifications': 0,
    }

    # Apply filters
    queryset = base_queryset
    notification_type = request.GET.get('notification_type')
    status = request.GET.get('status')
    date_range = request.GET.get('date_range')

    if notification_type:
        priority_map = {'urgent': 'high', 'warning': 'medium', 'info': 'low'}
        if notification_type in priority_map:
            queryset = queryset.filter(priority=priority_map[notification_type])

    if status:
        if status == 'read':
            queryset = queryset.filter(is_read=True)
        elif status == 'unread':
            queryset = queryset.filter(is_read=False)

    if date_range:
        today = timezone.now().date()
        if date_range == 'today':
            queryset = queryset.filter(created_at__date=today)
        elif date_range == 'week':
            start_of_week = today - timedelta(days=today.weekday())
            queryset = queryset.filter(created_at__date__gte=start_of_week)
        elif date_range == 'month':
            queryset = queryset.filter(created_at__month=today.month, created_at__year=today.year)

    # Order and paginate
    ordered_queryset = queryset.order_by('-created_at')
    paginator = Paginator(ordered_queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Add notification_type for template styling
    priority_to_type_map = {'high': 'urgent', 'medium': 'warning', 'low': 'info'}
    for notification in page_obj:
        notification.notification_type = priority_to_type_map.get(notification.priority, 'info')

    context = {
        'notifications': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'page_title': 'الإشعارات',
    }

    return render(request, 'complaints/notifications_list.html', context)


@login_required
@require_http_methods(["POST"])
def mark_notification_as_read(request, notification_id):
    """Marks a single notification as read."""
    notification = get_object_or_404(Notification, pk=notification_id, target_users=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
    return JsonResponse({'status': 'success'})


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_as_read(request):
    """Marks all unread notifications for the user as read."""
    Notification.objects.filter(target_users=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    return JsonResponse({'status': 'success', 'message': 'All notifications marked as read.'})


@login_required
@require_http_methods(["POST"])
def delete_notification(request, notification_id):
    """Deletes a single notification."""
    notification = get_object_or_404(Notification, pk=notification_id, target_users=request.user)
    notification.delete()
    return JsonResponse({'status': 'success'})


@login_required
@require_http_methods(["POST"])
def notification_bulk_action(request):
    """Handles bulk actions for notifications (mark as read, delete)."""
    action = request.POST.get('action')
    notification_ids = request.POST.getlist('notification_ids[]')

    if not action or not notification_ids:
        return JsonResponse({'status': 'error', 'message': 'Missing action or notification IDs.'}, status=400)

    queryset = Notification.objects.filter(
        pk__in=notification_ids, target_users=request.user
    )

    if action == 'mark_as_read':
        updated_count = queryset.update(is_read=True, read_at=timezone.now())
        message = f'{updated_count} notifications marked as read.'
    elif action == 'delete':
        deleted_count, _ = queryset.delete()
        message = f'{deleted_count} notifications deleted.'
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid action.'}, status=400)

    return JsonResponse({'status': 'success', 'message': message})






def ajax_complaint_stats(request):
    """
    AJAX endpoint to get complaint statistics
    Returns JSON response with complaint statistics
    """
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    # Get filter parameters
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    queryset = Complaint.objects.all()
    
    # Apply filters
    if status:
        queryset = queryset.filter(status=status)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    
    # Get statistics
    stats = {
        'total': queryset.count(),
        'new': queryset.filter(status='new').count(),
        'in_progress': queryset.filter(status='in_progress').count(),
        'resolved': queryset.filter(status='resolved').count(),
        'overdue': queryset.filter(status='overdue').count(),
        'by_type': list(queryset.values('complaint_type__name').annotate(count=Count('id'))),
        'by_status': list(queryset.values('status').annotate(count=Count('id'))),
        'by_date': list(queryset.extra(select={'date': "date(created_at)"})
                      .values('date')
                      .annotate(count=Count('id'))
                      .order_by('date'))
    }
    
    return JsonResponse(stats, safe=False)


# AJAX Views for smart customer selection and data loading
@login_required
def search_customers(request):
    """البحث الذكي عن العملاء"""
    print("===== بدء البحث عن العملاء =====")
    
    query = request.GET.get('q', '')
    print(f"مصطلح البحث: '{query}'")
    print(f"طول المصطلح: {len(query)}")
    
    if len(query) < 2:
        print("مصطلح البحث قصير جداً - إرجاع نتائج فارغة")
        return JsonResponse({'results': []})
    
    try:
        print("جاري البحث في قاعدة البيانات...")
        customers = Customer.objects.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        ).select_related('branch')[:10]
        
        print(f"تم العثور على {customers.count()} عميل")
        
        results = []
        for customer in customers:
            customer_data = {
                'id': customer.id,
                'text': f"{customer.name} - {customer.phone}",
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email or '',
                'address': customer.address or '',
                'branch': customer.branch.name if customer.branch else '',
            }
            results.append(customer_data)
            print(f"  - عميل: {customer.name} (ID: {customer.id})")
        
        print(f"===== انتهاء البحث - تم إرجاع {len(results)} نتيجة =====")
        return JsonResponse({'results': results})
        
    except Exception as e:
        print("===== خطأ في البحث عن العملاء =====")
        print(f"نوع الخطأ: {type(e).__name__}")
        print(f"رسالة الخطأ: {str(e)}")
        return JsonResponse({
            'error': f'حدث خطأ في البحث: {str(e)}',
            'results': []
        }, status=500)


@login_required
def get_customer_info(request, customer_id):
    """جلب معلومات العميل"""
    try:
        customer = Customer.objects.select_related('branch').get(pk=customer_id)
        
        data = {
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email or 'غير محدد',
            'address': customer.address or 'غير محدد',
            'branch': customer.branch.name if customer.branch else 'غير محدد',
            'customer_type': customer.get_customer_type_display() if hasattr(customer, 'customer_type') else 'غير محدد',
            'status': customer.get_status_display() if hasattr(customer, 'status') else 'نشط',
        }
        
        return JsonResponse(data)
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'العميل غير موجود'}, status=404)


@login_required
def get_customer_orders(request, customer_id):
    """جلب طلبات العميل مع رسائل تصحيح"""
    print(f"===== بدء جلب طلبات العميل {customer_id} =====")
    
    try:
        print(f"البحث عن العميل برقم: {customer_id}")
        customer = Customer.objects.get(pk=customer_id)
        print(f"تم العثور على العميل: {customer.name}")
        
        print("جاري جلب طلبات العميل...")
        orders = Order.objects.filter(customer=customer).select_related(
            'salesperson', 'created_by'
        ).order_by('-created_at')[:20]
        
        print(f"تم العثور على {orders.count()} طلب")
        
        orders_data = []
        for order in orders:
            print(f"معالجة الطلب {order.id}:")
            
            # معلومات البائع
            salesperson_name = 'غير محدد'
            if order.salesperson:
                salesperson_name = order.salesperson.name
                print(f"  البائع: {salesperson_name}")
            elif hasattr(order, 'salesperson_name_raw') and order.salesperson_name_raw:
                salesperson_name = order.salesperson_name_raw
                print(f"  البائع (خام): {salesperson_name}")
            else:
                print("  البائع: غير محدد")
            
            # معلومات منشئ الطلب
            created_by_name = 'غير محدد'
            if hasattr(order, 'created_by') and order.created_by:
                first_name = order.created_by.first_name
                last_name = order.created_by.last_name
                full_name = f"{first_name} {last_name}"
                created_by_name = full_name.strip()
                if not created_by_name:
                    created_by_name = order.created_by.username
                print(f"  منشئ الطلب: {created_by_name}")
            else:
                print("  منشئ الطلب: غير محدد")
            
            # حساب المبلغ الإجمالي
            total_amount = 0
            if hasattr(order, 'total_amount') and order.total_amount:
                total_amount = float(order.total_amount)
                print(f"  المبلغ الإجمالي: {total_amount}")
            else:
                print("  المبلغ الإجمالي: 0")
            
            # حالة الطلب
            order_status = 'غير محدد'
            if hasattr(order, 'status'):
                order_status = order.get_status_display()
                print(f"  حالة الطلب: {order_status}")
            else:
                print("  حالة الطلب: غير محدد")
            
            # تاريخ الإنشاء
            created_date = ''
            if order.created_at:
                created_date = order.created_at.strftime('%Y-%m-%d')
                print(f"  تاريخ الإنشاء: {created_date}")
            
            # وصف الطلب
            description = (getattr(order, 'description', '') or
                           getattr(order, 'notes', '') or 'لا يوجد وصف')
            print(f"  الوصف: {description[:50]}...")
            
            order_data = {
                'id': order.id,
                'order_number': getattr(order, 'order_number', f'طلب #{order.id}'),
                'total_amount': total_amount,
                'status': order_status,
                'created_at': created_date,
                'description': description,
                'salesperson': salesperson_name,
                'created_by': created_by_name,
            }
            orders_data.append(order_data)
        
        print(f"===== تم جلب {len(orders_data)} طلب بنجاح =====")
        return JsonResponse({'orders': orders_data})
        
    except Customer.DoesNotExist:
        print(f"===== خطأ: العميل {customer_id} غير موجود =====")
        return JsonResponse({'error': 'العميل غير موجود'}, status=404)
    except Exception as e:
        print("===== خطأ في جلب طلبات العميل =====")
        print(f"نوع الخطأ: {type(e).__name__}")
        print(f"رسالة الخطأ: {str(e)}")
        return JsonResponse({
            'error': f'حدث خطأ في جلب الطلبات: {str(e)}'
        }, status=500)


@login_required
def get_complaint_type_fields(request, type_id):
    """جلب الحقول المطلوبة لنوع الشكوى"""
    try:
        complaint_type = get_object_or_404(ComplaintType, id=type_id)
        
        # قائمة الموظفين المتاحين للتعيين
        available_staff = []
        if (hasattr(complaint_type, 'responsible_department') and
                complaint_type.responsible_department):
            # جلب موظفي القسم المختص
            from accounts.models import User
            staff_users = User.objects.filter(
                department=complaint_type.responsible_department,
                is_active=True
            ).values('id', 'first_name', 'last_name', 'username')
            
            for user in staff_users:
                full_name = f"{user['first_name']} {user['last_name']}".strip()
                if not full_name:
                    full_name = user['username']
                available_staff.append({
                    'id': user['id'],
                    'name': full_name
                })
        else:
            # جلب جميع المستخدمين النشطين
            from accounts.models import User
            staff_users = User.objects.filter(
                is_active=True
            ).values('id', 'first_name', 'last_name', 'username')
            
            for user in staff_users:
                full_name = f"{user['first_name']} {user['last_name']}".strip()
                if not full_name:
                    full_name = user['username']
                available_staff.append({
                    'id': user['id'],
                    'name': full_name
                })
        
        # قائمة الأقسام المتاحة
        departments = []
        all_departments = Department.objects.filter(is_active=True).values('id', 'name')
        for dept in all_departments:
            departments.append({
                'id': dept['id'],
                'name': dept['name']
            })
        
        # تحديد القسم الافتراضي
        default_dept = None
        if (hasattr(complaint_type, 'responsible_department') and
                complaint_type.responsible_department):
            default_dept = complaint_type.responsible_department.id
        
        return JsonResponse({
            'name': complaint_type.name,
            'description': complaint_type.description or 'لا يوجد وصف',
            'staff': available_staff,
            'departments': departments,
            'default_department': default_dept,
            'expected_resolution_hours': getattr(
                complaint_type, 'expected_resolution_hours', 24
            ),
        })
        
    except ComplaintType.DoesNotExist:
        return JsonResponse({'error': 'نوع الشكوى غير موجود'}, status=404)
