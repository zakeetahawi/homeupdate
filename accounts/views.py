from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q

from .models import (
    Notification, CompanyInfo, FormField, Department,
    Salesperson, Branch, Role, UserRole
)
from .utils import get_user_notifications
from .forms import (
    CompanyInfoForm, FormFieldForm, DepartmentForm,
    SalespersonForm, RoleForm, RoleAssignForm
)

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
        form.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'اسم المستخدم'
        })
        form.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'كلمة المرور'
        })
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
                form.fields['username'].widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': 'اسم المستخدم'
                })
                form.fields['password'].widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': 'كلمة المرور'
                })

                if form.is_valid():
                    username = form.cleaned_data.get('username')
                    password = form.cleaned_data.get('password')
                    logger.info(f"Login attempt for user: {username}")

                    # محاولة المصادقة المباشرة
                    user = authenticate(
                        request=request,
                        username=username,
                        password=password
                    )

                    if user is not None:
                        login(request, user)
                        messages.success(request, f'مرحباً بك {username}!')
                        next_url = request.GET.get('next', 'home')
                        return redirect(next_url)
                    else:
                        messages.error(
                            request,
                            'اسم المستخدم أو كلمة المرور غير صحيحة.'
                        )
                else:
                    messages.error(
                        request,
                        'اسم المستخدم أو كلمة المرور غير صحيحة.'
                    )
            except Exception as auth_error:
                logger.error(f"[Authentication Error] {auth_error}")
                logger.error(traceback.format_exc())
                messages.error(
                    request,
                    'حدث خطأ أثناء محاولة تسجيل الدخول. يرجى المحاولة مرة أخرى.'
                )

        # التحقق من وجود مستخدمين في النظام
        try:
            from odoo_db_manager.models import SetupToken, DatabaseConfig

            if User.objects.count() == 0:
                # لا يوجد مستخدمين في النظام، توجيه المستخدم إلى صفحة الإعداد الأولي
                logger.info("No users found in the system, redirecting to setup page")

                # التحقق من وجود رمز إعداد صالح
                valid_token = SetupToken.objects.filter(is_used=False, is_expired=False).first()

                if not valid_token:
                    # إنشاء رمز إعداد جديد
                    from datetime import datetime, timedelta
                    valid_token = SetupToken.objects.create(
                        expires_at=datetime.now() + timedelta(hours=24)
                    )
                    messages.info(request, 'تم إنشاء رمز إعداد جديد للنظام. يرجى استخدامه لإعداد النظام لأول مرة.')

                # التحقق من وجود قاعدة بيانات نشطة
                if not DatabaseConfig.objects.filter(is_active=True).exists():
                    # إنشاء قاعدة بيانات افتراضية
                    import os
                    logger.info("No active database found, creating default database")

                    try:
                        # محاولة استخدام متغيرات البيئة
                        db_host = os.environ.get('DB_HOST', 'localhost')
                        db_port = os.environ.get('DB_PORT', '5432')
                        db_user = os.environ.get('DB_USER', 'crm_user')
                        db_password = os.environ.get('DB_PASSWORD', '5525')
                        db_name = os.environ.get('DB_NAME', 'crm_system')

                        # التحقق من وجود متغيرات البيئة الخاصة بـ PostgreSQL
                        if 'PGHOST' in os.environ:
                            db_host = os.environ.get('PGHOST')
                            db_port = os.environ.get('PGPORT', '5432')
                            db_user = os.environ.get('PGUSER', 'postgres')
                            db_password = os.environ.get('PGPASSWORD', '')
                            db_name = os.environ.get('PGDATABASE', 'postgres')

                            logger.info(f"Using PostgreSQL environment settings: {db_host}:{db_port}/{db_name}")

                        DatabaseConfig.objects.create(
                            name="قاعدة البيانات الرئيسية",
                            db_type="postgresql",
                            host=db_host,
                            port=db_port,
                            username=db_user,
                            password=db_password,
                            database_name=db_name,
                            is_active=True,
                            is_default=True
                        )
                    except Exception as db_error:
                        logger.error(f"Error creating default database: {db_error}")
                        logger.error(traceback.format_exc())

                        # إنشاء قاعدة بيانات افتراضية بقيم ثابتة
                        DatabaseConfig.objects.create(
                            name="قاعدة البيانات الرئيسية",
                            db_type="postgresql",
                            host="localhost",
                            port="5432",
                            username="crm_user",
                            password="5525",
                            database_name="crm_system",
                            is_active=True,
                            is_default=True
                        )

                # توجيه المستخدم إلى صفحة الإعداد
                try:
                    return redirect('odoo_db_manager:setup_with_token', token=valid_token.token)
                except Exception as redirect_error:
                    logger.error(f"Error redirecting to setup page: {redirect_error}")
                    logger.error(traceback.format_exc())

                    # محاولة توجيه بديلة
                    return redirect(f'/odoo-db-manager/setup/{valid_token.token}/')
        except Exception as setup_error:
            logger.error(f"[Setup Error] {setup_error}")
            logger.error(traceback.format_exc())
            # لا نقوم بإعادة رفع الاستثناء هنا، بل نستمر في عرض نموذج تسجيل الدخول

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
def notifications_list(request):
    """
    View for listing all notifications
    """
    # Get filter parameters
    filter_type = request.GET.get('filter', 'all')

    # Get all notifications for the user
    all_notifications = get_user_notifications(request.user)

    # Filter notifications based on read status
    if filter_type == 'unread':
        notifications = all_notifications.filter(is_read=False)
    elif filter_type == 'read':
        notifications = all_notifications.filter(is_read=True)
    else:  # 'all'
        notifications = all_notifications

    # Paginate notifications
    paginator = Paginator(notifications, 10)  # Show 10 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'title': 'الإشعارات',
    }
    return render(request, 'accounts/notifications.html', context)

@login_required
def notification_detail(request, notification_id):
    """
    View for notification detail
    """
    # Get notification
    notification = get_object_or_404(Notification, id=notification_id)

    # Check if user has access to this notification
    user_notifications = get_user_notifications(request.user)
    if notification not in user_notifications:
        messages.error(request, 'ليس لديك صلاحية للوصول إلى هذا الإشعار.')
        return redirect('accounts:notifications')

    # Mark notification as read
    if not notification.is_read:
        notification.mark_as_read(request.user)

    context = {
        'notification': notification,
        'title': notification.title,
    }
    return render(request, 'accounts/notification_detail.html', context)

@login_required
def mark_notification_read(request, notification_id):
    """
    View for marking notification as read
    """
    if request.method == 'POST':
        # Get notification
        notification = get_object_or_404(Notification, id=notification_id)

        # Check if user has access to this notification
        user_notifications = get_user_notifications(request.user)
        if notification not in user_notifications:
            return JsonResponse({
                'success': False,
                'message': 'ليس لديك صلاحية للوصول إلى هذا الإشعار.'
            })

        # Mark notification as read
        notification.mark_as_read(request.user)

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'طريقة غير صالحة.'})

@login_required
def mark_all_notifications_read(request):
    """
    View for marking all notifications as read
    """
    if request.method == 'POST':
        # Get all unread notifications for the user
        unread_notifications = get_user_notifications(
            request.user, unread_only=True
        )

        # Mark all as read
        for notification in unread_notifications:
            notification.mark_as_read(request.user)

        return JsonResponse({
            'success': True,
            'count': unread_notifications.count()
        })

    return JsonResponse({'success': False, 'message': 'طريقة غير صالحة.'})

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
            form = CompanyInfoForm(
                request.POST, request.FILES, instance=company
            )
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
        messages.error(
            request,
            'حدث خطأ غير متوقع أثناء معالجة معلومات الشركة. يرجى مراجعة الدعم الفني.'
        )
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
    departments = Department.objects.all()

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

    # جلب قائمة الأقسام الرئيسية للتصفية
    parent_departments = Department.objects.filter(parent__isnull=True)

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
            messages.error(
                request,
                'لا يمكن حذف القسم لأنه يحتوي على أقسام فرعية.'
            )
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
    salespersons = Salesperson.objects.all()

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

    # جلب قائمة الفروع للتصفية
    branches = Branch.objects.all()

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
        except Exception:
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
    عرض قائمة الأدوار مع إمكانية البحث
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

    # تقسيم الصفحات
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

            messages.success(
                request,
                f'تم إسناد دور {role.name} لـ {count} مستخدمين بنجاح.'
            )
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
    users = User.objects.filter(is_active=True).exclude(
        is_superuser=True
    ).prefetch_related('user_roles')

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
