import json
import logging
from django.http import JsonResponse, HttpResponse
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Order, OrderItem, Payment
from .forms import OrderForm, OrderItemFormSet, PaymentForm, OrderEditForm, OrderItemEditFormSet
from .permissions import (
    get_user_orders_queryset,
    can_user_view_order,
    can_user_edit_order,
    can_user_delete_order,
    order_create_permission_required,
    order_edit_permission_required,
    order_delete_permission_required
)
from accounts.models import Branch, Salesperson, Department
from customers.models import Customer
from inventory.models import Product
from inspections.models import Inspection
from datetime import datetime, timedelta
from django.db import models
import traceback

logger = logging.getLogger(__name__)
from django.utils.translation import gettext_lazy as _
class OrdersDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'orders/dashboard.html'
    def get_context_data(self, **kwargs):
        """Provide dashboard statistics using manufacturing `order_status` counts.

        Uses get_user_orders_queryset to respect user permissions.
        """
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # تطبيق نظام الصلاحيات - الحصول على الطلبات حسب دور المستخدم
        orders = get_user_orders_queryset(self.request.user)

        # Basic statistics
        context['total_orders'] = orders.count()
        # use order_status (manufacturing state) for dashboard counts
        # 'pending' here refers to the ORDER_STATUS_CHOICES 'pending'
        context['pending_orders'] = orders.filter(order_status='pending').count()
        context['completed_orders'] = orders.filter(order_status__in=['completed', 'delivered']).count()
        context['recent_orders'] = orders.order_by('-created_at')[:10]

        # Sales statistics - use order_status to detect completed orders
        context['total_sales'] = orders.filter(order_status='completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        context['monthly_sales'] = orders.filter(order_status='completed', created_at__month=today.month).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        return context

@login_required
def order_list(request):
    """
    View for displaying the list of orders with search and filtering
    مع إضافة الفلترة الشهرية
    """
    from core.monthly_filter_utils import apply_monthly_filter, get_available_years

    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('order_status', '')
    status_param = request.GET.get('status', '')
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

    # تطبيق الفلترة الشهرية
    orders, monthly_filter_context = apply_monthly_filter(orders, request, 'order_date')
    
    # الحصول على معاملات السنة للعرض
    selected_years = request.GET.getlist('years')
    year_filter = request.GET.get('year', '')

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
            Q(order_status__icontains=search_query) |
            Q(tracking_status__icontains=search_query) |
            Q(order_date__icontains=search_query) |
            Q(expected_delivery_date__icontains=search_query)
        )

    if status_filter:
        # the status filter in the UI corresponds to the manufacturing/order_status
        orders = orders.filter(order_status=status_filter)

    # Filter by customer-facing status (e.g., VIP) if provided
    if status_param:
        # only allow known values for safety
        if status_param in ['vip', 'normal']:
            orders = orders.filter(status=status_param)

    order_type_filter = request.GET.get('order_type', '')
    if order_type_filter:
        # البحث الدقيق في selected_types مع تحسين للبحث
        orders = orders.filter(selected_types__icontains=order_type_filter)

    # فلتر التاريخ
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        orders = orders.filter(order_date__gte=date_from)
    
    if date_to:
        orders = orders.filter(order_date__lte=date_to)

    # Order by created_at
    orders = orders.order_by('-created_at')

    # Pagination
    paginator = Paginator(orders, page_size)  # Show page_size orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get currency symbol from system settings
    from accounts.models import SystemSettings
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'

    # معلومات فلتر السنة
    available_years = Order.objects.dates('order_date', 'year', order='DESC')
    available_years = [year.year for year in available_years]

    # Branches for filter dropdown
    branches = []
    if show_branch_filter:
        branches = Branch.objects.filter(is_active=True)

    # حساب الفلاتر النشطة للفلتر المضغوط
    active_filters = []
    if search_query:
        active_filters.append('search')
    if status_filter:
        active_filters.append('status')
    if status_param:
        active_filters.append('customer_status')
    if order_type_filter:
        active_filters.append('order_type')
    if branch_filter:
        active_filters.append('branch')
    if date_from:
        active_filters.append('date_from')
    if date_to:
        active_filters.append('date_to')
    if monthly_filter_context.get('selected_year'):
        active_filters.append('year')
    if monthly_filter_context.get('selected_month'):
        active_filters.append('month')

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_param': status_param,
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
        'date_from': date_from,
        'date_to': date_to,
        # سياق الفلتر المضغوط
        'has_active_filters': len(active_filters) > 0,
        'active_filters_count': len(active_filters),
        # إضافة سياق الفلترة الشهرية
        **monthly_filter_context,
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
@require_http_methods(["POST"])
def update_contract_number(request, pk):
    """تحديث رقم العقد للطلب"""
    try:
        order = Order.objects.get(pk=pk)

        # التحقق من الصلاحيات
        if not request.user.has_perm('orders.change_order'):
            return JsonResponse({
                'success': False,
                'message': 'ليس لديك صلاحية لتعديل هذا الطلب'
            }, status=403)

        # قراءة البيانات
        data = json.loads(request.body)
        contract_number = data.get('contract_number', '').strip()

        if not contract_number:
            return JsonResponse({
                'success': False,
                'message': 'رقم العقد مطلوب'
            }, status=400)

        # تحديث رقم العقد
        order.contract_number = contract_number
        order.save(update_fields=['contract_number'])

        return JsonResponse({
            'success': True,
            'message': 'تم حفظ رقم العقد بنجاح',
            'contract_number': contract_number
        })

    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'الطلب غير موجود'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)

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
    from accounts.models import SystemSettings
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'
    
    # Get rejection logs if manufacturing order exists
    rejection_logs = []
    manufacturing_order = order.manufacturing_order
    if manufacturing_order:
        try:
            rejection_logs = manufacturing_order.rejection_logs.all().order_by('-rejected_at')
        except Exception:
            pass

    context = {
        'order': order,
        'payments': payments,
        'order_items': order_items,
        'inspections': inspections,
        'currency_symbol': currency_symbol,  # Add currency symbol to context
        'rejection_logs': rejection_logs,  # Add rejection logs
        # computed totals to avoid relying on possibly-stale stored fields
        'computed_total_amount': None,
        'computed_total_discount_amount': None,
        'computed_final_price_after_discount': None,
        'computed_remaining_amount': None,
    }

    # Compute totals from items (use on-the-fly values to avoid inconsistencies)
    try:
        from decimal import Decimal
        subtotal = Decimal('0')
        total_discount = Decimal('0')
        for it in order_items:
            # use model properties which return Decimal
            subtotal += Decimal(str(it.total_price))
            total_discount += Decimal(str(it.discount_amount))

        final_after = subtotal - total_discount

        context['computed_total_amount'] = subtotal
        context['computed_total_discount_amount'] = total_discount
        context['computed_final_price_after_discount'] = final_after
        # remaining amount should be what remains to pay from the final after-discount total
        paid = Decimal(str(order.paid_amount or 0))
        context['computed_remaining_amount'] = final_after - paid
    except Exception:
        # if anything goes wrong, leave computed values as None so template falls back
        pass

    return render(request, 'orders/order_detail.html', context)

@order_create_permission_required
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

                # 4.5. معالجة الصور الإضافية للفاتورة
                additional_images = request.FILES.getlist('additional_invoice_images')
                if additional_images:
                    from .models import OrderInvoiceImage
                    for img in additional_images:
                        OrderInvoiceImage.objects.create(
                            order=order,
                            image=img
                        )

                # 5. معالجة المنتجات المحددة إن وجدت
                selected_products_json = request.POST.get('selected_products', '')
                print("selected_products_json:", selected_products_json)
                subtotal = 0
                total_discount_for_items = 0
                if selected_products_json:
                    try:
                        selected_products = json.loads(selected_products_json)
                        print("selected_products:", selected_products)
                        for product_data in selected_products:
                            # تحسين معالجة القيم العشرية لحل مشكلة الاقتطاع في الهواتف المحمولة
                            from decimal import Decimal, InvalidOperation

                            # معالجة آمنة للكمية
                            try:
                                quantity = Decimal(str(product_data['quantity']))
                                if quantity < 0:
                                    print(f"تحذير: كمية سالبة تم تجاهلها: {quantity}")
                                    continue
                            except (InvalidOperation, ValueError, TypeError) as e:
                                print(f"خطأ في تحويل الكمية: {product_data.get('quantity', 'غير محدد')} - {e}")
                                continue

                            # معالجة آمنة لسعر الوحدة
                            try:
                                unit_price = Decimal(str(product_data['unit_price']))
                                if unit_price < 0:
                                    print(f"تحذير: سعر سالب تم تجاهله: {unit_price}")
                                    continue
                            except (InvalidOperation, ValueError, TypeError) as e:
                                print(f"خطأ في تحويل سعر الوحدة: {product_data.get('unit_price', 'غير محدد')} - {e}")
                                continue

                            # معالجة آمنة لنسبة الخصم
                            try:
                                discount_percentage = Decimal(str(product_data.get('discount_percentage', 0)))
                                if discount_percentage < 0 or discount_percentage > 100:
                                    print(f"تحذير: نسبة خصم غير صالحة: {discount_percentage}% - تم تعيينها إلى 0%")
                                    discount_percentage = Decimal('0')
                            except (InvalidOperation, ValueError, TypeError) as e:
                                print(f"خطأ في تحويل نسبة الخصم: {product_data.get('discount_percentage', 'غير محدد')} - {e}")
                                discount_percentage = Decimal('0')

                            print(f"إنشاء عنصر طلب: المنتج={product_data['product_id']}, الكمية={quantity}, السعر={unit_price}, الخصم={discount_percentage}%")

                            item = OrderItem.objects.create(
                                order=order,
                                product_id=product_data['product_id'],
                                quantity=quantity,
                                unit_price=unit_price,
                                discount_percentage=discount_percentage,
                                item_type=product_data.get('item_type', 'product'),
                                notes=product_data.get('notes', '')
                            )
                            print("تم إنشاء عنصر:", item)
                            # حساب المجموع قبل الخصم ومبلغ الخصم لكل عنصر بشكل منفصل
                            item_total = item.quantity * item.unit_price
                            item_discount = item_total * (item.discount_percentage / 100) if item.discount_percentage else 0
                            subtotal += item_total
                            total_discount_for_items += item_discount
                            print("subtotal حتى الآن:", subtotal)
                    except Exception as e:
                        print(f"Error creating order items: {e}")
                # final_price should be the pre-discount subtotal
                order.final_price = subtotal
                order._is_auto_update = True  # تمييز التحديث التلقائي
                order.save(update_fields=['final_price'])
                print("order.final_price بعد الحفظ:", order.final_price)
                # اجعل المبلغ الإجمالي يساوي السعر النهائي قبل الخصم (مسمى total_amount يستخدم للـ pre-discount subtotal)
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
                    # إعادة حساب الإجماليات بعد إنشاء عناصر الطلب
                    try:
                        from .tasks import calculate_order_totals_async
                        calculate_order_totals_async.delay(order.pk)
                    except Exception:
                        try:
                            # Force recalculation locally when background tasks are not available
                            order.calculate_final_price(force_update=True)
                            order.total_amount = order.final_price
                            order.save(update_fields=['final_price', 'total_amount'])
                        except Exception:
                            pass
                else:
                    print("Formset errors:", formset.errors)

                # تم إزالة نظام إنشاء العقد الإلكتروني من النموذج التقليدي
                # يرجى استخدام نظام الويزارد لإنشاء العقود الإلكترونية
                messages.success(request, 'تم إنشاء الطلب بنجاح!')

                # إذا كان الطلب AJAX، أرجع JSON response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    # تحديد رابط التوجيه
                    if paid_amount > 0:
                        redirect_url = f'/orders/{order.pk}/success/?show_print=1&paid_amount={paid_amount}'
                    else:
                        redirect_url = f'/orders/{order.pk}/success/'

                    return JsonResponse({
                        'success': True,
                        'message': 'تم إنشاء الطلب بنجاح!',
                        'order_id': order.pk,
                        'order_number': order.order_number,
                        'redirect_url': redirect_url
                    })

                # إعادة التوجيه بناءً على الدفعة
                if paid_amount > 0:
                    return redirect(f'/orders/{order.pk}/success/?show_print=1&paid_amount={paid_amount}')
                else:
                    return redirect('orders:order_success', pk=order.pk)

            except Exception as e:
                print("حدث خطأ أثناء حفظ الطلب:", e)
                print(traceback.format_exc())

                # إذا كان الطلب AJAX، أرجع JSON response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'حدث خطأ أثناء حفظ الطلب: {str(e)}',
                        'error': str(e)
                    }, status=500)

                messages.error(request, f'حدث خطأ أثناء حفظ الطلب: {e}')
        else:
            print("--- FORM IS INVALID ---")
            print("Validation Errors:", form.errors)

            # إذا كان الطلب AJAX، أرجع JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'يرجى تصحيح الأخطاء في النموذج.'
                }, status=400)

            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج.')
    else:
        # GET request - الحصول على معرف العميل من GET إذا كان موجوداً
        customer_param = request.GET.get('customer')
        customer = None
        if customer_param:
            try:
                # محاولة البحث بالـ ID أولاً (في حالة كان رقمي) - محسن
                if customer_param.isdigit():
                    customer = Customer.objects.select_related('branch', 'category').get(id=customer_param)
                else:
                    # البحث بكود العميل إذا لم يكن رقمي - محسن
                    customer = Customer.objects.select_related('branch', 'category').get(code=customer_param)
            except Customer.DoesNotExist:
                customer = None
        
        form = OrderForm(user=request.user, customer=customer)

    # Get currency symbol from system settings
    from accounts.models import SystemSettings
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'

    context = {
        'form': form,
        'customer': customer,  # إضافة العميل للسياق
        'currency_symbol': currency_symbol,
        'title': 'إنشاء طلب جديد'
    }

    return render(request, 'orders/order_form.html', context)

@order_edit_permission_required
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
                # تتبع التعديلات قبل الحفظ
                modified_fields = {}
                
                # تتبع تعديلات حقول الطلب
                order_fields_to_track = [
                    'contract_number', 'contract_number_2', 'contract_number_3',
                    'invoice_number', 'invoice_number_2', 'invoice_number_3',
                    'notes', 'delivery_address', 'location_address',
                    'expected_delivery_date'
                ]
                
                for field_name in order_fields_to_track:
                    old_value = getattr(order, field_name)
                    new_value = form.cleaned_data.get(field_name)
                    if old_value != new_value:
                        modified_fields[field_name] = {
                            'old': old_value,
                            'new': new_value
                        }
                
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

                # تعيين المستخدم المعدل على الطلب قبل الحفظ
                order._modified_by = request.user

                # حفظ الطلب
                order.save()

                # التأكد من أن الطلب تم حفظه بنجاح وله مفتاح أساسي
                if not order.pk:
                    raise Exception("فشل في حفظ الطلب: لم يتم إنشاء مفتاح أساسي")

                # Save order items
                formset = OrderItemFormSet(request.POST, prefix='items', instance=order)
                items_modified = False
                if formset.is_valid():
                    # تتبع التعديلات في العناصر
                    for form_item in formset:
                        if form_item.cleaned_data and not form_item.cleaned_data.get('DELETE', False):
                            # عنصر جديد أو معدل
                            if form_item.instance.pk:
                                # عنصر موجود - تحقق من التعديلات
                                item_fields_to_track = ['quantity', 'unit_price', 'discount_percentage', 'product']
                                for field_name in item_fields_to_track:
                                    old_value = getattr(form_item.instance, field_name)
                                    new_value = form_item.cleaned_data.get(field_name)
                                    if str(old_value) != str(new_value):
                                        if 'order_items' not in modified_fields:
                                            modified_fields['order_items'] = []
                                        modified_fields['order_items'].append({
                                            'item_id': form_item.instance.pk,
                                            'product': str(form_item.instance.product),
                                            'field': field_name,
                                            'old': old_value,
                                            'new': new_value
                                        })
                                        items_modified = True
                            else:
                                # عنصر جديد
                                if 'new_order_items' not in modified_fields:
                                    modified_fields['new_order_items'] = []
                                modified_fields['new_order_items'].append({
                                    'product': str(form_item.cleaned_data.get('product')),
                                    'quantity': form_item.cleaned_data.get('quantity'),
                                    'unit_price': form_item.cleaned_data.get('unit_price'),
                                    'discount_percentage': form_item.cleaned_data.get('discount_percentage', 0)
                                })
                                items_modified = True
                    
                    # التحقق من العناصر المحذوفة
                    for form_item in formset.deleted_forms:
                        if form_item.instance.pk:
                            if 'deleted_order_items' not in modified_fields:
                                modified_fields['deleted_order_items'] = []
                            modified_fields['deleted_order_items'].append({
                                'item_id': form_item.instance.pk,
                                'product': str(form_item.instance.product),
                                'quantity': form_item.instance.quantity,
                                'unit_price': form_item.instance.unit_price
                            })
                            items_modified = True
                    
                    # تعيين المستخدم المعدل على جميع العناصر قبل الحفظ
                    for form_item in formset:
                        if form_item.instance.pk:  # عنصر موجود
                            form_item.instance._modified_by = request.user
                    
                    formset.save()
                    # إعادة حساب إجماليات الطلب بعد حفظ عناصر الطلب
                    try:
                        from .tasks import calculate_order_totals_async
                        calculate_order_totals_async.delay(order.pk)
                    except Exception:
                        try:
                            # Force recalculation locally when background tasks are not available
                            order.calculate_final_price(force_update=True)
                            order.total_amount = order.final_price
                            order.save(update_fields=['final_price', 'total_amount'])
                        except Exception:
                            pass
                else:
                    print("UPDATE - Formset errors:", formset.errors)
                    messages.warning(request, 'تم تحديث الطلب ولكن هناك أخطاء في عناصر الطلب.')

                # إنشاء سجل التعديل اليدوي إذا كانت هناك تعديلات
                # تم تعطيل هذا لأن signals تقوم بإنشاء السجلات الآن
                # if modified_fields:
                #     from .models import OrderModificationLog
                #     
                #     modification_details = []
                #     
                #     # تفاصيل تعديلات حقول الطلب
                #     field_labels = {
                #         'contract_number': 'رقم العقد',
                #         'contract_number_2': 'رقم العقد الإضافي 2',
                #         'contract_number_3': 'رقم العقد الإضافي 3',
                #         'invoice_number': 'رقم الفاتورة',
                #         'invoice_number_2': 'رقم الفاتورة الإضافي 2',
                #         'invoice_number_3': 'رقم الفاتورة الإضافي 3',
                #         'notes': 'الملاحظات',
                #         'delivery_address': 'عنوان التسليم',
                #         'location_address': 'عنوان التركيب',
                #         'expected_delivery_date': 'تاريخ التسليم المتوقع'
                #     }
                #     
                #     for field_name, values in modified_fields.items():
                #         if field_name in field_labels:
                #             old_val = values.get('old') or 'غير محدد'
                #             new_val = values.get('new') or 'غير محدد'
                #             modification_details.append(f"{field_labels[field_name]}: {old_val} → {new_val}")
                #         elif field_name == 'order_items':
                #             modification_details.append(f"تعديل {len(values)} عنصر من عناصر الطلب")
                #         elif field_name == 'new_order_items':
                #             modification_details.append(f"إضافة {len(values)} عنصر جديد للطلب")
                #         elif field_name == 'deleted_order_items':
                #             modification_details.append(f"حذف {len(values)} عنصر من الطلب")
                #     
                #     OrderModificationLog.objects.create(
                #         order=order,
                #         modification_type='تعديل يدوي للطلب',
                #         modified_by=request.user,
                #         details=' | '.join(modification_details) if modification_details else 'تعديل على الطلب',
                #         notes='تعديل يدوي من قبل المستخدم',
                #         is_manual_modification=True,
                #         modified_fields=modified_fields
                #     )

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
    from accounts.models import SystemSettings
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'

    context = {
        'form': form,
        'order': order,
        'currency_symbol': currency_symbol,
        'title': f'تعديل الطلب: {order.order_number}'
    }

    return render(request, 'orders/order_form.html', context)

@order_delete_permission_required
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
            # الآن نموذج Order يتعامل مع حذف السجلات بشكل آمن
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
    from accounts.models import SystemSettings
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
    View for listing salespersons and their orders - Optimized to fix N+1 query problem
    """
    # استخدام annotate لحساب الإحصائيات في استعلام واحد بدلاً من N+1
    from django.db.models import Case, When, IntegerField
    
    salespersons = Salesperson.objects.select_related('branch').annotate(
        total_orders=Count('order'),
        completed_orders=Count(
            Case(
                When(order__status='completed', then=1),
                output_field=IntegerField()
            )
        ),
        pending_orders=Count(
            Case(
                When(order__status='pending', then=1),
                output_field=IntegerField()
            )
        ),
        total_sales=Sum(
            Case(
                When(order__status='completed', then='order__total_amount'),
                default=0,
                output_field=models.DecimalField(max_digits=10, decimal_places=2)
            )
        )
    ).prefetch_related('order_set')

    context = {
        'salespersons': salespersons,
        'title': 'قائمة مندوبي المبيعات'
    }

    return render(request, 'orders/salesperson_list.html', context)

@order_edit_permission_required
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

    # Get customer notes
    from customers.models import CustomerNote
    customer_notes = CustomerNote.objects.filter(
        customer=order.customer
    ).select_related('created_by').order_by('-created_at')[:5]

    # Check if there are manual modifications
    has_manual_modifications = order.modification_logs.filter(is_manual_modification=True).exists()
    
    # Get currency symbol from system settings
    from accounts.models import SystemSettings
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'
    
    # Get rejection logs if manufacturing order exists
    rejection_logs = []
    manufacturing_order = order.manufacturing_order
    if manufacturing_order:
        try:
            rejection_logs = manufacturing_order.rejection_logs.all().order_by('-rejected_at')
        except Exception:
            pass

    context = {
        'order': order,
        'payments': payments,
        'order_items': order_items,
        'inspections': inspections,
        'customer_notes': customer_notes,
        'can_edit': can_user_edit_order(request.user, order),
        'can_delete': can_user_delete_order(request.user, order),
        'has_manual_modifications': has_manual_modifications,
        'currency_symbol': currency_symbol,
        'rejection_logs': rejection_logs,
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

    # Get customer notes
    from customers.models import CustomerNote
    customer_notes = CustomerNote.objects.filter(
        customer=order.customer
    ).select_related('created_by').order_by('-created_at')[:5]
    
    # Get currency symbol from system settings
    system_settings = SystemSettings.get_settings()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'
    
    # Get rejection logs if manufacturing order exists
    rejection_logs = []
    manufacturing_order = order.manufacturing_order
    if manufacturing_order:
        try:
            rejection_logs = manufacturing_order.rejection_logs.all().order_by('-rejected_at')
        except Exception:
            pass

    context = {
        'order': order,
        'payments': payments,
        'order_items': order_items,
        'inspections': inspections,
        'customer_notes': customer_notes,
        'can_edit': can_user_edit_order(request.user, order),
        'can_delete': can_user_delete_order(request.user, order),
        'currency_symbol': currency_symbol,
        'rejection_logs': rejection_logs,
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


@order_edit_permission_required
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

            # حفظ الطلب مع تتبع المستخدم
            updated_order = form.save(commit=False)
            updated_order._modified_by = request.user
            updated_order.save()

            # حفظ عناصر الطلب مع تمرير المستخدم الحالي
            formset.instance = updated_order
            # تمرير المستخدم الحالي إلى كل عنصر طلب
            for form_item in formset:
                if form_item.instance:
                    form_item.instance._modified_by = request.user
            formset.save()

            # إعادة حساب المبلغ الإجمالي
            # حاول استخدام مهمة الخلفية ثم احتياطي محلي
            try:
                from .tasks import calculate_order_totals_async
                calculate_order_totals_async.delay(updated_order.pk)
            except Exception:
                try:
                    updated_order.calculate_total()
                except Exception:
                    pass

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


@order_delete_permission_required
def order_delete_by_number(request, order_number):
    """حذف الطلب باستخدام رقم الطلب"""
    order = get_object_or_404(Order, order_number=order_number)

    if not can_user_delete_order(request.user, order):
        messages.error(request, "ليس لديك صلاحية لحذف هذا الطلب.")
        return redirect("orders:order_detail_by_number", order_number=order_number)

    if request.method == 'POST':
        order_number_for_message = order.order_number

        try:
            # الآن نموذج Order يتعامل مع حذف السجلات بشكل آمن
            order.delete()
            messages.success(request, f'تم حذف الطلب {order_number_for_message} بنجاح.')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف الطلب: {str(e)}')

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
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'

    # إنشاء جدول العناصر مرة واحدة للاستخدام في كلا الفرعين (يشمل عمود الخصم وحساب الإجمالي بعد الخصم)
    items_html_rows = []
    for item in order.items.all():
        # تنسيق الأرقام وإجراء حسابات الخصم لكل سطر
        try:
            unit_price = float(item.unit_price or 0)
            line_total = float(item.total_price or 0)
            quantity = float(item.quantity or 0)
            discount_pct = float(item.discount_percentage or 0)
            discount_amount = float(getattr(item, 'discount_amount', 0) or 0)
            line_total_after_discount = float(getattr(item, 'total_after_discount', line_total) or 0)

            unit_price_formatted = f"{unit_price:.2f}".rstrip('0').rstrip('.')
            line_total_formatted = f"{line_total:.2f}".rstrip('0').rstrip('.')
            discount_pct_formatted = f"{discount_pct:.2f}".rstrip('0').rstrip('.')
            line_after_discount_formatted = f"{line_total_after_discount:.2f}".rstrip('0').rstrip('.')
        except (ValueError, TypeError):
            unit_price_formatted = "0"
            line_total_formatted = "0"
            discount_pct_formatted = "0"
            line_after_discount_formatted = "0"
            quantity = 0

        # Append a row with: description | qty | unit price | discount% | total after discount
        items_html_rows.append(
            f"""
            <tr>
                <td style=\"padding:10px;border:1px solid #ddd;text-align:right;word-break:break-word;\">{item.product.name if getattr(item, 'product', None) else 'منتج'}</td>
                <td style=\"padding:10px;border:1px solid #ddd;text-align:center;\">{int(quantity) if float(quantity).is_integer() else (str(quantity).rstrip('0').rstrip('.'))}</td>
                <td style=\"padding:10px;border:1px solid #ddd;text-align:center;\">{unit_price_formatted} {currency_symbol}</td>
                <td style=\"padding:10px;border:1px solid #ddd;text-align:center;\">{discount_pct_formatted}%</td>
                <td style=\"padding:10px;border:1px solid #ddd;text-align:center;\">{line_after_discount_formatted} {currency_symbol}</td>
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
            # حساب المبلغ النهائي بعد الخصم (افضل استخدام الخاصية إذا كانت متاحة)
            try:
                final_after = float(getattr(order, 'final_price_after_discount', None))
            except Exception:
                final_after = float(total_amount) - float(getattr(order, 'total_discount_amount', 0) or 0)
            remaining_amount = max(0, final_after - paid_amount)  # تجنب القيم السالبة

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

        # حساب مجاميع الخصم والسعر النهائي بعد الخصم واستبدال العناصر المناسبة
        try:
            total_discount_amount_val = float(getattr(order, 'total_discount_amount', 0) or 0)
        except Exception:
            total_discount_amount_val = 0
        try:
            final_price_after_discount_val = float(getattr(order, 'final_price_after_discount', None) or getattr(order, 'final_price', None) or float(order.total_amount or 0) - total_discount_amount_val)
        except Exception:
            final_price_after_discount_val = 0

        total_discount_formatted = f"{total_discount_amount_val:.2f}".rstrip('0').rstrip('.')
        final_price_after_discount_formatted = f"{final_price_after_discount_val:.2f}".rstrip('0').rstrip('.')

        # استبدال نُسخ القوالب للخصم والسعر النهائي بعد الخصم
        html_content = html_content.replace('${order.total_discount_amount}', total_discount_formatted)
        html_content = html_content.replace('${order.final_price_after_discount}', final_price_after_discount_formatted)

        # مجاميع أساسية - استبدال الأرقام الثابتة القديمة
        try:
            paid_amount_val = float(order.paid_amount or 0)
            total_amount_val = float(order.final_price or order.total_amount or 0)
            # remaining should be calculated from the final after-discount total
            try:
                # prefer computed final price if we already calculated it
                remaining_amount_val = max(0, float(final_price_after_discount_val) - paid_amount_val)
            except Exception:
                # fallback to the order property
                remaining_amount_val = max(0, float(getattr(order, 'final_price_after_discount', None) or getattr(order, 'final_price', None) or total_amount_val) - paid_amount_val)
            
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
            # compute final after discount (prefer property if available)
            try:
                final_after = float(getattr(order, 'final_price_after_discount', None))
            except Exception:
                # compute fallback: subtotal - total_discount_amount
                final_after = float(total_amount) - float(getattr(order, 'total_discount_amount', 0) or 0)
            remaining_amount = max(0, final_after - paid_amount)
            
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

            # جدولة رفع الملف إلى Google Drive بشكل غير متزامن
            from .tasks import upload_contract_to_drive_async
            try:
                upload_contract_to_drive_async.delay(order.pk)
                success_message = 'تم جدولة رفع الملف إلى Google Drive. سيتم الرفع في الخلفية.'
                status = 'scheduled'
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'فشل في جدولة رفع الملف: {str(e)}'
                })

            return JsonResponse({
                'success': True,
                'message': success_message,
                'data': {
                    'order_id': order.pk,
                    'status': status,
                    'message': 'جاري الرفع في الخلفية...'
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

@login_required
def order_status_history(request, order_id):
    """عرض سجل تفصيلي لتغييرات حالة الطلب"""
    order = get_object_or_404(Order, id=order_id)
    
    # التحقق من الصلاحيات
    if not request.user.has_perm('orders.view_order'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("ليس لديك صلاحية لعرض تفاصيل الطلب")
    
    # الحصول على سجلات تغيير الحالة
    status_logs = order.status_logs.all().order_by('-created_at')
    
    # البحث والفلترة
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    user_filter = request.GET.get('user', '')
    change_type_filter = request.GET.get('change_type', '')
    is_automatic_filter = request.GET.get('is_automatic', '')

    if search_query:
        status_logs = status_logs.filter(
            Q(notes__icontains=search_query) |
            Q(changed_by__first_name__icontains=search_query) |
            Q(changed_by__last_name__icontains=search_query) |
            Q(changed_by__username__icontains=search_query)
        )

    if status_filter:
        status_logs = status_logs.filter(new_status=status_filter)

    if user_filter:
        status_logs = status_logs.filter(changed_by__id=user_filter)

    if change_type_filter:
        status_logs = status_logs.filter(change_type=change_type_filter)

    if is_automatic_filter:
        is_auto = is_automatic_filter.lower() == 'true'
        status_logs = status_logs.filter(is_automatic=is_auto)
    
    # الترقيم
    paginator = Paginator(status_logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # الحصول على قائمة الحالات للمفلتر (حالات الأقسام)
    status_choices = []

    # إضافة حالات الطلب الأساسية
    status_choices.extend(Order.ORDER_STATUS_CHOICES)

    # إضافة حالات المعاينة
    try:
        from inspections.models import Inspection
        inspection_choices = [(f"inspection_{choice[0]}", f"معاينة: {choice[1]}") for choice in Inspection.STATUS_CHOICES]
        status_choices.extend(inspection_choices)
    except ImportError:
        pass

    # إضافة حالات التركيب
    try:
        from installations.models import InstallationSchedule
        installation_choices = [(f"installation_{choice[0]}", f"تركيب: {choice[1]}") for choice in InstallationSchedule.STATUS_CHOICES]
        status_choices.extend(installation_choices)
    except ImportError:
        pass

    # إضافة حالات التصنيع
    try:
        from manufacturing.models import ManufacturingOrder
        manufacturing_choices = [(f"manufacturing_{choice[0]}", f"تصنيع: {choice[1]}") for choice in ManufacturingOrder.STATUS_CHOICES]
        status_choices.extend(manufacturing_choices)
    except ImportError:
        pass

    # إضافة حالات التقطيع
    try:
        from cutting.models import CuttingOrder
        cutting_choices = [(f"cutting_{choice[0]}", f"تقطيع: {choice[1]}") for choice in CuttingOrder.STATUS_CHOICES]
        status_choices.extend(cutting_choices)
    except ImportError:
        pass

    # الحصول على قائمة المستخدمين للمفلتر
    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.filter(
        id__in=status_logs.values_list('changed_by', flat=True).distinct()
    ).order_by('first_name', 'last_name')
    
    context = {
        'order': order,
        'page_obj': page_obj,
        'status_logs': page_obj,
        'status_choices': status_choices,
        'users': users,
        'total_logs': status_logs.count(),
        'search_query': search_query,
        'status_filter': status_filter,
        'user_filter': user_filter,
        'change_type_filter': change_type_filter,
        'is_automatic_filter': is_automatic_filter,
        'search_query': search_query,
        'status_filter': status_filter,
        'user_filter': user_filter,
        'total_logs': status_logs.count(),
    }
    
    return render(request, 'orders/status_history.html', context)


@login_required
@require_http_methods(["POST"])
def check_invoice_duplicate(request):
    """
    API للتحقق من تكرار رقم الفاتورة للعميل نفسه مع نفس نوع الطلب
    """
    try:
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        invoice_number = data.get('invoice_number', '').strip()
        order_type = data.get('order_type', '')
        current_order_id = data.get('current_order_id')  # للتعديل
        
        if not customer_id or not invoice_number:
            return JsonResponse({
                'is_duplicate': False,
                'message': ''
            })
        
        # البحث عن طلبات سابقة للعميل بنفس رقم المرجع
        existing_orders = Order.objects.filter(
            customer_id=customer_id
        ).filter(
            Q(invoice_number=invoice_number) |
            Q(invoice_number_2=invoice_number) |
            Q(invoice_number_3=invoice_number)
        )
        
        # استثناء الطلب الحالي في حالة التعديل
        if current_order_id:
            existing_orders = existing_orders.exclude(pk=current_order_id)
        
        # التحقق من وجود طلب بنفس النوع
        for existing_order in existing_orders:
            try:
                existing_types = existing_order.get_selected_types_list()
                if order_type in existing_types:
                    return JsonResponse({
                        'is_duplicate': True,
                        'message': f'⚠️ رقم المرجع "{invoice_number}" مستخدم مسبقاً لهذا العميل في طلب من نفس النوع (رقم الطلب: {existing_order.order_number})',
                        'order_number': existing_order.order_number
                    })
            except:
                pass
        
        return JsonResponse({
            'is_duplicate': False,
            'message': ''
        })
        
    except Exception as e:
        logger.error(f"خطأ في التحقق من تكرار رقم الفاتورة: {str(e)}")
        return JsonResponse({
            'is_duplicate': False,
            'message': '',
            'error': str(e)
        })
