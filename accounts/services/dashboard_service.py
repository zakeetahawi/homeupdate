from django.db.models import Sum, Q
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta

from customers.models import Customer
from orders.models import Order
from inventory.models import Product, StockTransaction


class DashboardService:
    @staticmethod
    def get_cached_stats(user=None):
        """
        الحصول على الإحصائيات العامة للوحة التحكم مع دعم التخزين المؤقت
        """
        cache_key = f'dashboard_stats_{user.id if user else "all"}'
        stats = cache.get(cache_key)
        
        if stats is None:
            today = timezone.now()
            last_month = today - timedelta(days=30)
            
            # إحصائيات العملاء
            customers = Customer.objects.all()
            if user and not user.is_superuser:
                customers = customers.filter(branch=user.branch)
            
            total_customers = customers.count()
            new_customers_last_month = customers.filter(created_at__gte=last_month).count()
            customer_growth = f"{(new_customers_last_month / total_customers * 100):.1f}%" if total_customers > 0 else "0%"
            
            # إحصائيات الطلبات
            orders = Order.objects.all()
            if user and not user.is_superuser:
                orders = orders.filter(Q(created_by=user) | Q(branch=user.branch))
                
            total_orders = orders.count()
            orders_last_month = orders.filter(created_at__gte=last_month)
            orders_last_month_count = orders_last_month.count()
            order_growth = f"{(orders_last_month_count / total_orders * 100):.1f}%" if total_orders > 0 else "0%"
            
            # إحصائيات المخزون
            products = Product.objects.all()
            current_inventory_value = sum(
                (p.current_stock or 0) * p.price 
                for p in products
            )
            
            prev_month_value = current_inventory_value  # سيتم تحسينه لاحقاً
            inventory_growth = f"{((current_inventory_value - prev_month_value) / prev_month_value * 100):.1f}%" if prev_month_value > 0 else "0%"
            
            # إحصائيات الإيرادات
            monthly_revenue = orders_last_month.aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            prev_month = today - timedelta(days=60)
            prev_monthly_revenue = orders.filter(
                created_at__gte=prev_month,
                created_at__lt=last_month
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            revenue_growth = f"{((monthly_revenue - prev_monthly_revenue) / prev_monthly_revenue * 100):.1f}%" if prev_monthly_revenue > 0 else "0%"
            
            stats = {
                'totalCustomers': total_customers,
                'totalOrders': total_orders,
                'inventoryValue': current_inventory_value,
                'monthlyRevenue': monthly_revenue,
                'customerGrowth': customer_growth,
                'orderGrowth': order_growth,
                'inventoryGrowth': inventory_growth,
                'revenueGrowth': revenue_growth,
            }
            
            # تخزين مؤقت للإحصائيات لمدة 5 دقائق
            cache.set(cache_key, stats, 300)
        
        return stats

    @staticmethod
    def get_recent_activities(user=None, limit=10):
        """
        الحصول على آخر النشاطات في النظام
        """
        activities = []
        today = timezone.now()
        
        # جمع آخر طلبات العملاء
        orders = Order.objects.select_related('customer').order_by('-created_at')[:limit]
        for order in orders:
            activities.append({
                'id': f'order_{order.id}',
                'type': 'order',
                'message': f'تم إنشاء طلب جديد للعميل {order.customer.name}',
                'timestamp': order.created_at.isoformat()
            })
        
        # جمع آخر معاملات المخزون
        transactions = StockTransaction.objects.select_related(
            'product'
        ).order_by('-date')[:limit]
        for trans in transactions:
            direction = 'إضافة' if trans.transaction_type == 'in' else 'سحب'
            activities.append({
                'id': f'inventory_{trans.id}',
                'type': 'inventory',
                'message': f'تم {direction} {trans.quantity} وحدة من {trans.product.name}',
                'timestamp': trans.date.isoformat()
            })
        
        # سيتم إضافة أنشطة أوامر الإنتاج بعد إعادة بناء نظام المصنع
        
        # ترتيب النشاطات حسب التاريخ
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:limit]

    @staticmethod
    def get_recent_orders(user=None, limit=5):
        """
        الحصول على آخر الطلبات
        """
        orders = Order.objects.select_related('customer').order_by('-created_at')
        if user and not user.is_superuser:
            orders = orders.filter(Q(created_by=user) | Q(branch=user.branch))
        
        recent_orders = []
        for order in orders[:limit]:
            recent_orders.append({
                'id': order.id,
                'customerName': order.customer.name,
                'amount': order.total_amount,
                'status': order.status,
                'date': order.created_at.isoformat()
            })
        
        return recent_orders

    @staticmethod
    def get_trends_data(days=30):
        """
        الحصول على بيانات الاتجاهات للرسم البياني
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        dates = []
        customers_data = []
        orders_data = []
        revenue_data = []
        
        current_date = start_date
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            dates.append(current_date.strftime('%Y-%m-%d'))
            
            # عدد العملاء الجدد
            customers_data.append(
                Customer.objects.filter(
                    created_at__date=current_date.date()
                ).count()
            )
            
            # عدد الطلبات
            daily_orders = Order.objects.filter(
                created_at__date=current_date.date()
            )
            orders_data.append(daily_orders.count())
            
            # الإيرادات
            daily_revenue = daily_orders.aggregate(
                total=Sum('total_amount')
            )['total'] or 0
            revenue_data.append(float(daily_revenue))
            
            current_date = next_date
        
        return {
            'labels': dates,
            'customers': customers_data,
            'orders': orders_data,
            'revenue': revenue_data
        }