import json
from django.http import JsonResponse, HttpResponse
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Order, OrderItem, Payment
from .forms import OrderForm, OrderItemFormSet, PaymentForm, OrderEditForm, OrderItemEditFormSet
from .permissions import get_user_orders_queryset, can_user_view_order, can_user_edit_order, can_user_delete_order
from accounts.models import Branch, Salesperson, Department, SystemSettings
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
            Q(contract_number_2__icontains=search_query) |
            Q(contract_number_3__icontains=search_query) |
            Q(invoice_number__icontains=search_query) |
            Q(invoice_number_2__icontains=search_query) |
            Q(invoice_number_3__icontains=search_query) |
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
        customer_param = request.POST.get('customer')
        customer = None
        if customer_param:
            try:
                # محاولة البحث بالـ ID أولاً (في حالة كان رقمي)
                if customer_param.isdigit():
                    customer = Customer.objects.get(id=customer_param)
                else:
                    # البحث بكود العميل إذا لم يكن رقمي
                    customer = Customer.objects.get(code=customer_param)
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
                payment_method = request.POST.get('payment_method', 'cash')
                # استخدام رقم الفاتورة كرقم مرجع للدفعة
                payment_reference = order.invoice_number or ''
                try:
                    paid_amount = float(paid_amount or 0)
                except Exception:
                    paid_amount = 0
                if paid_amount > 0:
                    from .models import Payment
                    Payment.objects.create(
                        order=order,
                        amount=paid_amount,
                        payment_method=payment_method,
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
                
                # إعادة التوجيه مع معلومة عن الدفع
                if paid_amount > 0:
                    # إعادة توجيه لصفحة النجاح مع خيار الطباعة
                    return redirect(f'/orders/{order.pk}/success/?show_print=1&paid_amount={paid_amount}')
                else:
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
        customer_param = request.GET.get('customer')
        customer = None
        if customer_param:
            try:
                # محاولة البحث بالـ ID أولاً (في حالة كان رقمي)
                if customer_param.isdigit():
                    customer = Customer.objects.get(id=customer_param)
                else:
                    # البحث بكود العميل إذا لم يكن رقمي
                    customer = Customer.objects.get(code=customer_param)
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
        customer_param = request.POST.get('customer')
        customer = None
        if customer_param:
            try:
                # محاولة البحث بالـ ID أولاً (في حالة كان رقمي)
                if customer_param.isdigit():
                    customer = Customer.objects.get(id=customer_param)
                else:
                    # البحث بكود العميل إذا لم يكن رقمي
                    customer = Customer.objects.get(code=customer_param)
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
                # تعيين رقم الفاتورة كرقم مرجع إذا لم يتم تحديد رقم مرجع
                if not payment.reference_number:
                    payment.reference_number = order.invoice_number or ''
                payment.save()

                messages.success(request, 'تم تسجيل الدفعة بنجاح.')
                return redirect('orders:order_detail', pk=order.pk)
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء حفظ الدفعة: {str(e)}')
                return render(request, 'orders/payment_form.html', {'form': form, 'order': order})
    else:
        # تعيين رقم الفاتورة كقيمة افتراضية
        initial_data = {'reference_number': order.invoice_number or ''}
        form = PaymentForm(initial=initial_data)

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
    customer_param = request.GET.get('customer_id')
    
    if not customer_param:
        return JsonResponse({
            'success': False,
            'message': 'معرف العميل مطلوب'
        })
    
    try:
        # محاولة البحث بالـ ID أولاً (في حالة كان رقمي)
        if customer_param.isdigit():
            customer = Customer.objects.get(id=customer_param)
        else:
            # البحث بكود العميل إذا لم يكن رقمي
            customer = Customer.objects.get(code=customer_param)
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


# Views باستخدام رقم الطلب (order_number) بدلاً من ID

@login_required
def order_detail_by_number(request, order_number):
    """عرض تفاصيل الطلب باستخدام رقم الطلب"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # التحقق من صلاحية المستخدم لحذف أو تعديل أو عرض هذا الطلب
    if not can_user_view_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لعرض هذا الطلب.")
        return redirect("orders:order_list")
    if not can_user_edit_order(request.user, order):
        messages.warning(request, "ليس لديك صلاحية لتعديل هذا الطلب.")
    if not can_user_delete_order(request.user, order):
        messages.warning(request, "ليس لديك صلاحية لحذف هذا الطلب.")
    
    payments = order.payments.all().order_by('-payment_date')
    order_items = order.items.all()
    
    # Get inspections related to this order
    inspections = []
    selected_types = order.get_selected_types_list()
    if 'inspection' in selected_types:
        from inspections.models import Inspection
        inspections = Inspection.objects.filter(order=order)

    context = {
        'order': order,
        'payments': payments,
        'order_items': order_items,
        'inspections': inspections,
        'can_edit': can_user_edit_order(request.user, order),
        'can_delete': can_user_delete_order(request.user, order),
    }
    
    return render(request, 'orders/order_detail.html', context)


@login_required  
def order_detail_by_code(request, order_code):
    """عرض تفاصيل الطلب باستخدام كود الطلب (نفس order_number)"""
    order = get_object_or_404(Order, order_number=order_code)
    
    # التحقق من صلاحية المستخدم لحذف أو تعديل أو عرض هذا الطلب
    if not can_user_view_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لعرض هذا الطلب.")
        return redirect("orders:order_list")
    if not can_user_edit_order(request.user, order):
        messages.warning(request, "ليس لديك صلاحية لتعديل هذا الطلب.")
    if not can_user_delete_order(request.user, order):
        messages.warning(request, "ليس لديك صلاحية لحذف هذا الطلب.")
    
    payments = order.payments.select_related().all().order_by('-payment_date')
    order_items = order.items.select_related('product').all()
    
    # Get inspections related to this order with optimization
    inspections = []
    selected_types = order.get_selected_types_list()
    if 'inspection' in selected_types:
        from inspections.models import Inspection
        inspections = Inspection.objects.filter(order=order).select_related('inspector')

    context = {
        'order': order,
        'payments': payments,
        'order_items': order_items,
        'inspections': inspections,
        'can_edit': can_user_edit_order(request.user, order),
        'can_delete': can_user_delete_order(request.user, order),
    }
    
    return render(request, 'orders/order_detail.html', context)


@login_required
def order_success_by_number(request, order_number):
    """صفحة نجاح إنشاء الطلب باستخدام رقم الطلب"""
    order = get_object_or_404(Order, order_number=order_number)
    
    if not can_user_view_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لعرض هذا الطلب.")
        return redirect("orders:order_list")
    
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def order_update_by_number(request, order_number):
    """تحديث الطلب المتقدم مع عناصر الطلب"""
    order = get_object_or_404(Order, order_number=order_number)

    if not can_user_edit_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لتعديل هذا الطلب.")
        return redirect("orders:order_detail_by_number", order_number=order_number)

    if request.method == 'POST':
        form = OrderEditForm(request.POST, instance=order)
        formset = OrderItemEditFormSet(request.POST, instance=order)

        # تشخيص الأخطاء
        if not form.is_valid():
            for field, errors in form.errors.items():
                messages.error(request, f"خطأ في {field}: {', '.join(errors)}")

        if not formset.is_valid():
            for i, form_errors in enumerate(formset.errors):
                if form_errors:
                    for field, errors in form_errors.items():
                        messages.error(request, f"خطأ في العنصر {i+1} - {field}: {', '.join(errors)}")

        if form.is_valid() and formset.is_valid():
            # حفظ القيم القديمة للعناصر قبل التعديل
            old_items_data = {}
            for form_item in formset:
                if form_item.instance.pk:
                    old_items_data[form_item.instance.pk] = {
                        'product': form_item.instance.product,
                        'quantity': form_item.instance.quantity,
                        'unit_price': form_item.instance.unit_price,
                        'notes': form_item.instance.notes,
                    }

            # تتبع التغييرات قبل الحفظ
            changes = []

            # تتبع تغييرات الطلب الأساسي بتفصيل أكثر
            for field in form.changed_data:
                if field in form.fields:
                    old_value = getattr(order, field, '')
                    new_value = form.cleaned_data[field]
                    field_label = form.fields[field].label or field

                    # تحسين عرض القيم للحقول المختلفة
                    if field == 'customer':
                        old_name = old_value.name if old_value else 'غير محدد'
                        new_name = new_value.name if new_value else 'غير محدد'
                        changes.append(f"تم تغيير العميل من '{old_name}' إلى '{new_name}'")
                    elif field == 'branch':
                        old_name = old_value.name if old_value else 'غير محدد'
                        new_name = new_value.name if new_value else 'غير محدد'
                        changes.append(f"تم تغيير الفرع من '{old_name}' إلى '{new_name}'")
                    elif field == 'salesperson':
                        old_name = old_value.name if old_value else 'غير محدد'
                        new_name = new_value.name if new_value else 'غير محدد'
                        changes.append(f"تم تغيير البائع من '{old_name}' إلى '{new_name}'")
                    elif field == 'paid_amount':
                        changes.append(f"تم تغيير المبلغ المدفوع من {old_value} ج.م إلى {new_value} ج.م")
                    elif field == 'notes':
                        old_notes = old_value or 'بدون ملاحظات'
                        new_notes = new_value or 'بدون ملاحظات'
                        changes.append(f"تم تغيير ملاحظات الطلب من '{old_notes}' إلى '{new_notes}'")
                    else:
                        changes.append(f"تم تغيير {field_label} من '{old_value}' إلى '{new_value}'")

            # تتبع تغييرات العناصر بتفصيل أكثر
            deleted_items = []
            modified_items = []
            added_items = []

            for form_item in formset:
                if form_item.cleaned_data.get('DELETE'):
                    if form_item.instance.pk:
                        product_name = form_item.instance.product.name if form_item.instance.product else 'غير محدد'
                        quantity = form_item.instance.quantity
                        price = form_item.instance.unit_price
                        deleted_items.append(f"حذف الصنف: {product_name} (الكمية: {quantity}, السعر: {price} ج.م)")
                elif form_item.instance.pk:
                    # عنصر موجود تم تعديله
                    if form_item.changed_data and form_item.instance.pk in old_items_data:
                        item_changes = []
                        old_data = old_items_data[form_item.instance.pk]

                        # تحديد اسم المنتج للاستخدام في الرسائل
                        # إذا تم تغيير المنتج، استخدم الاسم القديم والجديد
                        # وإلا استخدم الاسم الحالي
                        if 'product' in form_item.changed_data:
                            old_product_name = old_data['product'].name if old_data['product'] else 'غير محدد'
                            new_product_name = form_item.cleaned_data['product'].name if form_item.cleaned_data.get('product') else 'غير محدد'
                        else:
                            # لم يتم تغيير المنتج، استخدم الاسم الحالي
                            current_product_name = old_data['product'].name if old_data['product'] else 'غير محدد'

                        for field in form_item.changed_data:
                            if field == 'product':
                                old_product = old_data['product']
                                new_product = form_item.cleaned_data[field]
                                old_name = old_product.name if old_product else 'غير محدد'
                                new_name = new_product.name if new_product else 'غير محدد'
                                item_changes.append(f"تبديل نوع الصنف من '{old_name}' إلى '{new_name}'")
                            elif field == 'quantity':
                                old_value = old_data['quantity']
                                new_value = form_item.cleaned_data[field]
                                # استخدام الاسم المناسب حسب ما إذا تم تغيير المنتج أم لا
                                if 'product' in form_item.changed_data:
                                    item_changes.append(f"تعديل كمية الصنف من {old_value} إلى {new_value} (المنتج: {old_product_name} → {new_product_name})")
                                else:
                                    item_changes.append(f"تعديل كمية الصنف '{current_product_name}' من {old_value} إلى {new_value}")
                            elif field == 'unit_price':
                                old_value = old_data['unit_price']
                                new_value = form_item.cleaned_data[field]
                                # استخدام الاسم المناسب حسب ما إذا تم تغيير المنتج أم لا
                                if 'product' in form_item.changed_data:
                                    item_changes.append(f"تعديل سعر الصنف من {old_value} ج.م إلى {new_value} ج.م (المنتج: {old_product_name} → {new_product_name})")
                                else:
                                    item_changes.append(f"تعديل سعر الصنف '{current_product_name}' من {old_value} ج.م إلى {new_value} ج.م")
                            elif field == 'notes':
                                old_value = old_data['notes'] or 'بدون ملاحظات'
                                new_value = form_item.cleaned_data[field] or 'بدون ملاحظات'
                                # استخدام الاسم المناسب حسب ما إذا تم تغيير المنتج أم لا
                                if 'product' in form_item.changed_data:
                                    item_changes.append(f"تعديل ملاحظات الصنف من '{old_value}' إلى '{new_value}' (المنتج: {old_product_name} → {new_product_name})")
                                else:
                                    item_changes.append(f"تعديل ملاحظات الصنف '{current_product_name}' من '{old_value}' إلى '{new_value}'")

                        if item_changes:
                            modified_items.extend(item_changes)
                else:
                    # عنصر جديد
                    if form_item.cleaned_data and not form_item.cleaned_data.get('DELETE'):
                        product_name = form_item.cleaned_data.get('product').name if form_item.cleaned_data.get('product') else 'غير محدد'
                        quantity = form_item.cleaned_data.get('quantity', 0)
                        price = form_item.cleaned_data.get('unit_price', 0)
                        notes = form_item.cleaned_data.get('notes', '') or 'بدون ملاحظات'
                        added_items.append(f"إضافة صنف جديد: {product_name} (الكمية: {quantity}, السعر: {price} ج.م, ملاحظات: {notes})")

            # حفظ الطلب
            updated_order = form.save()

            # حفظ عناصر الطلب
            formset.instance = updated_order
            formset.save()

            # إعادة حساب المبلغ الإجمالي
            updated_order.calculate_total()

            # تسجيل التعديلات
            from .models import OrderNote

            # تسجيل التعديلات العامة
            if changes or deleted_items or modified_items or added_items:
                content_parts = []
                content_parts.append(f'تم تعديل الطلب بواسطة {request.user.get_full_name() or request.user.username}')
                content_parts.append('=' * 50)

                if changes:
                    content_parts.append('📝 تعديلات البيانات الأساسية:')
                    for change in changes:
                        content_parts.append(f'• {change}')
                    content_parts.append('')

                if added_items:
                    content_parts.append('➕ إضافة أصناف جديدة:')
                    for item in added_items:
                        content_parts.append(f'• {item}')
                    content_parts.append('')

                if modified_items:
                    content_parts.append('✏️ تعديل الأصناف الموجودة:')
                    for item in modified_items:
                        content_parts.append(f'• {item}')
                    content_parts.append('')

                if deleted_items:
                    content_parts.append('🗑️ حذف الأصناف:')
                    for item in deleted_items:
                        content_parts.append(f'• {item}')
                    content_parts.append('')

                # إضافة معلومات إضافية
                content_parts.append(f'💰 إجمالي المبلغ بعد التعديل: {updated_order.total_amount} ج.م')
                content_parts.append(f'💳 المبلغ المدفوع: {updated_order.paid_amount} ج.م')
                content_parts.append(f'📊 المديونية: {updated_order.remaining_amount} ج.م')

                content = '\n'.join(content_parts)

                OrderNote.objects.create(
                    order=updated_order,
                    note_type='modification',
                    title='تعديل الطلب',
                    content=content,
                    created_by=request.user,
                    is_important=True
                )

            messages.success(request, f'تم تحديث الطلب {order.order_number} وعناصره بنجاح.')
            return redirect('orders:order_detail_by_number', order_number=order_number)
        else:
            # إذا كان هناك أخطاء في النموذج
            messages.error(request, 'حدث خطأ في حفظ التعديلات. يرجى مراجعة البيانات المدخلة.')
    else:
        form = OrderEditForm(instance=order)
        formset = OrderItemEditFormSet(instance=order)

    return render(request, 'orders/order_edit_form.html', {
        'form': form,
        'formset': formset,
        'order': order,
        'is_update': True
    })


@login_required
def order_delete_by_number(request, order_number):
    """حذف الطلب باستخدام رقم الطلب"""
    order = get_object_or_404(Order, order_number=order_number)
    
    if not can_user_delete_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لحذف هذا الطلب.")
        return redirect("orders:order_detail_by_number", order_number=order_number)
    
    if request.method == 'POST':
        order_number_for_message = order.order_number
        order.delete()
        messages.success(request, f'تم حذف الطلب {order_number_for_message} بنجاح.')
        return redirect('orders:order_list')
    
    return render(request, 'orders/order_confirm_delete.html', {'order': order})


# Views للإعادة التوجيه من ID إلى order_number
@login_required
def order_detail_redirect(request, pk):
    """إعادة توجيه من ID إلى order_number"""
    order = get_object_or_404(Order, pk=pk)
    return redirect('orders:order_detail_by_number', order_number=order.order_number)

@login_required
def order_success_redirect(request, pk):
    """إعادة توجيه من ID إلى order_number"""
    order = get_object_or_404(Order, pk=pk)
    return redirect('orders:order_success_by_number', order_number=order.order_number)

@login_required
def order_update_redirect(request, pk):
    """إعادة توجيه من ID إلى order_number"""
    order = get_object_or_404(Order, pk=pk)
    return redirect('orders:order_update_by_number', order_number=order.order_number)

@login_required
def order_delete_redirect(request, pk):
    """إعادة توجيه من ID إلى order_number"""
    order = get_object_or_404(Order, pk=pk)
    return redirect('orders:order_delete_by_number', order_number=order.order_number)


# ====================
# Invoice Printing Views
# ====================

@login_required
def invoice_print(request, order_number):
    """طباعة فاتورة الطلب مباشرةً وفق القالب المحفوظ أو قالب افتراضي، مع ضمان A4 والطباعة مباشرة عند الطلب."""
    order = get_object_or_404(Order, order_number=order_number)

    # نماذج القوالب والسجلات
    from .invoice_models import InvoiceTemplate, InvoicePrintLog
    from accounts.models import SystemSettings, CompanyInfo

    # استرجاع القالب الافتراضي أو إنشاؤه من بيانات الشركة
    template = InvoiceTemplate.get_default_template()
    if not template:
        company_info = CompanyInfo.objects.first()
        template = InvoiceTemplate.objects.create(
            name='القالب الافتراضي',
            is_default=True,
            company_name=(company_info.name if company_info else 'اسم الشركة'),
            company_address=(company_info.address if company_info else 'عنوان الشركة'),
            company_phone=(company_info.phone if company_info else ''),
            company_email=(company_info.email if company_info else ''),
            company_website=(company_info.website if company_info else ''),
            primary_color=(company_info.primary_color if company_info else '#0d6efd'),
            secondary_color=(company_info.secondary_color if company_info else '#198754'),
            accent_color=(company_info.accent_color if company_info else '#ffc107'),
            created_by=request.user,
        )

    # تسجيل الاستخدام
    template.increment_usage()
    print_type = 'auto' if request.GET.get('auto_print') in ['1', 'true', 'True'] else 'manual'
    InvoicePrintLog.objects.create(order=order, template=template, printed_by=request.user, print_type=print_type)

    # إعدادات النظام والعملات
    system_settings = SystemSettings.get_settings()
    company_info = CompanyInfo.objects.first()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ريال'

    # إنشاء جدول العناصر مرة واحدة للاستخدام في كلا الفرعين
    items_html_rows = []
    for item in order.items.all():
        # تنسيق الأسعار لإزالة الأصفار الزائدة
        try:
            unit_price = float(item.unit_price or 0)
            total_price = float(item.total_price or 0)
            quantity = int(item.quantity or 0)
            
            # تنسيق الأسعار بحيث تظهر بشكل صحيح
            unit_price_formatted = f"{unit_price:.2f}".rstrip('0').rstrip('.')
            total_price_formatted = f"{total_price:.2f}".rstrip('0').rstrip('.')
            
        except (ValueError, TypeError):
            unit_price_formatted = "0"
            total_price_formatted = "0"
            quantity = 0
            
        items_html_rows.append(
            f"""
            <tr>
                <td style=\"padding:10px;border:1px solid #ddd;text-align:right;word-break:break-word;\">{item.product.name if getattr(item, 'product', None) else 'منتج'}</td>
                <td style=\"padding:10px;border:1px solid #ddd;text-align:center;\">{quantity}</td>
                <td style=\"padding:10px;border:1px solid #ddd;text-align:center;\">{unit_price_formatted} {currency_symbol}</td>
                <td style=\"padding:10px;border:1px solid #ddd;text-align:center;\">{total_price_formatted} {currency_symbol}</td>
            </tr>
            """
        )
    items_html = "".join(items_html_rows)

    # محتوى القالب
    if template.html_content and len(template.html_content) > 50:
        html_content = template.html_content

        # استبدال بيانات الشركة والطلب الأساسية
        basic_replacements = {
            '${companyInfo.name}': template.company_name or (company_info.name if company_info else 'اسم الشركة'),
            '${companyInfo.address}': template.company_address or (company_info.address if company_info else 'المملكة العربية السعودية'),
            '${companyInfo.phone}': template.company_phone or (company_info.phone if company_info else ''),
            '${companyInfo.email}': template.company_email or (company_info.email if company_info else ''),
            '${companyInfo.website}': template.company_website or (company_info.website if company_info else ''),
            '${systemSettings.currency_symbol}': currency_symbol,
            '${order.order_number}': order.order_number,
            '${order.code}': order.order_number,
            '${order.contract_number}': getattr(order, 'contract_number', '') or '',
            '${order.invoice_number}': getattr(order, 'invoice_number', '') or str(order.order_number),
        }
        for placeholder, value in basic_replacements.items():
            html_content = html_content.replace(placeholder, str(value))
 
        # العميل
        customer_name = getattr(order.customer, 'name', '') or ''
        customer_phone = getattr(order.customer, 'phone', '') or ''
        html_content = html_content.replace('${customer.name}', customer_name)
        html_content = html_content.replace('${customer.phone}', customer_phone)

        # البائع والفرع
        salesperson_name = ''
        salesperson_phone = ''
        try:
            if getattr(order, 'salesperson', None):
                salesperson_name = order.salesperson.name or ''
                salesperson_phone = order.salesperson.phone or ''
            elif getattr(order, 'salesperson_name_raw', None):
                salesperson_name = order.salesperson_name_raw or ''
        except Exception:
            pass
        branch_phone = getattr(getattr(order, 'branch', None), 'phone', '') or ''
        branch_name = getattr(getattr(order, 'branch', None), 'name', '') or ''
        html_content = html_content.replace('${salesperson.name}', salesperson_name)
        html_content = html_content.replace('${salesperson.phone}', salesperson_phone)
        html_content = html_content.replace('${branch.phone}', branch_phone)
        html_content = html_content.replace('${branch.name}', branch_name)

        # موعد التسليم المتوقع
        expected_delivery = ''
        if getattr(order, 'expected_delivery_date', None):
            expected_delivery = order.expected_delivery_date.strftime('%Y-%m-%d')
        html_content = html_content.replace('${order.expected_delivery_date}', expected_delivery)

        # المبالغ المالية - التأكد من الحصول على القيم الصحيحة
        try:
            # أولوية للـ final_price ثم total_amount
            total_amount = float(order.final_price or order.total_amount or 0)
            paid_amount = float(order.paid_amount or 0)
            remaining_amount = max(0, total_amount - paid_amount)  # تجنب القيم السالبة
            
            # تنسيق الأسعار لإزالة الأصفار الزائدة
            total_formatted = f"{total_amount:.2f}".rstrip('0').rstrip('.')
            paid_formatted = f"{paid_amount:.2f}".rstrip('0').rstrip('.')
            remaining_formatted = f"{remaining_amount:.2f}".rstrip('0').rstrip('.')
            
            html_content = html_content.replace('${order.total_amount}', total_formatted)
            html_content = html_content.replace('${order.paid_amount}', paid_formatted)
            html_content = html_content.replace('${order.remaining_amount}', remaining_formatted)
        except (ValueError, TypeError):
            # في حالة وجود خطأ، استخدم قيم افتراضية
            html_content = html_content.replace('${order.total_amount}', '0')
            html_content = html_content.replace('${order.paid_amount}', '0')
            html_content = html_content.replace('${order.remaining_amount}', '0')
        
        # رمز العملة من إعدادات النظام
        html_content = html_content.replace('${systemSettings.currency_symbol}', currency_symbol)

        # اسم العميل والهاتف والعنوان
        address_value = (order.delivery_address or getattr(order.customer, 'address', None) or 'غير محدد')
        html_content = html_content.replace('أحمد محمد', order.customer.name)
        html_content = html_content.replace('0501234567', order.customer.phone or '')
        html_content = html_content.replace('سيتم تحديد العنوان لاحقاً', address_value)
        html_content = html_content.replace('الرياض، المملكة العربية السعودية', address_value)
        html_content = html_content.replace('${customer.address}', address_value)
        html_content = html_content.replace('${order.address}', address_value)

        # التاريخ (ميلادي)
        order_date_str = (order.order_date or order.created_at).strftime('%Y-%m-%d')
        html_content = html_content.replace('2025-01-01', order_date_str)
        html_content = html_content.replace('${order.order_date}', order_date_str)

        # نوع الطلب
        try:
            order_type_display = order.get_selected_type_display()
        except Exception:
            order_type_display = getattr(order, 'get_order_type_display', lambda: 'طلب')( )
        for typ in ['معاينة', 'تركيب', 'تسليم', 'إكسسوار', 'منتج', 'خدمة']:
            html_content = html_content.replace(typ, order_type_display)
        html_content = html_content.replace('${order.type}', order_type_display)
        html_content = html_content.replace('${order.order_type}', order_type_display)

        # إدراج عناصر الطلب داخل tbody إن وجد، أو ضمن عنصر بديل
        tbody_pattern = r'<tbody[^>]*>.*?</tbody>'
        if re.search(tbody_pattern, html_content, re.DOTALL):
            html_content = re.sub(tbody_pattern, f'<tbody>{items_html}</tbody>', html_content, flags=re.DOTALL)
        else:
            html_content = html_content.replace('${order.items_table}', f'<tbody>{items_html}</tbody>')

        # مجاميع أساسية - استبدال الأرقام الثابتة القديمة
        try:
            paid_amount_val = float(order.paid_amount or 0)
            total_amount_val = float(order.final_price or order.total_amount or 0)
            remaining_amount_val = max(0, total_amount_val - paid_amount_val)
            
            # تنسيق الأسعار لإزالة الأصفار الزائدة
            total_val_formatted = f"{total_amount_val:.2f}".rstrip('0').rstrip('.')
            paid_val_formatted = f"{paid_amount_val:.2f}".rstrip('0').rstrip('.')
            remaining_val_formatted = f"{remaining_amount_val:.2f}".rstrip('0').rstrip('.')
            
            # استبدال الأرقام الثابتة القديمة
            html_content = html_content.replace('34280.00', total_val_formatted)
            html_content = html_content.replace('0.00', paid_val_formatted)
            
            # استبدال المتغيرات إذا لم تكن قد استُبدلت من قبل
            if '${order.paid_amount}' in html_content:
                html_content = html_content.replace('${order.paid_amount}', paid_val_formatted)
            if '${order.remaining_amount}' in html_content:
                html_content = html_content.replace('${order.remaining_amount}', remaining_val_formatted)
        except (ValueError, TypeError):
            # في حالة وجود خطأ، استخدم قيم افتراضية
            html_content = html_content.replace('34280.00', '0')
            html_content = html_content.replace('${order.paid_amount}', '0')
            html_content = html_content.replace('${order.remaining_amount}', '0')

    else:
        # قالب افتراضي بسيط - مع تنسيق الأسعار
        try:
            total_amount = float(order.final_price or order.total_amount or 0)
            paid_amount = float(order.paid_amount or 0)
            remaining_amount = max(0, total_amount - paid_amount)
            
            # تنسيق الأسعار لإزالة الأصفار الزائدة
            total_formatted = f"{total_amount:.2f}".rstrip('0').rstrip('.')
            paid_formatted = f"{paid_amount:.2f}".rstrip('0').rstrip('.')
            remaining_formatted = f"{remaining_amount:.2f}".rstrip('0').rstrip('.')
        except (ValueError, TypeError):
            total_formatted = "0"
            paid_formatted = "0"
            remaining_formatted = "0"
            
        html_content = f"""
        <div style=\"font-family: 'Cairo', Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;\">
            <div style=\"text-align: center; border-bottom: 2px solid #0d6efd; padding-bottom: 20px; margin-bottom: 30px;\">
                <h1 style=\"color: #0d6efd; margin: 0;\">فاتورة</h1>
                <p style=\"margin: 10px 0;\">رقم الطلب: {order.order_number}</p>
                <p style=\"margin: 10px 0;\">التاريخ: {(order.order_date or order.created_at).strftime('%Y-%m-%d')}</p>
            </div>

            <div style=\"margin-bottom: 30px;\">
                <h3 style=\"color: #0d6efd; border-bottom: 1px solid #dee2e6; padding-bottom: 10px;\">معلومات العميل</h3>
                <p><strong>الاسم:</strong> {order.customer.name}</p>
                <p><strong>الهاتف:</strong> {order.customer.phone or 'غير محدد'}</p>
                <p><strong>العنوان:</strong> {(order.delivery_address or getattr(order.customer, 'address', None) or 'غير محدد')}</p>
                <p><strong>نوع الطلب:</strong> {getattr(order, 'get_selected_type_display', lambda: 'طلب')( )}</p>
            </div>

            <div style=\"margin-bottom: 30px;\">
                <h3 style=\"color: #0d6efd; border-bottom: 1px solid #dee2e6; padding-bottom: 10px;\">تفاصيل الطلب</h3>
                <table style=\"width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 15px;\">
                    <thead>
                        <tr style=\"background: #0d6efd; color: white;\">
                            <th style=\"padding: 12px; text-align: right; border: 1px solid #ddd;\">الوصف</th>
                            <th style=\"padding: 12px; text-align: center; border: 1px solid #ddd;\">الكمية</th>
                            <th style=\"padding: 12px; text-align: center; border: 1px solid #ddd;\">السعر</th>
                            <th style=\"padding: 12px; text-align: center; border: 1px solid #ddd;\">المجموع</th>
                        </tr>
                    </thead>
                    <tbody>{items_html}</tbody>
                </table>
            </div>

            <div style=\"background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px;\">
                <div style=\"display: flex; justify-content: space-between; margin-bottom: 10px;\">
                    <span><strong>المجموع الكلي:</strong></span>
                    <span><strong>{total_formatted} {currency_symbol}</strong></span>
                </div>
                <div style=\"display: flex; justify-content: space-between; margin-bottom: 10px; color: #198754;\">
                    <span>المبلغ المدفوع:</span>
                    <span>{paid_formatted} {currency_symbol}</span>
                </div>
                <div style=\"display: flex; justify-content: space-between; color: #dc3545; border-top: 1px solid #dee2e6; padding-top: 10px;\">
                    <span>المبلغ المتبقي:</span>
                    <span>{remaining_formatted} {currency_symbol}</span>
                </div>
            </div>

            <div style=\"text-align: center; color: #6c757d; font-size: 12px; border-top: 1px solid #dee2e6; padding-top: 20px;\">
                <p>شكراً لتعاملكم معنا</p>
                <p>{template.company_name or (company_info.name if company_info else 'اسم الشركة')}</p>
            </div>
        </div>
        """

    # غلاف HTML للطباعة على A4 + طباعة تلقائية اختيارية
    auto_print_script = (
        """
        <script>
            window.addEventListener('load', function() {
                setTimeout(function() { window.print(); }, 500);
            });
        </script>
        """
        if request.GET.get('auto_print') in ['1', 'true', 'True'] else ''
    )

    full_html = f"""
    <!DOCTYPE html>
    <html dir=\"rtl\" lang=\"ar\">
    <head>
        <meta charset=\"UTF-8\">
        <title>فاتورة - {order.order_number}</title>
        <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
        <link href=\"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css\" rel=\"stylesheet\">
        <link href=\"https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap\" rel=\"stylesheet\">
        <style>
            body {{ font-family: 'Cairo', Arial, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
            @media print {{
                @page {{ size: A4; margin: 10mm; }}
                body {{ margin: 0; padding: 0; background: white !important; font-size: 10px !important; }}
                .print-buttons {{ display: none !important; }}
                .invoice-container {{ box-shadow: none !important; border-radius: 0 !important; max-width: none !important; }}
            }}
            .invoice-container {{ max-width: 210mm; margin: 0 auto; background: white; box-shadow: 0 0 20px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
            .invoice-container table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
            .invoice-container th, .invoice-container td {{ padding: 10px; border: 1px solid #ddd; }}
            .invoice-container td:first-child {{ text-align: right; word-break: break-word; }}
            .invoice-container td:nth-child(2), .invoice-container td:nth-child(3), .invoice-container td:nth-child(4) {{ text-align: center; }}
        </style>
        {auto_print_script}
    </head>
    <body>
        <div class=\"invoice-container\">{html_content}</div>
        <div class=\"print-buttons text-center mt-4\">
            <button onclick=\"window.print()\" class=\"btn btn-primary me-2\"><i class=\"fas fa-print\"></i> طباعة</button>
            <button onclick=\"window.close()\" class=\"btn btn-secondary\"><i class=\"fas fa-times\"></i> إغلاق</button>
        </div>
    </body>
    </html>
    """

    return HttpResponse(full_html)

@login_required  
def invoice_print_redirect(request, pk):
    """إعادة توجيه من ID إلى order_number لطباعة الفاتورة"""
    order = get_object_or_404(Order, pk=pk)
    return redirect('orders:invoice_print', order_number=order.order_number)


# AJAX endpoints for contract file upload to Google Drive

@login_required
def ajax_upload_contract_to_google_drive(request):
    """رفع ملف العقد إلى Google Drive عبر AJAX"""
    if request.method == 'POST':
        try:
            order_id = request.POST.get('order_id')

            if not order_id:
                return JsonResponse({
                    'success': False,
                    'message': 'معرف الطلب مطلوب'
                })

            # الحصول على الطلب
            order = get_object_or_404(Order, id=order_id)

            # التحقق من وجود ملف العقد
            if not order.contract_file:
                return JsonResponse({
                    'success': False,
                    'message': 'لا يوجد ملف عقد للرفع'
                })

            # التحقق من أن الملف لم يتم رفعه مسبقاً
            if order.is_contract_uploaded_to_drive:
                return JsonResponse({
                    'success': False,
                    'message': 'تم رفع هذا الملف مسبقاً إلى Google Drive'
                })

            # رفع الملف إلى Google Drive
            from orders.services.google_drive_service import get_contract_google_drive_service

            drive_service = get_contract_google_drive_service()
            if not drive_service:
                return JsonResponse({
                    'success': False,
                    'message': 'خدمة Google Drive غير متوفرة. يرجى التحقق من الإعدادات.'
                })

            # رفع الملف
            result = drive_service.upload_contract_file(
                order.contract_file.path,
                order
            )

            # تحديث بيانات الطلب
            order.contract_google_drive_file_id = result['file_id']
            order.contract_google_drive_file_url = result['view_url']
            order.contract_google_drive_file_name = result['filename']
            order.is_contract_uploaded_to_drive = True
            order.save(update_fields=[
                'contract_google_drive_file_id', 'contract_google_drive_file_url',
                'contract_google_drive_file_name', 'is_contract_uploaded_to_drive'
            ])

            return JsonResponse({
                'success': True,
                'message': 'تم رفع الملف بنجاح إلى Google Drive',
                'data': {
                    'filename': result['filename'],
                    'view_url': result['view_url'],
                    'customer_name': result['customer_name'],
                    'branch_name': result['branch_name']
                }
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'خطأ في رفع الملف: {str(e)}'
            })

    return JsonResponse({
        'success': False,
        'message': 'طريقة الطلب غير صحيحة'
    })


@login_required
def check_contract_upload_status(request, pk):
    """التحقق من حالة رفع ملف العقد إلى Google Drive"""
    try:
        order = get_object_or_404(Order, pk=pk)

        return JsonResponse({
            'is_uploaded': order.is_contract_uploaded_to_drive,
            'google_drive_url': order.contract_google_drive_file_url,
            'file_name': order.contract_google_drive_file_name,
            'file_id': order.contract_google_drive_file_id
        })
    except Exception as e:
        return JsonResponse({
            'is_uploaded': False,
            'error': str(e)
        })
