from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta, datetime
from .models import Warehouse, WarehouseLocation, StockAlert

@login_required
def warehouse_location_list(request):
    """View for listing warehouse locations"""
    # البحث والتصفية
    search_query = request.GET.get('search', '')
    warehouse_id = request.GET.get('warehouse', '')
    status = request.GET.get('status', '')
    sort_by = request.GET.get('sort', 'name')
    
    # البدء بجميع المواقع
    locations = WarehouseLocation.objects.all().select_related('warehouse')
    
    # تطبيق البحث
    if search_query:
        locations = locations.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # تصفية حسب المستودع
    if warehouse_id:
        locations = locations.filter(warehouse_id=warehouse_id)
    
    # تصفية حسب الحالة
    if status == 'active':
        locations = locations.filter(is_active=True)
    elif status == 'inactive':
        locations = locations.filter(is_active=False)
    
    # حساب نسبة الإشغال لكل موقع
    for location in locations:
        location.used_capacity = 50  # قيمة افتراضية، يجب تحديثها لاحقاً
        location.occupancy_rate = int((location.used_capacity / location.capacity) * 100)
    
    # تطبيق الترتيب
    if sort_by == 'name':
        locations = sorted(locations, key=lambda x: x.name)
    elif sort_by == '-name':
        locations = sorted(locations, key=lambda x: x.name, reverse=True)
    elif sort_by == 'warehouse':
        locations = sorted(locations, key=lambda x: x.warehouse.name)
    elif sort_by == 'occupancy':
        locations = sorted(locations, key=lambda x: x.occupancy_rate)
    elif sort_by == '-occupancy':
        locations = sorted(locations, key=lambda x: x.occupancy_rate, reverse=True)
    
    # الإحصائيات
    total_locations = len(locations)
    warehouses_count = Warehouse.objects.count()
    products_count = 1000  # قيمة افتراضية، يجب تحديثها لاحقاً
    occupancy_rate = 65  # قيمة افتراضية، يجب تحديثها لاحقاً
    
    # الصفحات
    paginator = Paginator(locations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إضافة عدد التنبيهات النشطة
    alerts_count = StockAlert.objects.filter(status='active').count()
    
    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = StockAlert.objects.filter(
        status='active'
    ).select_related('product').order_by('-created_at')[:5]
    
    # إضافة السنة الحالية لشريط التذييل
    current_year = datetime.now().year
    
    # الحصول على المستودعات لفلتر البحث
    warehouses = Warehouse.objects.filter(is_active=True)
    
    context = {
        'locations': page_obj,
        'page_obj': page_obj,
        'warehouses': warehouses,
        'total_locations': total_locations,
        'warehouses_count': warehouses_count,
        'products_count': products_count,
        'occupancy_rate': occupancy_rate,
        'search_query': search_query,
        'selected_warehouse': warehouse_id,
        'selected_status': status,
        'sort_by': sort_by,
        'active_menu': 'warehouse_locations',
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year
    }
    return render(request, 'inventory/warehouse_location_list.html', context)

@login_required
def warehouse_location_create(request):
    """View for creating a new warehouse location"""
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        warehouse_id = request.POST.get('warehouse')
        capacity = request.POST.get('capacity')
        description = request.POST.get('description')
        is_active = request.POST.get('is_active') == 'on'
        
        if not all([name, code, warehouse_id, capacity]):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'يجب إدخال جميع الحقول المطلوبة'
                })
            messages.error(request, 'يجب إدخال جميع الحقول المطلوبة')
            return redirect('inventory:warehouse_location_list')
        
        # التحقق من عدم تكرار الرمز
        if WarehouseLocation.objects.filter(code=code).exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'رمز الموقع مستخدم بالفعل'
                })
            messages.error(request, 'رمز الموقع مستخدم بالفعل')
            return redirect('inventory:warehouse_location_list')
        
        try:
            warehouse = get_object_or_404(Warehouse, id=warehouse_id)
            
            location = WarehouseLocation.objects.create(
                name=name,
                code=code,
                warehouse=warehouse,
                capacity=capacity,
                description=description,
                is_active=is_active
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'تم إضافة موقع التخزين بنجاح',
                    'location_id': location.id
                })
            
            messages.success(request, 'تم إضافة موقع التخزين بنجاح')
            return redirect('inventory:warehouse_location_list')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'حدث خطأ أثناء إضافة موقع التخزين: {str(e)}'
                })
            messages.error(request, f'حدث خطأ أثناء إضافة موقع التخزين: {str(e)}')
            return redirect('inventory:warehouse_location_list')
    
    return redirect('inventory:warehouse_location_list')

@login_required
def warehouse_location_update(request, pk):
    """View for updating a warehouse location"""
    location = get_object_or_404(WarehouseLocation, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        warehouse_id = request.POST.get('warehouse')
        capacity = request.POST.get('capacity')
        description = request.POST.get('description')
        is_active = request.POST.get('is_active') == 'on'
        
        if not all([name, code, warehouse_id, capacity]):
            messages.error(request, 'يجب إدخال جميع الحقول المطلوبة')
            return redirect('inventory:warehouse_location_update', pk=pk)
        
        # التحقق من عدم تكرار الرمز
        if WarehouseLocation.objects.filter(code=code).exclude(pk=pk).exists():
            messages.error(request, 'رمز الموقع مستخدم بالفعل')
            return redirect('inventory:warehouse_location_update', pk=pk)
        
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        
        location.name = name
        location.code = code
        location.warehouse = warehouse
        location.capacity = capacity
        location.description = description
        location.is_active = is_active
        location.save()
        
        messages.success(request, 'تم تحديث موقع التخزين بنجاح')
        return redirect('inventory:warehouse_location_list')
    
    warehouses = Warehouse.objects.filter(is_active=True)
    
    context = {
        'location': location,
        'warehouses': warehouses,
        'active_menu': 'warehouse_locations'
    }
    return render(request, 'inventory/warehouse_location_form.html', context)

@login_required
def warehouse_location_delete(request, pk):
    """View for deleting a warehouse location"""
    location = get_object_or_404(WarehouseLocation, pk=pk)
    
    if request.method == 'POST':
        # التحقق من عدم وجود منتجات مرتبطة بالموقع
        # هذا التحقق سيتم تنفيذه لاحقاً عند إضافة العلاقة بين المنتجات والمواقع
        
        location.delete()
        messages.success(request, 'تم حذف موقع التخزين بنجاح')
        return redirect('inventory:warehouse_location_list')
    
    context = {
        'location': location,
        'active_menu': 'warehouse_locations'
    }
    return render(request, 'inventory/warehouse_location_confirm_delete.html', context)

@login_required
def warehouse_location_detail(request, pk):
    """View for viewing warehouse location details"""
    location = get_object_or_404(WarehouseLocation, pk=pk)
    
    # حساب نسبة الإشغال
    location.used_capacity = 50  # قيمة افتراضية، يجب تحديثها لاحقاً
    location.occupancy_rate = int((location.used_capacity / location.capacity) * 100)
    
    # إضافة عدد التنبيهات النشطة
    alerts_count = StockAlert.objects.filter(status='active').count()
    
    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = StockAlert.objects.filter(
        status='active'
    ).select_related('product').order_by('-created_at')[:5]
    
    # إضافة السنة الحالية لشريط التذييل
    current_year = datetime.now().year
    
    context = {
        'location': location,
        'active_menu': 'warehouse_locations',
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year
    }
    return render(request, 'inventory/warehouse_location_detail.html', context)
