from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db import models
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from accounts.mixins import DepartmentRequiredMixin, PermissionRequiredMixin, BranchAccessMixin
from .models import Installation, InstallationQualityCheckOld, InstallationStep, InstallationTeam
from .forms import InstallationForm, InstallationStepForm, InstallationQualityCheckForm

class InstallationDashboardView(LoginRequiredMixin, DepartmentRequiredMixin, TemplateView):
    template_name = 'installations/dashboard.html'
    department_code = 'installations'  # رمز قسم التركيبات
    permission_denied_message = _("ليس لديك صلاحية للوصول إلى لوحة تحكم التركيبات")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now()

        # Get all installations for the current user or all if superuser
        if self.request.user.is_superuser:
            installations = Installation.objects.all()
        else:
            # فلترة حسب الفرع إذا لم يكن المستخدم مشرفًا
            if hasattr(self.request.user, 'branch') and self.request.user.branch:
                installations = Installation.objects.filter(
                    models.Q(team__members=self.request.user) |
                    models.Q(order__branch=self.request.user.branch)
                ).distinct()
            else:
                installations = Installation.objects.filter(team__members=self.request.user)

        # Count installations by status
        context['pending_installations_count'] = installations.filter(status='pending').count()
        context['completed_installations_count'] = installations.filter(status='completed').count()
        context['in_progress_installations_count'] = installations.filter(status='in_progress').count()
        context['overdue_installations_count'] = installations.filter(
            status__in=['pending', 'in_progress'],
            scheduled_date__lt=today.date()
        ).count()

        # Get recent installations and quality checks
        context['recent_installations'] = installations.order_by('-created_at')[:10]
        context['recent_quality_checks'] = InstallationQualityCheck.objects.filter(
            installation__in=installations
        ).order_by('-created_at')[:5]

        return context

class InstallationListView(LoginRequiredMixin, DepartmentRequiredMixin, ListView):
    model = Installation
    template_name = 'installations/installation_list.html'
    context_object_name = 'installations'
    paginate_by = 10
    department_code = 'installations'  # رمز قسم التركيبات
    permission_denied_message = _("ليس لديك صلاحية للوصول إلى قائمة التركيبات")

    def get_queryset(self):
        # الحصول على الاستعلام الأساسي
        if self.request.user.is_superuser:
            queryset = Installation.objects.all()
        else:
            # فلترة حسب الفرع إذا لم يكن المستخدم مشرفًا
            if hasattr(self.request.user, 'branch') and self.request.user.branch:
                queryset = Installation.objects.filter(
                    models.Q(team__members=self.request.user) |
                    models.Q(order__branch=self.request.user.branch)
                ).distinct()
            else:
                queryset = Installation.objects.filter(team__members=self.request.user)

        # تطبيق التصفية حسب الحالة
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # تطبيق البحث
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(order__order_number__icontains=search_query) |
                models.Q(notes__icontains=search_query) |
                models.Q(team__name__icontains=search_query)
            )

        return queryset.select_related('order', 'team', 'inspection')  # تحسين الأداء باستخدام select_related

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Installation.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context

class InstallationCreateView(LoginRequiredMixin, DepartmentRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Installation
    template_name = 'installations/installation_form.html'
    form_class = InstallationForm
    success_url = reverse_lazy('installations:dashboard')
    department_code = 'installations'  # رمز قسم التركيبات
    required_permission = 'installations.add_installation'  # صلاحية إضافة تركيب
    permission_denied_message = _("ليس لديك صلاحية لإنشاء طلب تركيب جديد")

    def get_form_kwargs(self):
        """إضافة المستخدم الحالي إلى معلمات النموذج"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # تعيين المستخدم الحالي كمنشئ للتركيب
        form.instance.created_by = self.request.user

        # التحقق من أن المستخدم ينتمي إلى نفس الفرع الذي ينتمي إليه الطلب
        if not self.request.user.is_superuser and form.instance.order.branch != self.request.user.branch:
            messages.error(self.request, _("لا يمكنك إنشاء طلب تركيب لطلب من فرع آخر"))
            return self.form_invalid(form)

        messages.success(self.request, _('تم إنشاء طلب التركيب بنجاح'))
        return super().form_valid(form)

class InstallationDetailView(LoginRequiredMixin, DepartmentRequiredMixin, BranchAccessMixin, DetailView):
    model = Installation
    template_name = 'installations/installation_detail.html'
    context_object_name = 'installation'
    department_code = 'installations'  # رمز قسم التركيبات
    permission_denied_message = _("ليس لديك صلاحية لعرض تفاصيل هذا التركيب")

    def test_func(self):
        # السماح للمستخدم المشرف بالوصول إلى جميع الصفحات
        if self.request.user.is_superuser:
            return True

        # الحصول على الكائن
        obj = self.get_object()

        # التحقق من أن المستخدم ينتمي إلى نفس الفرع أو عضو في فريق التركيب
        return (
            (hasattr(self.request.user, 'branch') and obj.order.branch == self.request.user.branch) or
            (obj.team and self.request.user in obj.team.members.all())
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # استخدام prefetch_related لتحسين الأداء
        context['steps'] = self.object.steps.all().select_related('completed_by').order_by('order')
        context['quality_checks'] = self.object.quality_checks.all().select_related('checked_by').order_by('-created_at')
        context['issues'] = self.object.issues.all().select_related('reported_by', 'assigned_to', 'resolved_by').order_by('-created_at')
        return context

class InstallationUpdateView(LoginRequiredMixin, DepartmentRequiredMixin, PermissionRequiredMixin, BranchAccessMixin, UpdateView):
    model = Installation
    template_name = 'installations/installation_form.html'
    form_class = InstallationForm
    success_url = reverse_lazy('installations:dashboard')
    department_code = 'installations'  # رمز قسم التركيبات
    required_permission = 'installations.change_installation'  # صلاحية تعديل تركيب
    permission_denied_message = _("ليس لديك صلاحية لتعديل هذا التركيب")

    def get_form_kwargs(self):
        """إضافة المستخدم الحالي إلى معلمات النموذج"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def test_func(self):
        # السماح للمستخدم المشرف بالوصول إلى جميع الصفحات
        if self.request.user.is_superuser:
            return True

        # الحصول على الكائن
        obj = self.get_object()

        # التحقق من أن المستخدم ينتمي إلى نفس الفرع أو عضو في فريق التركيب
        return (
            (hasattr(self.request.user, 'branch') and obj.order.branch == self.request.user.branch) or
            (obj.team and self.request.user in obj.team.members.all())
        )

    def form_valid(self, form):
        # تسجيل التغييرات في الحالة
        if 'status' in form.changed_data:
            old_status = self.get_object().status
            new_status = form.cleaned_data['status']

            # تحديث تواريخ البدء والانتهاء تلقائيًا
            if new_status == 'in_progress' and not form.instance.actual_start_date:
                form.instance.actual_start_date = timezone.now()
            elif new_status == 'completed' and not form.instance.actual_end_date:
                form.instance.actual_end_date = timezone.now()

            # إنشاء إشعار بتغيير الحالة
            if old_status != new_status:
                # هنا يمكن إضافة كود لإنشاء إشعار بتغيير الحالة
                pass

        messages.success(self.request, _('تم تحديث طلب التركيب بنجاح'))
        return super().form_valid(form)

class InstallationDeleteView(LoginRequiredMixin, DepartmentRequiredMixin, PermissionRequiredMixin, BranchAccessMixin, DeleteView):
    model = Installation
    template_name = 'installations/installation_confirm_delete.html'
    success_url = reverse_lazy('installations:dashboard')
    department_code = 'installations'  # رمز قسم التركيبات
    required_permission = 'installations.delete_installation'  # صلاحية حذف تركيب
    permission_denied_message = _("ليس لديك صلاحية لحذف هذا التركيب")

    def test_func(self):
        # السماح للمستخدم المشرف بالوصول إلى جميع الصفحات
        if self.request.user.is_superuser:
            return True

        # الحصول على الكائن
        obj = self.get_object()

        # التحقق من أن المستخدم ينتمي إلى نفس الفرع
        if hasattr(self.request.user, 'branch') and obj.order.branch != self.request.user.branch:
            return False

        # التحقق من أن التركيب ليس في حالة مكتملة أو قيد التنفيذ
        if obj.status in ['completed', 'in_progress']:
            messages.error(self.request, _("لا يمكن حذف تركيب مكتمل أو قيد التنفيذ"))
            return False

        return super().test_func()

    def delete(self, request, *args, **kwargs):
        # تسجيل عملية الحذف في سجل النشاط
        # هنا يمكن إضافة كود لتسجيل عملية الحذف

        messages.success(request, _('تم حذف طلب التركيب بنجاح'))
        return super().delete(request, *args, **kwargs)


# وظائف لإدارة خطوات التركيب
@login_required
@csrf_protect
@require_POST
def add_installation_step(request, installation_id):
    """إضافة خطوة جديدة للتركيب"""
    installation = get_object_or_404(Installation, pk=installation_id)

    # التحقق من الصلاحيات
    if not request.user.is_superuser:
        if not request.user.has_perm('installations.add_installationstep'):
            return JsonResponse({'status': 'error', 'message': _('ليس لديك صلاحية لإضافة خطوات')}, status=403)

        # التحقق من أن المستخدم ينتمي إلى نفس الفرع أو عضو في فريق التركيب
        if not (hasattr(request.user, 'branch') and installation.order.branch == request.user.branch) and not (installation.team and request.user in installation.team.members.all()):
            return JsonResponse({'status': 'error', 'message': _('ليس لديك صلاحية للوصول إلى هذا التركيب')}, status=403)

    # استخدام النموذج للتحقق من البيانات
    form = InstallationStepForm(request.POST)

    if form.is_valid():
        # إنشاء الخطوة
        try:
            step = form.save(commit=False)
            step.installation = installation
            step.save()

            return JsonResponse({
                'status': 'success',
                'message': _('تمت إضافة الخطوة بنجاح'),
                'step': {
                    'id': step.id,
                    'name': step.name,
                    'order': step.order,
                    'is_completed': step.is_completed
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        # إرجاع أخطاء التحقق من النموذج
        errors = {field: errors[0] for field, errors in form.errors.items()}
        return JsonResponse({'status': 'error', 'message': _('بيانات غير صالحة'), 'errors': errors}, status=400)


@login_required
@csrf_protect
@require_POST
def mark_step_complete(request, step_id):
    """تحديد خطوة كمكتملة"""
    step = get_object_or_404(InstallationStep, pk=step_id)

    # التحقق من الصلاحيات
    if not request.user.is_superuser:
        if not request.user.has_perm('installations.change_installationstep'):
            return JsonResponse({'status': 'error', 'message': _('ليس لديك صلاحية لتعديل الخطوات')}, status=403)

        # التحقق من أن المستخدم ينتمي إلى نفس الفرع أو عضو في فريق التركيب
        installation = step.installation
        if not (hasattr(request.user, 'branch') and installation.order.branch == request.user.branch) and not (installation.team and request.user in installation.team.members.all()):
            return JsonResponse({'status': 'error', 'message': _('ليس لديك صلاحية للوصول إلى هذا التركيب')}, status=403)

    # تحديث الخطوة
    step.is_completed = True
    step.completed_at = timezone.now()
    step.completed_by = request.user
    step.save()

    return JsonResponse({
        'status': 'success',
        'message': _('تم تحديد الخطوة كمكتملة'),
        'step': {
            'id': step.id,
            'is_completed': step.is_completed,
            'completed_at': step.completed_at.strftime('%Y-%m-%d %H:%M'),
            'completed_by': step.completed_by.get_full_name()
        }
    })


# وظائف لإدارة فحوصات الجودة
@login_required
@csrf_protect
@require_POST
def add_quality_check(request, installation_id):
    """إضافة فحص جودة جديد للتركيب"""
    installation = get_object_or_404(Installation, pk=installation_id)

    # التحقق من الصلاحيات
    if not request.user.is_superuser:
        if not request.user.has_perm('installations.add_installationqualitycheck'):
            return JsonResponse({'status': 'error', 'message': _('ليس لديك صلاحية لإضافة فحوصات الجودة')}, status=403)

        # التحقق من أن المستخدم ينتمي إلى نفس الفرع أو عضو في فريق التركيب
        if not (hasattr(request.user, 'branch') and installation.order.branch == request.user.branch) and not (installation.team and request.user in installation.team.members.all()):
            return JsonResponse({'status': 'error', 'message': _('ليس لديك صلاحية للوصول إلى هذا التركيب')}, status=403)

    # استخدام النموذج للتحقق من البيانات
    form = InstallationQualityCheckForm(request.POST)

    if form.is_valid():
        # إنشاء فحص الجودة
        try:
            check = form.save(commit=False)
            check.installation = installation
            check.checked_by = request.user
            check.save()

            # تحديث متوسط تقييم الجودة للتركيب
            avg_rating = installation.quality_checks.aggregate(models.Avg('rating'))['rating__avg']
            if avg_rating:
                installation.quality_rating = round(avg_rating)
                installation.save()

            return JsonResponse({
                'status': 'success',
                'message': _('تم إضافة فحص الجودة بنجاح'),
                'check': {
                    'id': check.id,
                    'criteria': check.get_criteria_display(),
                    'rating': check.rating,
                    'checked_by': check.checked_by.get_full_name(),
                    'created_at': check.created_at.strftime('%Y-%m-%d %H:%M')
                },
                'installation_rating': installation.quality_rating
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        # إرجاع أخطاء التحقق من النموذج
        errors = {field: errors[0] for field, errors in form.errors.items()}
        return JsonResponse({'status': 'error', 'message': _('بيانات غير صالحة'), 'errors': errors}, status=400)
