from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import models
import json
from datetime import timedelta
from orders.models import Order
from accounts.models import SystemSettings
from .models import (
    InstallationSchedule, InstallationTeam, Technician, Driver,
    ModificationRequest, ModificationImage, ManufacturingOrder,
    ModificationReport, ReceiptMemo, InstallationPayment, InstallationArchive, CustomerDebt,
    ModificationErrorAnalysis, ModificationErrorType
)
from .forms import (
    InstallationScheduleForm, InstallationTeamForm, TechnicianForm, TechnicianEditForm, DriverForm,
    ModificationRequestForm, ModificationImageForm, ManufacturingOrderForm,
    ModificationReportForm, ReceiptMemoForm, InstallationPaymentForm,
    InstallationStatusForm, ModificationErrorAnalysisForm, InstallationFilterForm,
    QuickScheduleForm, DailyScheduleForm, CustomerDebtForm
)
from django.urls import reverse


def currency_format(amount):
    """تنسيق المبلغ مع عملة النظام"""
    try:
        settings = SystemSettings.get_settings()
        symbol = settings.currency_symbol
        formatted_amount = f"{amount:,.2f}"
        return f"{formatted_amount} {symbol}"
    except Exception:
        return f"{amount:,.2f} ر.س"


@login_required
def dashboard(request):
    """لوحة تحكم التركيبات - محسّنة للأداء"""
    from django.db.models import Q, Count
    from manufacturing.models import ManufacturingOrder
    
    # استخدام select_related و prefetch_related لتحسين الأداء
    
    # 1. إحصائيات عامة - إجمالي طلبات التركيب في النظام
    total_installation_orders = Order.objects.filter(
        selected_types__icontains='installation'
    ).count()

    # 2. إحصائيات التركيبات المجدولة - استعلام واحد فقط
    installation_stats = InstallationSchedule.objects.aggregate(
        completed=Count('id', filter=Q(status='completed')),
        in_installation=Count('id', filter=Q(status='in_installation')),
        scheduled=Count('id', filter=Q(status='scheduled')),
        pending=Count('id', filter=Q(status='pending')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        modification_required=Count('id', filter=Q(status='modification_required')),
    )

    # 3. الطلبات الجاهزة للتركيب - استعلام محسّن
    ready_orders_query = Order.objects.filter(
        selected_types__icontains='installation',
        order_status__in=['ready_install', 'completed'],
        installationschedule__isnull=True
    )
    
    ready_manufacturing_query = ManufacturingOrder.objects.filter(
        status__in=['ready_install', 'delivered'],
        order__selected_types__icontains='installation',
        order__installationschedule__isnull=True
    )
    
    # حساب العدد بطريقة محسّنة
    ready_order_ids = set(ready_orders_query.values_list('id', flat=True))
    ready_mfg_order_ids = set(ready_manufacturing_query.values_list('order_id', flat=True))
    total_orders_ready_for_installation = len(ready_order_ids | ready_mfg_order_ids)

    # 4. إحصائيات أخرى محسّنة
    orders_with_debt = Order.objects.filter(
        selected_types__icontains='installation',
        total_amount__gt=F('paid_amount')
    ).count()

    orders_in_manufacturing = ManufacturingOrder.objects.filter(
        status__in=['pending', 'in_progress'],
        order__selected_types__icontains='installation'
    ).count()

    delivered_manufacturing_orders = ManufacturingOrder.objects.filter(
        status='delivered',
        order__selected_types__icontains='installation'
    ).count()

    # 5. التركيبات المجدولة اليوم - مع select_related (استبعاد المكتملة)
    today = timezone.now().date()
    today_installations = InstallationSchedule.objects.filter(
        scheduled_date=today,
        status__in=['scheduled', 'pending', 'in_progress', 'in_installation']
    ).exclude(status='completed').select_related('order__customer', 'team')[:10]

    # 6. التركيبات القادمة - محدودة (استبعاد المكتملة)
    upcoming_installations = InstallationSchedule.objects.filter(
        scheduled_date__gt=today,
        status__in=['scheduled', 'pending', 'in_progress', 'in_installation']
    ).exclude(status='completed').select_related('order__customer', 'team')[:5]

    # 7. الطلبات الجديدة - محسّنة
    recent_orders = Order.objects.filter(
        selected_types__icontains='installation',
        created_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).select_related('customer', 'manufacturing_order')[:10]

    # 8. الطلبات التي تحتاج جدولة - محسّنة ومحدودة
    orders_needing_scheduling = list(
        Order.objects.filter(
            selected_types__icontains='installation',
            order_status__in=['ready_install', 'completed'],
            installationschedule__isnull=True
        ).select_related('customer', 'manufacturing_order')[:10]
    )
    
    # إضافة أوامر التصنيع الجاهزة (بدون تكرار)
    existing_order_ids = {order.id for order in orders_needing_scheduling}
    additional_mfg_orders = ManufacturingOrder.objects.filter(
        status__in=['ready_install', 'delivered'],
        order__selected_types__icontains='installation',
        order__installationschedule__isnull=True
    ).exclude(order_id__in=existing_order_ids).select_related('order__customer')[:5]
    
    additional_orders = [mfg.order for mfg in additional_mfg_orders]
    orders_needing_scheduling.extend(additional_orders)

    # 9. إحصائيات الفرق - محسّنة
    teams_stats = InstallationTeam.objects.filter(
        is_active=True
    ).annotate(
        installations_count=Count('installationschedule')
    )

    context = {
        'total_installations': total_installation_orders,
        'completed_installations': installation_stats['completed'],
        'pending_installations': installation_stats['pending'],
        'in_progress_installations': installation_stats['in_progress'],
        'in_installation_installations': installation_stats['in_installation'],
        'scheduled_installations': installation_stats['scheduled'],
        'orders_ready_for_installation': total_orders_ready_for_installation,
        'total_modifications': installation_stats['modification_required'],
        'orders_with_debt': orders_with_debt,
        'orders_in_manufacturing': orders_in_manufacturing,
        'delivered_manufacturing_orders': delivered_manufacturing_orders,
        'today_installations': today_installations,
        'upcoming_installations': upcoming_installations,
        'recent_orders': recent_orders,
        'orders_needing_scheduling': orders_needing_scheduling,
        'teams_stats': teams_stats,
    }

    return render(request, 'installations/dashboard.html', context)

    return render(request, 'installations/dashboard.html', context)


@login_required
def change_installation_status(request, installation_id):
    """تغيير حالة التركيب مع نافذة منبثقة ذكية"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)

    if request.method == 'POST':
        form = InstallationStatusForm(request.POST, instance=installation)
        if form.is_valid():
            old_status = installation.status
            new_status = form.cleaned_data['status']
            reason = form.cleaned_data.get('reason', '')
            
            # حفظ التغيير
            installation = form.save()

            # إنشاء سجل تغيير الحالة
            from .models import InstallationStatusLog, InstallationEventLog
            InstallationStatusLog.objects.create(
                installation=installation,
                old_status=old_status,
                new_status=new_status,
                changed_by=request.user,
                reason=reason,
                notes=form.cleaned_data.get('notes', '')
            )

            # إنشاء سجل حدث
            InstallationEventLog.objects.create(
                installation=installation,
                event_type='status_change',
                description=f'تم تغيير الحالة من {dict(InstallationSchedule.STATUS_CHOICES)[old_status]} إلى {dict(InstallationSchedule.STATUS_CHOICES)[new_status]}',
                user=request.user,
                metadata={
                    'old_status': old_status,
                    'new_status': new_status,
                    'reason': reason
                }
            )

            # إنشاء أمر تصنيع تعديل إذا تم طلب تعديل
            if new_status == 'modification_required':
                # إنشاء طلب تعديل تلقائياً
                modification_request = ModificationRequest.objects.create(
                    installation=installation,
                    customer=installation.order.customer,
                    modification_type='تعديل مطلوب',
                    description=reason or 'طلب تعديل من قسم التركيبات',
                    priority='medium'
                )
                
                # إنشاء أمر تصنيع تعديل في المصنع
                ManufacturingOrder.objects.create(
                    modification_request=modification_request,
                    order_type='modification',
                    status='pending',
                    description=f'أمر تعديل من قسم التركيبات - {reason}'
                )

            # تحديث حالة الطلب عند الإكمال
            if new_status == 'completed' and old_status != 'completed':
                installation.order.order_status = 'completed'
                installation.order.save()
                messages.success(request, 'تم إكمال التركيب بنجاح')
            else:
                messages.success(request, 'تم تحديث حالة التركيب بنجاح')

            # إرجاع JSON للنافذة المنبثقة
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'تم تحديث حالة التركيب بنجاح',
                    'new_status': new_status,
                    'new_status_display': installation.get_status_display()
                })

            return redirect('installations:installation_detail', installation_id=installation.id)
        else:
            # إرجاع أخطاء النموذج للنافذة المنبثقة
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = InstallationStatusForm(instance=installation)

    # للطلبات AJAX، إرجاع النموذج كـ HTML
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        context = {
            'form': form,
            'installation': installation,
            'title': 'تغيير حالة التركيب'
        }
        from django.template.loader import render_to_string
        html = render_to_string('installations/change_status_modal.html', context, request=request)
        return JsonResponse({'html': html})

    context = {
        'form': form,
        'installation': installation,
        'title': 'تغيير حالة التركيب'
    }

    return render(request, 'installations/change_status.html', context)


@login_required
def installation_list(request):
    """قائمة التركيبات - محسّنة مع فلاتر ذكية"""
    from django.db.models import Q
    from manufacturing.models import ManufacturingOrder
    
    # معالجة الفلاتر
    filter_form = InstallationFilterForm(request.GET)
    
    # استخراج قيم الفلاتر
    status_filter = request.GET.get('status', '')
    team_filter = request.GET.get('team', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '').strip()
    location_type_filter = request.GET.get('location_type', '')
    order_status_filter = request.GET.get('order_status', '')
    
    # بناء الاستعلامات بطريقة محسّنة
    installation_items = []
    
    # 1. جلب التركيبات المجدولة
    if not status_filter or status_filter in ['scheduled', 'in_installation', 'completed', 'cancelled', 'modification_required', 'modification_in_progress', 'modification_completed']:
        scheduled_query = InstallationSchedule.objects.select_related(
            'order__customer', 'team'
        )
        
        # تطبيق فلاتر التركيبات المجدولة
        if status_filter and status_filter != 'needs_scheduling':
            scheduled_query = scheduled_query.filter(status=status_filter)
        if team_filter:
            scheduled_query = scheduled_query.filter(team_id=team_filter)
        if location_type_filter:
            scheduled_query = scheduled_query.filter(location_type=location_type_filter)
        if date_from:
            try:
                date_from_obj = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
                scheduled_query = scheduled_query.filter(scheduled_date__gte=date_from_obj)
            except ValueError:
                pass
        if date_to:
            try:
                date_to_obj = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
                scheduled_query = scheduled_query.filter(scheduled_date__lte=date_to_obj)
            except ValueError:
                pass
        if search:
            search_q = Q(order__order_number__icontains=search) | \
                      Q(order__customer__name__icontains=search) | \
                      Q(order__customer__phone__icontains=search)
            scheduled_query = scheduled_query.filter(search_q)
        
        # إضافة التركيبات المجدولة للقائمة
        for installation in scheduled_query:
            installation_items.append({
                'type': 'scheduled',
                'installation': installation,
                'order': installation.order,
                'customer': installation.order.customer,
                'team': installation.team,
                'status': installation.status,
                'scheduled_date': installation.scheduled_date,
                'created_at': installation.created_at,
                'location_type': getattr(installation, 'location_type', None),
            })
    
    # 2. جلب الطلبات الجاهزة للتركيب (غير المجدولة)
    if not status_filter or status_filter == 'needs_scheduling':
        # الطلبات العادية الجاهزة
        ready_orders_query = Order.objects.filter(
            selected_types__icontains='installation',
            order_status__in=['ready_install', 'completed'],
            installationschedule__isnull=True
        ).select_related('customer')
        
        # تطبيق فلاتر الطلبات الجاهزة
        if order_status_filter:
            ready_orders_query = ready_orders_query.filter(order_status=order_status_filter)
        if search:
            search_q = Q(order_number__icontains=search) | \
                      Q(customer__name__icontains=search) | \
                      Q(customer__phone__icontains=search)
            ready_orders_query = ready_orders_query.filter(search_q)
        
        # إضافة الطلبات العادية
        for order in ready_orders_query:
            installation_items.append({
                'type': 'needs_scheduling',
                'installation': None,
                'order': order,
                'customer': order.customer,
                'team': None,
                'status': 'needs_scheduling',
                'scheduled_date': None,
                'created_at': order.created_at,
                'location_type': getattr(order, 'location_type', None),
            })
        
        # أوامر التصنيع الجاهزة
        ready_manufacturing_query = ManufacturingOrder.objects.filter(
            status__in=['ready_install', 'delivered'],
            order__selected_types__icontains='installation',
            order__installationschedule__isnull=True
        ).select_related('order__customer')
        
        # تطبيق نفس فلاتر البحث
        if search:
            search_q = Q(order__order_number__icontains=search) | \
                      Q(order__customer__name__icontains=search) | \
                      Q(order__customer__phone__icontains=search)
            ready_manufacturing_query = ready_manufacturing_query.filter(search_q)
        
        # تجنب التكرار
        existing_order_ids = {item['order'].id for item in installation_items if item['type'] == 'needs_scheduling'}
        
        for mfg_order in ready_manufacturing_query:
            if mfg_order.order_id not in existing_order_ids:
                installation_items.append({
                    'type': 'needs_scheduling',
                    'installation': None,
                    'order': mfg_order.order,
                    'customer': mfg_order.order.customer,
                    'team': None,
                    'status': 'needs_scheduling',
                    'scheduled_date': None,
                    'created_at': mfg_order.created_at,
                    'location_type': getattr(mfg_order.order, 'location_type', None),
                })
    
    # 3. جلب الطلبات تحت التصنيع (للعرض فقط)
    if not status_filter or status_filter == 'under_manufacturing':
        under_manufacturing_query = ManufacturingOrder.objects.filter(
            status__in=['pending_approval', 'approved', 'in_cutting', 'cutting_completed', 'in_manufacturing', 'quality_check'],
            order__selected_types__icontains='installation'
        ).select_related('order__customer')
        
        # تطبيق فلاتر البحث
        if search:
            search_q = Q(order__order_number__icontains=search) | \
                      Q(order__customer__name__icontains=search) | \
                      Q(order__customer__phone__icontains=search)
            under_manufacturing_query = under_manufacturing_query.filter(search_q)
        
        for mfg_order in under_manufacturing_query:
            installation_items.append({
                'type': 'under_manufacturing',
                'installation': None,
                'order': mfg_order.order,
                'customer': mfg_order.order.customer,
                'team': None,
                'status': 'under_manufacturing',
                'manufacturing_status': mfg_order.status,
                'scheduled_date': None,
                'created_at': mfg_order.created_at,
                'location_type': None,
            })
    
    # ترتيب النتائج حسب الأولوية والتاريخ
    def sort_key(item):
        # أولوية للطلبات التي تحتاج جدولة
        if item['status'] == 'needs_scheduling':
            return (0, item['created_at'])
        elif item['status'] == 'scheduled':
            return (1, item['scheduled_date'] or item['created_at'])
        else:
            return (2, item['created_at'])
    
    installation_items.sort(key=sort_key, reverse=True)
    
    # ترقيم الصفحات
    from django.core.paginator import Paginator
    page_size = int(request.GET.get('page_size', 25))
    paginator = Paginator(installation_items, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # إحصائيات سريعة
    total_count = len(installation_items)
    needs_scheduling_count = sum(1 for item in installation_items if item['status'] == 'needs_scheduling')
    scheduled_count = sum(1 for item in installation_items if item['status'] in ['scheduled', 'in_installation'])
    completed_count = sum(1 for item in installation_items if item['status'] == 'completed')

    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'installations': page_obj,
        'has_filters': bool(status_filter or team_filter or date_from or date_to or search or location_type_filter or order_status_filter),
        # إحصائيات
        'total_count': total_count,
        'needs_scheduling_count': needs_scheduling_count,
        'scheduled_count': scheduled_count,
        'completed_count': completed_count,
        # قيم الفلاتر الحالية للـ URL parameters
        'current_filters': {
            'status': status_filter,
            'team': team_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
            'location_type': location_type_filter,
            'order_status': order_status_filter,
            'page_size': page_size,
        }
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
    # تصحيح ��لعلاقة مع ModificationReport
    modification_reports = ModificationReport.objects.filter(
        modification_request__installation=installation
    )
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
    
    # التحقق من أن التركيب بحاجة جدولة
    if installation.status not in ['needs_scheduling', 'pending']:
        messages.warning(request, 'هذا التركيب لا يحتاج جدولة أو تم جدولته بالفعل')
        return redirect('installations:installation_detail', installation_id=installation.id)

    if request.method == 'POST':
        form = InstallationScheduleForm(request.POST, instance=installation)
        if form.is_valid():
            installation = form.save(commit=False)
            installation.status = 'scheduled'  # تغيير الحالة إلى مجدول
            installation.save()
            
            # إنشاء سجل حدث
            from .models import InstallationEventLog
            InstallationEventLog.objects.create(
                installation=installation,
                event_type='schedule_change',
                description=f'تم جدولة التركيب للتاريخ {installation.scheduled_date} في الساعة {installation.scheduled_time}',
                user=request.user,
                metadata={
                    'scheduled_date': str(installation.scheduled_date),
                    'scheduled_time': str(installation.scheduled_time),
                    'team': installation.team.name if installation.team else None
                }
            )
            
            messages.success(request, _('تم جدولة التركيب بنجاح'))
            return redirect('installations:installation_detail', installation_id=installation.id)
    else:
        # تعيين قيم افتراضية للجدولة (48 ساعة من الآن)
        scheduled_date = timezone.now().date() + timezone.timedelta(days=2)
        default_time = timezone.datetime.strptime('09:00', '%H:%M').time()
        
        # محاولة جلب عدد الشبابيك من ملف المعاينة
        windows_count = None
        try:
            # البحث عن ملف معاينة للطلب
            from inspections.models import InspectionOrder
            inspection_orders = InspectionOrder.objects.filter(
                order=installation.order
            ).order_by('-created_at')
            
            if inspection_orders.exists():
                latest_inspection = inspection_orders.first()
                # محاولة استخراج عدد الشبابيك من ملاحظات المعاينة
                if latest_inspection.notes:
                    import re
                    # البحث عن أرقام في الملاحظات
                    numbers = re.findall(r'\d+', latest_inspection.notes)
                    if numbers:
                        windows_count = int(numbers[0])  # أول رقم في الملاحظات
                elif hasattr(latest_inspection, 'windows_count') and latest_inspection.windows_count:
                    windows_count = latest_inspection.windows_count
        except Exception as e:
            print(f"خطأ في جلب عدد الشبابيك: {e}")
        
        initial_data = {
            'scheduled_date': scheduled_date,
            'scheduled_time': default_time
        }
        
        if windows_count:
            initial_data['windows_count'] = windows_count
        
        form = InstallationScheduleForm(instance=installation, initial=initial_data)

    context = {
        'form': form,
        'installation': installation,
        'title': 'جدولة التركيب'
    }

    return render(request, 'installations/schedule_installation.html', context)


@login_required
def update_status(request, installation_id):
    """تحديث حالة التركيب"""
    try:
        installation = get_object_or_404(InstallationSchedule, id=installation_id)
        
        if request.method == 'POST':
            new_status = request.POST.get('status')
            
            # التحقق من صحة الحالة الجديدة
            if not new_status:
                return JsonResponse({
                    'success': False,
                    'error': 'لم يتم تحديد الحالة الجديدة'
                })
            
            # التحقق من أن الحالة صحيحة
            valid_statuses = dict(InstallationSchedule.STATUS_CHOICES)
            if new_status not in valid_statuses:
                return JsonResponse({
                    'success': False,
                    'error': f'الحالة غير صحيحة: {new_status}'
                })
            
            # حفظ الحالة القديمة
            old_status = installation.status
            
            # تحديث الحالة بدون التحقق من Google Drive
            installation.status = new_status
            # استخدام update_fields لتجنب استدعاء دالة save الكاملة
            installation.save(update_fields=['status'])
            
            # إنشاء سجل حدث
            try:
                from .models import InstallationEventLog
                InstallationEventLog.objects.create(
                    installation=installation,
                    event_type='status_change',
                    description=f'تم تغيير الحالة من {valid_statuses.get(old_status, old_status)} إلى {valid_statuses.get(new_status, new_status)}',
                    user=request.user,
                    metadata={
                        'old_status': old_status,
                        'new_status': new_status,
                        'changed_by': request.user.username
                    }
                )
            except Exception as e:
                # لا نريد أن يفشل التحديث بسبب سجل الحدث
                print(f"خطأ في إنشاء سجل الحدث: {e}")
            
            # إرسال رسالة نجاح
            messages.success(request, f'تم تحديث حالة التركيب بنجاح إلى: {valid_statuses.get(new_status, new_status)}')
            
            return JsonResponse({
                'success': True,
                'message': f'تم تحديث الحالة بنجاح إلى: {valid_statuses.get(new_status, new_status)}',
                'new_status': new_status,
                'new_status_display': valid_statuses.get(new_status, new_status)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'طريقة الطلب غير صحيحة'
            })
            
    except InstallationSchedule.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'التركيب غير موجود'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'حدث خطأ أثناء تحديث الحالة: {str(e)}'
        })


# API Views
@csrf_exempt
@require_http_methods(["POST"])
def receive_completed_order(request):
    # تعطيل الجدولة التلقائية نهائياً
    return JsonResponse({
        'success': False,
        'error': 'يرجى جدولة التركيب يدوياً من شاشة الجدولة فقط. لا يسمح بالجدولة التلقائية.'
    }, status=400)


# API Views للطلبات
@login_required
def orders_modal(request):
    """عرض الطلبات في modal"""
    order_type = request.GET.get('type', 'total')

    if order_type == 'total':
        # إجمالي طلبات التركيب فقط
        orders = Order.objects.filter(
            selected_types__icontains='installation'
        ).select_related('customer', 'branch', 'salesperson')
    elif order_type == 'ready':
        # جلب الطلبات العادية الجاهزة للتركيب - فقط طلبات التركيب
        regular_orders = Order.objects.filter(
            selected_types__icontains='installation',
            order_status__in=['ready_install', 'completed'],
            installationschedule__isnull=True
        ).select_related('customer', 'branch', 'salesperson')

        # جلب أوامر التصنيع الجاهزة للتركيب (فقط من نوع تركيب)
        from manufacturing.models import ManufacturingOrder
        manufacturing_orders = ManufacturingOrder.objects.filter(
            status__in=['ready_install', 'delivered'],  # إضافة حالة "تم التسليم"
            order__selected_types__icontains='installation',
            order__installationschedule__isnull=True  # التأكد من عدم وجود جدولة
        ).select_related('order', 'order__customer', 'order__branch', 'order__salesperson')

        # دمج الطلبات مع تمييز أوامر التصنيع (بدون تكرار)
        orders = list(regular_orders)
        existing_order_ids = set(order.id for order in orders)
        
        for mfg_order in manufacturing_orders:
            # إضافة أمر التصنيع فقط إذا لم يكن موجوداً بالفعل
            if mfg_order.order.id not in existing_order_ids:
                # إضافة أمر التصنيع للطلب (سيتم التعامل معه في القالب)
                mfg_order.order.manufacturing_order = mfg_order
                orders.append(mfg_order.order)
                existing_order_ids.add(mfg_order.order.id)
    elif order_type == 'manufacturing':
        # عرض جميع أوامر التصنيع قيد التنفيذ أو قيد الانتظار (وليس فقط الأحدث لكل طلب)
        from manufacturing.models import ManufacturingOrder
        manufacturing_orders = ManufacturingOrder.objects.filter(
            order__selected_types__icontains='installation',
            status__in=['pending', 'in_progress']
        ).select_related('order', 'order__customer', 'order__branch', 'order__salesperson').order_by('-created_at')
        orders = []
        for mfg in manufacturing_orders:
            mfg.order.manufacturing_order = mfg  # ربط أمر التصنيع بالطلب لسهولة العرض في القالب
            orders.append(mfg.order)
    elif order_type == 'completed':
        # التركيبات المكتملة من قسم التركيبات فقط
        schedules = InstallationSchedule.objects.filter(
            status='completed'
        ).select_related('order', 'order__customer', 'order__branch', 'order__salesperson')
        orders = [schedule.order for schedule in schedules]
    elif order_type == 'debt':
        # الطلبات مع المديونية - فقط طلبات التركيب
        orders = Order.objects.filter(
            selected_types__icontains='installation',
            order_status__in=['ready_install', 'completed'],
            installationschedule__isnull=True
        ).filter(
            total_amount__gt=F('paid_amount')
        ).select_related('customer', 'branch', 'salesperson')
    elif order_type == 'modifications':
        # جلب التعديلات مع الطلبات المرتبطة - فقط طلبات التركيب
        modifications = ModificationRequest.objects.filter(
            installation__order__selected_types__icontains='installation'
        ).select_related(
            'installation', 'installation__order', 'installation__order__customer',
            'installation__order__branch', 'installation__order__salesperson'
        ).order_by('-created_at')
        orders = [mod.installation.order for mod in modifications]
    elif order_type == 'scheduled':
        # التركيبات المجدولة
        schedules = InstallationSchedule.objects.filter(
            status='scheduled'
        ).select_related('order', 'order__customer', 'order__branch', 'order__salesperson')
        orders = [schedule.order for schedule in schedules]
    elif order_type == 'in_installation':
        # التركيبات قيد التركيب
        schedules = InstallationSchedule.objects.filter(
            status='in_installation'
        ).select_related('order', 'order__customer', 'order__branch', 'order__salesperson')
        orders = [schedule.order for schedule in schedules]
    elif order_type == 'needs_scheduling':
        # التركيبات بحاجة جدولة
        schedules = InstallationSchedule.objects.filter(
            status='needs_scheduling'
        ).select_related('order', 'order__customer', 'order__branch', 'order__salesperson')
        orders = [schedule.order for schedule in schedules]
    elif order_type == 'delivered_manufacturing':
        # أوامر التصنيع التي تم تسليمها - فقط طلبات التركيب
        from manufacturing.models import ManufacturingOrder
        manufacturing_orders = ManufacturingOrder.objects.filter(
            status='delivered',
            order__selected_types__icontains='installation'
        ).select_related('order', 'order__customer', 'order__branch', 'order__salesperson')
        
        orders = []
        for mfg_order in manufacturing_orders:
            # إضافة أمر التصنيع للطلب (سيتم التعامل معه في القالب)
            mfg_order.order.manufacturing_order = mfg_order
            orders.append(mfg_order.order)
    else:
        orders = Order.objects.none()

    context = {
        'orders': orders,
        'manufacturing_orders': [],  # سيتم إضافة أوامر التصنيع إذا لزم الأمر
        'currency_symbol': 'ج.م',
        'order_type': order_type,  # إضافة نوع الطلب للسياق
        'debug_info': {
            'order_type': order_type,
            'orders_count': len(orders),
            'manufacturing_orders_count': 0
        }
    }

    return render(request, 'installations/orders_modal.html', context)


@login_required
def schedule_from_needs_scheduling(request, installation_id):
    """جدولة تركيب من قائمة بحاجة جدولة"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    # التحقق من أن التركيب بحاجة جدولة
    if installation.status != "needs_scheduling":
        messages.warning(request, "هذا التركيب لا يحتاج جدولة أو تم جدولته بالفعل")
        return redirect("installations:dashboard")

    if request.method == "POST":
        form = InstallationScheduleForm(request.POST, instance=installation)
        if form.is_valid():
            installation = form.save(commit=False)
            installation.status = "scheduled"  # تغيير الحالة إلى مجدول
            installation.save()
            
            # إنشاء سجل حدث
            from .models import InstallationEventLog
            InstallationEventLog.objects.create(
                installation=installation,
                event_type="schedule_change",
                description=f"تم جدولة التركيب للتاريخ {installation.scheduled_date} في الساعة {installation.scheduled_time}",
                user=request.user,
                metadata={
                    "scheduled_date": str(installation.scheduled_date),
                    "scheduled_time": str(installation.scheduled_time),
                    "team": installation.team.name if installation.team else None
                }
            )
            
            messages.success(request, _("تم جدولة التركيب بنجاح"))
            return redirect("installations:dashboard")
    else:
        # ��عيين قيم افتراضية للجدولة
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        default_time = timezone.datetime.strptime("09:00", "%H:%M").time()
        
        form = InstallationScheduleForm(instance=installation, initial={
            "scheduled_date": tomorrow,
            "scheduled_time": default_time
        })

    context = {
        "form": form,
        "installation": installation,
        "title": "جدولة التركيب"
    }

    return render(request, "installations/schedule_installation.html", context)


# باقي الدوال المطلوبة للنظام
@login_required
def create_modification_request(request, installation_id):
    """إنشاء طلب تعديل"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)

    if request.method == 'POST':
        form = ModificationRequestForm(request.POST)
        if form.is_valid():
            modification_request = form.save(commit=False)
            modification_request.installation = installation
            modification_request.customer = installation.order.customer
            modification_request.save()

            # تحديث حالة التركيب إلى يحتاج تعديل
            installation.status = 'modification_required'
            installation.save()

            messages.success(request, 'تم إنشاء طلب التعديل بنجاح')
            return redirect('installations:modification_detail', modification_id=modification_request.id)
    else:
        form = ModificationRequestForm()

    context = {
        'form': form,
        'installation': installation,
        'title': 'إنشاء طلب تعديل'
    }

    return render(request, 'installations/create_modification.html', context)


@login_required
def modification_detail(request, modification_id):
    """تفاصيل طلب التعديل"""
    modification_request = get_object_or_404(ModificationRequest, id=modification_id)
    images = ModificationImage.objects.filter(modification=modification_request)

    context = {
        'modification_request': modification_request,
        'images': images,
        'title': 'تفاصيل طلب التعديل'
    }

    return render(request, 'installations/modification_detail.html', context)


@login_required
def upload_modification_images(request, modification_id):
    """رفع صور التعديل"""
    modification_request = get_object_or_404(ModificationRequest, id=modification_id)

    if request.method == 'POST':
        form = ModificationImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.modification = modification_request
            image.save()
            messages.success(request, 'تم رفع الصورة بنجاح')
            return redirect('installations:modification_detail', modification_id=modification_request.id)
    else:
        form = ModificationImageForm()

    context = {
        'form': form,
        'modification_request': modification_request,
        'title': 'رفع صور التعديل'
    }

    return render(request, 'installations/upload_images.html', context)


@login_required
def create_manufacturing_order(request, modification_id):
    """إنشاء أمر تصنيع للتعديل"""
    modification_request = get_object_or_404(ModificationRequest, id=modification_id)

    if request.method == 'POST':
        form = ManufacturingOrderForm(request.POST)
        if form.is_valid():
            manufacturing_order = form.save(commit=False)
            manufacturing_order.modification_request = modification_request
            manufacturing_order.order_type = 'modification'
            manufacturing_order.save()

            # تحديث حالة طلب التعديل
            modification_request.installation.status = 'modification_in_progress'
            modification_request.installation.save()

            messages.success(request, 'تم إنشاء أمر التصنيع بنجاح')
            return redirect('installations:manufacturing_order_detail', order_id=manufacturing_order.id)
    else:
        form = ManufacturingOrderForm()

    context = {
        'form': form,
        'modification_request': modification_request,
        'title': 'إنشاء أمر تصنيع للتعديل'
    }

    return render(request, 'installations/create_manufacturing_order.html', context)


@login_required
def manufacturing_order_detail(request, order_id):
    """تفاصيل أمر التصنيع"""
    manufacturing_order = get_object_or_404(ManufacturingOrder, id=order_id)

    context = {
        'manufacturing_order': manufacturing_order,
        'title': 'تفاصيل أمر التصنيع'
    }

    return render(request, 'installations/manufacturing_order_detail.html', context)


@login_required
def complete_manufacturing_order(request, order_id):
    """إكمال أمر التصنيع"""
    manufacturing_order = get_object_or_404(ManufacturingOrder, id=order_id)

    if request.method == 'POST':
        form = ModificationReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.manufacturing_order = manufacturing_order
            report.modification_request = manufacturing_order.modification_request
            report.created_by = request.user
            report.save()

            # تحديث حالة أمر التصنيع
            manufacturing_order.status = 'completed'
            manufacturing_order.actual_completion_date = timezone.now()
            manufacturing_order.save()

            # تحديث حالة التركيب
            installation = manufacturing_order.modification_request.installation
            installation.status = 'modification_completed'
            installation.save()

            messages.success(request, 'تم إكمال أمر التصنيع بنجاح')
            return redirect('installations:manufacturing_order_detail', order_id=manufacturing_order.id)
    else:
        form = ModificationReportForm()

    context = {
        'form': form,
        'manufacturing_order': manufacturing_order,
        'title': 'إكمال أمر التصنيع'
    }

    return render(request, 'installations/complete_manufacturing_order.html', context)


@login_required
def modification_requests_list(request):
    """قائمة طلبات التعديل"""
    modifications = ModificationRequest.objects.select_related(
        'installation', 'installation__order', 'customer'
    ).order_by('-created_at')

    # فلترة
    status_filter = request.GET.get('status')
    if status_filter:
        modifications = modifications.filter(installation__status=status_filter)

    priority_filter = request.GET.get('priority')
    if priority_filter:
        modifications = modifications.filter(priority=priority_filter)

    # ترقيم الصفحات
    paginator = Paginator(modifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'title': 'طلبات التعديل'
    }

    return render(request, 'installations/modification_requests_list.html', context)


@login_required
def manufacturing_orders_list(request):
    """قائمة أوامر التصنيع للتعديلات"""
    orders = ManufacturingOrder.objects.select_related(
        'modification_request', 'modification_request__installation',
        'modification_request__installation__order', 'assigned_to'
    ).filter(order_type='modification').order_by('-created_at')

    # فلترة
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)

    # ترقيم الصفحات
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'title': 'أوامر التصنيع للتعديلات'
    }

    return render(request, 'installations/manufacturing_orders_list.html', context)


@login_required
@login_required
def check_debt_before_schedule(request, order_id):
    """التحقق من المديونية قبل الجدولة"""
    order = get_object_or_404(Order, id=order_id)
    
    # الحصول على رمز العملة من إعدادات النظام
    from accounts.models import SystemSettings
    system_settings = SystemSettings.objects.first()
    currency_symbol = system_settings.currency_symbol if system_settings else 'ج.م'
    
    # حساب المديونية
    debt_amount = order.total_amount - order.paid_amount
    
    response_data = {
        'has_debt': debt_amount > 0,
        'debt_amount': float(debt_amount) if debt_amount > 0 else 0,
        'customer_name': order.customer.name,
        'order_number': order.order_number,
        'total_amount': float(order.total_amount),
        'paid_amount': float(order.paid_amount),
        'currency_symbol': currency_symbol,
    }
    
    return JsonResponse(response_data)


@login_required
def quick_schedule_installation(request, order_id):
    """جدولة سريعة للتركيب من الطلب"""

    # الحصول على الطلب من قاعدة البيانات
    order = get_object_or_404(Order, id=order_id)

    # التحقق من عدم وجود جدولة سابقة
    if InstallationSchedule.objects.filter(order=order).exists():
        messages.warning(request, _('يوجد جدولة تركيب سابقة لهذا الطلب'))
        return redirect('installations:dashboard')

    # التحقق من أن الطلب جاهز للتركيب
    is_ready_for_installation = False
    
    # التحقق من حالة الطلب العادية
    if order.order_status in ['ready_install', 'completed', 'delivered']:
        is_ready_for_installation = True
    
    # التحقق من أمر التصنيع إذا كان موجوداً
    try:
        from manufacturing.models import ManufacturingOrder
        manufacturing_order = ManufacturingOrder.objects.filter(order=order).first()
        if manufacturing_order and manufacturing_order.status in ['ready_install', 'delivered']:
            is_ready_for_installation = True
    except:
        pass
    
    if not is_ready_for_installation:
        messages.error(request, 'لا يمكن جدولة التركيب. الطلب ليس جاهزاً للتركيب بعد. يجب أن يكون الطلب في حالة "جاهز للتركيب" أو "تم التسليم" في المصنع.')
        return redirect('installations:dashboard')

    if request.method == 'POST':
        form = QuickScheduleForm(request.POST, order=order)
        if form.is_valid():
            installation = form.save(commit=False)
            installation.order = order
            installation.status = 'scheduled'
            installation.save()
            
            # تحديث معلومات العميل إذا تم تعديل العنوان
            update_customer_address = form.cleaned_data.get('update_customer_address')
            if update_customer_address and order.customer:
                try:
                    old_address = order.customer.address
                    order.customer.address = update_customer_address
                    order.customer.save(update_fields=['address'])
                    
                    # إضافة ملاحظة في التركيب عن تحديث العنوان
                    address_note = f"\n--- تحديث العنوان ---\n"
                    address_note += f"العنوان السابق: {old_address or 'غير محدد'}\n"
                    address_note += f"العنوان الجديد: {update_customer_address}\n"
                    address_note += f"تم التحديث بواسطة: {request.user.username}\n"
                    address_note += f"تاريخ التحديث: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
                    address_note += f"--- نهاية تحديث العنوان ---\n"
                    
                    if installation.notes:
                        installation.notes += address_note
                    else:
                        installation.notes = address_note
                    
                    # تحديث عنوان التركيب أيضاً
                    if form.cleaned_data.get('location_address'):
                        installation.location_address = form.cleaned_data['location_address']
                    else:
                        installation.location_address = update_customer_address
                    
                    # تحديث عنوان المعاينات المرتبطة بنفس العميل
                    try:
                        from inspections.models import Inspection
                        inspections = Inspection.objects.filter(customer=order.customer)
                        for inspection in inspections:
                            inspection_note = f"\n--- تحديث العنوان من قسم التركيبات ---\n"
                            inspection_note += f"العنوان الجديد: {update_customer_address}\n"
                            inspection_note += f"تم التحديث بواسطة: {request.user.username}\n"
                            inspection_note += f"تاريخ التحديث: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
                            inspection_note += f"--- نهاية تحديث العنوان ---\n"
                            
                            if inspection.notes:
                                inspection.notes += inspection_note
                            else:
                                inspection.notes = inspection_note
                            inspection.save(update_fields=['notes'])
                    except Exception as inspection_error:
                        print(f"خطأ في تحديث عنوان المعاينات: {inspection_error}")
                    
                    messages.success(request, 'تم تحديث عنوان العميل بنجاح في التركيبات والمعاينات')
                except Exception as e:
                    messages.warning(request, f'تعذر تحديث عنوان العميل: {str(e)}')
            elif form.cleaned_data.get('location_address'):
                # استخراج نوع المكان من العنوان إذا كان موجوداً
                address_text = form.cleaned_data['location_address']
                location_type = form.cleaned_data.get('location_type')
                
                # تحديث عنوان التركيب فقط
                installation.location_address = address_text.split('\nنوع المكان:')[0].strip()
                if location_type:
                    installation.location_type = location_type
            
            messages.success(request, _('تم جدولة التركيب بنجاح'))
            return redirect('installations:dashboard')
    else:
        # تعيين قيم افتراضية
        tomorrow = timezone.now().date() + timezone.timedelta(days=1)
        default_time = timezone.datetime.strptime('09:00', '%H:%M').time()
        form = QuickScheduleForm(order=order, initial={
            'scheduled_date': tomorrow,
            'scheduled_time': default_time
        })

    context = {
        'form': form,
        'order': order,
    }

    return render(request, 'installations/quick_schedule_installation.html', context)


@login_required
def daily_schedule(request):
    """الجدول اليومي المحسن"""
    if request.method == 'POST':
        form = DailyScheduleForm(request.POST)
    else:
        form = DailyScheduleForm()

    installations = []
    if form.is_valid():
        date = form.cleaned_data.get('date')
        team = form.cleaned_data.get('team')
        status = form.cleaned_data.get('status')
        salesperson = form.cleaned_data.get('salesperson')
        branch = form.cleaned_data.get('branch')
        search = form.cleaned_data.get('search')

        # فلترة التركيبات
        installations = InstallationSchedule.objects.filter(
            scheduled_date=date
        ).select_related(
            'order', 'order__customer', 'order__salesperson', 'order__branch', 'team'
        ).prefetch_related('team__technicians', 'team__driver')

        # فلترة حسب الحالة
        if status:
            installations = installations.filter(status=status)
        else:
            # عرض التركيبات المجدولة وقيد التركيب وقيد التنفيذ افتراضياً
            installations = installations.filter(
                status__in=['scheduled', 'in_installation', 'in_progress']
            )

        # فلترة حسب الفريق
        if team:
            installations = installations.filter(team=team)

        # فلترة حسب البائع
        if salesperson:
            installations = installations.filter(order__salesperson=salesperson)

        # فلترة حسب الفرع
        if branch:
            installations = installations.filter(order__branch=branch)

        # بحث شامل متعدد الحقول
        if search:
            installations = installations.filter(
                Q(order__order_number__icontains=search) |
                Q(order__customer__name__icontains=search) |
                Q(order__customer__phone__icontains=search) |
                Q(order__contract_number__icontains=search) |
                Q(order__customer__phone2__icontains=search) |
                Q(order__customer__email__icontains=search) |
                Q(order__salesperson__name__icontains=search) |
                Q(team__name__icontains=search) |
                Q(order__branch__name__icontains=search) |
                Q(notes__icontains=search) |
                Q(status__icontains=search) |
                Q(scheduled_date__icontains=search) |
                Q(completion_date__icontains=search)
            )
        installations = installations.order_by('scheduled_time')

    context = {
        'form': form,
        'installations': installations,
    }

    return render(request, 'installations/daily_schedule.html', context)


@login_required
def print_daily_schedule(request):
    """طباعة الجدول اليومي المحسن"""
    date = request.GET.get('date', timezone.now().date())
    team_id = request.GET.get('team')
    status = request.GET.get('status')
    salesperson_id = request.GET.get('salesperson')
    branch_id = request.GET.get('branch')
    search = request.GET.get('search')

    installations = InstallationSchedule.objects.filter(
        scheduled_date=date
    ).select_related(
        'order', 'order__customer', 'order__salesperson', 'order__branch', 'team'
    ).prefetch_related('team__technicians', 'team__driver')

    # فلترة حسب الحالة
    if status:
        installations = installations.filter(status=status)
    else:
        # عرض التركيبات المجدولة وقيد التركيب وقيد التنفيذ افتراضياً
        installations = installations.filter(
            status__in=['scheduled', 'in_installation', 'in_progress']
        )

    # فلترة حسب الفريق
    if team_id:
        installations = installations.filter(team_id=team_id)

    # فلترة حسب البائع
    if salesperson_id:
        installations = installations.filter(order__salesperson_id=salesperson_id)

    # فلترة حسب الفرع
    if branch_id:
        installations = installations.filter(order__branch_id=branch_id)

    # البحث
    if search:
        installations = installations.filter(
            models.Q(order__order_number__icontains=search) |
            models.Q(order__customer__name__icontains=search) |
            models.Q(order__customer__phone__icontains=search)
        )

    installations = installations.order_by('scheduled_time')

    context = {
        'installations': installations,
        'date': date,
        'filters': {
            'team_id': team_id,
            'status': status,
            'salesperson_id': salesperson_id,
            'branch_id': branch_id,
            'search': search
        }
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
    """إكمال التركيب مع تحديث التاريخ الفعلي"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)

    if request.method == 'POST':
        # تحديث الحالة والتاريخ الفعلي للإكمال
        installation.status = 'completed'
        installation.completion_date = timezone.now()
        
        # تحديث تاريخ التركيب الفعلي إلى تاريخ اليوم
        installation.installation_date = timezone.now().date()
        
        installation.save()

        # إنشاء أرشيف
        InstallationArchive.objects.create(
            installation=installation,
            archived_by=request.user
        )

        # إنشاء سجل حدث
        from .models import InstallationEventLog
        InstallationEventLog.objects.create(
            installation=installation,
            event_type='completion',
            description=f'تم إكمال التركيب في {installation.installation_date}',
            user=request.user,
            metadata={
                'scheduled_date': str(installation.scheduled_date),
                'actual_completion_date': str(installation.installation_date),
                'completion_time': str(installation.completion_date)
            }
        )

        messages.success(request, _('تم إكمال التركيب بنجاح وتحديث التاريخ الفعلي'))
        return redirect('installations:installation_detail', installation_id=installation.id)

    context = {
        'installation': installation,
    }

    return render(request, 'installations/complete_installation.html', context)


@login_required
def team_management(request):
    """إدارة الفرق"""
    teams = InstallationTeam.objects.all().prefetch_related('technicians', 'driver')
    
    # جلب الفنيين المرتبطين بفرق التركيب فقط (من قسم التركيبات)
    technicians_in_teams = []
    for team in teams:
        installation_technicians = team.technicians.filter(department='installation')
        technicians_in_teams.extend(installation_technicians)
    
    # إزالة التكرار
    technicians_in_teams = list(set(technicians_in_teams))
    
    # جلب فنيي التركيبات النشطين غير المرتبطين بأي فريق (متاحين للإضافة)
    technicians_in_team_ids = [tech.id for tech in technicians_in_teams]
    unassigned_technicians = Technician.objects.filter(
        is_active=True,
        department='installation'
    ).exclude(id__in=technicians_in_team_ids)
    
    drivers = Driver.objects.filter(is_active=True)

    context = {
        'teams': teams,
        'technicians': technicians_in_teams,
        'unassigned_technicians': unassigned_technicians,
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
    """إضافة فني لقسم التركيبات"""
    if request.method == 'POST':
        form = TechnicianForm(request.POST)
        if form.is_valid():
            try:
                technician = form.save(commit=False)
                # تعيين القسم للتركيبات افتراضياً
                technician.department = 'installation'
                technician.save()
                messages.success(request, 'تم إضافة الفني لقسم التركيبات بنجاح')
                return redirect('installations:team_management')
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء حفظ الفني: {str(e)}')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
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
            try:
                form.save()
                messages.success(request, 'تم إضافة السائق بنجاح')
                return redirect('installations:team_management')
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء حفظ السائق: {str(e)}')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
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


@login_required
def installation_stats_api(request):
    """API لإحصائيات التركيبات"""
    total = InstallationSchedule.objects.count()
    completed = InstallationSchedule.objects.filter(status='completed').count()
    pending = InstallationSchedule.objects.filter(status='pending').count()
    in_progress = InstallationSchedule.objects.filter(status='in_progress').count()

    return JsonResponse({
        'total': total,
        'completed': completed,
        'pending': pending,
        'in_progress': in_progress
    })


# إدارة مديونية العملاء
@login_required
def manage_customer_debt(request, order_id):
    """إدارة مديونية العميل"""
    order = get_object_or_404(Order, id=order_id)
    debt, created = CustomerDebt.objects.get_or_create(
        order=order,
        defaults={
            'customer': order.customer,
            'debt_amount': order.remaining_amount
        }
    )

    if request.method == 'POST':
        form = CustomerDebtForm(request.POST, instance=debt)
        if form.is_valid():
            debt = form.save()
            messages.success(request, 'تم تحديث مديونية العميل بنجاح')
            return redirect('installations:dashboard')
    else:
        form = CustomerDebtForm(instance=debt)

    context = {
        'form': form,
        'order': order,
        'debt': debt,
        'title': 'إدارة مديونية العميل'
    }

    return render(request, 'installations/manage_debt.html', context)


@login_required
def pay_debt(request, debt_id):
    """دفع المديونية"""
    debt = get_object_or_404(CustomerDebt, id=debt_id)

    if request.method == 'POST':
        form = CustomerDebtForm(request.POST, instance=debt)
        if form.is_valid():
            debt = form.save()
            if debt.is_paid:
                debt.payment_date = timezone.now()
                debt.save()
                messages.success(request, 'تم تسجيل الدفع بنجاح')
            return redirect('installations:dashboard')
    else:
        form = CustomerDebtForm(instance=debt)

    context = {
        'form': form,
        'debt': debt,
        'title': 'دفع المديونية'
    }

    return render(request, 'installations/pay_debt.html', context)


@login_required
def debt_list(request):
    """قائمة مديونيات العملاء"""
    debts = CustomerDebt.objects.select_related('customer', 'order').order_by('-created_at')

    # تطبيق الفلاتر
    status_filter = request.GET.get('status')
    if status_filter == 'paid':
        debts = debts.filter(is_paid=True)
    elif status_filter == 'unpaid':
        debts = debts.filter(is_paid=False)

    # ترقيم الصفحات
    paginator = Paginator(debts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'debts': page_obj,
    }

    return render(request, 'installations/debt_list.html', context)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def schedule_manufacturing_order(request, manufacturing_order_id):
    """جدولة أمر التصنيع للتركيب - يدوية"""
    try:
        from manufacturing.models import ManufacturingOrder
        manufacturing_order = get_object_or_404(ManufacturingOrder, id=manufacturing_order_id)

        # التحقق من أن أمر التصنيع جاهز للتركيب
        if manufacturing_order.status != 'ready_install':
            return JsonResponse({
                'success': False,
                'message': 'أمر التصنيع ليس جاهزاً للتركيب'
            })

        # التحقق من عدم وجود جدولة تركيب موجودة
        if InstallationSchedule.objects.filter(order=manufacturing_order.order).exists():
            return JsonResponse({
                'success': False,
                'message': 'يوجد جدولة تركيب موجودة بالفعل لهذا الطلب'
            })

        # إنشاء جدولة تركيب جديدة بحالة "needs_scheduling" بدلاً من "scheduled"
        installation_schedule = InstallationSchedule.objects.create(
            order=manufacturing_order.order,
            status='needs_scheduling',  # بحاجة جدولة يدوية
            notes=f'تم إنشاء جدولة تركيب من أمر التصنيع #{manufacturing_order.id} - يحتاج جدولة يدوية'
        )

        # تحديث حالة أمر التصنيع إلى "completed"
        manufacturing_order.status = 'completed'
        manufacturing_order.save()

        # إنشاء سجل حدث
        from .models import InstallationEventLog
        InstallationEventLog.objects.create(
            installation=installation_schedule,
            event_type='schedule_change',
            description=f'تم إنشاء جدولة تركيب من أمر التصنيع #{manufacturing_order.id} - يحتاج جدولة يدوية',
            user=request.user,
            metadata={
                'manufacturing_order_id': manufacturing_order.id,
                'action': 'manual_scheduling_required'
            }
        )

        return JsonResponse({
            'success': True,
            'message': f'تم إنشاء جدولة تركيب بنجاح - يرجى جدولتها يدوياً'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ أثناء إنشاء الجدولة: {str(e)}'
        })


@login_required
@permission_required('installations.change_installationschedule', raise_exception=True)
def edit_schedule(request, installation_id):
    """تعديل جدولة التركيب"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)

    if request.method == 'POST':
        form = InstallationScheduleForm(request.POST, instance=installation)
        if form.is_valid():
            old_date = installation.scheduled_date
            old_time = installation.scheduled_time
            old_team = installation.team
            
            installation = form.save()
            
            # إنشاء سجل حدث للتعديل
            from .models import InstallationEventLog
            InstallationEventLog.objects.create(
                installation=installation,
                event_type='schedule_change',
                description=f'تم تعديل الجدولة من {old_date} {old_time} إلى {installation.scheduled_date} {installation.scheduled_time}',
                user=request.user,
                metadata={
                    'old_date': str(old_date) if old_date else None,
                    'old_time': str(old_time) if old_time else None,
                    'new_date': str(installation.scheduled_date),
                    'new_time': str(installation.scheduled_time),
                    'old_team': old_team.name if old_team else None,
                    'new_team': installation.team.name if installation.team else None
                }
            )
            
            messages.success(request, 'تم تعديل جدولة التركيب بنجاح')
            return redirect('installations:installation_detail', installation_id=installation.id)
    else:
        form = InstallationScheduleForm(instance=installation)

    context = {
        'form': form,
        'installation': installation,
        'title': 'تعديل جدولة التركيب'
    }

    return render(request, 'installations/edit_schedule.html', context)


@login_required
def modification_error_analysis(request):
    """تحليل أخطاء التعديلات"""
    error_analyses = ModificationErrorAnalysis.objects.select_related(
        'modification_request', 'modification_request__installation',
        'modification_request__installation__order', 'error_type', 'analyzed_by'
    ).order_by('-created_at')

    # فلترة حسب نوع الخطأ
    error_type_filter = request.GET.get('error_type')
    if error_type_filter:
        error_analyses = error_analyses.filter(error_type_id=error_type_filter)

    # فلترة حسب الشدة
    severity_filter = request.GET.get('severity')
    if severity_filter:
        error_analyses = error_analyses.filter(severity=severity_filter)

    # إحصائيات الأخطاء
    error_stats = {
        'total_errors': error_analyses.count(),
        'critical_errors': error_analyses.filter(severity='critical').count(),
        'high_errors': error_analyses.filter(severity='high').count(),
        'medium_errors': error_analyses.filter(severity='medium').count(),
        'low_errors': error_analyses.filter(severity='low').count(),
    }

    # أنواع الأخطاء الأكثر شيوعاً
    common_error_types = ModificationErrorType.objects.annotate(
        error_count=Count('modificationerroranalysis')
    ).order_by('-error_count')[:5]

    # ترقيم الصفحات
    paginator = Paginator(error_analyses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # تحضير بيانات أنواع الأخطاء للرسم البياني
    error_types_for_chart = [
        (error_type.name, error_type.name)
        for error_type in ModificationErrorType.objects.all()
    ]

    context = {
        'page_obj': page_obj,
        'error_analyses': page_obj,
        'error_stats': error_stats,
        'common_error_types': common_error_types,
        'error_types': error_types_for_chart,
        'title': 'تحليل أخطاء التعديلات'
    }

    return render(request, 'installations/error_analysis.html', context)


@login_required
def add_error_analysis(request, modification_id):
    """إضافة تحليل خطأ للتعديل"""
    modification_request = get_object_or_404(ModificationRequest, id=modification_id)

    if request.method == 'POST':
        form = ModificationErrorAnalysisForm(request.POST, request.FILES)
        if form.is_valid():
            error_analysis = form.save(commit=False)
            error_analysis.modification_request = modification_request
            error_analysis.analyzed_by = request.user
            error_analysis.save()
            
            messages.success(request, 'تم إضافة تحليل الخطأ بنجاح')
            return redirect('installations:modification_error_analysis')
    else:
        form = ModificationErrorAnalysisForm()

    context = {
        'form': form,
        'modification_request': modification_request,
        'title': 'إضافة تحليل خطأ'
    }

    return render(request, 'installations/add_error_analysis.html', context)


@login_required
def installation_analytics(request):
    """تحليل التركيبات الشهري"""
    from django.db.models import Count, Avg
    from django.utils import timezone
    import calendar

    # الحصول على الشهر والسنة من الطلب
    current_date = timezone.now()
    year = int(request.GET.get('year', current_date.year))
    month = int(request.GET.get('month', current_date.month))

    # إحصائيات الشهر المحدد
    start_date = timezone.datetime(year, month, 1).date()
    if month == 12:
        end_date = timezone.datetime(year + 1, 1, 1).date()
    else:
        end_date = timezone.datetime(year, month + 1, 1).date()

    # إحصائيات التركيبات للشهر
    monthly_installations = InstallationSchedule.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lt=end_date
    )

    # إحصائيات حسب الح��لة
    status_stats = monthly_installations.values('status').annotate(
        count=Count('id')
    ).order_by('-count')

    # إحصائيات حسب الفريق
    team_stats = monthly_installations.filter(team__isnull=False).values(
        'team__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')

    # إحصائيات يومية للشهر
    daily_stats = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        day_date = timezone.datetime(year, month, day).date()
        day_installations = monthly_installations.filter(
            created_at__date=day_date
        ).count()
        daily_stats.append({
            'date': day_date,
            'count': day_installations
        })

    # إحصائيات التعديلات
    modification_stats = ModificationRequest.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lt=end_date
    ).values('modification_type').annotate(
        count=Count('id')
    ).order_by('-count')

    # متوسط وقت الإكمال (بالأيام)
    completed_installations = monthly_installations.filter(
        status='completed',
        completion_date__isnull=False
    )
    
    # حساب متوسط الوقت بالطريقة اليدوية
    avg_completion_days = None
    if completed_installations.exists():
        total_days = 0
        count = 0
        for installation in completed_installations:
            if installation.scheduled_date and installation.completion_date:
                days_diff = (installation.completion_date.date() - installation.scheduled_date).days
                total_days += days_diff
                count += 1
        
        if count > 0:
            avg_completion_days = total_days / count

    # قوائم السنوات والشهور للفلترة
    years = list(range(2020, 2026))
    months = list(range(1, 13))
    
    context = {
        'year': year,
        'month': month,
        'years': years,
        'months': months,
        'month_name': calendar.month_name[month],
        'monthly_installations': monthly_installations,
        'status_stats': status_stats,
        'team_stats': team_stats,
        'daily_stats': daily_stats,
        'modification_stats': modification_stats,
        'avg_completion_days': avg_completion_days,
        'total_installations': monthly_installations.count(),
        'completed_installations': monthly_installations.filter(status='completed').count(),
        'title': f'تحليل التركيبات - {calendar.month_name[month]} {year}'
    }

    return render(request, 'installations/installation_analytics.html', context)


@login_required
def installation_event_logs(request):
    """سجل أحداث التركيبات"""
    from .models import InstallationEventLog
    
    # تحسين الاستعلام لضمان جلب جميع البيانات المطلوبة
    event_logs = InstallationEventLog.objects.select_related(
        'installation', 
        'installation__order', 
        'installation__order__customer', 
        'user'
    ).prefetch_related(
        'installation__order__customer'
    ).order_by('-created_at')

    # فلترة حسب نوع الحدث
    event_type_filter = request.GET.get('event_type')
    if event_type_filter:
        event_logs = event_logs.filter(event_type=event_type_filter)

    # فلترة حسب التركيب
    installation_filter = request.GET.get('installation')
    if installation_filter:
        event_logs = event_logs.filter(installation_id=installation_filter)

    # فلترة حسب التاريخ
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        event_logs = event_logs.filter(created_at__date__gte=date_from)
    if date_to:
        event_logs = event_logs.filter(created_at__date__lte=date_to)

    # ترقيم الصفحات
    paginator = Paginator(event_logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # أنواع الأحداث المتاحة
    event_types = InstallationEventLog.objects.values_list(
        'event_type', flat=True
    ).distinct()

    # إضافة معلومات تشخيصية للتصحيح
    debug_info = {
        'total_logs': event_logs.count(),
        'page_size': 50,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
    }

    context = {
        'page_obj': page_obj,
        'event_logs': page_obj,
        'event_types': event_types,
        'title': 'سجل أحداث التركيبات',
        'debug_info': debug_info,  # للتشخيص فقط
    }

    return render(request, 'installations/event_logs.html', context)


@login_required
def installation_in_progress_list(request):
    """قائمة التركيبات قيد التنفيذ"""
    installations = InstallationSchedule.objects.filter(
        status__in=['in_progress', 'in_installation']
    ).select_related(
        'order', 'order__customer', 'team'
    ).order_by('scheduled_date', 'scheduled_time')

    # فلترة حسب الفريق
    team_filter = request.GET.get('team')
    if team_filter:
        installations = installations.filter(team_id=team_filter)

    # فلترة حسب التاريخ
    date_filter = request.GET.get('date')
    if date_filter:
        installations = installations.filter(scheduled_date=date_filter)

    # إحصائيات سريعة
    stats = {
        'total_in_progress': installations.count(),
        'today_in_progress': installations.filter(
            scheduled_date=timezone.now().date()
        ).count(),
        'overdue': installations.filter(
            scheduled_date__lt=timezone.now().date()
        ).count()
    }

    context = {
        'installations': installations,
        'stats': stats,
        'teams': InstallationTeam.objects.filter(is_active=True),
        'title': 'التركيبات قيد التنفيذ'
    }

    return render(request, 'installations/in_progress_list.html', context)


@login_required
def print_installation_schedule(request):
    """طباعة جدول التركيبات"""
    date = request.GET.get('date', timezone.now().date())
    team_id = request.GET.get('team')
    status = request.GET.get('status')

    installations = InstallationSchedule.objects.select_related(
        'order', 'order__customer', 'team'
    ).order_by('scheduled_date', 'scheduled_time')

    # تطبيق الفلاتر
    if date:
        installations = installations.filter(scheduled_date=date)
    if team_id:
        installations = installations.filter(team_id=team_id)
    if status:
        installations = installations.filter(status=status)

    context = {
        'installations': installations,
        'date': date,
        'team': InstallationTeam.objects.get(id=team_id) if team_id else None,
        'status': status,
        'print_date': timezone.now(),
        'title': 'جدول التركيبات'
    }

    return render(request, 'installations/print_schedule.html', context)


@login_required
def view_scheduling_details(request, installation_id):
    """عرض تفاصيل الجدولة"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    # الحصول على سجل تغييرات الجدولة
    from .models import InstallationEventLog
    schedule_events = InstallationEventLog.objects.filter(
        installation=installation,
        event_type='schedule_change'
    ).order_by('-created_at')

    # الحصول على التركيبات المجدولة في نفس اليوم
    same_day_installations = InstallationSchedule.objects.filter(
        scheduled_date=installation.scheduled_date
    ).exclude(id=installation.id).select_related('order', 'order__customer', 'team')

    context = {
        'installation': installation,
        'schedule_events': schedule_events,
        'same_day_installations': same_day_installations,
        'title': 'تفاصيل الجدولة'
    }

    return render(request, 'installations/scheduling_details.html', context)


@login_required
def edit_scheduling_settings(request, installation_id):
    """تعديل إعدادات الجدولة"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)

    if request.method == 'POST':
        form = InstallationScheduleForm(request.POST, instance=installation)
        if form.is_valid():
            # حفظ الإعدادات القديمة للمقارنة
            old_settings = {
                'scheduled_date': installation.scheduled_date,
                'scheduled_time': installation.scheduled_time,
                'team': installation.team,
                'priority': getattr(installation, 'priority', None),
                'estimated_duration': getattr(installation, 'estimated_duration', None)
            }
            
            installation = form.save()
            
            # إنشاء سجل للتغييرات
            from .models import InstallationEventLog
            changes = []
            if old_settings['scheduled_date'] != installation.scheduled_date:
                changes.append(f"التاريخ: {old_settings['scheduled_date']} → {installation.scheduled_date}")
            if old_settings['scheduled_time'] != installation.scheduled_time:
                changes.append(f"الوقت: {old_settings['scheduled_time']} → {installation.scheduled_time}")
            if old_settings['team'] != installation.team:
                old_team = old_settings['team'].name if old_settings['team'] else 'غير محدد'
                new_team = installation.team.name if installation.team else 'غير محدد'
                changes.append(f"الفريق: {old_team} → {new_team}")
            
            if changes:
                InstallationEventLog.objects.create(
                    installation=installation,
                    event_type='settings_change',
                    description=f'تم تعديل إعدادات الجدولة: {", ".join(changes)}',
                    user=request.user,
                    metadata={
                        'old_settings': old_settings,
                        'changes': changes
                    }
                )
            
            messages.success(request, 'تم تحديث إعدادات الجدولة بنجاح')
            return redirect('installations:installation_detail', installation_id=installation.id)
    else:
        form = InstallationScheduleForm(instance=installation)

    context = {
        'form': form,
        'installation': installation,
        'title': 'تعديل إعدادات الجدولة'
    }

    return render(request, 'installations/edit_scheduling_settings.html', context)


def get_installation_date_info(installation):
    """
    دالة مساعدة للحصول على معلومات تاريخ التركيب مع الملاحظات
    """
    if installation.notes:
        # البحث عن ملاحظات تغيير التاريخ
        if "--- ملاحظة تغيير التاريخ ---" in installation.notes:
            return {
                'has_date_change': True,
                'notes': installation.notes,
                'scheduled_date': installation.scheduled_date,
                'completion_date': installation.completion_date
            }
    
    return {
        'has_date_change': False,
        'notes': installation.notes,
        'scheduled_date': installation.scheduled_date,
        'completion_date': installation.completion_date
    }


@login_required
def update_installation_date_from_scheduled(request, installation_id):
    """تحديث تاريخ التركيب بناء على التاريخ المجدول"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    
    if request.method == 'POST':
        try:
            # تحديث التاريخ بناء على التاريخ المجدول
            if installation.scheduled_date:
                installation.installation_date = installation.scheduled_date
                installation.save(update_fields=['installation_date'])
                
                # إنشاء سجل حدث
                from .models import InstallationEventLog
                InstallationEventLog.objects.create(
                    installation=installation,
                    event_type='date_update',
                    description=f'تم تحديث تاريخ التركيب إلى {installation.scheduled_date} بناء على التاريخ المجدول',
                    user=request.user,
                    metadata={
                        'old_date': None,
                        'new_date': str(installation.scheduled_date),
                        'updated_from_scheduled': True
                    }
                )
                
                messages.success(request, f'تم تحديث تاريخ التركيب بنجاح إلى {installation.scheduled_date}')
                return JsonResponse({
                    'success': True,
                    'message': f'تم تحديث التاريخ بنجاح إلى {installation.scheduled_date}',
                    'new_date': str(installation.scheduled_date)
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'لا يوجد تاريخ مجدول للتركيب'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'حدث خطأ أثناء تحديث التاريخ: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'طريقة الطلب غير صحيحة'
    })


@login_required
@permission_required('installations.delete_installationschedule', raise_exception=True)
def delete_installation(request, installation_id):
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    if request.method == 'POST':
        installation.delete()
        messages.success(request, 'تم حذف التركيب بنجاح.')
        return redirect(reverse('installations:installation_list'))
    return render(request, 'installations/installation_confirm_delete.html', {
        'installation': installation
    })


@login_required
def debt_orders_list(request):
    """قائمة الطلبات التي عليها مديونية"""
    from django.db.models import Q, F
    
    # معالجة الفلاتر
    order_status_filter = request.GET.get('order_status', '')
    search = request.GET.get('search', '').strip()
    page_size = int(request.GET.get('page_size', 25))
    
    # جلب الطلبات التي عليها مديونية (باستخدام F expressions لحساب المبلغ المتبقي)
    debt_orders_query = Order.objects.filter(
        total_amount__gt=F('paid_amount')
    ).select_related('customer', 'salesperson', 'branch').annotate(
        debt_amount=F('total_amount') - F('paid_amount')
    )
    
    # تطبيق الفلاتر
    if order_status_filter:
        debt_orders_query = debt_orders_query.filter(order_status=order_status_filter)
    
    if search:
        search_q = Q(order_number__icontains=search) | \
                  Q(customer__name__icontains=search) | \
                  Q(customer__phone__icontains=search)
        debt_orders_query = debt_orders_query.filter(search_q)
    
    # ترتيب حسب المبلغ المتبقي (الأعلى أولاً)
    debt_orders_query = debt_orders_query.order_by('-debt_amount', '-created_at')
    
    # ترقيم الصفحات
    paginator = Paginator(debt_orders_query, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # حساب الإجماليات
    total_debt = debt_orders_query.aggregate(
        total=models.Sum('debt_amount')
    )['total'] or 0
    
    # إحصائيات حسب الحالة
    status_stats = debt_orders_query.values('order_status').annotate(
        count=Count('id'),
        debt_sum=models.Sum('debt_amount')
    ).order_by('-debt_sum')
    
    context = {
        'page_obj': page_obj,
        'debt_orders': page_obj,
        'total_debt': total_debt,
        'total_count': debt_orders_query.count(),
        'status_stats': status_stats,
        'current_filters': {
            'order_status': order_status_filter,
            'search': search,
            'page_size': page_size,
        },
        'has_filters': bool(order_status_filter or search),
        'order_status_choices': [
            ('', 'جميع الحالات'),
            ('pending_approval', 'قيد الموافقة'),
            ('approved', 'تمت الموافقة'),
            ('ready_install', 'جاهز للتركيب'),
            ('completed', 'مكتمل'),
            ('delivered', 'تم التسليم'),
        ]
    }
    
    return render(request, 'installations/debt_orders_list.html', context)


@login_required
def team_detail(request, team_id):
    """تفاصيل الفريق"""
    team = get_object_or_404(InstallationTeam, id=team_id)
    
    # إحصائيات الفريق
    team_installations = InstallationSchedule.objects.filter(team=team)
    completed_count = team_installations.filter(status='completed').count()
    in_progress_count = team_installations.filter(status='in_installation').count()
    scheduled_count = team_installations.filter(status='scheduled').count()
    
    context = {
        'team': team,
        'team_installations': team_installations.order_by('-created_at')[:10],
        'stats': {
            'total': team_installations.count(),
            'completed': completed_count,
            'in_progress': in_progress_count,
            'scheduled': scheduled_count,
        }
    }
    
    return render(request, 'installations/team_detail.html', context)


@login_required
def edit_team(request, team_id):
    """تعديل الفريق"""
    team = get_object_or_404(InstallationTeam, id=team_id)
    
    if request.method == 'POST':
        form = InstallationTeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث بيانات الفريق بنجاح'))
            return redirect('installations:team_management')
    else:
        form = InstallationTeamForm(instance=team)
    
    context = {
        'form': form,
        'team': team,
    }
    
    return render(request, 'installations/edit_team.html', context)


@login_required
def delete_team(request, team_id):
    """حذف الفريق"""
    team = get_object_or_404(InstallationTeam, id=team_id)
    
    if request.method == 'POST':
        team_name = team.name
        team.delete()
        messages.success(request, f'تم حذف الفريق "{team_name}" بنجاح')
        return redirect('installations:team_management')
    
    context = {
        'team': team,
    }
    
    return render(request, 'installations/confirm_delete_team.html', context)


@login_required
def edit_technician(request, technician_id):
    """تعديل الفني"""
    technician = get_object_or_404(Technician, id=technician_id)
    
    if request.method == 'POST':
        form = TechnicianEditForm(request.POST, instance=technician)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث بيانات الفني بنجاح')
            return redirect('installations:team_management')
    else:
        form = TechnicianEditForm(instance=technician)
    
    context = {
        'form': form,
        'technician': technician,
    }
    
    return render(request, 'installations/edit_technician.html', context)


@login_required
def delete_technician(request, technician_id):
    """حذف الفني - مع التحقق من عدم استخدامه في أقسام أخرى"""
    technician = get_object_or_404(Technician, id=technician_id)
    
    # التحقق من أن الفني غير مرتبط بأي فريق تركيب
    installation_teams = InstallationTeam.objects.filter(technicians=technician)
    
    if request.method == 'POST':
        # إذا كان الفني مرتبط بفرق تركيب، لا يمكن حذفه
        if installation_teams.exists():
            teams_names = ', '.join([team.name for team in installation_teams])
            messages.error(request, f'لا يمكن حذف الفني "{technician.name}" لأنه مرتبط بالفرق التالية: {teams_names}. يجب إزالته من الفرق أولاً.')
            return redirect('installations:team_management')
        
        # تحذير: هذا سيحذف الفني من النظام بالكامل
        technician_name = technician.name
        technician.delete()
        messages.warning(request, f'تم حذف الفني "{technician_name}" من النظام بالكامل')
        return redirect('installations:team_management')
    
    context = {
        'technician': technician,
        'installation_teams': installation_teams,
    }
    
    return render(request, 'installations/confirm_delete_technician.html', context)


@login_required
def edit_driver(request, driver_id):
    """تعديل السائق"""
    driver = get_object_or_404(Driver, id=driver_id)
    
    if request.method == 'POST':
        form = DriverForm(request.POST, instance=driver)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تحديث بيانات السائق بنجاح'))
            return redirect('installations:team_management')
    else:
        form = DriverForm(instance=driver)
    
    context = {
        'form': form,
        'driver': driver,
    }
    
    return render(request, 'installations/edit_driver.html', context)


@login_required
def delete_driver(request, driver_id):
    """حذف السائق"""
    driver = get_object_or_404(Driver, id=driver_id)
    
    if request.method == 'POST':
        driver_name = driver.name
        driver.delete()
        messages.success(request, f'تم حذف السائق "{driver_name}" بنجاح')
        return redirect('installations:team_management')
    
    context = {
        'driver': driver,
    }
    
    return render(request, 'installations/confirm_delete_driver.html', context)


# Views للوصول بالكود بدلاً من ID
@login_required
def installation_detail_by_code(request, installation_code):
    """عرض تفاصيل التركيب باستخدام كود التركيب"""
    # البحث بطريقة محسنة للأداء
    if '-T' in installation_code:
        order_number = installation_code.replace('-T', '')
        installation = get_object_or_404(
            InstallationSchedule.objects.select_related('order', 'order__customer', 'team'),
            order__order_number=order_number
        )
    else:
        # للأكواد القديمة
        installation_id = installation_code.replace('#', '').replace('-T', '')
        installation = get_object_or_404(
            InstallationSchedule.objects.select_related('order', 'order__customer', 'team'),
            id=installation_id
        )
    
    return installation_detail(request, installation.id)

@login_required
def installation_detail_redirect(request, installation_id):
    """إعادة توجيه من ID إلى كود التركيب"""
    installation = get_object_or_404(InstallationSchedule, id=installation_id)
    return redirect('installations:installation_detail_by_code', installation_code=installation.installation_code)