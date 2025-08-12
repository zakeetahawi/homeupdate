from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q

from .models import CompanyInfo, FormField, Department, Salesperson, Branch, Role, UserRole, SimpleNotification, ComplaintNotification
from .forms import CompanyInfoForm, FormFieldForm, DepartmentForm, SalespersonForm, RoleForm, RoleAssignForm

# سيتم إضافة دوال الإشعارات هنا

# الحصول على نموذج المستخدم المخصص
User = get_user_model()

def login_view(request):
    """
    View for user login
    """
    import logging
    import traceback
    logger = logging.getLogger('django')

    # إعداد نموذج تسجيل الدخول الافتراضي
    form = AuthenticationForm()

    # إضافة الأنماط إلى حقول النموذج
    try:
        form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'اسم المستخدم'})
        form.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'كلمة المرور'})
    except Exception as form_error:
        logger.error(f"[Form Error] {form_error}")

    try:
        # التحقق مما إذا كان المستخدم مسجل الدخول بالفعل
        if request.user.is_authenticated:
            return redirect('home')

        # معالجة طلب تسجيل الدخول
        if request.method == 'POST':
            try:
                form = AuthenticationForm(request, data=request.POST)

                # إضافة الأنماط إلى حقول النموذج
                form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'اسم المستخدم'})
                form.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'كلمة المرور'})

                if form.is_valid():
                    username = form.cleaned_data.get('username')
                    password = form.cleaned_data.get('password')
                    logger.info(f"Login attempt for user: {username}")

                    # محاولة المصادقة المباشرة
                    user = authenticate(request=request, username=username, password=password)

                    if user is not None:
                        login(request, user)
                        messages.success(request, f'مرحباً بك {username}!')
                        next_url = request.GET.get('next', 'home')
                        return redirect(next_url)
                    else:
                        messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
                else:
                    messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة.')
            except Exception as auth_error:
                logger.error(f"[Authentication Error] {auth_error}")
                logger.error(traceback.format_exc())
                messages.error(request, 'حدث خطأ أثناء محاولة تسجيل الدخول. يرجى المحاولة مرة أخرى.')

        # تم إزالة منطق إعداد النظام الأولي (غير مستخدم بعد الآن)

        # عرض نموذج تسجيل الدخول
        context = {
            'form': form,
            'title': 'تسجيل الدخول',
        }

        return render(request, 'accounts/login.html', context)
    except Exception as e:
        logger.error(f"[Critical Login Error] {e}")
        logger.error(traceback.format_exc())

        # في حالة حدوث خطأ غير متوقع، نعرض صفحة تسجيل دخول بسيطة
        context = {
            'form': form,
            'title': 'تسجيل الدخول',
            'error_message': 'حدث خطأ في النظام. يرجى الاتصال بمسؤول النظام.'
        }

        return render(request, 'accounts/login.html', context)

def logout_view(request):
    """
    View for user logout
    """
    logout(request)
    messages.success(request, 'تم تسجيل الخروج بنجاح.')
    return redirect('home')

def admin_logout_view(request):
    """
    View for admin logout that supports GET method
    """
    logout(request)
    messages.success(request, 'تم تسجيل الخروج بنجاح.')
    return redirect('admin:index')

@login_required
def profile_view(request):
    """
    View for user profile
    """
    context = {
        'user': request.user,
        'title': 'الملف الشخصي',
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def company_info_view(request):
    try:
        if not request.user.is_superuser:
            messages.error(request, 'هذه الصفحة متاحة فقط لمديري النظام.')
            return redirect('home')
        """
        View for managing company information
        """
        # Get or create company info
        company, _ = CompanyInfo.objects.get_or_create(
            defaults={
                'name': 'شركة الخواجه',
                'address': 'العنوان',
                'phone': '01234567890',
                'email': 'info@example.com',
            }
        )

        if request.method == 'POST':
            form = CompanyInfoForm(request.POST, request.FILES, instance=company)
            if form.is_valid():
                form.save()
                messages.success(request, 'تم تحديث معلومات الشركة بنجاح.')
                return redirect('accounts:company_info')
        else:
            form = CompanyInfoForm(instance=company)

        context = {
            'form': form,
            'company': company,
            'title': 'معلومات الشركة',
        }

        return render(request, 'accounts/company_info.html', context)
    except Exception as e:
        import traceback
        print("[CompanyInfo Error]", e)
        traceback.print_exc()
        messages.error(request, 'حدث خطأ غير متوقع أثناء معالجة معلومات الشركة. يرجى مراجعة الدعم الفني.')
        return redirect('home')

@staff_member_required
def form_field_list(request):
    """
    View for listing form fields
    """
    form_type = request.GET.get('form_type', '')

    # Filter form fields
    if form_type:
        form_fields = FormField.objects.filter(form_type=form_type)
    else:
        form_fields = FormField.objects.all()

    # Paginate form fields
    paginator = Paginator(form_fields, 10)  # Show 10 form fields per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'form_type': form_type,
        'form_types': dict(FormField.FORM_CHOICES),
        'title': 'إدارة حقول النماذج',
    }

    return render(request, 'accounts/form_field_list.html', context)

@staff_member_required
def form_field_create(request):
    """
    View for creating a new form field
    """
    if request.method == 'POST':
        form = FormFieldForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة الحقل بنجاح.')
            return redirect('accounts:form_field_list')
    else:
        # Pre-fill form type if provided in GET parameters
        form_type = request.GET.get('form_type', '')
        form = FormFieldForm(initial={'form_type': form_type})

    context = {
        'form': form,
        'title': 'إضافة حقل جديد',
    }

    return render(request, 'accounts/form_field_form.html', context)

@staff_member_required
def form_field_update(request, pk):
    """
    View for updating a form field
    """
    form_field = get_object_or_404(FormField, pk=pk)

    if request.method == 'POST':
        form = FormFieldForm(request.POST, instance=form_field)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الحقل بنجاح.')
            return redirect('accounts:form_field_list')
    else:
        form = FormFieldForm(instance=form_field)

    context = {
        'form': form,
        'form_field': form_field,
        'title': 'تعديل الحقل',
    }

    return render(request, 'accounts/form_field_form.html', context)

@staff_member_required
def form_field_delete(request, pk):
    """
    View for deleting a form field
    """
    form_field = get_object_or_404(FormField, pk=pk)

    if request.method == 'POST':
        form_field.delete()
        messages.success(request, 'تم حذف الحقل بنجاح.')
        return redirect('accounts:form_field_list')

    context = {
        'form_field': form_field,
        'title': 'حذف الحقل',
    }

    return render(request, 'accounts/form_field_confirm_delete.html', context)

@staff_member_required
def toggle_form_field(request, pk):
    """
    View for toggling a form field's enabled status via AJAX
    """
    if request.method == 'POST':
        form_field = get_object_or_404(FormField, pk=pk)
        form_field.enabled = not form_field.enabled
        form_field.save()

        return JsonResponse({
            'success': True,
            'enabled': form_field.enabled,
            'field_id': form_field.id
        })

    return JsonResponse({'success': False, 'message': 'طريقة غير صالحة.'})

# إدارة الأقسام Department Management Views

@staff_member_required
def department_list(request):
    """
    عرض قائمة الأقسام مع إمكانية البحث والتصفية
    """
    search_query = request.GET.get('search', '')
    parent_filter = request.GET.get('parent', '')

    # قاعدة البيانات الأساسية
    departments = Department.objects.all().select_related('parent').prefetch_related('children')

    # تطبيق البحث
    if search_query:
        departments = departments.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # تصفية حسب القسم الرئيسي
    if parent_filter:
        departments = departments.filter(parent_id=parent_filter)

    # الترتيب
    departments = departments.order_by('order', 'name')

    # التقسيم لصفحات
    paginator = Paginator(departments, 15)  # 15 قسم في كل صفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # جلب قائمة الأقسام الرئيسية للتصفية مع كاش
    from django.core.cache import cache
    parent_departments = cache.get('parent_departments')
    if not parent_departments:
        parent_departments = list(Department.objects.filter(parent__isnull=True))
        cache.set('parent_departments', parent_departments, 3600)  # كاش لمدة ساعة

    context = {
        'page_obj': page_obj,
        'total_departments': departments.count(),
        'search_query': search_query,
        'parent_filter': parent_filter,
        'parent_departments': parent_departments,
        'title': 'إدارة الأقسام',
    }

    return render(request, 'accounts/department_list.html', context)

@staff_member_required
def department_create(request):
    """
    إنشاء قسم جديد
    """
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة القسم بنجاح.')
            return redirect('accounts:department_list')
    else:
        form = DepartmentForm()

    context = {
        'form': form,
        'title': 'إضافة قسم جديد',
    }

    return render(request, 'accounts/department_form.html', context)

@staff_member_required
def department_update(request, pk):
    """
    تحديث قسم
    """
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث القسم بنجاح.')
            return redirect('accounts:department_list')
    else:
        form = DepartmentForm(instance=department)

    context = {
        'form': form,
        'department': department,
        'title': 'تعديل القسم',
    }

    return render(request, 'accounts/department_form.html', context)

@staff_member_required
def department_delete(request, pk):
    """
    حذف قسم
    """
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        # فحص ما إذا كان القسم يحتوي على أقسام فرعية
        if department.children.exists():
            messages.error(request, 'لا يمكن حذف القسم لأنه يحتوي على أقسام فرعية.')
            return redirect('accounts:department_list')

        department.delete()
        messages.success(request, 'تم حذف القسم بنجاح.')
        return redirect('accounts:department_list')

    context = {
        'department': department,
        'title': 'حذف القسم',
    }

    return render(request, 'accounts/department_confirm_delete.html', context)

@staff_member_required
def toggle_department(request, pk):
    """
    تفعيل/إيقاف قسم
    """
    if request.method == 'POST':
        department = get_object_or_404(Department, pk=pk)
        department.is_active = not department.is_active
        department.save()

        return JsonResponse({
            'success': True,
            'is_active': department.is_active,
            'department_id': department.id
        })

    return JsonResponse({'success': False, 'message': 'طريقة غير صالحة.'})

# إدارة البائعين Salesperson Management Views

@staff_member_required
def salesperson_list(request):
    """
    عرض قائمة البائعين مع إمكانية البحث والتصفية
    """
    search_query = request.GET.get('search', '')
    branch_filter = request.GET.get('branch', '')
    is_active = request.GET.get('is_active', '')

    # قاعدة البيانات الأساسية
    salespersons = Salesperson.objects.select_related('branch').all()

    # تطبيق البحث
    if search_query:
        salespersons = salespersons.filter(
            Q(name__icontains=search_query) |
            Q(employee_number__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    # تصفية حسب الفرع
    if branch_filter:
        salespersons = salespersons.filter(branch_id=branch_filter)

    # تصفية حسب الحالة
    if is_active:
        is_active = is_active == 'true'
        salespersons = salespersons.filter(is_active=is_active)

    # الترتيب
    salespersons = salespersons.order_by('name')

    # التقسيم لصفحات
    paginator = Paginator(salespersons, 10)  # 10 بائعين في كل صفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # جلب قائمة الفروع للتصفية مع كاش
    from django.core.cache import cache
    branches = cache.get('branches')
    if not branches:
        branches = list(Branch.objects.all())
        cache.set('branches', branches, 3600)  # كاش لمدة ساعة

    context = {
        'page_obj': page_obj,
        'total_salespersons': salespersons.count(),
        'search_query': search_query,
        'branch_filter': branch_filter,
        'is_active': is_active,
        'branches': branches,
        'title': 'قائمة البائعين',
    }

    return render(request, 'accounts/salesperson_list.html', context)

@staff_member_required
def salesperson_create(request):
    """
    إنشاء بائع جديد
    """
    if request.method == 'POST':
        form = SalespersonForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إضافة البائع بنجاح.')
            return redirect('accounts:salesperson_list')
    else:
        form = SalespersonForm()

    context = {
        'form': form,
        'title': 'إضافة بائع جديد',
    }

    return render(request, 'accounts/salesperson_form.html', context)

@staff_member_required
def salesperson_update(request, pk):
    """
    تحديث بائع
    """
    salesperson = get_object_or_404(Salesperson, pk=pk)

    if request.method == 'POST':
        form = SalespersonForm(request.POST, instance=salesperson)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث بيانات البائع بنجاح.')
            return redirect('accounts:salesperson_list')
    else:
        form = SalespersonForm(instance=salesperson)

    context = {
        'form': form,
        'salesperson': salesperson,
        'title': 'تعديل بيانات البائع',
    }

    return render(request, 'accounts/salesperson_form.html', context)

@staff_member_required
def salesperson_delete(request, pk):
    """
    حذف بائع
    """
    salesperson = get_object_or_404(Salesperson, pk=pk)

    if request.method == 'POST':
        try:
            salesperson.delete()
            messages.success(request, 'تم حذف البائع بنجاح.')
        except Exception as e:
            messages.error(request, 'لا يمكن حذف البائع لارتباطه بسجلات أخرى.')
        return redirect('accounts:salesperson_list')

    context = {
        'salesperson': salesperson,
        'title': 'حذف البائع',
    }

    return render(request, 'accounts/salesperson_confirm_delete.html', context)

@staff_member_required
def toggle_salesperson(request, pk):
    """
    تفعيل/إيقاف بائع
    """
    if request.method == 'POST':
        salesperson = get_object_or_404(Salesperson, pk=pk)
        salesperson.is_active = not salesperson.is_active
        salesperson.save()

        return JsonResponse({
            'success': True,
            'is_active': salesperson.is_active,
            'salesperson_id': salesperson.id
        })

    return JsonResponse({'success': False, 'message': 'طريقة غير صالحة.'})

# إدارة الأدوار Role Management Views

@staff_member_required
def role_list(request):
    """
    عرض قائمة الأدوار مع إمكانية البحث والتصفية والتقسيم بشكل مستقل
    """
    roles = Role.objects.all()

    # بحث عن الأدوار
    search_query = request.GET.get('search', '')
    if search_query:
        roles = roles.filter(name__icontains=search_query)

    # تصفية الأدوار
    role_type = request.GET.get('type', '')
    if role_type == 'system':
        roles = roles.filter(is_system_role=True)
    elif role_type == 'custom':
        roles = roles.filter(is_system_role=False)

    # ترتيب الأدوار
    roles = roles.order_by('name')

    # التقسيم لصفحات
    paginator = Paginator(roles, 10)  # عرض 10 أدوار في كل صفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_type': role_type,
        'title': 'إدارة الأدوار',
    }

    return render(request, 'accounts/role_list.html', context)

@staff_member_required
def role_create(request):
    """
    إنشاء دور جديد
    """
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()
            messages.success(request, f'تم إنشاء دور {role.name} بنجاح.')
            return redirect('accounts:role_list')
    else:
        form = RoleForm()

    context = {
        'form': form,
        'title': 'إنشاء دور جديد',
    }

    return render(request, 'accounts/role_form.html', context)

@staff_member_required
def role_update(request, pk):
    """
    تحديث دور
    """
    role = get_object_or_404(Role, pk=pk)

    # لا يمكن تحديث أدوار النظام إلا للمشرفين
    if role.is_system_role and not request.user.is_superuser:
        messages.error(request, 'لا يمكنك تعديل أدوار النظام الأساسية.')
        return redirect('accounts:role_list')

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            updated_role = form.save()

            # تحديث صلاحيات المستخدمين الذين لديهم هذا الدور
            for user_role in UserRole.objects.filter(role=updated_role):
                user = user_role.user
                # إعادة تعيين الصلاحيات من الأدوار
                user_roles = user.user_roles.all()
                # إعادة تعيين صلاحيات المستخدم
                user.user_permissions.clear()
                for ur in user_roles:
                    for permission in ur.role.permissions.all():
                        user.user_permissions.add(permission)

            messages.success(request, f'تم تحديث دور {role.name} بنجاح.')
            return redirect('accounts:role_list')
    else:
        form = RoleForm(instance=role)

    context = {
        'form': form,
        'role': role,
        'title': f'تحديث دور {role.name}',
    }

    return render(request, 'accounts/role_form.html', context)

@staff_member_required
def role_delete(request, pk):
    """
    حذف دور
    """
    role = get_object_or_404(Role, pk=pk)

    # لا يمكن حذف أدوار النظام
    if role.is_system_role:
        messages.error(request, 'لا يمكن حذف أدوار النظام الأساسية.')
        return redirect('accounts:role_list')

    if request.method == 'POST':
        role_name = role.name

        # حذف علاقات الدور بالمستخدمين
        UserRole.objects.filter(role=role).delete()

        # حذف الدور
        role.delete()

        messages.success(request, f'تم حذف دور {role_name} بنجاح.')
        return redirect('accounts:role_list')

    context = {
        'role': role,
        'title': f'حذف دور {role.name}',
    }

    return render(request, 'accounts/role_confirm_delete.html', context)

@staff_member_required
def role_assign(request, pk):
    """
    إسناد دور للمستخدمين
    """
    role = get_object_or_404(Role, pk=pk)

    if request.method == 'POST':
        form = RoleAssignForm(request.POST, role=role)
        if form.is_valid():
            users = form.cleaned_data['users']
            count = 0
            for user in users:
                # إنشاء علاقة بين الدور والمستخدم
                UserRole.objects.get_or_create(user=user, role=role)
                # إضافة صلاحيات الدور للمستخدم
                for permission in role.permissions.all():
                    user.user_permissions.add(permission)
                count += 1

            messages.success(request, f'تم إسناد دور {role.name} لـ {count} مستخدمين بنجاح.')
            return redirect('accounts:role_list')
    else:
        form = RoleAssignForm(role=role)

    context = {
        'form': form,
        'role': role,
        'title': f'إسناد دور {role.name} للمستخدمين',
    }

    return render(request, 'accounts/role_assign_form.html', context)

@staff_member_required
def role_management(request):
    """
    الصفحة الرئيسية لإدارة الأدوار
    """
    roles = Role.objects.all().prefetch_related('user_roles', 'permissions')
    users = User.objects.filter(is_active=True).exclude(is_superuser=True).prefetch_related('user_roles')

    # تصفية الأدوار
    role_type = request.GET.get('type', '')
    if role_type == 'system':
        roles = roles.filter(is_system_role=True)
    elif role_type == 'custom':
        roles = roles.filter(is_system_role=False)

    # تقسيم الصفحات
    paginator = Paginator(roles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'users': users,
        'role_type': role_type,
        'title': 'إدارة الأدوار والصلاحيات',
        'total_roles': roles.count(),
        'total_users': users.count(),
    }

    return render(request, 'accounts/role_management.html', context)

@login_required
def set_default_theme(request):
    """
    تعيين الثيم الافتراضي للمستخدم
    """
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            theme = data.get('theme', 'default')
            
            # حفظ الثيم الافتراضي للمستخدم
            request.user.default_theme = theme
            request.user.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'تم تعيين "{theme}" كثيم افتراضي'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': f'حدث خطأ: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'طريقة غير مدعومة'
    })


# ==================== 🎨 نظام الإشعارات البسيط والجميل ====================

@login_required
def get_notifications_data(request):
    """الحصول على بيانات الإشعارات للواجهة - محدث للإشعارات الجماعية"""
    try:
        from accounts.models import GroupNotification

        # استخدام الإشعارات الجماعية الجديدة بدلاً من الإشعارات الفردية القديمة
        group_notifications = GroupNotification.objects.filter(
            target_users=request.user
        ).order_by('-created_at')[:20]

        # إشعارات الشكاوى (تبقى كما هي)
        if request.user.is_superuser or \
           (hasattr(request.user, 'is_general_manager') and request.user.is_general_manager) or \
           (hasattr(request.user, 'is_factory_manager') and request.user.is_factory_manager):
            complaint_notifications = ComplaintNotification.objects.all().order_by('-created_at')[:20]
        elif hasattr(request.user, 'is_region_manager') and request.user.is_region_manager:
            # مدير المنطقة يرى إشعارات فروعه
            complaint_notifications = ComplaintNotification.objects.filter(recipient=request.user).order_by('-created_at')[:10]
        elif hasattr(request.user, 'is_branch_manager') and request.user.is_branch_manager:
            # مدير الفرع يرى إشعارات فرعه
            complaint_notifications = ComplaintNotification.objects.filter(recipient=request.user).order_by('-created_at')[:10]
            complaint_notifications = ComplaintNotification.objects.filter(recipient=request.user).order_by('-created_at')[:10]
        elif hasattr(request.user, 'is_salesperson') and request.user.is_salesperson:
            # البائع يرى إشعاراته فقط
            complaint_notifications = ComplaintNotification.objects.filter(
                recipient=request.user
            ).order_by('-created_at')[:10]
        else:
            # المستخدمون الآخرون يرون إشعاراتهم فقط
            complaint_notifications = ComplaintNotification.objects.filter(
                recipient=request.user
            ).order_by('-created_at')[:10]

        # تحويل الإشعارات الجماعية إلى قوائم
        order_data = []
        for notification in group_notifications:
            # فحص ما إذا كان المستخدم قد قرأ الإشعار
            is_read = notification.is_read_by_user(request.user)

            order_data.append({
                'id': notification.id,
                'title': notification.title,
                'customer_name': notification.customer_name,
                'order_number': notification.order_number,
                'status': notification.get_priority_display(),  # استخدام الأولوية كحالة
                'icon': notification.get_icon(),
                'color_class': notification.get_color_class(),
                'time_ago': str(notification.created_at.strftime('%Y-%m-%d %H:%M')),
                'is_read': is_read,
                'notification_type': notification.notification_type,
                'priority': notification.priority,
            })

        complaint_data = []
        for notification in complaint_notifications:
            complaint_data.append({
                'id': notification.id,
                'title': notification.title,
                'customer_name': notification.customer_name,
                'complaint_number': notification.complaint_number,
                'icon': notification.get_icon(),
                'color_class': notification.get_color_class(),
                'time_ago': notification.get_time_ago(),
                'is_read': notification.is_read,
                'complaint_type': notification.complaint_type,
                'priority': notification.priority,
            })

        # العدادات - استخدام الإشعارات الجماعية
        # حساب الإشعارات غير المقروءة للمستخدم الحالي
        unread_orders = 0
        for notification in group_notifications:
            if not notification.is_read_by_user(request.user):
                unread_orders += 1

        # عدادات الشكاوى (تبقى كما هي)
        if request.user.is_superuser or \
           (hasattr(request.user, 'is_general_manager') and request.user.is_general_manager) or \
           (hasattr(request.user, 'is_factory_manager') and request.user.is_factory_manager):
            urgent_complaints = ComplaintNotification.objects.filter(
                is_read=False,
                priority__in=['high', 'critical']
            ).count()
        else:
            urgent_complaints = ComplaintNotification.objects.filter(
                recipient=request.user,
                is_read=False,
                priority__in=['high', 'critical']
            ).count()

        return JsonResponse({
            'success': True,
            'order_notifications': order_data,
            'complaint_notifications': complaint_data,
            'unread_orders_count': unread_orders,
            'urgent_complaints_count': urgent_complaints,
        })

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"خطأ في get_notifications_data: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def mark_order_notification_read(request, notification_id):
    """تحديد إشعار طلب كمقروء"""
    try:
        # مدير النظام والمدير العام ومسؤول المصنع يمكنهم تحديد أي إشعار كمقروء
        if request.user.is_superuser or \
           (hasattr(request.user, 'is_general_manager') and request.user.is_general_manager) or \
           (hasattr(request.user, 'is_factory_manager') and request.user.is_factory_manager):
            notification = get_object_or_404(SimpleNotification, id=notification_id)
        else:
            # المستخدمون الآخرون يحددون إشعاراتهم فقط
            notification = get_object_or_404(
                SimpleNotification,
                id=notification_id,
                recipient=request.user
            )

        notification.mark_as_read()

        return JsonResponse({
            'success': True,
            'message': 'تم تحديد الإشعار كمقروء'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def mark_complaint_notification_read(request, notification_id):
    """تحديد إشعار شكوى كمقروء"""
    if request.method == 'POST':
        try:
            # مدير النظام والمدير العام ومسؤول المصنع يمكنهم تحديد أي إشعار كمقروء
            if request.user.is_superuser or \
               (hasattr(request.user, 'is_general_manager') and request.user.is_general_manager) or \
               (hasattr(request.user, 'is_factory_manager') and request.user.is_factory_manager):
                notification = get_object_or_404(ComplaintNotification, id=notification_id)
            else:
                # المستخدمون الآخرون يحددون إشعاراتهم فقط
                notification = get_object_or_404(
                    ComplaintNotification,
                    id=notification_id,
                    recipient=request.user
                )

            notification.mark_as_read()

            return JsonResponse({
                'success': True,
                'message': 'تم تحديد الإشعار كمقروء'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    return JsonResponse({'success': False, 'error': 'طريقة غير صحيحة'})


@login_required
def mark_all_order_notifications_read(request):
    """تحديد جميع إشعارات الطلبات كمقروءة"""
    if request.method == 'POST':
        try:
            from django.utils import timezone
            updated_count = SimpleNotification.objects.filter(
                recipient=request.user,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )

            return JsonResponse({
                'success': True,
                'message': f'تم تحديد {updated_count} إشعار كمقروء',
                'updated_count': updated_count
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    return JsonResponse({'success': False, 'error': 'طريقة غير صحيحة'})


@login_required
def mark_all_complaint_notifications_read(request):
    """تحديد جميع إشعارات الشكاوى كمقروءة"""
    if request.method == 'POST':
        try:
            from django.utils import timezone
            updated_count = ComplaintNotification.objects.filter(
                recipient=request.user,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )

            return JsonResponse({
                'success': True,
                'message': f'تم تحديد {updated_count} إشعار كمقروء',
                'updated_count': updated_count
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    return JsonResponse({'success': False, 'error': 'طريقة غير صحيحة'})


@login_required
def order_notifications_list(request):
    """قائمة إشعارات الطلبات"""
    notifications = SimpleNotification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')

    # فلترة حسب النوع
    notification_type = request.GET.get('type')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)

    # فلترة حسب الأولوية
    priority = request.GET.get('priority')
    if priority:
        notifications = notifications.filter(priority=priority)

    # فلترة حسب حالة القراءة
    read_status = request.GET.get('read')
    if read_status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif read_status == 'read':
        notifications = notifications.filter(is_read=True)

    # البحث
    search = request.GET.get('search')
    if search:
        notifications = notifications.filter(
            Q(title__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(order_number__icontains=search)
        )

    # التصفح
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'notifications': page_obj,
        'notification_types': SimpleNotification.TYPE_CHOICES,
        'priorities': SimpleNotification.PRIORITY_CHOICES,
        'current_filters': {
            'type': notification_type,
            'priority': priority,
            'read': read_status,
            'search': search,
        }
    }

    return render(request, 'accounts/notifications/order_list.html', context)


@login_required
def complaint_notifications_list(request):
    """قائمة إشعارات الشكاوى"""
    notifications = ComplaintNotification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')

    # فلترة حسب النوع
    complaint_type = request.GET.get('type')
    if complaint_type:
        notifications = notifications.filter(complaint_type=complaint_type)

    # فلترة حسب الأولوية
    priority = request.GET.get('priority')
    if priority:
        notifications = notifications.filter(priority=priority)

    # فلترة حسب حالة القراءة
    read_status = request.GET.get('read')
    if read_status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif read_status == 'read':
        notifications = notifications.filter(is_read=True)

    # البحث
    search = request.GET.get('search')
    if search:
        notifications = notifications.filter(
            Q(title__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(complaint_number__icontains=search)
        )

    # التصفح
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'notifications': page_obj,
        'complaint_types': ComplaintNotification.TYPE_CHOICES,
        'priorities': ComplaintNotification.PRIORITY_CHOICES,
        'current_filters': {
            'type': complaint_type,
            'priority': priority,
            'read': read_status,
            'search': search,
        }
    }

    return render(request, 'accounts/notifications/complaint_list.html', context)


@login_required
def notification_detail(request, notification_type, notification_id):
    """تفاصيل الإشعار"""
    if notification_type == 'order':
        notification = get_object_or_404(
            SimpleNotification,
            id=notification_id,
            recipient=request.user
        )
        template = 'accounts/notifications/order_detail.html'
    elif notification_type == 'complaint':
        notification = get_object_or_404(
            ComplaintNotification,
            id=notification_id,
            recipient=request.user
        )
        template = 'accounts/notifications/complaint_detail.html'
    else:
        return JsonResponse({'error': 'نوع إشعار غير صحيح'}, status=400)

    # تحديد كمقروء
    notification.mark_as_read()

    context = {
        'notification': notification,
    }

    return render(request, template, context)


@login_required
def group_notification_detail(request, notification_id):
    """تفاصيل الإشعار الجماعي مع تتبع القراءة"""
    from accounts.models import GroupNotification, GroupNotificationRead
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f'محاولة الوصول للإشعار {notification_id} من المستخدم {request.user.username}')

    try:
        # البحث عن الإشعار أولاً
        notification = GroupNotification.objects.filter(id=notification_id).first()
        logger.info(f'نتيجة البحث عن الإشعار: {notification is not None}')

        if not notification:
            logger.warning(f'الإشعار {notification_id} غير موجود')
            from django.http import Http404
            raise Http404(f'الإشعار رقم {notification_id} غير موجود')

        # التحقق من أن المستخدم مستهدف في هذا الإشعار
        is_target_user = notification.target_users.filter(id=request.user.id).exists()
        logger.info(f'هل المستخدم {request.user.username} مستهدف؟ {is_target_user}')

        if not is_target_user:
            target_users = [u.username for u in notification.target_users.all()]
            logger.warning(f'المستخدم {request.user.username} ليس مستهدف. المستهدفين: {target_users}')
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied(f'ليس لديك صلاحية لعرض هذا الإشعار. المستخدمين المستهدفين: {target_users}. أنت: {request.user.username}')

        # تحديد الإشعار كمقروء من قبل المستخدم الحالي
        logger.info(f'محاولة تحديد الإشعار {notification_id} كمقروء للمستخدم {request.user.username}')
        notification.mark_as_read_by_user(request.user)
        logger.info(f'تم تحديد الإشعار {notification_id} كمقروء بنجاح')

    except Exception as e:
        logger.error(f'خطأ في الوصول للإشعار {notification_id}: {str(e)}')
        import traceback
        logger.error(f'تفاصيل الخطأ: {traceback.format_exc()}')
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, f'خطأ في الوصول للإشعار: {str(e)}')
        return redirect('accounts:notifications_list')

    # جلب معلومات القراءة
    reads = GroupNotificationRead.objects.filter(
        notification=notification
    ).select_related('user').order_by('-read_at')

    # تحديد ما إذا كان المستخدم مدير نظام
    is_admin = request.user.is_superuser

    # للمدير: عرض جميع من قرأ الإشعار
    # للمستخدم العادي: عرض قراءته فقط إذا كان الإشعار مرتبط بطلب أنشأه
    user_read = None
    all_reads = []

    if is_admin:
        # المدير يرى جميع القراءات
        all_reads = reads
    else:
        # المستخدم العادي يرى قراءته فقط إذا كان الطلب مرتبط به
        user_read = reads.filter(user=request.user).first()

        # التحقق من أن الطلب مرتبط بالمستخدم
        is_related_to_user = False
        if notification.order_number:
            try:
                from orders.models import Order
                order = Order.objects.get(order_number=notification.order_number)
                # التحقق من أن المستخدم هو البائع أو منشئ الطلب
                if (order.salesperson and order.salesperson.user == request.user) or order.created_by == request.user:
                    is_related_to_user = True
            except Order.DoesNotExist:
                pass

        # إذا كان الطلب مرتبط بالمستخدم، يمكنه رؤية قراءته
        if not is_related_to_user:
            user_read = None

    context = {
        'notification': notification,
        'user_read': user_read,
        'all_reads': all_reads,
        'is_admin': is_admin,
        'read_count': notification.get_read_count(),
        'unread_count': notification.get_unread_count(),
        'total_users': notification.target_users.count(),
    }

    return render(request, 'accounts/notifications/group_notification_detail.html', context)


@login_required
def debug_notification(request, notification_id):
    """صفحة تشخيص الإشعار"""
    from accounts.models import GroupNotification
    from django.http import JsonResponse

    try:
        notification = GroupNotification.objects.filter(id=notification_id).first()

        debug_info = {
            'notification_id': notification_id,
            'notification_exists': notification is not None,
            'current_user': request.user.username,
            'current_user_id': request.user.id,
        }

        if notification:
            debug_info.update({
                'notification_title': notification.title,
                'target_users_count': notification.target_users.count(),
                'target_users': [u.username for u in notification.target_users.all()],
                'is_target_user': notification.target_users.filter(id=request.user.id).exists(),
                'notification_type': notification.notification_type,
                'created_at': str(notification.created_at),
            })

        return JsonResponse(debug_info, json_dumps_params={'ensure_ascii': False, 'indent': 2})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def mark_group_notification_read(request, notification_id):
    """تحديد الإشعار الجماعي كمقروء"""
    from accounts.models import GroupNotification
    from django.http import JsonResponse

    if request.method != 'POST':
        return JsonResponse({'error': 'طريقة غير مسموحة'}, status=405)

    try:
        notification = GroupNotification.objects.filter(
            id=notification_id,
            target_users=request.user
        ).first()

        if not notification:
            return JsonResponse({'error': 'الإشعار غير موجود'}, status=404)

        # تحديد الإشعار كمقروء
        notification.mark_as_read_by_user(request.user)

        return JsonResponse({'success': True, 'message': 'تم تحديد الإشعار كمقروء'})

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'خطأ في تحديد الإشعار {notification_id} كمقروء: {str(e)}')
        return JsonResponse({'error': f'خطأ في تحديد الإشعار كمقروء: {str(e)}'}, status=500)


@login_required
def notifications_list(request):
    """صفحة قائمة الإشعارات المبسطة"""
    from accounts.models import GroupNotification, GroupNotificationRead

    # جلب الإشعارات الجماعية التي يستطيع المستخدم رؤيتها
    notifications_query = GroupNotification.objects.filter(
        target_users=request.user
    ).order_by('-created_at')

    # إضافة معلومات القراءة لكل إشعار
    notifications = []
    unread_count = 0

    for notification in notifications_query:
        is_read = notification.is_read_by_user(request.user)
        notifications.append({
            'notification': notification,
            'is_read': is_read,
            'read_count': notification.get_read_count(),
            'total_users': notification.target_users.count(),
        })
        if not is_read:
            unread_count += 1

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'total_count': len(notifications),
        'is_admin': request.user.is_superuser,
    }

    return render(request, 'accounts/notifications_list.html', context)


@login_required
def complaints_list(request):
    """صفحة قائمة الشكاوى"""
    # مدير النظام والمدير العام ومسؤول المصنع يرون كل الشكاوى
    if request.user.is_superuser or \
       (hasattr(request.user, 'is_general_manager') and request.user.is_general_manager) or \
       (hasattr(request.user, 'is_factory_manager') and request.user.is_factory_manager):
        complaints = ComplaintNotification.objects.all().order_by('-created_at')
        unread_count = ComplaintNotification.objects.filter(is_read=False).count()
    else:
        # المستخدمون الآخرون يرون شكاواهم فقط
        complaints = ComplaintNotification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')
        unread_count = complaints.filter(is_read=False).count()

    total_count = complaints.count()

    context = {
        'complaints': complaints,
        'unread_count': unread_count,
        'total_count': total_count,
    }

    return render(request, 'accounts/complaints_list.html', context)
