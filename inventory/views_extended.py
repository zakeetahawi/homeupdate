from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import (
    Category, Product, Supplier, Warehouse, WarehouseLocation,
    PurchaseOrder, PurchaseOrderItem, StockTransaction, StockAlert
)
from accounts.models import User, Branch

# Category Views
@login_required
def category_list(request):
    """View for listing categories"""
    categories = Category.objects.all().prefetch_related('children', 'products')

    # إضافة عدد التنبيهات النشطة
    alerts_count = StockAlert.objects.filter(status='active').count()

    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = StockAlert.objects.filter(
        status='active'
    ).select_related('product').order_by('-created_at')[:5]

    # إضافة السنة الحالية لشريط التذييل
    from datetime import datetime
    current_year = datetime.now().year

    context = {
        'categories': categories,
        'active_menu': 'categories',
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year
    }
    return render(request, 'inventory/category_list_new.html', context)

@login_required
def category_create(request):
    """View for creating a new category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        parent_id = request.POST.get('parent')

        if not name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'يجب إدخال اسم الفئة'
                })
            messages.error(request, 'يجب إدخال اسم الفئة')
            return redirect('inventory:category_list')

        parent = None
        if parent_id:
            parent = get_object_or_404(Category, id=parent_id)

        try:
            category = Category.objects.create(
                name=name,
                description=description,
                parent=parent
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'تم إضافة الفئة بنجاح',
                    'category_id': category.id
                })
            
            messages.success(request, 'تم إضافة الفئة بنجاح')
            return redirect('inventory:category_list')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'حدث خطأ أثناء إضافة الفئة: {str(e)}'
                })
            messages.error(request, f'حدث خطأ أثناء إضافة الفئة: {str(e)}')
            return redirect('inventory:category_list')

    return redirect('inventory:category_list')

@login_required
def category_update(request, pk):
    """View for updating a category"""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        parent_id = request.POST.get('parent')

        if not name:
            messages.error(request, 'يجب إدخال اسم الفئة')
            return redirect('inventory:category_list')

        # تجنب تعيين الفئة كأب لنفسها
        if parent_id and int(parent_id) == pk:
            messages.error(request, 'لا يمكن تعيين الفئة كأب لنفسها')
            return redirect('inventory:category_list')

        parent = None
        if parent_id:
            parent = get_object_or_404(Category, id=parent_id)

            # تجنب الدورات في شجرة الفئات
            if category.id in [c.id for c in parent.get_ancestors(include_self=True)]:
                messages.error(request, 'لا يمكن تعيين فئة فرعية كأب')
                return redirect('inventory:category_list')

        category.name = name
        category.description = description
        category.parent = parent
        category.save()

        messages.success(request, 'تم تحديث الفئة بنجاح')
        return redirect('inventory:category_list')

    categories = Category.objects.exclude(pk=pk)
    context = {
        'category': category,
        'categories': categories,
        'active_menu': 'categories'
    }
    return render(request, 'inventory/category_form.html', context)

@login_required
def category_delete(request, pk):
    """View for deleting a category"""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        # التحقق من وجود منتجات مرتبطة بالفئة
        if category.products.exists():
            messages.error(request, 'لا يمكن حذف الفئة لأنها تحتوي على منتجات')
            return redirect('inventory:category_list')

        # التحقق من وجود فئات فرعية
        if category.children.exists():
            messages.error(request, 'لا يمكن حذف الفئة لأنها تحتوي على فئات فرعية')
            return redirect('inventory:category_list')

        category.delete()
        messages.success(request, 'تم حذف الفئة بنجاح')
        return redirect('inventory:category_list')

    context = {
        'category': category,
        'active_menu': 'categories'
    }
    return render(request, 'inventory/category_confirm_delete.html', context)

# Warehouse Views
@login_required
def warehouse_list(request):
    """View for listing warehouses"""
    warehouses = Warehouse.objects.all().select_related('branch', 'manager', 'created_by')

    # حساب عدد المنتجات في كل مستودع بناءً على حركات المخزون
    for warehouse in warehouses:
        # حساب المنتجات التي لها حركات مخزون في هذا المستودع
        warehouse.product_count = StockTransaction.objects.filter(
            warehouse=warehouse
        ).values('product').distinct().count()
        
        # إضافة قائمة المنتجات للعرض في التفاصيل
        warehouse.products = Product.objects.filter(
            transactions__warehouse=warehouse
        ).distinct()

    # حساب إحصائيات المستودعات
    active_warehouses_count = Warehouse.objects.filter(is_active=True).count()
    inactive_warehouses_count = Warehouse.objects.filter(is_active=False).count()

    # إضافة عدد التنبيهات النشطة
    alerts_count = StockAlert.objects.filter(status='active').count()

    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = StockAlert.objects.filter(
        status='active'
    ).select_related('product').order_by('-created_at')[:5]

    # إضافة السنة الحالية لشريط التذييل
    from datetime import datetime
    current_year = datetime.now().year

    # الحصول على الفروع والمستخدمين لنموذج الإضافة
    branches = Branch.objects.all()
    users = User.objects.filter(is_active=True)

    context = {
        'warehouses': list(warehouses),  # تحويل إلى list لتجنب مشاكل QuerySet
        'active_warehouses_count': active_warehouses_count,
        'inactive_warehouses_count': inactive_warehouses_count,
        'branches': branches,
        'users': users,
        'active_menu': 'warehouses',
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year
    }
    return render(request, 'inventory/warehouse_list_new.html', context)

@login_required
def warehouse_create(request):
    """View for creating a new warehouse"""
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        branch_id = request.POST.get('branch')
        manager_id = request.POST.get('manager')
        address = request.POST.get('address')
        notes = request.POST.get('notes')
        is_active = request.POST.get('is_active') == 'on'

        # التحقق من البيانات المطلوبة
        if not all([name, code]):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'يجب إدخال اسم المستودع والرمز'
                })
            messages.error(request, 'يجب إدخال اسم المستودع والرمز')
            return redirect('inventory:warehouse_list')

        # التحقق من عدم تكرار الرمز
        if Warehouse.objects.filter(code=code).exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'رمز المستودع مستخدم بالفعل'
                })
            messages.error(request, 'رمز المستودع مستخدم بالفعل')
            return redirect('inventory:warehouse_list')

        # الفرع اختياري - يمكن تركه فارغاً
        branch = None
        if branch_id:
            try:
                branch = Branch.objects.get(id=branch_id)
            except Branch.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'الفرع المحدد غير موجود'
                    })
                messages.error(request, 'الفرع المحدد غير موجود')
                return redirect('inventory:warehouse_list')

        manager = None
        if manager_id:
            try:
                manager = User.objects.get(id=manager_id)
            except User.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'المدير المحدد غير موجود'
                    })
                messages.error(request, 'المدير المحدد غير موجود')
                return redirect('inventory:warehouse_list')

        try:
            warehouse = Warehouse.objects.create(
                name=name,
                code=code,
                branch=branch,
                manager=manager,
                address=address,
                notes=notes,
                is_active=is_active,
                created_by=request.user
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'تم إضافة المستودع بنجاح',
                    'warehouse_id': warehouse.id
                })
            
            messages.success(request, 'تم إضافة المستودع بنجاح')
            return redirect('inventory:warehouse_list')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'حدث خطأ أثناء إضافة المستودع: {str(e)}'
                })
            messages.error(request, f'حدث خطأ أثناء إضافة المستودع: {str(e)}')
            return redirect('inventory:warehouse_list')

    return redirect('inventory:warehouse_list')


@login_required
def warehouse_update(request, pk):
    """View for updating a warehouse"""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        branch_id = request.POST.get('branch')
        manager_id = request.POST.get('manager')
        address = request.POST.get('address')
        notes = request.POST.get('notes')
        is_active = request.POST.get('is_active') == 'on'

        if not all([name, code]):
            messages.error(request, 'يجب إدخال اسم المستودع والرمز')
            return redirect('inventory:warehouse_list')

        # التحقق من عدم تكرار الرمز (باستثناء المستودع الحالي)
        if Warehouse.objects.filter(code=code).exclude(pk=pk).exists():
            messages.error(request, 'رمز المستودع مستخدم بالفعل')
            return redirect('inventory:warehouse_list')

        # تحديث البيانات
        warehouse.name = name
        warehouse.code = code
        warehouse.address = address
        warehouse.notes = notes
        warehouse.is_active = is_active
        
        # تحديث الفرع إذا تم تحديده
        if branch_id:
            warehouse.branch = get_object_or_404(Branch, id=branch_id)
        else:
            warehouse.branch = None
            
        # تحديث المدير إذا تم تحديده
        if manager_id:
            warehouse.manager = get_object_or_404(User, id=manager_id)
        else:
            warehouse.manager = None

        warehouse.save()
        messages.success(request, 'تم تحديث المستودع بنجاح')
        return redirect('inventory:warehouse_list')

    # عرض نموذج التحديث
    branches = Branch.objects.all()
    users = User.objects.filter(is_active=True)
    
    context = {
        'warehouse': warehouse,
        'branches': branches,
        'users': users,
        'active_menu': 'warehouses'
    }
    return render(request, 'inventory/warehouse_form.html', context)


@login_required
def warehouse_delete(request, pk):
    """View for deleting a warehouse"""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    if request.method == 'POST':
        warehouse_name = warehouse.name
        
        # التحقق من وجود حركات مخزون مرتبطة بالمستودع
        stock_transactions_count = StockTransaction.objects.filter(
            warehouse=warehouse
        ).count()
        
        # التحقق من وجود طلبات شراء مرتبطة بالمستودع
        purchase_orders_count = PurchaseOrder.objects.filter(warehouse=warehouse).count()
        
        # التحقق من وجود مواقع تخزين مرتبطة
        locations_count = warehouse.locations.count()
        
        # جمع جميع البيانات المرتبطة
        total_related_items = stock_transactions_count + purchase_orders_count + locations_count
        
        if total_related_items > 0:
            # تحضير رسالة تفصيلية بالبيانات المرتبطة
            error_details = []
            if stock_transactions_count > 0:
                error_details.append(f"حركات المخزون ({stock_transactions_count})")
            if purchase_orders_count > 0:
                error_details.append(f"طلبات الشراء ({purchase_orders_count})")
            if locations_count > 0:
                error_details.append(f"مواقع التخزين ({locations_count})")
            
            error_message = f'لا يمكن حذف المستودع "{warehouse_name}" لأنه مرتبط بـ: {", ".join(error_details)}. يجب حذف هذه البيانات أولاً.'
            
            messages.error(request, error_message)
            return redirect('inventory:warehouse_list')
        
        # إذا لم توجد عوائق، قم بالحذف
        try:
            warehouse.delete()
            messages.success(request, f'تم حذف المستودع "{warehouse_name}" بنجاح')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف المستودع: {str(e)}')
        
        return redirect('inventory:warehouse_list')
    
    return redirect('inventory:warehouse_list')


@login_required
def warehouse_detail(request, pk):
    """View for warehouse details"""
    warehouse = get_object_or_404(Warehouse.objects.select_related('branch', 'manager', 'created_by'), pk=pk)
    
    # إحصائيات المستودع الفعلية
    from django.db.models import Sum, Count, Q
    
    # عدد المنتجات في المستودع
    products_in_warehouse = StockTransaction.objects.filter(
        warehouse=warehouse
    ).values('product').distinct().count()
    
    # إجمالي الكمية في المستودع
    total_quantity = StockTransaction.objects.filter(
        warehouse=warehouse,
        transaction_type='in'
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # إجمالي الكمية الصادرة
    total_out_quantity = StockTransaction.objects.filter(
        warehouse=warehouse,
        transaction_type='out'
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    # الكمية المتوفرة حالياً
    available_quantity = total_quantity - total_out_quantity
    
    # القيمة الإجمالية للمخزون
    total_value = 0
    if available_quantity > 0:
        # حساب القيمة بناءً على سعر المنتجات
        product_values = StockTransaction.objects.filter(
            warehouse=warehouse,
            transaction_type='in'
        ).select_related('product').values('product__price', 'quantity')
        
        for item in product_values:
            total_value += float(item['product__price'] or 0) * float(item['quantity'] or 0)
    
    # آخر حركات المخزون
    recent_transactions = StockTransaction.objects.filter(
        warehouse=warehouse
    ).select_related('product', 'created_by').order_by('-transaction_date')[:10]
    
    # المنتجات في المستودع مع كمياتها
    warehouse_products = []
    products_data = StockTransaction.objects.filter(
        warehouse=warehouse
    ).values('product__id').distinct()

    for product_data in products_data:
        product_id = product_data['product__id']

        # الحصول على آخر حركة للمنتج في هذا المستودع
        last_trans = StockTransaction.objects.filter(
            warehouse=warehouse,
            product_id=product_id
        ).select_related('product', 'product__category').order_by('-transaction_date', '-id').first()

        if last_trans:
            available = last_trans.running_balance

            if available > 0:  # إظهار المنتجات المتوفرة فقط
                warehouse_products.append({
                    'id': product_id,
                    'name': last_trans.product.name,
                    'code': last_trans.product.code,
                    'category': last_trans.product.category,
                    'unit': last_trans.product.unit,
                    'quantity': available,
                    'last_update': last_trans.transaction_date
                })
    
    context = {
        'warehouse': warehouse,
        'active_menu': 'warehouses',
        'products_count': products_in_warehouse,
        'total_quantity': available_quantity,
        'total_value': total_value,
        'recent_transactions': recent_transactions,
        'warehouse_products': warehouse_products,
        'locations_count': warehouse.locations.count()
    }
    return render(request, 'inventory/warehouse_detail.html', context)

# Supplier Views
@login_required
def supplier_list(request):
    """View for listing suppliers"""
    # البحث والتصفية
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'name')

    # البدء بجميع الموردين
    suppliers = Supplier.objects.all()

    # تطبيق البحث
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(address__icontains=search_query) |
            Q(tax_number__icontains=search_query)
        )

    # تطبيق الترتيب
    if sort_by:
        suppliers = suppliers.order_by(sort_by)

    # الإحصائيات
    active_purchase_orders = PurchaseOrder.objects.filter(
        status__in=['draft', 'pending', 'approved', 'partial']
    ).count()

    total_purchases = PurchaseOrder.objects.filter(
        status__in=['approved', 'partial', 'received']
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    top_products_count = 10  # قيمة افتراضية

    # الصفحات
    paginator = Paginator(suppliers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # إضافة عدد التنبيهات النشطة
    alerts_count = StockAlert.objects.filter(status='active').count()

    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = StockAlert.objects.filter(
        status='active'
    ).select_related('product').order_by('-created_at')[:5]

    # إضافة السنة الحالية لشريط التذييل
    from datetime import datetime
    current_year = datetime.now().year

    context = {
        'suppliers': page_obj,
        'page_obj': page_obj,
        'active_purchase_orders': active_purchase_orders,
        'total_purchases': total_purchases,
        'top_products_count': top_products_count,
        'search_query': search_query,
        'sort_by': sort_by,
        'active_menu': 'suppliers',
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year
    }
    return render(request, 'inventory/supplier_list_new.html', context)

@login_required
def supplier_create(request):
    """View for creating a new supplier"""
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_person = request.POST.get('contact_person')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        notes = request.POST.get('notes')

        if not name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'يجب إدخال اسم المورد'
                })
            messages.error(request, 'يجب إدخال اسم المورد')
            return redirect('inventory:supplier_list')

        try:
            supplier = Supplier.objects.create(
                name=name,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                notes=notes
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'تم إضافة المورد بنجاح',
                    'supplier_id': supplier.id
                })
            
            messages.success(request, 'تم إضافة المورد بنجاح')
            return redirect('inventory:supplier_list')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'حدث خطأ أثناء إضافة المورد: {str(e)}'
                })
            messages.error(request, f'حدث خطأ أثناء إضافة المورد: {str(e)}')
            return redirect('inventory:supplier_list')

    return redirect('inventory:supplier_list')

# Purchase Order Views
@login_required
def purchase_order_list(request):
    """View for listing purchase orders"""
    # البحث والتصفية
    search_query = request.GET.get('search', '')
    supplier_id = request.GET.get('supplier', '')
    status = request.GET.get('status', '')
    date_range = request.GET.get('date_range', '')

    # البدء بجميع الطلبات
    purchase_orders = PurchaseOrder.objects.all().select_related('supplier', 'warehouse', 'created_by')

    # تطبيق البحث
    if search_query:
        purchase_orders = purchase_orders.filter(
            Q(order_number__icontains=search_query) |
            Q(supplier__name__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    # تصفية حسب المورد
    if supplier_id:
        purchase_orders = purchase_orders.filter(supplier_id=supplier_id)

    # تصفية حسب الحالة
    if status:
        purchase_orders = purchase_orders.filter(status=status)

    # تصفية حسب الفترة الزمنية
    today = timezone.now().date()
    if date_range == 'today':
        purchase_orders = purchase_orders.filter(order_date=today)
    elif date_range == 'week':
        start_of_week = today - timedelta(days=today.weekday())
        purchase_orders = purchase_orders.filter(order_date__gte=start_of_week)
    elif date_range == 'month':
        purchase_orders = purchase_orders.filter(order_date__year=today.year, order_date__month=today.month)
    elif date_range == 'quarter':
        current_quarter = (today.month - 1) // 3 + 1
        quarter_start_month = (current_quarter - 1) * 3 + 1
        quarter_start_date = timezone.datetime(today.year, quarter_start_month, 1).date()
        purchase_orders = purchase_orders.filter(order_date__gte=quarter_start_date)
    elif date_range == 'year':
        purchase_orders = purchase_orders.filter(order_date__year=today.year)

    # الإحصائيات
    total_orders = purchase_orders.count()
    pending_orders = purchase_orders.filter(status__in=['draft', 'pending']).count()
    received_orders = purchase_orders.filter(status='received').count()
    total_amount = purchase_orders.aggregate(total=Sum('total_amount'))['total'] or 0

    # الصفحات
    paginator = Paginator(purchase_orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # الحصول على الموردين لفلتر البحث
    suppliers = Supplier.objects.all()

    # إضافة عدد التنبيهات النشطة
    alerts_count = StockAlert.objects.filter(status='active').count()

    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = StockAlert.objects.filter(
        status='active'
    ).select_related('product').order_by('-created_at')[:5]

    # إضافة السنة الحالية لشريط التذييل
    from datetime import datetime
    current_year = datetime.now().year

    # إضافة التاريخ الحالي لنموذج إنشاء طلب شراء جديد
    today = timezone.now()

    # الحصول على المستودعات لنموذج إنشاء طلب شراء جديد
    warehouses = Warehouse.objects.filter(is_active=True)

    context = {
        'purchase_orders': page_obj,
        'page_obj': page_obj,
        'suppliers': suppliers,
        'warehouses': warehouses,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'received_orders': received_orders,
        'total_amount': total_amount,
        'search_query': search_query,
        'selected_supplier': supplier_id,
        'selected_status': status,
        'selected_date_range': date_range,
        'active_menu': 'purchase_orders',
        'alerts_count': alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year,
        'today': today
    }
    return render(request, 'inventory/purchase_order_list_new.html', context)

@login_required
def purchase_order_create(request):
    """View for creating a new purchase order"""
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        warehouse_id = request.POST.get('warehouse')
        expected_date = request.POST.get('expected_date')
        notes = request.POST.get('notes')
        
        if not supplier_id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'يجب اختيار المورد'
                })
            messages.error(request, 'يجب اختيار المورد')
            return redirect('inventory:purchase_order_list')
        
        try:
            supplier = get_object_or_404(Supplier, id=supplier_id)
            warehouse = None
            if warehouse_id:
                warehouse = get_object_or_404(Warehouse, id=warehouse_id)
            
            # إنشاء طلب الشراء
            purchase_order = PurchaseOrder.objects.create(
                supplier=supplier,
                warehouse=warehouse,
                expected_date=expected_date if expected_date else None,
                notes=notes,
                created_by=request.user
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'تم إنشاء طلب الشراء بنجاح',
                    'purchase_order_id': purchase_order.id
                })
            
            messages.success(request, 'تم إنشاء طلب الشراء بنجاح')
            return redirect('inventory:purchase_order_list')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'حدث خطأ أثناء إنشاء طلب الشراء: {str(e)}'
                })
            messages.error(request, f'حدث خطأ أثناء إنشاء طلب الشراء: {str(e)}')
            return redirect('inventory:purchase_order_list')
    
    return redirect('inventory:purchase_order_list')

# Alert Views
@login_required
def alert_list(request):
    """View for listing stock alerts"""
    # البحث والتصفية
    alert_type = request.GET.get('alert_type', '')
    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')
    date_range = request.GET.get('date_range', '')

    # البدء بجميع التنبيهات
    alerts = StockAlert.objects.all().select_related('product', 'resolved_by')

    # تصفية حسب نوع التنبيه
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)

    # تصفية حسب الحالة
    if status:
        alerts = alerts.filter(status=status)

    # تصفية حسب الأولوية
    if priority:
        alerts = alerts.filter(priority=priority)

    # تصفية حسب الفترة الزمنية
    today = timezone.now().date()
    if date_range == 'today':
        alerts = alerts.filter(created_at__date=today)
    elif date_range == 'week':
        start_of_week = today - timedelta(days=today.weekday())
        alerts = alerts.filter(created_at__date__gte=start_of_week)
    elif date_range == 'month':
        alerts = alerts.filter(created_at__date__year=today.year, created_at__date__month=today.month)

    # الإحصائيات
    active_alerts_count = StockAlert.objects.filter(status='active').count()
    low_stock_alerts_count = StockAlert.objects.filter(status='active', alert_type='low_stock').count()
    expiry_alerts_count = StockAlert.objects.filter(status='active', alert_type='expiry').count()
    resolved_alerts_count = StockAlert.objects.filter(status='resolved').count()

    # الصفحات
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # إضافة آخر التنبيهات للعرض في القائمة المنسدلة
    recent_alerts = StockAlert.objects.filter(
        status='active'
    ).select_related('product').order_by('-created_at')[:5]

    # إضافة السنة الحالية لشريط التذييل
    from datetime import datetime
    current_year = datetime.now().year

    context = {
        'alerts': page_obj,
        'page_obj': page_obj,
        'active_alerts_count': active_alerts_count,
        'low_stock_alerts_count': low_stock_alerts_count,
        'expiry_alerts_count': expiry_alerts_count,
        'resolved_alerts_count': resolved_alerts_count,
        'selected_type': alert_type,
        'selected_status': status,
        'selected_priority': priority,
        'selected_date_range': date_range,
        'active_menu': 'stock_alerts',
        'alerts_count': active_alerts_count,
        'recent_alerts': recent_alerts,
        'current_year': current_year
    }
    return render(request, 'inventory/alert_list_new.html', context)

@login_required
def alert_resolve(request, pk):
    """View for resolving an alert"""
    alert = get_object_or_404(StockAlert, pk=pk)

    if alert.status != 'active':
        messages.error(request, 'هذا التنبيه ليس نشطاً')
        return redirect('inventory:alert_list')

    alert.status = 'resolved'
    alert.resolved_at = timezone.now()
    alert.resolved_by = request.user
    alert.save()

    messages.success(request, 'تم حل التنبيه بنجاح')
    return redirect('inventory:alert_list')

@login_required
def alert_ignore(request, pk):
    """View for ignoring an alert"""
    alert = get_object_or_404(StockAlert, pk=pk)

    if alert.status != 'active':
        messages.error(request, 'هذا التنبيه ليس نشطاً')
        return redirect('inventory:alert_list')

    alert.status = 'ignored'
    alert.resolved_at = timezone.now()
    alert.resolved_by = request.user
    alert.save()

    messages.success(request, 'تم تجاهل التنبيه بنجاح')
    return redirect('inventory:alert_list')

@login_required
@require_POST
def alert_resolve_multiple(request):
    """View for resolving multiple alerts"""
    alert_ids = request.POST.get('alert_ids', '')

    if not alert_ids:
        messages.error(request, 'لم يتم تحديد أي تنبيهات')
        return redirect('inventory:alert_list')

    alert_id_list = [int(id) for id in alert_ids.split(',')]
    alerts = StockAlert.objects.filter(id__in=alert_id_list, status='active')

    for alert in alerts:
        alert.status = 'resolved'
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save()

    messages.success(request, f'تم حل {alerts.count()} تنبيه بنجاح')
    return redirect('inventory:alert_list')
