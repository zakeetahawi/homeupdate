import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Order, OrderItem, Payment
from .forms import OrderForm, OrderItemFormSet, PaymentForm
from .permissions import get_user_orders_queryset, can_user_view_order, can_user_edit_order, can_user_delete_order
from accounts.models import Branch, Salesperson, Department, Notification, SystemSettings
from customers.models import Customer
from inventory.models import Product
from inspections.models import Inspection
from datetime import datetime, timedelta
from django.db import models
import traceback

class OrdersDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'orders/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # تطبيق نظام الصلاحيات - الحصول على الطلبات حسب دور المستخدم
        orders = get_user_orders_queryset(self.request.user)

        # Basic statistics
        context['total_orders'] = orders.count()
        context['pending_orders'] = orders.filter(status='pending').count()
        context['completed_orders'] = orders.filter(status='completed').count()
        context['recent_orders'] = orders.order_by('-created_at')[:10]

        # Sales statistics
        context['total_sales'] = orders.filter(status='completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        context['monthly_sales'] = orders.filter(created_at__month=today.month).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        return context

@login_required
def order_list(request):
    """
    View for displaying the list of orders with search and filtering
    """
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    page_size = request.GET.get('page_size', '25')
    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        elif page_size < 1:
            page_size = 25
    except Exception:
        page_size = 25


    # Branch filter for main branch users
    show_branch_filter = False
    branch_filter = request.GET.get('branch', '')
    user_branch = getattr(request.user, 'branch', None)
    if user_branch and getattr(user_branch, 'is_main_branch', False):
        show_branch_filter = True

    # إذا كان المستخدم من الفرع الرئيسي واختار فرعًا من الفلتر، اعرض فقط طلبات هذا الفرع
    if show_branch_filter and branch_filter:
        orders = Order.objects.select_related('customer', 'salesperson').filter(branch__id=branch_filter)
    else:
        orders = get_user_orders_queryset(request.user).select_related('customer', 'salesperson')

    # تطبيق فلتر السنة مع دعم السنوات المتعددة والسنة الافتراضية
    selected_years = request.GET.getlist('years')
    year_filter = request.GET.get('year', '')
    
    # إذا تم تحديد سنوات متعددة
    if selected_years:
        try:
            year_filters = Q()
            for year_str in selected_years:
                if year_str != 'all':
                    year = int(year_str)
                    year_filters |= Q(order_date__year=year)
            
            if year_filters:
                orders = orders.filter(year_filters)
        except (ValueError, TypeError):
            pass
    # إذا تم تحديد سنة واحدة فقط
    elif year_filter and year_filter != 'all':
        try:
            year = int(year_filter)
            orders = orders.filter(order_date__year=year)
        except (ValueError, TypeError):
            pass
    # إذا لم يتم تحديد أي سنة، استخدم السنة الافتراضية من الإعدادات
    else:
        from accounts.models import DashboardYearSettings
        default_year = DashboardYearSettings.get_default_year()
        orders = orders.filter(order_date__year=default_year)

    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer__name__icontains=search_query) |
            Q(customer__phone__icontains=search_query) |
            Q(contract_number__icontains=search_query) |
            Q(invoice_number__icontains=search_query) |
            Q(salesperson__name__icontains=search_query) |
            Q(branch__name__icontains=search_query) |
            Q(notes__icontains=search_query) |
            Q(selected_types__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(order_date__icontains=search_query) |
            Q(expected_delivery_date__icontains=search_query)
        )

    if status_filter:
        orders = orders.filter(status=status_filter)

    order_type_filter = request.GET.get('order_type', '')
    if order_type_filter:
        orders = orders.filter(selected_types__icontains=order_type_filter)

    # Order by created_at
    orders = orders.order_by('-created_at')

    # Pagination
    paginator = Paginator(orders, page_size)  # Show page_size orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get currency symbol from system settings
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'

    # معلومات فلتر السنة
    available_years = Order.objects.dates('order_date', 'year', order='DESC')
    available_years = [year.year for year in available_years]

    # Branches for filter dropdown
    branches = []
    if show_branch_filter:
        branches = Branch.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'order_type_filter': order_type_filter,
        'year_filter': year_filter,
        'selected_years': selected_years,
        'available_years': available_years,
        'current_year': timezone.now().year,
        'total_orders': orders.count(),
        'currency_symbol': currency_symbol,  # Add currency symbol to context
        'page_size': page_size,
        'show_branch_filter': show_branch_filter,
        'branches': branches,
        'branch_filter': branch_filter,
    }

    return render(request, 'orders/order_list.html', context)


@login_required
def order_success(request, pk):
    """عرض صفحة نجاح إنشاء الطلب"""
    try:
        order = Order.objects.get(pk=pk)

        # السماح فقط لمن يملك صلاحية إضافة طلب
        if not request.user.has_perm('orders.add_order'):
            messages.error(request, 'ليس لديك صلاحية لعرض هذه الصفحة.')
            return redirect('orders:order_list')

        context = {
            'order': order,
            'title': f'تم إنشاء الطلب بنجاح - {order.order_number}'
        }

        return render(request, 'orders/order_success.html', context)

    except Order.DoesNotExist:
        messages.error(request, 'الطلب غير موجود.')
        return redirect('orders:order_list')

@login_required
def order_detail(request, pk):
    """
    View for displaying order details
    """
    order = get_object_or_404(Order, pk=pk)

    # التحقق من صلاحية المستخدم لحذف أو تعديل أو عرض هذا الطلب
    if not can_user_view_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لعرض هذا الطلب.")
        return redirect("orders:order_list")
    if not can_user_edit_order(request.user, order):
        messages.warning(request, "ليس لديك صلاحية لتعديل هذا الطلب.")
    if not can_user_delete_order(request.user, order):
        messages.warning(request, "ليس لديك صلاحية لحذف هذا الطلب.")
    payments = order.payments.all().order_by('-payment_date')

    # Now all information is in the Order model
    order_items = order.items.all()

    # Get inspections related to this order
    inspections = []
    selected_types = order.get_selected_types_list()
    if 'inspection' in selected_types:
        # Get inspections directly related to this order
        inspections = order.inspections.all().order_by('-created_at')

        # If no direct inspections, get inspections for this customer created after this order
        if not inspections.exists():
            inspections = Inspection.objects.filter(
                customer=order.customer,
                created_at__gte=order.created_at
            ).order_by('-created_at')

    # Get currency symbol from system settings
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'

    context = {
        'order': order,
        'payments': payments,
        'order_items': order_items,
        'inspections': inspections,
        'currency_symbol': currency_symbol,  # Add currency symbol to context
    }

    return render(request, 'orders/order_detail.html', context)

@login_required
@permission_required('orders.add_order', raise_exception=True)
def order_create(request):
    """
    View for creating a new order
    """
    if request.method == 'POST':
        print("POST DATA:", request.POST)
        # الحصول على معرف العميل من POST أو GET
        customer_id = request.POST.get('customer')
        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                customer = None
        
        form = OrderForm(request.POST, request.FILES, user=request.user, customer=customer)
        
        if form.is_valid():
            print("Form is valid. Proceeding to save.")
            try:
                # Save order
                # 1. إنشاء كائن الطلب بدون حفظه
                order = form.save(commit=False)
                order.created_by = request.user

                # 2. تعيين الفرع إذا لم يتم توفيره
                if not order.branch:
                    order.branch = request.user.branch

                # 3. معالجة حقل المعاينة المرتبطة
                related_inspection_value = form.cleaned_data.get('related_inspection')
                if related_inspection_value == 'customer_side':
                    order.related_inspection_type = 'customer_side'
                    order.related_inspection = None
                elif related_inspection_value and related_inspection_value != '':
                    try:
                        from inspections.models import Inspection
                        inspection = Inspection.objects.get(id=related_inspection_value)
                        order.related_inspection = inspection
                        order.related_inspection_type = 'inspection'
                    except Inspection.DoesNotExist:
                        order.related_inspection = None
                        order.related_inspection_type = None
                else:
                    order.related_inspection = None
                    order.related_inspection_type = None

                # 4. حفظ الطلب في قاعدة البيانات للحصول على مفتاح أساسي
                order.save()

                # التأكد من أن الطلب تم حفظه بنجاح وله مفتاح أساسي
                if not order.pk:
                    raise Exception("فشل في حفظ الطلب: لم يتم إنشاء مفتاح أساسي")

                # 5. معالجة المنتجات المحددة إن وجدت
                selected_products_json = request.POST.get('selected_products', '')
                print("selected_products_json:", selected_products_json)
                total = 0
                if selected_products_json:
                    try:
                        selected_products = json.loads(selected_products_json)
                        print("selected_products:", selected_products)
                        for product_data in selected_products:
                            item = OrderItem.objects.create(
                                order=order,
                                product_id=product_data['product_id'],
                                quantity=product_data['quantity'],
                                unit_price=product_data['unit_price'],
                                item_type=product_data.get('item_type', 'product'),
                                notes=product_data.get('notes', '')
                            )
                            print("تم إنشاء عنصر:", item)
                            total += item.quantity * item.unit_price
                            print("total حتى الآن:", total)
                    except Exception as e:
                        print(f"Error creating order items: {e}")
                order.final_price = total
                order.save(update_fields=['final_price'])
                print("order.final_price بعد الحفظ:", order.final_price)
                # تحديث المبلغ الإجمالي ليعكس السعر النهائي
                order.total_amount = order.final_price
                order.save(update_fields=['total_amount'])

                # --- معالجة الدفعة (بعد تحديث final_price) ---
                paid_amount = request.POST.get('paid_amount')
                payment_verified = request.POST.get('payment_verified')
                payment_notes = request.POST.get('payment_notes', '')
                payment_reference = request.POST.get('payment_reference', '')
                try:
                    paid_amount = float(paid_amount or 0)
                except Exception:
                    paid_amount = 0
                if paid_amount > 0:
                    from .models import Payment
                    Payment.objects.create(
                        order=order,
                        amount=paid_amount,
                        payment_method='cash',
                        created_by=request.user,
                        notes=payment_notes,
                        reference_number=payment_reference
                    )
                if payment_verified == '1':
                    order.payment_verified = True
                    order.save(update_fields=['payment_verified'])

                # 6. معالجة عناصر الطلب من النموذج
                formset = OrderItemFormSet(request.POST, prefix='items', instance=order)
                if formset.is_valid():
                    formset.save()
                else:
                    print("Formset errors:", formset.errors)

                messages.success(request, 'تم إنشاء الطلب بنجاح!')
                return redirect('orders:order_success', pk=order.pk)

            except Exception as e:
                print("حدث خطأ أثناء حفظ الطلب:", e)
                print(traceback.format_exc())
                messages.error(request, f'حدث خطأ أثناء حفظ الطلب: {e}')
        else:
            print("--- FORM IS INVALID ---")
            print("Validation Errors:", form.errors)
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج.')
    else:
        # GET request - الحصول على معرف العميل من GET إذا كان موجوداً
        customer_id = request.GET.get('customer')
        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                customer = None
        
        form = OrderForm(user=request.user, customer=customer)

    # Get currency symbol from system settings
    currency_symbol = 'ج.م'

    context = {
        'form': form,
        'customer': customer,  # إضافة العميل للسياق
        'currency_symbol': currency_symbol,
        'title': 'إنشاء طلب جديد'
    }

    return render(request, 'orders/order_form.html', context)

@login_required
@permission_required('orders.change_order', raise_exception=True)
def order_update(request, pk):
    """
    View for updating an existing order
    """
    order = get_object_or_404(Order, pk=pk)

    # التحقق من صلاحية المستخدم لتعديل هذا الطلب

    # التحقق من صلاحية المستخدم لحذف هذا الطلب
    if not can_user_delete_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لحذف هذا الطلب.")
        return redirect("orders:order_detail", pk=pk)
    if not can_user_edit_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لتعديل هذا الطلب.")
        return redirect("orders:order_detail", pk=pk)

    # التحقق من صلاحية المستخدم لعرض هذا الطلب
    if not can_user_view_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لعرض هذا الطلب.")
        return redirect("orders:order_list")
    
    if request.method == 'POST':
        # الحصول على معرف العميل من POST
        customer_id = request.POST.get('customer')
        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                customer = None
        
        form = OrderForm(request.POST, request.FILES, instance=order, user=request.user, customer=customer)
        
        if form.is_valid():
            try:
                # Save order
                order = form.save(commit=False)
                
                # معالجة حقل المعاينة المرتبطة
                related_inspection_value = form.cleaned_data.get('related_inspection')
                if related_inspection_value == 'customer_side':
                    order.related_inspection_type = 'customer_side'
                    order.related_inspection = None
                elif related_inspection_value and related_inspection_value != '':
                    try:
                        from inspections.models import Inspection
                        inspection = Inspection.objects.get(id=related_inspection_value)
                        order.related_inspection = inspection
                        order.related_inspection_type = 'inspection'
                    except Inspection.DoesNotExist:
                        order.related_inspection = None
                        order.related_inspection_type = None
                else:
                    order.related_inspection = None
                    order.related_inspection_type = None

                # حفظ الطلب
                order.save()

                # التأكد من أن الطلب تم حفظه بنجاح وله مفتاح أساسي
                if not order.pk:
                    raise Exception("فشل في حفظ الطلب: لم يتم إنشاء مفتاح أساسي")

                # Save order items
                formset = OrderItemFormSet(request.POST, prefix='items', instance=order)
                if formset.is_valid():
                    formset.save()
                else:
                    print("UPDATE - Formset errors:", formset.errors)
                    messages.warning(request, 'تم تحديث الطلب ولكن هناك أخطاء في عناصر الطلب.')

                messages.success(request, 'تم تحديث الطلب بنجاح!')
                return redirect('orders:order_detail', pk=order.pk)

            except Exception as e:
                print(f"Error updating order: {e}")
                messages.error(request, f'حدث خطأ أثناء تحديث الطلب: {str(e)}')
        else:
            print("--- UPDATE FORM IS INVALID ---")
            print("Validation Errors:", form.errors)
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج.')
    else:
        # GET request - استخدام عميل الطلب الحالي
        customer = order.customer
        form = OrderForm(instance=order, user=request.user, customer=customer)

    # Get currency symbol from system settings
    currency_symbol = 'ج.م'

    context = {
        'form': form,
        'order': order,
        'currency_symbol': currency_symbol,
        'title': f'تعديل الطلب: {order.order_number}'
    }

    return render(request, 'orders/order_form.html', context)

@login_required
@permission_required('orders.delete_order', raise_exception=True)
def order_delete(request, pk):
    """
    View for deleting an order
    """
    order = get_object_or_404(Order, pk=pk)

    # التحقق من صلاحية المستخدم لتعديل هذا الطلب

    # التحقق من صلاحية المستخدم لحذف هذا الطلب
    if not can_user_delete_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لحذف هذا الطلب.")
        return redirect("orders:order_detail", pk=pk)
    if not can_user_edit_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لتعديل هذا الطلب.")
        return redirect("orders:order_detail", pk=pk)

    # التحقق من صلاحية المستخدم لعرض هذا الطلب
    if not can_user_view_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لعرض هذا الطلب.")
        return redirect("orders:order_list")

    if request.method == 'POST':
        try:
            order.delete()
            messages.success(request, 'تم حذف الطلب بنجاح.')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف الطلب: {str(e)}')
        return redirect('orders:order_list')

    context = {
        'order': order,
        'title': f'حذف الطلب: {order.order_number}',
    }

    return render(request, 'orders/order_confirm_delete.html', context)

@login_required
@permission_required('orders.add_payment', raise_exception=True)
def payment_create(request, order_pk):
    """
    View for creating a new payment for an order
    """
    order = get_object_or_404(Order, pk=order_pk)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                # التأكد من أن الطلب له مفتاح أساسي
                if not order.pk:
                    messages.error(request, 'لا يمكن إنشاء دفعة: الطلب ليس له مفتاح أساسي')
                    return redirect('orders:order_detail', pk=order_pk)

                payment = form.save(commit=False)
                payment.order = order
                payment.created_by = request.user
                payment.save()

                messages.success(request, 'تم تسجيل الدفعة بنجاح.')
                return redirect('orders:order_detail', pk=order.pk)
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء حفظ الدفعة: {str(e)}')
                return render(request, 'orders/payment_form.html', {'form': form, 'order': order})
    else:
        form = PaymentForm()

    # Get currency symbol from system settings
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'

    context = {
        'form': form,
        'order': order,
        'title': f'تسجيل دفعة جديدة للطلب: {order.order_number}',
        'currency_symbol': currency_symbol,  # Add currency symbol to context
    }

    return render(request, 'orders/payment_form.html', context)

@login_required
@permission_required('orders.delete_payment', raise_exception=True)
def payment_delete(request, pk):
    """
    View for deleting a payment
    """
    payment = get_object_or_404(Payment, pk=pk)
    order = payment.order

    if request.method == 'POST':
        try:
            payment.delete()
            messages.success(request, 'تم حذف الدفعة بنجاح.')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف الدفعة: {str(e)}')
        return redirect('orders:order_detail', pk=order.pk)

    context = {
        'payment': payment,
        'order': order,
        'title': f'حذف دفعة من الطلب: {order.order_number}'
    }

    return render(request, 'orders/payment_confirm_delete.html', context)

@login_required
def salesperson_list(request):
    """
    View for listing salespersons and their orders
    """
    salespersons = Salesperson.objects.all()

    # Add order statistics for each salesperson
    for sp in salespersons:
        sp.total_orders = Order.objects.filter(salesperson=sp).count()
        sp.completed_orders = Order.objects.filter(salesperson=sp, status='completed').count()
        sp.pending_orders = Order.objects.filter(salesperson=sp, status='pending').count()
        sp.total_sales = Order.objects.filter(salesperson=sp, status='completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    context = {
        'salespersons': salespersons,
        'title': 'قائمة مندوبي المبيعات'
    }

    return render(request, 'orders/salesperson_list.html', context)

@login_required
@permission_required('orders.change_order', raise_exception=True)
def update_order_status(request, order_id):
    """
    View for updating order status with detailed logging
    """
    order = get_object_or_404(Order, pk=order_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status and new_status in dict(Order.TRACKING_STATUS_CHOICES).keys():
            try:
                # حفظ الحالة القديمة
                old_status = order.tracking_status
                
                # تحديث الحالة
                order.tracking_status = new_status
                order.save()
                
                # تسجيل تغيير الحالة في السجل
                from .models import OrderStatusLog
                OrderStatusLog.objects.create(
                    order=order,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=request.user,
                    notes=notes
                )
                
                messages.success(request, f'تم تحديث حالة الطلب بنجاح من "{dict(Order.TRACKING_STATUS_CHOICES).get(old_status, old_status)}" إلى "{dict(Order.TRACKING_STATUS_CHOICES).get(new_status, new_status)}"')
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء تحديث حالة الطلب: {str(e)}')
        else:
            messages.error(request, 'حالة الطلب غير صالحة.')

    return redirect('orders:order_detail', pk=order_id)


@login_required
def get_order_details_api(request, order_id):
    """
    API endpoint لجلب تفاصيل الطلب للتركيبات
    """
    try:
        order = get_object_or_404(Order, pk=order_id)

        # جلب بيانات العميل
        customer_data = {
            'name': order.customer.name,
            'phone': order.customer.phone,
            'address': getattr(order.customer, 'address', ''),
        }

        # جلب بيانات البائع والفرع
        salesperson_name = ''
        branch_name = ''

        if order.salesperson:
            salesperson_name = order.salesperson.name
            if order.salesperson.branch:
                branch_name = order.salesperson.branch.name
        elif order.branch:
            branch_name = order.branch.name

        # محاولة استخراج عدد الشبابيك من الملاحظات أو العناصر
        windows_count = 0

        # البحث في ملاحظات الطلب عن عدد الشبابيك
        if order.notes:
            import re
            windows_match = re.search(r'(\d+)\s*شباك', order.notes)
            if windows_match:
                windows_count = int(windows_match.group(1))

        # إذا لم نجد في الملاحظات، نحسب من عناصر الطلب
        if windows_count == 0:
            order_items = order.items.all()
            for item in order_items:
                if 'شباك' in item.product.name.lower() or 'نافذة' in item.product.name.lower():
                    windows_count += item.quantity

        response_data = {
            'success': True,
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': customer_data['name'],
                'customer_phone': customer_data['phone'],
                'customer_address': customer_data['address'],
                'salesperson_name': salesperson_name,
                'branch_name': branch_name,
                'windows_count': windows_count,
                'total_amount': float(order.total_amount),
                'delivery_type': order.delivery_type,
                'delivery_address': order.delivery_address,
                'notes': order.notes,
                'created_at': order.created_at.strftime('%Y-%m-%d'),
            }
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def get_customer_inspections(request):
    """
    API endpoint لجلب معاينات العميل المحدد
    """
    customer_id = request.GET.get('customer_id')
    
    if not customer_id:
        return JsonResponse({
            'success': False,
            'message': 'معرف العميل مطلوب'
        })
    
    try:
        customer = Customer.objects.get(id=customer_id)
        inspections = Inspection.objects.filter(customer=customer).order_by('-created_at')
        
        # تحضير قائمة المعاينات
        inspection_choices = [
            {'value': 'customer_side', 'text': 'طرف العميل'}
        ]
        
        for inspection in inspections:
            # تأكد من أن القيمة نصية
            inspection_choices.append({
                'value': str(inspection.id),  # تأكد من أن القيمة نصية
                'text': f"{inspection.customer.name if inspection.customer else 'عميل غير محدد'} - {inspection.contract_number or f'معاينة {inspection.id}'} - {inspection.created_at.strftime('%Y-%m-%d')}"
            })
        
        return JsonResponse({
            'success': True,
            'choices': inspection_choices
        })
        
    except Customer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'العميل غير موجود'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'خطأ في جلب المعاينات: {str(e)}'
        })


#
