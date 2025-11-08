"""
واجهات API للتحديثات الحية والبيانات المخزونية
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Sum, F, Case, When, IntegerField
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import Product, StockAlert, StockTransaction, StockTransfer, Category, Warehouse
from .inventory_utils import (
    get_cached_dashboard_stats,
    get_cached_stock_level,
    invalidate_product_cache
)
from notifications.models import Notification


@require_GET
@login_required
def dashboard_stats_api(request):
    """
    API للإحصائيات الحية للوحة التحكم
    """
    try:
        # الحصول على إحصائيات محدثة
        stats = get_cached_dashboard_stats()
        
        # إضافة إحصائيات إضافية للإشعارات الحية
        # الأخبار المهمة
        recent_alerts = StockAlert.objects.filter(
            status='active'
        ).select_related('product').order_by('-created_at')[:5]
        
        # تنبيهات حديثة للمستخدم
        user_notifications = Notification.objects.filter(
            visible_to=request.user,
            is_read=False
        ).filter(notification_type__in=[
            'stock_shortage', 'low_stock', 'out_of_stock'
        ]).order_by('-created_at')[:5]
        
        # عدد التنبيهات غير المقروءة
        unread_notifications_count = user_notifications.count()
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'recent_alerts': [
                {
                    'id': alert.id,
                    'type': alert.alert_type,
                    'priority': alert.priority,
                    'title': alert.title,
                    'message': alert.message,
                    'product_name': alert.product.name,
                    'product_code': alert.product.code,
                    'current_balance': alert.quantity_after,
                    'threshold': alert.threshold_limit,
                    'created_at': alert.created_at.isoformat(),
                } for alert in recent_alerts
            ],
            'notifications': [
                {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'notification_type': notification.notification_type,
                    'created_at': notification.created_at.isoformat(),
                } for notification in user_notifications
            ],
            'unread_count': unread_notifications_count,
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_GET
@login_required
def product_stock_info_api(request, product_id):
    """
    API للحصول على معلومات المخزون الفورية لمنتج معين
    """
    try:
        product = get_object_or_404(Product, id=product_id)
        current_stock = get_cached_stock_level(product_id)
        
        # حساب الحالة
        if current_stock <= 0:
            status = 'out_of_stock'
            status_text = 'نفذ من المستودع'
            status_color = '#dc3545'
        elif current_stock <= product.minimum_stock:
            status = 'low_stock'
            status_text = 'مخزون منخفض'
            status_color = '#ffc107'
        elif hasattr(product, 'maximum_stock') and product.maximum_stock and current_stock > product.maximum_stock:
            status = 'overstock'
            status_text = 'فائض في المخزون'
            status_color = '#fd7e14'
        else:
            status = 'normal'
            status_text = 'مخزون متوفر'
            status_color = '#28a745'
        
        # آخر الحركات
        recent_transactions = StockTransaction.objects.filter(
            product=product
        ).select_related('created_by').order_by('-transaction_date')[:10]
        
        return JsonResponse({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'code': product.code,
                'price': float(product.price) if product.price else 0,
                'unit': product.unit,
                'minimum_stock': product.minimum_stock,
                'current_stock': current_stock,
                'status': status,
                'status_text': status_text,
                'status_color': status_color,
            },
            'transactions': [
                {
                    'id': trans.id,
                    'transaction_type': trans.transaction_type,
                    'quantity': trans.quantity,
                    'running_balance': trans.running_balance,
                    'transaction_date': trans.transaction_date.isoformat(),
                    'created_by': trans.created_by.get_full_name() if trans.created_by else 'System',
                    'notes': trans.notes,
                } for trans in recent_transactions
            ],
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_GET
@login_required
def stock_alerts_api(request):
    """
    API للحصول على جميع تنبيهات المخزون النشطة
    """
    try:
        # الفلاتر
        alert_type = request.GET.get('alert_type', '')
        status = request.GET.get('status', 'active')
        priority = request.GET.get('priority', '')
        
        alerts = StockAlert.objects.all().select_related('product')
        
        # تطبيق الفلاتر
        if alert_type:
            alerts = alerts.filter(alert_type=alert_type)
        if status:
            alerts = alerts.filter(status=status)
        if priority:
            alerts = alerts.filter(priority=priority)
        
        # إحصائيات سريعة
        stats = {
            'total_count': alerts.count(),
            'high_priority': alerts.filter(priority='high').count(),
            'medium_priority': alerts.filter(priority='medium').count(),
            'low_priority': alerts.filter(priority='low').count(),
            'by_type': {
                'low_stock': alerts.filter(alert_type='low_stock').count(),
                'out_of_stock': alerts.filter(alert_type='out_of_stock').count(),
                'overstock': alerts.filter(alert_type='overstock').count(),
            }
        }
        
        # البيانات الرئيسية
        alerts_data = alerts.order_by('-created_at')[:50]
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'alerts': [
                {
                    'id': alert.id,
                    'product': {
                        'id': alert.product.id,
                        'name': alert.product.name,
                        'code': alert.product.code,
                    },
                    'alert_type': alert.alert_type,
                    'priority': alert.priority,
                    'title': alert.title,
                    'message': alert.message,
                    'quantity_before': alert.quantity_before,
                    'quantity_after': alert.quantity_after,
                    'threshold_limit': alert.threshold_limit,
                    'status': alert.status,
                    'created_at': alert.created_at.isoformat(),
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                    'resolved_by': alert.resolved_by.get_full_name() if alert.resolved_by else None,
                } for alert in alerts_data
            ],
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_POST
@login_required
def resolve_alert_api(request, alert_id):
    """
    API لمعالجة تنبيه مخزون
    """
    try:
        alert = get_object_or_404(StockAlert, id=alert_id)
        
        if alert.status != 'active':
            return JsonResponse({
                'success': False,
                'message': 'هذا التنبيه ليس نشطاً'
            })
        
        alert.status = 'resolved'
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save()
        
        # إلغاء صلاحية ذاكرة التخزين المؤقتة
        invalidate_product_cache(alert.product.id)
        
        return JsonResponse({
            'success': True,
            'message': 'تم حل التنبيه بنجاح',
            'alert_status': alert.status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_GET
@login_required
def warehouse_stock_summary_api(request, warehouse_id=None):
    """
    API للحصول على ملخص المخزون للمستودعات
    """
    try:
        warehouses = Warehouse.objects.filter(is_active=True)
        
        if warehouse_id:
            warehouses = warehouses.filter(id=warehouse_id)
        
        warehouse_data = []
        
        for warehouse in warehouses:
            # حساب إحصائيات المستودع
            total_products = StockTransaction.objects.filter(
                warehouse=warehouse
            ).values('product').distinct().count()
            
            current_stock_sum = StockTransaction.objects.filter(
                warehouse=warehouse,
                transaction_type='in'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            out_stock_sum = StockTransaction.objects.filter(
                warehouse=warehouse,
                transaction_type='out'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            available_stock = current_stock_sum - out_stock_sum
            
            # حساب القيمة الإجمالية
            stock_value = 0
            last_transactions = StockTransaction.objects.filter(
                warehouse=warehouse,
                transaction_type='in'
            ).select_related('product').order_by('-transaction_date')[:50]
            
            for trans in last_transactions:
                if trans.product and trans.product.price:
                    # حساب قيمة المنتج بناءً على رصيده الحالي
                    try:
                        current_balance = get_cached_stock_level(trans.product.id)
                        stock_value += float(trans.product.price) * float(current_balance)
                    except:
                        pass
            
            warehouse_data.append({
                'id': warehouse.id,
                'name': warehouse.name,
                'branch': warehouse.branch.name if warehouse.branch else None,
                'total_products': total_products,
                'available_stock': available_stock,
                'total_value': round(stock_value, 2),
                'last_updated': timezone.now().isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'warehouses': warehouse_data,
            'total_warehouses': len(warehouse_data),
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_GET
@login_required
def category_stock_analysis_api(request):
    """
    API للتحليل المخزون حسب الفئات
    """
    try:
        category_stats = Category.objects.annotate(
            product_count=Count('products')
        ).filter(product_count__gt=0).order_by('-product_count')[:20]
        
        categories_data = []
        
        for category in category_stats:
            # حساب مخزون الفئة
            category_stock = 0
            category_value = 0
            low_stock_count = 0
            out_of_stock_count = 0
            
            products = category.products.all()[:20]  # محدود للإداء
            
            for product in products:
                stock_level = get_cached_stock_level(product.id)
                category_stock += stock_level
                
                if product.price:
                    category_value += float(product.price) * stock_level
                
                if stock_level <= 0:
                    out_of_stock_count += 1
                elif stock_level <= product.minimum_stock:
                    low_stock_count += 1
            
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'product_count': category.product_count,
                'total_stock': category_stock,
                'total_value': round(category_value, 2),
                'low_stock_count': low_stock_count,
                'out_of_stock_count': out_of_stock_count,
                'health_status': 'critical' if out_of_stock_count > category.product_count * 0.3
                                  else 'warning' if low_stock_count > category.product_count * 0.5
                                  else 'good'
            })
        
        return JsonResponse({
            'success': True,
            'categories': categories_data,
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_GET
@login_required
def get_stock_notifications_count(request):
    """
    API للحصول على عدد الإشعارات غير المقروءة
    """
    try:
        # إشعارات النظام غير المقروءة
        system_notifications = Notification.objects.filter(
            visible_to=request.user,
            is_read=False,
            notification_type__in=['stock_shortage', 'low_stock', 'out_of_stock']
        )
        
        # تنبيهات المخزون النشطة
        stock_alerts = StockAlert.objects.filter(
            status='active'
        )
        
        return JsonResponse({
            'success': True,
            'system_notifications': system_notifications.count(),
            'stock_alerts': stock_alerts.count(),
            'total_notifications': system_notifications.count() + stock_alerts.count(),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_GET
@login_required
def inventory_value_report_api(request):
    """
    API لتقرير قيمة المخزون الكلية - تحليل مالي متقدم
    """
    try:
        from decimal import Decimal
        
        # حساب القيمة الإجمالية للمخزون
        total_inventory_value = Decimal('0')
        category_breakdown = []
        warehouse_breakdown = []
        
        # تحليل حسب الفئات
        categories = Category.objects.annotate(
            product_count=Count('products')
        ).filter(product_count__gt=0)
        
        for category in categories:
            category_value = Decimal('0')
            category_stock = 0
            products_in_category = 0
            
            products = Product.objects.filter(category=category).select_related('category')
            
            for product in products:
                try:
                    stock_level = get_cached_stock_level(product.id)
                    if stock_level > 0 and product.price:
                        product_value = Decimal(str(product.price)) * Decimal(str(stock_level))
                        category_value += product_value
                        category_stock += stock_level
                        products_in_category += 1
                        total_inventory_value += product_value
                except:
                    pass
            
            if category_value > 0:
                category_breakdown.append({
                    'id': category.id,
                    'name': category.name,
                    'total_value': float(category_value),
                    'total_stock': category_stock,
                    'product_count': products_in_category,
                    'percentage': 0  # سيتم حسابها لاحقاً
                })
        
        # حساب النسب المئوية
        for cat in category_breakdown:
            if total_inventory_value > 0:
                cat['percentage'] = round(
                    (Decimal(str(cat['total_value'])) / total_inventory_value) * 100, 2
                )
        
        # تحليل حسب المستودعات
        warehouses = Warehouse.objects.filter(is_active=True)
        
        for warehouse in warehouses:
            warehouse_value = Decimal('0')
            warehouse_stock = 0
            
            # الحصول على المنتجات في المستودع
            warehouse_transactions = StockTransaction.objects.filter(
                warehouse=warehouse,
                transaction_type='in'
            ).values('product_id').distinct()
            
            for trans in warehouse_transactions[:50]:  # محدود للأداء
                try:
                    product = Product.objects.get(id=trans['product_id'])
                    stock_level = get_cached_stock_level(product.id)
                    
                    if stock_level > 0 and product.price:
                        product_value = Decimal(str(product.price)) * Decimal(str(stock_level))
                        warehouse_value += product_value
                        warehouse_stock += stock_level
                except:
                    pass
            
            if warehouse_value > 0:
                warehouse_breakdown.append({
                    'id': warehouse.id,
                    'name': warehouse.name,
                    'branch': warehouse.branch.name if warehouse.branch else 'بدون فرع',
                    'total_value': float(warehouse_value),
                    'total_stock': warehouse_stock,
                    'percentage': round(
                        (warehouse_value / total_inventory_value) * 100, 2
                    ) if total_inventory_value > 0 else 0
                })
        
        # إحصائيات إضافية
        total_products = Product.objects.count()
        products_with_stock = sum(
            1 for p in Product.objects.all()[:100]  # محدود للأداء
            if get_cached_stock_level(p.id) > 0
        )
        
        low_value_products = []
        high_value_products = []
        
        products_with_values = []
        for product in Product.objects.select_related('category')[:100]:
            try:
                stock_level = get_cached_stock_level(product.id)
                if stock_level > 0 and product.price:
                    product_value = float(product.price) * stock_level
                    products_with_values.append({
                        'id': product.id,
                        'name': product.name,
                        'value': product_value,
                        'stock': stock_level,
                        'price': float(product.price)
                    })
            except:
                pass
        
        # ترتيب حسب القيمة
        products_with_values.sort(key=lambda x: x['value'], reverse=True)
        high_value_products = products_with_values[:10]
        low_value_products = products_with_values[-10:] if len(products_with_values) > 10 else []
        
        return JsonResponse({
            'success': True,
            'summary': {
                'total_inventory_value': float(total_inventory_value),
                'total_products': total_products,
                'products_with_stock': products_with_stock,
                'total_categories': len(category_breakdown),
                'total_warehouses': len(warehouse_breakdown)
            },
            'category_breakdown': sorted(
                category_breakdown, 
                key=lambda x: x['total_value'], 
                reverse=True
            ),
            'warehouse_breakdown': sorted(
                warehouse_breakdown,
                key=lambda x: x['total_value'],
                reverse=True
            ),
            'top_value_products': high_value_products,
            'low_value_products': low_value_products,
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_GET
@login_required
def stock_turnover_analysis_api(request):
    """
    API لتحليل معدل دوران المخزون - تحليل متقدم
    """
    try:
        # الحصول على الفترة الزمنية من الطلب
        days = int(request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # حساب معدل الدوران لكل منتج
        turnover_data = []
        
        products = Product.objects.select_related('category')[:50]  # محدود للأداء
        
        for product in products:
            try:
                # حساب المخزون الحالي
                current_stock = get_cached_stock_level(product.id)
                
                # حساب إجمالي الخروج في الفترة
                total_out = StockTransaction.objects.filter(
                    product=product,
                    transaction_type='out',
                    transaction_date__range=[start_date, end_date]
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                # حساب إجمالي الدخول في الفترة
                total_in = StockTransaction.objects.filter(
                    product=product,
                    transaction_type='in',
                    transaction_date__range=[start_date, end_date]
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                # حساب المخزون المتوسط
                avg_stock = (current_stock + total_in - total_out) / 2 if total_in > 0 else current_stock
                
                # حساب معدل الدوران
                if avg_stock > 0:
                    turnover_rate = total_out / avg_stock
                else:
                    turnover_rate = 0
                
                # عدد الأيام للتخلص من المخزون
                if total_out > 0:
                    days_to_sell = (current_stock / (total_out / days)) if total_out > 0 else 999
                else:
                    days_to_sell = 999
                
                # تحديد الحالة
                if turnover_rate > 2:
                    status = 'سريع الحركة'
                    status_color = '#28a745'
                elif turnover_rate > 1:
                    status = 'متوسط الحركة'
                    status_color = '#ffc107'
                elif turnover_rate > 0.5:
                    status = 'بطيء الحركة'
                    status_color = '#fd7e14'
                else:
                    status = 'راكد'
                    status_color = '#dc3545'
                
                turnover_data.append({
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'code': product.code,
                        'category': product.category.name if product.category else 'بدون فئة'
                    },
                    'current_stock': current_stock,
                    'total_in': total_in,
                    'total_out': total_out,
                    'avg_stock': round(avg_stock, 2),
                    'turnover_rate': round(turnover_rate, 2),
                    'days_to_sell': round(days_to_sell, 1) if days_to_sell < 999 else 'N/A',
                    'status': status,
                    'status_color': status_color
                })
            except:
                pass
        
        # ترتيب حسب معدل الدوران
        turnover_data.sort(key=lambda x: x['turnover_rate'], reverse=True)
        
        # إحصائيات عامة
        fast_moving = len([d for d in turnover_data if d['turnover_rate'] > 2])
        medium_moving = len([d for d in turnover_data if 1 < d['turnover_rate'] <= 2])
        slow_moving = len([d for d in turnover_data if 0.5 < d['turnover_rate'] <= 1])
        stagnant = len([d for d in turnover_data if d['turnover_rate'] <= 0.5])
        
        return JsonResponse({
            'success': True,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'summary': {
                'total_products': len(turnover_data),
                'fast_moving': fast_moving,
                'medium_moving': medium_moving,
                'slow_moving': slow_moving,
                'stagnant': stagnant
            },
            'turnover_data': turnover_data,
            'fast_moving_products': [d for d in turnover_data if d['turnover_rate'] > 2][:10],
            'stagnant_products': [d for d in turnover_data if d['turnover_rate'] <= 0.5][:10],
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_GET
@login_required
def pending_transfers_api(request):
    """
    API للحصول على التحويلات المعلقة حسب صلاحيات المستخدم
    
    - مدير النظام: يرى جميع التحويلات
    - مسؤول المخزون: يرى فقط التحويلات الواردة لمستودعاته
    """
    try:
        from .models import Warehouse
        
        user = request.user
        
        # مدير النظام يرى جميع التحويلات المعلقة
        if user.is_superuser:
            pending_transfers = StockTransfer.objects.filter(
                status__in=['approved', 'in_transit']
            ).select_related('from_warehouse', 'to_warehouse', 'created_by').order_by('-transfer_date')
        else:
            # مسؤول المخزون يرى فقط التحويلات الواردة لمستودعاته
            managed_warehouses = Warehouse.objects.filter(manager=user)
            
            if not managed_warehouses.exists():
                return JsonResponse({
                    'success': True,
                    'count': 0,
                    'transfers': [],
                    'message': 'لا توجد مستودعات مسجلة باسمك'
                })
            
            pending_transfers = StockTransfer.objects.filter(
                to_warehouse__in=managed_warehouses,
                status__in=['approved', 'in_transit']
            ).select_related('from_warehouse', 'to_warehouse', 'created_by').order_by('-transfer_date')
        
        # بناء البيانات
        transfers_data = []
        for transfer in pending_transfers[:20]:  # أول 20
            transfers_data.append({
                'id': transfer.id,
                'transfer_number': transfer.transfer_number,
                'from_warehouse': {
                    'id': transfer.from_warehouse.id,
                    'name': transfer.from_warehouse.name
                },
                'to_warehouse': {
                    'id': transfer.to_warehouse.id,
                    'name': transfer.to_warehouse.name
                },
                'status': transfer.status,
                'status_display': transfer.get_status_display(),
                'transfer_date': transfer.transfer_date.isoformat() if transfer.transfer_date else None,
                'expected_arrival_date': transfer.expected_arrival_date.isoformat() if transfer.expected_arrival_date else None,
                'created_by': transfer.created_by.get_full_name() if transfer.created_by else 'النظام',
                'created_at': transfer.created_at.isoformat(),
                'total_items': transfer.items.count() if hasattr(transfer, 'items') else 0,
                'reason': transfer.reason or '',
                'url': f'/inventory/stock-transfer/{transfer.id}/'
            })
        
        return JsonResponse({
            'success': True,
            'count': pending_transfers.count(),
            'transfers': transfers_data,
            'is_superuser': user.is_superuser,
            'managed_warehouses': [
                {'id': w.id, 'name': w.name} 
                for w in Warehouse.objects.filter(manager=user)
            ] if not user.is_superuser else [],
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)


@require_GET
@login_required
def reorder_recommendations_api(request):
    """
    API لاقتراحات إعادة الطلب التلقائي - نظام ذكي
    """
    try:
        recommendations = []
        
        products = Product.objects.select_related('category')
        
        for product in products[:100]:  # محدود للأداء
            try:
                current_stock = get_cached_stock_level(product.id)
                
                # فحص إذا كان المخزون أقل من الحد الأدنى
                if current_stock <= product.minimum_stock:
                    # حساب متوسط الاستهلاك اليومي
                    last_30_days = timezone.now().date() - timedelta(days=30)
                    
                    consumption = StockTransaction.objects.filter(
                        product=product,
                        transaction_type='out',
                        transaction_date__gte=last_30_days
                    ).aggregate(total=Sum('quantity'))['total'] or 0
                    
                    daily_consumption = consumption / 30 if consumption > 0 else 0
                    
                    # حساب الكمية المقترحة
                    # الكمية = (الحد الأقصى - المخزون الحالي) + (متوسط الاستهلاك * 7 أيام)
                    max_stock = product.minimum_stock * 3  # افتراضي
                    buffer_stock = daily_consumption * 7
                    
                    suggested_quantity = max(
                        (max_stock - current_stock) + buffer_stock,
                        product.minimum_stock - current_stock
                    )
                    
                    # حساب الأولوية
                    if current_stock <= 0:
                        priority = 'عاجل'
                        priority_level = 3
                    elif current_stock <= product.minimum_stock * 0.5:
                        priority = 'عالي'
                        priority_level = 2
                    else:
                        priority = 'متوسط'
                        priority_level = 1
                    
                    # تقدير الوقت حتى نفاد المخزون
                    if daily_consumption > 0:
                        days_until_stockout = current_stock / daily_consumption
                    else:
                        days_until_stockout = 999
                    
                    recommendations.append({
                        'product': {
                            'id': product.id,
                            'name': product.name,
                            'code': product.code,
                            'category': product.category.name if product.category else 'بدون فئة'
                        },
                        'current_stock': current_stock,
                        'minimum_stock': product.minimum_stock,
                        'suggested_quantity': round(suggested_quantity, 2),
                        'daily_consumption': round(daily_consumption, 2),
                        'days_until_stockout': round(days_until_stockout, 1) if days_until_stockout < 999 else 'N/A',
                        'priority': priority,
                        'priority_level': priority_level,
                        'estimated_cost': float(product.price * suggested_quantity) if product.price else 0
                    })
            except:
                pass
        
        # ترتيب حسب الأولوية
        recommendations.sort(key=lambda x: (x['priority_level'], -x['current_stock']), reverse=True)
        
        # حساب التكلفة الإجمالية
        total_estimated_cost = sum(r['estimated_cost'] for r in recommendations)
        
        return JsonResponse({
            'success': True,
            'summary': {
                'total_recommendations': len(recommendations),
                'urgent': len([r for r in recommendations if r['priority'] == 'عاجل']),
                'high_priority': len([r for r in recommendations if r['priority'] == 'عالي']),
                'medium_priority': len([r for r in recommendations if r['priority'] == 'متوسط']),
                'total_estimated_cost': round(total_estimated_cost, 2)
            },
            'recommendations': recommendations,
            'urgent_items': [r for r in recommendations if r['priority'] == 'عاجل'][:20],
            'last_updated': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        }, status=500)
