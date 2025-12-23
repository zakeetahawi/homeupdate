from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from django.core.paginator import Paginator
from django.db.models import Count, Case, When, IntegerField
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Customer, CustomerCategory, CustomerNote
from orders.models import Order

from .forms import CustomerForm, CustomerSearchForm, CustomerNoteForm
from .permissions import (
    get_user_customers_queryset,
    can_user_view_customer,
    can_user_edit_customer,
    can_user_delete_customer,
    can_user_create_customer,
    get_user_customer_permissions,
    is_customer_cross_branch
)

def get_queryset_for_user(user, search_term=None):
    """دالة مساعدة للحصول على العملاء المسموح للمستخدم برؤيتهم"""
    from .models import Customer
    from django.db.models.query import QuerySet
    
    try:
        queryset = get_user_customers_queryset(user, search_term)
        
        # التأكد من أن النتيجة هي QuerySet صحيح
        if isinstance(queryset, QuerySet) and hasattr(queryset, 'select_related'):
            return queryset
        elif queryset is None:
            return Customer.objects.none()
        else:
            # إذا لم تكن QuerySet، إرجاع جميع العملاء كـ fallback
            print(f"Warning: get_user_customers_queryset returned unexpected type: {type(queryset)}")
            return Customer.objects.all()
    except Exception as e:
        # في حالة حدوث خطأ، إرجاع جميع العملاء كـ fallback مع طباعة تفاصيل الخطأ
        print(f"Error in get_queryset_for_user: {str(e)}")
        return Customer.objects.all()

@login_required
def customer_list(request):
    """
    View for displaying the list of customers with search and filtering
    تم تحسين الأداء باستخدام select_related وتحسين الاستعلامات
    مع إضافة الفلترة الشهرية
    """
    from core.monthly_filter_utils import apply_monthly_filter, get_available_years

    form = CustomerSearchForm(request.GET)

    # الحصول على معامل البحث أولاً
    search_term = request.GET.get('search', '').strip()

    # تمرير معامل البحث لدالة الصلاحيات
    queryset = get_queryset_for_user(request.user, search_term)

    # التحقق من أن queryset صحيح
    if not hasattr(queryset, 'select_related'):
        # إذا لم يكن QuerySet صحيح، استخدم جميع العملاء
        queryset = Customer.objects.all()

    customers = queryset.select_related(
        'category', 'branch', 'created_by'
    ).prefetch_related('customer_orders')

    # تطبيق الفلترة الشهرية (بناءً على تاريخ إنشاء العميل)
    customers, monthly_filter_context = apply_monthly_filter(customers, request, 'created_at')

    # تحسين الاستعلامات باستخدام الفهارس
    if form.is_valid():
        search = form.cleaned_data.get('search')
        category = form.cleaned_data.get('category')
        customer_type = form.cleaned_data.get('customer_type')
        status = form.cleaned_data.get('status')
        branch = form.cleaned_data.get('branch')

        # تحسين استعلام البحث
        if search:
            # استخدام استعلامات منفصلة لتحسين الأداء
            name_query = Q(name__icontains=search)
            code_query = Q(code__icontains=search)
            phone_query = Q(phone__icontains=search) | Q(phone2__icontains=search)
            email_query = Q(email__icontains=search)

            customers = customers.filter(
                name_query | code_query | phone_query | email_query
            )

        # استخدام الفهارس للتصفية
        if category:
            customers = customers.filter(category=category)

        if customer_type:
            customers = customers.filter(customer_type=customer_type)

        if status:
            customers = customers.filter(status=status)

        if branch:
            customers = customers.filter(branch=branch)

    # استخدام فهرس created_at للترتيب
    customers = customers.order_by('-created_at')

    # تحسين الأداء عن طريق حساب العدد الإجمالي مرة واحدة فقط
    total_customers = customers.count()

    # Pagination
    paginator = Paginator(customers, 10)  # Show 10 customers per page
    page_number = request.GET.get('page')
    
    # إصلاح مشكلة pagination عندما يكون page parameter array
    if page_number and isinstance(page_number, (list, tuple)):
        page_number = page_number[0] if page_number else '1'
    elif page_number and str(page_number).startswith('[') and str(page_number).endswith(']'):
        try:
            import re
            match = re.search(r'\[(\d+)\]', str(page_number))
            if match:
                page_number = match.group(1)
        except:
            page_number = '1'
    
    page_obj = paginator.get_page(page_number)

    # Store form values for template context
    search_value = request.GET.get('search', '')
    category_value = request.GET.get('category', '')
    customer_type_value = request.GET.get('customer_type', '')
    status_value = request.GET.get('status', '')
    branch_value = request.GET.get('branch', '')

    # معلومات فلتر السنة
    from customers.models import Customer

    # إضافة معلومات إضافية للعملاء من الفروع الأخرى - محسن لتجنب N+1
    cross_branch_customers = []
    if search_term and hasattr(request.user, 'branch') and request.user.branch:
        # جمع معرفات العملاء في قائمة واحدة بدلاً من استعلام منفصل لكل عميل
        customer_ids = [customer.pk for customer in page_obj]
        # استعلام واحد للتحقق من ال��ملاء من فروع أخرى
        cross_branch_customer_ids = Customer.objects.filter(
            pk__in=customer_ids
        ).exclude(branch=request.user.branch).values_list('pk', flat=True)
        cross_branch_customers = list(cross_branch_customer_ids)
    # الحصول على السنوات المتاحة للفلترة الشهرية
    available_years = get_available_years(Customer, 'created_at')
    selected_years = request.GET.getlist('years')
    year_filter = request.GET.get('year', '')

    # حساب الفلاتر النشطة للفلتر المضغوط
    active_filters = []
    if search_value:
        active_filters.append('search')
    if category_value:
        active_filters.append('category')
    if customer_type_value:
        active_filters.append('customer_type')
    if status_value:
        active_filters.append('status')
    if branch_value:
        active_filters.append('branch')
    if monthly_filter_context.get('selected_year'):
        active_filters.append('year')
    if monthly_filter_context.get('selected_month'):
        active_filters.append('month')

    # الحصول على البيانات المطلوبة للفلاتر
    from customers.models import CustomerCategory
    from accounts.models import Branch

    categories = CustomerCategory.objects.all()
    branches = Branch.objects.all()

    context = {
        'page_obj': page_obj,
        'form': form,
        'total_customers': total_customers,
        'search_query': search_value,  # للتوافق مع template
        'search_value': search_value,  # للتوافق مع form
        'category_value': category_value,
        'customer_type_value': customer_type_value,
        'status_value': status_value,
        'branch_value': branch_value,
        'cross_branch_customers': cross_branch_customers,
        'user_branch': request.user.branch,
        'available_years': available_years,
        'selected_years': selected_years,
        'year_filter': year_filter,
        # سياق الفلتر المضغوط
        'has_active_filters': len(active_filters) > 0,
        'active_filters_count': len(active_filters),
        'categories': categories,
        'branches': branches,
        # إضافة سياق الفلترة الشهرية
        **monthly_filter_context,
    }

    return render(request, 'customers/customer_list.html', context)

@login_required
def customer_detail(request, pk):
    """
    View for displaying customer details, orders, and notes
    تحسين الأداء باستخدام select_related و prefetch_related
    """
    print("=" * 80)
    print("🔥 CUSTOMER DETAIL VIEW STARTED!")
    print(f"🔥 Request URL: {request.get_full_path()}")
    print(f"🔥 Customer PK: {pk}")
    print("=" * 80)
    
    # الحصول على العميل مباشرة (مثل الصفحة التجريبية)
    try:
        customer = Customer.objects.select_related(
            'category', 'branch', 'created_by'
        ).get(pk=pk)
    except Customer.DoesNotExist:
        messages.error(request, "العميل غير موجود.")
        return redirect("customers:customer_list")

    # التحقق من الصلاحيات بعد جلب العميل
    is_cross_branch = is_customer_cross_branch(request.user, customer)
    if not can_user_view_customer(request.user, customer, allow_cross_branch=is_cross_branch):
        messages.error(request, "ليس لديك صلاحية لعرض هذا العميل.")
        return redirect("customers:customer_list")

    # إضافة ملاحظة عند الوصول لعميل من فرع آخر
    if is_cross_branch:
        CustomerNote.objects.create(
            customer=customer,
            note=f"تم الوصول لبيانات العميل من فرع {request.user.branch.name if request.user.branch else 'غير محدد'} بواسطة {request.user.get_full_name() or request.user.username}",
            created_by=request.user
        )

    # تحسين استعلام الطلبات باستخدام prefetch_related
    customer_orders = customer.customer_orders.select_related('customer', 'salesperson', 'branch').prefetch_related('items').order_by('-created_at')[:10]

    # Get orders with items only (for product orders)
    orders = []
    for order in customer_orders:
        # Include service orders always
        if hasattr(order, 'order_type') and order.order_type == 'service':
            orders.append(order)
        # Include product orders only if they have items
        elif hasattr(order, 'order_type') and order.order_type == 'product' and order.items.exists():
            orders.append(order)
        # Include all orders if order_type is not available (new structure)
        elif not hasattr(order, 'order_type') or order.order_type is None:
            orders.append(order)

    # تحسين استعلام المعاينات باستخدام select_related
    inspections = customer.inspections.select_related('customer', 'branch', 'created_by').order_by('-created_at')[:10]
    
    # إضافة معلومات تشخيصية مفصلة
    print("=" * 50)
    print(f"DEBUG START: Customer {customer.pk} - {customer.code}")
    print("=" * 50)
    print(f"DEBUG: Customer.inspections manager: {customer.inspections}")
    print(f"DEBUG: Inspections count: {customer.inspections.count()}")
    print(f"DEBUG: All inspections for customer: {list(customer.inspections.all().values_list('id', 'inspection_code', 'status', 'scheduled_date', 'customer_id'))}")
    print(f"DEBUG: Recent inspections: {list(inspections.values_list('inspection_code', 'status', 'scheduled_date'))}")
    print(f"DEBUG: Recent inspections objects: {list(inspections)}")
    
    # اختبار بديل للمعاينات - استعلام مباشر
    from inspections.models import Inspection
    direct_inspections = Inspection.objects.filter(customer=customer).order_by('-created_at')[:10]
    print(f"DEBUG: Direct inspections query: {list(direct_inspections.values_list('inspection_code', 'status', 'scheduled_date'))}")
    
    # إذا كان الاستعلام المباشر يحتوي على معاينات ولكن customer.inspections فارغ، استخدم الاستعلام المباشر
    if direct_inspections.exists() and not inspections.exists():
        print("DEBUG: Using direct inspections query as fallback")
        inspections = direct_inspections
    
    print("=" * 50)
    print("DEBUG END")
    print("=" * 50)

    # تحميل ملاحظات العميل مسبقًا
    customer_notes = customer.notes_history.select_related('created_by').order_by('-created_at')[:15]

    note_form = CustomerNoteForm()

    # تحديد الصلاحيات للعميل من فرع آخر
    can_edit = can_user_edit_customer(request.user, customer) and not is_cross_branch
    can_add_notes = True  # يمكن إضافة ملاحظات حتى للعملاء من فروع أخرى

    context = {
        'customer': customer,
        'orders': orders,
        'inspections': inspections,
        'note_form': note_form,
        'customer_notes': customer_notes,
        'is_cross_branch': is_cross_branch,
        'user_branch': request.user.branch,
        'can_edit': can_edit,
        'can_add_notes': can_add_notes,
    }

    return render(request, 'customers/customer_detail.html', context)

@login_required
@permission_required('customers.add_customer', raise_exception=True)
def customer_create(request):

    # التحقق من صلاحية المستخدم لإنشاء عميل
    if not can_user_create_customer(request.user):
        messages.error(request, "ليس لديك صلاحية لإنشاء عملاء.")
        return redirect("customers:customer_list")
    """
    View for creating a new customer with image upload
    """
    if not request.user.branch:
        messages.error(request, _('لا يمكنك إضافة عميل لأنك غير مرتبط بفرع'))
        return redirect('customers:customer_list')

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                customer = form.save(commit=False)
                customer.created_by = request.user

                # تعيين الفرع
                if request.user.branch.is_main_branch:
                    branch = form.cleaned_data.get('branch')
                    if not branch:
                        messages.error(request, _('يرجى اختيار الفرع'))
                        return render(request, 'customers/customer_form.html', {'form': form})
                    customer.branch = branch
                else:
                    customer.branch = request.user.branch

                customer.save()

                # معالجة بيانات المسؤولين للشركات والجهات الحكومية
                if customer.customer_type in ['corporate', 'government']:
                    save_customer_responsibles(request, customer)

                messages.success(request, _('تم إضافة العميل {} بنجاح').format(customer.name))
                return redirect('customers:customer_detail', pk=customer.pk)
            except Exception as e:
                messages.error(request, _('حدث خطأ أثناء حفظ العميل: {}').format(str(e)))
        else:
            print(f"Form errors: {form.errors}")  # للتشخيص
            # التحقق من وجود عميل مكرر لعرض البطاقة
            if 'phone' in form.errors and hasattr(form, 'existing_customer'):
                existing_customer = form.existing_customer
                context = {
                    'form': form,
                    'title': _('إضافة عميل جديد'),
                    'existing_customer': existing_customer,
                    'show_duplicate_alert': True
                }
                return render(request, 'customers/customer_form.html', context)
    else:
        form = CustomerForm(user=request.user)

    context = {
        'form': form,
        'title': _('إضافة عميل جديد')
    }
    return render(request, 'customers/customer_form.html', context)

@login_required
@permission_required('customers.change_customer', raise_exception=True)
def customer_update(request, pk):
    """
    View for updating customer details including image
    """

    try:
        customer = Customer.objects.select_related('branch').get(pk=pk)
    except Customer.DoesNotExist:
        messages.error(request, 'العميل غير موجود في قاعدة البيانات.')
        return redirect('customers:customer_list')

    # التحقق من صلاحية المستخدم لتعديل هذا العميل
    if not can_user_edit_customer(request.user, customer):
        messages.error(request, "ليس لديك صلاحية لتعديل هذا العميل.")
        return redirect("customers:customer_detail", pk=pk)

    # Check if user has access to this customer's branch
    if not request.user.is_superuser and customer.branch != request.user.branch:
        messages.error(request, 'لا يمكنك تعديل بيانات عميل في فرع آخر')
        return redirect('customers:customer_list')

    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES, instance=customer, user=request.user)
        if form.is_valid():
            try:
                updated_customer = form.save()

                # معالجة بيانات المسؤولين للشركات والجهات الحكومية
                if updated_customer.customer_type in ['corporate', 'government']:
                    save_customer_responsibles(request, updated_customer)
                else:
                    # حذف المسؤولين إذا تم تغيير نوع العميل
                    updated_customer.responsibles.all().delete()

                messages.success(request, 'تم تحديث بيانات العميل بنجاح.')
                return redirect('customers:customer_detail', pk=customer.pk)
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء تحديث بيانات العميل: {str(e)}')
    else:
        form = CustomerForm(instance=customer, user=request.user)

    context = {
        'form': form,
        'customer': customer,
        'title': 'تعديل بيانات العميل'
    }

    return render(request, 'customers/customer_form.html', context)

@login_required
@permission_required('customers.delete_customer', raise_exception=True)
def customer_delete(request, pk):
    """View for deleting a customer with proper error handling."""
    customer = get_object_or_404(Customer, pk=pk)

    # السماح فقط لمدير النظام بحذف العملاء
    if not request.user.is_superuser:
        messages.error(request, "❌ عذراً، فقط مدير النظام يمكنه حذف العملاء")
        return redirect("customers:customer_detail", pk=pk)

    # التحقق من صلاحية المستخدم لحذف هذا العميل
    if not can_user_delete_customer(request.user, customer):
        messages.error(request, "ليس لديك صلاحية لحذف هذا العميل.")
        return redirect("customers:customer_detail", pk=pk)

    # التحقق من صلاحية المستخدم لعرض هذا العميل
    if not can_user_view_customer(request.user, customer):
        messages.error(request, "ليس لديك صلاحية لعرض هذا العميل.")
        return redirect("customers:customer_list")

    # Check related records before attempting deletion
    has_related_records = False
    relations = {
        'inspections': _('معاينة'),
        'orders': _('طلب'),
        'installations': _('تركيب'),
    }

    related_counts = {}
    for rel, label in relations.items():
        if hasattr(customer, rel):
            count = getattr(customer, rel).count()
            if count > 0:
                has_related_records = True
                related_counts[label] = count

    if request.method == 'POST':
        if has_related_records:
            # Format message showing all related records
            records_msg = ', '.join(
                f'{count} {label}'
                for label, count in related_counts.items()
            )
            msg = (
                f'لا يمكن حذف العميل لوجود السجلات التالية: {records_msg}. '
                'يمكنك تعطيل حساب العميل بدلاً من حذفه.'
            )
            messages.error(request, msg)
            return redirect('customers:customer_detail', pk=customer.pk)

        try:
            customer.delete()
            messages.success(request, 'تم حذف العميل بنجاح.')
            return redirect('customers:customer_list')
        except ProtectedError as e:
            # Determine related records from protection error
            protected_objects = list(e.protected_objects)
            relations_found = {
                'inspection': _('معاينات'),
                'order': _('طلبات'),
                'installation': _('تركيبات')
            }

            found_relations = [
                rel_name
                for model_name, rel_name in relations_found.items()
                if any(obj._meta.model_name == model_name
                      for obj in protected_objects)
            ]

            if found_relations:
                records_msg = ' و'.join(found_relations)
                msg = (
                    f'لا يمكن حذف العميل لوجود {records_msg} مرتبطة به. '
                    'يمكنك تعطيل حساب العميل بدلاً من حذفه.'
                )
                messages.error(request, msg)
            return redirect('customers:customer_detail', pk=customer.pk)
        except Exception as e:
            msg = f'حدث خطأ أثناء محاولة حذف العميل: {str(e)}'
            messages.error(request, msg)
            return redirect('customers:customer_detail', pk=customer.pk)

    context = {'customer': customer}
    return render(request, 'customers/customer_confirm_delete.html', context)

@login_required
@require_POST
def add_customer_note(request, pk):
    """
    View for adding a note to a customer
    """
    try:
        customer = Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        messages.error(request, "العميل غير موجود.")
        return redirect("customers:customer_list")

    # التحقق من صلاحية المستخدم لعرض هذا العميل (مع السماح بالوصول عبر الفروع)
    is_cross_branch = is_customer_cross_branch(request.user, customer)
    if not can_user_view_customer(request.user, customer, allow_cross_branch=is_cross_branch):
        messages.error(request, "ليس لديك صلاحية لعرض هذا العميل.")
        return redirect("customers:customer_list")
    
    form = CustomerNoteForm(request.POST, user=request.user)

    if form.is_valid():
        try:
            note = form.save(commit=False)
            note.customer = customer
            note.created_by = request.user

            # إضافة معلوم��ت الفرع إذا كان من فرع مختلف
            if is_cross_branch:
                note.note = f"[من فرع {request.user.branch.name if request.user.branch else 'غير محدد'}] {note.note}"

            note.save()
            messages.success(request, 'تمت إضافة الملاحظة بنجاح.')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حفظ الملاحظة: {str(e)}')
    else:
        # إظهار أخطاء النموذج بالتفصيل
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                if field == 'note':
                    error_messages.append(str(error))
                else:
                    error_messages.append(f'{field}: {error}')

        if error_messages:
            messages.error(request, '; '.join(error_messages))
        else:
            messages.error(request, 'حدث خطأ أثناء إضافة الملاحظة.')

    return redirect('customers:customer_detail', pk=pk)

@login_required
@require_POST
def add_customer_note_by_code(request, customer_code):
    """
    View for adding a note to a customer using customer code
    """
    try:
        customer = Customer.objects.get(code=customer_code)
    except Customer.DoesNotExist:
        messages.error(request, "العميل غير موجود.")
        return redirect("customers:customer_list")

    # التحقق من صلاحية المستخدم لعرض هذا العميل (مع السماح بالوصول عبر الفروع)
    is_cross_branch = is_customer_cross_branch(request.user, customer)
    if not can_user_view_customer(request.user, customer, allow_cross_branch=is_cross_branch):
        messages.error(request, "ليس لديك صلاحية لعرض هذا العميل.")
        return redirect("customers:customer_list")

    form = CustomerNoteForm(request.POST, user=request.user)

    if form.is_valid():
        try:
            note_text = form.cleaned_data['note']

            # التحقق من عدم وجود ملاحظة مطابقة في آخر 30 ثانية لمنع التكرار
            from django.utils import timezone
            from datetime import timedelta

            # تنظيف النص للمقارنة
            clean_note_text = note_text.strip().lower()

            recent_notes = CustomerNote.objects.filter(
                customer=customer,
                created_by=request.user,
                created_at__gte=timezone.now() - timedelta(seconds=30)
            )

            # فحص النصوص المتشابهة
            for recent_note in recent_notes:
                if recent_note.note.strip().lower() == clean_note_text:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': 'تم إضافة هذه الملاحظة مؤخراً'})
                    messages.warning(request, 'تم إضافة هذه الملاحظة مؤخراً.')
                    return redirect("customers:customer_detail_by_code", customer_code=customer.code)


            note = form.save(commit=False)
            note.customer = customer
            note.created_by = request.user

            # إضافة معلومات الفرع إذا كان من فرع مختلف
            if is_cross_branch:
                note.note = f"[من فرع {request.user.branch.name if request.user.branch else 'غير محدد'}] {note.note}"

            note.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'تمت إضافة الملاحظة بنجاح'})

            messages.success(request, 'تمت إضافة الملاحظة بنجاح.')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': f'حدث خطأ أثناء حفظ الملاحظة: {str(e)}'})
            messages.error(request, f'حدث خطأ أثناء حفظ الملاحظة: {str(e)}')
    else:
        # إظهار أخطاء النموذج بالتفصيل
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                if field == 'note':
                    error_messages.append(str(error))
                else:
                    error_messages.append(f'{field}: {error}')

        if error_messages:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': '; '.join(error_messages)})
            messages.error(request, '; '.join(error_messages))
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'حدث خطأ أثناء إضافة الملاحظة.'})
            messages.error(request, 'حدث خطأ أثناء إضافة الملاحظة.')

    return redirect('customers:customer_detail_by_code', customer_code=customer_code)


@login_required
def delete_customer_note(request, customer_pk, note_pk):
    """
    View for deleting a customer note
    """
    note = get_object_or_404(CustomerNote, pk=note_pk, customer__pk=customer_pk)

    if request.method == 'POST':
        note.delete()
        messages.success(request, 'تم حذف الملاحظة بنجاح.')
        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error', 'message': 'طريقة طلب غير صالحة'})

@login_required
def customer_category_list(request):
    """
    View for displaying customer categories
    """
    categories = CustomerCategory.objects.all()
    context = {
        'categories': categories
    }
    return render(request, 'customers/category_list.html', context)

@login_required
def add_customer_category(request):
    """
    View for adding a new customer category
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        if name:
            category = CustomerCategory.objects.create(
                name=name,
                description=description
            )
            return JsonResponse({
                'status': 'success',
                'category': {
                    'id': category.id,
                    'name': category.name
                }
            })

    return JsonResponse({'status': 'error', 'message': 'بيانات غير صالحة'})

@login_required
@require_POST
def delete_customer_category(request, category_id):
    """
    View for deleting a customer category
    """
    category = get_object_or_404(CustomerCategory, pk=category_id)

    # Only allow deletion if no customers are using this category
    if category.customers.exists():
        return JsonResponse({
            'status': 'error',
            'message': 'لا يمكن حذف التصنيف لأنه مرتبط بعملاء'
        })

    category.delete()
    return JsonResponse({'status': 'success'})

@login_required
def get_customer_notes(request, pk):
    """API endpoint to get customer notes"""
    customer = get_object_or_404(Customer, pk=pk)

    # التحقق من صلاحية المستخدم لحذف هذا العميل
    if not can_user_delete_customer(request.user, customer):
        messages.error(request, "ليس لديك صلاحية لحذف هذا العميل.")
        return redirect("customers:customer_detail", pk=pk)

    # التحقق من صلاحية المستخدم لعرض هذا العميل
    if not can_user_view_customer(request.user, customer):
        messages.error(request, "ليس لديك صلاحية لعرض هذا العميل.")
        return redirect("customers:customer_list")
    notes = customer.notes_history.all().order_by('-created_at')
    notes_data = [{
        'note': note.note,
        'created_at': note.created_at.strftime('%Y-%m-%d %H:%M'),
        'created_by': note.created_by.get_full_name() or note.created_by.username
    } for note in notes]

    return JsonResponse({'notes': notes_data})

@login_required
def get_customer_details(request, pk):
    """API endpoint to get customer details"""
    try:
        customer = get_object_or_404(Customer, pk=pk)

        # التحقق من صلاحية المستخدم لعرض هذا العميل
        if not can_user_view_customer(request.user, customer):
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية لعرض هذا العميل.'
            }, status=403)

        customer_data = {
            'id': customer.id,
            'name': customer.name,
            'code': customer.code,
            'phone': customer.phone,
            'email': customer.email or '',
            'address': customer.address or '',
            'customer_type': customer.get_customer_type_display() if hasattr(customer, 'customer_type') else '',
            'status': customer.get_status_display() if hasattr(customer, 'status') else 'نشط'
        }

        return JsonResponse({
            'success': True,
            'customer': customer_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'خطأ في جلب بيانات العميل: {str(e)}'
        }, status=500)


class CustomerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'customers/dashboard.html'

    def get_context_data(self, **kwargs):
        """
        تحسين أداء لوحة التحكم باستخدام استعلامات أكثر كفاءة
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # تطبيق نظام الصلاحيات - الحصول على العملاء حسب دور المستخدم
        try:
            customers = get_user_customers_queryset(user)

            # التحقق من أن customers هو QuerySet صحيح
            if not hasattr(customers, 'select_related'):
                customers = Customer.objects.all()

            customers = customers.select_related("category", "branch", "created_by")

            # تطبيق فلتر السنة مع إمكانية الاستثناء
            from accounts.utils import apply_default_year_filter
            customers = apply_default_year_filter(customers, self.request, 'created_at', 'customers')

        except Exception as e:
            print(f"Error in CustomerDashboardView: {str(e)}")
            customers = Customer.objects.select_related("category", "branch", "created_by")

        # استخدام استعلامات أكثر كفاءة
        from django.db.models import Count, Case, When, IntegerField

        # استخدام استعلام واحد للحصول على جميع الإحصائيات
        customer_stats = customers.aggregate(
            total=Count('id'),
            active=Count(Case(When(status='active', then=1), output_field=IntegerField())),
            inactive=Count(Case(When(status='inactive', then=1), output_field=IntegerField()))
        )

        context['total_customers'] = customer_stats['total']
        context['active_customers'] = customer_stats['active']
        context['inactive_customers'] = customer_stats['inactive']

        # تحميل العملاء الأخيرين مع البيانات المرتبطة
        context['recent_customers'] = customers.order_by('-created_at')[:10]

        return context

@login_required
def test_customer_form(request):
    """Test view for debugging customer form"""
    form = CustomerForm(user=request.user)
    return render(request, '../test_form.html', {'form': form})

@login_required
def find_customer_by_phone(request):
    """API: البحث عن عميل برقم الهاتف وإرجاع بياناته JSON"""
    phone = request.GET.get('phone')
    if not phone:
        return JsonResponse({'found': False, 'error': 'رقم الهاتف مطلوب'}, status=400)
    
    # البحث المحسن برقم الهاتف
    phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '')
    customers = Customer.objects.filter(
        Q(phone__icontains=phone) | 
        Q(phone2__icontains=phone) |
        Q(phone__icontains=phone_clean) | 
        Q(phone2__icontains=phone_clean) |
        Q(phone=phone) | 
        Q(phone2=phone)
    ).select_related('branch')
    
    if customers.exists():
        customer_data = []
        for customer in customers:
            is_cross_branch = is_customer_cross_branch(request.user, customer)
            customer_data.append({
                'id': customer.pk,
                'name': customer.name,
                'code': customer.code,
                'branch': customer.branch.name if customer.branch else 'غير محدد',
                'phone': customer.phone,
                'phone2': customer.phone2,
                'email': customer.email,
                'address': customer.address,
                'url': f"/customers/{customer.pk}/",
                'is_cross_branch': is_cross_branch,
                'can_create_order': True,  # يمكن إنشاء طلبات لجميع العملاء
                'can_edit': not is_cross_branch,  # يمكن التعديل فقط لعملاء نفس الفرع
            })
        
        return JsonResponse({
            'found': True,
            'customers': customer_data,
            'count': len(customer_data)
        })
    
    return JsonResponse({'found': False})

@login_required
def check_customer_phone(request):
    """API: التحقق من وجود عميل برقم الهاتف مع validation للصيغة"""
    import re

    phone = request.GET.get('phone', '').strip()
    customer_id = request.GET.get('customer_id')  # لاستثناء العميل الحالي عند التعديل

    if not phone:
        return JsonResponse({
            'valid': False,
            'found': False,
            'error': 'رقم الهاتف مطلوب'
        }, status=400)

    # تنظيف الرقم من المسافات والرموز
    phone = re.sub(r'[^\d]', '', phone)

    # فحص صيغة الرقم
    if not re.match(r'^01[0-9]{9}$', phone):
        return JsonResponse({
            'valid': False,
            'found': False,
            'error': 'رقم الهاتف يجب أن يكون 11 رقم ويبدأ بـ 01 (مثال: 01234567890)'
        })

    # فحص التكرار
    qs = Customer.objects.filter(Q(phone=phone) | Q(phone2=phone))

    # استثناء العميل الحالي عند التعديل
    if customer_id:
        try:
            qs = qs.exclude(pk=int(customer_id))
        except (ValueError, TypeError):
            pass

    customer = qs.first()
    if customer:
        # تحديد أي رقم هو المكرر
        phone_field = 'phone' if customer.phone == phone else 'phone2'
        return JsonResponse({
            'valid': True,
            'found': True,
            'error': f'رقم الهاتف مستخدم بالفعل للعميل: {customer.name}',
            'customer': {
                'id': customer.pk,
                'name': customer.name,
                'branch': customer.branch.name if customer.branch else 'غير محدد',
                'phone': customer.phone,
                'phone2': customer.phone2,
                'email': customer.email,
                'address': customer.address,
                'url': f"/customers/{customer.pk}/",
                'duplicate_field': phone_field
            }
        })

    return JsonResponse({
        'valid': True,
        'found': False,
        'message': 'رقم الهاتف متاح للاستخدام'
    })

@login_required
@require_POST
def update_customer_address(request, pk):
    """تحديث عنوان العميل ونوع المكان"""
    try:
        customer = get_object_or_404(Customer, pk=pk)
    except Customer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'العميل غير موجود'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ أثناء تحديث عنوان العميل: {str(e)}'
        })

    # التحقق من صلاحية المستخدم لحذف هذا العميل
    if not can_user_delete_customer(request.user, customer):
        messages.error(request, "ليس لديك صلاحية لحذف هذا العميل.")
        return redirect("customers:customer_detail", pk=pk)

    # التحقق من صلاحية المستخدم لعرض هذا العميل
    if not can_user_view_customer(request.user, customer):
        messages.error(request, "ليس لديك صلاحية لعرض هذا العميل.")
        return redirect("customers:customer_list")

    # التحقق من الصلاحيات
    if not request.user.is_superuser and request.user.branch != customer.branch:
        return JsonResponse({
            'success': False,
            'error': 'ليس لديك صلاحية لتحديث هذا العميل'
        })

    address = request.POST.get('address', '').strip()
    location_type = request.POST.get('location_type', '').strip()

    if not address:
        return JsonResponse({
            'success': False,
            'error': 'العنوان مطلوب'
        })

    # تحديث عنوان العميل ونوع المكان
    customer.address = address
    if location_type:
        customer.location_type = location_type
    customer.save()

    return JsonResponse({
        'success': True,
        'message': 'تم تحديث عنوان العميل بنجاح',
        'address': customer.address,
        'location_type': customer.location_type
    })

@login_required
def customer_api(request):
    """
    API endpoint for Select2 customer search
    يدعم البحث بالاسم والهاتف والبريد الإلكتروني
    """
    search_term = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = 20
    
    # الحصول على العملاء المسموح للمستخدم برؤيتهم
    try:
        customers = get_user_customers_queryset(request.user, search_term)
        
        # التحقق من أن customers هو QuerySet صحيح
        if not hasattr(customers, 'filter'):
            customers = Customer.objects.all()
    except Exception as e:
        print(f"Error in customer_api: {str(e)}")
        customers = Customer.objects.all()
    
    # إذا كان هناك مصطلح بحث، تطبيق التصفية
    if search_term:
        customers = customers.filter(
            Q(name__icontains=search_term) |
            Q(phone__icontains=search_term) |
            Q(email__icontains=search_term)
        )
    
    # ترتيب النتائج
    customers = customers.order_by('name')
    
    # تطبيق التصفح
    paginator = Paginator(customers, page_size)
    page_obj = paginator.get_page(page)
    
    # تحويل البيانات للصيغة المطلوبة
    results = []
    for customer in page_obj:
        results.append({
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email or '',
            'address': customer.address or '',
            'branch': customer.branch.name if customer.branch else ''
        })
    
    return JsonResponse({
        'results': results,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_count': paginator.count
    })

@login_required
def customer_detail_by_code(request, customer_code):
    """
    View for displaying customer details using customer code
    عرض تفاصيل العميل باستخدام كود العميل
    """
    
    try:
        # البحث عن العميل في جميع العملاء أولاً
        customer = Customer.objects.select_related(
            'category', 'branch', 'created_by'
        ).get(code=customer_code)

        # تحديد ما إذا كان العميل من فرع آخر
        is_cross_branch = is_customer_cross_branch(request.user, customer)

        # للمستخدمين المشرفين، نعرض سجل الوصول إذا كان العميل من فرع مختلف
        show_cross_branch_alert = is_cross_branch
        if request.user.is_superuser and hasattr(request.user, 'branch') and request.user.branch:
            show_cross_branch_alert = customer.branch != request.user.branch

    except Customer.DoesNotExist:
        messages.error(request, f"العميل بكود {customer_code} غير موجود.")
        return redirect("customers:customer_list")

    # التحقق من صلاحية المستخدم لعرض هذا العميل
    if not can_user_view_customer(request.user, customer, allow_cross_branch=is_cross_branch):
        messages.error(request, "ليس لديك صلاحية لعرض هذا العميل.")
        return redirect("customers:customer_list")

    # تسجيل الوصول للعميل
    from customers.models import CustomerAccessLog
    from django.utils import timezone
    from datetime import timedelta

    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    # التحقق من عدم وجود سجل وصول مماثل في آخر دقيقة لتجنب التكرار
    one_minute_ago = timezone.now() - timedelta(minutes=1)
    recent_access = CustomerAccessLog.objects.filter(
        customer=customer,
        user=request.user,
        accessed_at__gte=one_minute_ago
    ).exists()

    if not recent_access:
        CustomerAccessLog.objects.create(
            customer=customer,
            user=request.user,
            user_branch=getattr(request.user, 'branch', None),
            customer_branch=customer.branch,
            is_cross_branch=is_cross_branch,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    # إضافة ملاحظة عند الوصول لعميل من فرع آخر
    if is_cross_branch:
        from django.utils import timezone
        from datetime import timedelta

        # التحقق من عدم وجود ملاحظة وصول مماثلة في آخر ساعة
        access_note_text = f"تم الوصول لبيانات العميل من فرع {request.user.branch.name if request.user.branch else 'غير محدد'} بواسطة {request.user.get_full_name() or request.user.username}"

        recent_access_notes = CustomerNote.objects.filter(
            customer=customer,
            created_by=request.user,
            note__icontains="تم الوصول لبيانات العميل",
            created_at__gte=timezone.now() - timedelta(hours=1)
        )

        if not recent_access_notes.exists():
            CustomerNote.objects.create(
                customer=customer,
                note=access_note_text,
                created_by=request.user
            )

    # تحسين استعلام الطلبات باستخدام prefetch_related
    customer_orders = customer.customer_orders.select_related(
        'customer', 'salesperson', 'branch'
    ).prefetch_related('items').order_by('-created_at')[:10]

    # Get orders with items only (for product orders)
    orders = []
    for order in customer_orders:
        # Include service orders always
        if hasattr(order, 'order_type') and order.order_type == 'service':
            orders.append(order)
        # Include product orders only if they have items
        elif hasattr(order, 'order_type') and order.order_type == 'product' and order.items.exists():
            orders.append(order)
        # For backward compatibility with orders without order_type
        else:
            orders.append(order)

    # تحسين استعلام المعاينات باستخدام select_related
    inspections = customer.inspections.select_related('customer', 'branch', 'created_by').order_by('-created_at')[:10]

    # تحسين استعلام الملاحظات مع التحقق من وجود العلاقة
    try:
        notes = customer.notes_history.select_related('created_by').order_by('-created_at')[:5]
    except AttributeError:
        # في حالة فشل select_related، نحاول الحصول على الملاحظات بدونها
        notes = customer.notes_history.all().order_by('-created_at')[:5]

    # جلب سجلات الوصول للعميل
    access_logs = customer.access_logs.select_related(
        'user', 'user_branch', 'customer_branch'
    ).order_by('-accessed_at')[:20]

    # الحصول على صلاحيات المستخدم لهذا العميل
    permissions = get_user_customer_permissions(request.user)

    context = {
        'customer': customer,
        'orders': orders,
        'inspections': inspections,
        'notes': notes,
        'access_logs': access_logs,
        'permissions': permissions,
        'is_cross_branch': is_cross_branch,
        'show_cross_branch_alert': show_cross_branch_alert,
        'user_branch': request.user.branch,
        'note_form': CustomerNoteForm(),  # إضافة نموذج الملاحظة
        'can_edit': can_user_edit_customer(request.user, customer),
    }

    return render(request, 'customers/customer_detail.html', context)

@login_required
def customer_detail_redirect(request, pk):
    """
    Redirect old ID-based URLs to code-based URLs
    إعادة توجيه الروابط القديمة المبنية على ID إلى الروابط المبنية على الكود
    """
    try:
        customer = Customer.objects.get(pk=pk)
        return redirect('customers:customer_detail_by_code', customer_code=customer.code)
    except Customer.DoesNotExist:
        messages.error(request, "العميل غير موجود.")
        return redirect("customers:customer_list")


def save_customer_responsibles(request, customer):
    """
    حفظ بيانات مسؤولي العميل من النموذج
    """
    from .models import CustomerResponsible

    # حذف المسؤولين الحاليين
    customer.responsibles.all().delete()

    # جمع بيانات المسؤولين من النموذج
    responsibles_data = []
    for key, value in request.POST.items():
        if key.startswith('responsible_') and key.endswith('_name'):
            # استخراج رقم المسؤول
            parts = key.split('_')
            if len(parts) >= 3:
                responsible_id = parts[1]
                name = value.strip()

                if name:  # فقط إذا كان الاسم موجود
                    position = request.POST.get(f'responsible_{responsible_id}_position', '').strip()
                    phone = request.POST.get(f'responsible_{responsible_id}_phone', '').strip()
                    email = request.POST.get(f'responsible_{responsible_id}_email', '').strip()
                    is_primary = request.POST.get(f'responsible_{responsible_id}_is_primary') == 'on'

                    responsibles_data.append({
                        'name': name,
                        'position': position,
                        'phone': phone,
                        'email': email,
                        'is_primary': is_primary,
                        'order': int(responsible_id)
                    })

    # ترتيب المسؤولين حسب الترتيب
    responsibles_data.sort(key=lambda x: x['order'])

    # التأكد من وجود مسؤول رئيسي واحد فقط
    primary_count = sum(1 for r in responsibles_data if r['is_primary'])
    if primary_count == 0 and responsibles_data:
        # إذا لم يكن هناك مسؤول رئيسي، اجعل الأول رئيسي
        responsibles_data[0]['is_primary'] = True
    elif primary_count > 1:
        # إذا كان هناك أكثر من مسؤول رئيسي، اجعل الأول فقط رئيسي
        primary_set = False
        for r in responsibles_data:
            if r['is_primary'] and not primary_set:
                primary_set = True
            elif r['is_primary'] and primary_set:
                r['is_primary'] = False

    # حفظ المسؤولين
    for i, responsible_data in enumerate(responsibles_data, 1):
        CustomerResponsible.objects.create(
            customer=customer,
            name=responsible_data['name'],
            position=responsible_data['position'],
            phone=responsible_data['phone'],
            email=responsible_data['email'],
            is_primary=responsible_data['is_primary'],
            order=i
        )
